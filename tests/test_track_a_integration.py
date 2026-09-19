"""Canonical R5A fit and command-boundary integration tests."""

from __future__ import annotations

import math
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.train_track_a import validate_experiment_id
from src.data.metabric import MetabricPaths
from src.training.track_a import fit_track_a, prepare_track_a_run


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_reference_coded_track_a_fit_preserves_all_frozen_boundaries() -> None:
    prepared = prepare_track_a_run(MetabricPaths.from_repository_root())
    bundle = fit_track_a(prepared, "r5a-canonical-integration")
    result = bundle.result

    assert (result.train_cohort.row_count, result.train_cohort.event_count) == (1332, 760)
    assert (result.validation_cohort.row_count, result.validation_cohort.event_count) == (285, 168)
    assert result.held_out_test_count == 286
    assert (result.test_transformed, result.test_predicted, result.test_scored) == (
        False,
        False,
        False,
    )
    assert result.matrix_diagnostic.feature_count == result.matrix_diagnostic.rank == 12
    assert result.matrix_diagnostic.condition_number == pytest.approx(966.3126760060184)
    assert result.matrix_diagnostic.zero_variance_features == ()
    assert result.matrix_diagnostic.duplicate_column_pairs == ()
    assert result.matrix_diagnostic.linear_dependencies == ()
    assert result.configuration.model_type == "CoxPHFitter"
    assert result.configuration.baseline_estimation_method == "breslow"
    assert result.configuration.penalizer == 0.0
    assert result.configuration.l1_ratio == 0.0
    assert result.configuration.strata == ()
    assert result.configuration.alpha == 0.05
    assert {
        item.raw_variable: item.reference_category
        for item in result.configuration.categorical_comparisons
    } == {
        "tumor_stage": "1",
        "er_status_measured_by_ihc": "Negative",
        "pr_status": "Negative",
        "her2_status": "Negative",
    }
    assert result.convergence_status == "CONVERGED"
    assert result.convergence_warnings == ()
    assert result.train_metric.c_index == pytest.approx(0.6714658168217612)
    assert result.validation_metric.c_index == pytest.approx(0.6506960067491564)
    stage_four = next(
        item for item in result.coefficients if item.feature_name == "tumor_stage_4"
    )
    assert math.isfinite(stage_four.coefficient)
    assert math.isfinite(stage_four.standard_error)
    assert stage_four.hazard_ratio_ci_lower_95 < stage_four.hazard_ratio < stage_four.hazard_ratio_ci_upper_95


@pytest.mark.parametrize(
    "value",
    ("", "../escape", "contains spaces", "slash/name", ".hidden", "a" * 129),
)
def test_experiment_id_rejects_unsafe_paths(value: str) -> None:
    with pytest.raises(ValueError, match="experiment ID"):
        validate_experiment_id(value)


def test_experiment_id_accepts_filesystem_safe_value() -> None:
    assert validate_experiment_id("r5a-track-a_baseline.v1") == "r5a-track-a_baseline.v1"


def test_training_script_executes_directly_from_repository_root() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/train_track_a.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--experiment-id" in completed.stdout
