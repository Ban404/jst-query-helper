#!/usr/bin/env python3
"""把连接器的 Node 内核同步到通用 MCP 包，保证两套逻辑逐字一致。

连接器包（MCP 连接器）与通用 MCP 包（任意 MCP 客户端）共用同一份
查询内核。这里从 connector/ 读取 server.mjs 与 ask.mjs，只改三处资源路径，
再复制引导文案与场景清单到 mcp/。改动内核后跑一次本脚本即可，避免两套漂移。

只读 connector/，只写 mcp/ 的生成文件。用法：python tools/sync_core.py
只用 Python 标准库。
"""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONN = os.path.join(ROOT, "connector")
MCP = os.path.join(ROOT, "mcp")
DATA = os.path.join(MCP, "data")

# 连接器里的内部目录是 jst/；通用 MCP 包用 data/ 放清单、bin/ 放可选查询程序。
# required=True 的片段必须命中，缺了说明内核结构变了，同步要人工确认；可选片段有则改。
REPLACEMENTS = [
    ("path.join(HERE, 'jst', 'scripts', 'actions.json')", "path.join(HERE, 'data', 'actions.json')", True),
    ("path.join(HERE, 'jst', 'READONLY')", "path.join(HERE, 'data', 'READONLY')", True),
    ("path.join(HERE, 'jst', rel)", "path.join(HERE, 'bin', rel)", True),
    ("name: 'jst-helper', version: '5.0.0'", "name: 'jst-query-mcp', version: '5.0.0'", False),
]


def convert(src_name, dst_name):
    with open(os.path.join(CONN, src_name), encoding="utf-8") as fh:
        text = fh.read()
    for old, new, required in REPLACEMENTS:
        if old not in text:
            if required:
                raise SystemExit("同步失败：%s 里找不到要替换的片段：%s" % (src_name, old))
            continue
        text = text.replace(old, new)
    with open(os.path.join(MCP, dst_name), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("生成 %s（源自 connector/%s）" % (dst_name, src_name))


def main():
    os.makedirs(DATA, exist_ok=True)
    convert("server.mjs", "server.mjs")
    convert("ask.mjs", "ask.mjs")
    for name in ("guide.json", "scenarios.json"):
        shutil.copyfile(os.path.join(CONN, name), os.path.join(MCP, name))
        print("复制 %s" % name)

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
    print("MCP 内核同步完成，mcp/ 目录已自包含。")


if __name__ == "__main__":
    main()
