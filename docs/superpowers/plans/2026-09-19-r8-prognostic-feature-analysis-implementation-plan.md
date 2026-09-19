# R8 Prognostic Genomic Feature Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a checksum-gated, read-only R8 analysis of the frozen R6 Track B penalized Cox model that extracts all 68 approved genomic coefficients, derives deterministic model-associated hazard summaries, persists a reproducible aggregate bundle, and passes the independent 30-check audit.

**Architecture:** Verify the canonical R6 bundle and every covered checksum before trusted pickle loading, then validate one exact 80-feature order across the persisted contract, fitted preprocessor, adapter, Cox coefficients, and Cox summary. Map only the approved 50 expression and 18 mutation-presence predictors, derive finite coefficient/hazard summaries and deterministic ranks, persist aggregate-only evidence, and independently reproduce and audit the result without fitting or reading patient rows.

**Tech Stack:** Python, pandas, NumPy, lifelines, existing Cognivex artifact/trust infrastructure, `csv`, `json`, `hashlib`, `pathlib`, pytest.

**Spec:** `docs/superpowers/specs/2026-09-19-r8-prognostic-feature-analysis-design.md`

## Global Constraints

- Execute later with native execution in one Codex session using `superpowers:executing-plans`; subagents remain off.
- R8 is analysis-only. No task may call `model.fit`, `fit_transform`, `CoxPHFitter.fit`, an R5/R6/R7 training entrypoint, or engineer training code.
- Do not retrain Track B, create another Cox model, create patient predictions, read patient rows for analysis, or modify canonical R6 artifacts.
- The only source bundle is `artifacts/models/track_b/r6-track-b-v1/`.
- The source model is frozen at `CoxPHFitter(baseline_estimation_method="breslow", penalizer=0.05, l1_ratio=0.5, alpha=0.05)`.
- The frozen encoded feature count is 80: 12 excluded clinical outputs, 50 expression outputs, and 18 mutation-presence outputs.
- Analyze exactly 68 genomic predictors and zero clinical predictors; retain all 68 in the canonical table.
- Freeze `COEF_EPS = 1e-6`, `is_active = abs(beta) > COEF_EPS`, and inclusive inactive boundaries at `abs(beta) <= COEF_EPS`.
- Rank by descending `abs_beta`, then ascending `frozen_genomic_order`.
- Treat p-values and confidence intervals as descriptive model-reported penalized-Cox output only; they never select, filter, rank, or emphasize a feature.
- Load pickles only through `src.artifacts.survival.load_trusted_pickle(path, trusted=True)` and only after path, frozen-source, checksum, metadata, and feature-contract validation.
- Never load a historical engineer pickle.
- Use current dependencies only. Do not add SHAP, statsmodels, biological libraries, visualization packages, or external APIs.
- R5, R6, R7, canonical data, and `ai_handoff_data/` remain unchanged.
- Do not add Streamlit, inference, orchestration, patient analysis, deployment, external enrichment, or R9 work.

## Review Focus

1. **A corrupt pickle is deserialized before its checksum fails.** Task 2 owns `test_checksum_failure_prevents_pickle_loader_call`, which uses a fail-fast loader spy and requires zero loader calls.
2. **The genomic mapping has the right 50/18 counts but a wrong fitted order.** Task 3 owns `test_mapping_rejects_reordered_authority_even_when_counts_match`, checking all four fitted authorities.
3. **Exact `COEF_EPS` boundaries drift because of inconsistent comparisons.** Task 4 owns `test_activity_and_direction_are_inclusive_at_both_exact_boundaries` for `+1e-6` and `-1e-6` plus adjacent floating-point values.
4. **A small p-value changes rank or report emphasis.** Task 5 owns `test_p_value_changes_cannot_change_rank_or_activity`; Task 6 owns `test_report_templates_make_no_significance_claims`.
5. **Timestamps or Git provenance break analytical reproduction.** Task 6 owns `test_fixed_context_reproduces_bundle_bytes`; Task 7 owns `test_semantic_verification_ignores_only_declared_volatile_metadata` and hashes both bundles before and after verification.

---

### Task 1: Add framework-independent R8 contracts

**Files:**
- Create: `src/contracts/prognostic_features.py`
- Modify: `src/contracts/__init__.py`
- Test: `tests/test_prognostic_feature_contracts.py`

**Interfaces:**
- Consumes: `src.contracts.analysis.SerializableContract`.
- Produces: `COEF_EPS`, `FeatureType`, `EffectDirection`, `DIRECTION_DISPLAY_TEXT`, `FEATURE_EFFECTS_CSV_COLUMNS`, `GenomicFeatureMapping`, `PenalizedCoxSummaryValues`, `PrognosticFeatureEffect`, and `PrognosticFeatureAnalysisResult`.

- [ ] **Step 1: Write failing contract tests.**

Create these exact tests:

- `test_r8_constants_and_direction_values_are_frozen`
- `test_feature_effect_csv_columns_have_exact_approved_order`
- `test_mapping_accepts_only_expression_or_mutation_presence`
- `test_effect_contract_rejects_nonfinite_values_and_inconsistent_activity`
- `test_analysis_result_requires_exactly_68_unique_nonclinical_effects`
- `test_contract_vocabulary_excludes_selected_by_lasso`

Assert `COEF_EPS == 1e-6`; exact direction values and display strings; the exact 20-column CSV tuple from the spec; `FeatureType` contains only `expression` and `mutation_presence`; ranks and frozen orders are positive; all numeric fields are finite; hazard ratios and their confidence bounds are positive; and a complete result contains 50 expression plus 18 mutation effects with no clinical type.

- [ ] **Step 2: Run the contract tests and confirm RED.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_contracts.py -q
```

Expected: collection fails because `src.contracts.prognostic_features` does not exist.

- [ ] **Step 3: Implement the smallest validated contracts.**

Use string enums and frozen, slotted dataclasses. Freeze these values:

```python
COEF_EPS = 1e-6

class FeatureType(StrEnum):
    EXPRESSION = "expression"
    MUTATION_PRESENCE = "mutation_presence"

class EffectDirection(StrEnum):
    HIGHER = "associated_with_higher_modeled_hazard"
    LOWER = "associated_with_lower_modeled_hazard"
    EFFECTIVELY_ZERO = "effectively_zero_under_r8_threshold"

