# Biomedical integration contracts

## Boundary

`src.contracts` is independent of Streamlit, pandas, lifelines, scikit-learn, and model runtimes. R3 adds aggregate data-quality contracts but contains no scientific result values.

## Contracts

- `AnalysisStatus`: `PENDING_DATA`, `DATA_READY`, `DATA_INVALID`, or `PENDING_MODEL`.
- `ValidationIssueSeverity`: `ERROR`, `WARNING`, or `INFORMATION`.
- `DatasetValidationIssue`: stable code, typed severity, and safe message.
- `DatasetValidationReport`: availability, message, and ordered issues.
- `CohortSplitSummary`: aggregate train, validation, and test counts only.
- `CohortSummary`: optional clinical, patient, genomic, matched, and split counts without rows.
- `DataArtifactStatus`: a repository-relative artifact name/path and checksum status.
- `DatasetMetadata`: validated aggregate feature counts, clinical field names, confirmed subtype labels/NC policy, and prepared dataset path.
- `MetabricIngestionResult`: typed validation, cohort, metadata, and checksum artifact statuses; it never carries CSV rows.
- `DataQualitySeverity`: `ERROR`, `WARNING`, or `INFORMATION` for data-engineering findings.
- `DataQualityStatus`: `DATA_QUALITY_READY`, `DATA_QUALITY_READY_WITH_WARNINGS`, or `DATA_QUALITY_BLOCKED`; it is never a clinical judgment.
- `DataQualityFinding`: stable code, typed severity, user-safe aggregate impact, optional field/group, and an actionable recommendation.
- `DataQualityReport`: deterministic aggregate quality findings, severity totals, and optional survival, clinical missingness, split, subtype, and genomic summaries; it never carries patient rows or identifiers.
- `ModelMetadata`: optional provenance fields pending model handoff.
- `ExperimentMetadata`: optional experiment, task, dataset, and feature-set identifiers.
- `SurvivalPredictionResult` and `SurvivalEvaluationResult`: pending-only prognosis boundaries.
- `SubtypePredictionResult` and `SubtypeEvaluationResult`: pending-only classification boundaries with no frozen subtype taxonomy.
- `FeatureImportanceResult`: pending-only gene-insight boundary with no ranking or biological claim.
- `AnalysisResult`: typed aggregate of all stages.

All contracts are frozen, slot-backed dataclasses and expose JSON-compatible `to_dict()` output. Numeric prediction, evaluation, and importance fields will be introduced only by the increment that defines and validates their semantics.
