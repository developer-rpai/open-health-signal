"""Hand-checked 2×2 tables for PRR, ROR, and the Evans rule."""

import math

import pytest

from inflammon.signals.disproportionality import (
    active_comparator_table,
    database_table,
    disproportionality,
)


def test_prr_and_ror_match_hand_calculation():
    #            reaction   no reaction
    # exposed        20           80
    # other         100         9800
    # PRR = (20/100) / (100/9900) = 0.2 * 99 = 19.8
    # ROR = (20/80) / (100/9800) = 0.25 * 98 = 24.5
    result = disproportionality(20, 80, 100, 9800)
    assert result.prr == pytest.approx(19.8)
    assert result.ror == pytest.approx(24.5)
    assert result.correction == "none"
    assert result.prr_ci_low < result.prr < result.prr_ci_high
    assert result.ror_ci_low < result.ror < result.ror_ci_high

    se_prr = math.sqrt(1 / 20 - 1 / 100 + 1 / 100 - 1 / 9900)
    expected_low = math.exp(math.log(19.8) - 1.96 * se_prr)
    expected_high = math.exp(math.log(19.8) + 1.96 * se_prr)
    # The published result is rounded to 6 decimal places.
    assert result.prr_ci_low == pytest.approx(expected_low, abs=5e-7)
    assert result.prr_ci_high == pytest.approx(expected_high, abs=5e-7)

    se_ror = math.sqrt(1 / 20 + 1 / 80 + 1 / 100 + 1 / 9800)
    assert result.ror_ci_low == pytest.approx(math.exp(math.log(24.5) - 1.96 * se_ror), abs=5e-7)
    assert result.ror_ci_high == pytest.approx(math.exp(math.log(24.5) + 1.96 * se_ror), abs=5e-7)

    # χ² = 10000 * (20*9800 - 80*100)^2 / (100 * 9900 * 120 * 9880)
    numerator = 10000 * (20 * 9800 - 80 * 100) ** 2
    denominator = 100 * 9900 * 120 * 9880
    assert result.chi2 == pytest.approx(numerator / denominator)
    assert result.evans_signal is True
    assert result.ror_signal is True


def test_small_cell_a_is_not_an_evans_signal():
    # PRR = (2/10) / (10/1010) = 20.2, but a = 2 is below the Evans minimum of 3.
    result = disproportionality(2, 8, 10, 1000)
    assert result.prr == pytest.approx(20.2)
    assert result.evans_signal is False
    assert result.ror_signal is False


def test_prr_below_two_is_not_an_evans_signal():
    # PRR = (10/100) / (100/1000) = 1.0
    result = disproportionality(10, 90, 100, 900)
    assert result.prr == pytest.approx(1.0)
    assert result.evans_signal is False
    assert result.ror_signal is False


def test_haldane_correction_when_a_cell_is_zero():
    result = disproportionality(5, 15, 0, 100)
    assert result.correction == "haldane_anscombe_0.5"
    # Corrected cells 5.5, 15.5, 0.5, 100.5
    prr = (5.5 / 21) / (0.5 / 101)
    assert result.prr == pytest.approx(prr)
    assert result.a == 5
    assert result.prr_ci_low > 1
    assert result.evans_signal is True


def test_negative_count_is_rejected():
    with pytest.raises(ValueError):
        disproportionality(5, -1, 3, 10)


def test_database_table_margins():
    assert database_table(100, 10, 50, 1000) == (10, 90, 40, 860)


def test_active_comparator_table():
    assert active_comparator_table(200, 20, 800, 40) == (20, 180, 40, 760)