DIRECTION_DISPLAY_TEXT = {
    EffectDirection.HIGHER: "Associated with higher modeled hazard",
    EffectDirection.LOWER: "Associated with lower modeled hazard",
    EffectDirection.EFFECTIVELY_ZERO: "Effectively zero under the R8 numerical coefficient threshold",
}
```

Define these exact dataclass fields:

```python
GenomicFeatureMapping(
    frozen_genomic_order: int,
    raw_feature_name: str,
    model_feature_name: str,
    feature_type: FeatureType,
)
PenalizedCoxSummaryValues(
    standard_error: float,
    beta_ci_lower_95: float,
    beta_ci_upper_95: float,
    hazard_ratio_ci_lower_95: float,
    hazard_ratio_ci_upper_95: float,
    comparison_to: float,
    z_statistic: float,
    p_value: float,
    negative_log2_p_value: float,
)
PrognosticFeatureEffect(
    rank: int,
    frozen_genomic_order: int,
    raw_feature_name: str,
    model_feature_name: str,
    feature_type: FeatureType,
    beta: float,
    abs_beta: float,
    hazard_ratio: float,
    direction: EffectDirection,
    direction_display: str,
    is_active: bool,
    model_summary: PenalizedCoxSummaryValues,
)
PrognosticFeatureAnalysisResult(
    schema_version: str,
    analysis_id: str,
    coef_eps: float,
    effects: tuple[PrognosticFeatureEffect, ...],
)
```

Freeze `FEATURE_EFFECTS_CSV_COLUMNS` as `("rank", "frozen_genomic_order", "raw_feature_name", "model_feature_name", "feature_type", "beta", "abs_beta", "hazard_ratio", "direction", "direction_display", "is_active", "standard_error", "beta_ci_lower_95", "beta_ci_upper_95", "hazard_ratio_ci_lower_95", "hazard_ratio_ci_upper_95", "comparison_to", "z_statistic", "p_value", "negative_log2_p_value")`. Validate exact counts, unique names/orders/ranks, finite numbers, positive hazard ratios, direction/activity consistency, and consecutive ranks. Export every public contract from `src/contracts/__init__.py`.

- [ ] **Step 4: Run focused tests and confirm GREEN.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_contracts.py -q
```

Expected: all Task 1 tests pass.

- [ ] **Step 5: Run relevant contract regressions.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py tests/test_survival_contracts.py tests/test_track_b_artifacts.py tests/test_track_c_contracts.py -q
```

Expected: existing contracts remain green.

- [ ] **Step 6: Commit Task 1.**

```powershell
git add src/contracts/prognostic_features.py src/contracts/__init__.py tests/test_prognostic_feature_contracts.py
git commit -m "feat(r8): add prognostic feature contracts"
```

### Task 2: Verify and trusted-load the frozen R6 source

**Files:**
- Create: `src/artifacts/prognostic_features.py`
- Create: `tests/r8_helpers.py`
- Modify: `src/artifacts/__init__.py`
- Test: `tests/test_prognostic_feature_source.py`

**Interfaces:**
- Consumes: `load_trusted_pickle(path: Path, *, trusted: bool = False)`, `track_b_feature_names(preprocessor)`, canonical R6 JSON/checksum files, `PenalizedCoxPHAdapter`, and sklearn `Pipeline`.
- Produces: `R6_BUNDLE_RELATIVE`, `VerifiedTrackBSource`, `verify_r6_checksums(bundle: Path) -> dict[str, str]`, and `verify_and_load_track_b_source(bundle: Path, repository_root: Path) -> VerifiedTrackBSource`.

- [ ] **Step 1: Create reusable no-fit R8 test fixtures and failing source tests.**

`tests/r8_helpers.py` must create a temporary repository-root-shaped canonical bundle containing copied JSON contracts, deterministic placeholder pickle bytes, and a generated checksum manifest. It must return monkeypatchable fitted-object doubles without calling any fit method.

Create these exact tests:

- `test_canonical_verified_bundle_loads_after_all_preload_checks`
- `test_alternate_source_bundle_path_is_rejected`
- `test_checksum_failure_prevents_pickle_loader_call`
- `test_wrong_experiment_or_task_identity_is_rejected`
- `test_wrong_penalizer_l1_ratio_alpha_or_baseline_is_rejected`
- `test_wrong_adapter_type_or_unfitted_adapter_is_rejected`
- `test_wrong_preprocessor_type_is_rejected`
- `test_engineer_pickle_path_is_rejected`
- `test_source_verifier_imports_no_training_or_engineer_module`

The checksum-order test monkeypatches `src.artifacts.prognostic_features.load_trusted_pickle` with a function that raises `AssertionError` if called and asserts its call count remains zero after a deliberate checksum mismatch.

- [ ] **Step 2: Run source tests and confirm RED.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_source.py -q
```

Expected: import fails because the R8 artifact source boundary does not exist.

- [ ] **Step 3: Implement the ordered trust gate.**

`verify_and_load_track_b_source` must execute exactly:

```python
resolved = Path(bundle).resolve()
canonical = (Path(repository_root).resolve() / R6_BUNDLE_RELATIVE).resolve()
if resolved != canonical:
    raise ValueError("R8 source must be the canonical R6 bundle")
verify_frozen_r6_tracked_state(repository_root)
digests = verify_r6_checksums(resolved)
metadata = read_and_validate_r6_metadata(resolved / "metadata.json")
contract = read_and_validate_r6_contract(resolved / "feature_contract.json")
preprocessor = load_trusted_pickle(resolved / "preprocessor.pkl", trusted=True)
model = load_trusted_pickle(resolved / "cox_model.pkl", trusted=True)
return validate_loaded_track_b_source(
    repository_root=repository_root,
    bundle=resolved,
    metadata=metadata,
    feature_contract=contract,
    verified_digests=digests,
    preprocessor=preprocessor,
    model=model,
)
```

Require the exact canonical checksum file set, R6 experiment/task/track identity, counts 7/50/18/75/80, selected configuration, Breslow/alpha values from the loaded fitter, adapter/preprocessor types, fitted state, and recorded lineage hashes. Define `VerifiedTrackBSource(repository_root: Path, bundle: Path, metadata: Mapping[str, object], feature_contract: Mapping[str, object], verified_digests: Mapping[str, str], preprocessor: Pipeline, model: PenalizedCoxPHAdapter, model_feature_names: tuple[str, ...])`; it contains no patient rows.

- [ ] **Step 4: Run focused source tests and confirm GREEN.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_source.py -q
```

Expected: all trust-gate tests pass and the corrupt-checksum test records zero loader calls.

- [ ] **Step 5: Run trusted-artifact regressions.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_survival_artifacts.py tests/test_track_b_artifacts.py tests/test_track_c_artifacts.py -q
```

Expected: R5–R7 artifact behavior remains green.

- [ ] **Step 6: Commit Task 2.**

```powershell
git add src/artifacts/prognostic_features.py src/artifacts/__init__.py tests/r8_helpers.py tests/test_prognostic_feature_source.py
git commit -m "feat(r8): verify trusted frozen Track B source"
```

### Task 3: Build and validate the exact genomic feature mapping

**Files:**
- Create: `src/analysis/__init__.py`
- Create: `src/analysis/prognostic_features.py`
- Test: `tests/test_prognostic_feature_mapping.py`

**Interfaces:**
- Consumes: `GenomicFeatureMapping`, `FeatureType`, and `VerifiedTrackBSource`.
- Produces: `build_genomic_feature_mapping(feature_contract: Mapping[str, object], model_feature_names: tuple[str, ...]) -> tuple[GenomicFeatureMapping, ...]` and `validate_genomic_mapping_authorities(mapping: tuple[GenomicFeatureMapping, ...], source: VerifiedTrackBSource) -> None`.

- [ ] **Step 1: Write failing mapping tests.**

Create these exact tests:

