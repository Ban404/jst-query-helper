#!/usr/bin/env python3
"""聚水潭查询助手 · 底层查询入口（技能包自带）。

AI 平时用 ask.py（一句命令拿到大白话答案）；这个脚本负责打底：
  1. 体检：水宝装了吗、登录了吗、授权了吗，还差哪一步
  2. 找登录凭据和查询程序（都由水宝提供，本包不带任何二进制）
  3. 查数据：自动补接口版本号、自动翻页、自动按 7 天分段、只读白名单

只用 Python 标准库。多数 AI 助手自带 Python；没有的话装一个 Python 3.8+ 即可。
"""

import base64
import datetime
import glob
import json
import os
import platform
import subprocess
import sys
import tempfile

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE_PATH = os.path.join(SKILL_DIR, "scripts", "guide.json")
ACTIONS_PATH = os.path.join(SKILL_DIR, "scripts", "actions.json")
READONLY_FLAG = os.path.join(SKILL_DIR, "READONLY")
CONFIG_PATH = os.path.join(SKILL_DIR, "config.json")

# 缓存放系统临时目录，不写技能包目录：技能市场装下来的目录可能是只读的。
CACHE_PATH = os.path.join(tempfile.gettempdir(), "jst-query-helper", "schema_revisions.json")


def load_guide():
    try:
        with open(GUIDE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"statuses": {}, "checks": [], "setup_steps": [], "facts": [], "errors": {}}


# --------------------------------------------------------------- 水宝的位置


def shuibao_homes():
    """水宝在不同系统上存放数据的目录：(数据根, 登录文件, 自带技能根)。"""
    candidates = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(os.path.join(appdata, "jstclient"))
    candidates.append(os.path.expanduser("~/Library/Application Support/jstclient"))
    candidates.append(os.path.expanduser("~/.config/jstclient"))
    return [
        (home,
         os.path.join(home, "configs", "user_config.json"),
         os.path.join(home, "data", "agent", "skills", "jst-open-platform"))
        for home in candidates
    ]


def cli_filename():
    system, machine = platform.system(), platform.machine()
    if system == "Windows":
        return os.path.join("windows-amd64", "jst-open-platform.exe")
    if system == "Darwin":
        folder = "darwin-arm64" if machine == "arm64" else "darwin-amd64"
        return os.path.join(folder, "jst-open-platform")
    return os.path.join("linux-amd64", "jst-open-platform")


def find_cli():
    """按优先级找查询程序。本技能包不带二进制，靠水宝安装后自带的那个。"""
    rel = os.path.join("scripts", "bin", cli_filename())

    fixed = os.environ.get("JST_CLI_PATH")                      # 1. 管理员显式指定
    if fixed and os.path.isfile(fixed):
        return fixed

    own = os.path.join(SKILL_DIR, rel)                          # 2. 包内自带（内部包兜底）
    if os.path.isfile(own):
        return own

    for _, _, skill_root in shuibao_homes():                    # 3. 水宝自带的技能目录
        p = os.path.join(skill_root, rel)
        if os.path.isfile(p):
            return p

    old = os.path.expanduser("~/.workbuddy/skills/jst-open-platform/" + rel.replace(os.sep, "/"))
    if os.path.isfile(old):                                     # 4. 以前装过的同名技能
        return old

    name = os.path.basename(cli_filename())                     # 5. 水宝换了目录结构就搜一遍
    for home, _, _ in shuibao_homes():
        base = os.path.join(home, "data", "agent", "skills")
        if os.path.isdir(base):
            hits = glob.glob(os.path.join(base, "**", name), recursive=True)
            if hits:
                return hits[0]
    return None


# ---------------------------------------------------------------- token 处理


def _jwt_looks_valid(token):
    parts = token.split(".")
    if len(parts) != 3:
        return False
    head = parts[0] + "=" * (-len(parts[0]) % 4)
    try:
        json.loads(base64.urlsafe_b64decode(head).decode("utf-8"))
        return True
    except Exception:
        return False


def normalize_token(raw):
    """水宝把 JWT 整体倒序后落盘；自动识别并翻正。"""
    if not raw:
        return None
    raw = raw.strip()
    if _jwt_looks_valid(raw):
        return raw
    flipped = raw[::-1]
    return flipped if _jwt_looks_valid(flipped) else raw


