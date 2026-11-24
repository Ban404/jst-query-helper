---
name: jst-query-helper
display_name: 聚水潭查询助手
display_name_en: JST Query Helper
description: 查询聚水潭 ERP 的店铺、商品、订单、库存、销售出库单和产品序列号；常见业务问题（待发货、序列号、库存、单笔订单、经营概览）一句话就能得到整理好的中文结论。首次使用时会自动引导安装水宝、登录、授权与续期。当用户提到聚水潭、库存、待发货、序列号，或问「怎么装」「水宝授权在哪」「为什么查不了」时使用。
description_zh: 查聚水潭 ERP 数据，常见业务问题一句话出结果，并带第一次使用的人一步步装好水宝、登录、授权。
description_en: Query JST ERP data with ready-made business answers and a guided first-time setup.
category: data
version: 5.0.0
author: Ban404
examples_zh:
  - "查一下现在还有多少库存"
  - "有没有货要发"
  - "查最近已发货订单的产品序列号"
  - "这个序列号是哪单发的"
  - "今天生意怎么样"
  - "查一下最近的售后退货退款"
  - "第一次用，我该怎么装"
  - "水宝授权在哪里点"
examples_en:
  - "Show current inventory"
  - "Any orders waiting to ship"
  - "List serial numbers shipped this month"
  - "Which order was this serial number shipped in"
  - "How do I set this up for the first time"
---

# 聚水潭查询助手

给**装上就用**的普通用户准备的。自带查询脚本，不依赖任何连接器、不需要管理员、不需要用户另外装软件。可用于 WorkBuddy、Goodax、DeepSeek、Harness 等各类 AI 助手。

第一次用的完整对话怎么演，见 @references/getting-started.md。

---

## 三条铁律

**1. 每次会话第一次用到本技能，先体检，别管用户问的是啥。**

即使用户直接问「查一下库存」，也先跑一次：

```bash
python "<技能目录>/scripts/jst.py" doctor
```

`<技能目录>` 就是本 `SKILL.md` 所在的文件夹。脚本用自身位置找文件，从哪个目录启动都行。AI 助手通常自带 Python；若没有，装一个 Python 3.8+ 即可。

**2. 一次只推进一步。**

体检返回 `what_to_do`，**把这句话原样讲给用户**，附 `url` 和 `success_check`，然后停下来等他说「好了」。不要一次把五步全列出来，不要自己猜原因，不要让用户去翻配置文件，不要把 token 贴到对话里。

**3. 用户说「好了」不等于成功，必须重新跑一次 `doctor`。**

只有重新体检返回 `status: READY` 才能继续查数据。没过就按新的 `what_to_do` 再说一遍（可以补一句「还差这步，我们再来一次」），不要表现得像出错了。

---

## 按体检结果走

| `status` | 阶段 | 让用户做什么 |
| --- | --- | --- |
| `SHUIBAO_MISSING` | 第 1 步 | 下载安装水宝 → 用自己的聚水潭账号登录 |
| `SHUIBAO_NOT_LOGGED_IN` | 第 2 步 | 打开水宝登录一次 |
| `CLI_MISSING` | 第 3 步 | 水宝 →「技能」/「技能市场」→ 安装「聚水潭 ERP 助手」，保持登录等半分钟 |
| `TOKEN_EXPIRED` | 第 4 步 | 重新登录（**不用重新授权**） |
| `TOKEN_REJECTED` | 第 4 步 | 重新登录；还不行就查网络 |
| `NOT_AUTHORIZED` | 第 5 步 | 水宝 →「连接管理」→ 聚水潭 → 授权，**本人点，只做一次** |
| `READY` | 完成 | 可以查数据了 |

`who`、`url`、`success_check` 三个字段直接讲给用户。想看全部步骤清单时跑 `python "<技能目录>/scripts/jst.py" setup`（不联网）。

要主动说清的事实（别等用户踩坑）：

- 水宝只在**安装、登录、授权、续期**这四个时刻要开着，查数据时可以关掉。新版水宝会在后台装「水宝守护服务」，是正常的，不用管。
- 水宝里的「聚水潭 ERP 助手」是技能市场里的技能，首次登录一般自动装好；没装上时按 `CLI_MISSING` 的提示装一次即可。
- 授权是账号级一次性的；**7 天过期的是登录，不是授权**。到期时主动提醒重新登录，不要让用户再去点授权。
- 每个人用自己的聚水潭账号登录。包可以共用，登录凭据不能共用，否则 ERP 里的记录算到别人头上。
- 没聚水潭账号的人，得先让公司开通账号，这一步 AI 帮不了。

---

## 就绪后：先想「一句话能不能解决」

**优先用 `ask.py`。** 它已经把自动分段（接口一次只能查 7 天）、自动翻页、数据落盘读取、结果整理成中文结论这些麻烦事都做掉了。不要自己拼参数、写循环、翻原始 JSON。

```bash
python "<技能目录>/scripts/ask.py" list                       # 不确定时先看能问什么
python "<技能目录>/scripts/ask.py" overview --days 7         # 今天生意怎么样
python "<技能目录>/scripts/ask.py" pending --days 30         # 有没有货要发
python "<技能目录>/scripts/ask.py" serials --days 30 --csv  # 已发货序列号（顺手导 CSV）
python "<技能目录>/scripts/ask.py" sn --sn SN-DEMO-0001    # 客户报个 SN，反查订单和物流
python "<技能目录>/scripts/ask.py" stock --keyword Arc --low 3
python "<技能目录>/scripts/ask.py" order --id 订单号
python "<技能目录>/scripts/ask.py" shops
python "<技能目录>/scripts/ask.py" query --action refund_single_query --days 7  # 其余查询接口
python "<技能目录>/scripts/ask.py" find 售后                 # 先找接口名，再给 query
```

