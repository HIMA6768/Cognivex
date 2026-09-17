# Biomedical integration contracts

## Boundary

`src.contracts` is independent of Streamlit, pandas, lifelines, scikit-learn, and model runtimes. R1 contracts represent pending states only and contain no scientific result values.

## Contracts

- `AnalysisStatus`: `PENDING_DATA` or `PENDING_MODEL`.
- `ValidationIssueSeverity`: `ERROR`, `WARNING`, or `INFORMATION`.
- `DatasetValidationIssue`: stable code, typed severity, and safe message.
- `DatasetValidationReport`: availability, message, and ordered issues.
- `CohortSummary`: optional clinical, genomic, and matched counts without assuming source columns.
- `ModelMetadata`: optional provenance fields pending model handoff.
- `ExperimentMetadata`: optional experiment, task, dataset, and feature-set identifiers.
- `SurvivalPredictionResult` and `SurvivalEvaluationResult`: pending-only prognosis boundaries.
- `SubtypePredictionResult` and `SubtypeEvaluationResult`: pending-only classification boundaries with no frozen subtype taxonomy.
- `FeatureImportanceResult`: pending-only gene-insight boundary with no ranking or biological claim.
- `AnalysisResult`: typed aggregate of all stages.

All contracts are frozen, slot-backed dataclasses and expose JSON-compatible `to_dict()` output. Numeric prediction, evaluation, and importance fields will be introduced only by the increment that defines and validates their semantics.
