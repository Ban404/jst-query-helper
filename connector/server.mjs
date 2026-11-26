#!/usr/bin/env node
/**
 * 聚水潭查询助手 · 连接器服务端（可选增强版）
 *
 * 技能市场包不需要它也能独立工作；这份是给启用连接器的企业用户用的。
 * 两者共用同一份 guide.json 引导文案，以及水宝自带的同一个查询程序。
 *
 * 只用 Node 标准库，不装 npm 包、不装 Python、包内不放第三方二进制。
 */

import readline from 'node:readline';
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createCore } from './core.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const core = createCore(HERE);
const GUIDE = core.guide;
const PROTOCOL = '2025-06-18';
const { homes: shuibaoHomes, tokenInfo, claimsOf, isReadOnly, findCli,
        runCli, listActionsFromCli: allActions, revisionOf, clearRevision, hintFor } = core;

function actionInfo(action) {
  return core.readActionCatalog()[action] || null;
}

// ---------------------------------------------------------------------------
// 体检：5 项按顺序，停在第一项没过的
// ---------------------------------------------------------------------------
async function check() {
  const checks = [];
  const names = GUIDE.checks || [];
  const add = (step, ok, detail) => checks.push({
    step, name: names[step - 1] || '', ok, detail,
  });
  const finish = (status, extra = {}) => {
    const s = GUIDE.statuses[status] || {};
    return {
      ok: status === 'READY', status, stage: s.stage || 0,
      title: s.title || '', what_happened: s.what_happened || '',
      what_to_do: s.what_to_do || '', who: s.who || '',
      url: s.url || '', success_check: s.success_check || '',
      can_ai_do: !!s.can_ai_do, checks, readonly: isReadOnly(), ...extra,
    };
  };

  const installed = shuibaoHomes().some((h) => existsSync(h.home));
  add(1, installed, installed ? '已安装' : '没找到水宝的数据目录');
  if (!installed) return finish('SHUIBAO_MISSING');

  const token = tokenInfo();
  add(2, !!token, token ? '已登录' : '还没登录过');
  if (!token) return finish('SHUIBAO_NOT_LOGGED_IN');

  const exe = findCli();
  add(3, !!exe, exe ? '水宝自带，可用' : '还没释放到本机');
  if (!exe) return finish('CLI_MISSING');

  const c = claimsOf(token);
  const exp = c.exp;
  const expired = typeof exp === 'number' && exp <= Date.now() / 1000;
  const expireText = typeof exp === 'number' ? new Date(exp * 1000).toLocaleString('zh-CN') : '未知';
  add(4, !expired, expired ? `已于 ${expireText} 过期` : `有效至 ${expireText}`);
  const common = { account: { company: c.co_name || '', user: c.u_name || '' }, token_expires_at: expireText };
  if (expired) return finish('TOKEN_EXPIRED', common);

  const probe = runCli(['list_connections'], token);
  const code = (probe.error || {}).code || '';
  if (!probe.ok && code !== 'AUTH_REQUIRED') {
    add(5, false, '连接失败：' + (code || '未知原因'));
    return finish('TOKEN_REJECTED', { ...common, detail: code });
  }
  add(5, !!probe.ok, probe.ok ? '已授权' : '未完成授权');
  if (!probe.ok) return finish('NOT_AUTHORIZED', { ...common, authorize_url: (probe.data || {}).authorize_url || '' });

  return finish('READY', common);
}

