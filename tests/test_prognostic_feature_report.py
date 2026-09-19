from __future__ import annotations

from pathlib import Path

import pytest

from src.analysis.prognostic_features import (
    build_genomic_feature_mapping,
    extract_prognostic_feature_effects,
)
from src.artifacts.prognostic_features import (
    render_prognostic_feature_report,
    verify_and_load_track_b_source,
)


@pytest.fixture(scope="module")
def report_text() -> str:
    root = Path(__file__).resolve().parents[1]
    source = verify_and_load_track_b_source(root / "artifacts/models/track_b/r6-track-b-v1", root)
    mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    result = extract_prognostic_feature_effects(source, mapping)
    metadata = {"source": {"experiment_id": "r6-track-b-v1"}}
    return render_prognostic_feature_report(result, metadata)


def test_report_contains_complete_sixty_eight_row_table_from_typed_records(report_text) -> None:
    rows = [line for line in report_text.splitlines() if line.startswith("| ")]
    data_rows = [line for line in rows if line.split("|")[1].strip().isdigit()]
    assert len(data_rows) == 68
    assert "r6-track-b-v1" in report_text


def test_report_templates_make_no_significance_claims(report_text) -> None:
    lower = report_text.lower()
    for prohibited in (
        "causes poor survival",
        "protective gene",
        "cancer driver",
        "true driver",
        "validated biomarker",
        "confirmed biomarker",
        "statistically significant feature",
    ):
        assert prohibited not in lower
    assert "model-associated" in lower
    assert "does not establish causality" in lower


def test_report_persists_expression_and_mutation_scale_limitations(report_text) -> None:
    lower = report_text.lower()
    assert "training-standardized expression unit" in lower
    assert "mutation presence versus absence" in lower
    assert "unscaled binary indicators" in lower
    assert "model-scale association ranking" in lower
