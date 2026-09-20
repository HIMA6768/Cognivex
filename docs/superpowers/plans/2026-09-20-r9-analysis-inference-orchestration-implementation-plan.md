# R9 Analysis / Inference Service and Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved R9 framework-independent one-record service over the frozen R5/R6/R7 bundles, with read-only aggregate R8 access.

**Architecture:** A construction-time immutable registry validates canonical text/byte evidence before trusted deserialization, then checks loaded R5/R6/R7 objects. Track adapters create exact ordered one-row frames and use only persisted transform/predict methods; AnalysisService owns validation, readiness, safe failure isolation, and typed results.

**Tech Stack:** Python, dataclasses, pathlib, hashlib, json, pandas, NumPy, scikit-learn, lifelines, and existing Cognivex artifact/preprocessing helpers.

**Spec:** `docs/superpowers/specs/2026-09-20-r9-analysis-inference-orchestration-design.md`

## Global Constraints

- R5/R6/R7/R8 code, data, bundles, metrics, and scientific decisions are frozen. Implement R9 only.
- Production construction is only `AnalysisService.from_canonical_artifacts(repository_root: Path)`. All artifact paths are hard-coded canonical repository-relative paths.
- Pre-load gates—canonical path, exact file set, checksums, metadata identity, persisted raw contract, textual configuration/class order, and lineage—complete before every `load_trusted_pickle(..., trusted=True)` call.
- Prove the exact global 75-field namespace only through verified R6 raw-75 or verified R5-seven plus R7-68. Never infer fields from dtypes, prefixes, or caller keys.
- R5/R6 return only finite `log_partial_hazard`, label `Model log relative hazard score`, and the frozen non-clinical interpretation. Do not exponentiate, categorize, or create a survival probability/recommendation.
- R7 returns the exact ordered classes `Basal`, `Her2`, `LumA`, `LumB`, `Normal`, `claudin-low`; probabilities are finite, six-long, normalized within `1e-8`, and never `NC`.
- Reuse persisted preprocessing/pipelines and R4D mutation semantics. No `fit`, `fit_transform`, training, tuning, selection, or direct fitter prediction call.
- Only `tumor_size` and `er_status_measured_by_ihc` permit `None`/NaN; materialize as `numpy.nan` for their frozen imputer. Reject bools, blank/nonfinite values, unsupported categories, and malformed mutations.
- Requests, responses, errors, audit evidence, and logs never persist/echo feature values, identifiers, predictions, probabilities, scores, paths, tracebacks, or pickle internals. Fixtures are synthetic and nonclinical.
- No Streamlit/FastAPI/Pydantic web types, UI, API, deployment, R10+, or historical engineer pickle use.
- R8 is a separate aggregate-only, zero-input, read-only getter returning all 68 effects with no retry.
- Persist only aggregate R9 audit evidence at `artifacts/audits/r9-inference-service-v1/audit.json` and `artifacts/audits/r9-inference-service-v1/checksums.sha256`.
- Frozen scope base: `1eca09a75deea94e557632063837f2d9abc9683c`.

## Review Focus

1. Corrupted pre-load checksum/metadata/contract causes zero trusted loads while healthy independent tracks stay available (Task 2).
2. Unknown key `Tumor_Size` is a global error and runs no track (Task 7).
3. Only approved nullable clinical fields accept missing values; bool/infinity/blank/unsupported category/malformed mutation fail safely without value echo (Tasks 4–7).
4. Post-load failure cannot erase a proven 75-field namespace; unavailable track cannot retry load/inference in `analyze()` (Tasks 2, 3, 7).
5. Incidental R7 estimator class order is reordered to frozen order and `NC` is rejected (Task 6).

---

## Locked File Structure

| File | Responsibility |
|---|---|
| `src/contracts/inference.py` | Immutable enums, request/result/error/R8-view contracts. |
| `src/contracts/__init__.py` | R9 exports. |
| `src/artifacts/inference_registry.py` | Canonical pre-load/post-load validation and immutable registry. |
| `src/artifacts/__init__.py` | Registry exports. |
| `src/inference/__init__.py`, `track_a.py`, `track_b.py`, `track_c.py` | Exact frozen inference adapters. |
| `src/services/__init__.py`, `analysis.py`, `prognostic_features.py` | Orchestration and R8 aggregate reader. |
| `src/audit/inference_service.py` | Independent 31-check audit. |
| `scripts/audit_inference_service.py` | Audit writer and read-only verifier CLI. |
| `tests/test_inference_contracts.py`, `test_inference_registry.py` | Contracts and trust boundary. |
| `tests/test_inference_track_a.py`, `test_inference_track_b.py`, `test_inference_track_c.py` | Track adapters. |
| `tests/test_analysis_service.py`, `test_prognostic_feature_service.py`, `test_inference_privacy.py` | Service, R8, privacy/framework tests. |
| `tests/test_inference_service_audit.py`, `tests/test_r9_canonical_provenance.py` | Audit and final canonical lifecycle. |
| `README.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/testing.md` | R9 boundary, limitations, verification. |