def decode_claims(token):
    try:
        p = token.split(".")[1] + "=" * (-len(token.split(".")[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(p).decode("utf-8"))
    except Exception:
        return {}


def resolve_token():
    """环境变量 > 本包 config.json > 水宝登录文件。返回 (token, 来源)。"""
    env = normalize_token(os.environ.get("JXY_TOKEN"))
    if env:
        return env, "环境变量 JXY_TOKEN"
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as fh:
                data = json.load(fh)
            t = normalize_token(data.get("jxy_token") or data.get("token"))
            if t:
                return t, CONFIG_PATH
        except Exception:
            pass
    for _, cfg, _ in shuibao_homes():
        if not os.path.isfile(cfg):
            continue
        try:
            with open(cfg, encoding="utf-8") as fh:
                t = normalize_token(json.load(fh).get("token"))
            if t:
                return t, cfg
        except Exception:
            continue
    return None, None


def build_env():
    env = dict(os.environ)
    token, _ = resolve_token()
    if token:
        env["JXY_TOKEN"] = token
    return env


# ------------------------------------------------------------------ 查询程序


def run_cli(argv):
    """调一次查询程序，返回它给出的 JSON。"""
    exe = find_cli()
    if not exe:
        return {"ok": False, "error": {"code": "CLI_MISSING", "message": "查询程序未就绪"}}
    try:
        proc = subprocess.run(
            [exe] + list(argv) + ["--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=build_env(), timeout=90,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": {"code": "TIMEOUT", "message": "查询超时，稍后再试"}}
    except Exception as exc:
        return {"ok": False, "error": {"code": "CLI_ERROR", "message": str(exc)[:200]}}
    out = (proc.stdout or "").strip()
    if not out:
        return {"ok": False, "error": {"code": "NO_OUTPUT", "message": (proc.stderr or "").strip()[:300]}}
    try:
        return json.loads(out)
    except Exception:
        return {"ok": False, "raw_output": out[:2000]}


def passthrough(argv):
    """原样转发（给 list_domains / describe_action 这类顶层命令用）。"""
    exe = find_cli()
    if not exe:
        print(json.dumps({"ok": False, "error": {"code": "CLI_MISSING"}}, ensure_ascii=False))
        return 2
    args = list(argv)
    if "--json" not in args:
        args.append("--json")
    return subprocess.run([exe] + args, env=build_env()).returncode


def list_all_actions():
    """不指定业务域时，按域逐个读再合并。

    水宝 2.0.611181 起，查询程序的 list_actions 必须带 --domain，
    不带会报 DOMAIN_REQUIRED；更早的版本可以直接返回全部。
    统一走「先取域、再逐域取接口」，新旧两版都能得到同样的 89 条。
    """
    dom = run_cli(["list_domains"])
    if not dom.get("ok"):
        return dom
    names = [x.get("domain") for x in (dom.get("data") or [])
             if isinstance(x, dict) and x.get("domain")]
    rows = []
    for name in names:
        res = run_cli(["list_actions", "--domain", name])
        if not res.get("ok"):
            return res
        for item in res.get("data") or []:
            if isinstance(item, dict):
                item = dict(item)
                item.setdefault("domain", name)
                rows.append(item)
    return {"ok": True, "data": rows, "count": len(rows), "domains": len(names)}


# --------------------------------------------------------------- 体检与引导


def cmd_setup():
    """完整的新手清单，不联网。"""
    g = load_guide()
    return {
        "product": g.get("product"),
        "download": g.get("shuibao_download"),
        "intro": g.get("shuibao_intro"),
        "need_you_in_person": "安装水宝、登录、点一次授权，共 3 步，其余由 AI 自动完成",
        "steps": g.get("setup_steps"),
        "facts": g.get("facts"),
        "how_to_check": "python <技能目录>/scripts/jst.py doctor",
    }


def local_state():
    """只查本机、不联网的四项体检。给每次查询做放行判断用，快且不会因为网络抖动误伤。"""
    installed = any(os.path.isdir(home) for home, _, _ in shuibao_homes())
    if not installed:
        return False, "SHUIBAO_MISSING"
    token, _ = resolve_token()
    if not token:
        return False, "SHUIBAO_NOT_LOGGED_IN"
    if not find_cli():
        return False, "CLI_MISSING"
    exp = decode_claims(token).get("exp")
    if isinstance(exp, (int, float)) and exp <= datetime.datetime.now().timestamp():
        return False, "TOKEN_EXPIRED"
    return True, "READY"


def cmd_doctor(online=True):
    """按顺序体检 5 项，停在第一项没过的，给可以直接念给用户听的话。

    online=False 时跳过第 5 项联网检查，用于日常查询的快速放行。
    """
    g = load_guide()
    statuses = g.get("statuses", {})
    names = g.get("checks", [])
    checks = []

    def add(step, ok, detail):
        checks.append({"step": step,
                       "name": names[step - 1] if step <= len(names) else "",
                       "ok": ok, "detail": detail})

    def finish(status, extra=None):
        s = statuses.get(status, {})
        out = {
            "ok": status == "READY", "status": status,
            "stage": s.get("stage", 0), "title": s.get("title", ""),
            "what_happened": s.get("what_happened", ""),
            "what_to_do": s.get("what_to_do", ""),
            "who": s.get("who", ""), "url": s.get("url", ""),
            "success_check": s.get("success_check", ""),
            "can_ai_do": s.get("can_ai_do", False),
            "checks": checks, "readonly": is_readonly(),
        }
        out.update(extra or {})
        return out

    installed = any(os.path.isdir(home) for home, _, _ in shuibao_homes())
    add(1, installed, "已安装" if installed else "没找到水宝的数据目录")
    if not installed:
        return finish("SHUIBAO_MISSING")

    token, source = resolve_token()
    from_water = bool(token and "jstclient" in str(source))
    add(2, bool(token), "已登录（水宝凭据）" if from_water else ("已登录（手动配置）" if token else "还没登录过"))
    if not token:
        return finish("SHUIBAO_NOT_LOGGED_IN")

    exe = find_cli()
    add(3, bool(exe), "水宝自带，可用" if exe else "还没释放到本机")
    if not exe:
        return finish("CLI_MISSING")

    claims = decode_claims(token)
    exp = claims.get("exp")
    expired = isinstance(exp, (int, float)) and exp <= datetime.datetime.now().timestamp()
    expire_text = (datetime.datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M")
                   if isinstance(exp, (int, float)) else "未知")
    add(4, not expired, "有效至 " + expire_text if not expired else "已于 " + expire_text + " 过期")
    account = {"company": claims.get("co_name", ""), "user": claims.get("u_name", "")}
    common = {"account": account, "token_expires_at": expire_text}
    if expired:
        return finish("TOKEN_EXPIRED", common)

    if not online:
        add(5, True, "本地检查通过，授权状态由查询时确认")
        return finish("READY", dict(common, fast_check=True))

    probe = run_cli(["list_connections"])
    code = (probe.get("error") or {}).get("code") or ""
    if not probe.get("ok") and code != "AUTH_REQUIRED":
        add(5, False, "连接失败：" + (code or "未知原因"))
        return finish("TOKEN_REJECTED", dict(common, detail=code))
    ok = bool(probe.get("ok"))
    add(5, ok, "已授权" if ok else "未完成授权")
    if not ok:
        return finish("NOT_AUTHORIZED",
                      dict(common, authorize_url=(probe.get("data") or {}).get("authorize_url", "")))
    return finish("READY", dict(common, authorize_url=""))


def guide_for_status(status):
    """把某个状态翻成可以直接讲给用户听的一段话。"""
    state = cmd_doctor(online=True)
    if state.get("status") == status:
        return state
    s = load_guide().get("statuses", {}).get(status, {})
    return {
        "ok": False, "status": status, "stage": s.get("stage", 0),
        "title": s.get("title", ""), "what_happened": s.get("what_happened", ""),
        "what_to_do": s.get("what_to_do", ""), "who": s.get("who", ""),
        "url": s.get("url", ""), "success_check": s.get("success_check", ""),
    }


# ---------------------------------------------------------------- 只读与预检


def is_readonly():
    return os.environ.get("JST_ALLOW_WRITE") != "1" and os.path.isfile(READONLY_FLAG)


def all_actions():
    try:
        with open(ACTIONS_PATH, encoding="utf-8") as fh:
            return json.load(fh).get("actions") or {}
    except Exception:
        return {}


def query_actions():
    """只读白名单：只有明确登记为查询的接口才放行。"""
    return {k for k, v in all_actions().items() if v.get("kind") == "query"}


def arg_value(args, name):
    for i, a in enumerate(args):
        if a == name and i + 1 < len(args):
            return args[i + 1]
        if a.startswith(name + "="):
            return a[len(name) + 1:]
    return None


def load_cache():
    try:
        with open(CACHE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_cache(cache):
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def fetch_revision(action):
    data = run_cli(["describe_action", "--action", action]).get("data") or {}
    return data.get("schema_revision") or (data.get("schema_contract") or {}).get("schema_revision")


def denied(action):
    """写操作、或没登记过的接口，一律挡下。"""
    meta = all_actions().get(action)
    if meta and meta.get("kind") == "write":
        code, message = "READONLY_MODE", "「%s」会修改 ERP 数据，只读版已拦下。" % (meta.get("name") or action)
    else:
        code, message = "ACTION_NOT_ALLOWED", "「%s」不是允许查询的接口。" % action
    return {
        "ok": False,
        "error": {
            "code": code, "message": message,
            "what_to_do": load_guide().get("errors", {}).get(code, "换个查询类的说法，或让我列出能查的内容。"),
        },
    }


def invoke(argv):
    """执行一次查询，自动补接口版本号；版本号过期会刷新并重试一次。返回 dict。"""
    action = arg_value(argv, "--action")
    if not action:
        return {"ok": False, "error": {"code": "ACTION_REQUIRED", "message": "缺少 --action"}}

    if is_readonly() and action not in query_actions():
        return denied(action)

    cache = load_cache()
    if arg_value(argv, "--schema_revision"):
        return run_cli(argv)

    rev = cache.get(action) or fetch_revision(action)
    if not rev:
        return run_cli(argv)

    res = run_cli(list(argv) + ["--schema_revision", rev])
    code = (res.get("error") or {}).get("code") or ""
    if code in ("SCHEMA_PREFLIGHT_REQUIRED", "SCHEMA_REVISION_MISMATCH"):
        fresh = fetch_revision(action)
        if fresh and fresh != rev:
            res = run_cli(list(argv) + ["--schema_revision", fresh])
            if res.get("ok"):
                rev = fresh

    if res.get("ok") and cache.get(action) != rev:
        cache[action] = rev
        save_cache(cache)
    return res


def query(action, params):
    """给 ask.py 用的简版入口：不用拼命令行字符串，中文参数也不会被 shell 改写。"""
    return invoke(["invoke", "--action", action,
                   "--params", json.dumps(params or {}, ensure_ascii=False)])


# ------------------------------------------------- 通用：取数据、翻页、分段


def rows_of(result):
    """把一次查询的结果摊平成 (列表, 分页信息)。

    数据少时在 data 里；数据多时查询程序会写文件，只给 raw_data_path。
    两种情况都要认，否则会出现「明明有数据却说 0 条」。
    """
    if not isinstance(result, dict) or not result.get("ok"):
        return [], {}

    blob = result.get("data")
    if not isinstance(blob, dict):
        path = result.get("raw_data_path")
        if path and os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    blob = json.load(fh)
            except Exception:
                return [], {}

    if not isinstance(blob, dict):
        return [], {}

    preferred = ("orders", "datas", "inventorys", "items", "skus", "refunds", "list", "rows")
    rows = []
    for key in preferred:
        if isinstance(blob.get(key), list):
            rows = blob[key]
            break
    if not rows:
        for value in blob.values():
            if isinstance(value, list) and (not value or isinstance(value[0], dict)):
                rows = value
                break

    meta = {k: blob.get(k) for k in ("has_next", "page_count", "page_index", "page_size", "data_count")
            if k in blob}
    return rows, meta


def paged(action, params, page_size=50, max_pages=20):
    """自动翻页，把多页结果合成一个列表。"""
    out, pages = [], 0
    base = dict(params or {})
    base.setdefault("page_size", page_size)
    index = 1
    while pages < max_pages:
        call_params = dict(base, page_index=index)
        res = query(action, call_params)
        if not res.get("ok"):
            return out, res
        rows, meta = rows_of(res)
        out.extend(rows)
        pages += 1
        if meta.get("has_next") is False or len(rows) < page_size:
            break
        if meta.get("page_count") and index >= meta["page_count"]:
            break
        index += 1
    return out, {"ok": True, "pages": pages}


def time_windows(days=7, span=7):
    """接口一次最多查 7 天，往前推 days 天就切成几段。返回 [(开始, 结束), ...]。"""
    now = datetime.datetime.now()
    start = now - datetime.timedelta(days=days)
    fmt = "%Y-%m-%d %H:%M:%S"
    windows = []
    cur = start
    while cur < now:
        end = min(cur + datetime.timedelta(days=span) - datetime.timedelta(seconds=1), now)
        windows.append((cur.strftime(fmt), end.strftime(fmt)))
        cur = end + datetime.timedelta(seconds=1)
    return windows


def segmented(action, params, days=7, page_size=50):
    """按 7 天一段连续查，并对每段自动翻页。返回 (合并后的行, 出错信息或 None)。
    传了 so_ids / o_ids / io_ids / sku_ids 等精确条件时不需要分段。
    """
    exact = any(k in (params or {}) for k in ("so_ids", "o_ids", "io_ids", "sku_ids", "i_ids"))
    out = []
    if exact:
        rows, res = paged(action, params, page_size=page_size)
        out.extend(rows)
        if isinstance(res, dict) and not res.get("ok"):
            return out, res
        return out, None

    for begin, end in time_windows(days):
        seg = dict(params or {}, modified_begin=begin, modified_end=end)
        rows, res = paged(action, seg, page_size=page_size)
        out.extend(rows)
        if isinstance(res, dict) and not res.get("ok"):
            return out, res
    return out, None


# -------------------------------------------------------------------- 命令行


def main():
    args = sys.argv[1:]
    if not args:
        print(json.dumps({
            "usage": "python scripts/jst.py <命令>；日常查数据请用 python scripts/ask.py list",
            "commands": ["setup", "doctor", "list_domains", "list_actions（不带域时自动汇总 12 个域）",
                         "list_actions --domain <域>", "describe_action --action <接口>",
                         "invoke --action <接口> --params '<JSON>'"],
            "first_step": "先跑 doctor",
        }, ensure_ascii=False, indent=2))
        return 0

    if args[0] == "setup":
        print(json.dumps(cmd_setup(), ensure_ascii=False, indent=2))
        return 0
    if args[0] in ("doctor", "--doctor"):
        print(json.dumps(cmd_doctor(online=True), ensure_ascii=False, indent=2))
        return 0

    # 日常查询只做本机四项检查，不每次联网体检；真失败了再回头给引导。
    ok, status = local_state()
    if not ok:
        s = guide_for_status(status)
        print(json.dumps({
            "ok": False, "status": status, "title": s.get("title"),
            "what_happened": s.get("what_happened"), "what_to_do": s.get("what_to_do"),
            "who": s.get("who"), "url": s.get("url"),
            "hint": "请先按上面这一步做完，再重新查。",
        }, ensure_ascii=False))
        return 2

    if args[0] == "invoke":
        res = invoke(args)
        code = (res.get("error") or {}).get("code") or ""
        if code == "AUTH_REQUIRED":
            s = guide_for_status("NOT_AUTHORIZED")
            res["what_to_do"] = s.get("what_to_do")
            res["who"] = s.get("who")
        elif code and code not in ("READONLY_MODE", "ACTION_NOT_ALLOWED"):
            res["hint"] = load_guide().get("errors", {}).get(code, "")
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res.get("ok") else 1
    if args[0] == "list_actions" and not arg_value(args, "--domain"):
        print(json.dumps(list_all_actions(), ensure_ascii=False))
        return 0
    return passthrough(args)


if __name__ == "__main__":
    sys.exit(main())
