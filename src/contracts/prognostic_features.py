"""Framework-independent R8 prognostic genomic feature contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math

from .analysis import SerializableContract


COEF_EPS = 1e-6


class FeatureType(StrEnum):
    """Approved genomic feature groups analyzed by R8."""

    EXPRESSION = "expression"
    MUTATION_PRESENCE = "mutation_presence"


class EffectDirection(StrEnum):
    """Model-association direction under the frozen R8 threshold."""

    HIGHER = "associated_with_higher_modeled_hazard"
    LOWER = "associated_with_lower_modeled_hazard"
    EFFECTIVELY_ZERO = "effectively_zero_under_r8_threshold"


DIRECTION_DISPLAY_TEXT = {
    EffectDirection.HIGHER: "Associated with higher modeled hazard",
    EffectDirection.LOWER: "Associated with lower modeled hazard",
    EffectDirection.EFFECTIVELY_ZERO: (
        "Effectively zero under the R8 numerical coefficient threshold"
    ),
}


FEATURE_EFFECTS_CSV_COLUMNS = (
    "rank",
    "frozen_genomic_order",
    "raw_feature_name",
    "model_feature_name",
    "feature_type",
    "beta",
    "abs_beta",
    "hazard_ratio",
    "direction",
    "direction_display",
    "is_active",
    "standard_error",
    "beta_ci_lower_95",
    "beta_ci_upper_95",
    "hazard_ratio_ci_lower_95",
    "hazard_ratio_ci_upper_95",
    "comparison_to",
    "z_statistic",
    "p_value",
    "negative_log2_p_value",
)


def _require_positive_integer(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_finite(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")


@dataclass(frozen=True, slots=True)
class GenomicFeatureMapping(SerializableContract):
    """One frozen raw-to-model genomic feature mapping."""

    frozen_genomic_order: int
    raw_feature_name: str
    model_feature_name: str
    feature_type: FeatureType

    def __post_init__(self) -> None:
        _require_positive_integer(self.frozen_genomic_order, "frozen_genomic_order")
        _require_text(self.raw_feature_name, "raw_feature_name")
        _require_text(self.model_feature_name, "model_feature_name")
        if not isinstance(self.feature_type, FeatureType):
            raise TypeError("feature_type must be a FeatureType")


@dataclass(frozen=True, slots=True)
class PenalizedCoxSummaryValues(SerializableContract):
    """Descriptive inferential values reported by the frozen Cox model."""

    standard_error: float
    beta_ci_lower_95: float
    beta_ci_upper_95: float
    hazard_ratio_ci_lower_95: float
    hazard_ratio_ci_upper_95: float
    comparison_to: float
    z_statistic: float
    p_value: float
    negative_log2_p_value: float

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            _require_finite(getattr(self, field_name), field_name)
        if self.standard_error < 0:
            raise ValueError("standard_error must be non-negative")
        if self.beta_ci_lower_95 > self.beta_ci_upper_95:
            raise ValueError("beta confidence interval bounds are reversed")
        if self.hazard_ratio_ci_lower_95 <= 0 or self.hazard_ratio_ci_upper_95 <= 0:
            raise ValueError("hazard ratio confidence bounds must be positive")
        if self.hazard_ratio_ci_lower_95 > self.hazard_ratio_ci_upper_95:
            raise ValueError("hazard ratio confidence interval bounds are reversed")
        if not 0 <= self.p_value <= 1:
            raise ValueError("p_value must be between zero and one")
        if self.negative_log2_p_value < 0:
            raise ValueError("negative_log2_p_value must be non-negative")


@dataclass(frozen=True, slots=True)
class PrognosticFeatureEffect(SerializableContract):
    """One ranked genomic coefficient from the frozen R6 Track B model."""

    rank: int
    frozen_genomic_order: int
    raw_feature_name: str
    model_feature_name: str
    feature_type: FeatureType
    beta: float
    abs_beta: float
    hazard_ratio: float
    direction: EffectDirection
    direction_display: str
    is_active: bool
    model_summary: PenalizedCoxSummaryValues

    def __post_init__(self) -> None:
        _require_positive_integer(self.rank, "rank")
        _require_positive_integer(self.frozen_genomic_order, "frozen_genomic_order")
        _require_text(self.raw_feature_name, "raw_feature_name")
        _require_text(self.model_feature_name, "model_feature_name")
        if not isinstance(self.feature_type, FeatureType):
            raise TypeError("feature_type must be a FeatureType")
        for field_name in ("beta", "abs_beta", "hazard_ratio"):
            _require_finite(getattr(self, field_name), field_name)
        if self.abs_beta < 0 or not math.isclose(self.abs_beta, abs(self.beta), rel_tol=0, abs_tol=1e-15):
            raise ValueError("abs_beta must equal abs(beta)")
        if self.hazard_ratio <= 0:
            raise ValueError("hazard_ratio must be positive")
        if not math.isclose(self.hazard_ratio, math.exp(self.beta), rel_tol=1e-12, abs_tol=1e-15):
            raise ValueError("hazard_ratio must equal exp(beta)")
        if not isinstance(self.is_active, bool):
            raise TypeError("is_active must be boolean")
        expected_active = self.abs_beta > COEF_EPS
        if self.is_active is not expected_active:
            raise ValueError("activity must use the frozen COEF_EPS threshold")
        expected_direction = (
            EffectDirection.HIGHER
            if self.beta > COEF_EPS
            else EffectDirection.LOWER
            if self.beta < -COEF_EPS
            else EffectDirection.EFFECTIVELY_ZERO
        )
        if self.direction is not expected_direction:
            raise ValueError("direction must match beta and the frozen threshold")
        if self.direction_display != DIRECTION_DISPLAY_TEXT[self.direction]:
            raise ValueError("direction_display must match direction")
        if not isinstance(self.model_summary, PenalizedCoxSummaryValues):
            raise TypeError("model_summary must be PenalizedCoxSummaryValues")


@dataclass(frozen=True, slots=True)
class PrognosticFeatureAnalysisResult(SerializableContract):
    """Complete aggregate-only R8 result for all frozen genomic predictors."""

    schema_version: str
    analysis_id: str
    coef_eps: float
    effects: tuple[PrognosticFeatureEffect, ...]

    def __post_init__(self) -> None:
        _require_text(self.schema_version, "schema_version")
        _require_text(self.analysis_id, "analysis_id")
        _require_finite(self.coef_eps, "coef_eps")
        if self.coef_eps != COEF_EPS:
            raise ValueError("coef_eps must equal the frozen COEF_EPS value")
        if not isinstance(self.effects, tuple) or not all(
            isinstance(effect, PrognosticFeatureEffect) for effect in self.effects
        ):
            raise TypeError("effects must be an ordered tuple of PrognosticFeatureEffect values")
        if len(self.effects) != 68:
            raise ValueError("R8 requires exactly 68 genomic effects")
        if sum(effect.feature_type is FeatureType.EXPRESSION for effect in self.effects) != 50:
            raise ValueError("R8 requires exactly 50 expression effects")
        if sum(effect.feature_type is FeatureType.MUTATION_PRESENCE for effect in self.effects) != 18:
            raise ValueError("R8 requires exactly 18 mutation-presence effects")
        for field_name, values in (
            ("raw feature names", [effect.raw_feature_name for effect in self.effects]),
            ("model feature names", [effect.model_feature_name for effect in self.effects]),
            ("frozen genomic orders", [effect.frozen_genomic_order for effect in self.effects]),
            ("ranks", [effect.rank for effect in self.effects]),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must be unique")
        if tuple(effect.rank for effect in self.effects) != tuple(range(1, 69)):
            raise ValueError("effect ranks must be consecutive in tuple order")
        if set(effect.frozen_genomic_order for effect in self.effects) != set(range(1, 69)):
            raise ValueError("frozen genomic orders must be consecutive from one through 68")
