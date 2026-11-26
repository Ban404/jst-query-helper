#!/usr/bin/env python3
"""真实环境自检：需要本机装好水宝、登录并完成授权。跑之前先跑 verify_offline.py。

验证：真实查一次聚水潭、9 个场景、只读拦截、CSV 导出、MCP 握手。
不会改动任何 ERP 数据。退出码 0 = 全过。
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JST = os.path.join(ROOT, "skill", "scripts", "jst.py")
ASK = os.path.join(ROOT, "skill", "scripts", "ask.py")
SERVER = os.path.join(ROOT, "connector", "server.mjs")
MCP_SERVER = os.path.join(ROOT, "mcp", "server.mjs")
PY = sys.executable
PASS, FAIL = [], []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(("  [OK]   " if ok else "  [FAIL] ") + label + (("  -> " + str(detail)) if detail else ""))


def run(script, args, timeout=300):
    env = dict(os.environ)
    env.pop("JXY_TOKEN", None)
    p = subprocess.run([PY, script] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, env=env)
    try:
        return json.loads((p.stdout or "").strip())
    except Exception:
        return {"_raw": (p.stdout or "")[:200], "_err": (p.stderr or "")[:200]}


def looks_answer(d):
    return bool(d.get("ok")) and bool(d.get("summary")) and isinstance(d.get("rows"), list) and "count" in d


def handshake(requests, timeout=600, server=SERVER):
    env = dict(os.environ)
    env.pop("JXY_TOKEN", None)
    payload = "\n".join(json.dumps(r, ensure_ascii=False) for r in requests) + "\n"
    p = subprocess.run(["node", server], input=payload, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, env=env)
    ans = {}
    for line in (p.stdout or "").splitlines():
        try:
            m = json.loads(line)
            if m.get("id") is not None:
                ans[m["id"]] = m
        except Exception:
            continue
    return ans


def tool_text(ans, req_id):
    parts = ((ans.get(req_id) or {}).get("result") or {}).get("content") or []
    try:
        return json.loads(parts[0]["text"])
    except Exception:
        return {"_text": (parts[0].get("text") if parts else "")[:200]}


def main():
    print("== 0. 体检 ==")
    state = run(JST, ["doctor"])
    check("体检返回结构化引导", bool(state.get("status")), state.get("status"))
    if state.get("status") != "READY":
        print("本机未就绪（%s）。请先按 what_to_do 完成安装/登录/授权。" % state.get("status"))
        return 1

    print("== 1. 底层查询 ==")
    shops = run(JST, ["invoke", "--action", "shops_query", "--params", '{"page_index":1,"page_size":3}'])
    check("真实查到店铺", shops.get("ok") is True, (shops.get("presentation") or {}).get("summary"))
    all_acts = run(JST, ["list_actions"])
    check("不带域自动汇总 12 域 / 89 接口",
          all_acts.get("ok") is True and all_acts.get("count") == 89 and all_acts.get("domains") == 12,
          (all_acts.get("count"), all_acts.get("domains")))

    print("== 2. 只读拦截 ==")
    actions = json.loads(open(os.path.join(ROOT, "catalog", "actions.json"), encoding="utf-8").read())["actions"]
    write_action = next((k for k, v in actions.items() if v.get("kind") == "write"), "")
    blocked = run(JST, ["invoke", "--action", write_action, "--params", "{}"])
    check("写接口被拦 READONLY_MODE", (blocked.get("error") or {}).get("code") == "READONLY_MODE")
    unknown = run(JST, ["invoke", "--action", "not_a_real_action_xyz", "--params", "{}"])
    check("未登记接口被拦 ACTION_NOT_ALLOWED",
          (unknown.get("error") or {}).get("code") == "ACTION_NOT_ALLOWED")

    print("== 3. 九个场景 ==")
    for label, argv in [
        ("list 场景清单", ["list"]),
        ("find 找接口", ["find", "库存"]),
        ("overview 经营概览", ["overview", "--days", "1"]),
        ("stock 库存速查", ["stock", "--days", "1"]),
        ("pending 待发货", ["pending", "--days", "1"]),
        ("serials 已发货序列号", ["serials", "--days", "1"]),
        ("shops 店铺列表", ["shops"]),
        ("sn 序列号反查", ["sn", "--sn", "SN-DEMO-0001", "--days", "1"]),
        ("query 通用查询", ["query", "--action", "refund_single_query", "--days", "1"]),
    ]:
        d = run(ASK, argv)
        if label.startswith(("list", "find")):
            check(label + " 返回场景/接口", d.get("ok") is True and d.get("count", 0) >= 1,
                  d.get("count"))
        else:
            check(label + " 有结论结构", looks_answer(d) or bool(d.get("what_to_do")),
                  (d.get("summary") or d.get("status") or str(d.get("_raw"))[:60]))

    print("== 4. CSV 导出 ==")
    tmp = os.path.join(tempfile.gettempdir(), "jst_verify_serials.csv")
    d = run(ASK, ["serials", "--days", "30", "--csv", tmp])
    ok_csv = os.path.isfile(tmp) and open(tmp, "rb").read(3) == b"\xef\xbb\xbf"
    check("导出 UTF-8 BOM 的 CSV", ok_csv and d.get("csv") == tmp, d.get("csv"))

    print("== 5. 连接器 MCP 握手 ==")
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "verify", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "jst_check", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "jst_query", "arguments": {"action": write_action, "params": "{}"}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "jst_actions", "arguments": {}}},
    ]
    ans = handshake(reqs)
    check("initialize 成功",
          ((ans.get(1) or {}).get("result") or {}).get("protocolVersion") == "2025-06-18")
    tools = [t["name"] for t in (((ans.get(2) or {}).get("result") or {}).get("tools") or [])]
    check("tools/list 返回 7 个工具", len(tools) == 7, tools)
    check("连接器体检返回 READY", tool_text(ans, 3).get("status") == "READY")
    check("连接器写操作被拦", (tool_text(ans, 4).get("error") or {}).get("code") == "READONLY_MODE")
    aa = tool_text(ans, 5)
    check("连接器 jst_actions 汇总 89 接口", aa.get("count") == 89 and aa.get("domains") == 12)

    print("== 6. 通用 MCP 包握手 ==")
    mreqs = [
        {"jsonrpc": "2.0", "id": 11, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "verify-mcp", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 12, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 13, "method": "tools/call", "params": {"name": "jst_check", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 14, "method": "tools/call", "params": {"name": "jst_query", "arguments": {"action": write_action, "params": "{}"}}},
        {"jsonrpc": "2.0", "id": 15, "method": "tools/call", "params": {"name": "jst_actions", "arguments": {}}},
    ]
    mans = handshake(mreqs, server=MCP_SERVER)
    check("MCP initialize 成功",
          ((mans.get(11) or {}).get("result") or {}).get("protocolVersion") == "2025-06-18")
    check("MCP serverInfo 名为 jst-query-mcp",
          (((mans.get(11) or {}).get("result") or {}).get("serverInfo") or {}).get("name") == "jst-query-mcp")
    mtools = [t["name"] for t in (((mans.get(12) or {}).get("result") or {}).get("tools") or [])]
    check("MCP tools/list 返回 7 个工具", len(mtools) == 7, mtools)
    check("MCP 体检返回 READY", tool_text(mans, 13).get("status") == "READY")
    check("MCP 写操作被拦", (tool_text(mans, 14).get("error") or {}).get("code") == "READONLY_MODE")
    maa = tool_text(mans, 15)
    check("MCP jst_actions 汇总 89 接口", maa.get("count") == 89 and maa.get("domains") == 12)

    print()
    print("通过 %d 项，失败 %d 项" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败：" + "、".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