// ---------------------------------------------------------------------------
// 工具
// ---------------------------------------------------------------------------
const TOOLS = [
  { name: 'jst_check', description: '环境体检。每次会话第一次使用、或任何查询报错时必须先调。返回还差哪一步和可直接讲给用户听的话。', inputSchema: { type: 'object', properties: {}, required: [] } },
  { name: 'jst_setup', description: '返回完整的新手安装清单：下载链接、需要本人做的 3 步、成功标准、常见事实。不联网。', inputSchema: { type: 'object', properties: {}, required: [] } },
  { name: 'jst_domains', description: '列出可查询的业务分类（12 类）。', inputSchema: { type: 'object', properties: {}, required: [] } },
  { name: 'jst_actions', description: '列出可查询的接口。指定 domain 就只列该分类；不填则自动遍历全部 12 个分类汇总。新版水宝要求按分类读取，这里已自动处理。', inputSchema: { type: 'object', properties: { domain: { type: 'string', description: '例如「库存」「订单」；留空表示全部' } }, required: [] } },
  { name: 'jst_fields', description: '查看某接口需要哪些参数、返回哪些字段。构造参数前必须先调。', inputSchema: { type: 'object', properties: { action: { type: 'string' } }, required: ['action'] } },
  { name: 'jst_query', description: '执行一次原始查询。只允许已登记的查询类接口，其余一律拦截。', inputSchema: { type: 'object', properties: { action: { type: 'string' }, params: { type: 'string', description: '参数的 JSON 字符串' } }, required: ['action'] } },
  { name: 'jst_ask', description: '一句话问业务问题，直接拿到整理好的中文结论。场景：overview 经营概览、pending 待发货订单、serials 已发货序列号、sn 序列号反查、stock 库存速查、order 单笔订单追查、shops 店铺列表、query 其他单据查询（覆盖全部 36 个查询接口）、find 找接口、list 能问什么。会自动分段、翻页、聚合，可导 CSV。', inputSchema: { type: 'object', properties: {
    scene: { type: 'string', description: 'overview / pending / serials / sn / stock / order / shops / query / find / list' },
    days: { type: 'number', description: '往前查多少天，默认 7；pending 和 serials 默认 30，sn 默认 90；最多 180' },
    keyword: { type: 'string', description: 'stock 的商品关键词，或 find 的接口关键词' },
    low: { type: 'number', description: 'stock 只看可用库存不超过这个数' },
    id: { type: 'string', description: 'order 用的订单号' },
    sn: { type: 'string', description: 'sn 场景用的产品序列号，可只填后几位' },
    action: { type: 'string', description: 'query 场景用的接口名，可先用 find 找' },
    csv: { type: 'string', description: '导出 CSV 的文件名，留空则不导出' },
  }, required: ['scene'] } },
];