| 用户会问 | 用哪个 |
| --- | --- |
| 今天生意怎么样 / 有什么要注意的 | `overview` |
| 有没有货要发 / 哪些订单还没发 | `pending` |
| 这个月发了哪些机器 / 序列号清单 | `serials` |
| 客户报了个序列号，是哪单发的 | `sn` |
| 还有多少库存 / 哪些货快没了 | `stock` |
| 这单发了吗 / 订单号 xxxx | `order` |
| 我有几个店 / 店铺编号 | `shops` |
| 售后退货退款 / 采购单 / 盘点单 / 调拨单 | `find` 找接口名 → `query` |
| 能不能查某某 | `find` |

**固定场景没覆盖时别急着说「查不了」**：先 `find 关键词` 找接口名，再 `query --action 接口名`。这样 36 个查询接口全部能问，`query` 会自动分段、翻页、去重，并把英文字段翻成中文列名。

**返回结果怎么用**：`summary` 是可以直接念给用户听的中文结论，`rows` 是整齐的表格，`notes` 是口径说明。用中文讲结论和关键数字，不要整段贴 JSON；用户要明细再展开 `rows`。对话里最多给 50 行，要全量加 `--csv`（导出 UTF-8 BOM，Excel 直接打开不乱码）。`--days` 最多 180 天，超了会给中文提示，不会傻跑。

`ask.py` 一次进程只体检一次，之后的所有查询共用，不会每条数据都联网检查一遍。

---

## 场景没覆盖时，再走精细查询

```bash
python "<技能目录>/scripts/jst.py" list_domains
python "<技能目录>/scripts/jst.py" list_actions --domain '库存'
python "<技能目录>/scripts/jst.py" list_actions              # 不带域：自动汇总 12 个域的 89 个接口
python "<技能目录>/scripts/jst.py" describe_action --action inventory_query
python "<技能目录>/scripts/jst.py" invoke --action inventory_query --params '{"page_index":1,"page_size":10}'
```

第三步**必须看**，确认必填参数、时间跨度限制。接口版本号不用管，脚本会自动补；`--json` 也不用管，脚本默认加了。也可以用 `ask.py find 关键词` 快速定位接口。

新版水宝（2.0.611181 起）要求 `list_actions` 按业务域读取，不带 `--domain` 会报 `DOMAIN_REQUIRED`；脚本已自动按 12 个域逐个取再合并，新旧版水宝都能用。

两个常见口径：产品序列号挂在**销售出库单**上，订单接口里没有；订单状态常见 `WaitConfirm`（已付款待审核）、`Confirmed`（已确认待发货）、`Sent`（已发货）、`Cancelled`（已取消）。

---

## 只能查，不能改

**白名单强制**：只有已登记的 36 个查询接口放行，另外 53 个写操作（发货、审核、取消订单、改备注等）以及任何没登记的接口都会被直接拦下，返回 `READONLY_MODE` 或 `ACTION_NOT_ALLOWED`。照实告诉用户「这会真实改动 ERP，只读版不允许」，不要试图绕过，也不要教用户去删 `READONLY` 文件。

---

## 万一 Python 跑不起来

极少数环境里 `python` 命令不可用。不要报错收场，改走降级路径：告诉用户去连接器市场启用同名的「聚水潭查询助手」连接器（平台会自动准备 Node），启用后会出现 `jst_check`、`jst_ask` 等工具，用那些工具做同样的体检和查询，话术完全一致。

如果检测到 `jst_check` 等工具已经存在（用户同时也装了连接器），优先用工具，体验和脚本版一样。

---

## 常见问题

| 用户会问 | 怎么答 |
| --- | --- |
| "水宝要一直开着吗" | 不用，只有装、登录、授权、续期这四个时刻要开 |
| "为什么昨天能查今天不行" | 多半是 7 天登录过期，重新登录水宝即可 |
| "授权要再做一次吗" | 不用，授权只做一次 |
| "换了电脑" | 新电脑重走安装、登录、授权 |
| "能查抖音后台吗" | 不能，只能查聚水潭 ERP |
| "没有聚水潭账号能用吗" | 不能，得先让公司给开账号 |
| "能查更久以前吗" | 能，`--days 90` 就行，脚本会自动按 7 天一段拆开查 |
| "结果怎么存成表" | 加 `--csv`，例如 `serials --days 30 --csv` |

---

给管理员：这是**技能市场包**，纯文本、不含任何二进制程序，查询程序由水宝安装后自带。技能包不能包含连接器；连接器包是另一份可选增强。两者共用 `scripts/guide.json` 的引导文案和 `scripts/scenarios.json` 的场景清单，改话术或加场景都只改一处。包内 `scripts/actions.json` 的接口清单（89 个：36 查询 / 53 写入）是从水宝自带查询程序按 12 个业务域重新识别生成的；水宝升级后，在工程目录跑一次 `python refresh_catalog.py` 即可刷新，再 `python build.py` 重新打包。
