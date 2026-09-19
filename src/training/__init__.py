"""Explicit model-training orchestrators; never imported by Streamlit startup."""

from .track_a import (
    FittedTrackABundle,
    PreparedTrackARun,
    TrackAFitStopped,
    evaluate_track_a_subset,
    fit_track_a,
    prepare_track_a_run,
)
from .track_b import (
    TRACK_B_CANDIDATES,
    PreparedTrackBRun,
    SelectedTrackBModel,
    finalize_track_b,
    prepare_track_b_run,
    select_track_b_candidate,
)
from .track_c import (
    PreparedTrackCRun,
    PreparedTrackCSelection,
    PreparedTrackCTest,
    SelectedTrackCModel,
    prepare_track_c_run,
    select_track_c_candidate,
    select_validation_winner,
)

__all__ = [
    "FittedTrackABundle",
    "PreparedTrackARun",
    "TrackAFitStopped",
    "evaluate_track_a_subset",
    "fit_track_a",
    "prepare_track_a_run",
    "TRACK_B_CANDIDATES",
    "PreparedTrackBRun",
    "SelectedTrackBModel",
    "prepare_track_b_run",
    "select_track_b_candidate",
    "finalize_track_b",
    "PreparedTrackCRun",
    "PreparedTrackCSelection",
    "PreparedTrackCTest",
    "SelectedTrackCModel",
    "prepare_track_c_run",
    "select_track_c_candidate",
    "select_validation_winner",
]
