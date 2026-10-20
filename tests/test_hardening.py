import json
import os
from pathlib import Path

import pytest

from similar_filename_finder.cli import main
from similar_filename_finder.core import analyze


@pytest.mark.parametrize("data", [None, [], "root", {"root": 4}])
def test_input_object_and_root_types(data):
    with pytest.raises((TypeError, ValueError)):
        analyze(data)


@pytest.mark.parametrize("threshold", [True, "0.5", None, 10**1000, float("nan"), float("inf")])
def test_threshold_requires_bounded_number(tmp_path, threshold):
    with pytest.raises(ValueError, match="threshold"):
        analyze({"root": str(tmp_path), "threshold": threshold})


@pytest.mark.parametrize("value", ["false", 1, None])
def test_cross_directory_flag_is_boolean(tmp_path, value):
    with pytest.raises(TypeError, match="boolean"):
        analyze({"root": str(tmp_path), "cross_directories": value})


def test_unicode_names_do_not_collapse_into_false_matches(tmp_path):
    (tmp_path / "第一章.txt").write_bytes(b"one")
    (tmp_path / "第二册.txt").write_bytes(b"two")
    assert analyze({"root": str(tmp_path)})["pairs"] == []


def test_canonical_unicode_versions_remain_candidates(tmp_path):
    (tmp_path / "résumé.txt").write_bytes(b"one")
    (tmp_path / "re\u0301sume\u0301-copy.txt").write_bytes(b"two")
    pairs = analyze({"root": str(tmp_path)})["pairs"]
    assert len(pairs) == 1
    assert pairs[0]["normalized"] == ["résumé", "résumé"]
    assert pairs[0]["content_status"] == "different"


def test_symbols_fall_back_instead_of_empty_comparison(tmp_path):
    (tmp_path / "☀.txt").write_bytes(b"one")
    (tmp_path / "☂.txt").write_bytes(b"two")
    assert analyze({"root": str(tmp_path)})["pairs"] == []


def test_discovery_prunes_git_and_reports_failed_subtrees(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    (tmp_path / "sub").mkdir()
    original = os.scandir

    def scan(path):
        if Path(path).name == ".git":
            raise AssertionError(".git traversed")
        if Path(path).name == "sub":
            raise PermissionError("synthetic")
        return original(path)

    monkeypatch.setattr(os, "scandir", scan)
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"root": str(tmp_path)}))
    assert main([str(source)]) == 2


def test_output_race_and_existing_dangling_link(tmp_path, monkeypatch):
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"root": str(tmp_path)}))
    output = tmp_path / "report.json"
    original = Path.open

    def raced(path, mode="r", *args, **kwargs):
        if path == output and mode == "x":
            with original(path, "w") as stream:
                stream.write("keep")
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", raced)
    assert main([str(source), "--output", str(output)]) == 2
    assert output.read_text() == "keep"
    link = tmp_path / "link.json"
    missing = tmp_path / "absent"
    try:
        link.symlink_to(missing)
    except OSError:
        pytest.skip("symlinks unavailable")
    assert main([str(source), "--output", str(link)]) == 2
    assert link.is_symlink() and not missing.exists()


def test_unresolvable_root_is_controlled(tmp_path, monkeypatch):
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"root": str(tmp_path)}))

    def unresolved(path, *args, **kwargs):
        raise RuntimeError("synthetic symlink loop")

    monkeypatch.setattr(Path, "resolve", unresolved)
    assert main([str(source)]) == 2
