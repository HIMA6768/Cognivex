"""Framework-independent contracts for the R5 Track A survival baseline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math

from .analysis import SerializableContract


def _text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _count(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _finite(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")


def _sha(value: str, name: str) -> None:
    _text(value, name)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value.lower()):
        raise ValueError(f"{name} must be a SHA-256 hex digest")


def _names(value: tuple[str, ...], name: str, *, allow_empty: bool = False) -> None:
    if not isinstance(value, tuple) or (not value and not allow_empty):
        raise ValueError(f"{name} must be an ordered tuple of names")
    if any(not isinstance(item, str) or not item.strip() for item in value) or len(set(value)) != len(value):
        raise ValueError(f"{name} must contain unique non-empty names")


class PHDiagnosticStatus(StrEnum):
    PASSED = "PASSED"
    FLAGGED = "FLAGGED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class CategoricalFeatureComparison(SerializableContract):
    raw_variable: str
    category: str
    reference_category: str
    derived_feature_name: str

    def __post_init__(self) -> None:
        for name in (
            "raw_variable",
            "category",
            "reference_category",
            "derived_feature_name",
        ):
            _text(getattr(self, name), name)
        if self.category == self.reference_category:
            raise ValueError("category and reference_category must differ")


@dataclass(frozen=True, slots=True)
class CoxModelConfiguration(SerializableContract):
    track: str
    task: str
    model_type: str
    baseline_estimation_method: str
    penalizer: float
    l1_ratio: float
    strata: tuple[str, ...]
    alpha: float
    duration_column: str
    event_column: str
    feature_names: tuple[str, ...]
    categorical_comparisons: tuple[CategoricalFeatureComparison, ...]

    def __post_init__(self) -> None:
        for name in ("track", "task", "model_type", "baseline_estimation_method", "duration_column", "event_column"):
            _text(getattr(self, name), name)
        _finite(self.penalizer, "penalizer")
        _finite(self.l1_ratio, "l1_ratio")
        _finite(self.alpha, "alpha")
        if self.penalizer < 0 or not 0 <= self.l1_ratio <= 1 or not 0 < self.alpha < 1:
            raise ValueError("Cox configuration numeric values are outside their valid ranges")
        _names(self.strata, "strata", allow_empty=True)
        _names(self.feature_names, "feature_names")
        if not isinstance(self.categorical_comparisons, tuple) or not all(
            isinstance(item, CategoricalFeatureComparison)
            for item in self.categorical_comparisons
        ):
            raise TypeError(
                "categorical_comparisons must contain CategoricalFeatureComparison values"
            )
        comparison_names = tuple(
            item.derived_feature_name for item in self.categorical_comparisons
        )
        _names(comparison_names, "categorical comparison feature names", allow_empty=True)
        if any(name not in self.feature_names for name in comparison_names):
            raise ValueError("categorical comparison features must appear in feature_names")
        if self.duration_column in self.feature_names or self.event_column in self.feature_names:
            raise ValueError("survival targets must not appear in feature_names")


@dataclass(frozen=True, slots=True)
class SurvivalCohortSummary(SerializableContract):
    split: str
    row_count: int
    event_count: int
    censored_count: int
    cohort_fingerprint: str

    def __post_init__(self) -> None:
        _text(self.split, "split")
        for name in ("row_count", "event_count", "censored_count"):
            _count(getattr(self, name), name)
        if self.event_count + self.censored_count != self.row_count:
            raise ValueError("event and censored counts must sum to row_count")
        _sha(self.cohort_fingerprint, "cohort_fingerprint")


@dataclass(frozen=True, slots=True)
class MatrixDiagnostic(SerializableContract):
    row_count: int
    feature_count: int
    rank: int
    condition_number: float
    zero_variance_features: tuple[str, ...]
    duplicate_column_pairs: tuple[tuple[str, str], ...]
    linear_dependencies: tuple[str, ...]
    all_finite: bool

    def __post_init__(self) -> None:
        for name in ("row_count", "feature_count", "rank"):
            _count(getattr(self, name), name)
        if self.rank > min(self.row_count, self.feature_count):
            raise ValueError("rank exceeds matrix dimensions")
        if (
            not isinstance(self.condition_number, (int, float))
            or isinstance(self.condition_number, bool)
            or math.isnan(float(self.condition_number))
            or self.condition_number < 1
        ):
            raise ValueError("condition_number must be at least 1 and not NaN")
        _names(self.zero_variance_features, "zero_variance_features", allow_empty=True)
        if not isinstance(self.duplicate_column_pairs, tuple) or any(
            not isinstance(pair, tuple) or len(pair) != 2 or any(not isinstance(item, str) or not item for item in pair)
            for pair in self.duplicate_column_pairs
        ):
            raise TypeError("duplicate_column_pairs must contain name pairs")
        if not isinstance(self.linear_dependencies, tuple) or not all(
            isinstance(item, str) and item for item in self.linear_dependencies
        ):
            raise TypeError("linear_dependencies must be an ordered tuple of strings")
        if not isinstance(self.all_finite, bool):
            raise TypeError("all_finite must be a bool")


@dataclass(frozen=True, slots=True)
class ConcordanceResult(SerializableContract):
    metric_name: str
    split: str
    row_count: int
    event_count: int
    censored_count: int
    c_index: float
    prediction_quantity: str
    score_direction: str
    risk_negated_for_metric: bool
    cohort_fingerprint: str

    def __post_init__(self) -> None:
        for name in ("metric_name", "split", "prediction_quantity", "score_direction"):
            _text(getattr(self, name), name)
        for name in ("row_count", "event_count", "censored_count"):
            _count(getattr(self, name), name)
        if self.event_count + self.censored_count != self.row_count:
            raise ValueError("event and censored counts must sum to row_count")
        _finite(self.c_index, "c_index")
        if not 0 <= self.c_index <= 1:
            raise ValueError("c_index must be between 0 and 1")
        if not isinstance(self.risk_negated_for_metric, bool):
            raise TypeError("risk_negated_for_metric must be a bool")
        _sha(self.cohort_fingerprint, "cohort_fingerprint")


@dataclass(frozen=True, slots=True)
class CoefficientEstimate(SerializableContract):
    feature_name: str
    coefficient: float
    hazard_ratio: float
    standard_error: float
    coefficient_ci_lower_95: float
    coefficient_ci_upper_95: float
    hazard_ratio_ci_lower_95: float
    hazard_ratio_ci_upper_95: float
    z_statistic: float
    p_value: float

    def __post_init__(self) -> None:
        _text(self.feature_name, "feature_name")
        for name in (
            "coefficient", "hazard_ratio", "standard_error", "coefficient_ci_lower_95",
            "coefficient_ci_upper_95", "hazard_ratio_ci_lower_95", "hazard_ratio_ci_upper_95",
            "z_statistic", "p_value",
        ):
            _finite(getattr(self, name), name)
        if self.hazard_ratio <= 0 or self.standard_error < 0 or not 0 <= self.p_value <= 1:
            raise ValueError("coefficient estimate values are outside their valid ranges")


@dataclass(frozen=True, slots=True)
class PHFeatureDiagnostic(SerializableContract):
    feature_name: str
    test_statistic: float
    p_value: float
    flagged: bool

    def __post_init__(self) -> None:
        _text(self.feature_name, "feature_name")
        _finite(self.test_statistic, "test_statistic")
        _finite(self.p_value, "p_value")
        if not 0 <= self.p_value <= 1:
            raise ValueError("p_value must be between 0 and 1")
        if not isinstance(self.flagged, bool):
            raise TypeError("flagged must be a bool")


@dataclass(frozen=True, slots=True)
class PHDiagnostics(SerializableContract):
    status: PHDiagnosticStatus
    time_transform: str
    threshold: float
    features: tuple[PHFeatureDiagnostic, ...]
    error_message: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.status, PHDiagnosticStatus):
            raise TypeError("status must be a PHDiagnosticStatus")
        _text(self.time_transform, "time_transform")
        _finite(self.threshold, "threshold")
        if not 0 < self.threshold < 1:
            raise ValueError("threshold must be between 0 and 1")
        if not isinstance(self.features, tuple) or not all(isinstance(item, PHFeatureDiagnostic) for item in self.features):
            raise TypeError("features must contain PHFeatureDiagnostic values")
        if self.error_message is not None:
            _text(self.error_message, "error_message")


@dataclass(frozen=True, slots=True)
class RuntimeProvenance(SerializableContract):
    python_version: str
    lifelines_version: str
    pandas_version: str
    numpy_version: str
    scipy_version: str
    sklearn_version: str
    git_commit: str
    prepared_sha256: str
    manifest_sha256: str

    def __post_init__(self) -> None:
        for name in ("python_version", "lifelines_version", "pandas_version", "numpy_version", "scipy_version", "sklearn_version"):
            _text(getattr(self, name), name)
        _text(self.git_commit, "git_commit")
        for name in ("prepared_sha256", "manifest_sha256"):
            _sha(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class ArtifactRecord(SerializableContract):
    name: str
    relative_path: str
    sha256: str
    trusted_binary: bool

    def __post_init__(self) -> None:
        _text(self.name, "name")
        _text(self.relative_path, "relative_path")
        _sha(self.sha256, "sha256")
        if not isinstance(self.trusted_binary, bool):
            raise TypeError("trusted_binary must be a bool")


@dataclass(frozen=True, slots=True)
class TrackAExperimentResult(SerializableContract):
    schema_version: str
    experiment_id: str
    configuration: CoxModelConfiguration
    train_cohort: SurvivalCohortSummary
    validation_cohort: SurvivalCohortSummary
    held_out_test_count: int
    test_transformed: bool
    test_predicted: bool
    test_scored: bool
    matrix_diagnostic: MatrixDiagnostic
    train_metric: ConcordanceResult
    validation_metric: ConcordanceResult
    coefficients: tuple[CoefficientEstimate, ...]
    ph_diagnostics: PHDiagnostics
    convergence_status: str
    convergence_warnings: tuple[str, ...]
    runtime: RuntimeProvenance

    def __post_init__(self) -> None:
        _text(self.schema_version, "schema_version")
        _text(self.experiment_id, "experiment_id")
        _count(self.held_out_test_count, "held_out_test_count")
        for name in ("test_transformed", "test_predicted", "test_scored"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a bool")
        if self.test_transformed or self.test_predicted or self.test_scored:
            raise ValueError("R5 held-out test evidence must remain false")
        expected = (
            (self.configuration, CoxModelConfiguration, "configuration"),
            (self.train_cohort, SurvivalCohortSummary, "train_cohort"),
            (self.validation_cohort, SurvivalCohortSummary, "validation_cohort"),
            (self.matrix_diagnostic, MatrixDiagnostic, "matrix_diagnostic"),
            (self.train_metric, ConcordanceResult, "train_metric"),
            (self.validation_metric, ConcordanceResult, "validation_metric"),
            (self.ph_diagnostics, PHDiagnostics, "ph_diagnostics"),
            (self.runtime, RuntimeProvenance, "runtime"),
        )
        for value, contract_type, name in expected:
            if not isinstance(value, contract_type):
                raise TypeError(f"{name} must be {contract_type.__name__}")
        if not isinstance(self.coefficients, tuple) or not all(isinstance(item, CoefficientEstimate) for item in self.coefficients):
            raise TypeError("coefficients must contain CoefficientEstimate values")
        _text(self.convergence_status, "convergence_status")
        if not isinstance(self.convergence_warnings, tuple) or not all(isinstance(item, str) and item for item in self.convergence_warnings):
            raise TypeError("convergence_warnings must be an ordered tuple of strings")
