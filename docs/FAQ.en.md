# FAQ

## Setup & login

**Q: Does Shuibao need to stay open?**
No. Only for four moments: install, login, authorize, and renewal when login expires. Close it otherwise.

**Q: Why does the AI ask me to install things before answering my first question?**
Because JST is a private ERP — account, login, and authorization can't be skipped. The AI checks the environment and tells you only the one missing step. After setup, just ask directly.

**Q: Login expired. Do I need to authorize again?**
No. Just reopen Shuibao and log in (~7 days). Authorization is one-time, account-level.

**Q: Where do I authorize?**
Shuibao → "Connection Management" (not "Settings") → find JST → Authorize. You must do it yourself.

**Q: It installed a "guard service" and a bunch of DingTalk skills — what are those?**
Normal components of the new Shuibao client, unrelated to JST queries. Allow/ignore them.

**Q: Check step 3 "query program ready" keeps failing.**
The "JST ERP Assistant" skill inside Shuibao isn't installed. Shuibao → "Skills"/"Skill Marketplace" → find it → install; if already installed, disable then re-enable, wait 30s. Restart Shuibao if still stuck.

**Q: Can I use it without a JST account?**
No. Your company must create one — nobody can skip this.

## Queries & results

**Q: Can it query Douyin / other backends?**
No. JST ERP only.

**Q: Where are serial numbers? Why aren't they in the order endpoint?**
Serials live on sales outbound records, not orders. Say "list shipped serials" or "which order shipped this SN".

**Q: Too many / too few results?**
- Too many: only the first 50 rows show in chat — say "export CSV" for the full set (Excel-friendly).
- Too few: default window is 7 days (30/90 for some scenarios) — say "last 90 days"; max 180 per call, longer is auto-segmented.

**Q: Why don't the numbers match the ERP?**
The tool counts by record "modified time", not order/outbound time, and dedupes records across windows. For important decisions, trust the ERP's raw data.

**Q: It can't find the document type I want.**
Say "can you query X" to find the endpoint name, then "query X". All 36 read-only endpoints are supported.

## Read-only & security

**Q: Can it ship orders / approve records?**
No, and it won't. The 53 write endpoints are blocked in code with `READONLY_MODE`.

**Q: Does it upload my credentials or data?**
No. Credentials are read locally, passed to the local query program, never uploaded, written into the project, or committed. See [SECURITY.md](../SECURITY.md).

**Q: Can several people share one account?**
Technically yes, but not advised — ERP activity logs are attributed to the account owner. Use your own account.

**Q: It says "python command not found".**
Rare environments lack `python`. Enable the same-name connector (the platform prepares Node), then use `jst_check` etc. — same wording.

## Developers

**Q: Does it work right after clone?**
`python tools/verify_offline.py` and `python -m pytest tests/ -q` need no Shuibao, network, or credentials. Only `verify_online.py` needs a set-up Shuibao.

**Q: Upstream upgraded and endpoints changed?**
Run `python tools/refresh_catalog.py`, then `python tools/build.py`. See [Recognition report](RECOGNITION.en.md).