### Task 1: Freeze framework-independent contracts

**Files:**
- Create: `src/contracts/inference.py`
- Modify: `src/contracts/__init__.py`
- Test: `tests/test_inference_contracts.py`

**Interfaces:**
- Produces `AnalysisTrack`, `TrackReadinessState`, `AnalysisRequest`, `RequestError`, `TrackError`, `ResultLineage`, `PrognosisResult`, `SubtypeClassificationResult`, `TrackOutcome`, `AnalysisResponse`, `PrognosticFeatureEffectView`, `PrognosticFeatureAnalysisView`, `AggregateAnalysisError`, `PrognosticFeatureAnalysisOutcome`.
- Defines `R9_SCHEMA_VERSION`, `PROGNOSIS_OUTPUT_KIND`, `PROGNOSIS_OUTPUT_LABEL`, `PROGNOSIS_INTERPRETATION`, and `FROZEN_SUBTYPE_CLASS_ORDER`.

- [ ] **Step 1: Write failing tests**

```python
def test_ready_outcome_requires_result_and_no_error() -> None:
    with pytest.raises(ValueError):
        TrackOutcome(AnalysisTrack.TRACK_A, TrackReadinessState.READY, None, None)

def test_subtype_requires_frozen_order_and_normalized_probabilities() -> None:
    with pytest.raises(ValueError):
        SubtypeClassificationResult(lineage, "Basal", ("Basal",), (1.0,))
```

Cover non-ready error requirements, finite prognosis, no `NC`, aggregate 68/50/18 order, and JSON-safe recursive serialization without feature values.

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_inference_contracts.py -q`

Expected: import failure for missing module.

- [ ] **Step 3: Implement minimum contracts**

```python
class TrackReadinessState(StrEnum):
    READY = "ready"
    MISSING_REQUIRED_FIELDS = "missing_required_fields"
    INVALID_INPUT = "invalid_input"
    ARTIFACT_UNAVAILABLE = "artifact_unavailable"
    INFERENCE_ERROR = "inference_error"

@dataclass(frozen=True, slots=True)
class TrackOutcome(SerializableContract):
    track: AnalysisTrack
    state: TrackReadinessState
    result: PrognosisResult | SubtypeClassificationResult | None
    error: TrackError | None
    def __post_init__(self) -> None:
        ready = self.state is TrackReadinessState.READY
        if ready != (self.result is not None) or ready != (self.error is None):
            raise ValueError("contradictory TrackOutcome")
```

Define the R8 view strictly as aggregate projection with R8 identity, source R6 identity, coefficient policy/counts, ordered effects, and neutral text; never path/patient data. Export all new public names.

- [ ] **Step 4: Run focused and adjacent tests**

Run: `python -m pytest tests/test_inference_contracts.py tests/test_track_c_contracts.py tests/test_prognostic_feature_audit.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/contracts/inference.py src/contracts/__init__.py tests/test_inference_contracts.py
git commit -m "feat(r9): add inference result contracts"
```

### Task 2: Build canonical pre-load registry and namespace proof

**Files:**
- Create: `src/artifacts/inference_registry.py`
- Modify: `src/artifacts/__init__.py`
- Test: `tests/test_inference_registry.py`

**Interfaces:**
- Produces `GlobalInputContract(raw_fields: tuple[str, ...])`, `PreloadedTrackArtifact`, `AvailableTrackArtifact`, `UnavailableTrackArtifact`, `R8AggregateArtifact`, `UnavailableR8AggregateArtifact`, `CanonicalArtifactRegistry`, and `preload_canonical_artifacts(repository_root: Path) -> CanonicalArtifactRegistry`.
- Uses fixed R5, R6, R7, R8 canonical paths only.

- [ ] **Step 1: Write failing pre-load tests**

```python
def test_bad_checksum_never_calls_trusted_loader(monkeypatch, root) -> None:
    calls = []
    monkeypatch.setattr(registry, "load_trusted_pickle", lambda path, **_: calls.append(path))
    corrupt_checksum(root, "track_a")
    assert registry.preload_canonical_artifacts(root).track_a.available is False
    assert calls == []

