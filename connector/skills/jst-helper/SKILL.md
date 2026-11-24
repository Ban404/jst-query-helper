---
name: jst-helper
display_name: 聚水潭查询助手（连接器版）
display_name_en: JST Query Helper (Connector)
description: 查询聚水潭 ERP 的店铺、商品、订单、库存、销售出库单和产品序列号；常见业务问题一句话就能得到整理好的中文结论。首次使用时自动引导安装水宝、登录、授权与续期。当用户提到聚水潭、库存、待发货、序列号，或问「怎么装」「水宝授权在哪」时使用。
description_zh: 查聚水潭 ERP 数据，常见业务问题一句话出结果，并带第一次使用的人一步步装好水宝、登录、授权。
description_en: Query JST ERP data with ready-made business answers and a guided first-time setup.
category: data
version: 5.0.0
author: Ban404
allowed-tools: jst_check,jst_setup,jst_domains,jst_actions,jst_fields,jst_query,jst_ask
examples_zh:
  - "查一下现在还有多少库存"
  - "有没有货要发"
  - "今天生意怎么样"
  - "这个序列号是哪单发的"
  - "查一下最近的售后退货退款"
  - "第一次用，我该怎么装"
  - "水宝授权在哪里点"
examples_en:
  - "Show current inventory"
  - "Any orders waiting to ship"
  - "Which order was this serial number shipped in"
  - "Guide me through the first-time setup"
---

# 聚水潭查询助手（连接器版）

本技能是连接器 `jst-helper` 自带的一部分，位于连接器包的 `skills/jst-helper/SKILL.md`。启用连接器后，工具和这份说明一起到位。

技能市场另有一份**独立版**（`jst-query-helper`），不依赖连接器也能用；两者共用同一套引导文案和场景清单，用户听到的话完全一样。

## 工具速查（7 个）

| 工具 | 什么时候用 | 参数 |
| --- | --- | --- |
| `jst_check` | **每次会话第一次**、任何查询报错、用户说「装好了」时 | 无 |
| `jst_setup` | 用户问「怎么装」「要几步」 | 无（不联网，返回下载链接、3 步本人操作、成功标准） |
| `jst_domains` | 想知道有哪些业务分类 | 无（返回 12 类） |
| `jst_actions` | 找有哪些接口 | `domain`：中文分类名如「库存」；**留空则自动汇总全部 12 个域**（新版水宝要求按域读取，连接器已自动处理） |
| `jst_fields` | 构造参数前**必调** | `action`：接口名 |
| `jst_query` | 场景没覆盖时的原始查询 | `action`：接口名；`params`：参数的 JSON 字符串 |
| `jst_ask` | **优先用**，一句话问业务问题 | `scene`（必填）；`days` `keyword` `low` `id` `sn` `action` `csv`（按需） |

`jst_ask` 的 `scene` 取值：`overview` 经营概览、`pending` 待发货、`serials` 已发货序列号、`sn` 序列号反查、`stock` 库存速查、`order` 单笔订单、`shops` 店铺列表、`query` 其他单据、`find` 找接口、`list` 能问什么。`days` 最多 180；`sn` 给产品序列号（可只给后几位）；`action` 给 `query` 用，可先 `find` 找名字。

## 三条铁律

1. **每次会话第一次用到本技能，先调 `jst_check`**，不管用户问的是业务问题还是「怎么用」。
2. **一次只推进一步**：把 `jst_check` 返回的 `what_to_do` 原样讲给用户，附 `url` 和 `success_check`，然后停下等他说「好了」。不要一次列五步，不要让用户翻配置文件，不要把 token 贴进对话。
3. **用户说「好了」必须重新调 `jst_check`**。只有 `status: READY` 才允许查数据；没过就按新的 `what_to_do` 再说一遍，别表现得像出错了。

## 按体检结果走