- `test_mapping_is_exactly_50_expression_18_mutation_and_zero_clinical`
- `test_mutation_mapping_appends_present_to_each_raw_mut_name`
- `test_mapping_rejects_79_or_81_fitted_model_names`
- `test_mapping_rejects_67_or_69_genomic_features`
- `test_mapping_rejects_duplicate_raw_or_model_name`
- `test_mapping_rejects_expression_mutation_collision`
- `test_mapping_rejects_missing_or_additional_model_name`
- `test_mapping_rejects_reordered_authority_even_when_counts_match`
- `test_all_four_fitted_authorities_must_agree`
- `test_mapping_uses_explicit_contract_not_dtype_or_prefix_discovery`

The four-authority test independently mutates the persisted model list, preprocessor names, adapter `feature_names`, `params_` index, and summary index and expects each mismatch to fail.

- [ ] **Step 2: Run mapping tests and confirm RED.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_mapping.py -q
```

Expected: imports fail because `src.analysis.prognostic_features` does not exist.

- [ ] **Step 3: Implement explicit contract mapping and four-authority validation.**

Construct only:

```python
expression = tuple(
    GenomicFeatureMapping(i, raw, raw, FeatureType.EXPRESSION)
    for i, raw in enumerate(contract["expression_features"], start=1)
)
mutation = tuple(
    GenomicFeatureMapping(i, raw, f"{raw}_present", FeatureType.MUTATION_PRESENCE)
    for i, raw in enumerate(contract["mutation_features"], start=51)
)
```

Require `model_feature_names == clinical_12 + mapped_68`, where `clinical_12` is the exact complement in persisted order. Then require equality with fitted preprocessor names, adapter names, `params_.index`, and `summary.index`. Do not inspect pandas dtypes or scan prefixes to identify genomic fields.

- [ ] **Step 4: Run focused mapping tests and confirm GREEN.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_mapping.py -q
```

Expected: all mapping tests pass.

- [ ] **Step 5: Run R6 feature-order regressions.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_track_b_preprocessing.py tests/test_track_b_artifacts.py tests/test_track_b_audit.py -q
```

Expected: R6 order and audit tests remain green.

- [ ] **Step 6: Commit Task 3.**

```powershell
git add src/analysis/__init__.py src/analysis/prognostic_features.py tests/test_prognostic_feature_mapping.py
git commit -m "feat(r8): map frozen genomic model features"
```

### Task 4: Extract coefficients and derive safe numerical values

**Files:**
- Modify: `src/analysis/prognostic_features.py`
- Test: `tests/test_prognostic_feature_analysis.py`

**Interfaces:**
- Consumes: `VerifiedTrackBSource`, `GenomicFeatureMapping`, `COEF_EPS`, `PenalizedCoxSummaryValues`, `PrognosticFeatureEffect`, and `PrognosticFeatureAnalysisResult`.
- Produces: `extract_prognostic_feature_effects(source: VerifiedTrackBSource, mapping: tuple[GenomicFeatureMapping, ...], coef_eps: float = COEF_EPS) -> PrognosticFeatureAnalysisResult`.

- [ ] **Step 1: Write failing numerical extraction tests.**

Create these exact parameterized tests:

- `test_positive_negative_zero_and_near_threshold_coefficients`
- `test_activity_and_direction_are_inclusive_at_both_exact_boundaries`
- `test_values_immediately_outside_threshold_are_active`
- `test_extraction_joins_params_and_summary_by_exact_name_not_position`
- `test_missing_or_duplicate_summary_row_is_rejected`
- `test_bool_nan_and_infinite_beta_are_rejected`
- `test_exp_overflow_and_nonpositive_or_nonfinite_hazard_ratio_are_rejected`
- `test_derived_hazard_ratio_matches_exp_beta_and_model_report`

Use synthetic betas `0.5`, `-0.5`, `0.0`, `0.5e-6`, `-0.5e-6`, `1e-6`, `-1e-6`, `math.nextafter(1e-6, math.inf)`, and `math.nextafter(-1e-6, -math.inf)`. Shuffle summary rows while preserving labels to prove exact-name joins.

- [ ] **Step 2: Run extraction tests and confirm RED.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_analysis.py -q
```

Expected: tests fail because coefficient extraction and numerical derivation are absent.

- [ ] **Step 3: Implement finite-safe derivation and exact-name extraction.**

Add private helpers with explicit behavior:

```python
def _direction(beta: float, coef_eps: float) -> EffectDirection:
    if beta > coef_eps:
        return EffectDirection.HIGHER
    if beta < -coef_eps:
        return EffectDirection.LOWER
    return EffectDirection.EFFECTIVELY_ZERO

def _hazard_ratio(beta: float) -> float:
    if isinstance(beta, bool) or not math.isfinite(beta):
        raise ValueError("beta must be a finite real number")
    try:
        value = math.exp(beta)
    except OverflowError as error:
        raise ValueError("hazard ratio overflowed") from error
    if not math.isfinite(value) or value <= 0:
        raise ValueError("hazard ratio must be finite and positive")
    return value
```

Index both `params_` and `summary` by `mapping.model_feature_name`, reject duplicate indexes, and compare `derived_hazard_ratio` with `model_reported_hazard_ratio` using `math.isclose(derived_hazard_ratio, model_reported_hazard_ratio, rel_tol=1e-12, abs_tol=1e-12)`. Build all 68 typed effects; do not use positional-only extraction. Because `PrognosticFeatureAnalysisResult` requires valid final ranks, sort with `(-abs_beta, frozen_genomic_order)` and assign ranks 1–68 here. Task 5 adds exhaustive tie, non-coefficient-independence, interval, and aggregate-summary coverage without changing this public result shape.

- [ ] **Step 4: Run focused extraction tests and confirm GREEN.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_analysis.py -q
```

Expected: numerical, threshold, finite, overflow, and name-join tests pass.

- [ ] **Step 5: Run contracts and mapping regressions.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_contracts.py tests/test_prognostic_feature_mapping.py tests/test_prognostic_feature_analysis.py -q
```

Expected: Tasks 1–4 remain green.

- [ ] **Step 6: Commit Task 4.**

```powershell
git add src/analysis/prognostic_features.py tests/test_prognostic_feature_analysis.py
git commit -m "feat(r8): extract frozen Cox genomic effects"
```

### Task 5: Preserve penalized-Cox summaries and rank deterministically

**Files:**
- Modify: `src/analysis/prognostic_features.py`
- Test: `tests/test_prognostic_feature_ranking.py`

**Interfaces:**
- Consumes: the Task 4 extraction interface and the frozen R6 summary columns.
- Produces: finalized ranked `PrognosticFeatureAnalysisResult` values through the unchanged `extract_prognostic_feature_effects(source: VerifiedTrackBSource, mapping: tuple[GenomicFeatureMapping, ...], coef_eps: float = COEF_EPS) -> PrognosticFeatureAnalysisResult` signature and `summarize_prognostic_feature_effects(result: PrognosticFeatureAnalysisResult) -> dict[str, object]`.

- [ ] **Step 1: Write failing summary and ranking tests.**

Create these exact tests:

- `test_all_nine_model_reported_summary_fields_are_preserved`
- `test_nonfinite_summary_value_or_incoherent_ci_is_rejected`
- `test_hazard_ratio_ci_must_be_finite_positive_and_ordered`
- `test_exact_abs_beta_ties_follow_frozen_genomic_order`
- `test_ranks_are_consecutive_one_through_sixty_eight`
- `test_p_value_changes_cannot_change_rank_or_activity`
- `test_activity_feature_type_and_ci_cannot_filter_or_reorder_rows`
- `test_all_effectively_zero_rows_remain_in_full_table`
- `test_analysis_produces_no_significance_classification`

Construct two effects with equal absolute coefficients and opposite signs, then reverse their input order; the lower `frozen_genomic_order` must rank first. Change p-values from `1e-12` to `0.9` without changing coefficients and require identical rank/activity output.

- [ ] **Step 2: Run ranking tests and confirm RED.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_ranking.py -q
```

Expected: failures identify missing complete summary validation and deterministic ranking behavior.

- [ ] **Step 3: Implement the smallest ranking and summary finalization.**

Read exactly `se(coef)`, coefficient and hazard-ratio 95% bounds, `cmp to`, `z`, `p`, and `-log2(p)`. Validate finite values and ordered intervals. Sort only with:

```python
ordered = sorted(effects, key=lambda item: (-item.abs_beta, item.frozen_genomic_order))
ranked = tuple(replace(item, rank=index) for index, item in enumerate(ordered, start=1))
```

`summarize_prognostic_feature_effects` returns only aggregate counts by feature type, activity, and direction plus total `68`; it emits no top-N selector and no p-value bucket.

- [ ] **Step 4: Run focused ranking tests and confirm GREEN.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_ranking.py -q
```

Expected: all summary/ranking tests pass with every row retained.

- [ ] **Step 5: Run the complete analysis-layer tests.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_contracts.py tests/test_prognostic_feature_mapping.py tests/test_prognostic_feature_analysis.py tests/test_prognostic_feature_ranking.py -q
```

Expected: Tasks 1–5 pass together.

- [ ] **Step 6: Commit Task 5.**

```powershell
git add src/analysis/prognostic_features.py tests/test_prognostic_feature_ranking.py
git commit -m "feat(r8): rank penalized Cox feature effects"
```

### Task 6: Persist the aggregate bundle and deterministic report

**Files:**
- Modify: `src/artifacts/prognostic_features.py`
- Modify: `src/artifacts/__init__.py`
- Test: `tests/test_prognostic_feature_artifacts.py`
- Test: `tests/test_prognostic_feature_report.py`

**Interfaces:**
- Consumes: `PrognosticFeatureAnalysisResult`, `VerifiedTrackBSource`, `FEATURE_EFFECTS_CSV_COLUMNS`, and `summarize_prognostic_feature_effects`.
- Produces: `render_prognostic_feature_report(result: PrognosticFeatureAnalysisResult, metadata: Mapping[str, object]) -> str`, `refresh_prognostic_feature_checksums(bundle: Path) -> None`, and `write_prognostic_feature_bundle(result: PrognosticFeatureAnalysisResult, source: VerifiedTrackBSource, output_root: Path) -> Path`.

- [ ] **Step 1: Write failing artifact, report, and language-safety tests.**

Create these exact tests:

- `test_pre_audit_bundle_has_exact_five_file_set`
- `test_feature_csv_has_exact_columns_and_sixty_eight_rows`
- `test_bundle_refuses_overwrite`
- `test_bundle_contains_no_patient_identifier_duration_event_prediction_or_risk`
- `test_float_json_csv_and_newline_serialization_are_deterministic`
- `test_fixed_context_reproduces_bundle_bytes`
- `test_metadata_contains_exact_r6_lineage_mapping_threshold_and_runtime`
- `test_summary_counts_are_derived_from_effects_not_constants`
- `test_report_contains_complete_sixty_eight_row_table_from_typed_records`
- `test_report_templates_make_no_significance_claims`
- `test_report_persists_expression_and_mutation_scale_limitations`

Scope language assertions to generated feature descriptions, headings, and conclusions. Require approved phrases and reject affirmative claims `causes poor survival`, `protective gene`, `cancer driver`, `true driver`, `validated biomarker`, `confirmed biomarker`, and `statistically significant feature`. Permit a limitations sentence that explicitly says such claims are not established.

- [ ] **Step 2: Run artifact/report tests and confirm RED.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_artifacts.py tests/test_prognostic_feature_report.py -q
```

Expected: failures identify missing bundle writer and renderer.

- [ ] **Step 3: Implement non-overwriting deterministic persistence.**

Before audit, write exactly:

```text
feature_effects.csv
metadata.json
summary.json
report.md
checksums.sha256
```

Use the exact 20-column contract, `.17g` for floats, `csv.DictWriter(stream, fieldnames=FEATURE_EFFECTS_CSV_COLUMNS, lineterminator="\n")`, JSON `sort_keys=True`, `indent=2`, `allow_nan=False`, UTF-8, and one trailing newline. Inject or monkeypatch timestamp/Git providers in tests; volatile `generated_at_utc` and generation commit remain metadata only. Derive report rows and summary counts from the same `result.effects` tuple. The checksum manifest sorts names and excludes itself.

- [ ] **Step 4: Run focused artifact/report tests and confirm GREEN.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_artifacts.py tests/test_prognostic_feature_report.py -q
```

Expected: exact file, serialization, language, and no-patient-output tests pass.

- [ ] **Step 5: Run analysis and existing artifact regressions.**

Run:

```powershell
$r8Tests = Get-ChildItem -LiteralPath tests -Filter 'test_prognostic_feature_*.py' | Select-Object -ExpandProperty FullName
.\.venv\Scripts\python.exe -m pytest $r8Tests tests/test_track_b_artifacts.py tests/test_track_c_artifacts.py -q
```

Expected: R8 focused tests and R6/R7 artifact tests pass.

- [ ] **Step 6: Commit Task 6.**

```powershell
git add src/artifacts/prognostic_features.py src/artifacts/__init__.py tests/test_prognostic_feature_artifacts.py tests/test_prognostic_feature_report.py
git commit -m "feat(r8): persist prognostic feature evidence"
```

### Task 7: Add read-only artifact verification

**Files:**
- Modify: `src/artifacts/prognostic_features.py`
- Modify: `src/artifacts/__init__.py`
- Create: `scripts/verify_prognostic_feature_artifacts.py`
- Test: `tests/test_prognostic_feature_verification.py`
- Test: `tests/test_prognostic_feature_cli.py`

**Interfaces:**
- Consumes: `verify_and_load_track_b_source`, `build_genomic_feature_mapping`, `validate_genomic_mapping_authorities`, `extract_prognostic_feature_effects`, and the persisted R8 bundle.
- Produces: `PrognosticFeatureBundleVerification(passed: bool, checks: Mapping[str, bool])` and `verify_prognostic_feature_bundle(bundle: Path, r6_bundle: Path, repository_root: Path) -> PrognosticFeatureBundleVerification` plus a read-only CLI.

- [ ] **Step 1: Write failing read-only verification tests.**

Create these exact tests:

- `test_verifier_rebuilds_and_compares_all_sixty_eight_rows`
- `test_verifier_checks_order_values_summary_report_lineage_and_checksums`
- `test_semantic_verification_ignores_only_declared_volatile_metadata`
- `test_verifier_detects_tampered_effect_summary_report_or_lineage`
- `test_verifier_hashes_r6_and_r8_before_and_after_and_writes_nothing`
- `test_verifier_never_refreshes_checksums`
- `test_verifier_cli_help_runs_from_repository_root`
- `test_verifier_cli_returns_zero_only_for_pass`

Take a SHA-256 map of every R6 and R8 bundle file immediately before and after verification and require exact dictionary equality. Monkeypatch every file-writing helper and checksum-refresh function to raise if called.

- [ ] **Step 2: Run verification tests and confirm RED.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_verification.py tests/test_prognostic_feature_cli.py -q
```

