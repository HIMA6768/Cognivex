# R9 Analysis / Inference Service and Orchestration Design

## 1. Purpose

R9 defines the framework-independent runtime boundary between one in-memory
analysis request and the frozen Cognivex R5, R6, R7, and R8 evidence. It is
the service future R10 presentation code will call. It is not a second
modelling stage, a clinical decision system, an API server, or a Streamlit
feature.

Given one record of supplied raw fields, the service will determine which
frozen patient-specific tracks are ready, run only those tracks using their
persisted train-fitted artifacts, and return typed, safe, non-clinical
results. It separately exposes the global R8 feature-analysis bundle without
combining it with an individual record.

Success means a future caller can use one stable Python service without
knowing pickle paths, preprocessing details, model-specific APIs, or R8 file
formats. R9 persists no request, prediction, probability, risk score, or
patient-level artifact.

## 2. Roadmap Boundary

R9 is **analysis/inference service plus orchestration** only.

It will:

- verify and trusted-load repository-owned R5, R6, and R7 artifacts;
- validate a one-record analysis request against frozen field contracts;
- calculate readiness independently for R5, R6, and R7;
- run transform-only preprocessing and frozen inference only;
- normalize outputs and failures into typed, serializable contracts;
- expose R8 as read-only aggregate evidence; and
- provide deterministic, privacy-preserving behavior for future R10.

It will not fit, refit, tune, select, calibrate, or otherwise change a model.
It will not modify any frozen artifact or feature contract. It will not add a
Streamlit result page, a web API, deployment configuration, R10, R11, or R12.

## 3. Immutable Authorities and Repository Findings

The following canonical paths are the only R9 runtime authorities. Artifact
paths are service configuration, never request input.

| Authority | Canonical path | Observed persisted capability |
|---|---|---|
| R5 Track A | `artifacts/models/track_a/r5a-track-a-baseline-v1/` | `preprocessor.pkl`, `cox_model.pkl`, `experiment.json`, metrics, coefficients, PH diagnostics, and checksums |
| R6 Track B | `artifacts/models/track_b/r6-track-b-v1/` | `preprocessor.pkl`, `cox_model.pkl`, feature contract, metadata, metrics, audit, and checksums |
| R7 Track C | `artifacts/models/track_c/r7-track-c-v1/` | self-contained `pipeline.pkl`, feature contract, metadata, metrics, report, audit, and checksums |
| R8 aggregate analysis | `artifacts/analysis/r8-prognostic-features-v1/` | `feature_effects.csv`, `summary.json`, `metadata.json`, `report.md`, audit, and checksums |

R5's persisted experiment configuration records the seven raw clinical
predictors through the canonical preprocessing schema and the 12 derived
model features:

1. `age_at_diagnosis`
2. `tumor_size`
3. `lymph_nodes_examined_positive`
4. `tumor_stage_2`
5. `tumor_stage_3`
6. `tumor_stage_4`
7. `tumor_stage_Unknown`
8. `er_status_measured_by_ihc_Positive`
9. `pr_status_Positive`
10. `her2_status_Positive`
11. `tumor_size_was_missing`
12. `er_status_measured_by_ihc_was_missing`

The seven raw clinical fields remain the canonical R4 schema order:
`age_at_diagnosis`, `tumor_size`, `tumor_stage`,
`lymph_nodes_examined_positive`, `er_status_measured_by_ihc`, `pr_status`,
and `her2_status`.

R6 persists a 75-raw-field contract: the same seven clinical fields, 50
selected expression fields, and 18 selected mutation annotation fields. Its
fitted preprocessor produces exactly 80 named fields. R6 metadata records
`PenalizedCoxPHAdapter`, `CoxPHFitter`, Breslow baseline estimation,
`penalizer=0.05`, and `l1_ratio=0.5`.

