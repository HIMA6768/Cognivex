"""R10-B1 aggregate metric projection contracts."""

from __future__ import annotations

import logging
from pathlib import Path
import subprocess

from src.services.analysis import AnalysisService


ROOT = Path(__file__).resolve().parents[1]


def _lf_checkout(tmp_path: Path) -> Path:
    clone = tmp_path / "lf-checkout"
    subprocess.run(
        ["git", "clone", "--quiet", "--local", "--no-hardlinks", "--no-checkout", str(ROOT), str(clone)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "-C", str(clone), "config", "core.autocrlf", "false"], check=True)
    subprocess.run(["git", "-C", str(clone), "config", "core.eol", "lf"], check=True)
    subprocess.run(["git", "-C", str(clone), "checkout", "--quiet", "HEAD"], check=True)
    return clone


def test_analysis_service_exposes_checksum_verified_aggregate_model_metrics() -> None:
    assert hasattr(AnalysisService, "get_model_evaluation")

    outcome = AnalysisService.from_canonical_artifacts(ROOT).get_model_evaluation()

    assert outcome.error is None
    assert outcome.view is not None
    view = outcome.view
    assert view.track_a.validation_c_index == 0.6506960067491564
    assert view.track_a.test_c_index == 0.6249832999331998
    assert view.track_b.validation_c_index == 0.6445444319460067
    assert view.track_b.test_c_index == 0.6409151636606546
    assert view.validation_delta == -0.006151574803149651
    assert view.test_delta == 0.01593186372745481
    assert view.track_c.test_macro_f1 == 0.7341756697737162
    assert view.track_c.test_weighted_f1 == 0.7486418142369518
    assert view.track_c.test_accuracy == 0.7491166077738516
    assert view.track_c.test_balanced_accuracy == 0.7193732768127931


def test_model_evaluation_outcome_contains_aggregate_metrics_not_patient_outputs() -> None:
    assert hasattr(AnalysisService, "get_model_evaluation")

    outcome = AnalysisService.from_canonical_artifacts(ROOT).get_model_evaluation()

    assert outcome.error is None
    assert outcome.view is not None
    serialized = outcome.view.to_dict()
    assert "patient" not in str(serialized).lower()
    assert "prediction" not in str(serialized).lower()
    assert "probabilit" not in str(serialized).lower()


def test_checksum_failure_returns_a_safe_aggregate_unavailable_state(monkeypatch) -> None:
    from src.artifacts import model_evaluation

    monkeypatch.setattr(model_evaluation, "_checksums", lambda _bundle: (_ for _ in ()).throw(ValueError("corrupt")))

    outcome = AnalysisService.from_canonical_artifacts(ROOT).get_model_evaluation()

    assert outcome.view is None
    assert outcome.error is not None
    assert outcome.error.code == "ARTIFACT_UNAVAILABLE"
    assert "corrupt" not in outcome.error.message
    assert "artifacts" not in outcome.error.message.lower()


def test_model_evaluation_reads_verified_metrics_in_an_lf_style_checkout(tmp_path: Path) -> None:
    clean_root = _lf_checkout(tmp_path)

    outcome = AnalysisService.from_canonical_artifacts(clean_root).get_model_evaluation()

    assert outcome.error is None
    assert outcome.view is not None
    assert outcome.view.track_a.test_c_index == 0.6249832999331998
    assert outcome.view.track_b.test_c_index == 0.6409151636606546
    assert outcome.view.track_c.test_macro_f1 == 0.7341756697737162


def test_model_evaluation_failure_logs_safe_server_diagnostics(monkeypatch, caplog) -> None:
    import src.services.model_evaluation as service_module

    def fail(_root: Path):
        raise ValueError("simulated aggregate verification failure")

    monkeypatch.setattr(service_module, "read_frozen_model_evaluation", fail)
    with caplog.at_level(logging.ERROR, logger="src.services.model_evaluation"):
        outcome = service_module.get_frozen_model_evaluation(ROOT)

    assert outcome.error is not None
    assert "[ONCOMAP_MODEL_EVAL_ERROR]" in caplog.text
    assert "exception_class=ValueError" in caplog.text
    assert "simulated aggregate verification failure" in caplog.text
    assert "Traceback" in caplog.text
    assert "metrics.json" in caplog.text
    assert "checksum_verification" in caplog.text
