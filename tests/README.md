# Tests

## Purpose

Unit tests for `scripts/bayan/`, run with the standard library:

```bash
python -m unittest discover -s tests -t tests
```

Each test copies `system/` and the sample library in
[`fixtures/library/`](fixtures/library/) into a temporary directory, so
tests never modify the working tree. The fixtures also serve as worked
examples of both metadata layouts (a list file per type, and one record
per file) and of the retrieval ladder (record summary, executive summary,
full content).
