# 打包与上架三套发行包

## 生成可上传的 zip

```bash
python tools/build.py
```

生成三个包到 `dist/`（构建时自动先跑 `tools/sync_core.py`，保证三套内核一致）：

| 文件 | 上架到 | zip 根 | 说明 |
| --- | --- | --- | --- |
| `聚水潭查询助手-技能包.zip` | 通用 AI 助手**技能**（主） | `jst-query-helper/` | 装了就能用，不依赖连接器 |
| `聚水潭查询助手-连接器包.zip` | MCP 连接器 | `jst-helper/` | 想要 MCP 工具的企业用户 |
| `聚水潭查询助手-MCP包.zip` | **npm / 任意 MCP 客户端** | `jst-query-mcp/` | Claude Desktop / Cursor / Cline 等 |

三套都是**纯文本、零二进制**——查询程序由水宝安装后自带，不分发第三方 exe，公开市场没有分发授权顾虑。每套目录都自带 README（中英）、LICENSE、CHANGELOG，单独拿出去就能发布。

## 三套上架步骤

**套装① 技能包 → 通用 AI 助手技能**

1. 填详情页：照 `README.md` 的「它能做什么」和 `docs/SCENARIOS.zh-CN.md` 复制名称、简介、示例问句；隐私说明指向 [SECURITY.md](../SECURITY.md)。
2. 技能市场 → 添加技能 → 上传技能包 zip。zip 根是 `jst-query-helper/`，根内直接是 `SKILL.md`。

**套装② 连接器包 → MCP 连接器**

3. 连接器市场上传连接器包 zip，其 `skills/jst-helper/SKILL.md` 会随连接器一起加载。`source: jst-helper` 要求全局唯一。

**套装③ 通用 MCP 包 → npm / 任意 MCP 客户端**

4. 发 npm：`cd mcp && npm publish`（先把 `package.json` 的 name 改成你注册的名字，或确认 `jst-query-mcp` 未被占用）。发布后用户用 `npx jst-query-mcp` 免安装启动。
5. 或提供 zip 下载：用户解压后照 `mcp/README.md` 把 `<解压目录>/server.mjs` 绝对路径填进客户端 MCP 配置（`mcp/config-examples.json` 有 Claude Desktop / Cursor / Cline / Windsurf 样例）。

**通用收尾**

6. **先自查**（见下），必须 0 失败。
7. 建议先给 2～3 个真实新用户灰度，重点看「连接管理授权」和「7 天重新登录」两步话术够不够白话。

## 自查命令

```bash
python tools/verify_offline.py     # 不需要水宝：结构 / 必填字段 / 隐私 / 白名单 / 场景 / 版本 / 打包
python tools/scan_secrets.py       # 全仓隐私扫描：无二进制 / 无凭据 / 无真实数据
python -m pytest tests/ -q         # 离线单元测试
python tools/verify_online.py      # 需要装好水宝并授权：真实查询 + 场景 + MCP 握手
```

`verify_offline.py` 检查的是**最终交付的包**的结构来源，日常改话术或加场景不用跑 `refresh_catalog.py`。

## 关键约束（省得踩坑）

- **为什么主交付是技能包**：陌生人点「+」是在技能市场。官方技能包没有「依赖某连接器」字段，平台也不会自动装连接器；若以连接器包为主，技能装上后一个工具都没有。技能包自带 `scripts/`，AI 用 Bash 直接跑，才真正装了就能用。
- **三套为什么能各自独立**：三套共用 `catalog/` 清单与 `guide.json` / `scenarios.json`，由 `tools/sync_core.py` 保持内核一致；每套目录都自带完整入口与文档，单独打包/发布都不缺文件。改内核后跑 `sync_core.py` + `build.py`，CI 会校验 MCP 内核与连接器是否同步。
- **通用 MCP 包不依赖任何 AI 平台**：它是标准 MCP Server（stdio，`2025-06-18`），`package.json` 带 `bin`，可 `npm publish` / `npx`。发布前确认 npm 包名未被占用，或改成你自己的 scope。
- **`source` 要求全局唯一**：`connector-meta.json` 的 `source: jst-helper` 若被占用，需换名并同步改 4 处（connector-meta、mcp.json、server.mjs、SKILL.md）。
- **`mcp.json` 的 `cwd`**：官方未写死相对基准；包里写 `cwd: "."`，且 `server.mjs` 内部一律用自身文件位置找资源、不依赖 cwd。上架后先自己启用一次确认工具出现。
- **上游目录不是稳定接口**：水宝的目录结构、token 格式、接口清单都不是对本项目的承诺。升级后跑 `refresh_catalog.py` + `build.py`。历史变化见 [识别报告](RECOGNITION.zh-CN.md)。
- **极少数环境没有 `python` 命令**：技能会引导改去启用同名连接器（平台自动准备 Node），话术不变。

## 隐私与合规

上架详情页的隐私说明请写明：本项目**不上传**任何数据或凭据，凭据只在本机读取并传给本机查询程序；导出的 CSV 可能含序列号与客户信息，由用户自行保管。完整声明见 [DISCLAIMER](../DISCLAIMER.md) 与 [SECURITY](../SECURITY.md)。
