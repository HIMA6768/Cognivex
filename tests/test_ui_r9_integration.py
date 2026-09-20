from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd

from src.contracts.inference import AnalysisTrack, TrackReadinessState
from src.ui.analysis_service import get_analysis_service
from src.ui.components.analysis import submit_track_request


ROOT = Path(__file__).resolve().parents[1]


def test_ui_request_boundary_returns_actual_frozen_r9_track_outputs() -> None:
    service = get_analysis_service(ROOT)
    row = pd.read_csv(ROOT / "data/metabric/prepared/METABRIC_prepared.csv", nrows=1).iloc[0]
    for track, entry in (
        (AnalysisTrack.TRACK_A, service.registry.track_a),
        (AnalysisTrack.TRACK_B, service.registry.track_b),
        (AnalysisTrack.TRACK_C, service.registry.track_c),
    ):
        response = submit_track_request(service, track, {field: row[field] for field in entry.required_fields})
        outcome = response.outcomes[0]
        assert outcome.state is TrackReadinessState.READY
        assert outcome.result is not None


def test_ui_r8_boundary_exposes_only_the_complete_global_effect_table() -> None:
    outcome = get_analysis_service(ROOT).get_prognostic_feature_analysis()
    assert outcome.error is None
    assert outcome.view is not None
    assert len(outcome.view.effects) == 68


def test_ui_modules_use_only_r9_service_boundary_not_model_or_artifact_loaders() -> None:
    prohibited_prefixes = ("src.artifacts", "src.inference", "src.preprocessing", "src.modeling")
    for path in (
        ROOT / "src/ui/analysis_service.py",
        ROOT / "src/ui/components/analysis.py",
        ROOT / "src/ui/pages/survival_analysis.py",
        ROOT / "src/ui/pages/subtype_classification.py",
        ROOT / "src/ui/pages/gene_insights.py",
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(prohibited_prefixes), path
            if isinstance(node, ast.Import):
                assert not any(alias.name.startswith(prohibited_prefixes) for alias in node.names), path
