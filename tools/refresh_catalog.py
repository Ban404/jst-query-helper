#!/usr/bin/env python3
"""上游客户端升级后，一键重新识别接口清单与领域说明。

只读上游文件，不改动任何上游程序。做两件事：
  1. 从水宝自带查询程序按业务域重新读出全部接口 → catalog/actions.json
  2. 把上游的领域说明复制到 catalog/domains/

用法：python tools/refresh_catalog.py
"""
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog")
ACTIONS = os.path.join(CATALOG, "actions.json")
DOMAINS = os.path.join(CATALOG, "domains")


def shuibao_home():
    appdata = os.environ.get("APPDATA")
    if appdata:
        p = os.path.join(appdata, "jstclient")
        if os.path.isdir(p):
            return p
    for p in (os.path.expanduser("~/Library/Application Support/jstclient"),
              os.path.expanduser("~/.config/jstclient")):
        if os.path.isdir(p):
            return p
    return None


def cli_path(home):
    system, machine = platform.system(), platform.machine()
    if system == "Windows":
        rel = "windows-amd64/jst-open-platform.exe"
    elif system == "Darwin":
        rel = ("darwin-arm64/" if machine == "arm64" else "darwin-amd64/") + "jst-open-platform"
    else:
        rel = "linux-amd64/jst-open-platform"
    return os.path.join(home, "data", "agent", "skills", "jst-open-platform",
                        "scripts", "bin", *rel.split("/"))


def _looks_like_jwt(text):
    """和 jst.py 的 normalize_token 同一判定：能拆出合法的 JSON header 才算 JWT。

    不能只看 'eyJ' 前缀——不同 alg/编码的 JWT header 未必这么开头，
    那样会把有效 token 反转成废串，导致刷新失败。
    """
    try:
        head = text.split(".")[0]
        import base64 as _b64
        obj = json.loads(_b64.urlsafe_b64decode(head + "=" * (-len(head) % 4)))
        return isinstance(obj, dict) and ("alg" in obj or "typ" in obj)
    except Exception:
        return False


def token_env(home):
    env = dict(os.environ)
    if not env.get("JXY_TOKEN"):
        cfg = os.path.join(home, "configs", "user_config.json")
        raw = json.load(open(cfg, encoding="utf-8")).get("token", "").strip()
        # 上游把 JWT 整体倒序落盘；翻转前后都按 JSON header 校验，取合法的那个
        token = raw if _looks_like_jwt(raw) else (raw[::-1] if _looks_like_jwt(raw[::-1]) else raw)
        env["JXY_TOKEN"] = token
    return env


def call(exe, env, argv):
    proc = subprocess.run([exe] + argv + ["--json"], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
    try:
        return json.loads((proc.stdout or "").strip())
    except Exception:
        raise SystemExit("查询程序返回异常：%s %s" % (argv, (proc.stdout or proc.stderr)[:300]))


def main():
    home = shuibao_home()
    if not home:
        raise SystemExit("没找到水宝数据目录：请先安装并登录一次水宝。")
    exe = cli_path(home)
    if not os.path.isfile(exe):
        raise SystemExit("没找到查询程序，请确认「聚水潭 ERP 助手」技能已装好：%s" % exe)
    env = token_env(home)

    dom = call(exe, env, ["list_domains"])
    if not dom.get("ok"):
        raise SystemExit("读业务域失败：%s" % dom.get("error"))
    names = [x["domain"] for x in dom["data"]]

    actions, per_domain = {}, {}
    for name in names:
        res = call(exe, env, ["list_actions", "--domain", name])
        if not res.get("ok"):
            raise SystemExit("读「%s」接口失败：%s" % (name, res.get("error")))
        rows = res.get("data") or []
        per_domain[name] = len(rows)
        for row in rows:
            actions[row["action"]] = {
                "kind": row.get("kind", ""),
                "name": row.get("name", ""),
                "domain": name,
            }

    os.makedirs(DOMAINS, exist_ok=True)
    src_domains = os.path.join(home, "data", "agent", "skills", "jst-open-platform", "references", "domains")
    copied = 0
    if os.path.isdir(src_domains):
        for fn in sorted(os.listdir(src_domains)):
            if fn.endswith(".md"):
                shutil.copy2(os.path.join(src_domains, fn), os.path.join(DOMAINS, fn))
                copied += 1

    old = {}
    if os.path.isfile(ACTIONS):
        try:
            old = json.load(open(ACTIONS, encoding="utf-8")).get("actions") or {}
        except Exception:
            pass

    payload = {
        "generated_for": "JST Query Helper (from upstream client bundled CLI)",
        "refreshed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cli": os.path.basename(exe),
        "domains": per_domain,
        "note": "kind=write 的接口在只读模式下被拦截；本文件由 refresh_catalog.py 重新识别生成",
        "actions": dict(sorted(actions.items())),
    }
    os.makedirs(CATALOG, exist_ok=True)
    with open(ACTIONS, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    added = sorted(set(actions) - set(old))
    removed = sorted(set(old) - set(actions))
    changed = sorted(k for k in set(old) & set(actions) if old[k] != actions[k])
    print("业务域 %d 个，接口 %d 个（查询 %d / 写入 %d）" % (
        len(names), len(actions),
        sum(1 for v in actions.values() if v["kind"] == "query"),
        sum(1 for v in actions.values() if v["kind"] == "write")))
    print("领域说明复制 %d 份" % copied)
    print("与上一版对比：新增 %d，移除 %d，字段变化 %d" % (len(added), len(removed), len(changed)))
    for label, items in (("新增", added), ("移除", removed), ("变化", changed)):
        if items:
            print("  %s：%s" % (label, "、".join(items[:12])))
    print("已写入 %s；改完记得跑 python tools/build.py 重建包。" % ACTIONS)


if __name__ == "__main__":
    main()
