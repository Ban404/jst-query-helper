#!/usr/bin/env python3
"""把三套源码各自打包成可直接上架/发布的 zip。

- 技能包 → 通用 AI 助手技能
- 连接器包 → MCP 连接器
- 通用 MCP 包 → npm / 任意 MCP 客户端

三套共用 catalog/ 里的接口清单与领域说明，构建时注入各自目录，保证一致。
只读源码、只写 dist/。三套都是纯文本，不含任何二进制。
用法：python tools/build.py
"""
import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
SKILL_SRC = os.path.join(ROOT, "skill")
CONN_SRC = os.path.join(ROOT, "connector")
MCP_SRC = os.path.join(ROOT, "mcp")
CATALOG = os.path.join(ROOT, "catalog", "domains")
ACTIONS = os.path.join(ROOT, "catalog", "actions.json")

# (源目录, zip 文件名, zip 内根目录)
PACKS = [
    (SKILL_SRC, "聚水潭查询助手-技能包.zip", "justerp-query-helper"),
    (CONN_SRC, "聚水潭查询助手-连接器包.zip", "jst-helper"),
    (MCP_SRC, "聚水潭查询助手-MCP包.zip", "jst-query-mcp"),
]

FORBIDDEN = {"__pycache__", ".cache", ".tmp", ".DS_Store", "config.json", ".pytest_cache"}
BINARY_EXT = (".exe", ".dll", ".so", ".dylib", ".bin", ".db", ".pyc")


def empty_dir(p):
    if os.path.isdir(p):
        shutil.rmtree(p)
    os.makedirs(p, exist_ok=True)


def ignore(_dir, names):
    return [n for n in names if n in FORBIDDEN or n.endswith(".pyc")]


def inject_catalog(target, actions_rel, domains_rel):
    """把统一接口清单与 12 份领域说明注入目标包，保证三套逐字一致。"""
    shutil.copy2(ACTIONS, os.path.join(target, *actions_rel.split("/")))
    domains = os.path.join(target, *domains_rel.split("/"))
    empty_dir(domains)
    for fn in sorted(os.listdir(CATALOG)):
        if fn.endswith(".md"):
            shutil.copy2(os.path.join(CATALOG, fn), os.path.join(domains, fn))


def build_one(src, target):
    shutil.copytree(src, target, ignore=ignore)
    if os.path.basename(src) == "skill":
        inject_catalog(target, "scripts/actions.json", "references/domains")
    elif os.path.basename(src) == "connector":
        inject_catalog(target, "jst/scripts/actions.json", "jst/references/domains")
    else:  # mcp
        inject_catalog(target, "data/actions.json", "data/domains")


def assert_clean(base):
    for folder, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in FORBIDDEN]
        for fn in files:
            if fn in FORBIDDEN:
                raise SystemExit("包里混进了不该分发的文件：" + os.path.join(folder, fn))
            if fn.lower().endswith(BINARY_EXT):
                raise SystemExit("包里出现二进制：" + os.path.join(folder, fn))


def zip_dir(source, zip_path, root_name):
    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for folder, dirs, files in os.walk(source):
            dirs[:] = [d for d in dirs if d not in FORBIDDEN]
            for fn in files:
                if fn in FORBIDDEN:
                    continue
                full = os.path.join(folder, fn)
                arc = os.path.join(root_name, os.path.relpath(full, source)).replace("\\", "/")
                info = zipfile.ZipInfo(arc, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with open(full, "rb") as fh:
                    z.writestr(info, fh.read(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
                count += 1
    return count


def main():
    for need in (ACTIONS, CATALOG):
        if not os.path.exists(need):
            raise SystemExit("缺少接口清单或领域文档：" + need)
    # 打包前确保通用 MCP 包内核是从连接器同步过来的最新版本
    sync = os.path.join(ROOT, "tools", "sync_core.py")
    if os.path.exists(sync):
        import subprocess
        import sys
        r = subprocess.run([sys.executable, sync], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit("内核同步失败：" + (r.stderr or r.stdout))
        print(r.stdout.strip())

    empty_dir(DIST)
    built = []
    for src, zip_name, root_name in PACKS:
        target = os.path.join(DIST, root_name)
        build_one(src, target)
        assert_clean(target)
        n = zip_dir(target, os.path.join(DIST, zip_name), root_name)
        built.append((zip_name, n))

    label = ["技能包（套装①，主）", "连接器包（套装②）", "通用 MCP 包（套装③）"]
    for (zip_name, n), tag in zip(built, label):
        print("%s：%s  %.1f KB  %d 个文件" % (
            tag, zip_name, os.path.getsize(os.path.join(DIST, zip_name)) / 1024, n))
    print("三套都不含二进制；查询程序由水宝安装后自带。")


if __name__ == "__main__":
    main()
