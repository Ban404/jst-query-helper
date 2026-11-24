# 聚水潭查询助手 · JST Query Helper

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-green.svg)](docs/QUICKSTART.zh-CN.md)
[![Node 18+](https://img.shields.io/badge/node-18%2B-green.svg)](docs/QUICKSTART.zh-CN.md)

用大白话查聚水潭 ERP：库存、待发货订单、发货序列号、单笔订单、经营情况，一句话出中文结论。
第一次使用会一步步引导你自己装好环境、登录、授权；全程只读，**不会改动 ERP 里的任何单据**。

> 本项目是**非官方社区工具**，与聚水潭、聚捷云、水宝官方无任何隶属或背书关系。使用前请读 [免责声明](DISCLAIMER.md)。

[English README](README.en.md) · [快速开始](docs/QUICKSTART.zh-CN.md) · [常见问题](docs/FAQ.zh-CN.md) · [架构说明](docs/ARCHITECTURE.zh-CN.md)

---

## 它能做什么

| 你说 | 它做 |
| --- | --- |
| 「今天生意怎么样」 | 待发货 / 已发货 / 取消几单，哪几款快没货 |
| 「有没有货要发」 | 列出待发货订单，并判断卡在没审核、缺货还是没出库单 |
| 「这个月发了哪些机器」 | 从销售出库单取出序列号清单，可导 Excel |
| 「客户报了个 SN，是哪单发的」 | 反查出库日期、订单号、物流单号、商品 |
| 「还有多少库存」 | 按商品名 / 库存阈值筛选 |
| 「这单发了吗」 | 订单详情 + 出库单 + 序列号一次查齐 |
| 「查售后退货退款 / 采购单 / 盘点单」 | 覆盖全部 **36 个只读查询接口**，字段自动翻成中文 |

- **9 个开箱场景** + 通用查询，覆盖全部 36 个查询接口；53 个写操作在代码层面被拦截。
- **自动处理脏活**：接口一次只能查 7 天→自动分段；多页→自动翻完；数据量大结果写成文件→自动读出来。
- **一次最多查 180 天**，超了给中文提示，不会傻跑。
- **结果能导 CSV**（UTF-8 BOM，Excel 双击不乱码）。

## 兼容的 AI 助手

这是一个**通用工具**，不绑定任何一家 AI 助手。下面这些平台都能用，方式略有不同：

| AI 助手 | 用哪一套 | 怎么接 |
| --- | --- | --- |
| **WorkBuddy** | 技能包 / 连接器包 | 技能市场装 `skill/`，或启用 MCP 连接器 |
| **Goodax** | 技能包 / 连接器包 | 按该平台的技能 / MCP 方式安装 |
| **DeepSeek** | 通用 MCP 包 | 在支持 MCP 的客户端里配置 `mcp/server.mjs` |
| **Harness** | 通用 MCP 包 | 同上，按平台 MCP 配置方式接入 |
| Claude Desktop / Cursor / Cline / Windsurf 等 | 通用 MCP 包 | 见 [`mcp/config-examples.json`](mcp/config-examples.json) |

无论用哪家助手，查的是同一份数据、走的是同一套只读逻辑、说的话也一样。具体安装步骤见 [快速开始](docs/QUICKSTART.zh-CN.md)。

## 它是怎么工作的

项目围绕一个关键事实设计：**聚水潭是私有 ERP，账号、登录、授权三道门绕不过去**。所以它不试图绕过任何东西，而是复用你本人在官方客户端（水宝）里已经完成的登录态和它自带的查询程序，只做只读查询。

```
你的问题 → 本项目的脚本 → 水宝自带的查询程序 → 聚水潭 ERP（只读）
                ↑
        复用你本人已登录、已授权的凭据（只在本机读取，不上传、不落盘）
```

**三个前提，缺一不可**：

1. 你自己有聚水潭账号（找公司开通，本项目帮不了）；
2. 你在本机装了水宝客户端并用自己的账号登录（提供凭据和查询程序）；
3. 你本人在水宝「连接管理」里给聚水潭点过一次授权。

装好并授权后，水宝可以关掉，查询照常工作。登录凭据约 7 天过期，重新登录即可，授权不用再做。

详细的组件关系见 [架构说明](docs/ARCHITECTURE.zh-CN.md)。

## 三套独立发行包

同一套只读查询内核，做成三套**各自独立、各自能上架/开源**的发行包。功能、话术、数据完全一致，只是接入方式不同，按需选一套：

| 套装 | 目录 | 上架到 | 运行时 | 适合谁 |
| --- | --- | --- | --- | --- |
| **① 技能包** | [`skill/`](skill/) | 通用 AI 助手技能 | Python 3.8+ | 个人用户，装上就能用 |
| **② 连接器包** | [`connector/`](connector/) | MCP 连接器 | Node 18+ | 想要 MCP 工具的企业用户 |
| **③ 通用 MCP 包** | [`mcp/`](mcp/) | npm / 任意 MCP 客户端 | Node 18+ | 任意 MCP 客户端用户 |

每一套都是完整自包含的一个目录：自带 README（中英）、LICENSE、CHANGELOG、免责声明引用和独立自检，单独拿出去就能发布。三套共用同一个接口清单 `catalog/`、同一份引导话术 `guide.json` 和场景清单 `scenarios.json`，由 `tools/sync_core.py` 保持内核一致，说法完全一样。打包脚本生成三个可直接上传的 zip，见 [打包与上架](docs/MARKETPLACE.zh-CN.md)。

仓库里**没有任何二进制文件**——查询程序由水宝安装后自带，本项目不分发、不捆绑第三方 exe。

## 快速开始

想直接用：看 [快速开始](docs/QUICKSTART.zh-CN.md)（面向完全不懂技术的人）。
想部署成技能 / 连接器：看 [打包与上架](docs/MARKETPLACE.zh-CN.md)。
想改代码：看 [贡献指南](CONTRIBUTING.md) 和 [本地开发](docs/ARCHITECTURE.zh-CN.md)。

开发者最小验证（**不需要装水宝、不需要联网、不需要任何凭据**）：

```bash
python tools/verify_offline.py     # 结构 / 脱敏 / 只读白名单 / 场景 / 打包，纯离线
```

需要真实查数据的验证（要装好水宝并授权）：

```bash
python tools/verify_online.py      # 真实查一次聚水潭 + 9 场景 + CSV 导出
```

## 目录结构

```
jst-query-helper/
├── README.md / README.en.md      项目说明（本文件 / 英文）
├── DISCLAIMER.md                 免责声明与非官方声明
├── SECURITY.md                   安全策略、凭据处理、漏洞报告
├── CONTRIBUTING.md / CHANGELOG.md
├── skill/                        【套装①】技能市场包（Python，自包含）
│   ├── SKILL.md                  给 AI 看的用法与三条铁律
│   ├── scripts/                  jst.py / ask.py / guide.json / scenarios.json / actions.json
│   ├── references/               首次使用剧本 + 12 份业务域说明
│   └── README.md / LICENSE / CHANGELOG.md
├── connector/                    【套装②】连接器市场包（Node，自包含）
│   ├── server.mjs / ask.mjs
│   ├── connector-meta.json / mcp.json / icon.svg
│   ├── skills/jst-helper/SKILL.md
│   ├── jst/                      只读白名单清单 + 业务域说明
│   └── README.md / LICENSE / CHANGELOG.md
├── mcp/                          【套装③】通用 MCP 包（Node，自包含，可 npm 发布）
│   ├── package.json / server.mjs / ask.mjs
│   ├── config-examples.json      各 MCP 客户端配置示例
│   ├── data/                     接口清单 + 只读标记 + 业务域说明
│   └── README.md / LICENSE / CHANGELOG.md
├── catalog/                      从水宝重新识别出的接口清单（89 个接口 / 12 个域，三套唯一真源）
├── tools/                        build.py / sync_core.py / refresh_catalog.py / verify_*.py
├── tests/                        离线单元测试（pytest）
└── docs/                         快速开始 / 架构 / FAQ / 上架 / 识别报告
```

## 边界与事实（如实在说）

- **做不到「装完立刻出数据」**：账号、本人登录、本人授权三道门绕不过去。能做到的是装好后全程在聊天里自助完成。
- **只读是代码强制的**：36 个查询接口白名单放行，53 个写操作和未登记接口一律拦下，返回 `READONLY_MODE` / `ACTION_NOT_ALLOWED`。
- **凭据只在本机读取**：不上传、不写进项目目录、不进 git；缓存只放系统临时目录。详见 [SECURITY.md](SECURITY.md)。
- **依赖外部客户端**：水宝的目录结构和查询程序不是对本项目承诺的接口，官方升级可能变化。本项目提供 `refresh_catalog.py` 重新识别，但无法保证永远兼容。
- **不支持查抖音后台**，只能查聚水潭 ERP。

## 许可

[MIT](LICENSE)。项目代码开源；聚水潭 / 水宝 / 聚捷云的名称与商标归各自权利人所有。使用前请读 [DISCLAIMER.md](DISCLAIMER.md)。
