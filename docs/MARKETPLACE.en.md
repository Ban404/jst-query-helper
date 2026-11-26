# Packaging & publishing the three editions

## Build the uploadable zips

```bash
python tools/build.py
```

Three packages go to `dist/` (the build first runs `tools/sync_core.py` so all three cores stay identical):

| File | Publish to | zip root | Purpose |
| --- | --- | --- | --- |
| `聚水潭查询助手-技能包.zip` | **Universal AI assistant skill** (primary) | `justerp-query-helper/` | Works on install, no connector needed |
| `聚水潭查询助手-连接器包.zip` | MCP connector | `jst-helper/` | MCP tools for enterprise users |
| `聚水潭查询助手-MCP包.zip` | **npm / any MCP client** | `jst-query-mcp/` | Claude Desktop / Cursor / Cline and more |

All three are **plain text, zero binaries** — the query program comes with Shuibao; no third-party exe is distributed. Each edition bundles its own README (zh/en), LICENSE and CHANGELOG, so it can be published on its own.

## Steps

**① Skill → Universal AI assistant skill**

1. Fill the listing: use README's "What it can do" and [Scenarios](SCENARIOS.en.md); point privacy notes to [SECURITY.md](../SECURITY.md).
2. Skill marketplace → Add skill → upload the skill zip (root `justerp-query-helper/`, `SKILL.md` at its root).

**② Connector → MCP connector**

3. Upload the connector zip; its `skills/jst-helper/SKILL.md` loads with the connector. `source: jst-helper` must be globally unique.

**③ Universal MCP → npm / any MCP client**

4. Publish to npm: `cd mcp && npm publish` (first confirm `jst-query-mcp` is free on npm, or rename in `package.json` to your own scope). Users then run `npx jst-query-mcp` with no install.
5. Or ship the zip: users unzip and put the absolute path `<unzip dir>/server.mjs` into their client's MCP config (`mcp/config-examples.json` has Claude Desktop / Cursor / Cline / Windsurf samples).

**Wrap-up**

6. **Self-check** (below) — must be 0 failures.
7. Gray-release to 2–3 real new users; focus on the authorize step and the 7-day re-login wording.

## Self-check commands

```bash
python tools/verify_offline.py     # no Shuibao: structure / required fields / privacy / whitelist / scenarios / version / packaging
python tools/scan_secrets.py       # repo-wide privacy scan
python -m pytest tests/ -q         # offline unit tests
python tools/verify_online.py      # needs Shuibao + authorization: live queries + scenarios + MCP handshake
```

## Constraints to avoid traps

- **Why the skill is primary**: users click "+" in the skill marketplace. A skill can't declare "depends on connector", and the platform won't auto-install connectors. The skill ships its own `scripts/` that the AI runs via Bash — that's what makes it work on install.
- **`source` must be globally unique**: if `source: jst-helper` in `connector-meta.json` is taken, rename it in 4 places (connector-meta, mcp.json, server.mjs, SKILL.md).
- **`cwd` in `mcp.json`**: the platform doesn't document the relative base. The package sets `cwd: "."`, and `server.mjs` locates all resources relative to itself, so it doesn't depend on cwd. Enable once after publishing to confirm tools appear.
- **Upstream paths aren't a stable API**: after a Shuibao upgrade run `refresh_catalog.py` + `build.py`. History: [Recognition report](RECOGNITION.en.md).
- **Rare environments lack `python`**: the skill guides users to enable the same-name connector (platform provides Node) with identical wording.

## Privacy & compliance

The listing's privacy note should say: the project **uploads nothing** — credentials are read locally and passed only to the local query program; exported CSVs may contain serials and customer info, managed by the user. See [DISCLAIMER](../DISCLAIMER.md) and [SECURITY](../SECURITY.md).
