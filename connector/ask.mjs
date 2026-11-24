#!/usr/bin/env node
/**
 * 聚水潭查询助手 · 一问一答（连接器版）
 *
 * 和技能包的 ask.py 是同一套场景、同一份 scenarios.json，说法完全一致。
 * 这份是纯 Node 标准库，不依赖 Python、不装 npm 包，供 server.mjs 用子进程调用。
 *
 * 用法：node ask.mjs pending --days 30
 *      node ask.mjs sn --sn SN-DEMO-0001          序列号反查订单/物流
 *      node ask.mjs query --action refund_single_query  其余查询接口
 */

import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const GUIDE = JSON.parse(readFileSync(path.join(HERE, 'guide.json'), 'utf8'));
const SCENARIOS = JSON.parse(readFileSync(path.join(HERE, 'scenarios.json'), 'utf8'));
const ACTIONS_FILE = path.join(HERE, 'jst', 'scripts', 'actions.json');
const READONLY_FILE = path.join(HERE, 'jst', 'READONLY');
const MAX_ROWS = 50;
const MAX_DAYS = 180;

// 通用单据查询用：把 ERP 的英文字段翻成中文列名，没登记的原样保留。
const FIELD_CN = {
  as_id: '售后单号', outer_as_id: '平台售后单号', as_date: '售后日期',
  po_id: '采购单号', io_id: '单据编号', so_id: '订单号', o_id: '内部单号',
  sku_id: '商品编码', i_id: '款号', name: '商品名称', sku_name: '商品名称',
  qty: '数量', num: '数量', amount: '金额', price: '单价', cost_price: '成本价',
  pay_amount: '实付金额', free_amount: '退款金额', buyer_apply_refund: '申请退款额',
  status: '状态', good_status: '货物状态', order_status: '订单状态',
  modified: '修改时间', created: '创建时间', order_date: '下单时间',
  io_date: '单据日期', pay_date: '付款时间',
  shop_name: '店铺', shop_id: '店铺编号', shop_site: '平台',
  wms_co_id: '发货仓', warehouse_name: '仓库', logistics_company: '物流公司',
  l_id: '物流单号', supplier_name: '供应商', supplier_id: '供应商编号',
  receiver_state: '省份', receiver_city: '城市', receiver_name: '收货人',
  remark: '备注', creator_name: '创建人', modifier_name: '修改人',
  sn: '序列号', min_qty: '最低库存', order_lock: '订单锁定',
};
const PREFERRED = ['单据编号', '售后单号', '采购单号', '订单号', '内部单号', '单据日期', '售后日期',
  '下单时间', '状态', '店铺', '商品编码', '商品名称', '数量', '金额', '实付金额',
  '申请退款额', '货物状态', '物流公司', '物流单号', '供应商', '仓库', '备注', '修改时间'];

const say = (obj) => process.stdout.write(JSON.stringify(obj, null, 2) + '\n');
const statuses = SCENARIOS.status_words || {};
const statusCn = (code) => statuses[code] || code || '未知状态';
const hintFor = (code) => (GUIDE.errors || {})[code] || '';

// ---------------------------------------------------------------------------
// 水宝在哪、登录凭据、查询程序
// ---------------------------------------------------------------------------
function homes() {
  const roots = [];
  if (process.env.APPDATA) roots.push(path.join(process.env.APPDATA, 'jstclient'));
  roots.push(path.join(os.homedir(), 'Library', 'Application Support', 'jstclient'));
  roots.push(path.join(os.homedir(), '.config', 'jstclient'));
  return roots.map((home) => ({
    home,
    cfg: path.join(home, 'configs', 'user_config.json'),
    skill: path.join(home, 'data', 'agent', 'skills', 'jst-open-platform'),
  }));
}

function cliRel() {
  if (process.platform === 'win32') return path.join('scripts', 'bin', 'windows-amd64', 'jst-open-platform.exe');
  if (process.platform === 'darwin') {
    const f = process.arch === 'arm64' ? 'darwin-arm64' : 'darwin-amd64';
    return path.join('scripts', 'bin', f, 'jst-open-platform');
  }
  return path.join('scripts', 'bin', 'linux-amd64', 'jst-open-platform');
}

function walkFor(dir, filename, depth = 4) {
  if (depth <= 0 || !existsSync(dir)) return null;
  let entries;
  try { entries = readdirSync(dir); } catch { return null; }
  for (const name of entries) {
    const p = path.join(dir, name);
    if (name === filename) return p;
    try {
      if (statSync(p).isDirectory()) {
        const hit = walkFor(p, filename, depth - 1);
        if (hit) return hit;
      }
    } catch { /* 没权限就跳过 */ }
  }
  return null;
}