Expected: failures identify the absent verification contract, function, and CLI.

- [ ] **Step 3: Implement in-memory reproduction and read-only CLI.**

The verifier must:

```python
before_r6 = hash_tree(r6_bundle)
before_r8 = hash_tree(bundle)
source = verify_and_load_track_b_source(r6_bundle, repository_root)
mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
validate_genomic_mapping_authorities(mapping, source)
recomputed = extract_prognostic_feature_effects(source, mapping)
persisted = read_persisted_prognostic_feature_bundle(bundle)
checks = compare_recomputed_and_persisted(recomputed, persisted, source)
after_r6 = hash_tree(r6_bundle)
after_r8 = hash_tree(bundle)
checks["source_unchanged"] = before_r6 == after_r6
checks["bundle_unchanged"] = before_r8 == after_r8
return PrognosticFeatureBundleVerification(passed=all(checks.values()), checks=checks)
```

Semantic comparison excludes only `generated_at_utc` and generation Git commit from reproducibility equality; it still validates their syntax and presence. The CLI accepts required `--bundle` and optional canonical-default `--source-bundle`, prints `PASS`/`FAIL` and sorted checks, and never writes.

- [ ] **Step 4: Run focused verification tests and confirm GREEN.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_verification.py tests/test_prognostic_feature_cli.py -q
```

Expected: semantic, tamper, checksum, CLI, and before/after hash tests pass.

- [ ] **Step 5: Run artifact regression tests.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_artifacts.py tests/test_prognostic_feature_report.py tests/test_prognostic_feature_verification.py tests/test_track_c_artifacts.py -q
```

Expected: all artifact writers and read-only verifiers remain green.

- [ ] **Step 6: Commit Task 7.**

```powershell
git add src/artifacts/prognostic_features.py src/artifacts/__init__.py scripts/verify_prognostic_feature_artifacts.py tests/test_prognostic_feature_verification.py tests/test_prognostic_feature_cli.py
git commit -m "feat(r8): verify prognostic artifacts read-only"
```

### Task 8: Add the analysis CLI

**Files:**
- Create: `scripts/analyze_prognostic_features.py`
- Modify: `tests/test_prognostic_feature_cli.py`

**Interfaces:**
- Consumes: the Task 2 source loader, Task 3 mapping, Task 4/5 extraction, and Task 6 writer.
- Produces: `scripts/analyze_prognostic_features.py` with `--analysis-id`, `--source-bundle`, and `--output-root` arguments and `main() -> int`.

- [ ] **Step 1: Write failing analysis CLI tests.**

Create these exact tests:

- `test_analysis_cli_help_runs_from_repository_root`
- `test_analysis_id_rejects_uppercase_path_separators_and_parent_segments`
- `test_analysis_cli_enforces_canonical_r6_source`
- `test_analysis_cli_refuses_existing_bundle`
- `test_analysis_cli_calls_verify_map_extract_write_in_order_without_fitting`
- `test_analysis_cli_never_imports_training_or_patient_data_modules`

The call-order test replaces each stage with a spy appending `verify`, `map`, `extract`, and `write`, then asserts that exact sequence. Replace `model.fit`, `fit_transform`, and known training entrypoints with fail-fast sentinels.

- [ ] **Step 2: Run CLI tests and confirm RED.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_cli.py -q
```

Expected: analysis CLI tests fail because the script does not exist.

- [ ] **Step 3: Implement the repository-root CLI.**

Use defaults:

```python
--analysis-id r8-prognostic-features-v1
--source-bundle ROOT / "artifacts/models/track_b/r6-track-b-v1"
--output-root ROOT / "artifacts/analysis"
```

Validate IDs with `r"[a-z0-9][a-z0-9._-]*"`; enforce the canonical source in `verify_and_load_track_b_source`; execute verify → map/authority validation → extract/rank → persist; print aggregate JSON containing bundle path, analysis ID, total, active, and effectively-zero counts. Import no `src.training` or `cognivex_ml` module.

- [ ] **Step 4: Run focused CLI tests and confirm GREEN.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_cli.py -q
```

Expected: help, ID, canonical-path, non-overwrite, call-order, and no-training tests pass.

- [ ] **Step 5: Run all focused R8 tests.**

Run:

```powershell
$r8Tests = Get-ChildItem -LiteralPath tests -Filter 'test_prognostic_feature_*.py' | Select-Object -ExpandProperty FullName
.\.venv\Scripts\python.exe -m pytest $r8Tests -q
```

Expected: all Tasks 1–8 pass without canonical artifact generation.

- [ ] **Step 6: Commit Task 8.**

```powershell
git add scripts/analyze_prognostic_features.py tests/test_prognostic_feature_cli.py
git commit -m "feat(r8): add prognostic analysis CLI"
```

### Task 9: Add the independent 30-check audit

**Files:**
- Create: `src/audit/prognostic_features.py`
- Modify: `src/audit/__init__.py`
- Create: `scripts/audit_prognostic_features.py`
- Test: `tests/test_prognostic_feature_audit.py`

**Interfaces:**
- Consumes: the canonical source/bundle verifiers, R5/R6/R7 frozen commits, and a literal successful full-suite summary.
- Produces: `R8_AUDIT_CHECK_NAMES`, `PrognosticFeatureAuditCheck(number: int, name: str, passed: bool, evidence: str)`, `PrognosticFeatureAuditReport(status: str, checks: tuple[PrognosticFeatureAuditCheck, ...], full_test_suite_summary: str)`, `finalize_prognostic_feature_audit(checks: tuple[PrognosticFeatureAuditCheck, ...], full_test_suite_summary: str) -> PrognosticFeatureAuditReport`, `audit_prognostic_feature_bundle(bundle: Path, r6_bundle: Path, repository_root: Path, full_test_suite_summary: str) -> PrognosticFeatureAuditReport`, and `write_prognostic_feature_audit(bundle: Path, r6_bundle: Path, repository_root: Path, full_test_suite_summary: str) -> PrognosticFeatureAuditReport`.

- [ ] **Step 1: Write failing audit-contract and persistence tests.**

Create these exact tests:

