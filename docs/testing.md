# Testing

R2 tests cover repository-relative canonical paths, imported SHA-256 integrity, metadata/schema mismatch, duplicate identifiers, one-to-one mapping, locked manifest partitions, aggregate cohort summaries, semantic preparation reproducibility, session reuse/refresh, aggregate-only rendering, persistent disclaimer, and prior shell/configuration contracts.

Obsolete tests for the superseded domain were removed with their production modules. Test count is not used as a success metric.

Run (the semantic preparation test needs the optional `data-preparation` dependencies):

```powershell
python -m pip install -e ".[dev,data-preparation]"
python -m pytest -q
python -m compileall -q app.py src tests
python -m compileall -q app.py src scripts tests
python -m pip check
```