function findCli() {
  const rel = cliRel();
  if (process.env.JST_CLI_PATH && existsSync(process.env.JST_CLI_PATH)) return process.env.JST_CLI_PATH;
  const own = path.join(HERE, 'jst', rel);
  if (existsSync(own)) return own;
  for (const h of homes()) {
    const p = path.join(h.skill, rel);
    if (existsSync(p)) return p;
  }
  const old = path.join(os.homedir(), '.workbuddy', 'skills', 'jst-open-platform', rel);
  if (existsSync(old)) return old;
  for (const h of homes()) {
    const hit = walkFor(path.join(h.home, 'data', 'agent', 'skills'), path.basename(rel));
    if (hit) return hit;
  }
  return null;
}

function looksLikeJwt(text) {
  if (!text || text.split('.').length !== 3) return false;
  try { JSON.parse(Buffer.from(text.split('.')[0], 'base64url').toString('utf8')); return true; }
  catch { return false; }
}

function straighten(text) {
  const raw = String(text || '').trim();
  if (!raw) return '';
  if (looksLikeJwt(raw)) return raw;
  const flipped = [...raw].reverse().join('');
  return looksLikeJwt(flipped) ? flipped : raw;
}

function tokenInfo() {
  if (process.env.JXY_TOKEN) return straighten(process.env.JXY_TOKEN);
  for (const h of homes()) {
    if (!existsSync(h.cfg)) continue;
    try {
      const t = straighten(JSON.parse(readFileSync(h.cfg, 'utf8')).token);
      if (t) return t;
    } catch { /* 文件坏了就试下一个 */ }
  }
  return '';
}

function claimsOf(token) {
  try { return JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString('utf8')); }
  catch { return {}; }
}

function allActions() {
  try { return JSON.parse(readFileSync(ACTIONS_FILE, 'utf8')).actions || {}; }
  catch { return {}; }
}

function isReadOnly() {
  return process.env.JST_ALLOW_WRITE !== '1' && existsSync(READONLY_FILE);
}

// ---------------------------------------------------------------------------
// 调查询程序：自动补版本号、只读白名单、结果落盘自动读
// ---------------------------------------------------------------------------
function runCli(args) {
  const exe = findCli();
  if (!exe) return { ok: false, error: { code: 'CLI_MISSING', message: '查询程序未就绪' } };
  const r = spawnSync(exe, [...args, '--json'], {
    encoding: 'utf8', timeout: 90000, windowsHide: true,
    env: { ...process.env, JXY_TOKEN: tokenInfo() },
  });
  const out = String(r.stdout || '').trim();
  if (!out) return { ok: false, error: { code: 'NO_OUTPUT', message: String(r.stderr || '查询程序没有返回内容').slice(0, 300) } };
  try { return JSON.parse(out); } catch { return { ok: false, raw_output: out.slice(0, 2000) }; }
}

const revisions = new Map();
function revisionOf(action) {
  if (revisions.has(action)) return revisions.get(action);
  const data = runCli(['describe_action', '--action', action]).data || {};
  const rev = data.schema_revision || (data.schema_contract || {}).schema_revision;
  if (rev) revisions.set(action, rev);
  return rev;
}

function denied(action) {
  const meta = allActions()[action];
  const write = meta && meta.kind === 'write';
  const code = write ? 'READONLY_MODE' : 'ACTION_NOT_ALLOWED';
  return {
    ok: false,
    error: {
      code,
      message: write ? `「${meta.name || action}」会修改 ERP 数据，只读版已拦下。` : `「${action}」不是允许查询的接口。`,
      what_to_do: hintFor(code) || '换个查询类的说法，或让我列出能查的内容。',
    },
  };
}

function query(action, params) {
  if (isReadOnly() && allActions()[action]?.kind !== 'query') return denied(action);
  const base = ['invoke', '--action', action, '--params', JSON.stringify(params || {})];
  let rev = revisionOf(action);
  let res = rev ? runCli([...base, '--schema_revision', rev]) : runCli(base);
  const code = (res.error || {}).code || '';
  if (rev && ['SCHEMA_PREFLIGHT_REQUIRED', 'SCHEMA_REVISION_MISMATCH'].includes(code)) {
    revisions.delete(action);
    const fresh = revisionOf(action);
    if (fresh) res = runCli([...base, '--schema_revision', fresh]);
  }
  return res;
}

