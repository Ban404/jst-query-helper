#!/usr/bin/env python3
"""聚水潭查询助手 · 一问一答入口。

AI 日常只用这个文件，命令长这样：

    python scripts/ask.py list                      # 能问什么
    python scripts/ask.py overview --days 7        # 今天生意怎么样
    python scripts/ask.py pending --days 30        # 有没有货要发
    python scripts/ask.py serials --days 30 --csv  # 已发货序列号（顺手导 CSV）
    python scripts/ask.py stock --keyword Arc --low 3
    python scripts/ask.py order --id 订单号
    python scripts/ask.py shops
    python scripts/ask.py sn --sn SN-DEMO-0001     # 序列号反查订单/物流
    python scripts/ask.py query --action refund_single_query  # 其余查询接口
    python scripts/ask.py find 采购

它替 AI 做掉四件麻烦事：接口一次只能查 7 天就自动分段、多页自动翻完、
数据量大时查询程序写文件就自动读出来、结果整理成人话 + 整齐的表格。

底层查数据在同目录的 jst.py，两个包共用 scenarios.json 里的场景清单。
只用 Python 标准库。
"""

import argparse
import csv
import datetime
import json
import os
import sys

import jst

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_ROWS = 50                      # 对话里最多给 50 行，要全量请用 --csv
MAX_DAYS = 180                     # 一次最多往前查 180 天，避免误填把接口打爆


def load_scenarios():
    """场景清单、字段字典、场景话术都在 jst.py 统一读，这里只做转发。"""
    return jst.load_scenarios()


def field_cn():
    return load_scenarios().get("field_cn") or {}


def preferred_cn():
    return load_scenarios().get("preferred_cn") or []


