from __future__ import annotations

from pathlib import Path

from src.services.analysis import AnalysisService


ROOT = Path(__file__).resolve().parents[1]


def test_r8_returns_all_ranked_effects_without_patient_input() -> None:
    outcome = AnalysisService.from_canonical_artifacts(ROOT).get_prognostic_feature_analysis()

    assert outcome.error is None
    assert outcome.view is not None
    assert len(outcome.view.effects) == 68
    assert tuple(effect.effect.rank for effect in outcome.view.effects) == tuple(range(1, 69))