def test_r6_and_r5_r7_routes_prove_same_ordered_namespace() -> None:
    assert r6_route.raw_fields == r5_r7_route.raw_fields
    assert len(r6_route.raw_fields) == 75
```

Use text-only synthetic artifact fixtures for wrong file set/checksum/metadata/raw contract/R7 classes/engineer-pickle path. Test both routes unavailable raises `GLOBAL_INPUT_CONTRACT_UNAVAILABLE` and no dynamic discovery occurs.

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_inference_registry.py -q`

Expected: import failure.

- [ ] **Step 3: Implement ordered pre-load checks**

```python
CANONICAL_BUNDLES = {
    AnalysisTrack.TRACK_A: Path("artifacts/models/track_a/r5a-track-a-baseline-v1"),
    AnalysisTrack.TRACK_B: Path("artifacts/models/track_b/r6-track-b-v1"),
    AnalysisTrack.TRACK_C: Path("artifacts/models/track_c/r7-track-c-v1"),
}
R8_BUNDLE = Path("artifacts/analysis/r8-prognostic-features-v1")
```

For every bundle validate in order: resolved canonical path, exact expected files, checksums, metadata identity, persisted raw contract, persisted configuration/class order, and lineage. Store only safe failure code/message. Derive exact 75 fields exclusively from verified R6 or verified R5+R7 and require exact equality when both proof routes exist.

- [ ] **Step 4: Run focused and frozen artifact tests**

Run: `python -m pytest tests/test_inference_registry.py tests/test_track_b_artifacts.py tests/test_track_c_artifacts.py tests/test_r8_canonical_provenance.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/artifacts/inference_registry.py src/artifacts/__init__.py tests/test_inference_registry.py
git commit -m "feat(r9): add canonical artifact preflight registry"
```

### Task 3: Add post-load validation and independent initialization

**Files:**
- Modify: `src/artifacts/inference_registry.py`
- Modify/Test: `tests/test_inference_registry.py`

**Interfaces:**
- Produces `build_canonical_registry(repository_root: Path) -> CanonicalArtifactRegistry`. Final entries are immutable and access never loads again.

- [ ] **Step 1: Write failing post-load tests**

```python
def test_postload_r6_failure_preserves_r5_r7_namespace(monkeypatch, root) -> None:
    monkeypatch.setattr(registry, "_load_track_b", raises_postload_failure)
    built = registry.build_canonical_registry(root)
    assert built.global_contract.raw_fields == R5_FIELDS + R7_FIELDS
    assert not built.track_b.available

def test_corrupt_r7_keeps_r5_and_r6_available(root) -> None:
    built = corrupt_track_c_postload(root)
    assert built.track_a.available and built.track_b.available and not built.track_c.available
```

Cover corrupt R5/R6/R7/R8 isolation, load exactly once at construction, and no R8 pickle load.

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_inference_registry.py -q`

Expected: failure until post-load entries exist.

- [ ] **Step 3: Implement post-load checks only after pre-load success**

```python
def _load_after_preload(preloaded: PreloadedTrackArtifact):
    try:
        objects = _trusted_load_once(preloaded)
        _validate_postload_track(preloaded, objects)
        return AvailableTrackArtifact(preloaded, *objects)
    except Exception:
        return UnavailableTrackArtifact("ARTIFACT_UNAVAILABLE", "Canonical artifact is unavailable")
```

Validate R5 fitted preprocessor/adapter/raw7/transformed12/Cox identity; R6 through `verify_and_load_track_b_source` with PenalizedCoxPHAdapter/CoxPHFitter/fitted/80/config checks; R7 fitted sklearn Pipeline/random forest/raw68/classes. Post-load failure alters only its entry, never the pre-proven global contract.

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/test_inference_registry.py tests/test_track_a_integration.py tests/test_track_b_audit.py tests/test_track_c_audit.py -q`

Expected: PASS.

```powershell
git add src/artifacts/inference_registry.py tests/test_inference_registry.py
git commit -m "feat(r9): validate trusted inference artifacts"
```

### Task 4: Implement exact R5 transform-only adapter

**Files:**
- Create: `src/inference/__init__.py`, `src/inference/track_a.py`
- Test: `tests/test_inference_track_a.py`

**Interfaces:**
- Produces `TrackAInferenceAdapter.required_fields: tuple[str, ...]` and `predict(features: Mapping[str, object]) -> PrognosisResult`.

- [ ] **Step 1: Write failing tests**

