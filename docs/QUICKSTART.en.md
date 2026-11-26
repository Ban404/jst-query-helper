# Quick start (for non-technical users)

This guide assumes you've never used a terminal. Just follow along.

## What you'll get

Once set up, you ask your AI assistant in plain English/Chinese — "anything waiting to ship?", "which units shipped this month?" — and it hands you a tidy answer, exportable to Excel.

## Step 1: Three things to install

**1. Install an AI assistant** (WorkBuddy, Goodax, DeepSeek, Harness — pick whichever you like).

**2. Install the Shuibao desktop client**

Open <https://jxy.ai/download> → click the Windows version → next, next, next.
(Product page: <https://www.juxieyun.com/shuibao>. If your company provided an installer, use that one.)

> If asked about the "Shuibao guard service", allow it — it's a normal component.

**3. Log in with your own account**

Open Shuibao and log in with **your own** JST account. No account? Ask your company to create one — nobody can skip this.
You can close Shuibao after logging in.

**4. Authorize once**

Open Shuibao → "Connection Management" (not "Settings") → find JST → click "Authorize".
This step **you must do yourself**, only once, never again.

## Step 2: Install this helper

In your AI assistant:

- **Skill marketplace**: search "JST Query Helper" and install (the main way);
- For stronger MCP tools, optionally enable the connector with the same name (enterprise users).

Then just talk to the AI, e.g.:

> Show current inventory

On first use, the AI checks the environment and tells you only the one step you're missing — one thing at a time, no jargon. After you finish, say "done" and it re-checks automatically.

## Step 3: What to ask

| You want | Say |
| --- | --- |
| Business overview | "How is business today" |
| Pending orders | "Anything waiting to ship" |
| Shipped serials | "Which units shipped this month", "export to Excel" |
| Reverse lookup | "Customer reports SN SN-DEMO-0001, which order shipped it" |
| Inventory | "How much stock", "what's running low" |
| One order | "Did order xxx ship" |
| Refunds / purchases | "Show recent refunds" |
| What's possible | "What can you query" |

Results are a Chinese table plus a one-line summary. Say "export CSV" to save it — Excel opens it cleanly.

Full list: [Scenarios](SCENARIOS.en.md).

## Four things to remember

1. **Shuibao only needs to be open for install / login / authorize / renewal** — close it otherwise.
2. **Login expires in ~7 days** — the AI will remind you to log in again; authorization stays.
3. **Everyone uses their own account** — the package is shareable, credentials aren't.
4. **It's read-only** — it can't and won't ship orders, approve, or change records.

## Stuck?

- Check the [FAQ](FAQ.en.md) first — most questions are there.
- Still stuck: open an Issue with the English error code and your environment (OS / Shuibao version). **Mask account names, serial numbers, and customer info in logs first.**

## Developers

To deploy from source, package, or contribute: [Packaging](MARKETPLACE.en.md) and [Contributing](../CONTRIBUTING.md).
