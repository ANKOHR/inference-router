"""Reports only count explicit records. No savings or quality estimation."""
from .core import TIERS
from .fixtures import encode


def summary(data):
    records = data["records"]
    labelled = [r for r in records if "expected_route" in r]
    mismatches = sum(r["route"] != r["expected_route"] for r in labelled)
    return {"total": len(records), "routes": {t: sum(r["route"] == t for r in records) for t in TIERS},
            "labelled": len(labelled), "matches": len(labelled)-mismatches,
            "mismatches": mismatches,
            # Multiclass: each wrong assignment contributes one false positive.
            "false_positives": mismatches, "score_total": sum(r["score"] for r in records),
            "synthetic_count": sum(r["synthetic"] for r in records),
            "real_count": sum(not r["synthetic"] for r in records)}


def render(data, fmt):
    s = summary(data)
    banner = (f"Data provenance: {s['synthetic_count']} synthetic fixture records; "
              f"{s['real_count']} real records declared Henry's own hand-entered data. "
              "Real ownership is user-declared, not verified. Empty inputs contain no data.")
    honesty = "Illustrative model tiers and routing policy. No model calls; quality, latency, cost and savings are unmeasured."
    output = {"provenance_banner": banner, "honesty": honesty, "summary": s,
              "policy": data["policy"], "records": data["records"], "input_files": data.get("input_files", [])}
    if fmt == "json":
        return encode(output)
    lines = ["# Inference Router report", "", banner, "", honesty, "", "## Computed figures", ""]
    lines += [f"- {k}: {v}" for k, v in s.items() if k != "routes"]
    lines += [f"- Routed to {k}: {v}" for k, v in s["routes"].items()]
    lines += ["", "False positives mean wrong tier assignments among labelled records only.", "",
              "Unlabelled records have no accuracy measurement.", "", "## Record evidence", "",
              "| ID | Route | Score | Expected |", "| --- | --- | --- | --- |"]
    lines += [f"| {r['id']} | {r['route']} | {r['score']} | {r.get('expected_route', 'unlabelled')} |" for r in data["records"]]
    lines += ["", "## Input provenance", ""]
    lines += [f"- {f['name']}: SHA-256 {f['sha256']}" for f in data.get("input_files", [])]
    return "\n".join(lines) + "\n"