function rowsOf(result) {
  if (!result || !result.ok) return { rows: [], meta: {} };
  let blob = result.data;
  if (!blob || typeof blob !== 'object') {
    const p = result.raw_data_path;
    if (p && existsSync(p)) {
      try { blob = JSON.parse(readFileSync(p, 'utf8')); } catch { return { rows: [], meta: {} }; }
    }
  }
  if (!blob || typeof blob !== 'object') return { rows: [], meta: {} };
  const preferred = ['orders', 'datas', 'inventorys', 'items', 'skus', 'refunds', 'list', 'rows'];
  let rows = [];
  for (const key of preferred) {
    if (Array.isArray(blob[key])) { rows = blob[key]; break; }
  }
  if (!rows.length) {
    for (const v of Object.values(blob)) {
      if (Array.isArray(v) && (!v.length || typeof v[0] === 'object')) { rows = v; break; }
    }
  }
  const meta = {};
  for (const k of ['has_next', 'page_count', 'page_index', 'page_size', 'data_count']) {
    if (k in blob) meta[k] = blob[k];
  }
  return { rows, meta };
}

function paged(action, params, pageSize = 50, maxPages = 20) {
  const out = [];
  const base = { ...(params || {}), page_size: (params || {}).page_size || pageSize };
  let index = 1, pages = 0;
  while (pages < maxPages) {
    const res = query(action, { ...base, page_index: index });
    if (!res.ok) return { rows: out, err: res };
    const { rows, meta } = rowsOf(res);
    out.push(...rows);
    pages += 1;
    if (meta.has_next === false || rows.length < base.page_size) break;
    if (meta.page_count && index >= meta.page_count) break;
    index += 1;
  }
  return { rows: out, err: null };
}

const fmt = (d) => {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
};

function timeWindows(days = 7, span = 7) {
  const now = new Date();
  const start = new Date(now.getTime() - days * 86400000);
  const out = [];
  let cur = new Date(start);
  while (cur < now) {
    const end = new Date(Math.min(cur.getTime() + span * 86400000 - 1000, now.getTime()));
    out.push([fmt(cur), fmt(end)]);
    cur = new Date(end.getTime() + 1000);
  }
  return out;
}

function segmented(action, params, days = 7, pageSize = 50) {
  const out = [];
  const exact = ['so_ids', 'o_ids', 'io_ids', 'sku_ids', 'i_ids'].some((k) => k in (params || {}));
  const windows = exact ? [[null, null]] : timeWindows(days);
  for (const [begin, end] of windows) {
    const seg = { ...(params || {}) };
    if (begin) { seg.modified_begin = begin; seg.modified_end = end; }
    const { rows, err } = paged(action, seg, pageSize);
    out.push(...rows);
    if (err) return { rows: out, err };
  }
  return { rows: out, err: null };
}

// ---------------------------------------------------------------------------
// 体检与统一输出
// ---------------------------------------------------------------------------
function ensureReady() {
  const st = GUIDE.statuses || {};
  const wrap = (key, extra = {}) => ({ ok: false, status: key, ...(st[key] || {}), ...extra });
  const installed = homes().some((h) => existsSync(h.home));
  if (!installed) return wrap('SHUIBAO_MISSING');
  const token = tokenInfo();
  if (!token) return wrap('SHUIBAO_NOT_LOGGED_IN');
  if (!findCli()) return wrap('CLI_MISSING');
  const c = claimsOf(token);
  if (typeof c.exp === 'number' && c.exp <= Date.now() / 1000) return wrap('TOKEN_EXPIRED');
  const probe = runCli(['list_connections']);
  const code = (probe.error || {}).code || '';
  if (!probe.ok && code !== 'AUTH_REQUIRED') return wrap('TOKEN_REJECTED', { detail: code });
  if (!probe.ok) return wrap('NOT_AUTHORIZED');
  return { ok: true, status: 'READY' };
}

function guideFor(res) {
  if (!res || res.ok) return null;
  const code = (res.error || {}).code || '';
  const map = { AUTH_REQUIRED: 'NOT_AUTHORIZED', TOKEN_REJECTED: 'TOKEN_REJECTED', CLI_MISSING: 'CLI_MISSING' };
  const key = map[code];
  return key ? { ok: false, status: key, ...(GUIDE.statuses[key] || {}) } : null;
}

function failed(code, message, extra = {}) {
  say({ ok: false, error: { code, message }, what_to_do: hintFor(code) || '稍后再试，或换个说法让我查别的内容。', ...extra });
  return 1;
}

function answer(name, summary, rows, notes = [], csvPath = '') {
  say({
    ok: true, scenario: name, summary, count: rows.length,
    rows: rows.slice(0, MAX_ROWS), truncated: rows.length > MAX_ROWS,
    truncated_note: rows.length > MAX_ROWS ? `对话里先给前 ${MAX_ROWS} 条，要全量可加 --csv 导出` : '',
    notes, csv: csvPath,
  });
  return 0;
}