R7 persists a self-contained scikit-learn `Pipeline` with exactly 68 raw
genomic fields: 50 expression fields followed by 18 selected mutation
annotation fields. The persisted selected model is `random_forest`; its
pipeline exposes `predict` and `predict_proba`, and its persisted class order
is exactly `Basal`, `Her2`, `LumA`, `LumB`, `Normal`, `claudin-low`.

R8 is not an inference model. Its canonical table retains 68 R6 genomic
coefficient records, while excluding the 12 encoded clinical R6 outputs. The
existing `verify_prognostic_feature_bundle(...)` API is a read-only semantic
recomputation verifier for the R8 bundle and frozen R6 source. It is suitable
for audit and verification, not a patient-analysis mechanism.

The current `app.py` and `src/ui/` shell are Streamlit-only presentation
code. Survival Analysis, Subtype Classification, Gene Insights, and Model
Comparison pages are still pending-state pages and no `src/inference/` or
`src/services/` runtime boundary currently exists. R9 leaves all UI files
unchanged.

## 4. Frozen Prediction APIs and Output Semantics

The R5 `LifelinesCoxPHAdapter.predict_risk(...)` and R6
`PenalizedCoxPHAdapter.predict_risk(...)` methods both invoke lifelines
`predict_log_partial_hazard(...)` and return finite log partial-hazard values.
Their internal lifelines fitters also technically expose partial hazard,
survival-function, and cumulative-hazard methods, but those are not frozen
project adapter outputs or validated Cognivex patient-facing measures.

R9 will expose **only** the frozen public adapter quantity:

`log_partial_hazard`

The neutral display label is **Model log relative hazard score**. The required
interpretation text is:

> Model-relative log partial hazard; not an absolute survival probability,
> mortality probability, risk category, treatment recommendation, or
> clinical prognosis.

R9 will not exponentiate this value to invent a new public partial-hazard
contract. It will not expose survival curves, cumulative hazards, five-year
survival percentages, recurrence probabilities, or low/medium/high labels.

R5 and R6 may both return this output when their own required fields are
available. R9 will not compare them for an individual, say genomics improved
a person's prognosis, or infer that one model is more accurate for a person.

## 5. Orchestration Approaches Considered

### Approach A — Explicit frozen adapters plus `AnalysisService` (selected)

Each track owns its canonical bundle, verification, required raw fields, and
the smallest possible transform-and-predict path. An explicit service owns
one immutable registry of verified adapters and coordinates request
validation, readiness, and failure isolation.

This has the strongest trust boundary, preserves exact field ordering, makes
track-level tests direct, and gives R10 one small integration interface. It
does not need dynamic loading or a framework dependency.

### Approach B — One monolithic `analyze()` function

This would initially require fewer files but would mix checksum verification,
pickle loading, request validation, three incompatible inference APIs,
readiness, R8 reading, result formatting, and error policy. It would make
failure isolation and future R10 use harder to test. It is not selected.

### Approach C — Generic plugin/model discovery registry

This would introduce dynamic artifact discovery and plugin trust complexity
for three fixed frozen tracks. It weakens the canonical-path policy and adds
no present R9 value. It is not selected.

## 6. Selected Architecture

R9 will use explicit composition:

```text
AnalysisRequest
  -> AnalysisService.analyze()
      -> request-level key / requested-track validation
      -> R5 adapter readiness -> transform-only -> frozen Cox adapter
      -> R6 adapter readiness -> transform-only -> frozen Cox adapter
      -> R7 adapter readiness -> frozen pipeline
  -> AnalysisResponse

AnalysisService.get_prognostic_feature_analysis()
  -> verified R8 aggregate reader
  -> PrognosticFeatureAnalysisOutcome
```

Service construction verifies and trusted-loads canonical artifacts once. The
service holds immutable adapter handles for its lifetime. It has no mutable
global singleton, no Streamlit cache, and no disk write path. R10 may later
cache one constructed service using its own resource mechanism outside R9.

## 7. Proposed Component Boundaries

