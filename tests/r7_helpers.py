from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.contracts import TrackCExclusionSummary
from src.data import TRACK_C_CLASS_ORDER, OrderedTrackCSplit, load_track_c_feature_contract, ordered_patient_fingerprint
from src.modeling.track_c import TRACK_C_CANDIDATES
from src.training.track_c import (
    PreparedTrackCRun,
    PreparedTrackCSelection,
    PreparedTrackCTest,
    finalize_track_c,
    select_track_c_candidate,
)


ROOT = Path(__file__).resolve().parents[1]


def _split(name: str, rows: int, offset: int):
    contract = load_track_c_feature_contract(ROOT)
    patient_ids = tuple(f"{name}-{index}" for index in range(rows))
    data: dict[str, object] = {}
    for feature_index, feature in enumerate(contract.expression_features):
        data[feature] = [float((feature_index + row + offset) % 11) for row in range(rows)]
    for feature_index, feature in enumerate(contract.mutation_features):
        data[feature] = ["E883K" if (row + feature_index + offset) % 7 == 0 else "0" for row in range(rows)]
    predictors = pd.DataFrame(data, index=pd.Index(patient_ids, name="patient_id"))
    targets = pd.Series(
        np.resize(np.asarray(TRACK_C_CLASS_ORDER, dtype=object), rows),
        index=predictors.index,
        name="pam50_+_claudin-low_subtype",
    )
    return OrderedTrackCSplit(
        split=name,
        patient_ids=patient_ids,
        predictors=predictors,
        targets=targets,
        exclusions=TrackCExclusionSummary(name, rows, rows, 0, 0, 0),
        fingerprint=ordered_patient_fingerprint(patient_ids),
    )


def make_synthetic_track_c_run():
    contract = load_track_c_feature_contract(ROOT)
    train = _split("train", 36, 0)
    validation = _split("validation", 18, 2)
    test = _split("test", 18, 4)
    selection_data = PreparedTrackCSelection(contract, train, validation)
    selected = select_track_c_candidate(selection_data, candidates=(TRACK_C_CANDIDATES[0],))
    prepared = PreparedTrackCRun(
        selection=selection_data,
        test=PreparedTrackCTest(test),
        prepared_sha256="a" * 64,
        manifest_sha256="b" * 64,
        repository_root=ROOT,
    )
    result = finalize_track_c(selected, prepared.test, experiment_id="r7-synthetic")
    return prepared, selected, result
