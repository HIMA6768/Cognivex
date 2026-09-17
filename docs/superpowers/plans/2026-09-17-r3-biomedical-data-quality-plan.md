# R3 Biomedical Data Quality Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a deterministic, aggregate-only, framework-independent data-quality report for the canonical R2 METABRIC cohort.

**Architecture:** R3 gates on the existing R2 ingestion result, then makes one read-only scan of the prepared CSV and current R2 metadata, manifest, and mapping. Typed quality contracts hold only aggregates; Streamlit caches and renders that report on the existing Data / Cohort page.

**Tech Stack:** Python 3.11 standard library (`csv`, `json`, `math`, `dataclasses`), Streamlit, pytest.

**Spec:** `docs/superpowers/specs/2026-09-17-r3-biomedical-data-quality-design.md`

## Global Constraints

- R3 begins only after R2 returns `DATA_READY`; R2 ingestion behavior remains unchanged.
- Read only the canonical prepared CSV and existing R2 metadata, manifest, and mapping.
- Return framework-independent, deterministic, aggregate-only contracts.
- Do not mutate, impute, rebalance, filter, select, encode, scale, or model data; never regenerate the locked manifest or drop NC rows.
- Treat structural failure as `ERROR`, downstream engineering limitations as `WARNING`, and descriptive facts as `INFORMATION`.
- Keep the suspicious-duration engineering heuristic centralized and non-clinical.
- Use synthetic invalid fixtures; do not copy the production METABRIC cohort into R3 tests.
- Keep subagents off and stop after the R3 gate.

---

### Task 1: Add quality contracts and rule configuration

**Files:** Modify `src/contracts/analysis.py`, `src/contracts/__init__.py`; create `src/data/quality_rules.py`; create `tests/test_data_quality.py`.

**Interfaces:** `DataQualityFinding`, `DataQualityReport`, `DataQualitySeverity`, `DataQualityStatus`, `QualityRules`, and `DEFAULT_QUALITY_RULES` are serializable and contain no Streamlit types.

- [x] **Step 1: Write failing contract tests**

```python
def test_quality_report_serializes_aggregate_findings() -> None:
    finding = DataQualityFinding(
        code="ZERO_SURVIVAL_DURATION",
        severity=DataQualitySeverity.WARNING,
        title="Zero survival duration",
        message="One record has a zero survival duration.",
        affected_count=1,
        affected_fraction=1 / 3,
        subject="overall_survival_months",
        recommendation="Review the source value before later preprocessing.",
    )
    report = DataQualityReport(
        status=DataQualityStatus.DATA_QUALITY_READY_WITH_WARNINGS,
        findings=(finding,),
        cohort_size=3,
        error_count=0,
        warning_count=1,
        information_count=0,
    )
    assert report.to_dict()["status"] == "DATA_QUALITY_READY_WITH_WARNINGS"
    assert "patient_id" not in str(report.to_dict())
```

- [x] **Step 2: Run the contract test and confirm the new imports fail.**

- [x] **Step 3: Add frozen validated dataclasses and the 1,200-month injected engineering rule.**

- [x] **Step 4: Re-run the contract test and confirm pass.**

### Task 2: Build the R3 quality scanner test-first

**Files:** Create `src/data/metabric_quality.py`; modify `src/data/__init__.py`; modify `tests/test_data_quality.py`.

**Interfaces:** `evaluate_metabric_quality(paths: MetabricPaths | None = None, ingestion: MetabricIngestionResult | None = None, rules: QualityRules = DEFAULT_QUALITY_RULES) -> DataQualityReport`.

- [x] **Step 1: Build a small synthetic canonical-layout fixture** with prepared rows, metadata, mapping, and manifest plus a typed `DATA_READY` ingestion result; it must never copy production rows.

- [x] **Step 2: Write failing tests for a valid report, invalid event, missing/negative survival time, duplicate patient, split contamination, and broken one-to-one mapping.**

- [x] **Step 3: Implement the R2 gate, identifier/mapping/manifest checks, canonical event coding checks, and deterministic status derivation.**

- [x] **Step 4: Re-run the focused tests and confirm pass.**

### Task 3: Cover clinical, genomic, subtype, and aggregate summary rules

**Files:** Modify `src/data/metabric_quality.py` and `tests/test_data_quality.py`.

**Interfaces:** The report exposes clinical missingness, survival summary, split distributions, subtype summary, and genomic summaries without row records or feature-value payloads.

- [x] **Step 1: Write failing tests for unexpected clinical category, accepted `Unknown` stage, missing feature, non-numeric/infinite genomic values, zero variance, valid/NC/unexpected subtype values, warning-only status, and blocked status.**

- [x] **Step 2: Implement schema-driven clinical checks, group-driven genomic checks, subtype mapping/policy checks, and aggregate findings.**

- [x] **Step 3: Run the focused R3 test module and confirm all synthetic cases pass.**

### Task 4: Add cached aggregate-only Data / Cohort presentation

**Files:** Modify `src/ui/data_cohort_state.py`, `src/ui/pages/data_cohort.py`, `tests/test_app_shell.py`; create or extend `tests/test_data_quality.py`.

**Interfaces:** `get_metabric_quality_state(session_state, ingestion, refresh=False) -> DataQualityReport` caches only the report and recomputes after a cohort refresh.

- [x] **Step 1: Write failing UI/state tests for a status, severity counts, aggregate endpoint/split/subtype/genomic summaries, cache reuse/refresh, and no patient identifiers or row data.**

- [x] **Step 2: Implement the cache boundary and concise responsive report sections using existing page components.**

- [x] **Step 3: Run UI and R3 tests and confirm pass.**

### Task 5: Document, scan, and verify R3

**Files:** Create `docs/data_quality.md`; modify `README.md`, `CHANGELOG.md`, `docs/architecture.md`, `docs/data.md`, `docs/api_contracts.md`, `docs/testing.md`, `docs/limitations.md`, `docs/user_flow.md`, and `docs/implementation_log.md`.

- [x] **Step 1: Document rule severities, engineering status semantics, the non-clinical duration sentinel, NC/Unknown policies, R3 findings, and R4 boundary.**

- [x] **Step 2: Run focused R3 tests, the full pytest suite, compile check, dependency check, and canonical R3 scan.**

- [x] **Step 3: Smoke-test desktop and mobile Data / Cohort, inspect browser/server errors, confirm no patient identifiers or rows, review the diff/status, and commit `feat: add METABRIC data quality validation`.**
