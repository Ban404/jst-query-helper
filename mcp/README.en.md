# JST Query Helper · Universal MCP Server

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Node 18+](https://img.shields.io/badge/node-18%2B-green.svg)](https://nodejs.org)

Query JST ERP in plain language — inventory, orders waiting to ship, shipped serial numbers, single orders, business overview — and get a tidy, ready-to-read answer. **Strictly read-only: it never changes any ERP record.**

This is a **standard MCP Server** (protocol `2025-06-18`) running over stdio. It is not tied to any AI platform: **Claude Desktop, Cursor, Cline, Windsurf, or any MCP-capable client can connect.**

> Unofficial community tool. No affiliation with or endorsement from JST, Jushuitan, Jieyun or Shuibao. Read the [disclaimer](../DISCLAIMER.md) and [security policy](../SECURITY.md) before use.

[中文](README.md) · [Client config examples](config-examples.json) · [Repository home](../README.md)

---

## Three editions — pick one

This project ships three independent packages with identical features and wording, differing only in how you connect:

| Edition | Directory | Where | Runtime | For |
| --- | --- | --- | --- | --- |
| Skill | `skill/` | Universal AI assistant skill | Python | Individual users, install and go |
| Connector | `connector/` | MCP connector | Node | Enterprise users who want MCP tools |
| **Universal MCP** (this one) | `mcp/` | Any MCP client | Node 18+ | Claude Desktop / Cursor / Cline and others |

All three share one action catalog, one guidance text and one scenario definition, so they say exactly the same thing. This package is for **standard MCP clients** — WorkBuddy, Goodax, DeepSeek, Harness and other AI assistants.

---

## Three prerequisites

This tool bypasses nothing. JST is a private ERP; account, login and authorization are three gates you must pass yourself:

1. You have a JST ERP account (provided by your company — this tool cannot create one);
2. [Shuibao client](https://jxy.ai/download) is installed and you are logged in with your own account;
3. You clicked authorize once in Shuibao's "Connection Manager" for JST.

After setup and authorization you can close Shuibao — queries keep working. **Login expires in about 7 days**; just log in again, authorization is one-time. Once connected, have the client call `jst_check` first; it tells you exactly what step remains and what to do.

---

## Connect a client

Unzip this package and note its **absolute path** (e.g. `/Users/me/mcp/jst-query-mcp/server.mjs` or `D:\mcp\jst-query-mcp\server.mjs`).

Add one block to your client's MCP config (full examples are in `config-examples.json`):

```json
{
  "mcpServers": {
    "jst-query": {
      "command": "node",
      "args": ["<absolute path to server.mjs>"]
    }
  }
}
```

Common config locations:

| Client | Config file |
| --- | --- |
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |
| Cursor | Settings → MCP → Add new global MCP server |
| Cline | Extension settings → MCP Servers → Configure |
| Windsurf | Settings → MCP → Add server |

Save and **restart the client**. On the first conversation, ask it to call `jst_check`, finish the install / login / authorization steps it returns, then start querying.

> Once published to npm you can skip the local path: set `command` to `npx` and `args` to `["-y", "jst-query-mcp"]`.

Optional environment variables (usually leave unset):

- `JST_CLI_PATH`: absolute path to the query program; auto-detected in the Shuibao install if unset.
- `JXY_TOKEN`: login token; read from local Shuibao config if unset (**never put a real token in a config file**).
- `JST_ALLOW_WRITE`: set to `1` only to disable the read-only whitelist; normal users never need this.

---

## Tools (7)

| Tool | When | Parameters |
| --- | --- | --- |
| `jst_check` | **First use of every session**, any query error, or after the user says "done" | none |
| `jst_setup` | "How do I set this up" | none (offline; returns download link, 3 user steps, success criteria) |
| `jst_domains` | List business categories | none (12 categories) |
| `jst_actions` | Find available actions | `domain`: category name like "库存"; empty auto-aggregates all 12 |
| `jst_fields` | **Must call** before building params | `action`: action name |
| `jst_query` | Raw query when scenarios don't cover it | `action`: action name; `params`: JSON string |
| `jst_ask` | **Preferred** — ask a business question in one line | `scene` (required) + optional `days` `keyword` `low` `id` `sn` `action` `csv` |

`jst_ask` scenes: `overview`, `pending`, `serials`, `sn`, `stock`, `order`, `shops`, `query`, `find`, `list`. `days` capped at 180.

**Three rules for the AI** (recommended in the client's system prompt):

1. On first use each session, call `jst_check` regardless of the question.
2. Advance one step at a time: relay `what_to_do` verbatim with `url` and `success_check`, then wait for "done".
3. When the user says "done", re-run `jst_check`; only `status: READY` permits querying.

Once ready, prefer `jst_ask` over hand-building params. If no fixed scenario fits, `find` an action name then `query` with `action` — all 36 query actions are reachable. The `summary` field is ready to read aloud.

---

## Read-only by design

Only the **36 registered query actions** are allowed; 53 write actions (ship, approve, cancel, edit notes, etc.) and any unregistered action are blocked with `READONLY_MODE` / `ACTION_NOT_ALLOWED`. `data/READONLY` is the read-only marker; removing it or setting `JST_ALLOW_WRITE=1` is the only way to lift the restriction — ordinary users should never do this.

---

## Layout

```
mcp/
├── package.json          npm metadata (publish / npx)
├── server.mjs            MCP Server (stdio, standard JSON-RPC)
├── ask.mjs               question-answer scenario engine
├── guide.json            first-time setup text
├── scenarios.json        scenario definitions
├── config-examples.json  client config examples
├── data/
│   ├── actions.json      action catalog (89: 36 query / 53 write)
│   ├── READONLY          read-only marker
│   └── domains/          12 domain notes
├── README.md / README.en.md
├── LICENSE / CHANGELOG.md
└── icon.svg
```

`server.mjs` / `ask.mjs` / `guide.json` / `scenarios.json` are synced from the connector core via `tools/sync_core.py`; `data/` is injected by `tools/build.py`.

---

## Developer checks

No Shuibao, network or credentials needed:

```bash
npm run check                    # Node syntax
python tools/verify_offline.py   # three editions: structure / privacy / readonly / packaging
```

With Shuibao installed and authorized:

```bash
python tools/verify_online.py    # real query + universal MCP handshake
```

---

## License

[MIT](LICENSE). JST / Shuibao / Jieyun names and trademarks belong to their respective owners.
