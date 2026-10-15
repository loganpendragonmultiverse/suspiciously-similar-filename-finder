import io
from pathlib import Path

import pytest

from similar_filename_finder.core import analyze


@pytest.mark.parametrize("key", ["max_hash_bytes_per_file", "max_hash_bytes_total"])
@pytest.mark.parametrize("budget", [None, 0, 2])
def test_zero_stat_size_never_proves_empty_content(tmp_path, monkeypatch, key, budget):
    # Real empty backing files provide stable, mutually consistent stat/fstat metadata.
    # The reader simulates virtual regular files with content despite st_size == 0.
    for name in ("report-a", "report-b"):
        (tmp_path / name).touch()
    original = Path.open
    reads = []

    class VirtualReader:
        def __init__(self, path):
            self.handle = original(path, "rb")
            self.content = io.BytesIO(path.name.encode())

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.handle.close()

        def fileno(self):
            return self.handle.fileno()

        def read(self, size):
            data = self.content.read(size)
            reads.append(len(data))
            return data

    def opened(path, *args, **kwargs):
        if args and args[0] == "rb" and path.parent == tmp_path:
            return VirtualReader(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", opened)
    report = analyze({"root": str(tmp_path), "threshold": 0, key: budget})
    assert report["exact_content_pairs"] == 0
    assert report["pairs"][0]["exact_content"] is None
    assert report["pairs"][0]["content_status"] == "unverified"
    assert report["hash_bytes_read"] == sum(reads)
    if budget == 0:
        assert not reads
    if budget is not None:
        assert report["hash_bytes_read"] <= budget * (2 if key.endswith("per_file") else 1)


def test_empty_files_require_eof_with_available_budget(tmp_path):
    for name in ("report-a", "report-b"):
        (tmp_path / name).touch()
    data = {"root": str(tmp_path), "threshold": 0}
    assert analyze(data)["exact_content_pairs"] == 1
    for key in ("max_hash_bytes_per_file", "max_hash_bytes_total"):
        result = analyze({**data, key: 0})
        assert result["hash_bytes_read"] == 0
        assert result["pairs"][0]["exact_content"] is None


def test_exact_budget_exhaustion_does_not_probe_beyond_limit(tmp_path):
    for name in ("report-a", "report-b"):
        (tmp_path / name).write_bytes(b"same")
    data = {"root": str(tmp_path), "threshold": 0}
    for key in ("max_hash_bytes_per_file", "max_hash_bytes_total"):
        result = analyze({**data, key: 4})
        assert result["exact_content_pairs"] == 0
        assert result["pairs"][0]["exact_content"] is None
    assert analyze({**data, "max_hash_bytes_total": 9})["exact_content_pairs"] == 1


def test_supported_linux_virtual_files_are_unverified(tmp_path):
    sources = [Path("/proc/sys/kernel/ostype"), Path("/proc/sys/kernel/osrelease")]
    if not all(path.is_file() and path.stat().st_size == 0 for path in sources):
        pytest.skip("small zero-stat-size Linux pseudofiles unavailable")
    for index, path in enumerate(sources):
        (tmp_path / f"report-{index}").symlink_to(path)
    for budget in (None, 0, 2):
        report = analyze({"root": str(tmp_path), "threshold": 0, "max_hash_bytes_total": budget})
        assert report["exact_content_pairs"] == 0
        assert report["pairs"][0]["exact_content"] is None
        if budget is not None:
            assert report["hash_bytes_read"] <= budget


def test_budget_allocation_follows_candidate_pair_first_encounter(tmp_path):
    for name in ("a-report.txt", "b-memo.txt", "c-memo.txt", "z-report.txt"):
        (tmp_path / name).write_bytes(b"x")
    report = analyze({"root": str(tmp_path), "threshold": 0.8, "max_hash_bytes_total": 3})
    pairs = {tuple(item["files"]): item for item in report["pairs"]}
    assert pairs[("a-report.txt", "z-report.txt")]["exact_content"] is True
    assert pairs[("b-memo.txt", "c-memo.txt")]["exact_content"] is None
    assert report["hash_bytes_read"] == 3
