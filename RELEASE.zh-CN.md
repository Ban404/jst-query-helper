# 三套发行包 · 发布清单

同一套只读查询内核，做成三套**各自独立、各自达标、各自能上架/开源**的发行包。功能与话术完全一致，只是接入方式不同。

## 一目了然

| | 套装① 技能包 | 套装② 连接器包 | 套装③ 通用 MCP 包 |
| --- | --- | --- | --- |
| 源码目录 | `skill/` | `connector/` | `mcp/` |
| 上架到 | 通用 AI 助手技能 | MCP 连接器 | npm / 任意 MCP 客户端 |
| 运行时 | Python 3.8+（平台自带） | Node 18+（平台自带） | Node 18+（用户本机） |
| 接入方式 | 装上即用，AI 跑脚本 | 启用后出 7 个 MCP 工具 | 客户端 MCP 配置 / `npx` |
| 入口文件 | `SKILL.md` | `connector-meta.json` | `package.json` + `server.mjs` |
| zip 文件 | `聚水潭查询助手-技能包.zip` | `聚水潭查询助手-连接器包.zip` | `聚水潭查询助手-MCP包.zip` |
| zip 根 | `jst-query-helper/` | `jst-helper/` | `jst-query-mcp/` |

三套都是**纯文本、零二进制**；查询程序由水宝安装后自带。每套目录都自带中英 README、MIT LICENSE、CHANGELOG、免责声明引用，单独拿出去就能发布。

## 每套怎么发

**① 技能包**：把 `skill/` 目录作为技能装进 AI 助手（WorkBuddy、Goodax、DeepSeek、Harness 等），或直接上传 `聚水潭查询助手-技能包.zip`。这是主交付。

**② 连接器包**：作为 MCP 连接器配置到 AI 助手，或使用 `聚水潭查询助手-连接器包.zip`。给想要 MCP 工具的企业用户，`source: jst-helper` 需全局唯一。

**③ 通用 MCP 包**（二选一或都做）：
- 发 npm：`cd mcp && npm publish`，之后用户 `npx jst-query-mcp`（先确认包名可用，或改成自己的 scope）。
- 发 zip：提供 `聚水潭查询助手-MCP包.zip` 下载，用户照 `mcp/README.md` 把 `<解压目录>/server.mjs` 填进客户端配置；`mcp/config-examples.json` 有 Claude Desktop / Cursor / Cline / Windsurf 样例。

## 三套如何保持一致

- 接口清单、引导话术、场景定义只有一份真源：`catalog/` + `guide.json` + `scenarios.json`。
- `tools/sync_core.py` 从连接器内核生成通用 MCP 内核（只改资源路径），`tools/build.py` 把清单注入三套并打包。
- CI 校验 MCP 内核与连接器同步；离线自检逐字比对三份清单。改一处、三边同步，不会漂移。

## 验证结果（本次已跑）

| 检查 | 结果 |
| --- | --- |
| 全仓敏感扫描 | 通过：无二进制 / 无凭据 / 无本机路径 / 无真实数据 |
| 离线自检 `verify_offline.py` | 88 项全过 |
| 单元测试 `pytest` | 13 项全过 |
| 在线自检 `verify_online.py` | 26 项全过（真实查询 + 三套 MCP 握手，含第三套） |
| 三个 zip 结构 | 各自单一根目录、无二进制、无凭据、入口齐全 |
| MCP 包解压自包含 | 解压到任意目录可启动，跨 cwd 握手正常（7 工具） |

```bash
# 复现验证（clone 后按需跑）
python tools/scan_secrets.py
python tools/verify_offline.py
python -m pytest tests/ -q
python tools/verify_online.py    # 需装好水宝并授权
python tools/build.py            # 重建三个 zip
```

## 发布前提醒

- 三套都含 [免责声明](DISCLAIMER.md) 与安全策略；公开前再跑一遍敏感扫描。
- 详情与隐私说明见 [打包与上架](docs/MARKETPLACE.zh-CN.md) 与 [SECURITY.md](SECURITY.md)。