async function dispatch(name, args) {
  const text = (obj) => JSON.stringify(obj, null, 2);

  if (name === 'jst_check') return text(await check());
  if (name === 'jst_setup') {
    return text({
      product: GUIDE.product,
      download: GUIDE.shuibao_download,
      intro: GUIDE.shuibao_intro,
      steps: GUIDE.setup_steps,
      facts: GUIDE.facts,
      how_to_check: '调用 jst_check',
    });
  }

  // 一问一答：交给包内 ask.mjs 跑，它自己会体检、分段、翻页，返回中文结论
  if (name === 'jst_ask') {
    const cli = ['ask.mjs', String(args.scene || 'list')];
    if (args.days) cli.push('--days', String(Number(args.days)));
    if (args.keyword) cli.push('--keyword', String(args.keyword));
    if (args.low !== undefined && args.low !== null && args.low !== '') cli.push('--low', String(args.low));
    if (args.id) cli.push('--id', String(args.id));
    if (args.sn) cli.push('--sn', String(args.sn));
    if (args.action) cli.push('--action', String(args.action));
    if (args.csv) cli.push('--csv', String(args.csv));
    const r = spawnSync(process.execPath, cli, {
      cwd: HERE, encoding: 'utf8', timeout: 300000, windowsHide: true,
      env: process.env, maxBuffer: 16 * 1024 * 1024,
    });
    const out = String(r.stdout || '').trim();
    return out || text({ ok: false, error: { code: 'NO_OUTPUT', message: String(r.stderr || '场景程序没有返回内容').slice(0, 300) } });
  }

  const state = await check();
  if (!state.ok) {
    return text({
      ok: false, status: state.status, title: state.title,
      what_happened: state.what_happened, what_to_do: state.what_to_do,
      who: state.who, url: state.url,
      hint: '请先按上面这一步做完，再重新查。',
    });
  }

  const token = tokenInfo();
  if (name === 'jst_domains') return text(runCli(['list_domains'], token));
  if (name === 'jst_actions') {
    const domain = String(args.domain || '').trim();
    // 水宝 2.0.611181 起 list_actions 必须按分类读；不填分类时自动遍历 12 个域再合并
    return text(domain ? runCli(['list_actions', '--domain', domain], token) : allActions(token));
  }
  if (name === 'jst_fields') return text(runCli(['describe_action', '--action', String(args.action || '')], token));

  if (name === 'jst_query') {
    const action = String(args.action || '');
    // 只读白名单：只有登记为 query 的接口才放行，写操作和来路不明的接口一律挡下
    const meta = actionInfo(action);
    if (isReadOnly() && (!meta || meta.kind !== 'query')) {
      const write = meta && meta.kind === 'write';
      const code = write ? 'READONLY_MODE' : 'ACTION_NOT_ALLOWED';
      return text({
        ok: false,
        error: {
          code,
          message: write ? `「${meta.name || action}」是修改数据的操作，只读版已经拦下了。` : `「${action}」不是允许查询的接口。`,
          what_to_do: hintFor(code),
        },
      });
    }
    let params = args.params;
    if (params && typeof params === 'object') params = JSON.stringify(params);
    if (!params) params = '{}';
    const base = ['invoke', '--action', action, '--params', String(params)];
    let rev = revisionOf(action, token);
    let result = rev ? runCli([...base, '--schema_revision', rev], token) : runCli(base, token);
    const code = (result.error || {}).code || '';
    if (rev && ['SCHEMA_PREFLIGHT_REQUIRED', 'SCHEMA_REVISION_MISMATCH'].includes(code)) {
      clearRevision(action);
      const fresh = revisionOf(action, token);
      if (fresh) result = runCli([...base, '--schema_revision', fresh], token);
    }
    // 只读被显式关掉时明确标注，别让用户以为还受保护
    if (!isReadOnly()) {
      result = { ...result, readonly: false, readonly_warning: '只读保护已关闭（JST_ALLOW_WRITE=1 或 READONLY 标记缺失），写操作可能真实改动 ERP。' };
    }
    return text(result);
  }

  throw new Error('不认识的工具：' + name);
}

// ---------------------------------------------------------------------------
// MCP 对话：一行进、一行出
// ---------------------------------------------------------------------------
function reply(id, result) { return { jsonrpc: '2.0', id, result }; }

async function handle(msg) {
  const { id, method, params } = msg;
  if (method === 'initialize') {
    return reply(id, {
      protocolVersion: PROTOCOL,
      capabilities: { tools: { listChanged: false } },
      serverInfo: { name: 'jst-helper', version: '5.0.1' },
    });
  }
  if (method === 'ping') return reply(id, {});
  if (method === 'tools/list') return reply(id, { tools: TOOLS });
  if (method === 'tools/call') {
    try {
      const text = await dispatch(params.name, params.arguments || {});
      return reply(id, { content: [{ type: 'text', text }], isError: false });
    } catch (e) {
      return reply(id, { content: [{ type: 'text', text: String(e.message || e) }], isError: true });
    }
  }
  if (!method || method.startsWith('notifications/')) return null;
  return { jsonrpc: '2.0', id, error: { code: -32601, message: '不支持的方法：' + method } };
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
rl.on('line', (line) => {
  if (!line.trim()) return;
  let msg;
  try { msg = JSON.parse(line); } catch { return; }
  Promise.resolve(handle(msg)).then((out) => {
    if (out) process.stdout.write(JSON.stringify(out) + '\n');
  });
});
