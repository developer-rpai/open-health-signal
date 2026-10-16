"""Newsletter schedule.

``weekly`` is the default: Monday 12:00 UTC. ``daily`` is a temporary test
mode: every day at 14:00 UTC. Approval, suppression, and dry-run do not
change with the cadence.
"""

from __future__ import annotations

import os

WEEKLY = "weekly"
DAILY = "daily"
WEEKLY_CRON = "0 12 * * 1"
DAILY_CRON = "0 14 * * *"


def newsletter_cadence(value: str | None = None) -> str:
    """Return ``daily`` or ``weekly``. Empty means weekly. Anything else errors."""
    raw = os.environ.get("NEWSLETTER_CADENCE", "") if value is None else value
    cadence = str(raw).strip().lower()
    if cadence in {"", WEEKLY}:
        return WEEKLY
    if cadence == DAILY:
        return DAILY
    raise ValueError(f"NEWSLETTER_CADENCE must be daily or weekly, got {raw!r}")


def schedule_matches(event_name: str, schedule: str | None, cadence: str | None = None) -> bool:
    """Whether this GitHub event should build or send.

    ``workflow_dispatch`` and ``repository_dispatch`` always match, so a manual
    run and an owner approval still proceed. A cron matches only its cadence.
    """
    resolved = newsletter_cadence(cadence)
    if event_name != "schedule":
        return True
    expected = DAILY_CRON if resolved == DAILY else WEEKLY_CRON
    return (schedule or "") == expected