The implementation will use the following focused modules, subject only to
equivalent existing repository conventions discovered during implementation:

| Module | Responsibility |
|---|---|
| `src/contracts/inference.py` | Framework-independent request, result, readiness, error, lineage, and R8-view contracts |
| `src/artifacts/inference_registry.py` | Canonical-path enforcement, checksum and metadata verification, trusted local loads, immutable runtime registry |
| `src/inference/track_a.py` | R5 exact-seven-field frame creation, transform-only preprocessing, log partial-hazard result |
| `src/inference/track_b.py` | R6 exact-75-field frame creation, transform-only preprocessing, log partial-hazard result |
| `src/inference/track_c.py` | R7 exact-68-field frame creation, pipeline prediction/probability ordering, subtype result |
| `src/services/analysis.py` | Request validation, requested-track behavior, readiness, track isolation, aggregate response |
| `src/services/prognostic_features.py` | R8 aggregate-only reader and safe view conversion |

No track adapter will import Streamlit, FastAPI, UI code, or a web request
type. No adapter will call `fit`, `fit_transform`, training code, candidate
selection, or a historical engineer model.

## 8. Artifact Initialization and Trust Boundary

`AnalysisService.from_canonical_artifacts(repository_root: Path)` will be the
only production construction path. It will resolve repository-relative,
hard-coded canonical bundle paths and reject any noncanonical location.

Artifact verification has two strict phases. No pickle deserialization may
occur until every applicable pre-load gate has passed. Tests will use a
loader spy to prove that a failed pre-load checksum, metadata, or contract
gate produces zero `load_trusted_pickle(..., trusted=True)` calls.

### Pre-load verification

Pre-load verification uses only repository-relative paths and text/binary
bytes that can be inspected without unpickling:

1. Require the expected canonical repository-relative bundle path.
2. Require the exact expected file set.
3. Verify each checksum manifest against every declared bundle file.
4. Validate metadata and experiment identity.
5. Validate persisted raw feature contracts: R5's canonical
   `PreprocessingSchema` plus persisted `experiment.json` configuration,
   R6's `feature_contract.json`, and R7's `feature_contract.json`.
6. Validate persisted class order/configuration where text artifacts provide
   it: R5's 12 configured output names and Cox identity, R6's 75/80 feature
   counts and frozen configuration, and R7's 68-feature and six-class
   contract.
7. Validate frozen lineage/source hashes, including R6 tracked-state checks
   and R8-to-R6 lineage equality.
8. For R8, verify the canonical aggregate bundle checksum manifest, metadata,
   summary, and source-R6 identity. The existing full semantic R8
   recomputation verifier remains the read-only audit/verification authority;
   R9 does not load R6 a second time merely to read the aggregate table.

Only after all applicable pre-load checks pass may
`load_trusted_pickle(..., trusted=True)` be called.

### Post-load validation

Post-load validation examines trusted objects already admitted through the
pre-load gate:

- **R5:** require trusted preprocessor and `LifelinesCoxPHAdapter` object
  types, fitted state, exact seven raw clinical fields, exact ordered
  12-feature transformed output, and the expected Cox adapter/fitter identity.
- **R6:** reuse `verify_and_load_track_b_source(...)`. Its own pre-load
  checksum and frozen-state gates run before its trusted loads; after loading,
  require the expected `PenalizedCoxPHAdapter`/`CoxPHFitter` identity, fitted
  state, exact 80-feature order, and frozen configuration.
- **R7:** require a trusted fitted scikit-learn `Pipeline`, exact verified
  68-field raw contract, expected estimator identity, estimator class order,
  and the frozen six-class taxonomy.

Historical engineer pickles and arbitrary caller-provided paths are always
rejected.

### Service-construction failure isolation

`AnalysisService.from_canonical_artifacts(repository_root)` first validates
the repository root, canonical runtime configuration, and global input
namespace. Those are the only classes of failure that prevent service
construction entirely.

