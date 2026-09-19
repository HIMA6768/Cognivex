"""Shared deterministic R5 test fixtures."""

from src.contracts import (
    CategoricalFeatureComparison,
    ConcordanceResult,
    CoxModelConfiguration,
    MatrixDiagnostic,
    PHDiagnosticStatus,
    PHDiagnostics,
    RuntimeProvenance,
    SurvivalCohortSummary,
    TrackAExperimentResult,
)


def make_track_a_result() -> TrackAExperimentResult:
    configuration = CoxModelConfiguration(
        track="track_a",
        task="clinical_survival",
        model_type="CoxPHFitter",
        baseline_estimation_method="breslow",
        penalizer=0.0,
        l1_ratio=0.0,
        strata=(),
        alpha=0.05,
        duration_column="overall_survival_months",
        event_column="overall_survival",
        feature_names=("age_at_diagnosis", "tumor_size", "tumor_stage_2"),
        categorical_comparisons=(
            CategoricalFeatureComparison(
                raw_variable="tumor_stage",
                category="2",
                reference_category="1",
                derived_feature_name="tumor_stage_2",
            ),
        ),
    )
    train = SurvivalCohortSummary("train", 3, 2, 1, "a" * 64)
    validation = SurvivalCohortSummary("validation", 2, 1, 1, "b" * 64)
    matrix = MatrixDiagnostic(3, 2, 2, 1.0, (), (), (), True)
    train_metric = ConcordanceResult(
        "harrell_c_index", "train", 3, 2, 1, 0.75, "log_partial_hazard",
        "higher_risk_is_higher_hazard", True, "a" * 64,
    )
    validation_metric = ConcordanceResult(
        "harrell_c_index", "validation", 2, 1, 1, 0.5, "log_partial_hazard",
        "higher_risk_is_higher_hazard", True, "b" * 64,
    )
    diagnostics = PHDiagnostics(PHDiagnosticStatus.PASSED, "rank", 0.05, (), None)
    runtime = RuntimeProvenance(
        python_version="3.14.6",
        lifelines_version="0.30.3",
        pandas_version="2.3.3",
        numpy_version="2.5.3",
        scipy_version="1.18.1",
        sklearn_version="1.9.1",
        git_commit="0" * 40,
        prepared_sha256="1" * 64,
        manifest_sha256="2" * 64,
    )
    return TrackAExperimentResult(
        schema_version="1.0",
        experiment_id="r5-test",
        configuration=configuration,
        train_cohort=train,
        validation_cohort=validation,
        held_out_test_count=2,
        test_transformed=False,
        test_predicted=False,
        test_scored=False,
        matrix_diagnostic=matrix,
        train_metric=train_metric,
        validation_metric=validation_metric,
        coefficients=(),
        ph_diagnostics=diagnostics,
        convergence_status="CONVERGED",
        convergence_warnings=(),
        runtime=runtime,
    )