```python
def test_track_a_transforms_exact_ordered_seven_once(adapter, clinical_features) -> None:
    result = adapter.predict(clinical_features)
    assert adapter.preprocessor.transform_columns == list(R5_RAW_FIELDS)
    assert adapter.preprocessor.fit_calls == 0
    assert result.output_kind == "log_partial_hazard"

def test_track_a_rejects_wrong_transformed_order(adapter, clinical_features) -> None:
    adapter.preprocessor.output_names = tuple(reversed(R5_MODEL_FIELDS))
    with pytest.raises(InferenceAdapterError):
        adapter.predict(clinical_features)
```

Test finite scalar, frozen label/disclaimer, nullable `numpy.nan`, and no direct fitter call.

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_inference_track_a.py -q`

Expected: import failure.

- [ ] **Step 3: Implement adapter**

```python
def predict(self, features: Mapping[str, object]) -> PrognosisResult:
    frame = pd.DataFrame([{name: _for_frame(features[name]) for name in self.required_fields}],
                         columns=list(self.required_fields))
    matrix = self._preprocessor.transform(frame)
    if tuple(track_a_feature_names(self._preprocessor)) != self._model_feature_names:
        raise InferenceAdapterError("R5 transformed feature order verification failed")
    return _prognosis_result(self._lineage, _one_finite_value(self._model.predict_risk(matrix), "R5"))
```

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/test_inference_track_a.py tests/test_track_a_training.py tests/test_track_a_integration.py -q`

Expected: PASS.

```powershell
git add src/inference/__init__.py src/inference/track_a.py tests/test_inference_track_a.py
git commit -m "feat(r9): add transform-only Track A inference"
```

### Task 5: Implement exact R6 transform-only adapter

**Files:**
- Create: `src/inference/track_b.py`
- Modify: `src/inference/__init__.py`
- Test: `tests/test_inference_track_b.py`

**Interfaces:**
- Produces `TrackBInferenceAdapter.required_fields: tuple[str, ...]` (exact 75) and `predict(features: Mapping[str, object]) -> PrognosisResult`.

- [ ] **Step 1: Write failing tests**

```python
def test_track_b_uses_raw75_and_verifies_model80(adapter, complete_features) -> None:
    adapter.predict(complete_features)
    assert len(adapter.required_fields) == 75
    assert len(adapter.model_feature_names) == 80
    assert adapter.preprocessor.fit_calls == 0

def test_track_b_uses_persisted_r4d_mutation_transformer(adapter, complete_features) -> None:
    adapter.predict(complete_features)
    assert adapter.preprocessor.mutation_transformer_calls == 1
```

Test wrong 80 order/nonfinite risk error, source mapping unchanged, no direct fitter and no second mutation parser.

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_inference_track_b.py -q`

Expected: import failure.

- [ ] **Step 3: Implement adapter**

```python
def predict(self, features: Mapping[str, object]) -> PrognosisResult:
    frame = _ordered_frame(features, self.required_fields)
    matrix = np.asarray(self._preprocessor.transform(frame), dtype=float)
    if tuple(track_b_feature_names(self._preprocessor)) != self._model_feature_names:
        raise InferenceAdapterError("R6 transformed feature order verification failed")
    return _prognosis_result(self._lineage, _one_finite_value(self._model.predict_risk(matrix), "R6"))
```

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/test_inference_track_b.py tests/test_track_b_preprocessing.py tests/test_track_b_training.py tests/test_track_b_artifacts.py -q`

Expected: PASS.

```powershell
git add src/inference/track_b.py src/inference/__init__.py tests/test_inference_track_b.py
git commit -m "feat(r9): add transform-only Track B inference"
```

### Task 6: Implement exact R7 persisted-pipeline adapter

**Files:**
- Create: `src/inference/track_c.py`
- Modify: `src/inference/__init__.py`
- Test: `tests/test_inference_track_c.py`

**Interfaces:**
- Produces `TrackCInferenceAdapter.required_fields: tuple[str, ...]` (exact 68) and `predict(features: Mapping[str, object]) -> SubtypeClassificationResult`.

- [ ] **Step 1: Write failing tests**

```python
def test_track_c_reorders_incidental_classes(adapter, genomic_features) -> None:
    result = adapter.predict(genomic_features)
    assert result.class_order == FROZEN_SUBTYPE_CLASS_ORDER
    assert sum(result.probabilities) == pytest.approx(1.0, abs=1e-8)

def test_track_c_rejects_nc_nonfinite_or_bad_probability(adapter, genomic_features) -> None:
    adapter.pipeline.predict.return_value = np.array(["NC"])
    with pytest.raises(InferenceAdapterError):
        adapter.predict(genomic_features)
```

