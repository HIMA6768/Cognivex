from __future__ import annotations

import json
from pathlib import Path

from r7_helpers import make_synthetic_track_c_run
from src.artifacts.track_c import render_track_c_report, write_track_c_artifacts


def _report(tmp_path: Path):
    prepared, selection, result = make_synthetic_track_c_run()
    bundle = write_track_c_artifacts(selection, result, prepared, tmp_path)
    metadata = json.loads((bundle / "metadata.json").read_text(encoding="utf-8"))
    return result, metadata, render_track_c_report(result, metadata)


def test_report_contains_objective_counts_target_classes_nc_policy_features_and_candidates(tmp_path: Path) -> None:
    result, metadata, report = _report(tmp_path)

    assert "Molecular Subtype Classification" in report
    assert "Train: 36 eligible" in report
    assert "Validation: 18 eligible" in report
    assert "Test: 18 eligible" in report
    assert "pam50_+_claudin-low_subtype" in report
    assert "NC" in report and "only from Track C" in report
    assert "Expression predictors: 50" in report
    assert "Mutation-presence predictors: 18" in report
    assert "Clinical predictors: 0" in report
    assert result.selected_definition.display_name in report


def test_report_contains_validation_leaderboard_selected_reason_test_metrics_per_class_and_confusion(tmp_path: Path) -> None:
    result, metadata, report = _report(tmp_path)

    assert "Validation leaderboard" in report
    assert "highest validation Macro-F1" in report
    assert "Final frozen-winner test metrics" in report
    assert "Per-class test metrics" in report
    assert "Confusion matrix" in report
    assert f"{result.test_metrics.macro_f1:.6f}" in report
    assert all(label in report for label in result.class_order)


def test_report_states_test_not_used_for_selection_and_avoids_biological_claims(tmp_path: Path) -> None:
    result, metadata, report = _report(tmp_path)

    assert "The test set was not used for model selection." in report
    assert "does not establish biological causality" in report
    assert "causes subtype" not in report.lower()


def test_report_is_deterministic_for_same_experiment_result(tmp_path: Path) -> None:
    result, metadata, report = _report(tmp_path)

    assert render_track_c_report(result, metadata) == report
