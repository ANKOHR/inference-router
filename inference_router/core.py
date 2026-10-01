"""Pure routing from declared requirements, not inferred prompt difficulty.

Model tiers are illustrative capability profiles, not measured provider claims.
"""
import re

MAX_PROMPT = 100_000
FIELDS = {"id", "prompt", "synthetic", "steps", "requires_reasoning", "requires_code", "expected_route", "source"}
TIERS = ("small", "medium", "large")
POLICY = {
    "label": "Illustrative routing policy; model capabilities and quality are unmeasured.",
    "small": "score 0-2",
    "medium": "score 3-5",
    "large": "score 6 or more",
    "score": "steps + 2*requires_reasoning + 2*requires_code + min(3, (prompt_chars-1)//1000)",
}

class RouterError(ValueError):
    """Named user-facing validation error."""


def validate(record):
    if not isinstance(record, dict):
        raise RouterError("SchemaError: record must be an object")
    unknown = set(record) - FIELDS
    if unknown:
        raise RouterError("SchemaError: unknown field(s): " + ", ".join(sorted(unknown)))
    for field in ("id", "prompt", "synthetic", "steps", "requires_reasoning", "requires_code"):
        if field not in record:
            raise RouterError(f"SchemaError: missing field {field}")
    if not isinstance(record["id"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", record["id"]):
        raise RouterError("SchemaError: id must be 1-64 ASCII letters, digits, dots, underscores or hyphens")
    prompt = record["prompt"]
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT:
        raise RouterError(f"SchemaError: prompt must contain 1-{MAX_PROMPT} characters and not be blank")
    if "\u2014" in prompt:
        raise RouterError("SchemaError: prompt contains prohibited U+2014; replace it with a hyphen")
    if type(record["steps"]) is not int or not 1 <= record["steps"] <= 100:
        raise RouterError("SchemaError: steps must be an integer between 1 and 100")
    for field in ("synthetic", "requires_reasoning", "requires_code"):
        if type(record[field]) is not bool:
            raise RouterError(f"SchemaError: {field} must be a boolean")
    if "expected_route" in record and record["expected_route"] not in TIERS:
        raise RouterError("SchemaError: expected_route must be small, medium or large")
    if "source" in record and record["source"] != "henry_entered":
        raise RouterError("SchemaError: source must be henry_entered")
    if not record["synthetic"] and record.get("source") != "henry_entered":
        raise RouterError("SchemaError: real inputs require source=henry_entered (a user declaration)")
    return dict(record)


def route(record):
    r = validate(record)
    length_points = min(3, (len(r["prompt"]) - 1) // 1000)
    score = r["steps"] + 2 * r["requires_reasoning"] + 2 * r["requires_code"] + length_points
    tier = "small" if score <= 2 else "medium" if score <= 5 else "large"
    result = {"id": r["id"], "synthetic": r["synthetic"], "route": tier, "score": score,
              "prompt_chars": len(r["prompt"]), "steps": r["steps"],
              "reasoning_points": 2 * r["requires_reasoning"], "code_points": 2 * r["requires_code"],
              "length_points": length_points}
    if "expected_route" in r:
        result["expected_route"] = r["expected_route"]
    return result


def workflow(records):
    seen = set()
    results = []
    for record in records:
        result = route(record)
        if result["id"] in seen:
            raise RouterError(f"SchemaError: duplicate id {result['id']}")
        seen.add(result["id"])
        results.append(result)
    results.sort(key=lambda r: r["id"])
    return {"schema_version": 1, "policy": POLICY, "records": results}