Test exact raw68 order, one `predict`, one `predict_proba`, zero external transform/fit, malformed persisted mutation handling.

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_inference_track_c.py -q`

Expected: import failure.

- [ ] **Step 3: Implement adapter**

```python
def predict(self, features: Mapping[str, object]) -> SubtypeClassificationResult:
    frame = _ordered_frame(features, self.required_fields)
    predicted = str(np.asarray(self._pipeline.predict(frame), dtype=object).reshape(-1)[0])
    output = reorder_and_validate_probabilities(
        self._pipeline.predict_proba(frame), self._pipeline.classes_, FROZEN_SUBTYPE_CLASS_ORDER)
    if predicted not in FROZEN_SUBTYPE_CLASS_ORDER or predicted == "NC":
        raise InferenceAdapterError("R7 pipeline emitted an unsupported subtype")
    return SubtypeClassificationResult(self._lineage, predicted, FROZEN_SUBTYPE_CLASS_ORDER,
        tuple(float(value) for value in output.probabilities[0]))
```

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/test_inference_track_c.py tests/test_track_c_models.py tests/test_track_c_artifacts.py tests/test_track_c_finalization.py -q`

Expected: PASS.

```powershell
git add src/inference/track_c.py src/inference/__init__.py tests/test_inference_track_c.py
git commit -m "feat(r9): add persisted Track C inference"
```

### Task 7: Implement AnalysisService validation, readiness, isolation

**Files:**
- Create: `src/services/__init__.py`, `src/services/analysis.py`
- Test: `tests/test_analysis_service.py`

**Interfaces:**
- Produces `AnalysisService.from_canonical_artifacts(repository_root: Path) -> AnalysisService`, `analyze(request: AnalysisRequest) -> AnalysisResponse`, and `allowed_input_fields: tuple[str, ...]`.

- [ ] **Step 1: Write failing service tests**

```python
def test_unknown_field_is_global_and_runs_no_track(service, complete_features) -> None:
    response = service.analyze(AnalysisRequest({**complete_features, "Tumor_Size": 4.0}))
    assert response.request_errors[0].code == "UNKNOWN_FIELD"
    assert service.adapter_call_counts == {AnalysisTrack.TRACK_A: 0, AnalysisTrack.TRACK_B: 0, AnalysisTrack.TRACK_C: 0}

def test_clinical_only_has_independent_readiness(service, clinical_features) -> None:
    response = service.analyze(AnalysisRequest(clinical_features))
    assert [item.state for item in response.outcomes] == [
        TrackReadinessState.READY, TrackReadinessState.MISSING_REQUIRED_FIELDS,
        TrackReadinessState.MISSING_REQUIRED_FIELDS]
```

Test genomic-only/complete/default A-B-C/caller subset, empty/duplicate/unknown tracks, ordered missing, all invalid classes, permitted missing fields, no retry, isolated inference failure, repeat determinism.

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_analysis_service.py -q`

Expected: import failure.

- [ ] **Step 3: Implement service**

```python
@classmethod
def from_canonical_artifacts(cls, repository_root: Path) -> AnalysisService:
    return cls(build_canonical_registry(repository_root))

def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
    errors = self._validate_global_request(request)
    tracks = self._resolve_requested_tracks(request, errors)
    if errors:
        return AnalysisResponse(R9_SCHEMA_VERSION, tracks, (), tuple(errors))
    return AnalysisResponse(R9_SCHEMA_VERSION, tracks,
        tuple(self._evaluate_track(track, request.features) for track in tracks), ())
```

Global exact key validation happens before any track. Per track: unavailable, missing, structural invalid, adapter. Convert unexpected adapter exception only here to safe `INFERENCE_ERROR`; never retry.

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/test_analysis_service.py tests/test_inference_contracts.py tests/test_inference_track_a.py tests/test_inference_track_b.py tests/test_inference_track_c.py -q`

Expected: PASS.

```powershell
git add src/services/__init__.py src/services/analysis.py tests/test_analysis_service.py
git commit -m "feat(r9): orchestrate safe frozen-track analysis"
```

### Task 8: Implement read-only R8 aggregate service

**Files:**
- Create: `src/services/prognostic_features.py`
- Modify: `src/services/__init__.py`, `src/services/analysis.py`
- Test: `tests/test_prognostic_feature_service.py`