- `test_audit_names_are_exactly_numbered_one_through_thirty`
- `test_audit_check_numbers_are_unique`
- `test_any_failed_check_makes_status_blocked`
- `test_only_thirty_true_checks_make_status_pass`
- `test_check_twenty_nine_requires_literal_successful_full_suite_summary`
- `test_audit_checks_frozen_r5_r6_r7_sources_and_artifacts`
- `test_audit_detects_fitting_imports_or_calls`
- `test_audit_writer_adds_audit_before_final_checksum_manifest`
- `test_final_checksum_manifest_covers_audit_and_excludes_itself`
- `test_audit_rerun_replaces_bootstrap_summary_with_final_summary`
- `test_audit_rerun_does_not_regenerate_feature_effects`
- `test_audit_cli_help_and_blocked_exit_code`

Freeze these exact names and order:

1. `Canonical R6 bundle identity is correct.`
2. `R6 model checksum and identity are unchanged.`
3. `R6 preprocessor and feature contract are unchanged.`
4. `R5 source and artifacts are unchanged.`
5. `R7 source and artifacts are unchanged.`
6. `R8 performs no model or preprocessing fitting.`
7. `Exactly 68 genomic predictors are analyzed.`
8. `Exactly 50 expression predictors are analyzed.`
9. `Exactly 18 mutation-presence predictors are analyzed.`
10. `Zero clinical predictors enter the genomic ranking.`
11. `Raw-to-model genomic mapping matches all frozen R6 orders.`
12. `Every genomic coefficient exists exactly once.`
13. `Every beta is finite.`
14. `Every abs_beta equals abs(beta).`
15. `Every hazard ratio equals exp(beta) within the frozen tolerance.`
16. `Every hazard ratio is finite and positive.`
17. `COEF_EPS and is_active are applied exactly.`
18. `Direction labels and display text match beta and tolerance.`
19. `Ranking is descending by absolute beta.`
20. `Exact ties follow frozen genomic order.`
21. `Effectively-zero features remain present and are labeled consistently.`
22. `Model-reported inferential values are not used for ranking, activity, or filtering.`
23. `Historical engineer pickles were not loaded.`
24. `No patient-level data is persisted.`
25. `Report, summary, and feature table agree.`
26. `Metadata lineage points to the exact frozen R6 source.`
27. `Final bundle checksums verify.`
28. `Artifact generation is reproducible and read-only relative to R6.`
29. `The complete test suite passes.`
30. `R9 was not started.`

- [ ] **Step 2: Run audit tests and confirm RED.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_audit.py -q
```

Expected: collection fails because the R8 audit module and CLI are absent.

- [ ] **Step 3: Implement all 30 checks and fail-closed finalization.**

Require `tuple(check.number for check in checks) == tuple(range(1, 31))`, exact names, no duplicates, and `status="PASS"` only when every check passes. Check 6 combines AST/import-boundary inspection with fail-fast runtime tests. Check 29 parses the final pytest summary and requires an explicitly successful run.

Implement audit persistence in this exact two-pass order to resolve checksum self-reference:

```text
1. Evaluate checks against the pre-audit bundle and create a provisional audit payload.
2. Write audit.json.
3. Refresh checksums.sha256 so it covers audit.json and every other file except itself.
4. Re-evaluate the complete bundle, including final checksum check 27.
5. Write the final audit.json containing the re-evaluated 30 checks.
6. Refresh checksums.sha256 again so it covers the exact final audit bytes.
7. Verify the final checksum manifest; raise and leave status BLOCKED if verification fails.
```

The CLI requires `--bundle`, canonical-default `--source-bundle`, `--full-test-suite-summary-file`, and `--full-test-suite-passed`; it exits zero only for final 30/30 PASS.

- [ ] **Step 4: Run focused audit tests and confirm GREEN.**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prognostic_feature_audit.py -q
```

Expected: exact-name/count, failure propagation, full-suite evidence, two-pass persistence, and checksum-order tests pass.

- [ ] **Step 5: Run complete focused R8 tests.**

Run:

```powershell
$r8Tests = Get-ChildItem -LiteralPath tests -Filter 'test_prognostic_feature_*.py' | Select-Object -ExpandProperty FullName
.\.venv\Scripts\python.exe -m pytest $r8Tests -q
```

Expected: all R8 unit/integration tests pass before canonical generation.

- [ ] **Step 6: Commit Task 9.**

```powershell
git add src/audit/prognostic_features.py src/audit/__init__.py scripts/audit_prognostic_features.py tests/test_prognostic_feature_audit.py
git commit -m "feat(r8): add independent prognostic audit"
```

### Task 10: Generate canonical R8 evidence, update active documentation, and verify provenance

**Files:**
- Create: `tests/test_r8_canonical_provenance.py`
- Create: `artifacts/analysis/r8-prognostic-features-v1/feature_effects.csv`
- Create: `artifacts/analysis/r8-prognostic-features-v1/metadata.json`
- Create: `artifacts/analysis/r8-prognostic-features-v1/summary.json`
- Create: `artifacts/analysis/r8-prognostic-features-v1/report.md`
- Create: `artifacts/analysis/r8-prognostic-features-v1/audit.json`
- Create: `artifacts/analysis/r8-prognostic-features-v1/checksums.sha256`
- Create: `docs/prognostic_feature_analysis.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture.md`
- Modify: `docs/model_integration.md`
- Modify: `docs/mutation_preprocessing.md`
- Modify: `docs/limitations.md`
- Modify: `docs/implementation_log.md`
- Test: `tests/test_r8_canonical_provenance.py`

**Interfaces:**
- Consumes: the completed analysis/audit CLIs, frozen R6 bundle, approved R8 spec, and all prior R8 tests.
- Produces: the one canonical `r8-prognostic-features-v1` aggregate bundle, active roadmap documentation, immutable provenance regression evidence, and a final 30/30 audit.

- [ ] **Step 1: Write the failing canonical provenance test before generation.**

Create these exact tests:

- `test_canonical_r8_bundle_matches_approved_pre_and_post_audit_file_sets`
- `test_canonical_r8_evidence_has_68_rows_50_expression_18_mutation_and_zero_clinical`
- `test_canonical_activity_counts_are_current_evidence_24_and_44`
- `test_canonical_metadata_matches_frozen_r6_hashes_and_configuration`
- `test_canonical_report_summary_and_feature_table_agree`
- `test_canonical_audit_has_thirty_passing_checks`
- `test_canonical_audit_records_final_no_lifecycle_skip_pytest_summary`
- `test_canonical_checksums_verify_without_ignored_pickles`

Read only aggregate R8 evidence and tracked R6 metadata/checksum manifests. Assert 24/44 only as current canonical evidence; do not expose either value to production selectors or constructors. The lifecycle file-set test requires the exact five-file pre-audit set when `audit.json` is absent and the exact six-file final set when it is present. The canonical audit test uses `pytest.skip("audit is generated after full-suite evidence")` only during the pre-audit lifecycle; once `audit.json` exists it requires exactly 30 passing checks. On the committed final repository state no canonical provenance test is skipped.

- [ ] **Step 2: Run the provenance test and confirm RED while focused implementation tests remain GREEN.**

Run:

