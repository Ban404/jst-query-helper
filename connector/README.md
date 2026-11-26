# 聚水潭查询助手 · 连接器包

[![License: MIT](LICENSE)](LICENSE)

用大白话查聚水潭 ERP：库存、待发货、发货序列号、单笔订单、经营情况，一句话出中文结论。首次使用引导装水宝、登录、授权，全程只读，**不改 ERP 任何单据**。

这是三套发行包里的**连接器包**，遵循标准 MCP 连接器协议：启用后出现 `jst_check`、`jst_ask` 等 7 个 MCP 工具，并自带一份技能说明。运行时用 Node。它和技能包是同一套逻辑的两份实现，话术完全一致。可用于 WorkBuddy、Goodax、DeepSeek、Harness 等各类支持 MCP 的 AI 助手。

[English](README.en.md) · [仓库首页](../README.md) · [技能包](../skill/README.md) · [通用 MCP 包](../mcp/README.md)

> 非官方社区工具，与聚水潭、聚捷云、水宝官方无隶属关系。使用前读 [免责声明](../DISCLAIMER.md)。

---

## 三个前提

1. 自己有聚水潭账号（找公司开通）；
2. 本机装了[水宝](https://jxy.ai/download)并用本人账号登录；
3. 本人在水宝「连接管理」里给聚水潭授权一次。

装好授权后水宝可关掉；登录约 7 天过期，重新登录即可，授权不用再做。启用连接器后让 AI 先调 `jst_check`，它会告诉你还差哪一步。

## 7 个工具

| 工具 | 用途 |
| --- | --- |
| `jst_check` | 环境体检，每次会话第一次必调 |
| `jst_setup` | 完整安装清单（不联网） |
| `jst_domains` / `jst_actions` / `jst_fields` | 查有哪些业务域、接口、参数 |
| `jst_query` | 原始只读查询 |
| `jst_ask` | **优先用**：一句话问业务问题 |

`jst_ask` 覆盖经营概览、待发货、已发货序列号、序列号反查、库存、单笔订单、店铺、通用单据查询、找接口 9 个场景，外加全部 36 个只读查询接口。53 个写操作被白名单拦截。

## 目录结构

```
connector/
├── connector-meta.json   连接器市场元数据
├── mcp.json              stdio MCP 启动配置
├── icon.svg              图标
├── server.mjs            MCP Server（7 个工具）
├── ask.mjs               一问一答场景引擎
├── guide.json / scenarios.json
├── skills/jst-helper/SKILL.md  连接器自带技能说明
├── jst/                  只读清单 + 12 份业务域说明
├── README.md / README.en.md
├── LICENSE / CHANGELOG.md
```

## 上架 / 开发

打包与上架见 [docs/MARKETPLACE.zh-CN.md](../docs/MARKETPLACE.zh-CN.md)。改内核后按 `tools/sync_core.py` 同步到通用 MCP 包，再 `python tools/build.py` 重新打包。开发者纯离线自检：`python tools/verify_offline.py`。

## 许可

[MIT](LICENSE)。
