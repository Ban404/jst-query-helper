# 架构说明

## 一句话

围绕「私有 ERP 的账号/登录/授权绕不过去」这个事实设计：**不绕过任何东西，只复用本机已完成的登录态和官方客户端自带的查询程序，做只读查询。**

## 数据流

```
用户（大白话）
    │
    ▼
AI 助手（WorkBuddy / Goodax / DeepSeek / Harness 等）
    │  读 SKILL.md 决定怎么走
    ▼
skill/scripts/ask.py  ──场景引擎──┐         connector/server.mjs (MCP 工具)
    │                            │                    │
    │ 统一体检                    │                    │
    ▼                            ▼                    ▼
skill/scripts/jst.py          guide.json /       connector/ask.mjs
    │  底层：找凭据、找程序、      scenarios.json       (同一套场景，Node 版)
    │  补版本号、翻页、分段         （话术唯一来源）
    ▼
水宝自带查询程序 jst-open-platform(.exe)
    │  带本机已登录的 token
    ▼
聚水潭 ERP（仅查询接口）
    │
    ▼
中文结论 + 表格 + 可选 CSV
```

## 三个入口，一套逻辑

| | 技能包 `skill/` | 连接器 `connector/` | 通用 MCP `mcp/` |
| --- | --- | --- | --- |
| 语言 | Python 3.8+ | Node 18+ | Node 18+ |
| 入口 | `jst.py`（底层）+ `ask.py`（场景） | `server.mjs`（MCP）+ `ask.mjs`（场景） | `server.mjs`（MCP）+ `ask.mjs`（场景） |
| 给谁 | 普通用户，装上就能用 | 想要 MCP 工具的企业用户 | Claude Desktop / Cursor / Cline 等任意 MCP 客户端 |
| 运行时 | Python 3.8+ | Node 18+ | 用户本机 Node 18+ |
| 发布 | 通用 AI 助手技能 | MCP 连接器 | npm / zip 下载 |

**保持一致的机制**：引导话术只在 `guide.json`、场景清单只在 `scenarios.json`、接口清单只在 `catalog/actions.json`。`tools/sync_core.py` 从连接器内核生成通用 MCP 包的 `server.mjs` / `ask.mjs`（只改资源路径），`tools/build.py` 再把三份清单分别复制进三个包。离线自检逐字比对，CI 还会校验 MCP 内核是否与连接器同步。改一处、三边同步。三套各自带中英 README、LICENSE、CHANGELOG，可独立发布。

## 关键组件

- **体检状态机**：`jst.py:cmd_doctor()` / `server.mjs:check()`。按顺序查 5 项：水宝装了没 → 登录了没 → 查询程序在不在 → 凭据过期没 → 授权了没。停在第一项没过的，返回可直接念给用户听的话（`what_to_do`/`who`/`url`/`success_check`）。
- **凭据复用**：`jst.py:resolve_token()`。优先环境变量 → 包内 `config.json`（不分发）→ 本机水宝配置。上游把 JWT 整体倒序落盘，`normalize_token()` 自动翻正。只读，不上传，不落盘到包目录。
- **查询程序查找**：`find_cli()` 有 5 级回退（显式环境变量 → 包内 → 水宝技能目录 → 旧技能 → 全目录搜索），应对上游目录结构变化。
- **接口版本号**：上游查询要求 `schema_revision` 预检。脚本从 `describe_action` 取版本号、缓存在系统临时目录、过期自动刷新重试一次（Python 落盘缓存，Node 常驻内存）。
- **只读白名单**：`catalog/actions.json` 登记 89 个接口（36 query / 53 write）。入口只放行 `kind=query`，其余返回 `READONLY_MODE` / `ACTION_NOT_ALLOWED`。`READONLY` 标记文件是第二道锁。
- **场景引擎**：`ask.py` / `ask.mjs`。9 个内置场景 + 通用 `query`。自动把长区间切成 7 天一段（接口限制）、自动翻页、从 `raw_data_path` 读大结果、英文字段翻中文、最多显示 50 行、可导 UTF-8 BOM 的 CSV。

## 目录约定

```
catalog/          接口清单 + 领域说明（三套唯一真源，由 refresh_catalog.py 生成）
skill/            【套装①】技能包源码（Python，自包含）
connector/        【套装②】连接器包源码（Node，自包含）
mcp/              【套装③】通用 MCP 包源码（Node，自包含，可 npm 发布）
tools/            build / sync_core / refresh_catalog / verify_offline / verify_online / scan_secrets
tests/            离线单元测试（pytest）
docs/             快速开始 / 架构 / FAQ / 场景 / 上架 / 识别报告
dist/             打包产物（gitignore，用 build.py 生成）
```

## 维护流程

1. 上游升级 → `python tools/refresh_catalog.py` 重新识别接口，对比差异；
2. 改话术 → 只改 `guide.json`；改场景 → 只改 `scenarios.json` + 引擎（Python 改 `ask.py`，Node 改连接器 `ask.mjs` 后跑 `sync_core.py` 同步到 MCP）；
3. 跑 `python tools/verify_offline.py` + `python -m pytest tests/ -q`；
4. 需要真实验证再跑 `python tools/verify_online.py`；
5. `python tools/build.py` 自动同步内核并重建三个 zip。

CI（`.github/workflows/ci.yml`）在多个 Python/Node 版本上自动跑离线自检、单元测试和隐私扫描。
