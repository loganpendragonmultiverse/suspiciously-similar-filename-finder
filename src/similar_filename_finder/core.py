from __future__ import annotations

import difflib
import hashlib
import json
import re
from itertools import combinations
from pathlib import Path
from typing import Any

PROJECT = "suspiciously-similar-filename-finder"


def _require(data: dict[str, Any], key: str) -> Any:
    value = data.get(key)
    if value is None or value == "" or value == []:
        raise ValueError(f"{key} is required")
    return value


def _filename_similarity(data: dict[str, Any]) -> dict[str, Any]:
    root = Path(_require(data, "root")).resolve()
    if not root.is_dir():
        raise ValueError("root must be an existing directory")
    threshold = float(data.get("threshold", 0.72))
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    cross_directories = bool(data.get("cross_directories", False))
    files = [
        path for path in sorted(root.rglob("*")) if path.is_file() and ".git" not in path.parts
    ]
    normalized = {}
    for path in files:
        stem = re.sub(
            "\\b(final|copy|backup|old|new|rev|version|v)\\b|\\(\\d+\\)|[-_ ]?\\d+$",
            "",
            path.stem.casefold(),
        ).strip(" -_()")
        normalized[path] = re.sub("[^a-z0-9]+", " ", stem).strip()
    groups = []
    fingerprints: dict[Path, str] = {}
    for left, right in combinations(files, 2):
        if not cross_directories and left.parent != right.parent:
            continue
        score = difflib.SequenceMatcher(None, normalized[left], normalized[right]).ratio()
        variant_marker = (
            normalized[left] == normalized[right] and left.name.casefold() != right.name.casefold()
        )
        if score >= threshold or variant_marker:
            for path in (left, right):
                fingerprints.setdefault(path, hashlib.sha256(path.read_bytes()).hexdigest())
            exact_content = fingerprints[left] == fingerprints[right]
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
    return {
        "files_scanned": len(files),
        "threshold": threshold,
        "cross_directories": cross_directories,
        "exact_content_pairs": sum(item["exact_content"] for item in groups),
        "pairs": sorted(groups, key=lambda item: (-item["similarity"], item["files"])),
    }


def analyze(data: dict[str, Any]) -> dict[str, Any]:
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
