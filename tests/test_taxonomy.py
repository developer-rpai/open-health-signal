"""Search clauses stay quoted, and the validation panel covers the three known signals."""

import json
import re
from pathlib import Path

from inflammon.taxonomy import CONDITIONS, VALIDATION_CHECKS, class_search_clause, drug_search_clause

# Official MeSH descriptor, not the entry term. "rheumatoid arthritis"[MeSH Terms]
# is not a heading, so PubMed esearch returns 0 for every year.
_MESH_QUERY = re.compile(r'^"[^"]+"\[MeSH Terms\]$')


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


def test_condition_pubmed_terms_are_well_formed_mesh_queries():
    assert CONDITIONS
    for topic in CONDITIONS:
        assert _MESH_QUERY.fullmatch(topic.pubmed_term), topic.key
        year_query = f"({topic.pubmed_term}) AND 2024[pdat]"
        assert year_query.startswith('("')
        assert year_query.endswith('[pdat]')
        assert "[MeSH Terms]" in year_query


def test_rheumatoid_arthritis_uses_the_mesh_descriptor():
    ra = next(topic for topic in CONDITIONS if topic.key == "rheumatoid_arthritis")
    assert ra.pubmed_term == '"Arthritis, Rheumatoid"[MeSH Terms]'


def test_publication_year_counts_are_nonzero_for_each_condition():
    keys = {topic.key for topic in CONDITIONS}
    for path in (Path("web/data/trends.json"), Path("data/snapshot/trends.json")):
        rows = json.loads(path.read_text())["publications"]
        by_topic: dict[str, list[int]] = {key: [] for key in keys}
        for row in rows:
            if row.get("grain") == "year" and row["topic"] in by_topic:
                by_topic[row["topic"]].append(row["count"])
        for key, counts in by_topic.items():
            assert counts, f"{path} missing {key}"
            assert all(count > 0 for count in counts), (path, key, counts)


def test_validation_panel_covers_jak_tnf_and_nsaid():
    ids = {item["id"] for item in VALIDATION_CHECKS}
    assert "jak_vs_tnf_pulmonary_embolism" in ids
    assert "jak_vs_tnf_myocardial_infarction" in ids
    assert "tnf_tuberculosis" in ids
    assert "nsaid_gi_haemorrhage" in ids
    jak = [item for item in VALIDATION_CHECKS if item["key"] == "jak_inhibitor"]
    assert all(item["comparator"] == "tnf_inhibitor" for item in jak)
    assert all(item["analysis"] == "active_comparator" for item in jak)
