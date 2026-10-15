# FDA and state safety page stub

Public pages that have no API — the FDA Drug Safety Communications index, and state health-department advisories such as California CDPH and the New York State Department of Health — change their HTML without notice. This Actor is the scraper for those pages.

It fetches each start URL once, reads anchor text with the Python HTML parser, and stores `title`, `url`, `sourcePage`, and `extractedAt` in the dataset. It does not run JavaScript and it does not follow every link on the site.

## Input

`startUrls` defaults to the FDA Drug Safety Communications page. Add a state advisory URL when you want that page included. `maxItems` caps the dataset (default 40).

## Local run

From this directory, with the [Apify CLI](https://docs.apify.com/cli/) installed and `APIFY_TOKEN` set if you need platform storage:

```bash
mkdir -p storage/key_value_stores/default
printf '%s\n' '{"startUrls":[{"url":"https://www.fda.gov/drugs/drug-safety-and-availability/drug-safety-communications"}],"maxItems":20}' > storage/key_value_stores/default/INPUT.json
apify run
```

The weekly `inflammon` package still parses the FDA index itself. Use this Actor when that page, or a state page, drifts.