After the repository-level gate, R5, R6, R7, and R8 initialize independently:

- a successfully verified R5/R6/R7 bundle creates one immutable available
  adapter entry;
- a verification or trusted-load failure creates an immutable unavailable
  track entry containing only safe failure code/message metadata, not a path,
  traceback, pickle detail, or exception text;
- a successfully verified R8 bundle creates an immutable aggregate reader;
  an R8 verification failure creates only an unavailable aggregate-reader
  entry.

The service therefore still constructs if one or more track artifacts are
unavailable. During `analyze()`, an attempted unavailable R5/R6/R7 track
returns `ARTIFACT_UNAVAILABLE` without a load or inference retry; independently
verified ready tracks continue normally. If R8 is unavailable,
`get_prognostic_feature_analysis()` alone returns its typed safe unavailable
outcome;
patient-track analysis remains usable. Artifact initialization happens only at
service construction.

## 9. Request and Global Input Contracts

R9 will use one flat, exact-name mapping rather than clinical/genomic nested
records:

```python
@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    features: Mapping[str, str | int | float | None]
    requested_tracks: tuple[AnalysisTrack, ...] | None = None
```

A flat mapping is selected because R5 clinical fields are a subset of R6,
while R6 and R7 share the same frozen genomic contract. Nested records would
force a second merge/duplicate-key policy without improving the exact
column-order boundary. Mapping values are never echoed in a response.

`AnalysisTrack` will be an ordered enum:

```python
class AnalysisTrack(StrEnum):
    TRACK_A = "track_a"
    TRACK_B = "track_b"
    TRACK_C = "track_c"
```

The canonical global input namespace is established during service
construction, after pre-load contract verification and before `analyze()` is
usable. It must contain exactly 75 distinct fields and has two accepted proof
routes:

- **Route A:** a successfully pre-load-verified R6 raw contract establishes
  the exact 75 ordered fields directly.
- **Route B:** a successfully pre-load-verified R5 seven-clinical-field
  contract plus a successfully pre-load-verified R7 68-genomic-field contract
  establish the same 75-field union.

When both proof routes are available, their ordered union must agree exactly.
Once established, post-load adapter failure cannot alter this namespace: a
post-load R5 failure with verified R6, a post-load R6 failure with verified
R5/R7, or a post-load R7 failure with verified R6 still permits service
construction with the original 75 fields.

If neither route can establish the canonical namespace, including when both
genomic persisted contracts fail their pre-load contract gates, service
construction fails with a repository-level
`GLOBAL_INPUT_CONTRACT_UNAVAILABLE` failure. This is not an individual-track
inference failure because the service cannot safely determine which request
keys are valid globally. The service does not dynamically discover features
from dataframe dtypes, prefixes, or caller keys.

Keys are exact, case-sensitive frozen names; R9 applies no key normalization.
An unknown key is a global `UNKNOWN_FIELD` request error and no requested
track executes. This deliberately catches API/UI typos. A mapping cannot
represent duplicate keys; a future JSON or UI adapter must reject duplicate
keys before constructing `AnalysisRequest`.

## 10. Requested-Track Semantics

`requested_tracks=None` means evaluate all three patient-specific tracks in
the fixed order A, B, C. Each receives its independent readiness outcome.

If `requested_tracks` is supplied, R9 evaluates exactly the supplied unique
tracks in the caller's order and does not silently fall back to another
model. The following are request errors and execute no track:

- `()` — `EMPTY_REQUESTED_TRACKS`
- a duplicate enum member — `DUPLICATE_REQUESTED_TRACK`
- an unknown/non-enum name — `UNKNOWN_REQUESTED_TRACK`

R8 is intentionally not a requested patient track. Callers obtain it only
through `get_prognostic_feature_analysis()`.

## 11. Track Field Requirements and Readiness

Each adapter exposes its ordered `required_fields` directly from its verified
frozen contract:

