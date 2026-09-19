from __future__ import annotations

import copy
import inspect
from pathlib import Path

import pytest

from src.artifacts import prognostic_features as source_module
from src.artifacts.prognostic_features import (
    R6_BUNDLE_RELATIVE,
    verify_and_load_track_b_source,
)

from r8_helpers import make_r8_source_fixture, replace_json


def _patch_valid_loaders(monkeypatch: pytest.MonkeyPatch, fixture) -> list[Path]:
    calls: list[Path] = []

    def loader(path: Path, *, trusted: bool = False):
        assert trusted is True
        calls.append(Path(path))
        return fixture.preprocessor if Path(path).name == "preprocessor.pkl" else fixture.model

    monkeypatch.setattr(source_module, "verify_frozen_r6_tracked_state", lambda root: None)
    monkeypatch.setattr(source_module, "load_trusted_pickle", loader)
    return calls


def test_canonical_verified_bundle_loads_after_all_preload_checks(tmp_path, monkeypatch) -> None:
    fixture = make_r8_source_fixture(tmp_path)
    calls = _patch_valid_loaders(monkeypatch, fixture)
    verified = verify_and_load_track_b_source(fixture.bundle, fixture.repository_root)
    assert calls == [fixture.bundle / "preprocessor.pkl", fixture.bundle / "cox_model.pkl"]
    assert verified.bundle == fixture.bundle.resolve()
    assert len(verified.model_feature_names) == 80
    assert verified.model_feature_names == tuple(verified.feature_contract["model_feature_names"])


def test_alternate_source_bundle_path_is_rejected(tmp_path, monkeypatch) -> None:
    fixture = make_r8_source_fixture(tmp_path)
    calls = _patch_valid_loaders(monkeypatch, fixture)
    alternate = tmp_path / "alternate"
    alternate.mkdir()
    with pytest.raises(ValueError, match="canonical R6 bundle"):
        verify_and_load_track_b_source(alternate, fixture.repository_root)
    assert calls == []


def test_checksum_failure_prevents_pickle_loader_call(tmp_path, monkeypatch) -> None:
    fixture = make_r8_source_fixture(tmp_path)
    calls: list[Path] = []
    monkeypatch.setattr(source_module, "verify_frozen_r6_tracked_state", lambda root: None)
    monkeypatch.setattr(
        source_module,
        "load_trusted_pickle",
        lambda path, *, trusted=False: calls.append(Path(path)),
    )
    (fixture.bundle / "metadata.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        verify_and_load_track_b_source(fixture.bundle, fixture.repository_root)
    assert calls == []


def test_wrong_experiment_or_task_identity_is_rejected(tmp_path, monkeypatch) -> None:
    fixture = make_r8_source_fixture(tmp_path)
    calls = _patch_valid_loaders(monkeypatch, fixture)
    replace_json(fixture.bundle, "metadata.json", lambda data: data.update(experiment_id="wrong"))
    with pytest.raises(ValueError, match="experiment"):
        verify_and_load_track_b_source(fixture.bundle, fixture.repository_root)
    assert calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    (("penalizer", 0.1), ("l1_ratio", 1.0)),
)
def test_wrong_penalizer_l1_ratio_alpha_or_baseline_is_rejected(
    tmp_path, monkeypatch, field, value
) -> None:
    fixture = make_r8_source_fixture(tmp_path)
    calls = _patch_valid_loaders(monkeypatch, fixture)
    replace_json(
        fixture.bundle,
        "metadata.json",
        lambda data: data["selected_configuration"].update({field: value}),
    )
    with pytest.raises(ValueError, match=field):
        verify_and_load_track_b_source(fixture.bundle, fixture.repository_root)
    assert calls == []


def test_wrong_adapter_type_or_unfitted_adapter_is_rejected(tmp_path, monkeypatch) -> None:
    fixture = make_r8_source_fixture(tmp_path)
    calls = _patch_valid_loaders(monkeypatch, fixture)
    monkeypatch.setattr(
        source_module,
        "load_trusted_pickle",
        lambda path, *, trusted=False: fixture.preprocessor if Path(path).name == "preprocessor.pkl" else object(),
    )
    with pytest.raises(TypeError, match="PenalizedCoxPHAdapter"):
        verify_and_load_track_b_source(fixture.bundle, fixture.repository_root)

    unfitted = copy.deepcopy(fixture.model)
    unfitted._fitted = False
    monkeypatch.setattr(
        source_module,
        "load_trusted_pickle",
        lambda path, *, trusted=False: fixture.preprocessor if Path(path).name == "preprocessor.pkl" else unfitted,
    )
    with pytest.raises(ValueError, match="fitted"):
        verify_and_load_track_b_source(fixture.bundle, fixture.repository_root)


def test_wrong_preprocessor_type_is_rejected(tmp_path, monkeypatch) -> None:
    fixture = make_r8_source_fixture(tmp_path)
    _patch_valid_loaders(monkeypatch, fixture)
    monkeypatch.setattr(
        source_module,
        "load_trusted_pickle",
        lambda path, *, trusted=False: object() if Path(path).name == "preprocessor.pkl" else fixture.model,
    )
    with pytest.raises(TypeError, match="Pipeline"):
        verify_and_load_track_b_source(fixture.bundle, fixture.repository_root)


def test_engineer_pickle_path_is_rejected(tmp_path, monkeypatch) -> None:
    fixture = make_r8_source_fixture(tmp_path)
    calls = _patch_valid_loaders(monkeypatch, fixture)
    engineer = fixture.repository_root / "cognivex_ml" / "models"
    engineer.mkdir(parents=True)
    with pytest.raises(ValueError, match="canonical R6 bundle"):
        verify_and_load_track_b_source(engineer, fixture.repository_root)
    assert calls == []


def test_source_verifier_imports_no_training_or_engineer_module() -> None:
    text = inspect.getsource(source_module)
    assert "src.training" not in text
    assert "cognivex_ml" not in text
    assert R6_BUNDLE_RELATIVE == Path("artifacts/models/track_b/r6-track-b-v1")
