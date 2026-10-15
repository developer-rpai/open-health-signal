# Weekly n8n workflow

`ism-weekly-refresh.json` is an export for self-hosted n8n.

It runs **once a week**, Monday at 12:00 in the workflow timezone. The file sets that timezone to UTC. Import it with the n8n workflow menu, then set two environment variables on the n8n host:

- `INFLAMMON_REPO` — absolute path of this repository
- `SIGNAL_WEBHOOK_URL` — where new high signals should be posted

The workflow runs `make refresh`, reads `data/snapshot/high_signals_new.json`, and posts only when that file lists signals that were not in the previous baseline. The first successful snapshot establishes the baseline and does not call the webhook.

Execute Command and local file reads require self-hosted n8n. n8n Cloud cannot see this repository’s disk.

The workflow is imported inactive. Turn it on after the environment variables are set.
