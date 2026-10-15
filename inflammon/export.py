"""Write the committed JSON snapshot the static dashboard reads."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from inflammon import __version__
from inflammon.taxonomy import DISCLAIMER

SNAPSHOT_DIRS = (Path("data/snapshot"), Path("web/data"))


def write_snapshot(payloads: dict[str, Any]) -> list[Path]:
    written: list[Path] = []
    for directory in SNAPSHOT_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
        for name, payload in payloads.items():
            path = directory / name
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
            written.append(path)
    return written


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def manifest(
    *,
    generated_at: str,
    sources: list[dict[str, Any]],
    faers: dict[str, Any],
    validation: dict[str, Any],
    signal_rows: int,
    high_signals: int,
    new_high_signals: int,
    baseline_run: bool,
) -> dict[str, Any]:
    return {
        "product": "Inflammation Signal Monitor",
        "version": __version__,
        "generated_at": generated_at,
        "refresh_cadence": "weekly",
        "spike_grain": "week",
        "disclaimer": DISCLAIMER,
        "openfda_last_updated": faers.get("last_updated"),
        "faers_report_total": faers.get("database_n"),
        "signal_rows": signal_rows,
        "high_signal_rows": high_signals,
        "new_high_signals": new_high_signals,
        "high_signal_baseline_run": baseline_run,
        "validation_recovered": validation.get("recovered"),
        "validation_tested": validation.get("tested"),
        "sources": sources,
        "not_medical_advice": True,
    }