function writeCsv(file, headers, rows) {
  const target = path.isAbsolute(file) ? file : path.join(process.cwd(), file);
  mkdirSync(path.dirname(target), { recursive: true });
  const esc = (v) => {
    const s = String(v ?? '');
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const lines = [headers.join(',')];
  for (const r of rows) lines.push(headers.map((h) => esc(r[h])).join(','));
  writeFileSync(target, '\uFEFF' + lines.join('\r\n'), 'utf8');
  return target;
}

const defaultCsv = (prefix) => `${prefix}_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.csv`;
const num = (v) => { const n = Number(v); return Number.isFinite(n) ? n : 0; };

function itemsOf(order) {
  return (order.items || []).slice(0, 4)
    .map((it) => `${it.name || it.sku_id || it.i_id} ×${it.qty || 1}`).join('、');
}

function daysAgo(text) {
  const d = new Date(String(text || '').replace(' ', 'T'));
  if (Number.isNaN(d.getTime())) return '';
  return Math.max(0, Math.floor((Date.now() - d.getTime()) / 86400000));
}

// ---------------------------------------------------------------------------
// 场景
// ---------------------------------------------------------------------------
function scShops(o) {
  const { rows, err } = paged('shops_query', {});
  const g = guideFor(err);
  if (g) return failed(g.status, g.title, { what_to_do: g.what_to_do });
  const picked = rows.map((r) => ({
    '店铺编号': r.shop_id, '店铺名称': r.shop_name || r.platform_shop_name,
    '平台': r.shop_site || '', '平台账号': r.nick, '授权到期': r.session_expired || '',
    '启用': r.enabled ? '是' : '否',
  }));
  const names = picked.slice(0, 5).map((p) => p['店铺名称']).filter(Boolean).join('、');
  return answer('店铺列表', `共 ${picked.length} 个店铺${names ? '：' + names : ''}。`, picked);
}

function scStock(o) {
  const days = Math.max(1, o.days || 7);
  const { rows, err } = segmented('inventory_query', {}, days);
  const g = guideFor(err);
  if (g) return failed(g.status, g.title, { what_to_do: g.what_to_do });
  const latest = new Map();
  for (const r of rows) {
    const key = r.sku_id || r.i_id || r.name;
    const prev = latest.get(key);
    if (!prev || String(r.modified || '') > String(prev.modified || '')) latest.set(key, r);
  }
  let items = [...latest.values()];
  const kw = String(o.keyword || '').trim().toLowerCase();
  if (kw) items = items.filter((r) => ['name', 'sku_id', 'i_id'].map((k) => String(r[k] || '')).join(' ').toLowerCase().includes(kw));
  if (o.low !== undefined && o.low !== null) items = items.filter((r) => num(r.qty) <= o.low);
  items.sort((a, b) => num(a.qty) - num(b.qty));
  const picked = items.map((r) => ({
    '商品编码': r.sku_id, '款号': r.i_id, '商品名称': r.name, '可用库存': num(r.qty),
    '订单锁定': num(r.order_lock), '拣货锁定': num(r.pick_lock), '最低库存': num(r.min_qty),
    '更新时间': r.modified || '',
  }));
  const zero = picked.filter((p) => p['可用库存'] <= 0).length;
  const cond = [kw ? `含「${o.keyword}」` : '', o.low !== undefined && o.low !== null ? `可用库存 ≤ ${o.low}` : '', `近 ${days} 天`].filter(Boolean);
  let summary = `查到 ${picked.length} 个 SKU（${cond.join('、')}）`;
  if (zero) summary += `，其中 ${zero} 个已经没货了`;
  summary += '。';
  let csvPath = '';
  if (o.csv) {
    csvPath = writeCsv(o.csv === true ? defaultCsv('库存') : o.csv,
      ['商品编码', '款号', '商品名称', '可用库存', '订单锁定', '拣货锁定', '最低库存', '更新时间'], picked);
    summary += ' 已导出到 ' + csvPath;
  }
  return answer('库存速查', summary, picked,
    ['库存按「可用库存」从少到多排；同一商品在多个时间段出现时只留最新一条。',
     `这是按修改时间查的，近 ${days} 天没变动的商品不会出现。`], csvPath);
}

function pendingOrders(days) {
  const { rows, err } = segmented('orders_single_query', {}, days);
  const wanted = new Set(['WaitConfirm', 'Confirmed']);
  const seen = new Set();
  const out = [];
  for (const r of rows) {
    if (!wanted.has(r.status)) continue;
    const sid = String(r.so_id || '');
    if (sid && seen.has(sid)) continue;
    seen.add(sid);
    out.push(r);
  }
  return { orders: out, err };
}

function scPending(o) {
  const days = Math.max(1, o.days || 30);
  const { orders, err } = pendingOrders(days);
  const g = guideFor(err);
  if (g) return failed(g.status, g.title, { what_to_do: g.what_to_do });
  const picked = orders.map((r) => {
    const sid = String(r.so_id || '');
    const { rows: io } = sid ? paged('orders_out_simple_query', { so_ids: [sid] }) : { rows: [] };
    const reason = io.length ? '已生成出库单，仓库在配货'
      : r.status === 'WaitConfirm' ? '还没审核，也没指定发货仓，仓库还没接到这单'
        : '已确认，但还没生成出库单';
    return {
      '订单号': sid, '内部单号': r.o_id, '状态': statusCn(r.status), '店铺': r.shop_name || '',
      '商品': itemsOf(r), '实付金额': r.pay_amount || r.buyer_paid_amount || '',
      '下单时间': r.order_date || '', '压了几天': daysAgo(r.order_date),
      '收货地': `${r.receiver_state || ''} ${r.receiver_city || ''}`.trim(),
      '卡在哪': reason, '物流单号': r.l_id || '',
    };
  });
  picked.sort((a, b) => String(a['下单时间']).localeCompare(String(b['下单时间'])));
  let summary;
  if (picked.length) {
    const f = picked[0];
    summary = `有 ${picked.length} 单待发货，最早一单是 ${String(f['下单时间']).slice(0, 10)}（${f['商品']}，压了 ${f['压了几天']} 天）。${f['卡在哪']}`;
  } else {
    summary = `近 ${days} 天没有待发货订单，都发出去或取消了。`;
  }
  let csvPath = '';
  if (o.csv) {
    csvPath = writeCsv(o.csv === true ? defaultCsv('待发货订单') : o.csv,
      ['订单号', '内部单号', '状态', '店铺', '商品', '实付金额', '下单时间', '压了几天', '收货地', '卡在哪', '物流单号'], picked);
    summary += ' 已导出到 ' + csvPath;
  }
  return answer('待发货订单', summary, picked,
    [`按订单「修改时间」分 7 天一段往前扫了 ${days} 天，不是按下单时间。`,
     '待发货 = 状态 WaitConfirm（已付款待审核）或 Confirmed（已确认待发货）。',
     '「卡在哪」是把订单和销售出库单对照后判断的，供参考，实际以 ERP 里为准。'], csvPath);
}

function scSerials(o) {
  const days = Math.max(1, o.days || 30);
  const { rows, err } = segmented('orders_out_simple_query', {}, days);
  const g = guideFor(err);
  if (g) return failed(g.status, g.title, { what_to_do: g.what_to_do });
  const records = [], seen = new Set();
  let missing = 0;
  for (const r of rows) {
    const sns = r.sns || [];
    if (!sns.length && (r.items || []).length) missing += 1;
    for (const s of sns) {
      const sn = String(s.sn || '').trim();
      if (!sn || seen.has(sn)) continue;
      seen.add(sn);
      records.push({
        '出库日期': String(r.io_date || '').slice(0, 10), '出库单号': r.io_id, '订单号': r.so_id,
        '商品编码': s.sku_id, '序列号': sn, '成本价': s.cost_price || s.cost_amount || '',
        '物流公司': r.logistics_company || '', '物流单号': r.l_id || '', '出库状态': r.status || '',
      });
    }
  }
  records.sort((a, b) => String(b['出库日期']).localeCompare(String(a['出库日期'])));
  let summary = `近 ${days} 天查到 ${rows.length} 张销售出库单，取出 ${records.length} 个不重复的序列号`;
  summary += missing ? `；${missing} 张单没绑序列号。` : '，每台都绑了序列号，数据很干净。';
  let csvPath = '';
  if (o.csv) {
    csvPath = writeCsv(o.csv === true ? defaultCsv('已发货序列号') : o.csv,
      ['出库日期', '出库单号', '订单号', '商品编码', '序列号', '成本价', '物流公司', '物流单号', '出库状态'], records);
    summary += ' 已导出到 ' + csvPath;
  }
  return answer('已发货序列号', summary, records,
    ['序列号挂在销售出库单主表上，订单接口里查不到。',
     '按出库单「修改时间」分 7 天一段查的，个别单据的出库日期可能早于查询范围。',
     '每条都带成本价，可以直接拿去和台账逐台对 SN。'], csvPath);
}

function scOrder(o) {
  const sid = String(o.id || '').trim();
  if (!sid) return failed('BAD_PARAMS', '要给我一个订单号。', { usage: 'order --id 订单号' });
  const res = query('orders_single_query', { so_ids: [sid] });
  const g = guideFor(res);
  if (g) return failed(g.status, g.title, { what_to_do: g.what_to_do });
  const { rows } = rowsOf(res);
  if (!rows.length) return failed('EMPTY_RESULT', `没查到订单号 ${sid}。`);
  const r = rows[0];
  const { rows: outs } = paged('orders_out_simple_query', { so_ids: [sid] });
  const sns = [];
  for (const io of outs) for (const s of io.sns || []) if (s.sn) sns.push(String(s.sn));
  const io = outs[0] || {};
  const detail = {
    '订单号': r.so_id, '内部单号': r.o_id, '状态': statusCn(r.status), '店铺': r.shop_name || '',
    '商品': itemsOf(r), '订单金额': r.amount || '', '实付金额': r.pay_amount || '',
    '下单时间': r.order_date || '', '付款时间': r.pay_date || '', '发货时间': r.send_date || '（还没发）',
    '收货地': `${r.receiver_state || ''}${r.receiver_city || ''}`.trim(),
    '物流公司': r.logistics_company || io.logistics_company || '',
    '物流单号': r.l_id || io.l_id || '（无）', '出库单': io.io_id || '（还没生成）',
    '序列号': sns.join('、') || '（无）', '买家留言': r.buyer_message || '', '发货仓': r.wms_co_id || 0,
  };
  const summary = outs.length ? `订单 ${sid} 已经发货，${detail['物流公司'] || '顺丰'} 物流单号 ${detail['物流单号']}。`
    : r.status === 'Cancelled' ? `订单 ${sid} 已经取消了，没有发货。`
      : `订单 ${sid} ${detail['状态']}，还没有出库单，仓库没接到这单。`;
  return answer('单笔订单追查', summary, [detail],
    ['订单详情和销售出库单是两次查询拼起来的；没有出库单通常意味着还没审核或没指定发货仓。']);
}

function scOverview(o) {
  const days = Math.max(1, o.days || 7);
  const a = segmented('orders_single_query', {}, days);
  const b = segmented('orders_out_simple_query', {}, days);
  const c = segmented('inventory_query', {}, days);
  for (const e of [a.err, b.err, c.err]) {
    const g = guideFor(e);
    if (g) return failed(g.status, g.title, { what_to_do: g.what_to_do });
  }
  const seen = new Set(), unique = [];
  for (const r of a.rows) {
    const sid = String(r.so_id || '');
    if (sid && seen.has(sid)) continue;
    seen.add(sid);
    unique.push(r);
  }
  const counts = {};
  for (const r of unique) counts[r.status || '未知'] = (counts[r.status || '未知'] || 0) + 1;
  const pending = (counts.WaitConfirm || 0) + (counts.Confirmed || 0);
  const sku = new Map();
  for (const r of c.rows) {
    const key = r.sku_id || r.i_id;
    if (!sku.has(key)) sku.set(key, r);
  }
  const low = [...sku.values()].filter((r) => num(r.qty) <= 2).length;
  const rows = [
    { '指标': '订单总数（去重）', '数值': unique.length, '说明': `近 ${days} 天有变动的订单` },
    { '指标': '待发货', '数值': pending, '说明': '已付款待审核 + 已确认待发货' },
    { '指标': '已发货', '数值': counts.Sent || 0, '说明': statusCn('Sent') },
    { '指标': '已取消', '数值': counts.Cancelled || 0, '说明': statusCn('Cancelled') },
    { '指标': '销售出库单', '数值': b.rows.length, '说明': '仓库侧已生成的出库单' },
    { '指标': '有变动的 SKU', '数值': sku.size, '说明': `近 ${days} 天库存有变动的商品种类` },
    { '指标': '库存 ≤ 2 的 SKU', '数值': low, '说明': '可能要补货' },
  ];
  let summary = `近 ${days} 天共 ${unique.length} 单：待发货 ${pending} 单、已发货 ${counts.Sent || 0} 单、取消 ${counts.Cancelled || 0} 单；仓库生成 ${b.rows.length} 张出库单。`;
  if (pending) summary += ' 有货要发，建议先看待发货明细。';
  if (low) summary += ` 另有 ${low} 款商品库存只剩 2 台或更少，留意补货。`;
  return answer('经营概览', summary, rows,
    ['按业务单据的「修改时间」统计，不是按下单/出库时间。',
     '想看某一项的明细，直接说「有没有货要发」「查序列号」「哪些货快没了」。']);
}

// ---------------------------------------------------------------------------
// 场景：序列号反查（售后追溯）
// ---------------------------------------------------------------------------
function scSn(o) {
  const sn = String(o.sn || '').trim().toLowerCase();
  if (!sn) return failed('BAD_PARAMS', '要给我一个产品序列号。', {
    usage: 'sn --sn 序列号 [--days 90]',
    what_to_do: '把机器背面或包装上的序列号发我，记不全只发后几位也行。',
  });
  const days = Math.max(1, o.days || 90);
  const { rows, err } = segmented('orders_out_simple_query', {}, days);
  const g = guideFor(err);
  if (g) return failed(g.status, g.title, { what_to_do: g.what_to_do });

  const hits = [];
  for (const r of rows) {
    for (const s of (r.sns || [])) {
      const cur = String(s.sn || '').trim();
      if (!cur || !cur.toLowerCase().includes(sn)) continue;
      hits.push({
        '序列号': cur, '出库日期': String(r.io_date || '').slice(0, 10),
        '出库单号': r.io_id, '订单号': r.so_id, '商品编码': s.sku_id,
        '成本价': s.cost_price || s.cost_amount || '',
        '物流公司': r.logistics_company || '', '物流单号': r.l_id || '',
        '出库状态': r.status || '', '店铺': r.shop_name || '',
      });
    }
  }
  const seen = new Set();
  const uniq = hits.filter((h) => {
    const key = `${h['序列号']}|${h['出库单号']}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).sort((a, b) => String(b['出库日期']).localeCompare(String(a['出库日期'])));

  if (!uniq.length) return failed('EMPTY_RESULT', `近 ${days} 天没找到序列号 ${o.sn}。`, {
    what_to_do: `把 days 调大再查一次（最多 ${MAX_DAYS} 天）；如果还是没有，可能是这台机器出库时间更早，或者没录唯一码。`,
  });
  const h = uniq[0];
  let summary = `序列号 ${h['序列号']} 查到 ${uniq.length} 条出库记录：${h['出库日期']} 出库，订单 ${h['订单号']}，${h['物流公司'] || '未填物流公司'} 物流单号 ${h['物流单号'] || '（无）'}。`;
  let csvPath = '';
  if (o.csv) {
    csvPath = writeCsv(o.csv === true ? defaultCsv('序列号反查') : o.csv,
      ['序列号', '出库日期', '出库单号', '订单号', '商品编码', '成本价', '物流公司', '物流单号', '出库状态', '店铺'], uniq);
    summary += ' 已导出到 ' + csvPath;
  }
  return answer('序列号反查', summary, uniq,
    [`按销售出库单的「修改时间」分 7 天一段往前查了 ${days} 天，不是按出库日期。`,
     '序列号支持只输后几位模糊匹配；同一个 SN 只留一条。',
     '序列号挂在出库单主表上，订单接口里查不到。'], csvPath);
}

// ---------------------------------------------------------------------------
// 场景：通用单据查询（覆盖固定场景之外的全部查询接口）
// ---------------------------------------------------------------------------
function pickColumns(rows) {
  if (!rows.length || typeof rows[0] !== 'object') return [];
  const scalar = Object.keys(rows[0]).filter((k) => {
    const v = rows[0][k];
    return v !== null && typeof v !== 'object';
  });
  const names = scalar.map((k) => FIELD_CN[k] || k);
  const head = PREFERRED.filter((n) => names.includes(n));
  const tail = names.filter((n) => !PREFERRED.includes(n)).sort();
  return head.concat(tail).slice(0, 18);
}

function scQuery(o) {
  const action = String(o.action || '').trim();
  if (!action) return failed('BAD_PARAMS', '要给我一个接口名。', {
    usage: 'query --action refund_single_query [--days 7] [--csv 路径]',
    what_to_do: '先跑 find 关键词 找接口名，例如 find 售后。',
  });
  const catalog = allActions();
  if (!Object.keys(catalog).length) return failed('CATALOG_MISSING', '接口清单没找到，这个技能可能没装全。');
  const meta = catalog[action] || {};
  if (!meta.name && !meta.kind) return failed('ACTION_NOT_ALLOWED', `接口 ${action} 没登记在清单里，只读版不允许调用。`, {
    what_to_do: `跑 find ${action} 看看有没有名字相近的查询接口。`,
  });
  if (meta.kind !== 'query') return failed('READONLY_MODE', `「${meta.name || action}」是修改数据的操作，只读版已经拦下了。`);

  const days = Math.max(1, o.days || 7);
  const { rows, err } = segmented(action, {}, days);
  const g = guideFor(err);
  if (g) return failed(g.status, g.title, { what_to_do: g.what_to_do });
  if (err) return failed('QUERY_FAILED', `查 ${meta.name || action} 没成功。`);

  const seen = new Set();
  const uniq = rows.filter((r) => {
    const key = JSON.stringify(r);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  const cols = pickColumns(uniq);
  const rawOf = {};
  if (uniq.length) for (const k of Object.keys(uniq[0])) rawOf[FIELD_CN[k] || k] = k;
  const picked = cols.length ? uniq.map((r) => {
    const out = {};
    for (const c of cols) out[c] = r[rawOf[c] ?? c] ?? '';
    return out;
  }) : [];

  const title = meta.name || action;
  let summary = `${title}：近 ${days} 天查到 ${picked.length} 条记录`;
  summary += picked.length ? '。' : '，这段时间没有数据，可以把 days 调大一点再试。';
  let csvPath = '';
  if (o.csv) {
    csvPath = writeCsv(o.csv === true ? defaultCsv(title) : o.csv, cols, picked);
    summary += ' 已导出到 ' + csvPath;
  }
  return answer(title, summary, picked,
    [`按「修改时间」分 7 天一段往前查了 ${days} 天，接口一次最多查 7 天。`,
     '只显示主要字段（最多 18 列）；要全部字段请用精细查询。',
     '这是只读查询，不会改动 ERP 里的任何单据。'], csvPath);
}

function scFind(o) {
  const kw = String(o.keyword || '').trim().toLowerCase();
  const hits = [];
  for (const [key, meta] of Object.entries(allActions())) {
    const text = `${key} ${meta.name || ''} ${meta.domain || ''}`.toLowerCase();
    if (!kw || text.includes(kw)) hits.push({
      '接口': key, '名称': meta.name || '', '分类': meta.domain || '',
      '能不能用': meta.kind === 'query' ? '可查询' : '只读版不允许',
    });
  }
  hits.sort((x, y) => (x['能不能用'] !== '可查询') - (y['能不能用'] !== '可查询')
    || String(x['分类']).localeCompare(String(y['分类'])) || String(x['接口']).localeCompare(String(y['接口'])));
  const usable = hits.filter((h) => h['能不能用'] === '可查询').length;
  return answer('找接口', `找到 ${hits.length} 个接口，其中 ${usable} 个可以查（其余是写操作，只读版拦下了）。`, hits,
    ['构造参数前先让我读一次这个接口的说明，确认必填项和时间跨度限制。']);
}

function scList() {
  const rows = (SCENARIOS.scenarios || []).map((s) => ({
    '场景': s.name, '命令': s.usage, '用户会这么问': (s.ask || []).join('、'), '能拿到什么': s.what,
  }));
  return answer('能问什么', `一共 ${rows.length} 个常用场景，直接说业务问题就行，我会挑合适的场景。`, rows, SCENARIOS.tips || []);
}

// ---------------------------------------------------------------------------
// 命令行
// ---------------------------------------------------------------------------
function parse(argv) {
  const o = { scene: argv[0] || 'list', days: undefined, keyword: '', low: undefined,
    id: '', sn: '', action: '', csv: undefined };
  for (let i = 1; i < argv.length; i++) {
    const a = argv[i];
    const next = () => (i + 1 < argv.length && !argv[i + 1].startsWith('--') ? argv[++i] : undefined);
    if (a === '--days') o.days = Number(next() || 7);
    else if (a === '--keyword') o.keyword = next() || '';
    else if (a === '--low') o.low = Number(next() || 0);
    else if (a === '--id') o.id = next() || '';
    else if (a === '--sn') o.sn = next() || '';
    else if (a === '--action') o.action = next() || '';
    else if (a === '--csv') o.csv = next() ?? true;
    else if (!a.startsWith('--') && o.scene === 'find') o.keyword = a;
  }
  return o;
}

const SCENES = {
  list: scList, shops: scShops, stock: scStock, pending: scPending,
  serials: scSerials, order: scOrder, overview: scOverview, find: scFind,
  sn: scSn, query: scQuery,
};

function main() {
  const o = parse(process.argv.slice(2));
  const fn = SCENES[o.scene];
  if (!fn) return failed('BAD_PARAMS', `不认识的场景「${o.scene}」。`, { usage: Object.keys(SCENES).join('、') });
  if (o.days && o.days > MAX_DAYS) return failed('BAD_PARAMS', `一次最多往前查 ${MAX_DAYS} 天，你填了 ${o.days} 天。`, {
    what_to_do: '把 days 改小一点，或者分几次查；已经查过的结果不会丢。',
  });
  if (o.scene === 'list' || o.scene === 'find') return fn(o);
  const state = ensureReady();
  if (!state.ok) {
    say({ ok: false, status: state.status, title: state.title, what_happened: state.what_happened,
      what_to_do: state.what_to_do, who: state.who, url: state.url,
      success_check: state.success_check, hint: '先做完这一步，再重新问一遍。' });
    return 2;
  }
  return fn(o);
}

process.exit(main());