| `status` | 让用户做什么 |
| --- | --- |
| `SHUIBAO_MISSING` | 按 `url` 下载安装水宝 → 用自己的聚水潭账号登录 |
| `SHUIBAO_NOT_LOGGED_IN` | 打开水宝登录一次 |
| `CLI_MISSING` | 水宝 →「技能」/「技能市场」→ 安装「聚水潭 ERP 助手」，保持登录等半分钟 |
| `TOKEN_EXPIRED` | 重新登录（**不用重新授权**） |
| `TOKEN_REJECTED` | 重新登录；还不行查网络 |
| `NOT_AUTHORIZED` | 水宝 →「连接管理」→ 聚水潭 → 授权，**本人点，只做一次** |
| `READY` | 可以查数据了 |

`who` 字段说明这步得用户本人动手，`success_check` 说明怎么算做对。想看全部步骤时调 `jst_setup`（不联网）。

要主动说清：水宝只在安装、登录、授权、续期这四个时刻要开着；新版水宝后台的「水宝守护服务」是正常的，不用管；「聚水潭 ERP 助手」是水宝技能市场里的技能，首次登录一般自动装好；授权是一次性的，**7 天过期的是登录不是授权**；每人用自己的账号；没聚水潭账号的人得先让公司开通。

## 就绪后：优先用 `jst_ask` 一句话问

`jst_ask` 已经把自动分段（接口一次只能查 7 天）、自动翻页、数据落盘读取、结果整理成中文结论都做掉了，不要自己拼参数、写循环、翻原始 JSON。

| 用户会问 | `scene` |
| --- | --- |
| 今天生意怎么样 | `overview` |
| 有没有货要发 | `pending` |
| 这个月发了哪些机器 / 序列号 | `serials` |
| 客户报了个序列号，是哪单发的 | `sn`（给 `sn`） |
| 还有多少库存 / 哪些货快没了 | `stock` |
| 这单发了吗 / 订单号 xxxx | `order` |
| 我有几个店 | `shops` |
| 售后退货退款 / 采购单 / 盘点单 / 调拨单 | `find` 找接口名 → `query`（给 `action`） |
| 能不能查某某 | `find` |
| 能问什么 | `list` |

可选参数：`days`（往前查多少天，最多 180；`sn` 默认 90）、`keyword`（stock 的商品词 / find 的关键词）、`low`（库存阈值）、`id`（订单号）、`sn`（产品序列号，可只给后几位）、`action`（query 用的接口名）、`csv`（导出 CSV 的文件名）。

**固定场景没覆盖时别急着说「查不了」**：先 `find` 找接口名，再 `query` 带上 `action`。这样 36 个查询接口全部能问，字段会自动翻成中文。

返回的 `summary` 可以直接念给用户，`rows` 是整齐的表格，`notes` 是口径说明。用中文讲结论和关键数字，不要整段贴 JSON。

## 场景没覆盖时，再走精细查询

`jst_domains` → `jst_actions`（给 `domain`）→ `jst_fields`（给 `action`，**必看**）→ `jst_query`（给 `action` 和 `params`）。`params` 是 JSON 字符串，接口版本号连接器会自动补，不用管。

查到结果用中文讲结论和关键数字。序列号挂在**销售出库单**上，订单接口里没有；常见状态 `WaitConfirm` / `Confirmed` / `Sent` / `Cancelled`。

## 只能查，不能改

**白名单强制**：只有已登记的 36 个查询接口放行，53 个写操作和任何没登记的接口都会被拦下，返回 `READONLY_MODE` 或 `ACTION_NOT_ALLOWED`。照实告诉用户「这会真实改动 ERP，只读版不允许」，不要试图绕过。

## 常见问题

| 用户会问 | 怎么答 |
| --- | --- |
| "水宝要一直开着吗" | 不用，只有装、登录、授权、续期要开 |
| "昨天能查今天不行" | 7 天登录过期，重新登录即可 |
| "授权要再做一次吗" | 不用，只做一次 |
| "能查抖音后台吗" | 不能，只能查聚水潭 ERP |
| "能查更久以前吗" | 能，`jst_ask` 给 `days: 90`，会自动按 7 天一段拆开 |
