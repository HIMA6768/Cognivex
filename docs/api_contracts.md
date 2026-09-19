# Biomedical integration contracts

## Boundary

`src.contracts` is independent of Streamlit, pandas, lifelines, scikit-learn, and model runtimes. R4/R4D preprocessing metadata contains no transformer objects, patient identifiers, or scientific result values.

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
- `PreprocessingTask` and `PreprocessingTrack`: frozen task/track names for Tracks A–D, including `clinical_mutation_survival` / `Track D`.
- `EligibilityReasonCode`, `ExclusionCount`, and `EligibilityResult`: stable row-aligned task masks/reasons plus aggregate exclusions without patient IDs.
- `SplitEligibilityCount`: aggregate eligible/excluded counts within one immutable manifest split.
- `MutationFeatureSelection`, `MutationSelectionMetadata`, and `MutationPreprocessingMetadata`: ordered raw/gene/derived mappings, fitted prevalence decisions, inclusive threshold semantics, all-gene burden policy, and aggregate-only selector evidence.
- `PreprocessingMetadata`: ordered raw/transformed feature names and explicit fit, imputation, encoding, scaling, mutation, NC, zero-duration, and leakage-guard policies. Track D additionally exposes exact standardized-continuous and unscaled-binary/one-hot final feature groups.
- `CanonicalPreprocessingReport`: aggregate R4 acceptance evidence, missing-indicator counts, artifact hashes, and transform-only fitted-state verification.
- `CategoricalFeatureComparison`: one derived categorical feature together with its raw variable, represented category, and explicit reference category.
- `CoxModelConfiguration`: frozen Track A estimator settings, ordered transformed features, target names, and category-versus-reference metadata.
- `MatrixDiagnostic`: pre-fit row/feature counts, exact rank, 2-norm condition number, finite-state, zero-variance, duplicate-column, and linear-dependency evidence.
- `SurvivalCohortSummary`, `ConcordanceResult`, `CoefficientEstimate`, `PHDiagnostics`, and `RuntimeProvenance`: aggregate R5A model evidence with no patient rows or identifiers.
- `TrackAExperimentResult`: complete R5A training/validation result, including explicit false flags proving the test split was not transformed, predicted, or scored.
- `ArtifactRecord`: checksummed artifact metadata with an explicit trusted-binary marker.
- `ModelMetadata`: optional provenance fields pending model handoff.
- `ExperimentMetadata`: optional experiment, task, dataset, and feature-set identifiers.
- `SurvivalPredictionResult` and `SurvivalEvaluationResult`: pending-only prognosis boundaries.
- `SubtypePredictionResult` and `SubtypeEvaluationResult`: pending-only classification boundaries with no frozen subtype taxonomy.
- `FeatureImportanceResult`: pending-only gene-insight boundary with no ranking or biological claim.
- `AnalysisResult`: typed aggregate of all stages.

All contracts are frozen, slot-backed dataclasses and expose JSON-compatible `to_dict()` output. R5A introduces aggregate Track A training/evaluation evidence only; patient prediction, Track B/D evaluation, subtype metrics, and importance fields remain gated.