| Track | Required raw fields | Result when complete |
|---|---:|---|
| R5 / Track A | 7 clinical | Cox model log partial hazard |
| R6 / Track B | 75: 7 clinical + 50 expression + 18 mutation annotations | Cox model log partial hazard |
| R7 / Track C | 68: 50 expression + 18 mutation annotations | subtype label plus ordered probabilities |
| R8 | 0 | separate aggregate analysis view |

Each requested track produces a `TrackOutcome` with one of these states:

- `READY` — required fields are present and valid; inference completed and
  `result` is populated.
- `MISSING_REQUIRED_FIELDS` — one or more required exact field names are
  absent; `missing_fields` is an ordered tuple and no inference occurs.
- `INVALID_INPUT` — a supplied required field is structurally invalid for
  that adapter; `invalid_fields` contains names only, never values.
- `ARTIFACT_UNAVAILABLE` — canonical trust, checksum, metadata, or load
  validation failed for that adapter; no inference occurs.
- `INFERENCE_ERROR` — a verified adapter raised unexpectedly after valid
  input; the safe error message contains no traceback or feature value.

Readiness is independent where safe. For example, clinical-only input yields
R5 `READY`, R6 `MISSING_REQUIRED_FIELDS`, and R7
`MISSING_REQUIRED_FIELDS`; genomic-only input yields R7 `READY`, R5
`MISSING_REQUIRED_FIELDS`, and R6 `MISSING_REQUIRED_FIELDS`; complete input
allows all three. A track failure never suppresses another ready track unless
there is a global request error.

## 12. Request-Level and Per-Track Value Validation

R9 validates only structural safety and ambiguity. Frozen preprocessors remain
authoritative for fitted imputation, encoding, scaling, and mutation
transformation. R9 never makes new fitted statistics or fills a field for
another track.

Per relevant track, validation is exact:

- expression and numeric clinical fields require a finite `int` or `float`;
  booleans are rejected even though Python treats them as integers;
- `NaN` and either infinity are rejected for required numeric/expression
  fields;
- `tumor_size` and `er_status_measured_by_ihc` alone may be supplied as
  `None` or IEEE `NaN`, matching the frozen preprocessor's approved missing
  policy; when materializing the one-row dataframe, `None` is represented as
  `numpy.nan`, the fitted imputer's recognized missing marker. This is value
  representation only, not imputation or a newly fitted statistic;
- categorical clinical values must be a nonblank exact member of the frozen
  canonical category declaration, except the approved nullable ER-IHC
  missing value above; this prevents `OneHotEncoder(handle_unknown="ignore")`
  from silently treating an unsupported category as all zero;
- blank strings are invalid, not implicit missing values;
- selected mutation annotations are passed to the existing R4D
  `classify_mutation_annotation` semantics through the persisted
  transformer; missing, blank, boolean, non-finite, and malformed values
  produce a track-level `INVALID_INPUT`;
- source mutation strings are not altered or rewritten by R9.

Validation creates exact ordered one-row dataframes only after an adapter is
ready. Each dataframe contains only that adapter's approved raw fields; no
model receives the global mapping or unrelated extra fields.

## 13. Result and Error Contracts

All contracts are frozen dataclasses/enums in `src/contracts/inference.py`,
independent of Streamlit, FastAPI, pandas widgets, and ORM types. Every
contract provides `to_dict()` using JSON-safe primitives.

