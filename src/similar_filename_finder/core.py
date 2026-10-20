from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import unicodedata
from itertools import combinations
from pathlib import Path
from typing import Any

PROJECT = "suspiciously-similar-filename-finder"


def _require(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if value is None or value == "" or value == []:
        raise ValueError(f"{key} is required")
    if not isinstance(value, str):
        raise TypeError(f"{key} must be text")
    return value


def _filename_similarity(data: dict[str, Any]) -> dict[str, Any]:
    try:
        root = Path(_require(data, "root")).resolve()
    except RuntimeError as exc:
        raise ValueError("root cannot be resolved") from exc
    if not root.is_dir():
        raise ValueError("root must be an existing directory")
    threshold_value = data.get("threshold", 0.72)
    if type(threshold_value) not in (int, float) or not 0 <= threshold_value <= 1:
        raise ValueError("threshold must be between 0 and 1")
    threshold = float(threshold_value)
    cross_directories = data.get("cross_directories", False)
    if type(cross_directories) is not bool:
        raise TypeError("cross_directories must be boolean")
    files = []
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as iterator:
            for entry in iterator:
                if entry.name == ".git":
                    continue
                if entry.is_file():
                    files.append(directory / entry.name)
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(directory / entry.name)
    files.sort()
    normalized = {}
    for path in files:
        stem = re.sub(
            "\\b(final|copy|backup|old|new|rev|version|v)\\b|\\(\\d+\\)|[-_ ]?\\d+$",
            "",
            unicodedata.normalize("NFKC", path.stem).casefold(),
        ).strip(" -_()")
        normalized[path] = (
            re.sub(r"[\W_]+", " ", stem).strip()
            or unicodedata.normalize("NFKC", path.stem).casefold()
        )
    groups: list[dict[str, Any]] = []
    per_file = _budget(data, "max_hash_bytes_per_file")
    remaining = _budget(data, "max_hash_bytes_total")
    fingerprints: dict[Path, tuple[str | None, str]] = {}
    snapshots: dict[Path, tuple[int, int, int, int, int]] = {}
    bytes_read = 0
    for left, right in combinations(files, 2):
        if not cross_directories and left.parent != right.parent:
            continue
        score = difflib.SequenceMatcher(None, normalized[left], normalized[right]).ratio()
        variant_marker = (
            normalized[left] == normalized[right] and left.name.casefold() != right.name.casefold()
        )
        if score >= threshold or variant_marker:
            for path in (left, right):
                if path not in fingerprints:
                    fingerprint, state, consumed, snapshot = _fingerprint(path, per_file, remaining)
                    fingerprints[path] = (fingerprint, state)
                    bytes_read += consumed
                    if remaining is not None:
                        remaining -= consumed
                    if snapshot is not None:
                        snapshots[path] = snapshot
            exact_content = False
            groups.append(
                {
                    "files": [
                        left.relative_to(root).as_posix(),
                        right.relative_to(root).as_posix(),
                    ],
                    "similarity": round(score, 3),
                    "normalized": [normalized[left], normalized[right]],
                    "exact_content": exact_content,
                    "reason": "exact content"
                    if exact_content
                    else "variant marker"
                    if variant_marker
                    else "similar name",
                }
            )
    for path, snapshot in snapshots.items():
        try:
            if _signature(path.stat()) != snapshot:
                fingerprints[path] = (None, "changed")
        except OSError:
            fingerprints[path] = (None, "unreadable")
    for item in groups:
        states = [fingerprints[root / name] for name in item["files"]]
        verified = all(state == "hashed" for _, state in states)
        item["exact_content"] = (states[0][0] == states[1][0]) if verified else None
        item["content_status"] = (
            "identical" if item["exact_content"] else "different" if verified else "unverified"
        )
        item["hash_status"] = [state for _, state in states]
        if item["exact_content"]:
            item["reason"] = "exact content"
    return {
        "hash_bytes_read": bytes_read,
        "files_scanned": len(files),
        "threshold": threshold,
        "cross_directories": cross_directories,
        "exact_content_pairs": sum(item["exact_content"] is True for item in groups),
        "pairs": sorted(groups, key=lambda item: (-item["similarity"], item["files"])),
    }


def analyze(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError("input must be a JSON object")
    return {"version": 1, "project": PROJECT, **_filename_similarity(data)}


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [f"# {report['project'].replace('-', ' ').title()} report", ""]
    for key, value in report.items():
        if key not in {"version", "project"}:
            lines.extend(
                [
                    f"## {key.replace('_', ' ').title()}",
                    "",
                    f"```json\n{json.dumps(value, indent=2, ensure_ascii=False, default=str)}\n```",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def _budget(data: dict[str, Any], key: str) -> int | None:
    value = data.get(key)
    if value is not None and (type(value) is not int or value < 0):
        raise ValueError(f"{key} must be a non-negative integer or null")
    return value


def _signature(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _fingerprint(
    path: Path,
    per_file: int | None,
    remaining: int | None,
) -> tuple[str | None, str, int, tuple[int, int, int, int, int] | None]:
    consumed = 0
    try:
        before = _signature(path.stat())
        size = before[2]
        if per_file is not None and size > per_file:
            return None, "per_file_budget", 0, None
        if remaining is not None and size > remaining:
            return None, "total_budget", 0, None
        result = hashlib.sha256()
        with path.open("rb") as handle:
            opened = _signature(os.fstat(handle.fileno()))
            # Windows stat/fstat may expose different ctime semantics (CPython #157671).
            # Compare ctime only within the same API, retaining identity/size/mtime cross-checks.
            if opened[:4] != before[:4]:
                return None, "changed", 0, None
            while True:
                allowance = 1024 * 1024
                if per_file is not None:
                    if consumed >= per_file:
                        return None, "per_file_budget", consumed, None
                    allowance = min(allowance, per_file - consumed)
                if remaining is not None:
                    if consumed >= remaining:
                        return None, "total_budget", consumed, None
                    allowance = min(allowance, remaining - consumed)
                block = handle.read(allowance)
                if not block:
                    break
                consumed += len(block)
                result.update(block)
            if consumed != size:
                return None, "changed", consumed, None
            if _signature(os.fstat(handle.fileno())) != opened or _signature(path.stat()) != before:
                return None, "changed", consumed, None
        return result.hexdigest(), "hashed", consumed, before
    except OSError:
        return None, "unreadable", consumed, None
