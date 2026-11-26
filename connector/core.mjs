#!/usr/bin/env node
/**
 * 聚水潭查询助手 · Node 共享内核
 *
 * connector/ask.mjs 与 connector/server.mjs 共用这里的水宝定位、登录凭据、
 * 只读开关、CLI 调用和话术展开，避免两份实现各写一遍导致行为漂移。
 * 通用 MCP 包由 tools/sync_core.py 从本文件生成 mcp/core.mjs（只改资源路径）。
 * 只用 Node 标准库。
 */

import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';

/** 递归展开 {{key}} 占位符，值本身带占位符也能展开（最多 5 轮）。 */
export function expandText(obj, values) {
  if (Array.isArray(obj)) return obj.map((v) => expandText(v, values));
  if (obj && typeof obj === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(obj)) out[k] = expandText(v, values);
    return out;
  }
  if (typeof obj !== 'string' || !obj.includes('{{')) return obj;
  let text = obj;
  for (let i = 0; i < 5; i += 1) {
    let hit = false;
    for (const [k, v] of Object.entries(values)) {
      const token = `{{${k}}}`;
      if (text.includes(token)) {
        text = text.split(token).join(String(v));
        hit = true;
      }
    }
    if (!hit) break;
  }
  return text;
}

/**
 * 以包所在目录为基准创建一套内核。两个入口各自传入 HERE，
 * 因此 mcp/ 生成版只需替换本文件里的资源路径，入口文件不用改。
 */
export function createCore(here) {
  const ACTIONS_FILE = path.join(here, 'jst', 'scripts', 'actions.json');
  const READONLY_FILE = path.join(here, 'jst', 'READONLY');
  const CONFIG_FILE = path.join(here, 'config.json');
  const GUIDE_FILE = path.join(here, 'guide.json');
  const SCENARIOS_FILE = path.join(here, 'scenarios.json');
  const revisions = new Map();

  const readJson = (file, fallback) => {
    try { return JSON.parse(readFileSync(file, 'utf8')); } catch { return fallback; }
  };

  // 引导文案：网址和公共话术在这里展开，业务代码拿到的就是最终文本。
  const guideRaw = readJson(GUIDE_FILE, {});
  const guideValues = {
    download: guideRaw.shuibao_download || '',
    intro: guideRaw.shuibao_intro || '',
    ...(guideRaw.phrases || {}),
  };
  const guide = expandText(guideRaw, guideValues);

  // 场景配置：状态词占位符在这里展开；{{days}} 留到场景按本次天数填。
  const scenarioRaw = readJson(SCENARIOS_FILE, {});
  const statusValues = {};
  for (const [k, v] of Object.entries(scenarioRaw.status_words || {})) {
    statusValues[`status_${k}`] = v;
  }
  const scenarios = expandText(scenarioRaw, statusValues);

  const notesFor = (scene, days) => {
    const raw = (scenarios.scene_notes || {})[scene];
    if (!raw) return [];
    const list = Array.isArray(raw) ? raw : [raw];
    return days == null ? list.slice() : list.map((s) => String(s).split('{{days}}').join(String(days)));
  };

  const hintFor = (code) => {
    const errors = guide.errors || {};
    return errors[code] || errors._default || '稍后再试，或换个说法让我查别的内容。';
  };

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
    const own = path.join(here, 'jst', rel);
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
    // 包内 config.json 是装不了水宝时的兜底（正常分发不含此文件）
    if (existsSync(CONFIG_FILE)) {
      try {
        const cfg = JSON.parse(readFileSync(CONFIG_FILE, 'utf8'));
        const t = straighten(cfg.jxy_token || cfg.token || '');
        if (t) return t;
      } catch { /* 配置文件坏了就继续找水宝 */ }
    }
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

  function isReadOnly() {
    return process.env.JST_ALLOW_WRITE !== '1' && existsSync(READONLY_FILE);
  }

  /** 读包内接口清单（一问一答版用） */
  function readActionCatalog() {
    try { return JSON.parse(readFileSync(ACTIONS_FILE, 'utf8')).actions || {}; }
    catch { return {}; }
  }

  function runCli(args, token) {
    const exe = findCli();
    if (!exe) return { ok: false, error: { code: 'CLI_MISSING', message: '查询程序未就绪' } };
    const r = spawnSync(exe, [...args, '--json'], {
      encoding: 'utf8', timeout: 90000, windowsHide: true, maxBuffer: 32 * 1024 * 1024,
      env: { ...process.env, JXY_TOKEN: token || tokenInfo() },
    });
    // 超时要有自己的语义，别降级成 NO_OUTPUT，否则引导话术对不上
    if (r.error && r.error.code === 'ETIMEDOUT') {
      return { ok: false, error: { code: 'TIMEOUT', message: '查询超时，稍后再试' } };
    }
    if (r.error) {
      return { ok: false, error: { code: 'CLI_ERROR', message: String(r.error.message || r.error).slice(0, 200) } };
    }
    const out = String(r.stdout || '').trim();
    if (!out) {
      return { ok: false, error: { code: 'NO_OUTPUT', message: String(r.stderr || '查询程序没有返回内容').slice(0, 300) } };
    }
    try { return JSON.parse(out); } catch { return { ok: false, raw_output: out.slice(0, 2000) }; }
  }

  /** 向 CLI 实时列接口（常驻 MCP 服务用；新版 list_actions 必须带 --domain） */
  function listActionsFromCli(token) {
    const dom = runCli(['list_domains'], token);
    if (!dom.ok) return dom;
    const names = (dom.data || []).filter((x) => x && x.domain).map((x) => x.domain);
    const rows = [];
    for (const name of names) {
      const res = runCli(['list_actions', '--domain', name], token);
      if (!res.ok) return res;
      for (const it of (res.data || [])) rows.push({ domain: name, ...it });
    }
    return { ok: true, data: rows, count: rows.length, domains: names.length };
  }

  function revisionOf(action, token) {
    if (revisions.has(action)) return revisions.get(action);
    const data = runCli(['describe_action', '--action', action], token).data || {};
    const rev = data.schema_revision || (data.schema_contract || {}).schema_revision;
    if (rev) revisions.set(action, rev);
    return rev;
  }

  function clearRevision(action) {
    revisions.delete(action);
  }

  return {
    guide, scenarios, notesFor, hintFor,
    homes, cliRel, walkFor, findCli, looksLikeJwt, straighten, tokenInfo, claimsOf,
    isReadOnly, readActionCatalog, runCli, listActionsFromCli, revisionOf, clearRevision,
  };
}
