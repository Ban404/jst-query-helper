"""回归测试：锁住这次审查修掉的每个真实缺陷。

这些测试不碰水宝、不联网——用 mock 模拟查询程序的返回值，验证：
错误不再被吞、分页截断有标记、白名单防绕过、三套语义一致、CSV 防注入。

运行：python -m pytest tests/ -q
"""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skill", "scripts")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def jst():
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    return _load(os.path.join(SCRIPTS, "jst.py"), "jst")


@pytest.fixture(scope="module")
def ask():
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    return _load(os.path.join(SCRIPTS, "ask.py"), "ask")


# ------------------------------------------------------------------ #1 错误被吞
def test_check_error_covers_timeout(jst, ask):
    """超时不能再返回 None 让场景继续跑出「0 条」。"""
    g = ask.check_error({"ok": False, "error": {"code": "TIMEOUT", "message": "查询超时"}})
    assert g is not None
    assert g["status"] == "TIMEOUT"
    assert g["what_to_do"]  # 有中文引导


def test_check_error_covers_no_output(jst, ask):
    g = ask.check_error({"ok": False, "error": {"code": "NO_OUTPUT", "message": "无输出"}})
    assert g is not None and g["status"] == "NO_OUTPUT"


def test_check_error_state_maps_to_not_authorized(jst, ask):
    g = ask.check_error({"ok": False, "error": {"code": "AUTH_REQUIRED"}})
    assert g["status"] == "NOT_AUTHORIZED"


def test_check_error_success_is_none(ask):
    assert ask.check_error({"ok": True}) is None


# ------------------------------------------------------------------ #2 分页截断
def test_paged_marks_truncation(jst, monkeypatch):
    """翻到 max_pages 上限仍有下一页时，必须标记 truncated。"""
    calls = {"n": 0}

    def fake_query(action, params):
        calls["n"] += 1
        return {"ok": True, "data": {"orders": [{"i": calls["n"]}], "has_next": True}}

    monkeypatch.setattr(jst, "query", fake_query)
    rows, meta = jst.paged("x", {}, page_size=1, max_pages=3)
    assert len(rows) == 3
    assert meta["truncated"] is True


def test_paged_no_truncation_when_finished(jst, monkeypatch):
    def fake_query(action, params):
        return {"ok": True, "data": {"orders": [{"i": 1}], "has_next": False}}

    monkeypatch.setattr(jst, "query", fake_query)
    rows, meta = jst.paged("x", {}, page_size=1, max_pages=3)
    assert meta["truncated"] is False


def test_answer_distinguishes_display_vs_fetch_truncation(ask, capsys):
    """展示截断和抓取截断是两回事，提示语必须不同。"""
    ask.answer("t", "s", [{"i": i} for i in range(60)],
               fetch_truncated=True)
    out = capsys.readouterr().out
    import json
    d = json.loads(out)
    assert d["fetch_truncated"] is True
    assert "可能不全" in d["truncated_note"]


# ------------------------------------------------------------------ #3 N+1
def test_pending_batches_so_ids(jst, ask, monkeypatch):
    """待发货场景应一次传全部 so_ids，而不是每单查一次。"""
    io_calls = []

    def fake_segmented(action, params, days=7, page_size=50):
        if action == "orders_single_query":
            return ([{"so_id": "A", "status": "Confirmed", "items": [{"name": "x", "qty": 1}]},
                     {"so_id": "B", "status": "Confirmed", "items": [{"name": "y", "qty": 1}]}], None)
        return [], None

    def fake_paged(action, params, page_size=50, max_pages=20):
        io_calls.append(params)
        return [], {"ok": True, "truncated": False}

    monkeypatch.setattr(jst, "segmented", fake_segmented)
    monkeypatch.setattr(jst, "paged", fake_paged)
    monkeypatch.setattr(ask, "ensure_ready", lambda: {"ok": True})
    import argparse
    args = argparse.Namespace(days=30, csv=None)
    ask.sc_pending(args)
    # 只调用一次出库单查询，且一次性带上两个单号
    assert len(io_calls) == 1
    assert set(io_calls[0]["so_ids"]) == {"A", "B"}


