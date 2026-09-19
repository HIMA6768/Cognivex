"""R6-P0 read-only engineer handoff compatibility tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from src.data.engineer_compatibility import (
    audit_expression_features,
    audit_mutation_features,
    audit_repository,
    compare_selected_features,
    parse_selected_features,
    scan_python_sources,
    write_audit_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_selected_features_parse_in_source_order_and_partition_by_suffix(tmp_path: Path) -> None:
    selected = tmp_path / "selected_features.txt"
    selected.write_text("gene_b\ngene_a\ntp53_mut\n", encoding="utf-8")

    contract = parse_selected_features(selected)

    assert contract.all_features == ("gene_b", "gene_a", "tp53_mut")
    assert contract.expression_features == ("gene_b", "gene_a")
    assert contract.mutation_features == ("tp53_mut",)


def test_selected_features_reject_duplicate_names(tmp_path: Path) -> None:
    selected = tmp_path / "selected_features.txt"
    selected.write_text("gene_a\ngene_a\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate selected features: gene_a"):
        parse_selected_features(selected)


def test_feature_comparison_reports_exact_missing_names_and_alias_candidates(tmp_path: Path) -> None:
    selected = tmp_path / "selected_features.txt"
    selected.write_text("gene_a\ngene_b\ntp53_mut\n", encoding="utf-8")
    contract = parse_selected_features(selected)

    result = compare_selected_features(("gene_a", "TP53_MUT", "unnamed:_0"), contract)

    assert result.expression_present == ("gene_a",)
    assert result.expression_missing == ("gene_b",)
    assert result.mutation_present == ()
    assert result.mutation_missing == ("tp53_mut",)
    assert result.alias_candidates == (("tp53_mut", "TP53_MUT"),)
    assert result.suspicious_index_columns == ("unnamed:_0",)


def test_mutation_audit_distinguishes_direct_binary_from_annotation_strings() -> None:
    frame = pd.DataFrame(
        {
            "numeric_mut": [0, 1, 0],
            "boolean_mut": [False, True, False],
            "annotation_mut": ["0", "H1047R", "0"],
        }
    )

    results = {
        item.feature: item
        for item in audit_mutation_features(
            frame,
            ("numeric_mut", "boolean_mut", "annotation_mut"),
        )
    }

    assert results["numeric_mut"].representation == "binary_numeric_0_1"
    assert results["numeric_mut"].directly_usable_as_binary is True
    assert results["boolean_mut"].representation == "boolean"
    assert results["boolean_mut"].directly_usable_as_binary is True
    assert results["annotation_mut"].representation == "mutation_annotation_string"
    assert results["annotation_mut"].directly_usable_as_binary is False
    assert results["annotation_mut"].unique_values_preview == ("0", "H1047R")


def test_expression_audit_reports_numeric_quality_without_transforming_values() -> None:
    frame = pd.DataFrame(
        {
            "usable": [1.0, 2.0, 3.0],
            "constant": [5.0, 5.0, 5.0],
            "text": ["1", "2", "bad"],
        }
    )
    before = frame.copy(deep=True)

    results = {
        item.feature: item
        for item in audit_expression_features(frame, ("usable", "constant", "text"))
    }

    assert results["usable"].compatible is True
    assert results["constant"].constant is True
    assert results["constant"].compatible is False
    assert results["text"].numeric_dtype is False
    assert results["text"].compatible is False
    pd.testing.assert_frame_equal(frame, before)


def test_python_source_scan_never_executes_engineer_entrypoints(tmp_path: Path) -> None:
    marker = tmp_path / "executed.txt"
    source = tmp_path / "engineer_script.py"
    source.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed')\n"
        "from sklearn.preprocessing import StandardScaler\n"
        "StandardScaler().fit_transform([[1], [2]])\n",
        encoding="utf-8",
    )

    scan = scan_python_sources((source,))

    assert marker.exists() is False
    assert scan.import_roots == ("pathlib", "sklearn")
    assert scan.fit_calls == (("engineer_script.py", 4, "fit_transform"),)


def test_canonical_audit_is_reproducible_and_preserves_r2_to_r5_files(tmp_path: Path) -> None:
    protected = (
        ROOT / "data" / "metabric" / "prepared" / "METABRIC_prepared.csv",
        ROOT / "data" / "metabric" / "metadata" / "manifest.csv",
        ROOT / "src" / "training" / "track_a.py",
        ROOT / "src" / "modeling" / "survival.py",
        ROOT / "artifacts" / "models" / "track_a" / "r5a-track-a-baseline-v1" / "experiment.json",
    )
    before = {path: _sha256(path) for path in protected}

    first = audit_repository(ROOT, engineer_source_ref="origin/anay/prediction_pipelines")
    second = audit_repository(ROOT, engineer_source_ref="origin/anay/prediction_pipelines")
    json_path, markdown_path = write_audit_artifacts(first, tmp_path)

    assert first == second
    assert first["status"] == "PASS"
    assert first["active_dataset"]["patient_count"] == 1904
    assert first["active_dataset"]["column_count"] == 693
    assert first["active_split"] == {"train": 1332, "validation": 286, "test": 286}
    assert first["selected_feature_contract"]["expression_count"] == 50
    assert first["selected_feature_contract"]["mutation_count"] == 18
    assert first["feature_compatibility"]["expression_present_count"] == 50
    assert first["feature_compatibility"]["mutation_present_count"] == 18
    assert first["feature_compatibility"]["expression_missing"] == []
    assert first["feature_compatibility"]["mutation_missing"] == []
    assert first["mutation_encoding"]["direct_binary_count"] == 0
    assert first["mutation_encoding"]["requires_transformation_count"] == 18
    assert first["mutation_encoding"]["approved_track_b_policy"] == {
        "approved": True,
        "source_annotations_immutable": True,
        "implementation_contract": "src.preprocessing.mutations.classify_mutation_annotation",
        "absence_rule": "trimmed numeric zero -> 0",
        "presence_rule": "valid non-zero annotation -> 1",
        "missing_rule": "fail clearly; do not impute or coerce",
        "malformed_rule": "fail clearly; do not coerce to mutation-present",
        "fit_statistics_required": False,
        "same_transform_for_train_validation_test": True,
    }
    assert first["blockers"] == []
    assert first["recommendation"] == "READY FOR R6 TRACK B"
    assert json.loads(json_path.read_text(encoding="utf-8"))["status"] == "PASS"
    assert "No new model was trained" in markdown_path.read_text(encoding="utf-8")
    assert {path: _sha256(path) for path in protected} == before


def test_audit_script_runs_directly_and_writes_only_requested_reports(tmp_path: Path) -> None:
    output = tmp_path / "audit"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/audit_engineer_compatibility.py",
            "--output-directory",
            str(output),
            "--engineer-source-ref",
            "origin/anay/prediction_pipelines",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "PASS"
    assert payload["recommendation"] == "READY FOR R6 TRACK B"
    assert {path.name for path in output.iterdir()} == {
        "engineer_compatibility_report.json",
        "engineer_compatibility_report.md",
    }


def test_imported_engineer_pickle_artifacts_are_gitignored() -> None:
    pickle_paths = sorted((ROOT / "cognivex_ml" / "models").glob("*.pkl"))
    assert pickle_paths

    for path in pickle_paths:
        completed = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, f"engineer model artifact is not ignored: {path.name}"
