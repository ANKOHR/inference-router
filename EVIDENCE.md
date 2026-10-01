# Local build evidence

Measured on 2026-10-01 on Windows, Python 3.12.10, CPU only. No model or network calls were made by the CLI.

- pytest: 46 passed; final suite invocation completed in 0.65 seconds.
- Installed console entry point: `ir fixtures --out demo`, `ir run --input demo`, `ir report --format md`, in sequence, each exit code 0.
- Full fixture/run/report wall-clock time including three process launches and output capture: 0.834393 seconds, measured with Python perf_counter. Target: less than 5 seconds.
- Synthetic fixture: 200 records; small 80, medium 80, large 40; score total 680; labelled 200; matches 200; mismatches 0; multiclass false positives 0.
- Both Markdown and JSON reports include provenance and unmeasured-figure labels.
- The separately hand-written five-record input is verified end to end in pytest.
- Byte-identical results and reports are verified by repeated runs in pytest.
- Corrupting a per-record expected label changes matches to 199 and false positives to 1 in the end-to-end CLI test. Changing task requirements also changes route totals.

Committed fixture input: `examples/synthetic-200`. Computed outputs: `evidence/fixture-report.md` and `evidence/fixture-report.json`. Input SHA-256 hashes in those reports match the fixture bytes. Reproduce with `ir run --input examples/synthetic-200` then `ir report --format md`. The fixture oracle is independent and is never used by the workflow to calculate its figures.

This is synthetic policy-agreement evidence, not measured model suitability. Timing measures this local CLI only; no model latency, cost, quality or savings were measured. The two-week real-use trial has not occurred. See VERDICT.md and the README improvement hook.
