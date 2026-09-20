"""Read-only projection of the verified R8 aggregate analysis bundle."""

from __future__ import annotations

import csv

from src.artifacts.inference_registry import AggregateEntry
from src.contracts.inference import PrognosticFeatureAnalysisView, PrognosticFeatureEffectView
from src.contracts.prognostic_features import (
    EffectDirection, FeatureType, PenalizedCoxSummaryValues, PrognosticFeatureEffect,
)


def _effect(row: dict[str, str]) -> PrognosticFeatureEffect:
    return PrognosticFeatureEffect(
        rank=int(row["rank"]), frozen_genomic_order=int(row["frozen_genomic_order"]),
        raw_feature_name=row["raw_feature_name"], model_feature_name=row["model_feature_name"],
        feature_type=FeatureType(row["feature_type"]), beta=float(row["beta"]), abs_beta=float(row["abs_beta"]),
        hazard_ratio=float(row["hazard_ratio"]), direction=EffectDirection(row["direction"]),
        direction_display=row["direction_display"], is_active=row["is_active"].lower() == "true",
        model_summary=PenalizedCoxSummaryValues(
            standard_error=float(row["standard_error"]), beta_ci_lower_95=float(row["beta_ci_lower_95"]),
            beta_ci_upper_95=float(row["beta_ci_upper_95"]), hazard_ratio_ci_lower_95=float(row["hazard_ratio_ci_lower_95"]),
            hazard_ratio_ci_upper_95=float(row["hazard_ratio_ci_upper_95"]), comparison_to=float(row["comparison_to"]),
            z_statistic=float(row["z_statistic"]), p_value=float(row["p_value"]),
            negative_log2_p_value=float(row["negative_log2_p_value"]),
        ),
    )


def read_prognostic_feature_analysis(entry: AggregateEntry) -> PrognosticFeatureAnalysisView:
    """Read verified aggregate text only; no patient input, model load, or write."""
    if not entry.available or entry.bundle is None or entry.metadata is None:
        raise ValueError("R8 aggregate artifact is unavailable")
    with (entry.bundle / "feature_effects.csv").open(newline="", encoding="utf-8") as source:
        effects = tuple(PrognosticFeatureEffectView(_effect(row)) for row in csv.DictReader(source))
    metadata = entry.metadata
    return PrognosticFeatureAnalysisView(
        analysis_id=str(metadata["analysis_id"]), schema_version=str(metadata["schema_version"]),
        source_r6_experiment_id=str(metadata["source"]["experiment_id"]),
        coef_eps=float(metadata["coefficient_contract"]["coef_eps"]), effects=effects,
        interpretation="Aggregate model-associated coefficients from the frozen R6 Track B model; not causal or clinical guidance.",
    )
