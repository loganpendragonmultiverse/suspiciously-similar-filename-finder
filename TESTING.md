# Testing

Install `.[dev]` in an isolated environment and run `ruff format --check .`, `ruff check .`, `mypy src tests`, `pytest`, and `python -m build`. Keep the configured coverage threshold. The budget, streaming, unreadable and changing-file regressions are in `tests/test_feature_wave.py`. CI supplies the supported OS/Python matrix.

The sample input uses the current directory. Tests override it with temporary files so development environments and build outputs never become scan fixtures.

Windows stat/fstat may disagree on ctime semantics ([CPython #157671](https://github.com/python/cpython/issues/157671)). The regression simulates that difference while retaining descriptor/path identity, size, mtime and same-API ctime checks.
