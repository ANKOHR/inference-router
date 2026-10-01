import json
from inference_router.core import workflow
from inference_router.fixtures import records, expectations
from inference_router.report import render, summary


def test_report_matches_ground_truth_exact():
    actual = json.loads(render(workflow(records()), "json"))["summary"]
    assert actual == {k: v for k, v in expectations().items() if k != "synthetic"}


def test_report_zero_false_positives():
    assert summary(workflow(records()))["false_positives"] == 0


def test_corrupted_ground_truth_changes_report():
    rows = records()
    rows[0]["expected_route"] = "large"
    s = summary(workflow(rows))
    assert s["mismatches"] == s["false_positives"] == 1
    assert s["matches"] == 199


def test_changed_requirements_change_routes():
    rows = records()
    rows[0]["steps"] = 6
    s = summary(workflow(rows))
    assert s["routes"] == {"small": 79, "medium": 80, "large": 41}
    assert s["score_total"] == 685


def test_report_carries_provenance_banner():
    rows = records(5)
    rows[0].update(synthetic=False, source="henry_entered")
    for fmt in ("json", "md"):
        text = render(workflow(rows), fmt)
        assert "Data provenance: 4 synthetic fixture records; 1 real records" in text
        assert "user-declared" in text


def test_hypothetical_figures_labelled():
    for fmt in ("md", "json"):
        text = render(workflow(records()), fmt)
        assert "Illustrative" in text and "savings are unmeasured" in text


def test_unlabelled_not_counted_as_correct():
    rows = records(5)
    for r in rows:
        del r["expected_route"]
    s = summary(workflow(rows))
    assert s["labelled"] == s["matches"] == s["false_positives"] == 0


def test_no_em_dashes_in_outputs():
    for fmt in ("md", "json"):
        assert "\u2014" not in render(workflow(records()), fmt)
