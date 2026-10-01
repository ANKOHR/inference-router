"""Synthetic fixtures with manually derived expectations. No randomness used."""
import json

# Synthetic: 40 repetitions of these five independently hand-scored cases.
CASES = [
    ("Say hello", 1, False, False, "small"),  # 1
    ("Summarise a short note", 2, False, False, "small"),  # 2
    ("Explain a logical deduction", 1, True, False, "medium"),  # 3
    ("Write and explain a function", 1, True, True, "medium"),  # 5
    ("Design and verify a parser", 2, True, True, "large"),  # 6
]


def records(count=200):
    if count not in (5, 200):
        raise ValueError("count must be 5 or 200")
    return [{"id": f"fixture-{i:03d}", "prompt": CASES[i % 5][0], "steps": CASES[i % 5][1],
             "requires_reasoning": CASES[i % 5][2], "requires_code": CASES[i % 5][3],
             "expected_route": CASES[i % 5][4], "synthetic": True} for i in range(count)]


def expectations(count=200):
    # Synthetic hand-computed ground truth, independent of the routing engine.
    n = count // 5
    return {"synthetic": True, "total": count, "routes": {"small": 2*n, "medium": 2*n, "large": n},
            "labelled": count, "matches": count, "mismatches": 0, "false_positives": 0,
            "score_total": 17*n, "synthetic_count": count, "real_count": 0}


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
