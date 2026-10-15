"""Weekly spike detection for publication, trial, and alert counts.

A point is a spike when both of these hold against a trailing baseline
that does not include the point itself:

- the z-score is at least 2, using the sample standard deviation
- the count is at least 1.5 times the baseline mean

The baseline needs at least four earlier weeks. A flat baseline (standard
deviation of zero) or a mean of zero is reported as not a spike, with a
reason, rather than treated as infinite evidence.

This is a screen for a weekly refresh. It is not a changepoint model and
it does not adjust for seasonality.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta

Z_THRESHOLD = 2.0
RATIO_THRESHOLD = 1.5
MIN_BASELINE = 4
DEFAULT_WINDOW = 8


@dataclass(frozen=True)
class SpikeResult:
    count: float
    baseline_n: int
    baseline_mean: float | None
    baseline_sd: float | None
    z: float | None
    ratio: float | None
    is_spike: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def detect_latest_spike(
    counts: list[float],
    *,
    z_threshold: float = Z_THRESHOLD,
    ratio_threshold: float = RATIO_THRESHOLD,
    min_baseline: int = MIN_BASELINE,
) -> SpikeResult:
    """Test the last count against every preceding count."""
    if len(counts) < min_baseline + 1:
        return SpikeResult(
            count=float(counts[-1]) if counts else 0.0,
            baseline_n=max(len(counts) - 1, 0),
            baseline_mean=None,
            baseline_sd=None,
            z=None,
            ratio=None,
            is_spike=False,
            reason="insufficient_baseline",
        )
    return _test_point(
        counts[-1],
        counts[:-1],
        z_threshold=z_threshold,
        ratio_threshold=ratio_threshold,
    )


def trailing_spikes(
    counts: list[float],
    *,
    window: int = DEFAULT_WINDOW,
    z_threshold: float = Z_THRESHOLD,
    ratio_threshold: float = RATIO_THRESHOLD,
) -> list[SpikeResult]:
    """Test each point against the preceding ``window`` points only.

    The first ``window`` results have no spike flag because the baseline
    is not yet available. Later points never see future counts.
    """
    if window < MIN_BASELINE:
        raise ValueError(f"window must be at least {MIN_BASELINE}")
    results: list[SpikeResult] = []
    for index, count in enumerate(counts):
        if index < window:
            results.append(
                SpikeResult(
                    count=float(count),
                    baseline_n=index,
                    baseline_mean=None,
                    baseline_sd=None,
                    z=None,
                    ratio=None,
                    is_spike=False,
                    reason="insufficient_baseline",
                )
            )
            continue
        results.append(
            _test_point(
                count,
                counts[index - window : index],
                z_threshold=z_threshold,
                ratio_threshold=ratio_threshold,
            )
        )
    return results


def complete_iso_weeks(today: date, n: int) -> list[tuple[date, date]]:
    """Return ``n`` complete Monday–Sunday weeks ending before ``today``.

    The week that contains ``today`` is still open, so it is excluded.
    Weeks are oldest first.
    """
    if n < 1:
        return []
    this_monday = today - timedelta(days=today.weekday())
    end = this_monday - timedelta(days=1)
    start = end - timedelta(days=6)
    weeks: list[tuple[date, date]] = []
    for _ in range(n):
        weeks.append((start, end))
        end = start - timedelta(days=1)
        start = end - timedelta(days=6)
    weeks.reverse()
    return weeks


def iso_week_label(start: date) -> str:
    iso = start.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _test_point(
    count: float,
    baseline: list[float],
    *,
    z_threshold: float,
    ratio_threshold: float,
) -> SpikeResult:
    n = len(baseline)
    mean = sum(baseline) / n
    variance = sum((value - mean) ** 2 for value in baseline) / (n - 1)
    sd = math.sqrt(variance)
    ratio = (count / mean) if mean > 0 else None
    if mean <= 0:
        return SpikeResult(float(count), n, mean, sd, None, ratio, False, "zero_baseline_mean")
    if sd == 0:
        # A perfectly flat baseline has an undefined z-score. A count that
        # still clears the ratio threshold is a spike; an equal count is not.
        is_spike = ratio is not None and count > mean and ratio >= ratio_threshold
        return SpikeResult(
            float(count),
            n,
            mean,
            sd,
            None,
            round(ratio, 6) if ratio is not None else None,
            is_spike,
            "spike_above_flat_baseline" if is_spike else "flat_baseline",
        )
    z = (count - mean) / sd
    is_spike = z >= z_threshold and ratio is not None and ratio >= ratio_threshold
    return SpikeResult(
        count=float(count),
        baseline_n=n,
        baseline_mean=round(mean, 6),
        baseline_sd=round(sd, 6),
        z=round(z, 6),
        ratio=round(ratio, 6) if ratio is not None else None,
        is_spike=is_spike,
        reason="spike" if is_spike else "within_baseline",
    )
