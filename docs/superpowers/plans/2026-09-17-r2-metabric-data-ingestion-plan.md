# R2 METABRIC Data Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the corrected METABRIC handoff as a repository-owned, validated, aggregate-only data source for the R2 Data / Cohort workspace.

**Architecture:** A framework-independent `src/data` service resolves repository-relative paths, verifies checksums, validates metadata/schema/matching, and returns typed aggregate-only results. Streamlit holds that result in session state and never stores or renders patient rows.

**Tech Stack:** Python 3.11+, standard-library `csv`/`json`/`hashlib`, Streamlit 1.39+, pytest, optional pandas/scikit-learn data-preparation extra.

**Spec:** `docs/superpowers/specs/2026-09-17-r2-metabric-data-ingestion-design.md`

## Global Constraints

- Use only `C:\Users\sajal\Downloads\Breast_Cancer_Data_Handoff_Corrected.zip`; ignore `ai_handoff_data/`, `(1)` variants, and older uploads.
- Create exactly one repository-owned canonical package under `data/metabric/`; do not stage `ai_handoff_data/`.
- Raw data remains unchanged; the active application reads only the prepared CSV.
- Preserve supplied provenance JSON and checksum file byte-for-byte; document direct verified provenance separately.
- Do not add modeling preprocessing, fitting, predictions, gene importance, or clinical-decision behavior.
- Use current parent session only; no subagents.

---

### Task 1: Install and verify the canonical handoff

**Files:** Create the two CSVs at `data/metabric/raw/` and `data/metabric/prepared/`; all listed JSON/CSV metadata plus `SHA256SUMS.txt` at `data/metabric/metadata/`; `data/metabric/README.md`; `scripts/prepare_data.py`; `docs/data_strategy.md`; and `docs/data_provenance_resolution.md`.

**Interfaces:** Original SHA names map to their required repository locations, including `HANDOFF_README.md` to `data/metabric/README.md`, `data_strategy.md` to `docs/data_strategy.md`, and `prepare_data.py` to `scripts/prepare_data.py`.

- [ ] **Step 1:** Verify every ZIP entry named in `SHA256SUMS.txt` through a streaming SHA-256 read before copying.
- [ ] **Step 2:** Copy only approved entries directly to canonical paths; do not create a second repository extraction directory.
- [ ] **Step 3:** Write `docs/data_provenance_resolution.md` with the user-verified Kaggle URL, owner, Version 1, license wording, and cBioPortal origin; state why historical provenance stays unchanged.
- [ ] **Step 4:** Measure raw and prepared byte/MiB sizes before staging. Stop instead of introducing Git LFS if either approaches 100 MiB.
- [ ] **Step 5:** Commit the data checkpoint: `git add data/metabric scripts/prepare_data.py docs/data_strategy.md docs/data_provenance_resolution.md` then `git commit -m "data: add canonical METABRIC R2 handoff"`.

### Task 2: Define and test typed ingestion contracts and paths

**Files:** Create `src/data/__init__.py`, `src/data/metabric.py`, and `tests/test_metabric_ingestion.py`; modify `src/contracts/analysis.py` and `src/contracts/__init__.py`.

**Interfaces:** `MetabricPaths.from_repository_root(root: Path | None = None) -> MetabricPaths`; `load_metabric(paths: MetabricPaths | None = None) -> MetabricIngestionResult`.

- [ ] **Step 1:** Write a failing `test_load_metabric_returns_only_validated_aggregate_contracts` that expects `DATA_READY`, 1,904 patient records, 1,904 matched samples, and no `rows` property.
- [ ] **Step 2:** Run `.\.venv\Scripts\python.exe -m pytest tests/test_metabric_ingestion.py -q -p no:cacheprovider`; confirm the expected missing import/contract failure.
- [ ] **Step 3:** Add frozen JSON-compatible `DataArtifactStatus`, `CohortSplitSummary`, `DatasetMetadata`, and `MetabricIngestionResult`; add `DATA_READY` and `DATA_INVALID` states.
- [ ] **Step 4:** Implement injected repository-relative paths; default root is only `Path(__file__).resolve().parents[2]`.
- [ ] **Step 5:** Re-run the focused test; confirm pass.

### Task 3: Validate artifacts, schema, matching, and partitions

