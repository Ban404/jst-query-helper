# JST Query Helper

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-green.svg)](docs/QUICKSTART.en.md)
[![Node 18+](https://img.shields.io/badge/node-18%2B-green.svg)](docs/QUICKSTART.en.md)

Ask plain-language questions about a JST (聚水潭) ERP account — inventory, orders waiting to ship, shipped serial numbers, a single order, or a business overview — and get a tidy Chinese-language answer. First-time users are guided step by step through installing the client, logging in, and authorizing it themselves. Everything is **read-only**; the tool never modifies ERP records.

> This is an **unofficial community tool**, with no affiliation to or endorsement from JST / Juxieyun / Shuibao. Read the [Disclaimer](DISCLAIMER.md) before use.

[中文 README](README.md) · [Quick start](docs/QUICKSTART.en.md) · [FAQ](docs/FAQ.en.md) · [Architecture](docs/ARCHITECTURE.en.md)

---

## What it can do

| You say | It does |
| --- | --- |
| "How is business today" | Counts of pending / shipped / cancelled orders, low-stock SKUs |
| "Anything waiting to ship" | Lists pending orders and whether each is stuck on approval, stock, or a missing pick list |
| "Which units shipped this month" | Serial numbers from sales outbound records, exportable to Excel |
| "Which order shipped this SN" | Reverse-lookups outbound date, order, tracking number, product |
| "How much stock is left" | Filters by product name or stock threshold |
| "Has this order shipped" | Order detail + outbound record + serials in one answer |
| "Show refunds / purchase orders" | Covers **all 36 read-only query endpoints**, fields translated to Chinese |

- **9 built-in scenarios** plus a generic query covering all 36 read endpoints; the 53 write endpoints are blocked in code.
- **Handles the busywork**: the upstream API allows only 7 days per call, so it auto-segments; auto-paginates; auto-reads large results that the CLI spills to a file.
- **Max 180 days** per question; beyond that it gives a friendly message instead of hammering the API.
- **CSV export** with UTF-8 BOM so Excel opens it correctly.

## Compatible AI assistants

This is a **universal tool** — it is not tied to any single AI assistant. All of the following work, with slightly different setup:

| AI assistant | Edition to use | How to connect |
| --- | --- | --- |
| **WorkBuddy** | Skill / Connector | Install `skill/` as a skill, or enable the MCP connector |
| **Goodax** | Skill / Connector | Install via that platform's skill / MCP mechanism |
| **DeepSeek** | Universal MCP | Configure `mcp/server.mjs` in an MCP-capable client |
| **Harness** | Universal MCP | Same as above, via the platform's MCP config |
| Claude Desktop / Cursor / Cline / Windsurf, etc. | Universal MCP | See [`mcp/config-examples.json`](mcp/config-examples.json) |

Whichever assistant you use, it queries the same data, runs the same read-only logic, and gives the same answers. See [Quick start](docs/QUICKSTART.en.md) for installation steps.

## How it works

The design respects one fact: **JST is a private ERP — account, login, and authorization cannot be bypassed.** So the tool bypasses nothing. It reuses the login state a user has already established in the official desktop client (Shuibao) and that client's bundled query program, and performs read-only queries.

```
your question → this tool's script → Shuibao's bundled query program → JST ERP (read-only)
                       ↑
        reuses your own already-authorized login, read locally, never uploaded
```

**Three prerequisites**, all required:

1. You have your own JST account (get one from your company — the tool can't create it);
2. You installed the Shuibao desktop client and logged in with your own account (it provides the credential and query program);
3. You clicked authorize once in Shuibao's "Connection Management" for JST.

After setup, Shuibao can be closed. The login expires in about 7 days (just log in again); the authorization is one-time.

See [Architecture](docs/ARCHITECTURE.en.md) for the component map.

## Three independent editions

One read-only query core, packaged as three **independent, individually publishable** editions. Identical features and wording — only the integration differs, so pick one:

| Edition | Directory | Publish to | Runtime | For |
| --- | --- | --- | --- | --- |
| **① Skill** | [`skill/`](skill/) | Universal AI assistant skill | Python 3.8+ | Individual users, install and go |
| **② Connector** | [`connector/`](connector/) | MCP connector | Node 18+ | Enterprise users wanting MCP tools |
| **③ Universal MCP** | [`mcp/`](mcp/) | npm / any MCP client | Node 18+ | Any MCP client user |

Each is a complete self-contained directory: its own README (zh/en), LICENSE, CHANGELOG, disclaimer reference and independent check — publishable on its own. All three share one action catalog `catalog/`, one guidance file and one scenario list, kept in sync by `tools/sync_core.py`, so wording is identical. The build script produces three uploadable zips; see [Packaging](docs/MARKETPLACE.en.md).

**No binaries in this repo** — the query program comes with Shuibao; nothing third-party is distributed here.

## Quick start

To use it: [Quick start](docs/QUICKSTART.en.md).
To publish as a skill / connector: [Packaging](docs/MARKETPLACE.en.md).
To develop: [Contributing](CONTRIBUTING.md) and [Architecture](docs/ARCHITECTURE.en.md).

Developer check — **no Shuibao, no network, no credentials needed**:

```bash
python tools/verify_offline.py
```

Live verification (requires Shuibao installed and authorized):

```bash
python tools/verify_online.py
```

## Limits, stated honestly

- **No "install and instantly get data"**: account, personal login, and authorization can't be skipped. What works is self-service in chat after a one-time setup.
- **Read-only enforced in code**: 36 query endpoints whitelisted; 53 write endpoints and unknown ones are rejected with `READONLY_MODE` / `ACTION_NOT_ALLOWED`.
- **Credentials read locally only**: never uploaded, never written into the project, never committed; cache lives in the system temp dir. See [SECURITY.md](SECURITY.md).
- **Depends on an external client**: Shuibao's paths and bundled CLI aren't an API promised to this project; an official upgrade may break them. `refresh_catalog.py` re-detects endpoints, but compatibility can't be guaranteed forever.
- **Cannot query Douyin backend** — JST ERP only.

## License

[MIT](LICENSE). Project code is open source; JST / Shuibao / Juxieyun names and trademarks belong to their respective owners. Read [DISCLAIMER.md](DISCLAIMER.md) before use.
