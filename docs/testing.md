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

R7 tests cover the exact genomic-only 50/18/68 contract; canonical target eligibility and manifest ordering; shared R4D mutation semantics; candidate-specific train-only preprocessing; all four frozen classifier definitions; fixed-order sklearn metrics; validation-only Macro-F1 selection and tie handling; winner-only test access; deterministic cohort/prediction/probability digests; non-overwriting aggregate artifacts; read-only trusted reload; provenance evidence; and all 28 independent audit checks.

R9 tests cover checksum-gated pre-load and post-load trust boundaries, independent per-track availability, exact transform-only R5/R6/R7 contracts, input validation/readiness isolation, output privacy, and R8 aggregate-only access. The audit lifecycle permits one explicitly marked pre-audit provenance skip during bootstrap; the final suite and final audit require zero R9 lifecycle skips.

R10-A tests cover repository-relative cached R9 service construction, partial request forwarding without UI-side preprocessing, typed Track A/B/C result rendering, safe readiness/error rendering, aggregate-only R8 rendering, AppTest page loading, and an AST guard preventing UI imports of model/preprocessing/artifact internals. R10-B0 tests compare synthetic Track A/B survival estimates against each frozen fitter's public Lifelines output at off-index 12/36/60-month horizons, reject a baseline that cannot cover those horizons, preserve log partial-hazard values, and retain the no-persistence runtime check.

R10-B1 tests cover grouped OncoMap navigation, responsive shell primitives, Overview facts/workflow/CTA, checksum-verified aggregate R5/R6/R7 Model Evaluation values, R8’s global 68/24/44 Gene Insights rendering, aggregate-only Dataset/Methodology/About pages, the transient unified 7/50/18 Patient Analysis request mapping, partial readiness, synthetic non-patient demo flow, fixed-horizon survival presentation, immutable subtype order, and an AST guard that prohibits direct UI imports/calls into artifact, model, preprocessing, or training layers.
