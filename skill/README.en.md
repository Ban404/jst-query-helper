# JST Query Helper · Skill Package

[![License: MIT](LICENSE)](LICENSE)

Query JST ERP in plain language — inventory, orders waiting to ship, shipped serial numbers, single orders, business overview — with a ready-to-read Chinese answer. First use walks the user through installing Shuibao, logging in and authorizing. **Strictly read-only.**

This is the **skill package**, one of three editions: a universal AI assistant skill. Install it and go — no connector, no admin, no extra software. Runs on Python. Works with WorkBuddy, Goodax, DeepSeek, Harness and other AI assistants.

[中文](README.md) · [Repository home](../README.md) · [Universal MCP](../mcp/README.en.md) · [Connector](../connector/README.en.md)

> Unofficial community tool, no affiliation with JST / Jushuitan / Shuibao. Read the [disclaimer](../DISCLAIMER.md).

---

## Three prerequisites

1. You have a JST ERP account (from your company);
2. [Shuibao](https://jxy.ai/download) is installed and you are logged in with your own account;
3. You authorized JST once in Shuibao's Connection Manager.

After setup you can close Shuibao. Login expires in ~7 days (just log in again); authorization is one-time. On first use, have the AI run `scripts/jst.py doctor` — it tells you what step remains.

## Ask anything

```
How is business today              → business overview
Anything waiting to ship           → pending orders
What shipped this month            → shipped serials (CSV export)
Customer gave an SN, which order   → serial lookup
How much stock left                → inventory
Refunds / purchase orders          → all 36 read-only query actions
```

9 ready-made scenarios + generic query; auto 7-day segmentation, paging, Chinese field mapping, UTF-8 BOM CSV export. 53 write actions are blocked in code.

## Layout

```
skill/
├── SKILL.md              AI instructions and three rules
├── scripts/              jst.py / ask.py / guide.json / scenarios.json / actions.json
├── references/           getting-started.md + 12 domain notes
├── config.example.json   rare fallback for token (usually unused)
├── READONLY              read-only marker
├── README.md / README.en.md
├── LICENSE / CHANGELOG.md
```

## Publish / develop

See [docs/MARKETPLACE.en.md](../docs/MARKETPLACE.en.md). After core changes, run `tools/sync_core.py` then `python tools/build.py`. Offline check: `python tools/verify_offline.py`.

## License

[MIT](LICENSE).
