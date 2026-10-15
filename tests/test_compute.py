"""Signal rows from a hand-built 2×2 table, with no network."""

from inflammon.compute import build_signal_rows, build_validation


def test_class_row_matches_the_hand_worked_example():
    rows = build_signal_rows(
        database_n=10000,
        exposures=[
            {
                "scope": "class",
                "key": "nsaid",
                "label": "NSAID",
                "drug_class": "nsaid",
                "report_count": 100,
            }
        ],
        pairs=[
            {
                "scope": "class",
                "key": "nsaid",
                "drug_class": "nsaid",
                "reaction": "GASTROINTESTINAL HAEMORRHAGE",
                "pair_count": 20,
                "preset": True,
            }
        ],
        reaction_totals={"GASTROINTESTINAL HAEMORRHAGE": 120},
    )
    assert len(rows) == 1
    assert rows[0]["a"] == 20
    assert rows[0]["b"] == 80
    assert rows[0]["c"] == 100
    assert rows[0]["d"] == 9800
    assert rows[0]["prr"] == 19.8
    assert rows[0]["evans_signal"] is True


def test_missing_validation_count_is_not_recovered():
    report = build_validation([])
    assert report["recovered"] == 0
    assert report["tested"] > 0
    assert all(check["recovered"] is False for check in report["checks"])
    assert all(check["reason"] == "missing_counts" for check in report["checks"])
