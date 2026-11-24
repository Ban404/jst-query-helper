# JST Query Helper · Connector Package

[![License: MIT](LICENSE)](LICENSE)

Query JST ERP in plain language — inventory, orders waiting to ship, shipped serial numbers, single orders, business overview — with a ready-to-read Chinese answer. First use walks the user through setup. **Strictly read-only.**

This is the **connector package**, one of three editions: a standard MCP connector. Enabling it exposes 7 MCP tools (`jst_check`, `jst_ask`, ...) plus a bundled skill instruction. Runs on Node. It is the same logic as the skill package in a different runtime, with identical wording. Works with WorkBuddy, Goodax, DeepSeek, Harness and other MCP-capable AI assistants.

[中文](README.md) · [Repository home](../README.md) · [Skill package](../skill/README.en.md) · [Universal MCP](../mcp/README.en.md)

> Unofficial community tool, no affiliation with JST / Jushuitan / Shuibao. Read the [disclaimer](../DISCLAIMER.md).

---

## Three prerequisites

1. You have a JST ERP account (from your company);
2. [Shuibao](https://jxy.ai/download) is installed and you are logged in with your own account;
3. You authorized JST once in Shuibao's Connection Manager.

After setup you can close Shuibao. Login expires in ~7 days (just log in again); authorization is one-time. Once enabled, have the AI call `jst_check` first — it tells you what step remains.

## 7 tools

| Tool | Purpose |
| --- | --- |
| `jst_check` | Environment check, required on first use each session |
| `jst_setup` | Full setup checklist (offline) |
| `jst_domains` / `jst_actions` / `jst_fields` | List business domains, actions, parameters |
| `jst_query` | Raw read-only query |
| `jst_ask` | **Preferred**: ask a business question in one line |

`jst_ask` covers 9 scenarios plus all 36 read-only query actions. 53 write actions are blocked.

## Layout

```
connector/
├── connector-meta.json   marketplace metadata
├── mcp.json              stdio MCP config
├── icon.svg
├── server.mjs            MCP Server (7 tools)
├── ask.mjs               scenario engine
├── guide.json / scenarios.json
├── skills/jst-helper/SKILL.md
├── jst/                  read-only catalog + 12 domain notes
├── README.md / README.en.md
├── LICENSE / CHANGELOG.md
```

## Publish / develop

See [docs/MARKETPLACE.en.md](../docs/MARKETPLACE.en.md). After core changes, run `tools/sync_core.py` then `python tools/build.py`. Offline check: `python tools/verify_offline.py`.

## License

[MIT](LICENSE).
