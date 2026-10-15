"""PRR and ROR for a 2×2 spontaneous-report table.

The table is::

                 reaction     no reaction
    exposed         a             b
    comparator      c             d

Proportional reporting ratio (Evans, Waller, Davis; Pharmacoepidemiology
and Drug Safety, 2001)::

    PRR = (a / (a + b)) / (c / (c + d))

Reporting odds ratio::

    ROR = (a / b) / (c / d) = (a * d) / (b * c)

Intervals are the normal approximation on the log scale, using 1.96 as
the two-sided 95% quantile::

    SE(ln PRR) = sqrt(1/a - 1/(a+b) + 1/c - 1/(c+d))
    SE(ln ROR) = sqrt(1/a + 1/b + 1/c + 1/d)

When any observed cell is zero, every cell is increased by 0.5
(Haldane–Anscombe) before the ratios, intervals, and chi-square are
calculated. The result still reports the observed counts. Chi-square is
Pearson’s statistic on the same cells used for the ratio::

    χ² = N (ad - bc)² / ((a+b)(c+d)(a+c)(b+d))

Evans signal: observed a ≥ 3, PRR ≥ 2, and χ² ≥ 4.
ROR signal: observed a ≥ 3 and the lower 95% bound of the ROR is above 1.

These are measures of disproportionate reporting. They are not risk
ratios in a treated population.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

Z_95 = 1.96
EVANS_PRR = 2.0
EVANS_CHI2 = 4.0
EVANS_MIN_A = 3
HALDANE = 0.5


@dataclass(frozen=True)
class Disproportionality:
    a: int
    b: int
    c: int
    d: int
    prr: float | None
    prr_ci_low: float | None
    prr_ci_high: float | None
    ror: float | None
    ror_ci_low: float | None
    ror_ci_high: float | None
    chi2: float | None
    correction: str
    evans_signal: bool
    ror_signal: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def disproportionality(a: int, b: int, c: int, d: int) -> Disproportionality:
    """Compute PRR, ROR, intervals, chi-square, and signal flags.

    ``a``, ``b``, ``c`` and ``d`` are observed report counts and must be
    non-negative. A negative count means the margins were inconsistent
    and the caller should drop the row rather than clamp it.
    """
    if min(a, b, c, d) < 0:
        raise ValueError(f"2×2 counts must be non-negative, got {(a, b, c, d)}")

    correction = "none"
    aa, bb, cc, dd = float(a), float(b), float(c), float(d)
    if min(aa, bb, cc, dd) == 0:
        aa, bb, cc, dd = aa + HALDANE, bb + HALDANE, cc + HALDANE, dd + HALDANE
        correction = "haldane_anscombe_0.5"

    prr, prr_low, prr_high = _prr_ci(aa, bb, cc, dd)
    ror, ror_low, ror_high = _ror_ci(aa, bb, cc, dd)
    chi2 = _chi2(aa, bb, cc, dd)

    evans = (
        a >= EVANS_MIN_A
        and prr is not None
        and prr >= EVANS_PRR
        and chi2 is not None
        and chi2 >= EVANS_CHI2
    )
    ror_signal = a >= EVANS_MIN_A and ror_low is not None and ror_low > 1

    return Disproportionality(
        a=a,
        b=b,
        c=c,
        d=d,
        prr=_round(prr),
        prr_ci_low=_round(prr_low),
        prr_ci_high=_round(prr_high),
        ror=_round(ror),
        ror_ci_low=_round(ror_low),
        ror_ci_high=_round(ror_high),
        chi2=_round(chi2),
        correction=correction,
        evans_signal=evans,
        ror_signal=ror_signal,
    )


def database_table(
    exposure_n: int,
    pair_n: int,
    reaction_n: int,
    database_n: int,
) -> tuple[int, int, int, int]:
    """Build a database-wide 2×2 table.

    ``pair_n`` is reports with both the exposure and the reaction.
    ``reaction_n`` is reports with the reaction in the whole extract.
    """
    a = pair_n
    b = exposure_n - pair_n
    c = reaction_n - pair_n
    d = database_n - a - b - c
    return a, b, c, d


def active_comparator_table(
    exposure_n: int,
    exposure_pair_n: int,
    comparator_n: int,
    comparator_pair_n: int,
) -> tuple[int, int, int, int]:
    """Build a 2×2 table against an active comparator class.

    Reports that mention both classes are not removed. That overlap is
    small relative to these classes and is recorded as a limitation.
    """
    a = exposure_pair_n
    b = exposure_n - exposure_pair_n
    c = comparator_pair_n
    d = comparator_n - comparator_pair_n
    return a, b, c, d


def _prr_ci(a: float, b: float, c: float, d: float) -> tuple[float | None, float | None, float | None]:
    exposed = a + b
    others = c + d
    if exposed <= 0 or others <= 0 or a <= 0 or c <= 0:
        return None, None, None
    prr = (a / exposed) / (c / others)
    se = math.sqrt(1 / a - 1 / exposed + 1 / c - 1 / others)
    return _log_interval(prr, se)


def _ror_ci(a: float, b: float, c: float, d: float) -> tuple[float | None, float | None, float | None]:
    if min(a, b, c, d) <= 0:
        return None, None, None
    ror = (a / b) / (c / d)
    se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    return _log_interval(ror, se)


def _log_interval(estimate: float, se: float) -> tuple[float, float, float]:
    log_est = math.log(estimate)
    return estimate, math.exp(log_est - Z_95 * se), math.exp(log_est + Z_95 * se)


def _chi2(a: float, b: float, c: float, d: float) -> float | None:
    n = a + b + c + d
    row1 = a + b
    row2 = c + d
    col1 = a + c
    col2 = b + d
    if n <= 0 or row1 <= 0 or row2 <= 0 or col1 <= 0 or col2 <= 0:
        return None
    return n * (a * d - b * c) ** 2 / (row1 * row2 * col1 * col2)


def _round(value: float | None) -> float | None:
    if value is None or math.isnan(value) or math.isinf(value):
        return None
    return round(value, 6)