```python
class TrackReadinessState(StrEnum):
    READY = "ready"
    MISSING_REQUIRED_FIELDS = "missing_required_fields"
    INVALID_INPUT = "invalid_input"
    ARTIFACT_UNAVAILABLE = "artifact_unavailable"
    INFERENCE_ERROR = "inference_error"

@dataclass(frozen=True, slots=True)
class ResultLineage:
    track: AnalysisTrack
    experiment_id: str
    schema_version: str
    contract_artifact_sha256: str

@dataclass(frozen=True, slots=True)
class PrognosisResult:
    lineage: ResultLineage
    output_kind: Literal["log_partial_hazard"]
    output_label: str
    value: float
    interpretation: str

@dataclass(frozen=True, slots=True)
class SubtypeClassificationResult:
    lineage: ResultLineage
    predicted_class: str
    class_order: tuple[str, ...]
    probabilities: tuple[float, ...]

@dataclass(frozen=True, slots=True)
class TrackError:
    code: str
    message: str
    track: AnalysisTrack
    missing_fields: tuple[str, ...] = ()
    invalid_fields: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class RequestError:
    code: str
    message: str
    fields: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class AggregateAnalysisError:
    code: str
    message: str

@dataclass(frozen=True, slots=True)
class PrognosticFeatureAnalysisOutcome:
    view: PrognosticFeatureAnalysisView | None
    error: AggregateAnalysisError | None

@dataclass(frozen=True, slots=True)
class TrackOutcome:
    track: AnalysisTrack
    state: TrackReadinessState
    result: PrognosisResult | SubtypeClassificationResult | None
    error: TrackError | None

@dataclass(frozen=True, slots=True)
class AnalysisResponse:
    schema_version: str
    requested_tracks: tuple[AnalysisTrack, ...]
    outcomes: tuple[TrackOutcome, ...]
    request_errors: tuple[RequestError, ...]
```

`RequestError` is framework independent and contains field names only when
useful. `RequestError`, `TrackError`, and every nested result must never
contain feature values, filesystem paths, raw tracebacks, pickle internals, or
deserialization exception text.

`TrackOutcome` enforces these invariants in `__post_init__`:

- when `state is TrackReadinessState.READY`, `result` must be populated and
  `error` must be `None`;
- when `state` is `MISSING_REQUIRED_FIELDS`, `INVALID_INPUT`,
  `ARTIFACT_UNAVAILABLE`, or `INFERENCE_ERROR`, `result` must be `None` and
  `error` must be populated;
- contradictory state/result/error combinations raise `ValueError` during
  contract construction.

`PrognosticFeatureAnalysisOutcome` enforces parallel aggregate-access
invariants in `__post_init__`:

- when R8 is available, `view` is populated and `error` is `None`;
- when R8 is unavailable, `view` is `None` and `error` is populated;
- contradictory view/error combinations raise `ValueError`.

`ResultLineage.contract_artifact_sha256` is the checksum for the persisted
contract source: R5 `experiment.json`, R6 `feature_contract.json`, and R7
`feature_contract.json`. It provides traceability without exposing a local
filesystem path. Developer-only registry diagnostics may expose canonical
artifact hashes; normal response results will not.

`PrognosisResult.value` must be finite. `SubtypeClassificationResult` must
contain exactly the frozen six classes and six finite probabilities in that
order; their sum must be within `1e-8` of one. There is no duplicate
"confidence" field, no `NC` prediction class, and no patient interpretation.

## 14. R5 and R6 Adapter Rules

`TrackAInferenceAdapter` and `TrackBInferenceAdapter` will:

1. select exactly the verified raw field order;
2. build one in-memory dataframe;
3. call only the persisted preprocessor's `transform(...)` method;
4. verify transformed order equals the R5 12-feature or R6 80-feature
   persisted contract;
5. call only the persisted model's `predict_risk(...)` method; and
6. return the one finite `log_partial_hazard` scalar in `PrognosisResult`.

Neither adapter calls `fit`, `fit_transform`, `predict_survival_function`,
`predict_cumulative_hazard`, direct fitter methods, training code, or model
selection code. No survival probability or risk category is constructed.

## 15. R7 Adapter Rules

`TrackCInferenceAdapter` will:

1. select exactly the verified 68 raw field order;
2. build one in-memory dataframe;
3. call the persisted pipeline's `predict(...)` once;
4. call `predict_proba(...)` once;
5. use the existing probability reordering/validation utility to align
   estimator classes to the frozen six-class order; and
