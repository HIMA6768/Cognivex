"""Read-only extraction of frozen aggregate R5/R6/R7 evaluation evidence."""

from __future__ import annotations

import json
from pathlib import Path

from src.artifacts.inference_registry import R5_BUNDLE, R6_BUNDLE, R7_BUNDLE, _canonical, _checksums
from src.contracts.model_evaluation import (
    ClassificationMetricView,
    ModelEvaluationView,
    SurvivalMetricView,
)


def _json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("metric payload is malformed")
    return payload


def _number(payload: dict[str, object], *keys: str) -> float:
    value: object = payload
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise ValueError("metric payload is incomplete")
        value = value[key]
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError("metric value is invalid")
    return float(value)


def model_evaluation_artifact_file_state(repository_root: Path) -> dict[str, object]:
    """Return safe server-side evidence for aggregate-metric loading failures."""
    root = Path(repository_root).resolve()
    state: dict[str, object] = {}
    for label, relative in (("track_a", R5_BUNDLE), ("track_b", R6_BUNDLE), ("track_c", R7_BUNDLE)):
        bundle = root / relative
        metrics = bundle / "metrics.json"
        try:
            _checksums(bundle)
            verification: dict[str, object] = {"passed": True}
        except Exception as error:
            verification = {
                "passed": False,
                "exception_class": type(error).__name__,
                "exception_message": str(error),
            }
        state[label] = {
            "bundle": relative.as_posix(),
            "bundle_exists": bundle.is_dir(),
            "metrics_path": (relative / "metrics.json").as_posix(),
            "metrics_exists": metrics.is_file(),
            "metrics_size_bytes": metrics.stat().st_size if metrics.is_file() else None,
            "checksum_verification": verification,
        }
    return state


def read_frozen_model_evaluation(repository_root: Path) -> ModelEvaluationView:
    """Verify aggregate text bundles, then read frozen metrics without model deserialization."""
    root = Path(repository_root).resolve()
    r5_bundle = _canonical(root, R5_BUNDLE)
    r6_bundle = _canonical(root, R6_BUNDLE)
    r7_bundle = _canonical(root, R7_BUNDLE)
    _checksums(r5_bundle)
    _checksums(r6_bundle)
    _checksums(r7_bundle)

    r5 = _json(r5_bundle / "metrics.json")
    r6 = _json(r6_bundle / "metrics.json")
    r7 = _json(r7_bundle / "metrics.json")
    track_a_validation = _number(r5, "validation", "c_index")
    if track_a_validation != _number(r6, "track_a", "validation", "c_index"):
        raise ValueError("frozen Track A lineage metrics disagree")
    return ModelEvaluationView(
        track_a=SurvivalMetricView(
            validation_c_index=track_a_validation,
            test_c_index=_number(r6, "track_a", "test", "c_index"),
        ),
        track_b=SurvivalMetricView(
            validation_c_index=_number(r6, "track_b", "validation", "c_index"),
            test_c_index=_number(r6, "track_b", "test", "c_index"),
        ),
        track_c=ClassificationMetricView(
            test_macro_f1=_number(r7, "test", "macro_f1"),
            test_weighted_f1=_number(r7, "test", "weighted_f1"),
            test_accuracy=_number(r7, "test", "accuracy"),
            test_balanced_accuracy=_number(r7, "test", "balanced_accuracy"),
        ),
        validation_delta=_number(r6, "comparison", "validation_delta"),
        test_delta=_number(r6, "comparison", "test_delta"),
    )
