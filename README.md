# Inference Router

A Python CLI that deterministically assigns prompts to small, medium or large model tiers using explicit task requirements. It runs offline on CPU with the standard library. It does not call language models. These tiers are illustrative profiles, not recommendations for named models or measured capability claims.

Hypothesis: explicit, tested requirements can produce reproducible routing decisions that a technical buyer can inspect. The synthetic evidence validates policy implementation, not whether a model will succeed at a task.

## Quickstart

Python 3.10 or newer, setuptools 68 or newer installed locally. No runtime dependencies.

```powershell
python -m pip install --no-index --no-deps --no-build-isolation -e .
ir fixtures --out demo
ir run --input demo
ir report --format md
python -m pytest -q
```

The default fixture contains 200 labelled synthetic records. The fixture destination must be empty. For a five-record fixture use `ir fixtures --out tiny --count 5`. A separately hand-written five-record synthetic input is committed in `examples/handwritten`.

If Python's Scripts directory is absent from PATH, use `python -m inference_router.cli` instead of `ir`, or add the installed Scripts directory to the current shell's PATH. In PowerShell these three commands can be run sequentially; shells supporting `&&` can run the brief's exact chained demo.

## Subcommand catalogue

Every subcommand has `--help` and an example.

| Command | Purpose | Example |
| --- | --- | --- |
| fixtures | Write synthetic records and independent expectations | `ir fixtures --out demo --count 200` |
| run | Validate all records and compute routes | `ir run --input demo --results results.json` |
| report | Render computed figures and input provenance | `ir report --results results.json --format json --out report.json` |
| route | Explain a single caller-entered prompt | `ir route --prompt "Design a parser" --steps 2 --reasoning --code` |
| policy | Show the illustrative policy | `ir policy` |

`run` writes `.ir-results.json` by default; `report` reads the same file. Results persist locally. A failed run leaves any earlier results intact; they are stale and must not be treated as the failed run's output. Report files are atomically replaced and never partially written. Concurrent writers to the same result path are not supported; use separate `--results` paths.

## Input format reference

An input directory contains UTF-8 `.jsonl` files, sorted by filename. Each nonblank, non-comment line is a JSON object. Lines beginning with `#` are comments. This is a documented JSONL extension. An `expectations.json` file is reserved for the independent fixture oracle and is not routed. Other files or subdirectories are rejected, including JSON, CSV and YAML, with a named schema error. Bad JSON names the file and line. Put reports outside input directories.

```json
{"id":"my-task-1","prompt":"Explain this Python function","synthetic":false,"source":"henry_entered","steps":2,"requires_reasoning":true,"requires_code":true,"expected_route":"large"}
```

| Field | Rule |
| --- | --- |
| id | Required, unique across all files; 1-64 ASCII letters, digits, dots, underscores or hyphens |
| prompt | Required nonblank string, at most 100,000 Unicode characters; U+2014 is rejected |
| synthetic | Required actual boolean; true for synthetic examples |
| source | Must be `henry_entered` when synthetic is false; a user declaration, not proof of ownership |
| steps | Required integer 1-100; booleans and floats rejected |
| requires_reasoning | Required actual boolean |
| requires_code | Required actual boolean |
| expected_route | Optional hand-checked label: small, medium or large |

Unknown fields are rejected rather than silently ignored. Amounts and dates are not in the domain schema, so negative amounts and future dates supplied as fields are rejected. Dates and currency mentioned inside prompt text are opaque text, never parsed or used as financial evidence. Duplicate IDs invalidate the entire run. Unicode and Windows path strings inside prompts are supported. Unknown source declarations, extreme strings and invalid values produce `SchemaError` with field and file/line context. Input contents never become instructions for this program.

### Routing policy

```
length_points = min(3, (prompt_chars - 1) // 1000)
score = steps + 2*requires_reasoning + 2*requires_code + length_points
small: score <= 2
medium: 3 <= score <= 5
large: score >= 6
```