**Interfaces:**
- Produces `read_prognostic_feature_analysis(entry: R8AggregateArtifact) -> PrognosticFeatureAnalysisView` and `AnalysisService.get_prognostic_feature_analysis() -> PrognosticFeatureAnalysisOutcome`.

- [ ] **Step 1: Write failing tests**

```python
def test_r8_returns_all_ranked_effects_without_patient_input(service) -> None:
    outcome = service.get_prognostic_feature_analysis()
    assert outcome.error is None and len(outcome.view.effects) == 68
    assert tuple(effect.rank for effect in outcome.view.effects) == tuple(range(1, 69))

def test_bad_r8_returns_safe_outcome_without_retry(service_with_bad_r8) -> None:
    outcome = service_with_bad_r8.get_prognostic_feature_analysis()
    assert outcome.view is None and outcome.error.code == "ARTIFACT_UNAVAILABLE"
    assert service_with_bad_r8.r8_read_count == 0
```

Test R8 corruption leaves patient tracks available, no path/hash/traceback error content, no filter parameter.

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_prognostic_feature_service.py -q`

Expected: import/attribute failure.

- [ ] **Step 3: Implement conversion**

```python
def get_prognostic_feature_analysis(self) -> PrognosticFeatureAnalysisOutcome:
    if not self._registry.r8.available:
        return PrognosticFeatureAnalysisOutcome(None, AggregateAnalysisError(
            "ARTIFACT_UNAVAILABLE", "Aggregate analysis artifact is unavailable"))
    return PrognosticFeatureAnalysisOutcome(read_prognostic_feature_analysis(self._registry.r8), None)
```

Read verified R8 text only; no model load, patient input, filtering, inference, or write.

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/test_prognostic_feature_service.py tests/test_prognostic_feature_audit.py tests/test_r8_canonical_provenance.py -q`

Expected: PASS.

```powershell
git add src/services/prognostic_features.py src/services/__init__.py src/services/analysis.py tests/test_prognostic_feature_service.py
git commit -m "feat(r9): expose aggregate prognostic feature analysis"
```

### Task 9: Prove privacy and framework boundaries

**Files:**
- Create: `tests/test_inference_privacy.py`
- Modify: `tests/test_analysis_service.py`, `tests/test_prognostic_feature_service.py`
- Test: `tests/test_inference_privacy.py`

**Interfaces:**
- Consumes all completed public R9 APIs.
- Produces test-only AST/synthetic evidence; adds no runtime persistence API.

- [ ] **Step 1: Write failing tests**

```python
def test_runtime_has_no_web_training_or_fit_calls() -> None:
    assert scan_runtime_imports_and_calls(Path("src/inference"), Path("src/services")) == []

def test_response_and_workdir_never_contain_synthetic_value(service, complete_features, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    response = service.analyze(AnalysisRequest(complete_features))
    assert "synthetic-secret-value" not in json.dumps(response.to_dict())
    assert list(tmp_path.iterdir()) == []
```

AST scan rejects `streamlit`, `fastapi`, `pydantic`, `src.training`, `fit`, and `fit_transform`. Also prove construction loads once, repeated calls do not reload, and errors are safe.

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_inference_privacy.py -q`

Expected: failure until completed runtime is exercised.

- [ ] **Step 3: Implement only safe test helpers/necessary corrections**

```python
FORBIDDEN_IMPORT_PREFIXES = ("streamlit", "fastapi", "pydantic", "src.training")
FORBIDDEN_CALL_NAMES = {"fit", "fit_transform"}
```

Keep scanners in tests unless Task 10 needs the same internal audit helper. Add no logging/file writing/testing backdoor.

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/test_inference_privacy.py tests/test_analysis_service.py tests/test_prognostic_feature_service.py -q`

Expected: PASS.

```powershell
git add tests/test_inference_privacy.py tests/test_analysis_service.py tests/test_prognostic_feature_service.py
git commit -m "test(r9): verify inference privacy and runtime boundary"
```

### Task 10: Build independent 31-check audit and verifier CLI

**Files:**
- Create: `src/audit/inference_service.py`, `scripts/audit_inference_service.py`, `tests/test_inference_service_audit.py`, `tests/test_r9_canonical_provenance.py`
- Modify: `src/audit/__init__.py`
- Create at final evidence only: `artifacts/audits/r9-inference-service-v1/audit.json`, `artifacts/audits/r9-inference-service-v1/checksums.sha256`

