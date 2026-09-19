# Testing

R4 tests cover serializable preprocessing contracts, source-to-canonical subtype mapping, independent task eligibility, stable exclusion reasons, train-only imputation/scaling, exact original-value indicators, unknown categories, deterministic feature ordering, sklearn cloneability, Track C identity handling, target/mutation exclusion, fail-loud leakage guards, canonical counts, fitted-state invariance, and canonical artifact immutability. R1–R3 shell, ingestion, and quality tests remain active.

R4D tests add controlled annotation parsing, malformed/missing rejection, inclusive 5% fit-local selection, transform-time selection stability, fold-varying gene sets, all-source-gene log1p burden, continuous-versus-binary scaling metadata, Track D eligibility, Track B isolation, P0 evidence agreement, canonical 27/44 evidence, and aggregate four-track UI readiness. Future fold tests do not require every fold to retain 27 genes.

R5A tests cover fixed reference encoding, Track B/D isolation, framework-independent survival contracts, matrix rank/condition diagnostics, pre-fit rank stopping, C-index direction/ties/censoring, convergence-warning stops, PH diagnostics, trusted local artifact checksums, direct CLI execution, the canonical train/validation fit, and untouched-test flags.

R6-P0 tests cover deterministic selected-feature parsing, duplicate rejection, exact/missing/alias detection, numeric and annotation mutation representations, the approved R4D mapping metadata, expression quality, AST-only source inspection without entrypoint execution, read-only canonical/R5 hash preservation, deterministic report generation, direct CLI execution, and Git-ignore protection for imported engineer pickle artifacts.

R6 tests cover the exact 7/50/18 raw contract, stable 80-feature output, frozen R5 clinical equivalence, train-only expression scaling, shared R4D mutation parsing, immutable source frames, canonical event semantics, identical A/B cohorts, validation-only candidate selection, winner-only test access, non-overwriting persistence, trusted reload reproduction, aggregate-only artifacts, and all 25 required audit checks.

Obsolete tests for the superseded domain were removed with their production modules. Test count is not used as a success metric.

Run:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q app.py src tests
python -m compileall -q app.py src scripts tests
python -m pip check
```
