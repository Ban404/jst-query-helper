#!/usr/bin/env python3
"""把连接器定为唯一真源，同步 Node 内核与共用配置到另外两套包。

connector/ 里的 core.mjs、server.mjs、ask.mjs、guide.json、scenarios.json
是三套发行包的共同来源。本脚本：
  1. core.mjs → mcp/core.mjs（只改资源路径）
  2. server.mjs / ask.mjs → mcp/（只改工具名与版本）
  3. guide.json / scenarios.json → skill/scripts/ 和 mcp/（逐字复制）

这样"改提示语只改一处"才真的成立：改完 connector 里的配置跑一次即可，
不需要人肉同步三份。用法：python tools/sync_core.py
只用 Python 标准库。
"""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONN = os.path.join(ROOT, "connector")
MCP = os.path.join(ROOT, "mcp")
SKILL_SCRIPTS = os.path.join(ROOT, "skill", "scripts")
DATA = os.path.join(MCP, "data")

# 连接器里的内部目录是 jst/；通用 MCP 包用 data/ 放清单，根目录下不再套 jst/。
# rel 本身已是 scripts/bin/<平台>/...，所以包内路径直接用 here，
# 不能拼成 bin/scripts/bin/... 这种不存在的嵌套。
CORE_REPLACEMENTS = [
    ("path.join(here, 'jst', 'scripts', 'actions.json')", "path.join(here, 'data', 'actions.json')", True),
    ("path.join(here, 'jst', 'READONLY')", "path.join(here, 'data', 'READONLY')", True),
    ("path.join(here, 'jst', rel)", "path.join(here, rel)", True),
]
ENTRY_REPLACEMENTS = [
    ("name: 'jst-helper', version: '5.0.1'", "name: 'jst-query-mcp', version: '5.0.1'", False),
]


def convert(src_name, dst_name, replacements):
    with open(os.path.join(CONN, src_name), encoding="utf-8") as fh:
        text = fh.read()
    for old, new, required in replacements:
        if old not in text:
            if required:
                raise SystemExit("同步失败：%s 里找不到要替换的片段：%s" % (src_name, old))
            continue
        text = text.replace(old, new)
    with open(os.path.join(MCP, dst_name), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("生成 mcp/%s（源自 connector/%s）" % (dst_name, src_name))


def main():
    os.makedirs(DATA, exist_ok=True)
    convert("core.mjs", "core.mjs", CORE_REPLACEMENTS)
    convert("server.mjs", "server.mjs", ENTRY_REPLACEMENTS)
    convert("ask.mjs", "ask.mjs", ENTRY_REPLACEMENTS)

    # 引导文案、场景清单、字段字典、话术：connector 是唯一真源，另外两套逐字复制
    for name in ("guide.json", "scenarios.json"):
        for dst_dir in (MCP, SKILL_SCRIPTS):
            shutil.copyfile(os.path.join(CONN, name), os.path.join(dst_dir, name))
            print("同步 %s → %s" % (name, os.path.basename(os.path.dirname(dst_dir)) or "mcp"))

    # 接口清单与领域说明：三套共用 catalog/ 唯一真源，注入后 mcp/ 源码目录即自包含可运行
    catalog = os.path.join(ROOT, "catalog")
    shutil.copyfile(os.path.join(catalog, "actions.json"), os.path.join(DATA, "actions.json"))
    print("注入 data/actions.json")
    domains_dst = os.path.join(DATA, "domains")
    if os.path.isdir(domains_dst):
        shutil.rmtree(domains_dst)
    os.makedirs(domains_dst)
    domains_src = os.path.join(catalog, "domains")
    for fn in sorted(os.listdir(domains_src)):
        if fn.endswith(".md"):
            shutil.copyfile(os.path.join(domains_src, fn), os.path.join(domains_dst, fn))
    print("注入 data/domains/（12 份）")

    marker = os.path.join(DATA, "READONLY")
    if not os.path.exists(marker):
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("READ ONLY — 本包只允许已登记的 36 个查询接口，写操作一律拦截。\n")
    print("同步完成，mcp/ 与 skill/scripts/ 均已与 connector/ 对齐。")


if __name__ == "__main__":
    main()
