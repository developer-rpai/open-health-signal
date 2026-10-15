# Contributing

Inflammation Signal Monitor is public-health software. Changes should stay
reproducible, cite their sources, and keep the “not medical advice” boundary intact.

## What helps

- A failing test for a signal-math bug, then the fix. PRR, ROR, chi-square, and the weekly spike rule live in `inflammon/signals/` and are covered by `tests/`.
- An ingester change that records a source failure instead of inventing a count.
- Dashboard copy that states a limitation in the same place as the chart.

## Local setup

```bash
make install
make test
make refresh    # weekly pull; uses the HTTP cache if you already have one
cd web && npm run dev -- --hostname 127.0.0.1 --port 43123
```

`make refresh` is the same job the Monday cron, GitHub Actions workflow, and n8n workflow run. Do not add a daily schedule.

## Data rules

- Public APIs only, unless a page has no API. Those pages belong in `apify/fda-safety-pages`, not in an unattended scraper with no schema.
- Store PubMed identifiers, titles, journals, and dates. Do not commit abstracts.
- Do not commit `data/raw/` or `data/inflammon.duckdb`. Commit the JSON snapshot under `data/snapshot/` and `web/data/` when a refresh is meant to be published.
- If an API fails, say so in the source status. Do not fill the gap with synthetic rows.

## Pull requests

Run `make test` and, if you touched the dashboard, `make build`. Describe which source or formula changed and how you checked it.
