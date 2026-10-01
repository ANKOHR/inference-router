import json
from inference_router.cli import main, read_input
from inference_router.core import workflow
from inference_router.fixtures import expectations, records
from inference_router.report import summary


def test_fixtures_labelled_synthetic(tmp_path):
    dest = tmp_path / "demo"
    assert main(["fixtures", "--out", str(dest)]) == 0
    assert (dest / "prompts.jsonl").read_text().startswith("# SYNTHETIC")
    rows, _ = read_input(dest)
    assert len(rows) == 200 and all(r["synthetic"] is True for r in rows)
    assert json.loads((dest / "expectations.json").read_text())["synthetic"] is True


def test_fixture_ground_truth_matches_hand_computed():
    oracle = expectations()
    assert oracle["routes"] == {"small": 80, "medium": 80, "large": 40}
    assert oracle["score_total"] == 680
    assert summary(workflow(records())) == {k: v for k, v in oracle.items() if k != "synthetic"}


def test_five_record_smallest_version():
    assert summary(workflow(records(5)))["routes"] == {"small": 2, "medium": 2, "large": 1}