**Interfaces:**
- Produces `InferenceServiceAuditCheck`, `InferenceServiceAuditReport`, `audit_inference_service(repository_root: Path, full_test_suite_summary: str) -> InferenceServiceAuditReport`, `write_inference_service_audit(repository_root: Path, full_test_suite_summary: str) -> InferenceServiceAuditReport`, `verify_inference_service_audit(repository_root: Path) -> InferenceServiceAuditReport`.
- CLI write: `python scripts/audit_inference_service.py --full-test-suite-summary-file <path> --full-test-suite-passed`. CLI read-only: `python scripts/audit_inference_service.py --verify`.

- [ ] **Step 1: Write failing exact audit tests**

```python
def test_audit_has_exactly_31_checks() -> None:
    report = audit_inference_service(canonical_root, "250 passed in 10.00s")
    assert [check.number for check in report.checks] == list(range(1, 32))

def test_any_failed_check_blocks(monkeypatch) -> None:
    monkeypatch.setattr(audit, "_check_no_patient_persistence", lambda *_: False)
    assert audit_inference_service(canonical_root, "250 passed in 10.00s").status == "BLOCKED"
```

Implement and test these exact checks in order: 1 R5 identity; 2 R6 identity; 3 R7 identity; 4 R8 identity/R6 lineage; 5 canonical paths; 6 engineer pickles unused; 7 no fitting/training; 8 exact global 75 proof; 9 R5 raw7; 10 R6 raw75; 11 R7 raw68; 12 R5 transform-only/12 order; 13 R6 transform-only/80 order; 14 R7 persisted pipeline only; 15 output kind/disclaimer; 16 no category/probability/recommendation; 17 frozen R7 class order; 18 finite normalized probabilities; 19 no NC; 20 partial readiness; 21 requested tracks; 22 isolation; 23 no feature echo; 24 no patient persistence; 25 R8 aggregate typed unavailable; 26 framework independent; 27 load once; 28 deterministic; 29 contracts/docs/metadata/behavior agree; 30 full suite pass; 31 R10 absent.

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_inference_service_audit.py -q`

Expected: import failure.

- [ ] **Step 3: Implement evidence and verifier**

```python
R9_AUDIT_BUNDLE = Path("artifacts/audits/r9-inference-service-v1")
def write_inference_service_audit(root: Path, summary: str) -> InferenceServiceAuditReport:
    report = audit_inference_service(root, summary)
    bundle = root / R9_AUDIT_BUNDLE
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "audit.json").write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n")
    _refresh_checksums(bundle)
    return verify_inference_service_audit(root)
```

Writer can exercise synthetic fixtures but persists no values. `--verify` only reads existing audit/checksum evidence, recomputes read-only checks, and never trains/writes/analyzes a patient.

- [ ] **Step 4: Run audit tests and exact verifier**

Run: `python -m pytest tests/test_inference_service_audit.py tests/test_r9_canonical_provenance.py -q`

Expected: PASS; canonical audit assertions may skip only before the first canonical evidence write.

Run: `python scripts/audit_inference_service.py --verify`

Expected: `PASS`, 31 checks, zero writes.

- [ ] **Step 5: Commit**

```powershell
git add src/audit/inference_service.py src/audit/__init__.py scripts/audit_inference_service.py tests/test_inference_service_audit.py tests/test_r9_canonical_provenance.py
git commit -m "feat(r9): add independent inference service audit"
```

### Task 11: Document and run final canonical verification lifecycle

**Files:**
- Modify: `README.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/testing.md`, `tests/test_r9_canonical_provenance.py`
- Create only after audit: R9 `audit.json` and `checksums.sha256` paths above.

**Interfaces:**
- Produces 31/31 PASS canonical evidence, checksum-covered audit JSON, a final no-lifecycle-skip pytest summary, and no frozen-scope changes.

- [ ] **Step 1: Write failing canonical provenance tests**

```python
def test_canonical_r9_audit_has_final_no_lifecycle_skip_summary() -> None:
    if not AUDIT.exists():
        pytest.skip("R9 audit is generated after bootstrap full-suite evidence")
    summary = json.loads(AUDIT.read_text())["full_test_suite_summary"]
    assert re.search(r"\b\d+ passed\b", summary)
    assert "failed" not in summary.lower()
    assert "R9 audit is generated after bootstrap full-suite evidence" not in summary
