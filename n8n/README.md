# Optional n8n example

GitHub Actions (`.github/workflows/weekly-refresh.yml`) is the Monday path. It builds the draft, and the owner approves the send. This n8n workflow is an example you can import on a self-hosted instance. It is not required, and it is not what sends the briefing.

`ism-weekly-refresh.json` runs **once a week**, Monday at 12:00 in the workflow timezone. The file sets that timezone to UTC. Import it with the n8n workflow menu, then set two environment variables on the n8n host:

- `INFLAMMON_REPO` — absolute path of this repository
- `SIGNAL_WEBHOOK_URL` — where new high signals should be posted

The workflow runs `make refresh`, then splits.

- One branch reads `data/snapshot/high_signals_new.json` and posts only when that file lists signals that were not in the previous baseline. The first successful snapshot establishes the baseline and does not call the webhook.
- The other branch runs `make newsletter`, which archives the issue and does not email anyone. Sending stays on GitHub Actions after the owner approves the draft, unless `NEWSLETTER_AUTO_SEND=1` and `NEWSLETTER_DRY_RUN=0`.

Execute Command and local file reads require self-hosted n8n. n8n Cloud cannot see this repository’s disk.

The workflow is imported inactive. Leave it inactive unless you want a second copy of the weekly archive.
