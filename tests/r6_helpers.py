"""Shared real-model R6 test fixture."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from src.contracts import TrackBHyperparameters
from src.data.metabric import MetabricPaths
from src.training.track_b import finalize_track_b, prepare_track_b_run, select_track_b_candidate


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def make_single_candidate_track_b_run():
    prepared = prepare_track_b_run(MetabricPaths.from_repository_root(ROOT))
    selection = select_track_b_candidate(
        prepared,
        candidates=(TrackBHyperparameters(0.1, 0.0),),
    )
    result = finalize_track_b(
        selection,
        prepared,
        experiment_id="r6-test-bundle",
        r5_artifact_root=(
            ROOT / "artifacts" / "models" / "track_a" / "r5a-track-a-baseline-v1"
        ),
    )
    return prepared, selection, result

