from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd

from src.contracts.inference import AnalysisRequest, FROZEN_SUBTYPE_CLASS_ORDER
from src.services.analysis import AnalysisService


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = (ROOT / "src/inference", ROOT / "src/services")
FORBIDDEN_IMPORT_PREFIXES = ("streamlit", "fastapi", "pydantic", "src.training")
FORBIDDEN_CALL_NAMES = {"fit", "fit_transform"}


def test_runtime_has_no_web_training_or_fit_calls() -> None:
    violations: list[str] = []
    for root in RUNTIME_ROOTS:
        for path in root.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) and any(alias.name.startswith(FORBIDDEN_IMPORT_PREFIXES) for alias in node.names):
                    violations.append(path.as_posix())
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(FORBIDDEN_IMPORT_PREFIXES):
                    violations.append(path.as_posix())
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_CALL_NAMES:
                    violations.append(path.as_posix())
    assert violations == []


def test_response_exposes_outputs_but_never_echoes_input_values(tmp_path, monkeypatch) -> None:
    service = AnalysisService.from_canonical_artifacts(ROOT)
    row = pd.read_csv(ROOT / "data/metabric/prepared/METABRIC_prepared.csv", nrows=1).iloc[0]
    values = {field: row[field] for field in service.allowed_input_fields}
    marker = "synthetic-secret-value"
    values["gata3"] = marker
    monkeypatch.chdir(tmp_path)
    response = service.analyze(AnalysisRequest(values))

    serialized = json.dumps(response.to_dict())
    assert marker not in serialized
    assert list(tmp_path.iterdir()) == []
    assert response.outcomes[0].result is not None
    assert response.outcomes[0].result.output_kind == "log_partial_hazard"
    assert response.outcomes[0].result.survival_estimates is not None
    assert response.outcomes[2].result is None or response.outcomes[2].result.predicted_class in FROZEN_SUBTYPE_CLASS_ORDER
