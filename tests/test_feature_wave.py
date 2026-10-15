from pathlib import Path

import pytest

from similar_filename_finder.core import _fingerprint, analyze


def fixture(tmp_path):
    for name in ("report.txt", "report-2.txt", "report-3.txt"):
        (tmp_path / name).write_bytes(b"same")
    return {"root": str(tmp_path), "threshold": 0}


def test_defaults_stream_and_cache(tmp_path, monkeypatch):
    data = fixture(tmp_path)
    original = Path.open
    calls = []

    def opened(path, *args, **kwargs):
        if args and args[0] == "rb":
            calls.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", opened)
    monkeypatch.setattr(Path, "read_bytes", lambda p: pytest.fail("whole file read"))
    report = analyze(data)
    assert len(calls) == 3
    assert report["hash_bytes_read"] == 12
    assert report["exact_content_pairs"] == 3
    assert all(pair["content_status"] == "identical" for pair in report["pairs"])


def test_budgets_and_different_content(tmp_path):
    data = fixture(tmp_path)
    limited = analyze({**data, "max_hash_bytes_per_file": 3})
    assert limited["hash_bytes_read"] == 0
    assert all(pair["exact_content"] is None for pair in limited["pairs"])
    assert all(pair["content_status"] == "unverified" for pair in limited["pairs"])
    total = analyze({**data, "max_hash_bytes_total": 8})
    assert total["hash_bytes_read"] == 8
    assert total["exact_content_pairs"] == 1
    assert any("total_budget" in pair["hash_status"] for pair in total["pairs"])
    (tmp_path / "report.txt").write_bytes(b"diff")
    assert analyze(data)["exact_content_pairs"] == 1
    assert analyze({**data, "max_hash_bytes_total": 0})["hash_bytes_read"] == 0


@pytest.mark.parametrize("value", [-1, 1.5, True, "12"])
def test_invalid_budget(tmp_path, value):
    with pytest.raises(ValueError):
        analyze({**fixture(tmp_path), "max_hash_bytes_total": value})


def test_unreadable_and_changing_files(tmp_path, monkeypatch):
    data = fixture(tmp_path)
    original = Path.open

    def denied(path, *args, **kwargs):
        if path.name == "report.txt" and args and args[0] == "rb":
            raise PermissionError("fixture")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    report = analyze(data)
    assert any("unreadable" in p["hash_status"] for p in report["pairs"])
    monkeypatch.setattr(Path, "open", original)
    from similar_filename_finder import core

    real = core._fingerprint
    count = 0

    def changed(path, per_file, remaining):
        nonlocal count
        result = real(path, per_file, remaining)
        count += 1
        if count == 3:
            (tmp_path / "report-2.txt").write_bytes(b"changed")
        return result

    monkeypatch.setattr(core, "_fingerprint", changed)
    report = analyze(data)
    assert any("changed" in p["hash_status"] for p in report["pairs"])
    assert all(p["exact_content"] is None for p in report["pairs"] if "changed" in p["hash_status"])


def test_streaming_large_and_growth_during_open(tmp_path, monkeypatch):
    path = tmp_path / "large"
    path.write_bytes(b"x" * (2 * 1024 * 1024 + 3))
    digest, state, count, snapshot = _fingerprint(path, None, None)
    assert state == "hashed" and count == path.stat().st_size and digest and snapshot
    original = Path.open

    def growing(p, *args, **kwargs):
        if args and args[0] == "rb":
            with original(p, "ab") as handle:
                handle.write(b"extra")
        return original(p, *args, **kwargs)

    monkeypatch.setattr(Path, "open", growing)
    assert _fingerprint(path, None, None)[1] == "changed"
