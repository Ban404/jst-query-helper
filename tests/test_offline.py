"""离线单元测试：只测纯逻辑，不需要水宝、网络或凭据。

运行：python -m pytest tests/ -q
"""
import base64
import importlib.util
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JST_PATH = os.path.join(ROOT, "skill", "scripts", "jst.py")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def jst():
    # 把脚本目录加进 sys.path，让 ask.py 里的 `import jst` 能找到
    sys.path.insert(0, os.path.dirname(JST_PATH))
    return _load(JST_PATH, "jst")


def _fake_jwt(payload, expired=False):
    head = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    p = dict(payload)
    p["exp"] = 1 if expired else 4102444800
    body = base64.urlsafe_b64encode(json.dumps(p).encode()).decode().rstrip("=")
    return head + "." + body + ".x"


# ------------------------------------------------------------------ token
def test_straighten_reversed_jwt(jst):
    good = _fake_jwt({"u_name": "tester"})
    reversed_blob = good[::-1]
    assert jst.normalize_token(reversed_blob) == good
    assert jst.normalize_token(good) == good


def test_straighten_garbage_unchanged(jst):
    assert jst.normalize_token("not-a-token") == "not-a-token"


def test_decode_claims(jst):
    tok = _fake_jwt({"co_name": "Demo Co", "u_name": "tester"})
    claims = jst.decode_claims(tok)
    assert claims["co_name"] == "Demo Co"
    assert claims["u_name"] == "tester"


def test_expired_detection(jst):
    exp = jst.decode_claims(_fake_jwt({}, expired=True))["exp"]
    assert exp <= __import__("datetime").datetime.now().timestamp()


# ------------------------------------------------------------------ 分段 / 翻页
def test_time_windows_advances(jst):
    wins = jst.time_windows(days=15, span=7)
    assert len(wins) >= 2
    for (a, b), (c, d) in zip(wins, wins[1:]):
        assert a < b and c < d          # 每段内部开始早于结束
        assert c > b                    # 下一段起点晚于上一段终点（首尾相接、不重叠）
    assert wins[0][0] < wins[-1][1]


def test_segmented_exact_skips_splitting(jst, monkeypatch):
    calls = []

    def fake_query(action, params):
        calls.append(params)
        return {"ok": True, "data": {"orders": [{"so_id": "X"}]}}

    monkeypatch.setattr(jst, "query", fake_query)
    rows, err = jst.segmented("orders_single_query", {"so_ids": ["X"]}, days=90)
    assert err is None
    assert len(rows) == 1
    assert len(calls) == 1  # 精确条件只查一次，不分段
    assert "modified_begin" not in calls[0]


# ------------------------------------------------------------------ 结果摊平
def test_rows_of_inline_data(jst):
    res = {"ok": True, "data": {"orders": [{"so_id": "1"}, {"so_id": "2"}], "has_next": False}}
    rows, meta = jst.rows_of(res)
    assert len(rows) == 2 and meta["has_next"] is False


def test_rows_of_from_file(jst, tmp_path):
    f = tmp_path / "raw.json"
    f.write_text(json.dumps({"datas": [{"sku": "A"}]}), encoding="utf-8")
    rows, _ = jst.rows_of({"ok": True, "raw_data_path": str(f)})
    assert rows == [{"sku": "A"}]


def test_rows_of_failed_result(jst):
    assert jst.rows_of({"ok": False}) == ([], {})


# ------------------------------------------------------------------ 只读白名单
def test_query_vs_write_partition(jst):
    q = jst.query_actions()
    assert len(q) == 36
    assert "shops_query" in q
    assert "inventory_query" in q


def test_denied_write_is_readonly(jst, monkeypatch):
    monkeypatch.setattr(jst, "load_guide", lambda: {"errors": {}})
    # 找一个写接口
    write = next(k for k, v in jst.all_actions().items() if v.get("kind") == "write")
    out = jst.denied(write)
    assert out["error"]["code"] == "READONLY_MODE"


def test_denied_unknown_is_not_allowed(jst, monkeypatch):
    monkeypatch.setattr(jst, "load_guide", lambda: {"errors": {}})
    out = jst.denied("definitely_not_an_action")
    assert out["error"]["code"] == "ACTION_NOT_ALLOWED"


def test_arg_value(jst):
    assert jst.arg_value(["invoke", "--action", "x", "--params", "{}"], "--action") == "x"
    assert jst.arg_value(["x", "--action=y"], "--action") == "y"
    assert jst.arg_value([], "--action") is None
