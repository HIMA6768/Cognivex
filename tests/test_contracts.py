"""R1 framework-independent biomedical contract tests."""

from __future__ import annotations

import json

import pytest

from src.contracts import (
    AnalysisResult,
    AnalysisStatus,
    CohortSummary,
    DatasetValidationIssue,
    DatasetValidationReport,
    ExperimentMetadata,
    FeatureImportanceResult,
    ModelMetadata,
    SubtypeEvaluationResult,
    SubtypePredictionResult,
    SurvivalEvaluationResult,
    SurvivalPredictionResult,
    ValidationIssueSeverity,
)


def _pending_data(message: str) -> dict[str, object]:
    return {
        "status": AnalysisStatus.PENDING_DATA,
        "message": message,
        "model": None,
        "experiment": None,
    }


def test_pending_analysis_serializes_without_framework_or_scientific_values() -> None:
    validation = DatasetValidationReport(
        status=AnalysisStatus.PENDING_DATA,
        message="Upload or select a research cohort to begin validation.",
        issues=(),
    )
    cohort = CohortSummary(
        status=AnalysisStatus.PENDING_DATA,
        message="Cohort summary is pending data ingestion.",
    )
    result = AnalysisResult(
        validation=validation,
        cohort=cohort,
        survival_prediction=SurvivalPredictionResult(**_pending_data("Pending cohort data.")),
        survival_evaluation=SurvivalEvaluationResult(**_pending_data("Pending model evaluation.")),
        subtype_prediction=SubtypePredictionResult(**_pending_data("Pending subtype data.")),
        subtype_evaluation=SubtypeEvaluationResult(**_pending_data("Pending model evaluation.")),
        feature_importance=FeatureImportanceResult(**_pending_data("Pending model evaluation.")),
    )

    decoded = json.loads(json.dumps(result.to_dict()))

    assert decoded["validation"]["status"] == "PENDING_DATA"
    assert decoded["cohort"]["clinical_records"] is None
    assert decoded["cohort"]["genomic_samples"] is None
    assert decoded["cohort"]["matched_samples"] is None
    assert decoded["subtype_prediction"] == {
        "status": "PENDING_DATA",
        "message": "Pending subtype data.",
        "model": None,
        "experiment": None,
    }


def test_validation_report_preserves_typed_issue_severity() -> None:
    issue = DatasetValidationIssue(
        code="DATA_NOT_LOADED",
        severity=ValidationIssueSeverity.INFORMATION,
        message="Load a research cohort before validation.",
    )
    report = DatasetValidationReport(
        status=AnalysisStatus.PENDING_DATA,
        message="Validation is pending data ingestion.",
        issues=(issue,),
    )

    assert report.to_dict()["issues"] == [
        {
            "code": "DATA_NOT_LOADED",
            "severity": "INFORMATION",
            "message": "Load a research cohort before validation.",
        }
    ]


def test_model_and_experiment_metadata_allow_an_unresolved_handoff() -> None:
    model = ModelMetadata(
        name=None,
        version=None,
        experiment_id=None,
        preprocessing_version=None,
        mock=False,
    )
    experiment = ExperimentMetadata(
        experiment_id=None,
        task=None,
        dataset_version=None,
        feature_set=None,
    )

    assert model.to_dict()["name"] is None
    assert experiment.to_dict()["task"] is None


@pytest.mark.parametrize(
    "factory",
    [
        lambda: DatasetValidationIssue("", ValidationIssueSeverity.ERROR, "Safe message"),
        lambda: DatasetValidationIssue("CODE", "ERROR", "Safe message"),
        lambda: DatasetValidationReport(AnalysisStatus.PENDING_DATA, "", ()),
        lambda: CohortSummary(
            AnalysisStatus.PENDING_DATA,
            "Pending data.",
            clinical_records=-1,
        ),
    ],
)
def test_invalid_contract_values_are_rejected(factory) -> None:
    with pytest.raises((TypeError, ValueError)):
        factory()
