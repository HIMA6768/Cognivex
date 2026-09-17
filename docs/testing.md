# Testing

R4 tests cover serializable preprocessing contracts, source-to-canonical subtype mapping, independent task eligibility, stable exclusion reasons, train-only imputation/scaling, exact original-value indicators, unknown categories, deterministic feature ordering, sklearn cloneability, Track C identity handling, target/mutation exclusion, fail-loud leakage guards, canonical counts, fitted-state invariance, and canonical artifact immutability. R1–R3 shell, ingestion, and quality tests remain active.

Obsolete tests for the superseded domain were removed with their production modules. Test count is not used as a success metric.

Run:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q app.py src tests
python -m compileall -q app.py src scripts tests
python -m pip check
```
