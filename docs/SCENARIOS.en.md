# Scenarios & endpoints

## 9 built-in scenarios

| Command | Users ask | Returns |
| --- | --- | --- |
| `overview [--days 7]` | how is business / overview | counts of pending / shipped / cancelled, low-stock SKUs |
| `pending [--days 30]` | anything to ship / unshipped orders | pending orders with whether stuck on approval, stock, or no pick list |
| `serials [--days 30] [--csv]` | units shipped this month / serial list | serials from outbound records, deduped, by date, exportable |
| `sn --sn SN [--days 90] [--csv]` | which order shipped this SN | reverse lookup: outbound date, order, tracking, product; partial SN ok |
| `stock [--keyword K] [--low N] [--days 7]` | stock left / running low | filtered by name / threshold, sorted ascending |
| `order --id ID` | did this ship / order status | order detail + outbound + serials in one answer |
| `shops` | how many shops / shop IDs | shop names, IDs, platform authorization expiry |
| `query --action NAME [--days 7] [--csv]` | refunds / purchases / stocktakes / transfers | all remaining query endpoints, auto-segment, fields translated |
| `find KEYWORD` | can you query X | find usable query endpoints among 89 by CN/EN keyword |

`list` prints this catalog. All network scenarios accept `--days` (max 180) and `--csv` to export.

## All query endpoints

When a scenario doesn't cover it: `find KEYWORD` to get the endpoint name, then `query --action NAME`. All 36 query endpoints are reachable.

Distribution across business domains (89 endpoints total: 36 query / 53 write):

| Domain | Count | Domain | Count |
| --- | --- | --- | --- |
| Basic info | 6 | Products | 15 |
| Orders | 10 | Inventory | 5 |
| After-sales | 6 | Purchasing | 12 |
| Inbound | 4 | Outbound | 5 |
| Other in/out | 3 | Transfers | 6 |
| Virtual warehouse | 9 | Seeding | 8 |

Field docs for each domain are in [`../catalog/domains/`](../catalog/domains/) (12 files, shipped by the upstream client, synced by `refresh_catalog.py`).

## Read-only boundary

- **36 `kind=query` endpoints** allowed (see `catalog/actions.json`);
- **53 `kind=write` endpoints** (ship, approve, cancel, edit notes…) always return `READONLY_MODE`;
- **any unregistered endpoint** returns `ACTION_NOT_ALLOWED`;
- enforced in code in both Python and Node entry points, plus a `READONLY` marker file in each package.

## Output contract

Every scenario returns one JSON:

```json
{
  "ok": true,
  "scenario": "Pending orders",
  "summary": "one-line Chinese conclusion, safe to read aloud",
  "count": 12,
  "rows": [ /* tidy table rows, max 50 in chat */ ],
  "truncated": false,
  "notes": [ /* caveats about the metric */ ],
  "csv": ""
}
```

- `summary` is for end users — numbers and key items, never raw JSON.
- `rows` is detail, expand only on request.
- Beyond 50 rows, `truncated=true`; add `--csv` for the full set (UTF-8 BOM, Excel-clean).

## Metric caveats

- Counts use record **modified time**, not order/outbound date.
- The upstream allows only 7 days per call; scripts auto-segment; max 180 days per task.
- The same record appearing in multiple windows is deduped.
- Serials live on outbound records, not orders.
- Common order statuses: `WaitConfirm`, `Confirmed`, `Sent`, `Cancelled`.