def say(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def default_hint():
    """兜底话术只从 guide.json 的 errors._default 读，不再散落多份。"""
    return jst.load_guide().get("errors", {}).get("_default") or "稍后再试，或换个说法让我查别的内容。"


def hint_for(code):
    errors = jst.load_guide().get("errors", {})
    return errors.get(code) or errors.get("_default") or default_hint()


def failed(code, message, extra=None):
    out = {
        "ok": False, "error": {"code": code, "message": message},
        "what_to_do": hint_for(code),
    }
    out.update(extra or {})
    say(out)
    return 1


def answer(name, summary, rows, notes=None, csv_path=None, fetch_truncated=False):
    """统一输出：一句能直接念给用户听的结论 + 整齐的表格。

    fetch_truncated 表示底层翻页达到上限、结果本身可能不全；这跟
    "对话里只显示前 50 条" 是两回事，必须分开讲清楚，不能让用户误以为
    加了 --csv 就能拿到全量。
    """
    total = len(rows)
    if fetch_truncated:
        note = "已达单次抓取上限，结果可能不全：请把 --days 调小分几次查，别直接拿这份做对账"
    elif total > MAX_ROWS:
        note = "对话里先给前 %d 条，要全量可加 --csv 导出" % MAX_ROWS
    else:
        note = ""
    notes = list(notes or [])
    if fetch_truncated:
        notes.append("底层翻页达到单次上限，导出文件也可能只含已抓取的部分。")
    say({
        "ok": True,
        "scenario": name,
        "summary": summary,
        "count": total,
        "rows": rows[:MAX_ROWS],
        "truncated": total > MAX_ROWS,
        "fetch_truncated": bool(fetch_truncated),
        "truncated_note": note,
        "notes": notes,
        "csv": csv_path or "",
    })
    return 0


def ensure_ready():
    """一次进程只体检一次；没好就返回能直接讲给用户听的引导，不甩英文报错。"""
    ok, status = jst.local_state()
    if not ok:
        return jst.guide_for_status(status)
    state = jst.cmd_doctor(online=True)
    return state if state.get("ok") else state


def check_error(res):
    """把任何查询失败翻成可讲给用户听的引导。

    覆盖 guide.json 里登记的全部错误码；状态类错误（登录/授权/CLI）走
    guide_for_status，其余（超时/无输出/版本不匹配/被拦截）走 errors 文案。
    返回统一结构 {status, title, what_to_do, ...}，成功返回 None。
    """
    if not isinstance(res, dict) or res.get("ok"):
        return None
    code = (res.get("error") or {}).get("code") or "QUERY_FAILED"
    message = (res.get("error") or {}).get("message") or ""
    state_map = {"AUTH_REQUIRED": "NOT_AUTHORIZED", "TOKEN_REJECTED": "TOKEN_REJECTED",
                 "CLI_MISSING": "CLI_MISSING", "TOKEN_EXPIRED": "TOKEN_EXPIRED"}
    if code in state_map:
        guide = jst.guide_for_status(state_map[code])
        return {"status": guide.get("status") or state_map[code],
                "title": message or (guide.get("title") or code),
                "what_to_do": guide.get("what_to_do"), "who": guide.get("who"),
                "url": guide.get("url")}
    hint = hint_for(code)
    return {"status": code, "title": message or code, "what_to_do": hint}


def fail_on_error(res):
    """场景里统一调用：有错就输出中文引导并返回 1，没错返回 None。"""
    guide = check_error(res)
    if not guide:
        return None
    extra = {"what_to_do": guide.get("what_to_do")}
    for k in ("who", "url"):
        if guide.get(k):
            extra[k] = guide[k]
    return failed(guide.get("status") or "QUERY_FAILED", guide.get("title") or "查询没成功", extra)


def was_truncated(res):
    """底层分段/翻页是否被截断，用来如实提示用户结果可能不全。"""
    return bool(isinstance(res, dict) and res.get("truncated"))


def _csv_cell(value):
    """防公式注入：买家名/店铺名来自电商平台，可能因 =/+/-/@ 开头在 Excel 里触发公式。"""
    s = "" if value is None else str(value)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def write_csv(path, headers, rows):
    """导出用 UTF-8 BOM，Excel 双击打开不乱码；单元格防公式注入。"""
    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([_csv_cell(h) for h in headers])
        for r in rows:
            w.writerow([_csv_cell(r.get(h, "")) for h in headers])
    return path


def default_csv(prefix):
    return "%s_%s.csv" % (prefix, datetime.datetime.now().strftime("%Y%m%d"))


def status_cn(code, words):
    return words.get(code, code or "未知状态")


# ---------------------------------------------------------------- 场景：店铺


def sc_shops(args):
    rows, res = jst.paged("shops_query", {}, page_size=50)
    bad = fail_on_error(res)
    if bad is not None:
        return bad
    picked = [{
        "店铺编号": r.get("shop_id"),
        "店铺名称": r.get("shop_name") or r.get("platform_shop_name"),
        "平台": r.get("shop_site") or "",
        "平台账号": r.get("nick"),
        "授权到期": r.get("session_expired") or "",
        "启用": "是" if _truthy(r.get("enabled")) else "否",
    } for r in rows]
    names = "、".join(str(p["店铺名称"]) for p in picked[:5] if p["店铺名称"])
    return answer("店铺列表", "共 %d 个店铺%s。" % (len(picked), ("：" + names) if names else ""), picked,
                  fetch_truncated=was_truncated(res))


# ---------------------------------------------------------------- 场景：库存


def sc_stock(args):
    days = max(1, args.days)
    rows, err = jst.segmented("inventory_query", {}, days=days, page_size=50)
    bad = fail_on_error(err) if err else None
    if bad is not None:
        return bad

    # 同一个 SKU 可能在多个时间段都出现，留最近改动的那条
    latest = {}
    for r in rows:
        key = r.get("sku_id") or r.get("i_id") or r.get("name")
        if key not in latest or str(r.get("modified") or "") > str(latest[key].get("modified") or ""):
            latest[key] = r
    items = list(latest.values())

    kw = (args.keyword or "").strip().lower()
    if kw:
        items = [r for r in items if kw in " ".join(
            str(r.get(k) or "") for k in ("name", "sku_id", "i_id")).lower()]

    low = args.low
    if low is not None:
        items = [r for r in items if _num(r.get("qty")) <= low]

    items.sort(key=lambda r: _num(r.get("qty")))
    picked = [{
        "商品编码": r.get("sku_id"),
        "款号": r.get("i_id"),
        "商品名称": r.get("name"),
        "可用库存": _num(r.get("qty")),
        "订单锁定": _num(r.get("order_lock")),
        "拣货锁定": _num(r.get("pick_lock")),
        "最低库存": _num(r.get("min_qty")),
        "更新时间": r.get("modified") or "",
    } for r in items]

    zero = [p for p in picked if p["可用库存"] <= 0]
    cond = []
    if kw:
        cond.append("含「%s」" % args.keyword)
    if low is not None:
        cond.append("可用库存 ≤ %d" % low)
    if cond:
        cond.append("近 %d 天" % days)
    summary = "查到 %d 个 SKU%s" % (len(picked), ("（" + "、".join(cond) + "）") if cond else "（近 %d 天有变动）" % days)
    if zero:
        summary += "，其中 %d 个已经没货了" % len(zero)
    summary += "。"

    csv_path = ""
    if args.csv:
        csv_path = write_csv(args.csv if args.csv is not True else default_csv("库存"),
                             ["商品编码", "款号", "商品名称", "可用库存", "订单锁定", "拣货锁定", "最低库存", "更新时间"],
                             picked)
        summary += " 已导出到 " + csv_path
    return answer("库存速查", summary, picked,
                  jst.notes_for(load_scenarios(), "stock", days),
                  csv_path, fetch_truncated=was_truncated(err))


def _num(v):
    """统一数值转换：浮点照留、科学计数法认得、非数字回 0。与 Node 版 num() 一致。"""
    try:
        n = float(v)
        if n != n or n in (float("inf"), float("-inf")):  # NaN / 无穷
            return 0
        return n
    except Exception:
        return 0


def _truthy(v):
    """统一真值判断：只认 1/true/'1'/'true'，'0'/'false'/2/空都算否。Node 版同规则。"""
    return v is True or v == 1 or (isinstance(v, str) and v.strip().lower() in ("1", "true", "yes"))


# ---------------------------------------------------------------- 场景：待发货


def _pending_orders(days):
    rows, err = jst.segmented("orders_single_query", {}, days=days, page_size=50)
    wanted = {"WaitConfirm", "Confirmed"}
    seen, out = set(), []
    for r in rows:
        if r.get("status") not in wanted:
            continue
        sid = str(r.get("so_id") or "")
        if sid and sid in seen:
            continue
        seen.add(sid)
        out.append(r)
    return out, err


def _items_of(order):
    items = order.get("items") or []
    return "、".join("%s ×%s" % (it.get("name") or it.get("sku_id") or it.get("i_id"),
                                it.get("qty") or 1) for it in items[:4])


def sc_pending(args):
    days = max(1, args.days)
    orders, err = _pending_orders(days)
    bad = fail_on_error(err) if err else None
    if bad is not None:
        return bad

    cfg = load_scenarios()
    words = cfg.get("status_words", {})
    reasons = cfg.get("pending_reasons") or {}
    # 批量取所有订单的出库单：原来每单一查，50 单就是 50 次进程启动，又慢又容易超时。
    # 一次传全部 so_ids，再按单号分组；某个单查不到出库单就是还没生成。
    all_sids = [str(o.get("so_id") or "") for o in orders if o.get("so_id")]
    io_rows = []
    io_err = None
    if all_sids:
        io_rows, io_err = jst.paged("orders_out_simple_query", {"so_ids": all_sids}, page_size=50)
    shipped = set(str(r.get("so_id") or "") for r in io_rows or [])
    picked = []
    for o in orders:
        sid = str(o.get("so_id") or "")
        if sid in shipped:
            reason = reasons.get("shipped", "已生成出库单，仓库在配货")
        elif o.get("status") == "WaitConfirm":
            reason = reasons.get("wait_confirm", "还没审核，也没指定发货仓，仓库还没接到这单")
        else:
            reason = reasons.get("confirmed", "已确认，但还没生成出库单")
        picked.append({
            "订单号": sid,
            "内部单号": o.get("o_id"),
            "状态": status_cn(o.get("status"), words),
            "店铺": o.get("shop_name") or "",
            "商品": _items_of(o),
            "实付金额": o.get("pay_amount") or o.get("buyer_paid_amount") or "",
            "下单时间": o.get("order_date") or "",
            "压了几天": _days_ago(o.get("order_date")),
            "收货地": (str(o.get("receiver_state") or "") + " " + str(o.get("receiver_city") or "")).strip(),
            "卡在哪": reason,
            "物流单号": o.get("l_id") or "",
        })

    picked.sort(key=lambda r: r["下单时间"])
    if picked:
        first = picked[0]
        summary = "有 %d 单待发货，最早一单是 %s（%s，压了 %s 天）。%s" % (
            len(picked), first["下单时间"][:10], first["商品"], first["压了几天"], first["卡在哪"])
    else:
        summary = "近 %d 天没有待发货订单，都发出去或取消了。" % days

    csv_path = ""
    if args.csv:
        headers = ["订单号", "内部单号", "状态", "店铺", "商品", "实付金额", "下单时间", "压了几天", "收货地", "卡在哪", "物流单号"]
        csv_path = write_csv(args.csv if args.csv is not True else default_csv("待发货订单"), headers, picked)
        summary += " 已导出到 " + csv_path
    pending_notes = jst.notes_for(cfg, "pending", days)
    if io_err and not io_err.get("ok"):
        # 批量查出库单失败：订单列表仍可信，但"卡在哪"判断不出来，如实说明
        pending_notes += jst.notes_for(cfg, "pending_io_failed")
    return answer("待发货订单", summary, picked, pending_notes,
                  csv_path, fetch_truncated=was_truncated(err) or was_truncated(io_err))


def _days_ago(text):
    try:
        d = datetime.datetime.strptime(str(text)[:19], "%Y-%m-%d %H:%M:%S")
        return max(0, (datetime.datetime.now() - d).days)
    except Exception:
        return ""


# ---------------------------------------------------------------- 场景：序列号


def sc_serials(args):
    days = max(1, args.days)
    orders, err = jst.segmented("orders_out_simple_query", {}, days=days, page_size=50)
    bad = fail_on_error(err) if err else None
    if bad is not None:
        return bad

    records, seen = [], set()
    missing = 0
    for o in orders:
        sns = o.get("sns") or []
        if not sns and (o.get("items") or []):
            missing += 1
        for s in sns:
            sn = str(s.get("sn") or "").strip()
            if not sn or sn in seen:
                continue
            seen.add(sn)
            records.append({
                "出库日期": str(o.get("io_date") or "")[:10],
                "出库单号": o.get("io_id"),
                "订单号": o.get("so_id"),
                "商品编码": s.get("sku_id"),
                "序列号": sn,
                "成本价": s.get("cost_price") or s.get("cost_amount") or "",
                "物流公司": o.get("logistics_company") or "",
                "物流单号": o.get("l_id") or "",
                "出库状态": o.get("status") or "",
            })
    records.sort(key=lambda r: r["出库日期"], reverse=True)

    summary = "近 %d 天查到 %d 张销售出库单，取出 %d 个不重复的序列号" % (days, len(orders), len(records))
    summary += "；%d 张单没绑序列号。" % missing if missing else "，每台都绑了序列号，数据很干净。"
    summary += " "

    csv_path = ""
    if args.csv:
        headers = ["出库日期", "出库单号", "订单号", "商品编码", "序列号", "成本价", "物流公司", "物流单号", "出库状态"]
        csv_path = write_csv(args.csv if args.csv is not True else default_csv("已发货序列号"), headers, records)
        summary += " 已导出到 " + csv_path

    return answer("已发货序列号", summary.strip(), records,
                  jst.notes_for(load_scenarios(), "serials"),
                  csv_path, fetch_truncated=was_truncated(err))


# ---------------------------------------------------------------- 场景：单笔订单


def sc_order(args):
    if not args.id:
        return failed("BAD_PARAMS", "要给我一个订单号。", {"usage": "order --id 订单号"})
    sid = str(args.id).strip()
    res = jst.query("orders_single_query", {"so_ids": [sid]})
    bad = fail_on_error(res)
    if bad is not None:
        return bad
    rows, _ = jst.rows_of(res)
    if not rows:
        return failed("EMPTY_RESULT", "没查到订单号 %s。" % sid)
    o = rows[0]
    words = load_scenarios().get("status_words", {})

    io_rows, io_res = jst.paged("orders_out_simple_query", {"so_ids": [sid]}, page_size=50)
    sns = []
    for io in io_rows:
        for s in io.get("sns") or []:
            if s.get("sn"):
                sns.append(str(s["sn"]))
    io = io_rows[0] if io_rows else {}

    detail = {
        "订单号": o.get("so_id"), "内部单号": o.get("o_id"),
        "状态": status_cn(o.get("status"), words), "店铺": o.get("shop_name") or "",
        "商品": _items_of(o),
        "订单金额": o.get("amount") or "", "实付金额": o.get("pay_amount") or "",
        "下单时间": o.get("order_date") or "", "付款时间": o.get("pay_date") or "",
        "发货时间": o.get("send_date") or "（还没发）",
        "收货地": (str(o.get("receiver_state") or "") + str(o.get("receiver_city") or "")).strip(),
        "物流公司": o.get("logistics_company") or io.get("logistics_company") or "",
        "物流单号": o.get("l_id") or io.get("l_id") or "（无）",
        "出库单": io.get("io_id") or "（还没生成）",
        "序列号": "、".join(sns) or "（无）",
        "买家留言": o.get("buyer_message") or "",
        "发货仓": o.get("wms_co_id") or 0,
    }

    if io_rows:
        summary = "订单 %s 已经发货，%s 物流单号 %s。" % (sid, detail["物流公司"] or "顺丰", detail["物流单号"])
    elif o.get("status") == "Cancelled":
        summary = "订单 %s 已经取消了，没有发货。" % sid
    else:
        summary = "订单 %s %s，还没有出库单，仓库没接到这单。" % (sid, detail["状态"])
    return answer("单笔订单追查", summary, [detail],
                  jst.notes_for(load_scenarios(), "order"),
                  fetch_truncated=was_truncated(io_res))


# ---------------------------------------------------------------- 场景：概览


def sc_overview(args):
    days = max(1, args.days)
    words = load_scenarios().get("status_words", {})
    orders, e1 = jst.segmented("orders_single_query", {}, days=days, page_size=50)
    outs, e2 = jst.segmented("orders_out_simple_query", {}, days=days, page_size=50)
    stocks, e3 = jst.segmented("inventory_query", {}, days=days, page_size=50)
    for err in (e1, e2, e3):
        bad = fail_on_error(err) if err else None
        if bad is not None:
            return bad

    seen, unique = set(), []
    for o in orders:
        sid = str(o.get("so_id") or "")
        if sid and sid in seen:
            continue
        seen.add(sid)
        unique.append(o)
    counts = {}
    for o in unique:
        st = o.get("status") or "未知"
        counts[st] = counts.get(st, 0) + 1
    pending = sum(counts.get(k, 0) for k in ("WaitConfirm", "Confirmed"))

    sku_latest = {}
    for r in stocks:
        key = r.get("sku_id") or r.get("i_id")
        if key not in sku_latest:
            sku_latest[key] = r
    low = [r for r in sku_latest.values() if _num(r.get("qty")) <= 2]

    rows = [{
        "指标": "订单总数（去重）", "数值": len(unique), "说明": "近 %d 天有变动的订单" % days,
    }, {
        "指标": "待发货", "数值": pending, "说明": "已付款待审核 + 已确认待发货",
    }, {
        "指标": "已发货", "数值": counts.get("Sent", 0), "说明": status_cn("Sent", words),
    }, {
        "指标": "已取消", "数值": counts.get("Cancelled", 0), "说明": status_cn("Cancelled", words),
    }, {
        "指标": "销售出库单", "数值": len(outs), "说明": "仓库侧已生成的出库单",
    }, {
        "指标": "有变动的 SKU", "数值": len(sku_latest), "说明": "近 %d 天库存有变动的商品种类" % days,
    }, {
        "指标": "库存 ≤ 2 的 SKU", "数值": len(low), "说明": "可能要补货",
    }]
    for st, n in sorted(counts.items(), key=lambda x: -x[1]):
        if st not in ("Sent", "Cancelled", "WaitConfirm", "Confirmed"):
            rows.append({"指标": "其他状态：" + status_cn(st, words), "数值": n, "说明": st})

    summary = "近 %d 天共 %d 单：待发货 %d 单、已发货 %d 单、取消 %d 单；仓库生成 %d 张出库单。" % (
        days, len(unique), pending, counts.get("Sent", 0), counts.get("Cancelled", 0), len(outs))
    if pending:
        summary += " 有货要发，建议先看待发货明细。"
    if low:
        summary += " 另有 %d 款商品库存只剩 2 台或更少，留意补货。" % len(low)
    return answer("经营概览", summary, rows,
                  jst.notes_for(load_scenarios(), "overview"),
                  fetch_truncated=any(was_truncated(e) for e in (e1, e2, e3)))


# ------------------------------------------------------- 场景：序列号反查（售后追溯）


def sc_sn(args):
    """客户报一个 SN，反查是哪张出库单、哪笔订单、哪个物流单号、哪天发的。"""
    sn = str(args.sn or "").strip().lower()
    if not sn:
        return failed("BAD_PARAMS", "要给我一个产品序列号。",
                      {"usage": "sn --sn 序列号 [--days 90]",
                       "what_to_do": "把机器背面或包装上的序列号发我，记不全只发后几位也行。"})
    days = max(1, args.days)
    outs, err = jst.segmented("orders_out_simple_query", {}, days=days, page_size=50)
    bad = fail_on_error(err) if err else None
    if bad is not None:
        return bad

    hits = []
    for o in outs:
        for s in o.get("sns") or []:
            cur = str(s.get("sn") or "").strip()
            if not cur or sn not in cur.lower():
                continue
            hits.append({
                "序列号": cur,
                "出库日期": str(o.get("io_date") or "")[:10],
                "出库单号": o.get("io_id"),
                "订单号": o.get("so_id"),
                "商品编码": s.get("sku_id"),
                "成本价": s.get("cost_price") or s.get("cost_amount") or "",
                "物流公司": o.get("logistics_company") or "",
                "物流单号": o.get("l_id") or "",
                "出库状态": o.get("status") or "",
                "店铺": o.get("shop_name") or "",
            })
    # 同一个 SN 可能重复出现在多个时间段，去重
    uniq, seen = [], set()
    for h in hits:
        key = (h["序列号"], h["出库单号"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
    uniq.sort(key=lambda r: r["出库日期"], reverse=True)

    if not uniq:
        return failed("EMPTY_RESULT", "近 %d 天没找到序列号 %s。" % (days, args.sn),
                      {"what_to_do": "把 --days 调大再查一次（最多 %d 天）；如果还是没有，可能是这台机器出库时间更早，或者没录唯一码。" % MAX_DAYS})
    h = uniq[0]
    summary = "序列号 %s 查到 %d 条出库记录：%s 出库，订单 %s，%s 物流单号 %s。" % (
        h["序列号"], len(uniq), h["出库日期"], h["订单号"],
        h["物流公司"] or "未填物流公司", h["物流单号"] or "（无）")

    csv_path = ""
    if args.csv:
        headers = ["序列号", "出库日期", "出库单号", "订单号", "商品编码", "成本价", "物流公司", "物流单号", "出库状态", "店铺"]
        csv_path = write_csv(args.csv if args.csv is not True else default_csv("序列号反查"), headers, uniq)
        summary += " 已导出到 " + csv_path
    return answer("序列号反查", summary, uniq,
                  jst.notes_for(load_scenarios(), "sn", days),
                  csv_path, fetch_truncated=was_truncated(err))


# ------------------------------------------------------- 场景：通用单据查询


def pick_columns(rows):
    """把 ERP 的英文字段翻成中文，按重要度挑最多 18 列，避免表格太宽。"""
    if not rows or not isinstance(rows[0], dict):
        return []
    scalar = [k for k, v in rows[0].items()
              if v is not None and not isinstance(v, (list, dict))]
    mapping = field_cn()
    cn = {k: mapping.get(k, k) for k in scalar}
    names = list(cn.values())
    head = [n for n in preferred_cn() if n in names]
    tail = sorted(n for n in names if n not in head)
    return (head + tail)[:18]


def sc_query(args):
    """覆盖 7 个固定场景之外的全部查询接口：自动分段、翻页、去重、中文化。"""
    action = str(args.action or "").strip()
    if not action:
        return failed("BAD_PARAMS", "要给我一个接口名。",
                      {"usage": "query --action refund_single_query [--days 7] [--csv 路径]",
                       "what_to_do": "先跑 find 关键词 找接口名，例如 find 售后。"})
    catalog = jst.all_actions()
    if not catalog:
        return failed("CATALOG_MISSING", "接口清单没找到，这个技能可能没装全。")
    meta = catalog.get(action) or {}
    if not meta:
        return failed("ACTION_NOT_ALLOWED", "接口 %s 没登记在清单里，只读版不允许调用。" % action,
                      {"what_to_do": "跑 find %s 看看有没有名字相近的查询接口。" % action})
    if meta.get("kind") != "query":
        return failed("READONLY_MODE", "「%s」是修改数据的操作，只读版已经拦下了。" % (meta.get("name") or action))

    days = max(1, args.days)
    rows, err = jst.segmented(action, {}, days=days, page_size=50)
    bad = fail_on_error(err) if err else None
    if bad is not None:
        return bad

    # 同一条单据可能在多个时间段重复出现
    uniq, seen = [], set()
    for r in rows:
        key = json.dumps(r, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)

    cols = pick_columns(uniq)
    mapping = field_cn()
    cn_to_raw = {mapping.get(k, k): k for k in (uniq[0].keys() if uniq else [])}
    picked = [{c: r.get(cn_to_raw.get(c, c), "") for c in cols} for r in uniq] if cols else []

    title = meta.get("name") or action
    summary = "%s：近 %d 天查到 %d 条记录" % (title, days, len(picked))
    summary += "，这段时间没有数据，可以把 --days 调大一点再试。" if not picked else "。"

    csv_path = ""
    if args.csv:
        csv_path = write_csv(args.csv if args.csv is not True else default_csv(title), cols, picked)
        summary += " 已导出到 " + csv_path
    return answer(title, summary, picked,
                  jst.notes_for(load_scenarios(), "query", days),
                  csv_path, fetch_truncated=was_truncated(err))


# ---------------------------------------------------------------- 场景：找接口


def sc_find(args):
    kw = (args.keyword or "").strip().lower()
    actions = jst.all_actions()
    hits = []
    for key, meta in actions.items():
        text = (key + " " + str(meta.get("name") or "") + " " + str(meta.get("domain") or "")).lower()
        if not kw or kw in text:
            hits.append({
                "接口": key, "名称": meta.get("name") or "",
                "分类": meta.get("domain") or "",
                "能不能用": "可查询" if meta.get("kind") == "query" else "只读版不允许",
            })
    hits.sort(key=lambda r: (r["能不能用"] != "可查询", r["分类"], r["接口"]))
    usable = sum(1 for h in hits if h["能不能用"] == "可查询")
    return answer("找接口", "找到 %d 个接口，其中 %d 个可以查（其余是写操作，只读版拦下了）。" % (len(hits), usable),
                  hits, jst.notes_for(load_scenarios(), "find"))


def sc_list(args):
    cfg = load_scenarios()
    rows = [{
        "场景": s.get("name"), "命令": s.get("usage"),
        "用户会这么问": "、".join(s.get("ask") or []),
        "能拿到什么": s.get("what"),
    } for s in cfg.get("scenarios", [])]
    return answer("能问什么", "一共 %d 个常用场景，直接说业务问题就行，我会挑合适的场景。" % len(rows),
                  rows, cfg.get("tips", []))


# -------------------------------------------------------------------- 命令行


def main():
    parser = argparse.ArgumentParser(description="聚水潭查询助手：一句话问业务问题")
    sub = parser.add_subparsers(dest="scene")

    p = sub.add_parser("list", help="列出能问什么")
    p.set_defaults(func=sc_list)

    p = sub.add_parser("shops", help="店铺列表")
    p.set_defaults(func=sc_shops)

    p = sub.add_parser("stock", help="库存速查")
    p.add_argument("--keyword", default="", help="商品名或编码关键词")
    p.add_argument("--low", type=int, default=None, help="只看可用库存不超过这个数")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--csv", nargs="?", const=True, default=None)
    p.set_defaults(func=sc_stock)

    p = sub.add_parser("pending", help="待发货订单")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--csv", nargs="?", const=True, default=None)
    p.set_defaults(func=sc_pending)

    p = sub.add_parser("serials", help="已发货序列号")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--csv", nargs="?", const=True, default=None)
    p.set_defaults(func=sc_serials)

    p = sub.add_parser("order", help="单笔订单追查")
    p.add_argument("--id", required=True)
    p.set_defaults(func=sc_order)

    p = sub.add_parser("overview", help="经营概览")
    p.add_argument("--days", type=int, default=7)
    p.set_defaults(func=sc_overview)

    p = sub.add_parser("sn", help="按序列号反查出库记录")
    p.add_argument("--sn", required=True, help="产品序列号，可只填后几位")
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--csv", nargs="?", const=True, default=None)
    p.set_defaults(func=sc_sn)

    p = sub.add_parser("query", help="通用单据查询，覆盖其余查询接口")
    p.add_argument("--action", required=True, help="接口名，可先用 find 找")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--csv", nargs="?", const=True, default=None)
    p.set_defaults(func=sc_query)

    p = sub.add_parser("find", help="按关键词找接口")
    p.add_argument("keyword", nargs="?", default="")
    p.set_defaults(func=sc_find)

    # 参数写错时 argparse 默认打英文 usage 就退出，AI 调用方拿不到结构化结果。
    # 拦下来转成统一的中文 JSON，和 Node 版行为一致。
    try:
        args = parser.parse_args()
    except SystemExit as exc:
        if exc.code in (0, None):
            return sc_list(argparse.Namespace())
        return failed("BAD_PARAMS", "参数没认出来，比如 --days 要填数字。",
                      {"what_to_do": "检查命令里的数字参数（--days / --low）是不是写成了文字。"})
    if not getattr(args, "func", None):
        return sc_list(args)

    # 统一防误填：跨度太大会把接口打爆；0 或负数同样不合法（Node 版按同一规则处理）
    days_val = getattr(args, "days", None)
    if days_val is not None:
        if days_val <= 0:
            return failed("BAD_PARAMS", "--days 要填大于 0 的天数，你填了 %d。" % days_val,
                          {"what_to_do": "填 1 到 %d 之间的数字。" % MAX_DAYS})
        if days_val > MAX_DAYS:
            return failed("BAD_PARAMS", "一次最多往前查 %d 天，你填了 %d 天。" % (MAX_DAYS, days_val),
                          {"what_to_do": "把 --days 改小一点，或者分几次查；已经查过的结果不会丢。"})

    # 不联网的场景直接跑，其余先体检一次
    if args.scene in ("list", "find"):
        return args.func(args)
    state = ensure_ready()
    if not state.get("ok"):
        say({
            "ok": False, "status": state.get("status"), "title": state.get("title"),
            "what_happened": state.get("what_happened"), "what_to_do": state.get("what_to_do"),
            "who": state.get("who"), "url": state.get("url"),
            "success_check": state.get("success_check"),
            "hint": "先做完这一步，再重新问一遍。",
        })
        return 2
    try:
        return args.func(args)
    except (OSError, IOError) as exc:
        # 多半是 --csv 路径写不进去（目录不存在/只读/是文件夹），别甩英文 traceback
        return failed("CSV_WRITE_FAILED", "CSV 写不进去：%s" % str(exc)[:150],
                      {"what_to_do": "换个能写的路径，或不加 --csv 直接在对话里看结果。"})


if __name__ == "__main__":
    sys.exit(main())
