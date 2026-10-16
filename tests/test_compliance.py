"""Compliance wording, openFDA key handling, and PubMed request identity."""

from __future__ import annotations

import json

from inflammon.compliance import FDA_CAVEAT, RESEARCH_LINE
from inflammon.http_client import openfda_request_params
from inflammon.ingest.pubmed import eutils_params


def test_caveat_is_the_fda_sentence():
    assert FDA_CAVEAT.startswith("There is no certainty that the reported event was actually due to the product.")
    assert "cannot be used to estimate the incidence of these events." in FDA_CAVEAT
    assert RESEARCH_LINE == (
        "For research and informational purposes only. Not medical advice. "
        "Do not stop or change any medication without talking to your doctor."
    )
    assert "causes" not in RESEARCH_LINE.lower()


def test_openfda_key_is_sent_and_kept_out_of_the_cache(monkeypatch):
    monkeypatch.setenv("OPENFDA_API_KEY", "secret-openfda-key")
    cache_params, request_params = openfda_request_params(
        "https://api.fda.gov/drug/event.json",
        {"search": "patient.reaction.reactionmeddrapt:HEADACHE", "limit": 1},
    )
    assert "api_key" not in cache_params
    assert request_params["api_key"] == "secret-openfda-key"
    assert request_params["search"] == cache_params["search"]
    untouched, same = openfda_request_params("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", {"db": "pubmed"})
    assert "api_key" not in same
    assert untouched == same


def test_eutils_sends_tool_and_email(monkeypatch):
    monkeypatch.setenv("NCBI_TOOL", "inflammon")
    monkeypatch.setenv("NCBI_EMAIL", "research@example.com")
    params = eutils_params()
    assert params["tool"] == "inflammon"
    assert params["email"] == "research@example.com"
    assert params["db"] == "pubmed"
    assert "abstract" not in json.dumps(params)


def test_eutils_omits_a_blank_email(monkeypatch):
    monkeypatch.delenv("NCBI_EMAIL", raising=False)
    params = eutils_params()
    assert params["tool"] == "inflammon"
    assert "email" not in params