```

Also test audit file set/checksums and branch-history forbidden-scope diff from frozen base.

- [ ] **Step 2: Focused suite then frozen snapshot**

Run: `python -m pytest tests/test_inference_contracts.py tests/test_inference_registry.py tests/test_inference_track_a.py tests/test_inference_track_b.py tests/test_inference_track_c.py tests/test_analysis_service.py tests/test_prognostic_feature_service.py tests/test_inference_privacy.py tests/test_inference_service_audit.py tests/test_r9_canonical_provenance.py tests/test_track_a_integration.py tests/test_track_b_audit.py tests/test_track_c_audit.py tests/test_prognostic_feature_audit.py -q`

Expected: PASS except the only documented pre-audit skip.

Run:
```powershell
git diff --name-only 1eca09a75deea94e557632063837f2d9abc9683c..HEAD -- data artifacts/models src/training src/modeling
git diff --name-only -- data artifacts/models src/training src/modeling
Get-FileHash artifacts/models/track_a/r5a-track-a-baseline-v1/checksums.sha256 -Algorithm SHA256
Get-FileHash artifacts/models/track_b/r6-track-b-v1/checksums.sha256 -Algorithm SHA256
Get-FileHash artifacts/models/track_c/r7-track-c-v1/checksums.sha256 -Algorithm SHA256
Get-FileHash artifacts/analysis/r8-prognostic-features-v1/checksums.sha256 -Algorithm SHA256
```

Expected: prohibited scope lists empty; retain hashes.

- [ ] **Step 3: Bootstrap, audit, then final suite**

Run:
```powershell
python -c "from pathlib import Path; from src.services.analysis import AnalysisService; print(len(AnalysisService.from_canonical_artifacts(Path('.')).allowed_input_fields))"
python -m pytest -q | Tee-Object -FilePath $env:TEMP\cognivex-r9-bootstrap-pytest.txt
python scripts/audit_inference_service.py --full-test-suite-summary-file $env:TEMP\cognivex-r9-bootstrap-pytest.txt --full-test-suite-passed
python -m pytest tests/test_r9_canonical_provenance.py -q
python -m pytest -q | Tee-Object -FilePath $env:TEMP\cognivex-r9-final-pytest.txt
```

Expected: smoke prints `75` without a record; bootstrap has zero failures and only pre-audit skip may exist; initial audit writes only two R9 evidence files; final suite has zero failures and zero R9 missing-audit lifecycle skips.

- [ ] **Step 4: Finalize, verify, and inspect scope**

Run:
```powershell
python scripts/audit_inference_service.py --full-test-suite-summary-file $env:TEMP\cognivex-r9-final-pytest.txt --full-test-suite-passed
python scripts/audit_inference_service.py --verify
python -m pytest tests/test_r9_canonical_provenance.py -q
python -m compileall -q app.py src scripts tests
python -m pip check
git diff --check
git diff --name-only 1eca09a75deea94e557632063837f2d9abc9683c..HEAD -- data artifacts/models src/training src/modeling
git diff --name-only -- data artifacts/models src/training src/modeling
git diff --name-only 1eca09a75deea94e557632063837f2d9abc9683c..HEAD
git status --short
```

Expected: final audit 31/31, read-only verifier PASS, provenance no lifecycle skip, compile/pip/diff PASS, prohibited scopes empty, only known untracked `ai_handoff_data/` remains.

- [ ] **Step 5: Commit final docs/evidence and rerun branch scope**

```powershell
git add README.md CHANGELOG.md docs/architecture.md docs/testing.md tests/test_r9_canonical_provenance.py artifacts/audits/r9-inference-service-v1/audit.json artifacts/audits/r9-inference-service-v1/checksums.sha256
git commit -m "docs(r9): record analysis service verification evidence"
git diff --name-only 1eca09a75deea94e557632063837f2d9abc9683c..HEAD -- data artifacts/models src/training src/modeling
git status --short
```

Expected: no prohibited branch-history scope and no untracked change except known handoff material.

## Plan Self-Review

- [x] Tasks 1–11 cover contracts, trust-gate phases, exact namespace, three adapters, service semantics, aggregate R8, privacy, all 31 audit checks, docs, and final lineage evidence.
- [x] Every public type/method used by later tasks is named in the producing task.
- [x] Review Focus cases map to test tasks.
- [x] Final audit check 30 uses the second full suite after audit creation; bootstrap evidence is never final.
- [x] Final audit/checksum verification has an exact read-only command.
- [x] Frozen scope checks compare both committed branch history and working tree to the stated base.
- [x] No R10/R11/R12, model fit/refit/tuning, UI/API, patient persistence, or historical engineer model is planned.
- [x] No unfinished marker or vague verification-command placeholder is present.

## Execution Handoff

Wait for human approval before execution. The approved method is native single-session execution with subagents OFF. Then use `superpowers:executing-plans` to execute Tasks 1–11 sequentially and stop at the R9 gate; do not start R10.
