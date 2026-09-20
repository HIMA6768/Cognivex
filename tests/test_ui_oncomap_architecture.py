"""Architecture guards for the OncoMap presentation layer."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "src/ui"
FORBIDDEN_IMPORT_PREFIXES = (
    "src.artifacts",
    "src.inference",
    "src.preprocessing",
    "src.modeling",
    "src.training",
)
FORBIDDEN_DIRECT_MODEL_METHODS = {"fit", "fit_transform", "transform", "predict", "predict_proba"}


def test_oncomap_ui_uses_only_service_and_contract_boundaries() -> None:
    violations: list[str] = []
    paths = (
        ROOT / "src/ui/analysis_service.py",
        ROOT / "src/ui/navigation.py",
        ROOT / "src/ui/shell.py",
        *sorted((UI_ROOT / "components").glob("*.py")),
        *sorted((UI_ROOT / "pages").glob("*.py")),
    )
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(FORBIDDEN_IMPORT_PREFIXES):
                violations.append(f"{path}: forbidden import {node.module}")
            if isinstance(node, ast.Import) and any(alias.name.startswith(FORBIDDEN_IMPORT_PREFIXES) for alias in node.names):
                violations.append(f"{path}: forbidden import")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_DIRECT_MODEL_METHODS:
                violations.append(f"{path}: direct model method {node.func.attr}")
    assert violations == []
