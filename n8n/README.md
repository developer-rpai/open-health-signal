# Weekly n8n workflow

`ism-weekly-refresh.json` is an export for self-hosted n8n.

It runs **once a week**, Monday at 12:00 in the workflow timezone. The file sets that timezone to UTC. Import it with the n8n workflow menu, then set two environment variables on the n8n host:

- `INFLAMMON_REPO` — absolute path of this repository
- `SIGNAL_WEBHOOK_URL` — where new high signals should be posted

The workflow runs `make refresh`, then splits.

- One branch reads `data/snapshot/high_signals_new.json` and posts only when that file lists signals that were not in the previous baseline. The first successful snapshot establishes the baseline and does not call the webhook.
- The other branch runs `make newsletter` even when there are no new high signals. That command archives the issue. It emails subscribers only when `NEWSLETTER_SEND=1` on the n8n host. Buttondown also needs `BUTTONDOWN_API_KEY`. The Resend alternative needs `NEWSLETTER_PROVIDER=resend`, `RESEND_API_KEY`, `RESEND_AUDIENCE_ID`, and `NEWSLETTER_FROM`. Set `NEWSLETTER_POSTAL_ADDRESS` for the issue footer. The refresh reads `OPENFDA_API_KEY` and `NCBI_EMAIL` when they are set on the host. See the repository README for which value is public and which is a secret.

Execute Command and local file reads require self-hosted n8n. n8n Cloud cannot see this repository’s disk.

The workflow is imported inactive. Turn it on after the environment variables are set.
