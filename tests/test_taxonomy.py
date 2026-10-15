"""Search clauses stay quoted, and the validation panel covers the three known signals."""

from inflammon.taxonomy import VALIDATION_CHECKS, class_search_clause, drug_search_clause


def test_generic_name_with_a_space_is_quoted():
    clause = drug_search_clause(["CERTOLIZUMAB PEGOL"])
    assert clause == 'patient.drug.openfda.generic_name.exact:"CERTOLIZUMAB PEGOL"'


def test_class_clause_joins_ingredients():
    clause = class_search_clause("jak_inhibitor")
    assert "TOFACITINIB" in clause
    assert "UPADACITINIB" in clause
    assert "BARICITINIB" in clause
    assert " OR " in clause
    assert clause.startswith("(") and clause.endswith(")")


def test_validation_panel_covers_jak_tnf_and_nsaid():
    ids = {item["id"] for item in VALIDATION_CHECKS}
    assert "jak_vs_tnf_pulmonary_embolism" in ids
    assert "jak_vs_tnf_myocardial_infarction" in ids
    assert "tnf_tuberculosis" in ids
    assert "nsaid_gi_haemorrhage" in ids
    jak = [item for item in VALIDATION_CHECKS if item["key"] == "jak_inhibitor"]
    assert all(item["comparator"] == "tnf_inhibitor" for item in jak)
    assert all(item["analysis"] == "active_comparator" for item in jak)
