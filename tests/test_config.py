"""话术单一真源回归测试：占位符、共用配置、三套一致、兜底话术。

不需要水宝、网络或凭据。运行：python -m pytest tests/ -q
"""
import importlib.util
import json
import os
import re
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
    sys.path.insert(0, SCRIPTS)
    return _load(os.path.join(SCRIPTS, "jst.py"), "jst")


@pytest.fixture(scope="module")
def ask(jst):
    return _load(os.path.join(SCRIPTS, "ask.py"), "ask")


def _placeholders(value):
    return set(re.findall(r"\{\{([^}]+)\}\}", json.dumps(value, ensure_ascii=False)))


def test_guide_placeholders_all_resolve(jst):
    loaded = jst.load_guide()
    assert not _placeholders(loaded), _placeholders(loaded)
    assert loaded["shuibao_download"] == "https://jxy.ai/download"
    assert loaded["statuses"]["SHUIBAO_MISSING"]["url"] == "https://jxy.ai/download"
    assert "{{download}}" not in json.dumps(loaded, ensure_ascii=False)


def test_guide_phrases_reused(jst):
    """公共话术从 phrases 展开，不再散在每个状态里。"""
    loaded = jst.load_guide()
    phrase = loaded["phrases"]["say_done"]
    hits = [k for k, v in loaded["statuses"].items() if phrase in str(v.get("what_to_do", ""))]
    assert len(hits) >= 4, hits
    assert phrase in loaded["statuses"]["TOKEN_EXPIRED"]["what_to_do"]


def test_default_hint_consumed(ask, jst):
    """兜底话术来自 errors._default，未登记的错误码也拿到中文话术。"""
    default = jst.load_guide()["errors"]["_default"]
    assert ask.hint_for("SOME_BRAND_NEW_ERROR") == default
    out = {}
    from contextlib import redirect_stdout
    import io
    buf = io.StringIO()
    with redirect_stdout(buf):
        ask.failed("SOME_BRAND_NEW_ERROR", "测试")
    out = json.loads(buf.getvalue())
    assert out["what_to_do"] == default


def test_scenarios_placeholders_only_days_left(jst):
    loaded = jst.load_scenarios()
    left = _placeholders(loaded) - {"days"}
    assert not left, left


def test_status_words_flow_into_pending_notes(jst):
    """上一版 status_words 与手写话术漂移，这里锁死它们同源。"""
    cfg = jst.load_scenarios()
    tips = jst.notes_for(cfg, "pending", 30)
    joined = " ".join(tips)
    assert cfg["status_words"]["WaitConfirm"] in joined
    assert cfg["status_words"]["Confirmed"] in joined
    assert "{{status_" not in joined
    assert "30 天" in joined


def test_notes_for_fills_days(jst):
    cfg = jst.load_scenarios()
    assert "7 天" in " ".join(jst.notes_for(cfg, "stock", 7))
    assert "90 天" in " ".join(jst.notes_for(cfg, "sn", 90))
    assert "{{days}}" not in " ".join(jst.notes_for(cfg, "stock", 7))


def test_field_dictionary_shared(jst):
    cfg = jst.load_scenarios()
    assert cfg["field_cn"]["so_id"] == "订单号"
    assert cfg["field_cn"]["qty"] == "数量"
    assert "订单号" in cfg["preferred_cn"]
    assert "pending_reasons" in cfg and cfg["pending_reasons"]["shipped"]


def test_three_packages_share_config_bytes():
    paths = [
        os.path.join(ROOT, "connector", "guide.json"),
        os.path.join(ROOT, "skill", "scripts", "guide.json"),
        os.path.join(ROOT, "mcp", "guide.json"),
        os.path.join(ROOT, "connector", "scenarios.json"),
        os.path.join(ROOT, "skill", "scripts", "scenarios.json"),
        os.path.join(ROOT, "mcp", "scenarios.json"),
    ]
    blobs = [open(p, "rb").read() for p in paths]
    assert blobs[:3] == [blobs[0]] * 3, "三套 guide.json 不一致，先跑 tools/sync_core.py"
    assert blobs[3:] == [blobs[3]] * 3, "三套 scenarios.json 不一致，先跑 tools/sync_core.py"


def test_no_hardcoded_url_in_guide_body():
    raw = open(os.path.join(ROOT, "connector", "guide.json"), encoding="utf-8").read()
    assert raw.count("https://jxy.ai/download") == 1
    assert raw.count("https://www.juxieyun.com/shuibao") == 1


def test_node_entries_use_shared_core():
    for rel in (("connector", "ask.mjs"), ("connector", "server.mjs"),
                ("mcp", "ask.mjs"), ("mcp", "server.mjs")):
        src = open(os.path.join(ROOT, *rel), encoding="utf-8").read()
        assert "from './core.mjs'" in src, rel
        assert "createCore(HERE)" in src, rel