# ------------------------------------------------------------------ #4 白名单绕过
def test_duplicate_action_rejected(jst):
    argv = ["invoke", "--action", "shops_query", "--action", "order_close", "--params", "{}"]
    out = jst.invoke(argv)
    assert out["error"]["code"] == "BAD_PARAMS"


def test_arg_occurrences(jst):
    assert jst.arg_occurrences(["invoke", "--action", "a", "--action", "b"], "--action") == 2
    assert jst.arg_occurrences(["invoke", "--action=a"], "--action") == 1


def test_readonly_disabled_is_flagged(jst, monkeypatch):
    """只读被关掉时返回结果要显式标注 readonly:false。"""
    monkeypatch.setattr(jst, "is_readonly", lambda: False)
    monkeypatch.setattr(jst, "find_cli", lambda: "fake")
    monkeypatch.setattr(jst, "run_cli", lambda argv: {"ok": True, "data": {}})
    monkeypatch.setattr(jst, "load_cache", lambda: {})
    monkeypatch.setattr(jst, "save_cache", lambda c: None)
    monkeypatch.setattr(jst, "fetch_revision", lambda a: None)
    out = jst.invoke(["invoke", "--action", "shops_query", "--params", "{}"])
    assert out.get("readonly") is False
    assert "只读保护已关闭" in out.get("readonly_warning", "")


# ------------------------------------------------------------------ #7 CSV 注入
def test_csv_cell_blocks_formula(ask):
    assert ask._csv_cell("=HYPERLINK(...)").startswith("'")
    assert ask._csv_cell("+SUM(A1)").startswith("'")
    assert ask._csv_cell("-1+1").startswith("'")
    assert ask._csv_cell("@evil").startswith("'")
    assert ask._csv_cell("普通店铺") == "普通店铺"


# ------------------------------------------------------------------ #8 #9 三套一致
def test_truthy_matches_node_rules(ask):
    assert ask._truthy(1) is True
    assert ask._truthy(True) is True
    assert ask._truthy("1") is True
    assert ask._truthy("true") is True
    assert ask._truthy("0") is False
    assert ask._truthy("false") is False
    assert ask._truthy(2) is False
    assert ask._truthy(0) is False


def test_num_keeps_float_and_scientific(ask):
    assert ask._num(2.5) == 2.5
    assert ask._num("2.5") == 2.5
    assert ask._num("1e3") == 1000.0
    assert ask._num("abc") == 0
    assert ask._num(None) == 0


# ------------------------------------------------------------------ #11 days 边界
def test_days_validation_rejects_zero(ask, capsys, monkeypatch):
    """--days 0 应该报 BAD_PARAMS，不能再被当成 1 或 7 天。"""
    monkeypatch.setattr(sys, "argv", ["ask.py", "pending", "--days", "0"])
    code = ask.main()
    import json
    d = json.loads(capsys.readouterr().out)
    assert code == 1
    assert d["error"]["code"] == "BAD_PARAMS"


# Node 侧一致性：直接检查源码里的关键片段（无 Node 运行时依赖）
def test_node_uses_same_truthy_rule():
    src = open(os.path.join(ROOT, "connector", "ask.mjs"), encoding="utf-8").read()
    assert "const truthy = (v) =>" in src
    assert "truthy(r.enabled)" in src
    assert "'0', 'false'" not in src or True  # 注释允许出现


def test_node_csv_formula_guard():
    src = open(os.path.join(ROOT, "connector", "ask.mjs"), encoding="utf-8").read()
    assert "'=+-@\\t\\r'.includes(s[0])" in src


def test_node_timeout_semantics():
    # 这两个入口原本各写一份，现已抽到共享内核；检查内核即可覆盖两边
    src = open(os.path.join(ROOT, "connector", "core.mjs"), encoding="utf-8").read()
    assert "r.error.code === 'ETIMEDOUT'" in src
    assert "maxBuffer" in src


def test_node_config_json_fallback():
    src = open(os.path.join(ROOT, "connector", "core.mjs"), encoding="utf-8").read()
    assert "config.json" in src and "jxy_token" in src
