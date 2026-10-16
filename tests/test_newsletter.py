"""Newsletter diff, rendering, and dry-run send."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from inflammon.cli import main
from inflammon.newsletter.cadence import DAILY_CRON, WEEKLY_CRON, newsletter_cadence, schedule_matches
from inflammon.newsletter.compose import compose_issue, fingerprint, load_snapshot
from inflammon.newsletter.publish import NewsletterSendError, build_and_save, send_resend
from inflammon.newsletter.render import render_html, render_text
from newsletter.resend.handler import confirm_token, handle_confirm, handle_subscribe

ROOT = Path(__file__).resolve().parents[1]
DISCLAIMER = "Not medical advice. Test disclaimer."


def _signal(**overrides) -> dict:
    row = {
        "scope": "class",
        "drug": None,
        "drug_label": None,
        "drug_class": "nsaid",
        "drug_class_label": "NSAID",
        "reaction": "GASTRIC ULCER",
        "analysis": "database",
        "comparator": "all_faers",
        "comparator_label": "All other FAERS reports",
        "preset": True,
        "admin_term": False,
        "indication_term": False,
        "prr": 2.0,
        "prr_ci_low": 1.8,
        "prr_ci_high": 2.2,
        "ror": 2.1,
        "ror_ci_low": 1.9,
        "ror_ci_high": 2.3,
        "evans_signal": True,
        "ror_signal": True,
        "a": 10,
    }
    row.update(overrides)
    return row


def _snapshot(**overrides) -> dict:
    base = {
        "manifest": {
            "generated_at": "2026-10-22T12:00:00+00:00",
            "openfda_last_updated": "2026-07-30",
            "disclaimer": DISCLAIMER,
        },
        "alerts": [],
        "recalls": [],
        "signals": [],
        "validation": {"checks": []},
        "publications": [],
        "trials": [],
    }
    base.update(overrides)
    return base


def _titles(issue: dict, section_id: str) -> list[str]:
    section = next(item for item in issue["sections"] if item["id"] == section_id)
    return [item["title"] for item in section["items"]]


def _section(issue: dict, section_id: str) -> dict:
    return next(item for item in issue["sections"] if item["id"] == section_id)


def test_weekly_diff_keeps_new_and_strengthened_only():
    earlier = _snapshot(
        manifest={
            "generated_at": "2026-10-15T12:00:00+00:00",
            "openfda_last_updated": "2026-07-30",
            "disclaimer": DISCLAIMER,
        },
        alerts=[{"title": "Old notice", "link": "https://example.com/old", "source": "FDA", "tags": ["nsaid"]}],
        recalls=[{"recall_number": "D-OLD", "product_description": "Old product", "classification": "Class II", "reason": "Old"}],
        signals=[
            _signal(reaction="UNCHANGED EVENT", prr=2.0),
            _signal(reaction="STRONGER EVENT", prr=2.0),
            _signal(reaction="NOT QUITE", prr=2.0),
        ],
        trials=[{"nct_id": "NCT000", "title": "Old trial", "topic": "psoriasis", "link": "https://clinicaltrials.gov/study/NCT000"}],
        publications=[{"pmid": "1", "title": "Old paper", "topic": "psoriasis", "link": "https://pubmed.ncbi.nlm.nih.gov/1/"}],
    )
    current = _snapshot(
        alerts=[
            {"title": "Old notice", "link": "https://example.com/old", "source": "FDA", "tags": ["nsaid"]},
            {"title": "Brand new notice", "link": "https://example.com/new", "source": "FDA", "published": "2026-10-20", "tags": ["jak_inhibitor"]},
            {"title": '<script>alert("x")</script>', "link": "https://example.com/xss", "source": "FDA", "tags": ["nsaid"]},
        ],
        recalls=[
            {"recall_number": "D-OLD", "product_description": "Old product", "classification": "Class II", "reason": "Old"},
            {"recall_number": "D-NEW", "product_description": "New lot", "classification": "Class I", "reason": "Particulate", "recalling_firm": "Example"},
        ],
        signals=[
            _signal(reaction="UNCHANGED EVENT", prr=2.1),
            _signal(reaction="STRONGER EVENT", prr=2.5, prr_ci_low=2.2, prr_ci_high=2.8),
            _signal(reaction="NOT QUITE", prr=2.49),
            _signal(reaction="FRESH EVENT", drug_class="tnf_inhibitor", prr=4.0),
            _signal(reaction="ADMIN NOISE", admin_term=True, prr=9.0),
            _signal(reaction="OFF LABEL INDICATION", indication_term=True, prr=9.0),
            _signal(reaction="NOT PRESET", preset=False, prr=9.0),
        ],
        trials=[
            {"nct_id": "NCT000", "title": "Old trial", "topic": "psoriasis"},
            {"nct_id": "NCT111", "title": "New psoriasis trial", "topic": "psoriasis", "status": "RECRUITING", "link": "https://clinicaltrials.gov/study/NCT111"},
        ],
        publications=[
            {"pmid": "1", "title": "Old paper", "topic": "psoriasis"},
            {"pmid": "2", "title": "New lupus paper", "topic": "lupus", "journal": "Lancet", "link": "https://pubmed.ncbi.nlm.nih.gov/2/"},
        ],
    )
    issue = compose_issue(current, fingerprint(earlier), site_url="http://127.0.0.1:43123")
    assert issue["kind"] == "weekly"
    assert "Brand new notice" in _titles(issue, "alerts")
    assert "Old notice" not in _titles(issue, "alerts")
    assert any("New lot" in title for title in _titles(issue, "recalls"))
    assert not any("Old product" in title for title in _titles(issue, "recalls"))
    signal_titles = _titles(issue, "signals")
    assert any("Fresh Event" in title for title in signal_titles)
    assert any("Stronger Event" in title for title in signal_titles)
    assert not any("Unchanged Event" in title for title in signal_titles)
    assert not any("Not Quite" in title for title in signal_titles)
    assert not any("Admin Noise" in title for title in signal_titles)
    assert not any("Off Label" in title for title in signal_titles)
    assert not any("Not Preset" in title for title in signal_titles)
    assert any("New psoriasis trial" in title for title in _titles(issue, "trials"))
    assert not any("Old trial" in title for title in _titles(issue, "trials"))
    assert any("New lupus paper" in title for title in _titles(issue, "papers"))
    stronger = next(item for item in _section(issue, "signals")["items"] if "Stronger Event" in item["title"])
    assert "at least 25% higher" in stronger["body"]
    assert "reported more often than expected" in stronger["body"]
    assert "disproportionality signal" in stronger["body"]
    assert "causes" not in stronger["body"].lower()
    fresh = next(item for item in _section(issue, "signals")["items"] if "Fresh Event" in item["title"])
    assert "Evans screen" in fresh["body"]
    assert issue["headline"].startswith("TNF inhibitors:")


def test_cadence_defaults_to_weekly_and_rejects_other_values(monkeypatch):
    monkeypatch.delenv("NEWSLETTER_CADENCE", raising=False)
    assert newsletter_cadence() == "weekly"
    assert newsletter_cadence("") == "weekly"
    assert newsletter_cadence("WEEKLY") == "weekly"
    monkeypatch.setenv("NEWSLETTER_CADENCE", "daily")
    assert newsletter_cadence() == "daily"
    with pytest.raises(ValueError, match="daily or weekly"):
        newsletter_cadence("hourly")


def test_schedule_matches_only_the_selected_cadence():
    assert schedule_matches("schedule", WEEKLY_CRON, "weekly")
    assert not schedule_matches("schedule", DAILY_CRON, "weekly")
    assert schedule_matches("schedule", DAILY_CRON, "daily")
    assert not schedule_matches("schedule", WEEKLY_CRON, "daily")
    assert schedule_matches("schedule", WEEKLY_CRON, None)
    assert schedule_matches("workflow_dispatch", "", "weekly")
    assert schedule_matches("repository_dispatch", DAILY_CRON, "weekly")
    assert schedule_matches("repository_dispatch", WEEKLY_CRON, "daily")
    assert DAILY_CRON == "0 14 * * *"
    assert WEEKLY_CRON == "0 12 * * 1"


def test_workflow_keeps_both_crons_and_the_approval_gate():
    text = (ROOT / ".github" / "workflows" / "weekly-refresh.yml").read_text(encoding="utf8")
    assert 'cron: "0 12 * * 1"' in text
    assert 'cron: "0 14 * * *"' in text
    assert "vars.NEWSLETTER_CADENCE == 'daily'" in text
    assert "github.event_name != 'schedule'" in text
    assert "vars.NEWSLETTER_AUTO_SEND" in text
    assert "NEWSLETTER_DRY_RUN" in text
    assert "issue-approved" in text


def test_daily_edition_is_built_when_little_is_new(monkeypatch):
    monkeypatch.setenv("NEWSLETTER_CADENCE", "daily")
    earlier = _snapshot()
    issue = compose_issue(_snapshot(), fingerprint(earlier), site_url="http://127.0.0.1:43123")
    blob = json.dumps(issue)
    assert issue["cadence"] == "daily"
    assert issue["kind"] == "daily"
    assert issue["kicker"].startswith("Daily test edition")
    assert issue["subject"].startswith("Daily test edition")
    assert "no new or strengthened high signals" in issue["headline"]
    assert "little is new" in issue["intro"]
    assert _section(issue, "alerts")["items"] == []
    assert _section(issue, "signals")["items"] == []
    assert _section(issue, "alerts")["empty"] == "None in this daily edition."
    assert "None this week." not in blob
    assert "causes" not in blob.lower()


def test_daily_diff_keeps_only_what_changed_and_stays_a_test_edition(monkeypatch):
    monkeypatch.setenv("NEWSLETTER_CADENCE", "daily")
    earlier = _snapshot(
        alerts=[{"title": "Old notice", "link": "https://example.com/old", "source": "FDA", "tags": ["nsaid"]}],
    )
    current = _snapshot(
        alerts=[
            {"title": "Old notice", "link": "https://example.com/old", "source": "FDA", "tags": ["nsaid"]},
            {"title": "Brand new notice", "link": "https://example.com/new", "source": "FDA", "tags": ["jak_inhibitor"]},
        ],
        signals=[_signal(reaction="FRESH EVENT", drug_class="tnf_inhibitor", prr=4.0)],
    )
    issue = compose_issue(current, fingerprint(earlier), site_url="http://127.0.0.1:43123")
    assert issue["kind"] == "daily"
    assert issue["headline"].startswith("TNF inhibitors:")
    assert issue["subject"] == "Daily test edition: " + issue["headline"]
    assert "Brand new notice" in _titles(issue, "alerts")
    assert "Old notice" not in _titles(issue, "alerts")
    weekly = compose_issue(current, fingerprint(earlier), site_url="http://127.0.0.1:43123", cadence="weekly")
    assert weekly["kind"] == "weekly"
    assert weekly["subject"] == weekly["headline"]
    assert "None this week." == _section(weekly, "recalls")["empty"]


def test_daily_dry_run_still_does_not_send(tmp_path, monkeypatch):
    monkeypatch.setenv("NEWSLETTER_CADENCE", "daily")
    monkeypatch.setenv("NEWSLETTER_DRY_RUN", "1")
    monkeypatch.delenv("NEWSLETTER_SEND", raising=False)

    def explode(*_args, **_kwargs):
        raise AssertionError("network")

    monkeypatch.setattr("inflammon.newsletter.publish._post", explode)
    snapshot_dir = _write_snapshot(tmp_path / "snapshot", _snapshot())
    summary = build_and_save(
        snapshot_dir=snapshot_dir,
        out_dir=tmp_path / "newsletter",
        web_data_dir=tmp_path / "web-data",
        web_email_dir=tmp_path / "email",
        site_url="http://127.0.0.1:43123",
        send=True,
    )
    issue = json.loads((tmp_path / "newsletter" / "issues" / "2026-10-22" / "issue.json").read_text())
    assert summary["kind"] == "daily"
    assert summary["delivery"]["sent"] is False
    assert summary["delivery"]["mode"] == "dry-run"
    assert "Daily test edition" in issue["kicker"]
    assert "Daily test edition" in (tmp_path / "newsletter" / "issues" / "2026-10-22" / "issue.txt").read_text()


def test_empty_weekly_section_says_none_this_week():
    earlier = _snapshot()
    issue = compose_issue(_snapshot(), fingerprint(earlier), site_url="http://127.0.0.1:43123")
    assert _section(issue, "alerts")["items"] == []
    assert _section(issue, "alerts")["empty"] == "None this week."
    assert "no new or strengthened high signals" in issue["headline"]


def test_inaugural_is_not_labeled_as_new_this_week():
    issue = compose_issue(
        _snapshot(
            validation={
                "checks": [
                    {
                        "key": "tnf_inhibitor",
                        "reaction": "TUBERCULOSIS",
                        "analysis": "database",
                        "comparator": "all_faers",
                        "evans_signal": True,
                        "ror_signal": True,
                        "recovered": True,
                        "prr": 7.54,
                        "prr_ci_low": 7.2,
                        "prr_ci_high": 7.9,
                        "ror": 7.6,
                        "ror_ci_low": 7.3,
                        "ror_ci_high": 7.9,
                    }
                ]
            }
        ),
        None,
        site_url="http://127.0.0.1:43123",
    )
    blob = json.dumps(issue).lower()
    assert issue["kind"] == "inaugural"
    assert "no earlier snapshot" in issue["intro"]
    assert "new this week" not in blob
    assert issue["headline"] == "TNF inhibitors: tuberculosis reported more often than expected (PRR 7.5)"
    assert "not week-over-week changes" in issue["intro"]


def test_html_and_text_rendering():
    issue = compose_issue(
        _snapshot(
            alerts=[{"title": '<script>alert("x")</script>', "link": "https://example.com/xss", "source": "FDA", "tags": ["nsaid"], "summary": "A & B"}],
            validation={
                "checks": [
                    {
                        "key": "tnf_inhibitor",
                        "reaction": "TUBERCULOSIS",
                        "analysis": "database",
                        "comparator": "all_faers",
                        "evans_signal": True,
                        "ror_signal": True,
                        "recovered": True,
                        "prr": 7.54,
                        "prr_ci_low": 7.2,
                        "prr_ci_high": 7.9,
                        "ror": 7.6,
                        "ror_ci_low": 7.3,
                        "ror_ci_high": 7.9,
                    }
                ]
            },
        ),
        None,
        site_url="http://127.0.0.1:43123",
    )
    html_body = render_html(issue, unsubscribe_href="http://127.0.0.1:43123/unsubscribe?token=signed")
    text_body = render_text(issue, unsubscribe_href="http://127.0.0.1:43123/unsubscribe?token=signed")
    assert 'name="viewport"' in html_body
    assert issue["headline"] in html_body
    assert DISCLAIMER in html_body
    assert "http://127.0.0.1:43123/unsubscribe?token=signed" in html_body
    assert "takes effect immediately" in html_body
    assert "List-Unsubscribe-Post" in html_body
    assert "<script>alert" not in html_body
    assert "&lt;script&gt;" in html_body
    assert "A &amp; B" in html_body
    assert issue["headline"] in text_body
    assert "There is no certainty that the reported event was actually due to the product." in html_body
    assert "For research and informational purposes only. Not medical advice. Do not stop or change any medication without talking to your doctor." in html_body
    assert "Data provided by the U.S. Food and Drug Administration (https://open.fda.gov)" in html_body
    assert "not affiliated with or endorsed by" in html_body
    assert "http://127.0.0.1:43123/unsubscribe" in html_body
    assert "Postal address placeholder" in html_body
    assert "NCBI disclaimer" in html_body
    assert "causes" not in html_body.lower()
    assert "<table" not in text_body
    assert "<p" not in text_body
    assert "<html" not in text_body
    assert "token=signed" in text_body
    assert "takes effect immediately" in text_body
    assert '<script>alert("x")</script>' in text_body


def test_dry_run_does_not_call_the_network(tmp_path, monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("network")

    monkeypatch.setattr("inflammon.newsletter.publish._post", explode)
    snapshot_dir = _write_snapshot(tmp_path / "snapshot", _snapshot())
    summary = build_and_save(
        snapshot_dir=snapshot_dir,
        out_dir=tmp_path / "newsletter",
        web_data_dir=tmp_path / "web-data",
        web_email_dir=tmp_path / "email",
        site_url="http://127.0.0.1:43123",
        send=False,
    )
    assert summary["delivery"]["sent"] is False
    assert summary["delivery"]["mode"] == "dry-run"
    assert (tmp_path / "newsletter" / "issues" / "2026-10-22" / "issue.html").is_file()


def test_send_without_a_key_fails_after_the_files_exist(tmp_path, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("NEWSLETTER_DRY_RUN", raising=False)
    snapshot_dir = _write_snapshot(tmp_path / "snapshot", _snapshot())
    with pytest.raises(NewsletterSendError, match="RESEND_API_KEY"):
        build_and_save(
            snapshot_dir=snapshot_dir,
            out_dir=tmp_path / "newsletter",
            web_data_dir=tmp_path / "web-data",
            web_email_dir=tmp_path / "email",
            send=True,
        )
    assert (tmp_path / "newsletter" / "issues" / "2026-10-22" / "issue.html").is_file()


def test_resend_send_checks_suppression_and_sets_idempotency(monkeypatch):
    captured = {}
    rows = {
        "sub_active": {"id": "sub_active", "email": "active@example.com", "status": "active"},
        "sub_bounced": {"id": "sub_bounced", "email": "bounced@example.com", "status": "bounced"},
    }

    def fake_post(url, *, headers, json):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        rows["sub_active"]["status"] = "complained"
        return {"id": "em_123"}

    def reload(subscriber_id):
        row = rows[subscriber_id]
        return dict(row)

    result = send_resend(
        {"slug": "2026-10-15", "subject": "Hello"},
        "<p>__UNSUBSCRIBE_URL__</p>",
        "__UNSUBSCRIBE_URL__",
        api_key="re_test",
        post=fake_post,
        subscribers=list(rows.values()),
        reload=reload,
        secret="signing-secret",
        functions_base="https://example.supabase.co/functions/v1",
        from_address="Inflammation Signal Monitor <briefing@example.com>",
    )
    assert result["sent"] is True
    assert result["provider"] == "resend"
    assert result["recipient_count"] == 1
    assert result["suppressed"] == 1
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["headers"]["Authorization"] == "Bearer re_test"
    assert captured["headers"]["Idempotency-Key"] == "2026-10-15:sub_active"
    assert captured["json"]["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert "re_test" not in captured["json"]["html"]

    again = send_resend(
        {"slug": "2026-10-15", "subject": "Hello"},
        "<p>__UNSUBSCRIBE_URL__</p>",
        "__UNSUBSCRIBE_URL__",
        api_key="re_test",
        post=fake_post,
        subscribers=[{"id": "sub_active", "email": "active@example.com", "status": "active"}],
        reload=reload,
        secret="signing-secret",
        functions_base="https://example.supabase.co/functions/v1",
        from_address="Inflammation Signal Monitor <briefing@example.com>",
    )
    assert again["recipient_count"] == 0
    assert again["suppressed"] == 1


def test_same_snapshot_stays_inaugural_until_a_newer_one_exists(tmp_path, monkeypatch):
    monkeypatch.delenv("NEWSLETTER_SEND", raising=False)
    snapshot_dir = _write_snapshot(tmp_path / "snapshot", _snapshot())
    kwargs = dict(
        snapshot_dir=snapshot_dir,
        out_dir=tmp_path / "newsletter",
        web_data_dir=tmp_path / "web-data",
        web_email_dir=tmp_path / "email",
        site_url="http://127.0.0.1:43123",
        send=False,
    )
    first = build_and_save(**kwargs)
    second = build_and_save(**kwargs)
    assert first["kind"] == "inaugural"
    assert second["kind"] == "inaugural"
    state = json.loads((tmp_path / "newsletter" / "state" / "previous.json").read_text())
    assert state["snapshot_generated_at"] == "2026-10-22T12:00:00+00:00"
    assert not (tmp_path / "newsletter" / "state" / "prior.json").exists()


def test_a_later_snapshot_diffs_against_the_previous_one(tmp_path):
    out = tmp_path / "newsletter"
    kwargs = dict(
        out_dir=out,
        web_data_dir=tmp_path / "web-data",
        web_email_dir=tmp_path / "email",
        site_url="http://127.0.0.1:43123",
        send=False,
    )
    first_dir = _write_snapshot(tmp_path / "snap1", _snapshot(alerts=[]))
    build_and_save(snapshot_dir=first_dir, **kwargs)
    second = _snapshot(
        alerts=[{"title": "Arrived later", "link": "https://example.com/later", "source": "FDA", "tags": ["nsaid"]}],
    )
    second["manifest"] = {
        "generated_at": "2026-10-29T12:00:00+00:00",
        "openfda_last_updated": "2026-07-30",
        "disclaimer": DISCLAIMER,
    }
    second_dir = _write_snapshot(tmp_path / "snap2", second)
    summary = build_and_save(snapshot_dir=second_dir, **kwargs)
    issue = json.loads((out / "issues" / "2026-10-29" / "issue.json").read_text())
    assert summary["kind"] == "weekly"
    assert "Arrived later" in _titles(issue, "alerts")
    prior = json.loads((out / "state" / "prior.json").read_text())
    assert prior["snapshot_generated_at"] == "2026-10-22T12:00:00+00:00"


def test_duplicate_trial_records_collapse_to_one_study():
    issue = compose_issue(
        _snapshot(
            trials=[
                {
                    "nct_id": "NCT1",
                    "title": "Same study",
                    "topic": "crohns_disease",
                    "status": "RECRUITING",
                    "link": "https://clinicaltrials.gov/study/NCT1",
                },
                {
                    "nct_id": "NCT1",
                    "title": "Same study",
                    "topic": "ulcerative_colitis",
                    "status": "RECRUITING",
                    "link": "https://clinicaltrials.gov/study/NCT1",
                },
                {
                    "nct_id": "NCT2",
                    "title": "Other study",
                    "topic": "lupus",
                    "status": "RECRUITING",
                    "link": "https://clinicaltrials.gov/study/NCT2",
                },
            ]
        ),
        None,
        site_url="http://127.0.0.1:43123",
    )
    titles = _titles(issue, "trials")
    assert titles.count("Same study") == 1
    assert "Other study" in titles


def test_real_snapshot_mentions_tuberculosis_and_gastrointestinal_haemorrhage():
    snapshot = load_snapshot(ROOT / "data" / "snapshot")
    issue = compose_issue(snapshot, None, site_url="http://127.0.0.1:43123")
    blob = json.dumps(issue).lower()
    assert "tuberculosis" in blob
    assert "gastrointestinal haemorrhage" in blob
    assert "new this week" not in blob
    assert "no earlier snapshot" in issue["intro"]
    html_body = render_html(issue, unsubscribe_href="http://127.0.0.1:43123/unsubscribe")
    assert "viewport" in html_body
    assert "7.5" in issue["headline"]


def test_cli_dry_run(tmp_path, monkeypatch):
    monkeypatch.delenv("NEWSLETTER_SEND", raising=False)
    monkeypatch.setattr("inflammon.newsletter.publish._post", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("network")))
    snapshot_dir = _write_snapshot(tmp_path / "snapshot", _snapshot())
    main(
        [
            "newsletter",
            "--snapshot",
            str(snapshot_dir),
            "--out",
            str(tmp_path / "out"),
            "--web-data",
            str(tmp_path / "web"),
            "--web-email",
            str(tmp_path / "email"),
            "--dry-run",
        ]
    )
    assert (tmp_path / "out" / "index.json").is_file()


def test_resend_double_opt_in_never_adds_a_contact_before_confirm():
    calls = []

    def post(url, *, headers, json):
        calls.append((url, json))
        return {"id": "email_1"}

    refused = handle_subscribe(
        {"email": "reader@example.com"},
        secret="s3cret",
        function_url="https://subscribe.example.com",
        api_key="re_test",
        from_address="Briefing <briefing@example.com>",
        post=post,
    )
    assert refused["status"] == 400
    assert calls == []

    accepted = handle_subscribe(
        {"email": "reader@example.com", "consent": "yes"},
        secret="s3cret",
        function_url="https://subscribe.example.com",
        api_key="re_test",
        from_address="Briefing <briefing@example.com>",
        post=post,
    )
    assert accepted["status"] == 200
    assert calls[0][0] == "https://api.resend.com/emails"
    assert "/confirm?email=" in calls[0][1]["text"]
    assert "audiences" not in calls[0][0]

    bad = handle_confirm(
        "reader@example.com",
        "not-the-token",
        secret="s3cret",
        audience_id="aud_1",
        api_key="re_test",
        post=post,
    )
    assert bad["status"] == 400
    assert len(calls) == 1

    token = confirm_token("reader@example.com", "s3cret")
    good = handle_confirm(
        "reader@example.com",
        token,
        secret="s3cret",
        audience_id="aud_1",
        api_key="re_test",
        post=post,
    )
    assert good["status"] == 200
    assert calls[1][0] == "https://api.resend.com/audiences/aud_1/contacts"
    assert calls[1][1]["email"] == "reader@example.com"


def _write_snapshot(directory: Path, snapshot: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(json.dumps(snapshot["manifest"]), encoding="utf8")
    (directory / "alerts.json").write_text(json.dumps({"items": snapshot["alerts"]}), encoding="utf8")
    (directory / "recalls.json").write_text(json.dumps({"items": snapshot["recalls"]}), encoding="utf8")
    (directory / "signals.json").write_text(json.dumps({"rows": snapshot["signals"]}), encoding="utf8")
    (directory / "validation.json").write_text(json.dumps(snapshot["validation"]), encoding="utf8")
    (directory / "recent.json").write_text(
        json.dumps({"publications": snapshot["publications"], "trials": snapshot["trials"]}),
        encoding="utf8",
    )
    return directory
