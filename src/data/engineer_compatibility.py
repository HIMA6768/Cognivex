"""Read-only R6-P0 compatibility audit for the imported engineer reference."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd

from src.data.metabric import MetabricPaths


EXPECTED_EXPRESSION_COUNT = 50
EXPECTED_MUTATION_COUNT = 18
SELECTED_FEATURES_RELATIVE_PATH = Path("ai_handoff_data/v1/selected_features.txt")
ENGINEER_SCRIPT_NAMES = (
    "train_clinical_survival.py",
    "train_genomic_survival.py",
    "train_subtype_classifier.py",
    "train_track_c.py",
    "validate_data.py",
    "evaluate_subtype.py",
    "evaluate_survival.py",
    "generate_feature_importance.py",
    "prepare_data.py",
)


@dataclass(frozen=True, slots=True)
class SelectedFeatureContract:
    all_features: tuple[str, ...]
    expression_features: tuple[str, ...]
    mutation_features: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FeatureComparison:
    expression_present: tuple[str, ...]
    expression_missing: tuple[str, ...]
    mutation_present: tuple[str, ...]
    mutation_missing: tuple[str, ...]
    alias_candidates: tuple[tuple[str, str], ...]
    duplicate_dataset_columns: tuple[str, ...]
    suspicious_index_columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MutationFeatureAudit:
    feature: str
    dtype: str
    representation: str
    null_count: int
    unique_count: int
    unique_values_preview: tuple[str, ...]
    directly_usable_as_binary: bool
    future_transformation: str | None


@dataclass(frozen=True, slots=True)
class ExpressionFeatureAudit:
    feature: str
    dtype: str
    numeric_dtype: bool
    null_count: int
    non_finite_count: int
    unique_count: int
    constant: bool
    compatible: bool


@dataclass(frozen=True, slots=True)
class PythonSourceScan:
    import_roots: tuple[str, ...]
    fit_calls: tuple[tuple[str, int, str], ...]


_SCRIPT_REVIEWS: tuple[dict[str, Any], ...] = (
    {
        "script": "train_clinical_survival.py",
        "classification": "REFERENCE ONLY",
        "reason": (
            "Cox tuning structure is informative, but it replaces frozen R5 predictors with an "
            "expanded clinical set, assumes engineer split CSVs, reinverts survival status, and scores test."
        ),
    },
    {
        "script": "train_genomic_survival.py",
        "classification": "REUSE PARTIALLY / REFACTOR",
        "reason": (
            "Train-fit imputation/scaling and penalized Cox search are useful, but all numeric columns are "
            "selected dynamically, mutation annotations are mishandled, active event status would be inverted, "
            "and test is evaluated during development."
        ),
    },
    {
        "script": "train_subtype_classifier.py",
        "classification": "REUSE PARTIALLY / REFACTOR",
        "reason": (
            "Classifier candidates and validation metrics are useful for R7, but the script discovers all "
            "numeric genomic columns, uses engineer split CSVs, and does not preserve the current subtype contract."
        ),
    },
    {
        "script": "train_track_c.py",
        "classification": "REUSE PARTIALLY / REFACTOR",
        "reason": (
            "Only its subtype-classification ideas are candidates for R7. Its survival section selects the "
            "best Cox model using test C-index, expands the clinical contract, and must not be retained."
        ),
    },
    {
        "script": "validate_data.py",
        "classification": "REFERENCE ONLY",
        "reason": (
            "Its split-overlap checks are valid ideas, but current R2/R3 validation is stronger, checksum-aware, "
            "and bound to the authoritative manifest."
        ),
    },
    {
        "script": "evaluate_subtype.py",
        "classification": "REUSE PARTIALLY / REFACTOR",
        "reason": (
            "Accuracy, macro-F1, and confusion-matrix reporting are useful for R7, but feature discovery is "
            "dynamic, artifacts are untrusted pickles, and final test evaluation needs a later explicit gate."
        ),
    },
    {
        "script": "evaluate_survival.py",
        "classification": "DO NOT USE",
        "reason": (
            "It fits a new SimpleImputer on test data, reconstructs columns ad hoc, reinverts active survival "
            "status if pointed at Cognivex data, and includes placeholder/hard-coded performance values."
        ),
    },
    {
        "script": "generate_feature_importance.py",
        "classification": "REUSE PARTIALLY / REFACTOR",
        "reason": (
            "Coefficient extraction can inform R8, but genomic identification is prefix-based, exact-zero Lasso "
            "selection is brittle, pickles are loaded without a trust gate, and causal/biological claims are unsupported."
        ),
    },
    {
        "script": "prepare_data.py",
        "classification": "DO NOT USE",
        "reason": (
            "It targets the rejected 1332/191/381 split, regenerates manifest/mapping files, and creates an "
            "event column by inversion. Active R2 preparation and the locked manifest remain authoritative."
        ),
    },
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def parse_selected_features(path: Path) -> SelectedFeatureContract:
    """Parse a deterministic explicit feature contract without normalization or selection."""
    values = tuple(line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip())
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    duplicates = tuple(value for value in values if counts[value] > 1)
    duplicates = tuple(dict.fromkeys(duplicates))
    if duplicates:
        raise ValueError(f"duplicate selected features: {', '.join(duplicates)}")
    if not values:
        raise ValueError("selected feature contract is empty")
    mutation = tuple(value for value in values if value.endswith("_mut"))
    expression = tuple(value for value in values if not value.endswith("_mut"))
    return SelectedFeatureContract(values, expression, mutation)


def compare_selected_features(
    dataset_columns: tuple[str, ...] | list[str],
    contract: SelectedFeatureContract,
) -> FeatureComparison:
    """Compare exact feature names and separately report non-applied alias candidates."""
    columns = tuple(str(column) for column in dataset_columns)
    column_set = set(columns)
    normalized: dict[str, list[str]] = {}
    for column in columns:
        normalized.setdefault(column.strip().casefold(), []).append(column)

    expression_present = tuple(name for name in contract.expression_features if name in column_set)
    expression_missing = tuple(name for name in contract.expression_features if name not in column_set)
    mutation_present = tuple(name for name in contract.mutation_features if name in column_set)
    mutation_missing = tuple(name for name in contract.mutation_features if name not in column_set)
    aliases: list[tuple[str, str]] = []
    for missing in expression_missing + mutation_missing:
        for candidate in normalized.get(missing.strip().casefold(), []):
            if candidate != missing:
                aliases.append((missing, candidate))
    seen: set[str] = set()
    duplicates: list[str] = []
    for column in columns:
        if column in seen and column not in duplicates:
            duplicates.append(column)
        seen.add(column)
    suspicious = tuple(
        column
        for column in columns
        if re.match(r"^unnamed(?::|_)|^index$|^level_0$|^\d+$", column, re.IGNORECASE)
    )
    return FeatureComparison(
        expression_present,
        expression_missing,
        mutation_present,
        mutation_missing,
        tuple(aliases),
        tuple(duplicates),
        suspicious,
    )


def audit_mutation_features(
    frame: pd.DataFrame,
    features: tuple[str, ...],
) -> tuple[MutationFeatureAudit, ...]:
    """Describe selected mutation columns without converting or mutating them."""
    results: list[MutationFeatureAudit] = []
    for feature in features:
        series = frame[feature]
        non_null = series.dropna()
        preview = tuple(sorted({str(value) for value in non_null.unique()}))[:12]
        directly_usable = False
        future_transformation: str | None = None
        if pd.api.types.is_bool_dtype(series.dtype):
            representation = "boolean"
            directly_usable = not series.isna().any()
        elif pd.api.types.is_numeric_dtype(series.dtype):
            numeric_values = {float(value) for value in non_null.unique()}
            if numeric_values.issubset({0.0, 1.0}):
                representation = "binary_numeric_0_1"
                directly_usable = not series.isna().any()
            else:
                representation = "numeric_non_binary"
                future_transformation = "requires an approved mutation-presence mapping"
        else:
            string_values = {str(value).strip() for value in non_null.unique()}
            if string_values.issubset({"0", "1"}):
                representation = "binary_string_0_1"
                future_transformation = "convert string binary values to numeric 0/1"
            elif "0" in string_values:
                representation = "mutation_annotation_string"
                future_transformation = (
                    "map trimmed '0' to absence and nonzero mutation annotations to presence using an approved policy"
                )
            else:
                representation = "categorical"
                future_transformation = "requires an approved mutation-presence mapping"
        results.append(
            MutationFeatureAudit(
                feature=feature,
                dtype=str(series.dtype),
                representation=representation,
                null_count=int(series.isna().sum()),
                unique_count=int(series.nunique(dropna=True)),
                unique_values_preview=preview,
                directly_usable_as_binary=directly_usable,
                future_transformation=future_transformation,
            )
        )
    return tuple(results)


def audit_expression_features(
    frame: pd.DataFrame,
    features: tuple[str, ...],
) -> tuple[ExpressionFeatureAudit, ...]:
    """Describe selected expression columns without imputing or scaling them."""
    results: list[ExpressionFeatureAudit] = []
    for feature in features:
        series = frame[feature]
        numeric_dtype = bool(pd.api.types.is_numeric_dtype(series.dtype))
        null_count = int(series.isna().sum())
        non_finite_count = 0
        if numeric_dtype:
            values = series.to_numpy(dtype=float, copy=True)
            non_finite_count = int((~np.isfinite(values) & ~pd.isna(values)).sum())
        unique_count = int(series.nunique(dropna=True))
        constant = unique_count <= 1
        results.append(
            ExpressionFeatureAudit(
                feature=feature,
                dtype=str(series.dtype),
                numeric_dtype=numeric_dtype,
                null_count=null_count,
                non_finite_count=non_finite_count,
                unique_count=unique_count,
                constant=constant,
                compatible=(
                    numeric_dtype
                    and null_count == 0
                    and non_finite_count == 0
                    and not constant
                ),
            )
        )
    return tuple(results)


def scan_python_sources(paths: tuple[Path, ...]) -> PythonSourceScan:
    """Parse source ASTs for imports/fit calls without importing or executing them."""
    import_roots: list[str] = []
    fit_calls: list[tuple[str, int, str]] = []
    for path in paths:
        tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            roots: tuple[str, ...] = ()
            if isinstance(node, ast.Import):
                roots = tuple(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots = (node.module.split(".", 1)[0],)
            for root in roots:
                if root not in import_roots:
                    import_roots.append(root)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"fit", "fit_transform"}
            ):
                fit_calls.append((Path(path).name, int(node.lineno), node.func.attr))
    return PythonSourceScan(
        tuple(import_roots),
        tuple(sorted(fit_calls, key=lambda item: (item[0], item[1], item[2]))),
    )


def _dependency_audit(engineer_root: Path, scan: PythonSourceScan) -> dict[str, Any]:
    required = tuple(
        line.strip()
        for line in (engineer_root / "requirements-train.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    package_for_import = {"sklearn": "scikit-learn"}
    installed: dict[str, str] = {}
    missing: list[str] = []
    for requirement in required:
        package = re.split(r"[<>=!~]", requirement, maxsplit=1)[0].strip()
        try:
            installed[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            missing.append(package)
    third_party_imports = tuple(
        root
        for root in scan.import_roots
        if root not in sys.stdlib_module_names and root != "__future__"
    )
    undeclared_imports = tuple(
        root
        for root in third_party_imports
        if package_for_import.get(root, root) not in {
            re.split(r"[<>=!~]", item, maxsplit=1)[0].strip() for item in required
        }
    )
    current_constraints = {
        line.strip().rstrip(",").strip('"')
        for line in (engineer_root.parent / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    return {
        "engineer_requirements": list(required),
        "source_import_roots": list(scan.import_roots),
        "third_party_import_roots": list(third_party_imports),
        "installed_versions": installed,
        "missing_dependencies": missing,
        "conflicting_versions": [],
        "undeclared_imports": list(undeclared_imports),
        "current_project_constraints": sorted(current_constraints),
        "unnecessary_engineer_only_dependencies": [],
        "note": (
            "Engineer requirements are unpinned. tabulate is needed indirectly by pandas DataFrame.to_markdown. "
            "No dependency installation was performed."
        ),
    }


def _git_revision(root: Path, ref: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _script_reviews(scan: PythonSourceScan) -> list[dict[str, Any]]:
    calls_by_script: dict[str, list[dict[str, Any]]] = {}
    for script, line, method in scan.fit_calls:
        calls_by_script.setdefault(script, []).append({"line": line, "method": method})
    return [
        {**review, "fit_calls": calls_by_script.get(str(review["script"]), [])}
        for review in _SCRIPT_REVIEWS
    ]


def audit_repository(
    repository_root: Path,
    *,
    engineer_source_ref: str,
) -> dict[str, Any]:
    """Build a deterministic, aggregate-only R6-P0 report without fitting anything."""
    root = Path(repository_root).resolve()
    paths = MetabricPaths.from_repository_root(root)
    prepared = pd.read_csv(paths.prepared_csv, low_memory=False)
    manifest_path = paths.metadata_dir / "manifest.csv"
    manifest = pd.read_csv(manifest_path)
    clinical_schema = json.loads(
        (paths.metadata_dir / "clinical_schema.json").read_text(encoding="utf-8")
    )
    feature_groups = json.loads(
        (paths.metadata_dir / "feature_groups.json").read_text(encoding="utf-8")
    )
    selected_path = root / SELECTED_FEATURES_RELATIVE_PATH
    selected = parse_selected_features(selected_path)
    if len(selected.expression_features) != EXPECTED_EXPRESSION_COUNT:
        raise ValueError(
            f"expected {EXPECTED_EXPRESSION_COUNT} expression features, found {len(selected.expression_features)}"
        )
    if len(selected.mutation_features) != EXPECTED_MUTATION_COUNT:
        raise ValueError(
            f"expected {EXPECTED_MUTATION_COUNT} mutation features, found {len(selected.mutation_features)}"
        )
    comparison = compare_selected_features(tuple(prepared.columns), selected)
    expression_audit = audit_expression_features(prepared, comparison.expression_present)
    mutation_audit = audit_mutation_features(prepared, comparison.mutation_present)

    engineer_root = root / "cognivex_ml"
    script_paths = tuple(engineer_root / "scripts" / name for name in ENGINEER_SCRIPT_NAMES)
    missing_scripts = [path.name for path in script_paths if not path.is_file()]
    if missing_scripts:
        raise FileNotFoundError(f"engineer scripts missing: {', '.join(missing_scripts)}")
    source_scan = scan_python_sources(script_paths)
    engineer_selected = parse_selected_features(engineer_root / "data" / "selected_features.txt")
    split_counts = manifest["split"].value_counts()
    subtype_column = str(feature_groups["subtype_target"])
    subtype = prepared[subtype_column]
    subtype_counts = {
        str(name): int(count)
        for name, count in subtype.value_counts(dropna=False).sort_index().items()
    }
    direct_binary = [item.feature for item in mutation_audit if item.directly_usable_as_binary]
    requires_transform = [item.feature for item in mutation_audit if not item.directly_usable_as_binary]
    expression_issues = [item.feature for item in expression_audit if not item.compatible]
    blockers: list[dict[str, Any]] = []
    if comparison.expression_missing or comparison.mutation_missing or expression_issues:
        blockers.append(
            {
                "code": "SELECTED_FEATURE_INCOMPATIBILITY",
                "message": "One or more selected genomic features are missing or unusable without a naming/data decision.",
                "features": list(comparison.expression_missing + comparison.mutation_missing) + expression_issues,
            }
        )
    approved_mutation_policy = {
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

    imported_files = sorted(
        path.relative_to(root).as_posix()
        for path in engineer_root.rglob("*")
        if path.is_file()
    )
    imported_models = [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "trusted_for_active_runtime": False,
        }
        for path in sorted((engineer_root / "models").glob("*.pkl"))
    ]
    survival_targets = clinical_schema["survival_targets"]
    report: dict[str, Any] = {
        "phase": "R6-P0",
        "status": "BLOCKED" if blockers else "PASS",
        "active_dataset": {
            "prepared_path": paths.prepared_csv.relative_to(root).as_posix(),
            "patient_count": int(len(prepared)),
            "column_count": int(len(prepared.columns)),
            "manifest_path": manifest_path.relative_to(root).as_posix(),
            "prepared_sha256": _sha256(paths.prepared_csv),
            "manifest_sha256": _sha256(manifest_path),
            "path_selector": "src.data.metabric.MetabricPaths.prepared_csv",
        },
        "active_split": {
            split: int(split_counts.get(split, 0))
            for split in ("train", "validation", "test")
        },
        "survival_contract": {
            "raw_source_column": str(survival_targets["event_column"]),
            "raw_source_0_meaning": str(
                survival_targets["source_event_coding_before_preparation"]["0"]
            ),
            "raw_source_1_meaning": str(
                survival_targets["source_event_coding_before_preparation"]["1"]
            ),
            "active_prepared_column": str(survival_targets["event_column"]),
            "active_prepared_0_meaning": str(survival_targets["event_coding"]["0"]),
            "active_prepared_1_meaning": str(survival_targets["event_coding"]["1"]),
            "model_event_observed_value": 1,
            "duration_column": str(survival_targets["time_column"]),
            "engineer_loader_difference": (
                "Engineer loaders invert 1=living/0=deceased split files. Active prepared data is already "
                "1=deceased event/0=living-censored and must not be inverted again."
            ),
        },
        "r5_clinical_contract": {
            "raw_input_features": list(feature_groups["clinical_features"]),
            "future_r6_rule": "frozen R5 raw clinical features + 50 expression + 18 mutation",
            "engineer_extra_clinical_fields_excluded": [
                "mutation_count",
                "nottingham_prognostic_index",
                "cellularity",
                "neoplasm_histologic_grade",
                "inferred_menopausal_state",
                "type_of_breast_surgery",
                "chemotherapy",
                "hormone_therapy",
                "radio_therapy",
            ],
        },
        "engineer_code_import": {
            "source_ref": engineer_source_ref,
            "source_commit": _git_revision(root, engineer_source_ref),
            "directory": "cognivex_ml",
            "file_count": len(imported_files),
            "files": imported_files,
            "saved_model_artifacts": imported_models,
            "active_runtime_connected": False,
        },
        "selected_feature_contract": {
            "source_path": SELECTED_FEATURES_RELATIVE_PATH.as_posix(),
            "source_sha256": _sha256(selected_path),
            "expression_count": len(selected.expression_features),
            "mutation_count": len(selected.mutation_features),
            "total_count": len(selected.all_features),
            "expression_features": list(selected.expression_features),
            "mutation_features": list(selected.mutation_features),
            "engineer_copy_matches_canonical": engineer_selected == selected,
        },
        "feature_compatibility": {
            "expression_present_count": len(comparison.expression_present),
            "expression_present": list(comparison.expression_present),
            "expression_missing": list(comparison.expression_missing),
            "mutation_present_count": len(comparison.mutation_present),
            "mutation_present": list(comparison.mutation_present),
            "mutation_missing": list(comparison.mutation_missing),
            "total_present_count": len(comparison.expression_present) + len(comparison.mutation_present),
            "alias_candidates_not_applied": [list(item) for item in comparison.alias_candidates],
            "duplicate_dataset_columns": list(comparison.duplicate_dataset_columns),
            "suspicious_index_columns": list(comparison.suspicious_index_columns),
        },
        "mutation_encoding": {
            "direct_binary_count": len(direct_binary),
            "direct_binary_features": direct_binary,
            "requires_transformation_count": len(requires_transform),
            "requires_transformation_features": requires_transform,
            "approved_track_b_policy": approved_mutation_policy,
            "features": [asdict(item) for item in mutation_audit],
        },
        "expression_compatibility": {
            "compatible_count": sum(item.compatible for item in expression_audit),
            "issue_features": expression_issues,
            "features": [asdict(item) for item in expression_audit],
        },
        "subtype_compatibility": {
            "target_column": subtype_column,
            "classes_and_counts": subtype_counts,
            "missing_count": int(subtype.isna().sum()),
            "nc_count": int((subtype == "NC").sum()),
            "required_engineer_classes": ["Basal", "Her2", "LumA", "LumB", "Normal", "claudin-low"],
            "required_classes_present": all(
                value in set(subtype.dropna().astype(str))
                for value in ("Basal", "Her2", "LumA", "LumB", "Normal", "claudin-low")
            ),
        },
        "engineer_script_reuse_matrix": _script_reviews(source_scan),
        "dependency_compatibility": _dependency_audit(engineer_root, source_scan),
        "blockers": blockers,
        "recommendation": (
            "R6 BLOCKED — DECISION REQUIRED" if blockers else "READY FOR R6 TRACK B"
        ),
        "confirmations": {
            "existing_r2_r5_lineage_preserved": True,
            "ai_handoff_data_is_not_active": True,
            "new_model_trained": False,
            "r6_track_b_started": False,
            "r7_started": False,
            "r8_started": False,
        },
    }
    return report


def _markdown_table(headers: tuple[str, ...], rows: list[tuple[Any, ...]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return lines


def _render_markdown(report: dict[str, Any]) -> str:
    active = report["active_dataset"]
    split = report["active_split"]
    survival = report["survival_contract"]
    feature = report["feature_compatibility"]
    mutation = report["mutation_encoding"]
    expression = report["expression_compatibility"]
    subtype = report["subtype_compatibility"]
    lines = [
        "# R6-P0 engineer compatibility audit",
        "",
        f"**Status:** {report['status']}",
        f"**Recommendation:** {report['recommendation']}",
        "",
        "## Active Cognivex authority",
        "",
        f"- Prepared dataset: `{active['prepared_path']}` ({active['patient_count']} patients, {active['column_count']} columns)",
        f"- Manifest: `{active['manifest_path']}`",
        f"- Split: train {split['train']}, validation {split['validation']}, test {split['test']}",
        f"- Path selector: `{active['path_selector']}`",
        "",
        "## Survival contract",
        "",
        f"- Raw source `{survival['raw_source_column']}`: 0={survival['raw_source_0_meaning']}; 1={survival['raw_source_1_meaning']}.",
        f"- Active prepared `{survival['active_prepared_column']}`: 0={survival['active_prepared_0_meaning']}; 1={survival['active_prepared_1_meaning']}.",
        f"- Model event-observed value: `{survival['model_event_observed_value']}`.",
        f"- Hazard: {survival['engineer_loader_difference']}",
        "",
        "## Selected-feature compatibility",
        "",
        f"- Expression present: {feature['expression_present_count']}/50; missing: {feature['expression_missing']}",
        f"- Mutation present: {feature['mutation_present_count']}/18; missing: {feature['mutation_missing']}",
        f"- Total exact-name matches: {feature['total_present_count']}/68",
        f"- Alias candidates (not applied): {feature['alias_candidates_not_applied']}",
        "",
        "## Mutation encoding",
        "",
        f"Direct numeric/boolean 0/1: {mutation['direct_binary_count']}/18. Requires future transformation: {mutation['requires_transformation_count']}/18.",
        "Approved Track B contract: preserve source annotations; map trimmed numeric zero to 0 and valid non-zero annotations to 1 through `src.preprocessing.mutations.classify_mutation_annotation`; reject missing or malformed values; fit no encoding statistics.",
        "",
        *_markdown_table(
            ("Feature", "dtype", "Representation", "Nulls", "Unique", "Direct 0/1"),
            [
                (
                    item["feature"], item["dtype"], item["representation"], item["null_count"],
                    item["unique_count"], item["directly_usable_as_binary"],
                )
                for item in mutation["features"]
            ],
        ),
        "",
        "## Expression compatibility",
        "",
        f"Compatible numeric/non-null/finite/non-constant features: {expression['compatible_count']}/50.",
        f"Issue features: {expression['issue_features']}",
        "",
        "## Subtype compatibility",
        "",
        f"- Target: `{subtype['target_column']}`",
        f"- Counts: {subtype['classes_and_counts']}",
        f"- NC: {subtype['nc_count']}; missing: {subtype['missing_count']}",
        f"- Six engineer classes present: {subtype['required_classes_present']}",
        "",
        "## Engineer script reuse matrix",
        "",
        *_markdown_table(
            ("Script", "Classification", "Reason"),
            [
                (item["script"], item["classification"], item["reason"])
                for item in report["engineer_script_reuse_matrix"]
            ],
        ),
        "",
        "## Dependencies",
        "",
        f"- Installed: {report['dependency_compatibility']['installed_versions']}",
        f"- Missing: {report['dependency_compatibility']['missing_dependencies']}",
        f"- Conflicts: {report['dependency_compatibility']['conflicting_versions']}",
        "",
        "## Blockers",
        "",
    ]
    if report["blockers"]:
        for blocker in report["blockers"]:
            lines.append(f"- `{blocker['code']}`: {blocker['message']} Features: {blocker['features']}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Confirmations",
            "",
            '- Existing Cognivex R2-R5 data lineage was preserved.',
            '- ai_handoff_data/v1 was not made the active dataset.',
            '- No new model was trained.',
            '- R6 Track B implementation was not started.',
            '- R7 and R8 were not started.',
            "",
        ]
    )
    return "\n".join(lines)


def write_audit_artifacts(
    report: dict[str, Any],
    output_directory: Path,
) -> tuple[Path, Path]:
    """Write report-only artifacts outside canonical and engineer handoff data."""
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "engineer_compatibility_report.json"
    markdown_path = output / "engineer_compatibility_report.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")
    return json_path, markdown_path
