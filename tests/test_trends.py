"""Weekly spike rule and ISO week windows."""

from datetime import date

from inflammon.signals.trends import complete_iso_weeks, detect_latest_spike, trailing_spikes


def test_complete_weeks_are_monday_to_sunday_and_exclude_the_open_week():
    # 15 October 2026 is a Thursday. The open week starts 12 October.
    weeks = complete_iso_weeks(date(2026, 10, 15), 16)
    assert len(weeks) == 16
    assert weeks[-1] == (date(2026, 10, 5), date(2026, 10, 11))
    for start, end in weeks:
        assert start.weekday() == 0
        assert end.weekday() == 6
        assert (end - start).days == 6
    assert weeks[1][0] - weeks[0][1] == __import__("datetime").timedelta(days=1)


def test_latest_point_spike():
    result = detect_latest_spike([10, 12, 9, 11, 10, 13, 11, 40])
    assert result.is_spike is True
    assert result.reason == "spike"
    assert result.z is not None and result.z > 2
    assert result.ratio is not None and result.ratio > 1.5


def test_quiet_series_is_not_a_spike():
    result = detect_latest_spike([10, 11, 10, 12, 11, 10, 11, 12])
    assert result.is_spike is False
    assert result.reason == "within_baseline"


def test_short_series_does_not_invent_a_spike():
    result = detect_latest_spike([1, 9, 1])
    assert result.is_spike is False
    assert result.reason == "insufficient_baseline"


def test_trailing_window_does_not_use_future_counts():
    counts = [10, 10, 10, 10, 10, 10, 10, 10, 40, 10]
    results = trailing_spikes(counts, window=8)
    assert results[8].is_spike is True
    assert results[9].is_spike is False
    assert all(result.is_spike is False for result in results[:8])


def test_flat_baseline_is_not_an_infinite_z_score():
    result = detect_latest_spike([5, 5, 5, 5, 5])
    assert result.is_spike is False
    assert result.reason == "flat_baseline"
    jump = detect_latest_spike([5, 5, 5, 5, 20])
    assert jump.is_spike is True
    assert jump.reason == "spike_above_flat_baseline"
