#!/usr/bin/env bash
# Weekly refresh for Inflammation Signal Monitor.
# Crontab, Monday 12:00 UTC:
#   0 12 * * 1 /path/to/repo/scripts/weekly_refresh.sh
set -euo pipefail
cd "$(dirname "$0")/.."
make refresh
make newsletter
