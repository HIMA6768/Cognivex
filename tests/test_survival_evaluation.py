"""R5 concordance direction and matrix-evidence tests."""

from __future__ import annotations

import numpy as np
import pytest

from src.evaluation.survival import diagnose_design_matrix, harrell_c_index


def _metric(durations: list[float], events: list[int], risks: list[float]):
    return harrell_c_index(
        durations,
        events,
        risks,
        split="synthetic",
        cohort_fingerprint="a" * 64,
    )


def test_higher_risk_for_earlier_event_is_perfect() -> None:
    assert _metric([1, 2, 3], [1, 1, 1], [3, 2, 1]).c_index == 1.0


def test_reversed_risk_is_anti_concordant() -> None:
    assert _metric([1, 2, 3], [1, 1, 1], [1, 2, 3]).c_index == 0.0


def test_tied_risk_scores_receive_half_credit() -> None:
    assert _metric([1, 2, 3], [1, 1, 1], [2, 2, 1]).c_index == pytest.approx(5 / 6)


def test_censoring_excludes_non_comparable_pairs() -> None:
    assert _metric([1, 2, 3], [0, 1, 1], [100, 2, 1]).c_index == 1.0


def test_matrix_diagnostic_reports_rank_duplicates_and_zero_variance() -> None:
    values = np.asarray([[1.0, 1.0, 5.0], [2.0, 2.0, 5.0], [3.0, 3.0, 5.0]])

    result = diagnose_design_matrix(values, ("first", "duplicate", "constant"))

    assert result.row_count == 3
    assert result.feature_count == 3
    assert result.rank == 2
    assert result.condition_number > 1e15
    assert result.duplicate_column_pairs == (("first", "duplicate"),)
    assert result.zero_variance_features == ("constant",)
    assert result.linear_dependencies
    assert result.all_finite is True


def test_matrix_diagnostic_rejects_non_finite_values() -> None:
    result = diagnose_design_matrix(np.asarray([[1.0], [np.nan]]), ("age",))

    assert result.all_finite is False


def test_matrix_diagnostic_reports_condition_number_for_full_rank_matrix() -> None:
    result = diagnose_design_matrix(np.eye(3), ("first", "second", "third"))

    assert result.rank == result.feature_count == 3
    assert result.condition_number == pytest.approx(1.0)