6. reject a nonfinite, nonnormalized, wrong-length, or `NC` result as
   `INFERENCE_ERROR`.

The adapter does not separately fit/transform a new preprocessor because the
persisted R7 pipeline is self-contained. It does not use clinical fields.

## 16. R8 Aggregate Analysis Access

The public aggregate-access method is exactly:

```python
def get_prognostic_feature_analysis(
    self,
) -> PrognosticFeatureAnalysisOutcome: ...
```

When R8 is verified, the returned outcome contains a separate
`PrognosticFeatureAnalysisView` with `error=None`. The view contains:

- R8 analysis ID, schema version, source R6 lineage, and coefficient policy;
- aggregate summary counts;
- all 68 ordered `PrognosticFeatureEffectView` records; and
- neutral aggregate interpretation text.

When R8 initialization failed, the returned outcome contains `view=None` and
one safe `AggregateAnalysisError` with the stable code
`ARTIFACT_UNAVAILABLE`. It does not retry loading and never exposes paths,
tracebacks, checksum values, deserialization details, or a normal-flow
exception to a future R10 caller. R8 unavailability never prevents
independently valid R5/R6/R7 inference.

It takes no patient features. The initial interface has no `active_only`
filter; R10 can filter the returned in-memory records for display without
rewriting canonical evidence. R9 preserves canonical rank order and never
joins a record's values to R8 effects. It does not create pseudo-SHAP values,
patient-specific importance, biological explanations, or causal claims.

## 17. Privacy, Statelessness, and Framework Boundary

R9 is in-memory and stateless for patient analysis. It writes no request,
patient ID, feature values, outcomes, probabilities, risk scores, prediction
history, or payload-bearing log. R9 adds no runtime logging layer in this
increment.

Responses never echo `AnalysisRequest.features`. Error messages identify
field names and safe error codes only; they never contain values, paths,
tracebacks, raw pickle details, or model internals.

R9 modules must not import `streamlit`, `fastapi`, `pydantic` web models, or
web-framework request/response types. The service remains usable directly in
Python tests, future R10, or a future separately approved wrapper.

## 18. Performance and Determinism

The service is single-record interactive inference only. It loads verified
artifacts once per `AnalysisService` instance and retains immutable handles.
There is no global mutable singleton, multiprocessing, async orchestration,
GPU requirement, batch server, queue, or model server.

For the same exact `AnalysisRequest`, canonical artifacts, and service
instance configuration, response ordering, readiness, output values,
probability order, and lineage are deterministic. R9's result contract has
no timestamp or random value. Artifact verification happens at construction,
not on every field edit.

## 19. Testing Strategy

Future R9 implementation must use synthetic, nonclinical one-record fixtures
that satisfy frozen raw contracts. Tests must never copy a real METABRIC row
or persist a patient-like prediction artifact.

Focused tests must cover:

- canonical-path-only construction, checksum mismatch isolation, historical
  engineer-pickle rejection, pre-load loader-spy fail-fast behavior, artifact
  load-once behavior, and no fitting;
- R6-alone and R5-plus-R7 proof routes establishing the same exact 75-field
  union when healthy; post-load adapter failure leaving that established union
  unchanged; failure of both proof routes blocking construction; and no
  dtype/prefix/caller-key feature discovery;
- corrupt R5 preserving independently verified R6/R7 service availability;
  corrupt R6 preserving independently verified R5/R7 availability; corrupt
  R7 preserving independently verified R5/R6 availability; and corrupt R8
  preserving patient-track analysis;
- unavailable requested tracks returning `ARTIFACT_UNAVAILABLE` without a
  load or inference retry during `analyze()`, and artifact initialization
  occurring only during service construction;
- exact verified R5/R6/R7 identities and R8 lineage;
- allowed-field union derived from frozen contracts, unknown-key rejection,
  and no dynamic discovery;
