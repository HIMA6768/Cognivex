# Testing

R4 tests cover serializable preprocessing contracts, source-to-canonical subtype mapping, independent task eligibility, stable exclusion reasons, train-only imputation/scaling, exact original-value indicators, unknown categories, deterministic feature ordering, sklearn cloneability, Track C identity handling, target/mutation exclusion, fail-loud leakage guards, canonical counts, fitted-state invariance, and canonical artifact immutability. R1–R3 shell, ingestion, and quality tests remain active.

R4D tests add controlled annotation parsing, malformed/missing rejection, inclusive 5% fit-local selection, transform-time selection stability, fold-varying gene sets, all-source-gene log1p burden, continuous-versus-binary scaling metadata, Track D eligibility, Track B isolation, P0 evidence agreement, canonical 27/44 evidence, and aggregate four-track UI readiness. Future fold tests do not require every fold to retain 27 genes.

R5A tests cover fixed reference encoding, Track B/D isolation, framework-independent survival contracts, matrix rank/condition diagnostics, pre-fit rank stopping, C-index direction/ties/censoring, convergence-warning stops, PH diagnostics, trusted local artifact checksums, direct CLI execution, the canonical train/validation fit, and untouched-test flags.

Obsolete tests for the superseded domain were removed with their production modules. Test count is not used as a success metric.

Run:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q app.py src tests
python -m compileall -q app.py src scripts tests
python -m pip check
```
