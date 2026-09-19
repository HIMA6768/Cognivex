from __future__ import annotations

import inspect
from pathlib import Path

from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

from src.data import load_track_c_feature_contract
from src.modeling.track_c import TRACK_C_CANDIDATES, build_track_c_candidate


ROOT = Path(__file__).resolve().parents[1]


def _candidate(key: str):
    return next(item for item in TRACK_C_CANDIDATES if item.key == key)


def _built(key: str):
    return build_track_c_candidate(_candidate(key), load_track_c_feature_contract(ROOT))


def test_candidate_registry_contains_exactly_four_families_in_frozen_order() -> None:
    assert tuple(item.key for item in TRACK_C_CANDIDATES) == (
        "logistic_regression",
        "random_forest",
        "gradient_boosting",
        "rbf_svm",
    )
    assert tuple(item.display_name for item in TRACK_C_CANDIDATES) == (
        "Logistic Regression",
        "Random Forest",
        "Gradient Boosting",
        "RBF SVM",
    )


def test_logistic_configuration_and_scaling_are_exact() -> None:
    pipeline = _built("logistic_regression")
    model = pipeline.named_steps["classifier"]

    assert isinstance(model, LogisticRegression)
    assert _candidate("logistic_regression").scale_expression is True
    assert {key: model.get_params()[key] for key in ("C", "class_weight", "max_iter", "random_state")} == {
        "C": 1.0,
        "class_weight": "balanced",
        "max_iter": 2000,
        "random_state": 42,
    }


def test_random_forest_configuration_and_unscaled_expression_are_exact() -> None:
    pipeline = _built("random_forest")
    model = pipeline.named_steps["classifier"]

    assert isinstance(model, RandomForestClassifier)
    assert _candidate("random_forest").scale_expression is False
    assert {key: model.get_params()[key] for key in ("n_estimators", "max_depth", "class_weight", "n_jobs", "random_state")} == {
        "n_estimators": 200,
        "max_depth": 8,
        "class_weight": "balanced",
        "n_jobs": -1,
        "random_state": 42,
    }


def test_gradient_boosting_configuration_and_unscaled_expression_are_exact() -> None:
    model = _built("gradient_boosting").named_steps["classifier"]

    assert isinstance(model, GradientBoostingClassifier)
    assert _candidate("gradient_boosting").scale_expression is False
    assert {key: model.get_params()[key] for key in ("n_estimators", "max_depth", "learning_rate", "random_state")} == {
        "n_estimators": 150,
        "max_depth": 4,
        "learning_rate": 0.1,
        "random_state": 42,
    }


def test_rbf_svm_configuration_probability_and_scaling_are_exact() -> None:
    model = _built("rbf_svm").named_steps["classifier"]

    assert isinstance(model, SVC)
    assert _candidate("rbf_svm").scale_expression is True
    assert {key: model.get_params()[key] for key in ("C", "kernel", "probability", "class_weight", "random_state")} == {
        "C": 1.0,
        "kernel": "rbf",
        "probability": True,
        "class_weight": "balanced",
        "random_state": 42,
    }


def test_all_supported_random_states_are_42_and_factory_is_deterministic() -> None:
    for definition in TRACK_C_CANDIDATES:
        first = build_track_c_candidate(definition, load_track_c_feature_contract(ROOT))
        second = build_track_c_candidate(definition, load_track_c_feature_contract(ROOT))
        assert first.named_steps["classifier"].get_params() == second.named_steps["classifier"].get_params()
        assert first.named_steps["classifier"].get_params()["random_state"] == 42


def test_track_c_model_module_has_no_lifelines_or_survival_import() -> None:
    import src.modeling.track_c as module

    source = inspect.getsource(module)
    assert "lifelines" not in source
    assert "survival" not in source.lower()