- clinical-only, genomic-only, and complete-input readiness behavior;
- omitted, subset, empty, duplicate, and unknown requested-track handling;
- exact R5 seven-field / 12-transformed-field transform-only prediction;
- exact R6 75-field / 80-transformed-field transform-only prediction;
- exact R7 68-field pipeline prediction, probability ordering, finite values,
  normalization, and no NC output;
- boolean/nonnumeric/nonfinite/blank/unsupported-category/malformed-mutation
  failure handling, including permitted frozen nullable clinical fields;
- track failure isolation and artifact failure closed behavior;
- no input echo, no payload-bearing error, no patient analysis file write;
- R8 full 68-effect read-only access without patient input;
- healthy and unavailable `PrognosticFeatureAnalysisOutcome` values, their
  view/error invariants, stable unavailable code, and no normal-flow exception
  or retry for an unavailable R8 reader;
- no Streamlit/FastAPI imports; and
- repeated valid input producing identical response contracts.

## 20. Independent R9 Audit Design

R9 will later implement one independent **31-check** audit. Every check must
be explicit PASS/FAIL; one failure blocks the R9 gate.

1. R5 canonical identity is verified.
2. R6 canonical identity is verified.
3. R7 canonical identity is verified.
4. R8 canonical identity and R6 lineage are verified.
5. Only canonical repository artifact paths are accepted.
6. Historical engineer pickles are unused.
7. R9 contains no fitting/training imports or `fit`/`fit_transform` calls.
8. The exact 75-field global namespace is derived through a frozen-contract proof route.
9. R5 required fields are exactly the frozen seven clinical fields.
10. R6 required fields are exactly the frozen 75 fields.
11. R7 required fields are exactly the frozen 68 fields.
12. R5 preprocessing is transform-only and its 12-feature order verifies.
13. R6 preprocessing is transform-only and its 80-feature order verifies.
14. R7 uses only persisted-pipeline inference.
15. R5/R6 output kind is exactly `log_partial_hazard` with the frozen disclaimer.
16. No risk category, absolute survival probability, or recommendation is created.
17. R7 class order is exactly the six frozen classes.
18. R7 probabilities are finite and normalized in that order.
19. R7 cannot emit NC.
20. Per-track readiness is correct for partial inputs.
21. Requested-track semantics are exact.
22. Safe track failure isolation is correct.
23. Responses and errors do not echo feature values.
24. No patient-level request/result data is persisted.
25. R8 is global, aggregate-only, read-only, and returns a typed unavailable outcome.
26. Runtime modules are framework independent.
27. A service instance loads each required artifact once.
28. Repeated frozen inference is deterministic.
29. Contracts, documentation, metadata, and service behavior agree.
30. The complete repository test suite passes.
31. R10 has not started.

## 21. Scientific and Interpretation Boundary

R9 exposes only frozen model mechanics with clear neutral labels. It is not a
diagnostic, treatment, or clinical decision system. R5/R6 values are relative
model scores, not absolute patient outcomes. R7 probabilities are model class
probabilities, not diagnostic confidence or biological explanation. R8 is an
aggregate model-coefficient resource, not individual explanation, causality,
mechanism, biomarker validation, or treatment relevance.

## 22. Reproducibility and Explicit Out of Scope

R9 will retain lineage hashes and immutable experiment identifiers in every
result, while keeping filesystem locations out of ordinary caller results.
Construction uses repository-relative canonical paths and checksum-gated
trusted local loading. The service will have no canonical patient inference
bundle; code, synthetic tests, and the future R9 audit are sufficient evidence.

Out of scope: UI changes, Streamlit integration, API/deployment work, model
training/retraining, model tuning, feature selection, calibration, threshold
policy, survival-probability presentation, Track D modelling, R8 feature
interpretation, patient persistence, monitoring, R10, R11, and R12.
