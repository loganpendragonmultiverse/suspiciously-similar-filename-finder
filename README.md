# Suspiciously Similar Filename Finder

[![CI](https://github.com/loganpendragonmultiverse/suspiciously-similar-filename-finder/actions/workflows/ci.yml/badge.svg)](https://github.com/loganpendragonmultiverse/suspiciously-similar-filename-finder/actions/workflows/ci.yml)

Identify likely duplicate or versioned filenames such as final, final-2, and copy variants. The command uses explicit UTF-8 JSON input and produces reviewable JSON or Markdown output.

## Three-minute start

```bash
python -m pip install .
similar-filenames examples/sample.json
similar-filenames examples/sample.json --format json --output report.json
```

The example documents the input shape. Version 1.1 hashes candidate pairs to distinguish byte-identical content from name-only similarity, validates the threshold, and supports opt-in `cross_directories` comparison. Existing report files are never overwritten. Source inputs are read-only except where the documented purpose explicitly creates a new output artifact.

## Privacy and platforms

The tool runs locally and does not upload input or include telemetry. Python 3.10 or newer is supported on Windows, macOS, and Linux.

## Interpretation boundary

Filename similarity does not establish identical contents. The tool is read-only and never deletes, renames, or merges files.

## Development

```bash
python -m pip install -e ".[dev]"
ruff format --check .
ruff check .
mypy src
pytest
python -m build
```

The project is feature-complete for its documented v1 scope. Maintenance focuses on correctness, security, compatibility, and well-supported input improvements.

Part of the [Logan Pendragon Forge open-source collection](https://www.loganpendragonforge.com/open-source/). Licensed under the [MIT License](LICENSE).
