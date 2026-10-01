import pytest
from inference_router.core import RouterError, route, workflow
from inference_router.fixtures import records


def test_thresholds():
    r = records(5)[0]
    for steps, expected in [(1, "small"), (2, "small"), (3, "medium"), (5, "medium"), (6, "large")]:
        assert route(dict(r, steps=steps))["route"] == expected


@pytest.mark.parametrize("patch", [
    {"steps": -1}, {"steps": True}, {"steps": 101}, {"requires_code": 1},
    {"synthetic": "true"}, {"prompt": ""}, {"prompt": "x"*100001},
    {"id": "../bad"}, {"amount": -1}, {"date": "2099-01-01"},
    {"expected_route": "invented"}, {"source": "unknown"},
    {"synthetic": False}, {"prompt": "bad\u2014text"},
])
def test_rejects_adversarial_values(patch):
    with pytest.raises(RouterError, match="SchemaError"):
        route(dict(records(5)[0], **patch))


def test_duplicate_ids():
    with pytest.raises(RouterError, match="duplicate id"):
        workflow([records(5)[0]]*2)


def test_handles_unicode_and_long_inputs():
    r = dict(records(5)[0], prompt="你好 café C:\\Users\\henry\\文書 " + "a"*99000)
    result = route(r)
    assert result["prompt_chars"] == len(r["prompt"])
    assert result["length_points"] == 3


def test_real_source_required_and_accepted():
    assert route(dict(records(5)[0], synthetic=False, source="henry_entered"))["synthetic"] is False


def test_length_boundaries():
    r = records(5)[0]
    for n, points in [(1000, 0), (1001, 1), (2000, 1), (2001, 2), (3001, 3)]:
        assert route(dict(r, prompt="x"*n))["length_points"] == points
