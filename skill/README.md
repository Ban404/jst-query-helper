# 聚水潭查询助手 · 技能包

[![License: MIT](LICENSE)](LICENSE)

用大白话查聚水潭 ERP：库存、待发货、发货序列号、单笔订单、经营情况，一句话出中文结论。第一次用会一步步引导装水宝、登录、授权，全程只读，**不改 ERP 任何单据**。

这是三套发行包里的**技能包**，遵循通用 AI 助手技能格式：装上就能用，不需要连接器、不需要管理员、不需要额外装软件。运行时用 Python。可用于 WorkBuddy、Goodax、DeepSeek、Harness 等各类 AI 助手。

[English](README.en.md) · [仓库首页](../README.md) · [通用 MCP 包](../mcp/README.md) · [连接器包](../connector/README.md)

> 非官方社区工具，与聚水潭、聚捷云、水宝官方无隶属关系。使用前读 [免责声明](../DISCLAIMER.md)。

---

## 三个前提

1. 自己有聚水潭账号（找公司开通）；
2. 本机装了[水宝](https://jxy.ai/download)并用本人账号登录；
3. 本人在水宝「连接管理」里给聚水潭授权一次。

装好授权后水宝可关掉；登录约 7 天过期，重新登录即可，授权不用再做。首次使用让 AI 跑 `scripts/jst.py doctor`，它会告诉你还差哪一步。

## 装上就能问

```
今天生意怎么样          → 经营概览
有没有货要发            → 待发货订单
这个月发了哪些机器      → 已发货序列号（可导 CSV）
客户报个 SN，哪单发的   → 序列号反查
还有多少库存            → 库存速查
查售后退货 / 采购单      → 36 个只读查询接口全覆盖
```

9 个开箱场景 + 通用查询；自动 7 天分段、翻页、字段中文化、CSV（UTF-8 BOM）导出。53 个写操作被代码层拦截。

## 目录结构

```
skill/
├── SKILL.md              给 AI 的用法与三条铁律
├── scripts/
│   ├── jst.py            体检 / 接口清单 / 只读查询
│   ├── ask.py            一问一答场景引擎
│   ├── guide.json        首次使用引导文案
│   ├── scenarios.json    场景定义
│   └── actions.json      接口清单（89：36 查询 / 53 写入）
├── references/
│   ├── getting-started.md  第一次用的完整对话剧本
│   └── domains/            12 份业务域说明
├── config.example.json   极少装不了水宝时的 token 兜底（一般不用）
├── READONLY              只读标记
├── README.md / README.en.md
├── LICENSE / CHANGELOG.md
```

## 上架 / 开发

打包与上架见 [docs/MARKETPLACE.zh-CN.md](../docs/MARKETPLACE.zh-CN.md)。改内核后按 `tools/sync_core.py` 同步到另外两套，再 `python tools/build.py` 重新打包。开发者纯离线自检：`python tools/verify_offline.py`。

## 许可

[MIT](LICENSE)。