**Files:** Modify `src/data/metabric.py` and `tests/test_metabric_ingestion.py`.

**Interfaces:** Stable issue codes are `ARTIFACT_MISSING`, `CHECKSUM_MISMATCH`, `METADATA_INVALID`, `SCHEMA_MISMATCH`, `DUPLICATE_PATIENT_ID`, `PATIENT_MAPPING_INVALID`, and `MANIFEST_INVALID`.

- [ ] **Step 1:** Write failing isolated tests for checksum tampering, a missing artifact, malformed JSON, missing required prepared column, duplicate prepared patient ID, non-1:1 mapping, and unknown/mismatched manifest splits.
- [ ] **Step 2:** Run the focused test file and confirm each failure occurs because validation is absent.
- [ ] **Step 3:** Implement chunked `hashlib.sha256`; parse JSON/CSV with only standard library; retain counts and identifier sets but never return source rows.
- [ ] **Step 4:** Validate feature/clinical headers, unique IDs, mapping, `train`/`validation`/`test` membership, and expected aggregate counts from `dataset_summary.json`.
- [ ] **Step 5:** Re-run the focused tests; confirm pass.

### Task 4: Adapt and test semantic preparation reproducibility

**Files:** Modify `scripts/prepare_data.py`, `pyproject.toml`, and `tests/test_metabric_ingestion.py`.

**Interfaces:** `prepare_dataset(raw_csv: Path, output_root: Path) -> None` writes fresh prepared/metadata outputs and never writes to `raw_csv`.

- [ ] **Step 1:** Write a failing temp-directory test that invokes `prepare_dataset` and compares canonical/reproduced header order, patient-ID order, event inversion, stage normalization, typo correction, mapping, and manifest values; no byte-equality assertion.
- [ ] **Step 2:** Run it; confirm failure because supplied paths assume a flat directory.
- [ ] **Step 3:** Inject raw/input and output root paths while retaining supplied transformations exactly.
- [ ] **Step 4:** Add optional `data-preparation` dependencies for pandas/scikit-learn, not Streamlit runtime dependencies.
- [ ] **Step 5:** Re-run preparation and ingestion tests; confirm pass.

### Task 5: Add aggregate-only session-backed Data / Cohort UI

**Files:** Create `src/ui/data_cohort_state.py`; modify `src/ui/pages/data_cohort.py`, `tests/test_app_shell.py`, and `tests/test_ui_foundation.py`.

**Interfaces:** `get_metabric_ingestion_state(session_state: MutableMapping[str, object], *, refresh: bool = False) -> MetabricIngestionResult`; session state stores only the result contract.

- [ ] **Step 1:** Write failing UI/state tests requiring aggregate 1,904 cohort text, no patient identifiers, rerun reuse, and explicit refresh reload.
- [ ] **Step 2:** Run UI tests; confirm the R1 pending-only page fails.
- [ ] **Step 3:** Render validation state, aggregate totals/splits, clinical field names/units, subtype labels/NC policy, and provenance resolution. Add a `Refresh validated data` control. Do not render dataframes, IDs, clinical values, or prediction UI.
- [ ] **Step 4:** Re-run UI tests; confirm pass.

### Task 6: Document and verify R2

**Files:** Modify `README.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/api_contracts.md`, `docs/data.md`, `docs/setup.md`, `docs/testing.md`, `docs/user_flow.md`, `docs/limitations.md`, and `docs/implementation_log.md`.

- [ ] **Step 1:** Document prepared-data use, raw immutability, integrity/schema validation, semantic preparation, aggregate-only UI, provenance resolution, and R2/R3 scope boundary.
- [ ] **Step 2:** Add R2 changelog and implementation-log entries without altering history.
- [ ] **Step 3:** Run the full pytest suite, compile `app.py src scripts tests`, run `pip check`, and run `git diff --check`.
- [ ] **Step 4:** Verify all SHA entries and CSV sizes; scan for Downloads/ZIP/`ai_handoff_data` path references and model/prediction/decision residue.
- [ ] **Step 5:** Smoke-test the live Streamlit Data / Cohort page for aggregate-only content, safe validation display, and research disclaimer; stop server.
- [ ] **Step 6:** Review final diff and commit with `git commit -m "feat: add validated METABRIC data ingestion"`.
