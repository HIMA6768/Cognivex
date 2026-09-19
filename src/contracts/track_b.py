"""Framework-independent R6 Track B feature contracts."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .analysis import SerializableContract
from .survival import ConcordanceResult, RuntimeProvenance, SurvivalCohortSummary


def _ordered_names(values: tuple[str, ...], field: str) -> None:
    if not isinstance(values, tuple) or not values:
        raise ValueError(f"{field} must be a non-empty ordered tuple")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{field} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise ValueError(f"{field} must contain unique names")


@dataclass(frozen=True, slots=True)
class TrackBFeatureContract(SerializableContract):
    """Exact ordered raw predictor contract for R6 Track B."""

    clinical_features: tuple[str, ...]
    expression_features: tuple[str, ...]
    mutation_features: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in ("clinical_features", "expression_features", "mutation_features"):
            _ordered_names(getattr(self, field), field)
        if len(self.clinical_features) != 7:
            raise ValueError("Track B requires exactly 7 clinical features")
        if len(self.expression_features) != 50:
            raise ValueError("Track B requires exactly 50 expression features")
        if len(self.mutation_features) != 18:
            raise ValueError("Track B requires exactly 18 mutation features")
        if any(name.endswith("_mut") for name in self.expression_features):
            raise ValueError("expression features must not use the mutation suffix")
        if any(not name.endswith("_mut") for name in self.mutation_features):
            raise ValueError("mutation features must use the _mut suffix")
        if len(set(self.raw_features)) != 75:
            raise ValueError("Track B raw feature groups must be disjoint")

    @property
    def raw_features(self) -> tuple[str, ...]:
        return self.clinical_features + self.expression_features + self.mutation_features


@dataclass(frozen=True, slots=True)
class TrackBHyperparameters(SerializableContract):
    """One predefined penalized-Cox candidate."""

    penalizer: float
    l1_ratio: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.penalizer, (int, float))
            or isinstance(self.penalizer, bool)
            or not math.isfinite(float(self.penalizer))
            or self.penalizer <= 0
        ):
            raise ValueError("penalizer must be a positive finite number")
        if (
            not isinstance(self.l1_ratio, (int, float))
            or isinstance(self.l1_ratio, bool)
            or not math.isfinite(float(self.l1_ratio))
            or not 0 <= self.l1_ratio <= 1
        ):
            raise ValueError("l1_ratio must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class TrackBCandidateResult(SerializableContract):
    """Validation-only outcome for one candidate configuration."""

    configuration: TrackBHyperparameters
    status: str
    validation_c_index: float | None
    error_message: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.configuration, TrackBHyperparameters):
            raise TypeError("configuration must be TrackBHyperparameters")
        if self.status not in {"CONVERGED", "FAILED"}:
            raise ValueError("candidate status must be CONVERGED or FAILED")
        if self.status == "CONVERGED":
            if self.validation_c_index is None or not 0 <= self.validation_c_index <= 1:
                raise ValueError("converged candidate requires a valid validation C-index")
            if self.error_message is not None:
                raise ValueError("converged candidate cannot include an error")
        elif self.validation_c_index is not None or not self.error_message:
            raise ValueError("failed candidate requires only an error message")


@dataclass(frozen=True, slots=True)
class TrackBExperimentResult(SerializableContract):
    """Complete aggregate R6 outcome after one frozen-winner test evaluation."""

    schema_version: str
    experiment_id: str
    feature_contract: TrackBFeatureContract
    model_feature_names: tuple[str, ...]
    selected_configuration: TrackBHyperparameters
    leaderboard: tuple[TrackBCandidateResult, ...]
    train_cohort: SurvivalCohortSummary
    validation_cohort: SurvivalCohortSummary
    test_cohort: SurvivalCohortSummary
    train_metric: ConcordanceResult
    validation_metric: ConcordanceResult
    test_metric: ConcordanceResult
    track_a_validation_metric: ConcordanceResult
    track_a_test_metric: ConcordanceResult
    validation_delta: float
    test_delta: float
    candidate_test_evaluation_count: int
    winner_test_evaluation_count: int
    runtime: RuntimeProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise ValueError("schema_version must be non-empty")
        if not isinstance(self.experiment_id, str) or not self.experiment_id:
            raise ValueError("experiment_id must be non-empty")
        if not isinstance(self.feature_contract, TrackBFeatureContract):
            raise TypeError("feature_contract must be TrackBFeatureContract")
        _ordered_names(self.model_feature_names, "model_feature_names")
        if len(self.model_feature_names) != 80:
            raise ValueError("Track B must persist exactly 80 model features")
        if not isinstance(self.selected_configuration, TrackBHyperparameters):
            raise TypeError("selected_configuration must be TrackBHyperparameters")
        if not isinstance(self.leaderboard, tuple) or not self.leaderboard or not all(
            isinstance(item, TrackBCandidateResult) for item in self.leaderboard
        ):
            raise TypeError("leaderboard must contain TrackBCandidateResult values")
        for value, expected, name in (
            (self.train_cohort, SurvivalCohortSummary, "train_cohort"),
            (self.validation_cohort, SurvivalCohortSummary, "validation_cohort"),
            (self.test_cohort, SurvivalCohortSummary, "test_cohort"),
            (self.train_metric, ConcordanceResult, "train_metric"),
            (self.validation_metric, ConcordanceResult, "validation_metric"),
            (self.test_metric, ConcordanceResult, "test_metric"),
            (self.track_a_validation_metric, ConcordanceResult, "track_a_validation_metric"),
            (self.track_a_test_metric, ConcordanceResult, "track_a_test_metric"),
            (self.runtime, RuntimeProvenance, "runtime"),
        ):
            if not isinstance(value, expected):
                raise TypeError(f"{name} must be {expected.__name__}")
        if not math.isclose(
            self.validation_delta,
            self.validation_metric.c_index - self.track_a_validation_metric.c_index,
            abs_tol=1e-12,
        ):
            raise ValueError("validation_delta does not match B minus A")
        if not math.isclose(
            self.test_delta,
            self.test_metric.c_index - self.track_a_test_metric.c_index,
            abs_tol=1e-12,
        ):
            raise ValueError("test_delta does not match B minus A")
        if self.candidate_test_evaluation_count != 0:
            raise ValueError("candidate models must never be evaluated on test")
        if self.winner_test_evaluation_count != 1:
            raise ValueError("the frozen winner must receive exactly one test evaluation")
