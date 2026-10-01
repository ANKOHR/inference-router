import json
import subprocess
import sys
import time
import pytest
from inference_router.cli import main, read_input
from inference_router.core import RouterError


def setup_demo(tmp_path):
    demo = tmp_path / "demo"
    result = tmp_path / "results.json"
    assert main(["fixtures", "--out", str(demo)]) == 0
    return demo, result


def test_run_completes_on_fixture(tmp_path, capsys):
    start = time.perf_counter()
    demo, result = setup_demo(tmp_path)
    assert main(["run", "--input", str(demo), "--results", str(result)]) == 0
    assert main(["report", "--results", str(result), "--format", "md"]) == 0
    assert time.perf_counter() - start < 5
    assert "Data provenance: 200 synthetic" in capsys.readouterr().out


def test_empty_input_renders_without_traceback(tmp_path, capsys):
    directory = tmp_path / "empty"
    directory.mkdir()
    result = tmp_path / "result.json"
    assert main(["run", "--input", str(directory), "--results", str(result)]) == 0
    capsys.readouterr()
    assert main(["report", "--results", str(result), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["total"] == 0


def test_malformed_input_named_error(tmp_path, capsys):
    (tmp_path / "bad.jsonl").write_text('# SYNTHETIC\n{broken\n', encoding="utf-8")
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "ParseError" in error and "bad.jsonl: line 2" in error and "Traceback" not in error


@pytest.mark.parametrize("suffix", ["csv", "yaml", "json"])
def test_unsupported_formats_named(tmp_path, suffix):
    (tmp_path / f"bad.{suffix}").write_text("malformed")
    with pytest.raises(RouterError, match="unsupported input"):
        read_input(tmp_path)


def test_determinism_byte_identical(tmp_path):
    demo, result = setup_demo(tmp_path)
    outputs = []
    for _ in range(2):
        assert main(["run", "--input", str(demo), "--results", str(result)]) == 0
        report = tmp_path / "report.md"
        assert main(["report", "--results", str(result), "--out", str(report)]) == 0
        outputs.append((result.read_bytes(), report.read_bytes()))
    assert outputs[0] == outputs[1]


def test_cli_smoke_all_subcommands(tmp_path, capsys):
    demo, result = setup_demo(tmp_path)
    assert main(["run", "--input", str(demo), "--results", str(result)]) == 0
    assert main(["report", "--results", str(result)]) == 0
    assert main(["report", "--results", str(result), "--format", "json"]) == 0
    assert main(["route", "--prompt", "ä½ å¥½", "--steps", "2", "--code"]) == 0
    assert main(["policy"]) == 0
    for name in ("fixtures", "run", "report", "route", "policy"):
        with pytest.raises(SystemExit) as exc:
            main([name, "--help"])
        assert exc.value.code == 0
    assert "\u2014" not in capsys.readouterr().out


def test_missing_input_named(tmp_path, capsys):
    assert main(["run", "--input", str(tmp_path / "missing")]) == 2
    assert "MissingInput" in capsys.readouterr().err


def test_report_write_failure_atomic(tmp_path, capsys):
    demo, result = setup_demo(tmp_path)
    main(["run", "--input", str(demo), "--results", str(result)])
    destination = tmp_path / "directory"
    destination.mkdir()
    assert main(["report", "--results", str(result), "--out", str(destination)]) == 2
    assert "WriteError" in capsys.readouterr().err
    assert not list(tmp_path.glob(".ir-*"))
    assert not list(destination.iterdir())


def test_schema_error_field_and_line(tmp_path, capsys):
    (tmp_path / "bad.jsonl").write_text('{"id":"bad"}\n')
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "missing field prompt" in error and "line 1" in error


def test_executable_module(tmp_path):
    p = subprocess.run([sys.executable, "-m", "inference_router.cli", "policy"], capture_output=True, text=True)
    assert p.returncode == 0 and "Illustrative" in p.stdout


def test_existing_results_preserved_on_invalid_input(tmp_path):
    demo, result = setup_demo(tmp_path)
    main(["run", "--input", str(demo), "--results", str(result)])
    before = result.read_bytes()
    (demo / "bad.jsonl").write_text("{bad")
    assert main(["run", "--input", str(demo), "--results", str(result)]) == 2
    assert result.read_bytes() == before


def test_handwritten_input_end_to_end(tmp_path, capsys):
    result = tmp_path / "result.json"
    assert main(["run", "--input", "examples/handwritten", "--results", str(result)]) == 0
    capsys.readouterr()
    assert main(["report", "--results", str(result), "--format", "json"]) == 0
    s = json.loads(capsys.readouterr().out)["summary"]
    assert s["routes"] == {"small": 2, "medium": 2, "large": 1}
    assert s["score_total"] == 17


def test_cli_corrupted_label_changes_report(tmp_path, capsys):
    demo, result = setup_demo(tmp_path)
    path = demo / "prompts.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[1])
    record["expected_route"] = "large"
    lines[1] = json.dumps(record)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert main(["run", "--input", str(demo), "--results", str(result)]) == 0
    capsys.readouterr()
    assert main(["report", "--results", str(result), "--format", "json"]) == 0
    s = json.loads(capsys.readouterr().out)["summary"]
    assert s["matches"] == 199 and s["false_positives"] == 1


def test_unicode_long_windows_path_roundtrip(tmp_path):
    from inference_router.fixtures import records
    demo = tmp_path / "input"
    demo.mkdir()
    r = dict(records(5)[0], prompt="你好 café C:\\Users\\henry " + "x"*99000)
    (demo / "unicode.jsonl").write_text("# SYNTHETIC\n" + json.dumps(r, ensure_ascii=False) + "\n", encoding="utf-8")
    result = tmp_path / "result.json"
    assert main(["run", "--input", str(demo), "--results", str(result)]) == 0
    assert json.loads(result.read_text())["records"][0]["prompt_chars"] == len(r["prompt"])
