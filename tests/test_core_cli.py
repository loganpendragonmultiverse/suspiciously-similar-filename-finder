import json
from pathlib import Path

import pytest

from similar_filename_finder.cli import main
from similar_filename_finder.core import PROJECT, analyze, render_json, render_markdown


def test_representative_sample_has_expected_result(tmp_path):
    data = json.loads(
        (Path(__file__).parents[1] / "examples" / "sample.json").read_text(encoding="utf-8")
    )
    data["root"] = str(tmp_path)
    (tmp_path / "report.txt").write_text("fixture", encoding="utf-8")
    (tmp_path / "report-copy.txt").write_text("fixture", encoding="utf-8")
    report = analyze(data)
    assert report["version"] == 1 and report["project"] == PROJECT
    assert report["files_scanned"] > 0 and isinstance(report["pairs"], list)
    assert all("exact_content" in item for item in report["pairs"])
    assert f'"project": "{PROJECT}"' in render_json(report)
    assert PROJECT.replace("-", " ").title() in render_markdown(report)


def test_missing_required_input_is_rejected():
    with pytest.raises(ValueError):
        analyze({})


def test_content_fingerprints_cross_directories_and_threshold(tmp_path):
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    (tmp_path / "one" / "report-final.txt").write_text("same", encoding="utf-8")
    (tmp_path / "two" / "report-copy.txt").write_text("same", encoding="utf-8")
    local = analyze({"root": str(tmp_path)})
    assert local["pairs"] == []
    report = analyze({"root": str(tmp_path), "cross_directories": True})
    assert report["exact_content_pairs"] == 1
    assert report["pairs"][0]["reason"] == "exact content"
    with pytest.raises(ValueError, match="threshold"):
        analyze({"root": str(tmp_path), "threshold": 2})


def test_cli_json_and_output_safety(tmp_path, capsys):
    root = tmp_path / "files"
    root.mkdir()
    (root / "report.txt").write_text("fixture", encoding="utf-8")
    source = tmp_path / "input.json"
    data = json.loads((Path(__file__).parents[1] / "examples" / "sample.json").read_text())
    data["root"] = str(root)
    source.write_text(json.dumps(data), encoding="utf-8")
    assert main([str(source), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["project"] == PROJECT
    output = tmp_path / "report.md"
    output.write_text("keep", encoding="utf-8")
    assert main([str(source), "--output", str(output)]) == 2
