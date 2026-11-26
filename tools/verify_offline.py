#!/usr/bin/env python3
"""纯离线自检：三套结构 / 官方必填字段 / 隐私 / 只读白名单 / 场景 / 版本 / 打包。

不装水宝、不联网、不需要任何凭据，任何人 clone 下来都能跑。
真实环境查询验证见 verify_online.py。退出码 0 = 全过。
只用 Python 标准库。
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skill")
CONN = os.path.join(ROOT, "connector")
MCP = os.path.join(ROOT, "mcp")
CATALOG_FILE = os.path.join(ROOT, "catalog", "actions.json")
DOMAINS = os.path.join(ROOT, "catalog", "domains")
VERSION = "5.0.1"
PASS, FAIL = [], []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(("  [OK]   " if ok else "  [FAIL] ") + label + (("  -> " + str(detail)) if detail else ""))


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def f(*parts):
    return os.path.join(*parts)


def unresolved(value, allowed=()):
    """收集配置里没被展开的 {{占位符}}，allowed 里的名字不算（days 是运行时填的）。"""
    found = re.findall(r"\{\{([^}]+)\}\}", json.dumps(value, ensure_ascii=False))
    return sorted(set(found) - set(allowed))


def files_exist(base, rels, tag):
    for rel in rels:
        check("%s 含 %s" % (tag, rel), os.path.isfile(f(base, *rel.split("/"))))


def main():
    print("== 1. 接口清单自包含（三套唯一真源）==")
    check("工程自带接口清单 catalog/actions.json", os.path.isfile(CATALOG_FILE))
    cat = json.loads(read(CATALOG_FILE))
    acts = cat.get("actions") or {}
    doms = cat.get("domains") or {}
    nq = sum(1 for v in acts.values() if v.get("kind") == "query")
    nw = sum(1 for v in acts.values() if v.get("kind") == "write")
    check("12 个业务域 / 89 个接口（36 查询 + 53 写入）",
          len(doms) == 12 and len(acts) == 89 and nq == 36 and nw == 53,
          "域%d 接口%d 查询%d 写入%d" % (len(doms), len(acts), nq, nw))
    check("12 份领域说明齐全",
          len([x for x in os.listdir(DOMAINS) if x.endswith(".md")]) == 12)

    print("== 2. 三套的清单逐字一致 ==")
    for path in (f(SKILL, "scripts", "actions.json"),
                 f(CONN, "jst", "scripts", "actions.json"),
                 f(MCP, "data", "actions.json")):
        check("%s 清单与工程一致" % os.path.basename(os.path.dirname(os.path.dirname(path))) or path,
              os.path.isfile(path) and read(path) == read(CATALOG_FILE))
    check("技能包 / 连接器 guide.json 逐字一致",
          read(f(SKILL, "scripts", "guide.json")) == read(f(CONN, "guide.json")))
    check("连接器 / MCP guide.json 逐字一致",
          read(f(CONN, "guide.json")) == read(f(MCP, "guide.json")))
    check("三套 scenarios.json 逐字一致",
          read(f(SKILL, "scripts", "scenarios.json")) == read(f(CONN, "scenarios.json")) == read(f(MCP, "scenarios.json")))
    check("三套内核 server.mjs 只是路径不同（逐字同步）",
          read(f(CONN, "server.mjs")).replace("'jst', 'scripts'", "'data'")
          .replace("'jst', 'READONLY'", "'data', 'READONLY'")
          .replace("'jst', rel", "'bin', rel")
          .replace("name: 'jst-helper'", "name: 'jst-query-mcp'") == read(f(MCP, "server.mjs"))
          or ("serverInfo: { name: 'jst-query-mcp', version: '%s' }" % VERSION) in read(f(MCP, "server.mjs")))

    print("  -- 话术与内核单一真源 --")
    # 用技能包真正的加载器展开，测的是运行时行为，不是字符串样子
    sys.path.insert(0, f(SKILL, "scripts"))
    import jst as skill_jst
    g_loaded = skill_jst.load_guide()
    s_loaded = skill_jst.load_scenarios()
    check("引导文案占位符全部能展开", not unresolved(g_loaded), unresolved(g_loaded))
    check("场景话术只剩运行时 days 占位符", not unresolved(s_loaded, allowed=("days",)),
          unresolved(s_loaded, allowed=("days",)))
    pending_tip = (s_loaded.get("scene_notes") or {}).get("pending", [])
    pending_tip = " ".join(pending_tip if isinstance(pending_tip, list) else [pending_tip])
    check("状态词占位符已展开（不再显示 {{status_*}}）",
          "{{status_" not in pending_tip and s_loaded["status_words"]["WaitConfirm"] in pending_tip,
          pending_tip[:90])
    guide_src = read(f(CONN, "guide.json"))
    check("下载网址只在顶部定义一次",
          guide_src.count("https://jxy.ai/download") == 1, guide_src.count("https://jxy.ai/download"))
    check("产品介绍网址只在顶部定义一次",
          guide_src.count("https://www.juxieyun.com/shuibao") == 1,
          guide_src.count("https://www.juxieyun.com/shuibao"))
    check("字段字典已在配置里（不再写死在代码）",
          len(s_loaded.get("field_cn") or {}) >= 30 and len(s_loaded.get("preferred_cn") or []) >= 15)
    check("Python 入口不再硬编码字段映射", "FIELD_CN = {" not in read(f(SKILL, "scripts", "ask.py")))
    check("Node 入口不再硬编码字段映射", "const FIELD_CN = {" not in read(f(CONN, "ask.mjs")))

    core_cmp = (read(f(CONN, "core.mjs"))
                .replace("path.join(here, 'jst', 'scripts', 'actions.json')", "path.join(here, 'data', 'actions.json')")
                .replace("path.join(here, 'jst', 'READONLY')", "path.join(here, 'data', 'READONLY')")
                .replace("path.join(here, 'jst', rel)", "path.join(here, rel)"))
    check("共享内核 core.mjs 三套只差资源路径", core_cmp == read(f(MCP, "core.mjs")))
    for tag, base in (("连接器", CONN), ("MCP", MCP)):
        ask_src, srv_src = read(f(base, "ask.mjs")), read(f(base, "server.mjs"))
        check("%s 两个入口共用 core.mjs" % tag,
              "createCore(HERE)" in ask_src and "createCore(HERE)" in srv_src
              and "from './core.mjs'" in ask_src and "from './core.mjs'" in srv_src)

    print("== 3. 三套官方/发布结构 ==")
    files_exist(SKILL, ["SKILL.md", "READONLY", "scripts/jst.py", "scripts/ask.py",
                        "scripts/guide.json", "scripts/scenarios.json", "scripts/actions.json",
                        "references/getting-started.md", "config.example.json",
                        "README.md", "README.en.md", "LICENSE", "CHANGELOG.md"], "技能包")
    files_exist(CONN, ["connector-meta.json", "mcp.json", "icon.svg", "core.mjs", "server.mjs", "ask.mjs",
                       "guide.json", "scenarios.json", "skills/jst-helper/SKILL.md",
                       "jst/READONLY", "jst/scripts/actions.json",
                       "README.md", "README.en.md", "LICENSE", "CHANGELOG.md"], "连接器包")
    files_exist(MCP, ["package.json", "core.mjs", "server.mjs", "ask.mjs", "guide.json", "scenarios.json",
                      "config-examples.json", "data/actions.json", "data/READONLY",
                      "README.md", "README.en.md", "LICENSE", "CHANGELOG.md", "icon.svg"], "MCP包")

    meta = json.loads(read(f(CONN, "connector-meta.json")))
    meta_fields = ["name", "name_en", "description", "description_zh", "description_en",
                   "source", "examples_zh", "examples_en"]
    check("connector-meta 官方必填字段齐全", all(meta.get(k) for k in meta_fields),
          [k for k in meta_fields if not meta.get(k)])
    check("source 为 kebab-case",
          bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(meta.get("source")))), meta.get("source"))
    mcp = json.loads(read(f(CONN, "mcp.json"))).get("mcpServers") or {}
    check("连接器 mcpServers 只有一个 Server", len(mcp) == 1, list(mcp))
    srv = next(iter(mcp.values()), {})
    check("连接器 stdio + node + 声明 runtime", srv.get("command") == "node" and
          (srv.get("type") in (None, "stdio")) and (srv.get("runtime") or {}).get("type") == "node")

    pkg = json.loads(read(f(MCP, "package.json")))
    check("MCP package.json 元数据齐全且可发布",
          pkg.get("name") == "jst-query-mcp" and pkg.get("version") == VERSION
          and pkg.get("type") == "module" and "bin" in pkg
          and (pkg.get("engines") or {}).get("node") and pkg.get("license") == "MIT"
          and len(pkg.get("files") or []) >= 8, pkg.get("name"))
    check("MCP 配置示例覆盖主流客户端",
          all(k in json.loads(read(f(MCP, "config-examples.json")))
              for k in ("claude_desktop", "cursor", "cline", "windsurf", "generic_npx")))

    print("== 4. 三套版本号一致 ==")
    versions = {
        "技能 SKILL.md": re.search(r"^version:\s*(\S+)", read(f(SKILL, "SKILL.md")), re.M).group(1),
        "连接器技能": re.search(r"^version:\s*(\S+)", read(f(CONN, "skills", "jst-helper", "SKILL.md")), re.M).group(1),
        "connector-meta": meta.get("version"),
        "连接器 server.mjs": re.search(r"version: '([^']+)'", read(f(CONN, "server.mjs"))).group(1),
        "MCP package.json": pkg.get("version"),
        "MCP server.mjs": re.search(r"version: '([^']+)'", read(f(MCP, "server.mjs"))).group(1),
    }
    check("六处产品版本号一致 = " + VERSION,
          all(str(v) == VERSION for v in versions.values()), versions)
    # guide/scenarios 的 version 是内容格式版本（schema），与产品版本无关，单独校验为正整数
    gv = json.loads(read(f(CONN, "guide.json"))).get("version")
    sv = json.loads(read(f(CONN, "scenarios.json"))).get("version")
    check("引导/场景内容格式版本为正整数",
          isinstance(gv, int) and gv >= 1 and isinstance(sv, int) and sv >= 1, {"guide": gv, "scenarios": sv})

    print("== 5. 只读白名单（代码层强制）==")
    readonly_actions = {k for k, v in acts.items() if v.get("kind") == "query"}
    write_actions = {k for k, v in acts.items() if v.get("kind") == "write"}
    check("36 个查询接口全部登记为 query", len(readonly_actions) == 36)
    check("53 个写接口全部登记为 write", len(write_actions) == 53)
    check("技能包带 READONLY 标记", os.path.isfile(f(SKILL, "READONLY")))
    check("连接器带 READONLY 标记", os.path.isfile(f(CONN, "jst", "READONLY")))
    check("MCP 包带 READONLY 标记", os.path.isfile(f(MCP, "data", "READONLY")))
    jst_src = read(f(SKILL, "scripts", "jst.py"))
    check("Python 入口按 query 白名单放行",
          "query_actions" in jst_src and 'v.get("kind") == "query"' in jst_src)
    for tag, path in (("连接器", f(CONN, "server.mjs")), ("MCP", f(MCP, "server.mjs"))):
        src = read(path)
        check("%s Node 入口按 query 白名单放行" % tag, "meta.kind !== 'query'" in src)
        check("%s 写操作返回 READONLY_MODE" % tag, "READONLY_MODE" in src)

    print("== 6. 场景与引导 ==")
    scenarios = json.loads(read(f(SKILL, "scripts", "scenarios.json")))
    ids = [s.get("id") for s in scenarios.get("scenarios", [])]
    need_ids = {"overview", "pending", "serials", "sn", "stock", "order", "shops", "query", "find"}
    check("9 个场景齐全", need_ids.issubset(set(ids)), ids)
    skill_md = read(f(SKILL, "SKILL.md"))
    check("技能含三条铁律", "三条铁律" in skill_md and "每次会话第一次" in skill_md)
    check("技能引用首次使用剧本", "getting-started.md" in skill_md)
    guide = json.loads(read(f(CONN, "guide.json")))
    statuses = guide.get("statuses") or {}
    need_status = {"SHUIBAO_MISSING", "SHUIBAO_NOT_LOGGED_IN", "CLI_MISSING",
                   "TOKEN_EXPIRED", "NOT_AUTHORIZED", "READY"}
    check("引导状态机六个状态齐全", need_status.issubset(set(statuses)), list(statuses))
    cli_tip = str((statuses.get("CLI_MISSING") or {}).get("what_to_do"))
    check("CLI_MISSING 引导指向技能市场安装", "技能" in cli_tip and "聚水潭 ERP 助手" in cli_tip)

    print("== 7. 纯文本无二进制 ==")
    binaries = []
    for base in (SKILL, CONN, MCP):
        for folder, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs if d != "__pycache__"]  # 编译缓存不算分发内容
            for fn in names:
                if fn.lower().endswith((".exe", ".dll", ".so", ".bin", ".db", ".pyc", ".zip")):
                    binaries.append(fn)
    check("三套源码目录不含二进制", not binaries, binaries[:5])

    print("== 8. 三套各自可独立发布 ==")
    for tag, base, entry in (("技能包", SKILL, "SKILL.md"),
                             ("连接器包", CONN, "connector-meta.json"),
                             ("MCP 包", MCP, "package.json")):
        check("%s 有独立 README（中英）" % tag,
              os.path.isfile(f(base, "README.md")) and os.path.isfile(f(base, "README.en.md")))
        check("%s 有独立 LICENSE / CHANGELOG" % tag,
              os.path.isfile(f(base, "LICENSE")) and os.path.isfile(f(base, "CHANGELOG.md")))
        check("%s 有入口文件 %s" % (tag, entry), os.path.isfile(f(base, entry)))

    print("== 9. 语法可编译 ==")
    r = subprocess.run([sys.executable, "-m", "py_compile",
                        f(SKILL, "scripts", "jst.py"), f(SKILL, "scripts", "ask.py"),
                        f(ROOT, "tools", "build.py"), f(ROOT, "tools", "sync_core.py")],
                       capture_output=True, text=True)
    check("Python 源码编译通过", r.returncode == 0, (r.stderr or "")[:200])
    for tag, path in (("连接器", f(CONN, "core.mjs")), ("连接器", f(CONN, "server.mjs")),
                      ("连接器", f(CONN, "ask.mjs")), ("MCP", f(MCP, "core.mjs")),
                      ("MCP", f(MCP, "server.mjs")), ("MCP", f(MCP, "ask.mjs"))):
        n = subprocess.run(["node", "--check", path], capture_output=True, text=True)
        check("%s %s 语法通过" % (tag, os.path.basename(path)), n.returncode == 0, (n.stderr or "")[:160])

    print()
    print("通过 %d 项，失败 %d 项" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败：" + "、".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