```powershell
$r8Tests = Get-ChildItem -LiteralPath tests -Filter 'test_prognostic_feature_*.py' | Select-Object -ExpandProperty FullName
.\.venv\Scripts\python.exe -m pytest $r8Tests -q
.\.venv\Scripts\python.exe -m pytest tests/test_r8_canonical_provenance.py -q
```

Expected: all focused implementation tests pass; provenance tests fail because the canonical R8 bundle does not exist.

- [ ] **Step 3: Snapshot every frozen R6 bundle hash before analysis.**

Run:

```powershell
$r6Snapshot = Join-Path $env:TEMP 'cognivex-r8-r6-before.json'
$r6Bundle = Resolve-Path 'artifacts/models/track_b/r6-track-b-v1'
$before = Get-ChildItem -LiteralPath $r6Bundle -File | Sort-Object Name | ForEach-Object {
    [PSCustomObject]@{ Name = $_.Name; SHA256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLower() }
}
$before | ConvertTo-Json | Set-Content -LiteralPath $r6Snapshot -Encoding utf8
```

Expected: the temporary snapshot lists all canonical R6 files and writes nothing under the repository.

- [ ] **Step 4: Generate the canonical R8 bundle exactly once.**

Run:

```powershell
.\.venv\Scripts\python.exe scripts/analyze_prognostic_features.py --analysis-id r8-prognostic-features-v1 --source-bundle artifacts/models/track_b/r6-track-b-v1 --output-root artifacts/analysis
```

Expected: exit 0; the pre-audit bundle contains exactly five files, 68 effects, and derived current evidence of 24 active plus 44 effectively-zero rows. Do not rerun this command against the existing canonical bundle.

- [ ] **Step 5: Inspect aggregate evidence and confirm GREEN for pre-audit provenance tests.**

Run:

```powershell
Import-Csv -LiteralPath 'artifacts/analysis/r8-prognostic-features-v1/feature_effects.csv' | Group-Object feature_type,is_active | Select-Object Name,Count
Get-Content -LiteralPath 'artifacts/analysis/r8-prognostic-features-v1/summary.json'
Get-Content -LiteralPath 'artifacts/analysis/r8-prognostic-features-v1/metadata.json'
.\.venv\Scripts\python.exe -m pytest tests/test_r8_canonical_provenance.py -q -k "not canonical_audit"
```

Expected: aggregate counts derive to 68/50/18/24/44, lineage matches R6, and every selected pre-audit provenance test passes. The audit test remains unselected until Step 10.

- [ ] **Step 6: Run the pre-audit read-only verifier.**

Run:

```powershell
.\.venv\Scripts\python.exe scripts/verify_prognostic_feature_artifacts.py --bundle artifacts/analysis/r8-prognostic-features-v1 --source-bundle artifacts/models/track_b/r6-track-b-v1
```

Expected: `PASS`; no R6 or R8 file hash changes. The verifier accepts the approved pre-audit five-file state and the final six-file state.

- [ ] **Step 7: Update active documentation from generated aggregate evidence.**

Document the exact R8 source/model boundary, 68-feature mapping, `COEF_EPS`, 24/44 current evidence, ranking rule, penalized-summary caveat, artifact paths, audit/verifier commands, and scientific limitations. Replace `R8 gene importance and biological support` in `docs/architecture.md` with frozen-R6 prognostic genomic feature analysis. State in `docs/model_integration.md` and `docs/mutation_preprocessing.md` that Track D model fitting remains deferred and unapproved. Do not modify imported engineer documentation or make biological-support claims.

- [ ] **Step 8: Run the complete test suite once and capture bootstrap evidence.**

Run:

```powershell
$bootstrapPytestEvidence = Join-Path $env:TEMP 'cognivex-r8-bootstrap-pytest.txt'
.\.venv\Scripts\python.exe -m pytest -ra 2>&1 | Tee-Object -FilePath $bootstrapPytestEvidence
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Get-Content -LiteralPath $bootstrapPytestEvidence | Select-Object -Last 1
```

Expected: pytest exits 0 and the final line is a literal successful bootstrap summary accepted by the audit parser. The canonical audit provenance assertion may still carry the approved pre-audit lifecycle skip because `audit.json` does not exist yet. This run bootstraps audit persistence but is not final evidence for audit check 29.

- [ ] **Step 9: Persist the initial audit from bootstrap evidence and refresh checksums.**

Run:

```powershell
.\.venv\Scripts\python.exe scripts/audit_prognostic_features.py --bundle artifacts/analysis/r8-prognostic-features-v1 --source-bundle artifacts/models/track_b/r6-track-b-v1 --full-test-suite-summary-file $bootstrapPytestEvidence --full-test-suite-passed
```

Expected: audit exits 0, writes the first `audit.json`, and refreshes `checksums.sha256` to cover `audit.json` plus the four other evidence files while excluding itself. This initial audit is lifecycle bootstrap evidence and must not be committed as the final audit.

- [ ] **Step 10: Run post-bootstrap read-only verification and canonical provenance tests.**

Run:

```powershell
.\.venv\Scripts\python.exe scripts/verify_prognostic_feature_artifacts.py --bundle artifacts/analysis/r8-prognostic-features-v1 --source-bundle artifacts/models/track_b/r6-track-b-v1
.\.venv\Scripts\python.exe -m pytest tests/test_r8_canonical_provenance.py -q
```

Expected: verifier reports `PASS`; canonical provenance tests now execute the six-file/audit path rather than skipping because `audit.json` exists.

- [ ] **Step 11: Run the complete repository suite again and capture the final no-lifecycle-skip evidence.**

Run:

```powershell
$finalPytestEvidence = Join-Path $env:TEMP 'cognivex-r8-final-pytest.txt'
.\.venv\Scripts\python.exe -m pytest -ra 2>&1 | Tee-Object -FilePath $finalPytestEvidence
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$finalPytestText = Get-Content -Raw -LiteralPath $finalPytestEvidence
if ($finalPytestText -match 'audit is generated after full-suite evidence') { throw 'Final full-suite evidence contains the R8 audit lifecycle skip' }
Get-Content -LiteralPath $finalPytestEvidence | Select-Object -Last 1
```

Expected: the second complete suite exits 0, the canonical R8 audit provenance test is exercised, and no skip caused by missing R8 audit evidence appears. This second summary is the only final full-suite evidence permitted for audit check 29.

- [ ] **Step 12: Finalize the audit from the second full-suite summary without regenerating canonical analysis.**

Run:

```powershell
$featureEffectsBeforeFinalAudit = (Get-FileHash -Algorithm SHA256 -LiteralPath 'artifacts/analysis/r8-prognostic-features-v1/feature_effects.csv').Hash.ToLower()
.\.venv\Scripts\python.exe scripts/audit_prognostic_features.py --bundle artifacts/analysis/r8-prognostic-features-v1 --source-bundle artifacts/models/track_b/r6-track-b-v1 --full-test-suite-summary-file $finalPytestEvidence --full-test-suite-passed
$featureEffectsAfterFinalAudit = (Get-FileHash -Algorithm SHA256 -LiteralPath 'artifacts/analysis/r8-prognostic-features-v1/feature_effects.csv').Hash.ToLower()
if ($featureEffectsBeforeFinalAudit -ne $featureEffectsAfterFinalAudit) { throw 'Audit rerun regenerated canonical analytical evidence' }
```

