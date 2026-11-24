# 聚水潭查询助手 · 通用 MCP Server

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Node 18+](https://img.shields.io/badge/node-18%2B-green.svg)](https://nodejs.org)

一句话查聚水潭 ERP：库存、待发货订单、发货序列号、单笔订单、经营情况，直接拿到整理好的中文结论。**全程只读，不会改动 ERP 里的任何单据。**

这是一个**标准 MCP Server**，遵守 MCP 协议（`2025-06-18`），通过 stdio 运行。它不属于任何特定 AI 平台——**Claude Desktop、Cursor、Cline、Windsurf，或任何支持 MCP 的客户端都能接入**。

> 非官方社区工具，与聚水潭、聚捷云、水宝官方无隶属或背书关系。使用前请读仓库根目录的 [免责声明](../DISCLAIMER.md) 与 [安全策略](../SECURITY.md)。

[English](README.en.md) · [客户端配置示例](config-examples.json) · [仓库首页](../README.md)

---

## 三套交付形态，选一套就行

本项目有三个独立发行包，功能相同、话术一致，只是接入方式不同：

| 套装 | 目录 | 用在 | 运行时 | 适合谁 |
| --- | --- | --- | --- | --- |
| 技能包 | `skill/` | 通用 AI 助手技能 | Python | 个人用户，装上就能用 |
| 连接器包 | `connector/` | MCP 连接器 | Node | 想要 MCP 工具的企业用户 |
| **通用 MCP 包**（本包） | `mcp/` | 任意 MCP 客户端 | Node 18+ | Claude Desktop / Cursor / Cline 等用户 |

三套共用同一份接口清单、引导文案和场景定义，说出来的话完全一样。本包是给**标准 MCP 客户端**用的，可对接 WorkBuddy、Goodax、DeepSeek、Harness 等各类 AI 助手。

---

## 用之前要满足三个前提

这个工具不绕过任何登录或授权。聚水潭是私有 ERP，账号、登录、授权三道门必须本人完成：

1. 你自己有聚水潭账号（找公司开通，本工具帮不了）；
2. 本机装了[水宝客户端](https://jxy.ai/download)并用自己的账号登录；
3. 本人在水宝「连接管理」里给聚水潭点过一次授权。

装好并授权后，水宝可以关掉，查询照常工作。**登录凭据约 7 天过期**，重新登录即可，授权不用再做。接好后让客户端先调用 `jst_check` 体检，它会告诉你还差哪一步、具体怎么操作。

---

## 接入客户端

先解压本包，记下解压后的**绝对路径**（例：`/Users/me/mcp/jst-query-mcp/server.mjs` 或 `D:\mcp\jst-query-mcp\server.mjs`）。

在客户端的 MCP 配置里加一段（`config-examples.json` 里有各客户端的完整样例）：

```json
{
  "mcpServers": {
    "jst-query": {
      "command": "node",
      "args": ["<本包解压目录>/server.mjs"]
    }
  }
}
```

各客户端配置文件通常在这里：

| 客户端 | 配置文件 |
| --- | --- |
| Claude Desktop（macOS） | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop（Windows） | `%APPDATA%\Claude\claude_desktop_config.json` |
| Cursor | 设置 → MCP → Add new global MCP server |
| Cline | 扩展设置 → MCP Servers → Configure |
| Windsurf | 设置 → MCP → Add server |

保存后**重启客户端**。首次对话先让它调用 `jst_check`，按返回的话做完安装 / 登录 / 授权，再开始查数据。

> 发布到 npm 后也能免安装启动：`command` 填 `npx`，`args` 填 `["-y", "jst-query-mcp"]`，不用写本地路径。

可选环境变量（一般不填）：

- `JST_CLI_PATH`：查询程序的绝对路径，不填则自动在水宝目录里找；
- `JXY_TOKEN`：登录凭据，不填则自动从本机水宝配置读取（**不要把真实 token 写进配置文件**）；
- `JST_ALLOW_WRITE`：设为 `1` 才解除只读白名单，普通用户无需设置。

---

## 可用工具（7 个）

| 工具 | 什么时候用 | 参数 |
| --- | --- | --- |
| `jst_check` | **每次会话第一次**、任何查询报错、用户说「装好了」时 | 无 |
| `jst_setup` | 问「怎么装」「要几步」 | 无（不联网，返回下载链接、本人要做的 3 步、成功标准） |
| `jst_domains` | 想知道有哪些业务分类 | 无（返回 12 类） |
| `jst_actions` | 找有哪些接口 | `domain`：中文分类名如「库存」；留空自动汇总全部 12 个域 |
| `jst_fields` | 构造参数前**必调** | `action`：接口名 |
| `jst_query` | 场景没覆盖时的原始查询 | `action`：接口名；`params`：参数的 JSON 字符串 |
| `jst_ask` | **优先用**，一句话问业务问题 | `scene`（必填）+ 可选 `days` `keyword` `low` `id` `sn` `action` `csv` |

`jst_ask` 的 `scene`：`overview` 经营概览、`pending` 待发货、`serials` 已发货序列号、`sn` 序列号反查、`stock` 库存速查、`order` 单笔订单、`shops` 店铺列表、`query` 其他单据、`find` 找接口、`list` 能问什么。`days` 最多 180。

**给 AI 的三条铁律**（接入后建议写进客户端的系统提示）：

1. 每次会话第一次用，先调 `jst_check`，不管用户问什么；
2. 一次只推进一步，把 `what_to_do` 原样讲给用户，附 `url` 和 `success_check`，停下等他说「好了」；
3. 用户说「好了」必须重新调 `jst_check`，只有 `status: READY` 才允许查数据。

就绪后优先用 `jst_ask` 一句话问，不要自己拼参数、写循环、翻原始 JSON。固定场景没覆盖时先 `find` 找接口名，再 `query` 带 `action`，这样 36 个查询接口全部能问。返回的 `summary` 可以直接念给用户听。

---

## 只能查，不能改

只有已登记的 **36 个查询接口**放行；53 个写操作（发货、审核、取消订单、改备注等）和任何没登记的接口都会被拦下，返回 `READONLY_MODE` / `ACTION_NOT_ALLOWED`。包内 `data/READONLY` 是只读标记，删掉它或设 `JST_ALLOW_WRITE=1` 才能解除——普通用户不该这么做。

---

## 目录结构

```
mcp/
├── package.json          npm 元数据（可 npm publish / npx）
├── server.mjs            MCP Server（stdio，标准 JSON-RPC）
├── ask.mjs               一问一答场景引擎
├── guide.json            首次使用引导文案
├── scenarios.json        场景定义
├── config-examples.json  各客户端配置示例
├── data/
│   ├── actions.json      接口清单（89：36 查询 / 53 写入）
│   ├── READONLY          只读标记
│   └── domains/          12 份业务域说明
├── README.md / README.en.md
├── LICENSE / CHANGELOG.md
└── icon.svg
```

`server.mjs` / `ask.mjs` / `guide.json` / `scenarios.json` 由 `tools/sync_core.py` 从连接器内核同步生成；`data/` 由 `tools/build.py` 注入。改内核后跑一次同步与打包即可。

---

## 开发者自测

不需要水宝、网络或凭据：

```bash
npm run check                    # Node 语法检查
python tools/verify_offline.py   # 三套结构 / 脱敏 / 只读 / 打包（仓库根目录）
```

需要真实查数据（装好水宝并授权后）：

```bash
python tools/verify_online.py    # 真实查询 + 通用 MCP Server 握手
```

---

## 许可

[MIT](LICENSE)。聚水潭 / 水宝 / 聚捷云的名称与商标归各自权利人所有。
