# 变更日志（通用 MCP Server 包）

本包遵循 [语义化版本](https://semver.org/lang/zh-CN/)。内核与技能包、连接器包同源，由 `tools/sync_core.py` 同步。

## 5.0.0 — 2026-11-23

首版，与仓库 5.0.0 对齐。

- 标准 MCP Server：协议 `2025-06-18`，stdio 传输，7 个工具（`jst_check` / `jst_setup` / `jst_domains` / `jst_actions` / `jst_fields` / `jst_query` / `jst_ask`）。
- npm 元数据：`package.json` 含 `bin`，可 `npm publish` 后用 `npx jst-query-mcp` 免安装启动。
- 面向 Claude Desktop / Cursor / Cline / Windsurf 的配置示例（`config-examples.json`）。
- 只读白名单：36 个查询接口放行，53 个写操作与未登记接口拦截（`data/READONLY`）。
- 首次使用引导状态机：装水宝 → 登录 → 查询程序 → 续期 → 授权 → READY，一次只推进一步。
- 9 个开箱场景 + 通用查询，自动 7 天分段、翻页、结果落盘读取、字段中文映射、CSV（UTF-8 BOM）导出。
- 兼容新版水宝 2.0.611181：`list_actions` 按域自动汇总 12 个域。
- 中英 README、MIT 许可证、免责声明与安全策略引用。