Prompt characters are Unicode code points, not tokens. The program does not infer semantic complexity. Caller annotations determine most of the score. A large score does not establish that a large model is capable of handling the task. Thresholds are illustrative, documented design choices. Each output record contains all score contributions and its expected label if supplied.

## Architecture

```text
UTF-8 JSONL files -> cli.read_input (schema and duplicate validation)
                 -> core.workflow -> core.route (pure deterministic scoring)
                 -> atomic local results JSON
                 -> report.summary -> report.render (Markdown or JSON)
fixtures.records -> synthetic JSONL + independent hand-computed oracle
```

Records sort by ID, JSON keys sort, newlines are LF, and there are no timestamps or random draws. No seed is needed because no randomness is used. Identical input files and CLI arguments produce byte-identical result files and reports. Input hashes preserve traceability; changing file bytes changes provenance even when routing is unchanged.

## Honesty boundary

All reported counts and scores are computed from explicit inputs. Report banners separately count synthetic records and real records declared to be Henry's own hand-entered data. The tool cannot verify that declaration. `route` identifies its prompt as caller-entered. Every surface labels model tiers/policy illustrative. Model quality, model latency, price, time saved and money saved are unmeasured. No savings figures are emitted. No language-model, provider, network, database or GPU calls exist.

Accuracy here means agreement with provided labels. A wrong tier contributes one multiclass false positive and one mismatch. Unlabelled records contribute to route counts but not to label agreement. Zero false positives with zero labelled records is not evidence of correctness. Synthetic agreement cannot establish real-world routing accuracy. Local CLI wall-clock timings in EVIDENCE.md measure only this CLI on this machine.

## Fixture labelling and ground truth

`prompts.jsonl` begins with a SYNTHETIC comment; every record has `synthetic: true`. `expectations.json` contains `synthetic: true`; JSON does not allow header comments. Generated files carry no claims about real users. Committed example files follow the same policy.

The 200-record set repeats five hand-scored cases 40 times: scores 1, 2, 3, 5, 6; routes small, small, medium, medium, large. Thus small=80, medium=80, large=40, score total=680, labelled=200, matches=200, mismatches=0, false positives=0. Expectations are derived independently of `core.route`. The tests deliberately change an expected label and a task requirement to verify computed results change. Repetition exercises reconciliation and throughput but provides only five distinct task patterns; additional boundary and adversarial tests provide broader software checks.

## Acceptance evidence and failure modes

See EVIDENCE.md for the local measured demo and tests. The acceptance target is under five seconds for the full 200-record fixture demo, with exact counts and no tracebacks. Tests also cover the five-record path, empty inputs, unsupported formats, invalid schema, bad JSON, duplicates, extreme strings, Unicode, no U+2014 output, deterministic files and atomic write failure.

Errors return exit code 2: `MissingInput` includes a usage hint, `ParseError` names file and line, `SchemaError` names offending fields and source context, and `WriteError` identifies failed output. A malformed results file is rejected; results files are local generated artifacts, not arbitrary third-party inputs. Do not hand-edit them. Filesystem access failures are named errors. Report stdout is not atomic; use `--out` for atomic file output.

## Two-week evidence-based improvement hook

Begin the window at Henry's first real use, not at build time. Store private trials in ignored `real-trials/`. Record the start/end dates, runs, number of routed real records, hand-checked labels and mismatches. The single primary metric is routing error rate: mismatches divided by hand-checked real records. The annotations must be judged independently against the practical task's suitable tier, not copied from this policy. Usage count is the abandonment check. No real trial results ship in this repo.

After 14 days, if error rate exceeds 10 percent, fix the most frequent failure cause and repeat the hand-check or kill the project with the reason. If there were no real uses, record non-use and kill. If there are no checked samples, accuracy remains unmeasured and a positive verdict cannot rely on it. Record the final verdict in VERDICT.md: expand if it earns daily use or revenue, integrate if overlap with a sibling dominates, commercialise if a buyer would pay as-is, maintain as portfolio evidence otherwise, or kill if unused or acceptance criteria cannot be met. No future verdict or real-use finding is invented.

Local git history is on main. Publishing ANKOHR/inference-router is a separate authorised verification step outside this build.