Expected: audit exits 0, records the second/final pytest summary, leaves all 30 checks `PASS`, refreshes final checksums including the exact final `audit.json`, and does not rerun the canonical analysis or change `feature_effects.csv`.

- [ ] **Step 13: Run final read-only verification and canonical provenance tests against final bytes.**

Run:

```powershell
.\.venv\Scripts\python.exe scripts/verify_prognostic_feature_artifacts.py --bundle artifacts/analysis/r8-prognostic-features-v1 --source-bundle artifacts/models/track_b/r6-track-b-v1
.\.venv\Scripts\python.exe -m pytest tests/test_r8_canonical_provenance.py -q
```

Expected: verifier reports `PASS`; provenance tests verify the final audit/checksum bytes, the final no-lifecycle-skip pytest summary, and exactly 30 passing checks.

- [ ] **Step 14: Prove frozen R6 bytes are unchanged.**

Run:

```powershell
$before = Get-Content -Raw -LiteralPath $r6Snapshot | ConvertFrom-Json
$after = Get-ChildItem -LiteralPath 'artifacts/models/track_b/r6-track-b-v1' -File | Sort-Object Name | ForEach-Object {
    [PSCustomObject]@{ Name = $_.Name; SHA256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLower() }
}
if (($before | ConvertTo-Json -Compress) -ne ($after | ConvertTo-Json -Compress)) { throw 'Frozen R6 bundle changed during R8' }
```

Expected: no exception and byte-identical before/after hash maps.

- [ ] **Step 15: Run compile, dependency, whitespace, and status verification.**

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app.py src scripts tests
.\.venv\Scripts\python.exe -m pip check
git diff --check
git status --short
```

Expected: compileall exits 0, `pip check` reports no broken requirements, diff check is clean, and status contains only intended R8 files plus the known pre-existing untracked `ai_handoff_data/` material.

- [ ] **Step 16: Review branch-wide and working-tree frozen scope before the final evidence commit.**

Run:

```powershell
git diff --name-only 99438b53960aa015c6839d6cb4bc45a11aa387a6..HEAD -- data artifacts/models src/training src/modeling
git diff --name-only -- data artifacts/models src/training src/modeling
git diff --name-only 99438b53960aa015c6839d6cb4bc45a11aa387a6..HEAD
```

Expected: both scoped commands are empty: no committed or uncommitted canonical data, R5/R6/R7 model artifact, training, or modeling file changed. The broader branch-range command exposes the complete R8 footprint for review.

- [ ] **Step 17: Commit Task 10 canonical evidence/documentation.**

Run:

```powershell
git add artifacts/analysis/r8-prognostic-features-v1 tests/test_r8_canonical_provenance.py docs/prognostic_feature_analysis.md README.md CHANGELOG.md docs/architecture.md docs/model_integration.md docs/mutation_preprocessing.md docs/limitations.md docs/implementation_log.md
git commit -m "docs(r8): record canonical prognostic feature analysis"
```

- [ ] **Step 18: Re-run branch-history frozen-scope and complete-footprint review after the final commit.**

Run:

```powershell
git diff --name-only 99438b53960aa015c6839d6cb4bc45a11aa387a6..HEAD -- data artifacts/models src/training src/modeling
git diff --name-only 99438b53960aa015c6839d6cb4bc45a11aa387a6..HEAD
```

Expected: the frozen-scope command is empty after every R8 commit, while the broader command lists only the approved R8 plan, implementation, aggregate analysis evidence, tests, and documentation footprint.

## Canonical Generation and Audit Order

The executor must preserve this order:

```text
focused R8 tests PASS
  -> snapshot frozen R6 hashes
  -> canonical analysis exactly once
  -> inspect aggregate evidence
  -> pre-audit read-only verification
  -> update active documentation
  -> bootstrap complete pytest PASS and capture literal bootstrap summary
  -> write initial audit.json from bootstrap evidence
  -> refresh checksums including audit.json
  -> post-bootstrap read-only verification
  -> canonical provenance tests exercise audit.json
  -> FINAL complete pytest PASS with no R8 audit lifecycle skip
  -> re-evaluate all 30 checks using the FINAL pytest summary
  -> write final audit.json without regenerating canonical analysis
  -> refresh final checksums
  -> final read-only verification
  -> canonical provenance tests against final audit/checksum bytes
  -> prove R6 before/after hashes identical
  -> compileall / pip check / diff check / status
  -> branch-range and working-tree frozen-scope checks
  -> final R8 evidence/documentation commit
  -> post-commit branch-range frozen-scope check
```

Test evidence must not influence coefficients, activity, direction, rank, or report content. Audit persistence is the only write after the canonical analysis bundle is created.

## Plan Self-Review Record

- **Specification coverage:** Every approved design section maps to Tasks 1–10: contracts, trust, mapping, coefficient derivation, summaries/ranking, persistence, read-only reproduction, CLI, audit, canonical evidence, documentation, and limitations.
- **Decision completeness:** Every public type, function, file set, command, threshold, ordering rule, and audit name used by a later task is defined by an earlier task.
- **Trust boundary:** Task 2 enforces canonical path, frozen tracked source, checksums, metadata/contract identity, then pickle loading; the loader-spy test proves corrupt bytes never reach deserialization.
- **No fitting:** No step calls or permits `fit`, `fit_transform`, `CoxPHFitter.fit`, model-selection code, training entrypoints, engineer code, or patient-row loaders.
- **Feature contract:** Every task uses 80 encoded R6 names, excludes 12 clinical outputs, maps 50 expression plus 18 mutation-presence names, and analyzes all 68 genomic rows.
- **Activity and direction:** `COEF_EPS` is exactly `1e-6`; exact positive/negative boundaries are inactive; only strict magnitude excess is active.
- **Ranking and statistics:** Ranking uses only descending absolute beta and frozen-order ties; model-reported p-values and intervals are descriptive and cannot filter or reorder.
- **Artifacts:** The pre-audit bundle has five approved aggregate files; the final bundle adds only `audit.json`; no patient rows or duplicate pickles are persisted.
- **Audit:** Task 9 freezes exactly 30 unique ordered checks, fail-closed status, required full-suite evidence, and final checksum coverage of `audit.json`.
- **Final test evidence:** Task 10 uses the first complete suite only to bootstrap audit persistence, then runs the complete suite again after `audit.json` exists; check 29 records only the second successful summary, which has no R8 audit lifecycle skip.
- **Reproducibility:** Tasks 6–7 define fixed-context byte reproduction, semantic comparison excluding only declared volatile provenance, and before/after source/output hash equality.
- **Frozen-scope history:** Task 10 checks both committed branch history and the working tree against pre-R8 base `99438b53960aa015c6839d6cb4bc45a11aa387a6`, then repeats the branch-range check after the final evidence commit.
- **Roadmap scope:** Track D fitting, R7 explanation, SHAP/permutation analysis, Streamlit, inference, deployment, enrichment, and R9 are absent.
- **Execution method:** The later implementation uses native single-session execution with subagents off and `superpowers:executing-plans`.
