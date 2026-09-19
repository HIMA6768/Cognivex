"""Trusted local R5 artifact-bundle tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.artifacts.survival import load_trusted_pickle, write_track_a_artifacts
from tests.r5_helpers import make_track_a_result


def test_artifact_bundle_is_complete_checksummed_and_machine_readable(tmp_path: Path) -> None:
    result = make_track_a_result()

    records = write_track_a_artifacts(
        preprocessor={"kind": "preprocessor"},
        model={"kind": "cox"},
        result=result,
        output_root=tmp_path,
    )
    bundle = tmp_path / result.experiment_id

    assert {path.name for path in bundle.iterdir()} == {
        "experiment.json", "metrics.json", "coefficients.csv", "ph_diagnostics.csv",
        "preprocessor.pkl", "cox_model.pkl", "checksums.sha256",
    }
    assert json.loads((bundle / "experiment.json").read_text(encoding="utf-8"))["experiment_id"] == "r5-test"
    experiment_text = (bundle / "experiment.json").read_text(encoding="utf-8")
    assert "patient_id" not in experiment_text
    assert '"reference_category": "1"' in experiment_text
    checksum_lines = (bundle / "checksums.sha256").read_text(encoding="utf-8").splitlines()
    assert len(checksum_lines) == 6
    for line in checksum_lines:
        digest, name = line.split("  ", maxsplit=1)
        assert digest == hashlib.sha256((bundle / name).read_bytes()).hexdigest()
    assert {record.name for record in records} == {line.split("  ", 1)[1] for line in checksum_lines}


def test_pickle_loading_requires_explicit_trust(tmp_path: Path) -> None:
    result = make_track_a_result()
    write_track_a_artifacts({}, {}, result, tmp_path)
    path = tmp_path / result.experiment_id / "preprocessor.pkl"

    with pytest.raises(PermissionError, match="trusted=True"):
        load_trusted_pickle(path)

    assert load_trusted_pickle(path, trusted=True) == {}


def test_existing_non_empty_bundle_is_not_overwritten(tmp_path: Path) -> None:
    result = make_track_a_result()
    bundle = tmp_path / result.experiment_id
    bundle.mkdir()
    (bundle / "keep.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_track_a_artifacts({}, {}, result, tmp_path)

    assert (bundle / "keep.txt").read_text(encoding="utf-8") == "keep"
