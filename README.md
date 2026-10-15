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


## 1.2.0 candidate

JSON input accepts optional `max_hash_bytes_per_file` and `max_hash_bytes_total` non-negative integer byte limits. Omitted or null limits preserve unlimited hashing. For example:

```json
{"root":"./documents","max_hash_bytes_per_file":10485760,"max_hash_bytes_total":52428800}
```

Candidate files are streamed in chunks of at most 1 MiB, hashed once per scan, and charged against the total by bytes actually read. A file whose observed size exceeds a remaining limit is skipped; later smaller candidates may still fit. Candidate pairs are visited in combinations of sorted paths; files consume budgets when first encountered in a qualifying pair. A later path in an early pair can therefore consume budget before an earlier path in a later pair. Reports expose `hash_bytes_read`, per-file `hash_status` (`hashed`, `per_file_budget`, `total_budget`, `unreadable`, or `changed`) and pair `content_status` (`identical`, `different`, or `unverified`). Unverified pairs have `exact_content: null` and never contribute to the exact-content count. Hashing checks file identity, size and timestamps before/after reading and at final classification; it is a point-in-time local audit, not a filesystem snapshot or proof against deliberate timestamp manipulation.


A digest is verified only after the stream returns EOF and the bytes read agree with stable metadata. Virtual files whose content disagrees with st_size remain unverified. A zero-byte budget cannot verify even an empty file. If a limit is exhausted exactly at the observed size, the file remains unverified because checking EOF could consume another byte. Leave at least one byte of available allowance for that EOF check; an EOF read consumes zero bytes. Actual content bytes, including bytes from an unverified attempt, are charged to the budget.
