"""Immutable R4 feature and target schema loaded from canonical metadata."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from src.data.metabric import MetabricPaths


@dataclass(frozen=True, slots=True)
class PreprocessingSchema:
    """Ordered task inputs and subtype mappings from repository metadata."""

    clinical_features: tuple[str, ...]
    numeric_clinical_features: tuple[str, ...]
    categorical_clinical_features: tuple[str, ...]
    categorical_categories: tuple[tuple[str, tuple[str, ...]], ...]
    mrna_features: tuple[str, ...]
    mutation_features: tuple[str, ...]
    survival_time_column: str
    survival_event_column: str
    subtype_target_column: str
    subtype_classes: tuple[str, ...]
    subtype_mapping: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        ordered_groups = (
            self.clinical_features,
            self.numeric_clinical_features,
            self.categorical_clinical_features,
            self.mrna_features,
            self.mutation_features,
            self.subtype_classes,
        )
        if any(not isinstance(group, tuple) or not group for group in ordered_groups):
            raise ValueError("preprocessing feature groups must be non-empty ordered tuples")
        if any(not isinstance(name, str) or not name.strip() for group in ordered_groups for name in group):
            raise ValueError("preprocessing feature names must be non-empty strings")
        if set(self.numeric_clinical_features) | set(self.categorical_clinical_features) != set(
            self.clinical_features
        ):
            raise ValueError("numeric and categorical clinical features must partition clinical_features")
        if len(set(self.clinical_features)) != len(self.clinical_features):
            raise ValueError("clinical features must be unique")
        if len(set(self.mrna_features)) != len(self.mrna_features):
            raise ValueError("mRNA features must be unique")
        if len(set(self.mutation_features)) != len(self.mutation_features):
            raise ValueError("mutation features must be unique")
        category_fields = tuple(field for field, _ in self.categorical_categories)
        if category_fields != self.categorical_clinical_features:
            raise ValueError("categorical category declarations must follow categorical feature order")
        if any(not categories for _, categories in self.categorical_categories):
            raise ValueError("categorical features must declare at least one category")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (self.survival_time_column, self.survival_event_column, self.subtype_target_column)
        ):
            raise ValueError("target column names must be non-empty strings")
        mapping_keys = tuple(source for source, _ in self.subtype_mapping)
        if len(set(mapping_keys)) != len(mapping_keys):
            raise ValueError("subtype mapping source labels must be unique")
        if any(target not in self.subtype_classes for _, target in self.subtype_mapping):
            raise ValueError("subtype mapping targets must belong to subtype_classes")

    @property
    def category_map(self) -> dict[str, tuple[str, ...]]:
        return dict(self.categorical_categories)

    @property
    def subtype_map(self) -> dict[str, str]:
        return dict(self.subtype_mapping)


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{field_name} must be a non-empty list of strings")
    return tuple(value)


def load_preprocessing_schema(paths: MetabricPaths | None = None) -> PreprocessingSchema:
    """Load ordered R4 inputs from the checksum-governed R2 metadata files."""
    resolved = paths or MetabricPaths.from_repository_root()
    feature_groups = _read_json(resolved.metadata_dir / "feature_groups.json")
    clinical_schema = _read_json(resolved.metadata_dir / "clinical_schema.json")
    subtype_labels = _read_json(resolved.metadata_dir / "subtype_labels.json")

    clinical_features = _string_tuple(feature_groups.get("clinical_features"), "clinical_features")
    mrna_features = _string_tuple(feature_groups.get("mrna_features"), "mrna_features")
    mutation_features = _string_tuple(feature_groups.get("mutation_features"), "mutation_features")

    input_features = clinical_schema.get("input_features")
    survival_targets = clinical_schema.get("survival_targets")
    if not isinstance(input_features, dict) or not isinstance(survival_targets, dict):
        raise ValueError("clinical_schema.json is missing input or survival target declarations")
    numeric: list[str] = []
    categorical: list[str] = []
    categories: list[tuple[str, tuple[str, ...]]] = []
    for feature in clinical_features:
        declaration = input_features.get(feature)
        if not isinstance(declaration, dict):
            raise ValueError(f"clinical schema is missing {feature}")
        feature_type = declaration.get("type")
        if feature_type in {"float", "integer"}:
            numeric.append(feature)
        elif feature_type == "categorical":
            categorical.append(feature)
            categories.append((feature, _string_tuple(declaration.get("categories"), f"{feature}.categories")))
        else:
            raise ValueError(f"clinical feature {feature} has an unsupported type")

    time_column = survival_targets.get("time_column")
    event_column = survival_targets.get("event_column")
    subtype_target = feature_groups.get("subtype_target")
    subtype_classes = _string_tuple(subtype_labels.get("classes"), "subtype classes")
    raw_mapping = subtype_labels.get("mapping")
    if not isinstance(time_column, str) or not isinstance(event_column, str) or not isinstance(subtype_target, str):
        raise ValueError("target column metadata is incomplete")
    if not isinstance(raw_mapping, dict) or not all(
        isinstance(source, str) and isinstance(target, str) for source, target in raw_mapping.items()
    ):
        raise ValueError("subtype mapping metadata is invalid")

    return PreprocessingSchema(
        clinical_features=clinical_features,
        numeric_clinical_features=tuple(numeric),
        categorical_clinical_features=tuple(categorical),
        categorical_categories=tuple(categories),
        mrna_features=mrna_features,
        mutation_features=mutation_features,
        survival_time_column=time_column,
        survival_event_column=event_column,
        subtype_target_column=subtype_target,
        subtype_classes=subtype_classes,
        subtype_mapping=tuple((source, target) for source, target in raw_mapping.items()),
    )
