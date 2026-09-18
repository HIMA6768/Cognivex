"""Read-only, aggregate-only R3 quality validation for canonical METABRIC data."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from src.contracts import (
    AnalysisStatus,
    CategoryCount,
    DataQualityFinding,
    DataQualityReport,
    DataQualitySeverity,
    DataQualityStatus,
    FieldQualitySummary,
    GenomicQualitySummary,
    MetabricIngestionResult,
    SplitQualitySummary,
    SubtypeQualitySummary,
    SurvivalQualitySummary,
)

from .metabric import MetabricPaths, load_metabric
from .quality_rules import DEFAULT_QUALITY_RULES, QualityRules


_ALLOWED_SPLITS = ("train", "validation", "test")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _read_csv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError(f"{path.name} must include a header")
        return tuple(reader.fieldnames), list(reader)


def _finding(
    code: str,
    severity: DataQualitySeverity,
    title: str,
    message: str,
    affected_count: int,
    denominator: int | None,
    subject: str | None,
    recommendation: str,
) -> DataQualityFinding:
    fraction = None if denominator in (None, 0) else affected_count / denominator
    return DataQualityFinding(
        code=code,
        severity=severity,
        title=title,
        message=message,
        affected_count=affected_count,
        affected_fraction=fraction,
        subject=subject,
        recommendation=recommendation,
    )


def _report(
    findings: list[DataQualityFinding],
    cohort_size: int | None,
    *,
    survival: SurvivalQualitySummary | None = None,
    clinical_missingness: tuple[FieldQualitySummary, ...] = (),
    split_summaries: tuple[SplitQualitySummary, ...] = (),
    subtype: SubtypeQualitySummary | None = None,
    genomic_summaries: tuple[GenomicQualitySummary, ...] = (),
) -> DataQualityReport:
    errors = sum(finding.severity is DataQualitySeverity.ERROR for finding in findings)
    warnings = sum(finding.severity is DataQualitySeverity.WARNING for finding in findings)
    information = sum(finding.severity is DataQualitySeverity.INFORMATION for finding in findings)
    status = (
        DataQualityStatus.DATA_QUALITY_BLOCKED
        if errors
        else DataQualityStatus.DATA_QUALITY_READY_WITH_WARNINGS
        if warnings
        else DataQualityStatus.DATA_QUALITY_READY
    )
    return DataQualityReport(
        status=status,
        findings=tuple(findings),
        cohort_size=cohort_size,
        error_count=errors,
        warning_count=warnings,
        information_count=information,
        survival=survival,
        clinical_missingness=clinical_missingness,
        split_summaries=split_summaries,
        subtype=subtype,
        genomic_summaries=genomic_summaries,
    )


def _r2_blocked_report(ingestion: MetabricIngestionResult) -> DataQualityReport:
    findings = [
        _finding(
            f"R2_{issue.code}",
            DataQualitySeverity.ERROR,
            "R2 structural validation failed",
            issue.message,
            0,
            None,
            None,
            "Resolve the R2 structural validation issue before running R3 quality checks.",
        )
        for issue in ingestion.validation.issues
    ]
    if not findings:
        findings.append(
            _finding(
                "R2_DATA_NOT_READY",
                DataQualitySeverity.ERROR,
                "R2 validation is not ready",
                ingestion.validation.message,
                0,
                None,
                None,
                "Run and resolve R2 validation before running R3 quality checks.",
            )
        )
    return _report(findings, ingestion.cohort.patient_records)


def _numeric(value: str) -> float | None:
    if not value.strip():
        return None
    try:
        numeric_value = float(value)
    except ValueError:
        return None
    return numeric_value if math.isfinite(numeric_value) else math.inf


def _category_counts(counter: Counter[str], total: int, labels: tuple[str, ...]) -> tuple[CategoryCount, ...]:
    return tuple(
        CategoryCount(label=label, count=counter[label], fraction=counter[label] / total if total else None)
        for label in labels
    )


def evaluate_metabric_quality(
    paths: MetabricPaths | None = None,
    ingestion: MetabricIngestionResult | None = None,
    rules: QualityRules = DEFAULT_QUALITY_RULES,
) -> DataQualityReport:
    """Evaluate R3 data quality after R2 passes, without altering source data."""
    resolved = paths or MetabricPaths.from_repository_root()
    r2_result = ingestion or load_metabric(resolved)
    if r2_result.validation.status is not AnalysisStatus.DATA_READY:
        return _r2_blocked_report(r2_result)

    findings: list[DataQualityFinding] = []
    try:
        schema = _read_json(resolved.metadata_dir / "clinical_schema.json")
        feature_groups = _read_json(resolved.metadata_dir / "feature_groups.json")
        subtype_labels = _read_json(resolved.metadata_dir / "subtype_labels.json")
        header, prepared_rows = _read_csv(resolved.prepared_csv)
        mapping_header, mapping_rows = _read_csv(resolved.metadata_dir / "patient_mapping.csv")
        manifest_header, manifest_rows = _read_csv(resolved.metadata_dir / "manifest.csv")
    except (OSError, ValueError, json.JSONDecodeError):
        return _report(
            [
                _finding(
                    "QUALITY_ARTIFACT_UNREADABLE",
                    DataQualitySeverity.ERROR,
                    "R3 quality artifacts are unreadable",
                    "The prepared dataset or required R2 metadata cannot be read for a quality scan.",
                    0,
                    None,
                    None,
                    "Restore the canonical R2 artifacts and re-run structural validation.",
                )
            ],
            None,
        )

    clinical_schema = schema.get("input_features")
    survival_schema = schema.get("survival_targets")
    clinical_features = feature_groups.get("clinical_features")
    mrna_features = feature_groups.get("mrna_features")
    mutation_features = feature_groups.get("mutation_features")
    subtype_column = feature_groups.get("subtype_target")
    if not (
        isinstance(clinical_schema, dict)
        and isinstance(survival_schema, dict)
        and isinstance(clinical_features, list)
        and isinstance(mrna_features, list)
        and isinstance(mutation_features, list)
        and isinstance(subtype_column, str)
    ):
        return _report(
            [
                _finding(
                    "QUALITY_METADATA_INVALID",
                    DataQualitySeverity.ERROR,
                    "R3 quality metadata is incomplete",
                    "Existing R2 metadata does not define the required quality-check contracts.",
                    0,
                    None,
                    None,
                    "Restore the canonical metadata and re-run R2 validation.",
                )
            ],
            None,
        )

    time_column = survival_schema.get("time_column")
    event_column = survival_schema.get("event_column")
    required_columns = {"patient_id", *clinical_features, *mrna_features, *mutation_features, subtype_column}
    if isinstance(time_column, str):
        required_columns.add(time_column)
    if isinstance(event_column, str):
        required_columns.add(event_column)
    missing_columns = sorted(column for column in required_columns if column not in header)
    declared_genomic_columns = set(mrna_features) | set(mutation_features)
    missing_genomic_columns = [column for column in missing_columns if column in declared_genomic_columns]
    missing_non_genomic_columns = [column for column in missing_columns if column not in declared_genomic_columns]
    duplicate_header_columns = len(header) - len(set(header))
    duplicate_feature_names = (
        len(mrna_features) - len(set(mrna_features)) + len(mutation_features) - len(set(mutation_features))
    )
    if missing_non_genomic_columns:
        findings.append(
            _finding(
                "REQUIRED_COLUMN_MISSING",
                DataQualitySeverity.ERROR,
                "Required canonical columns are missing",
                f"{len(missing_non_genomic_columns)} declared non-genomic columns are absent from the prepared dataset.",
                len(missing_non_genomic_columns),
                len(required_columns),
                "prepared dataset schema",
                "Restore the canonical prepared schema before downstream engineering proceeds.",
            )
        )
    if missing_genomic_columns:
        findings.append(
            _finding(
                "GENOMIC_FEATURE_MISSING",
                DataQualitySeverity.ERROR,
                "Declared genomic feature columns are missing",
                f"{len(missing_genomic_columns)} declared genomic feature columns are absent from the prepared dataset.",
                len(missing_genomic_columns),
                len(declared_genomic_columns),
                "genomic feature groups",
                "Restore the canonical genomic feature contract before downstream engineering proceeds.",
            )
        )
    if duplicate_header_columns or duplicate_feature_names:
        findings.append(
            _finding(
                "FEATURE_CONTRACT_DUPLICATE",
                DataQualitySeverity.ERROR,
                "Duplicate feature names were found",
                "Prepared headers or declared genomic feature groups contain duplicate names.",
                duplicate_header_columns + duplicate_feature_names,
                None,
                "feature groups",
                "Restore unique canonical feature names before downstream engineering proceeds.",
            )
        )
    if missing_columns or duplicate_header_columns or duplicate_feature_names or not isinstance(time_column, str) or not isinstance(event_column, str):
        return _report(findings, len(prepared_rows))

    patient_ids = [row.get("patient_id", "").strip() for row in prepared_rows]
    patient_counter = Counter(patient_ids)
    missing_patient_ids = patient_counter.pop("", 0)
    duplicate_patient_ids = sum(count - 1 for count in patient_counter.values() if count > 1)
    if missing_patient_ids:
        findings.append(
            _finding(
                "PATIENT_ID_MISSING",
                DataQualitySeverity.ERROR,
                "Prepared records are missing patient identifiers",
                f"{missing_patient_ids} prepared records have no patient identifier.",
                missing_patient_ids,
                len(prepared_rows),
                "patient_id",
                "Restore patient identifiers before downstream engineering proceeds.",
            )
        )
    if duplicate_patient_ids:
        findings.append(
            _finding(
                "PATIENT_ID_DUPLICATE",
                DataQualitySeverity.ERROR,
                "Prepared patient identifiers are duplicated",
                f"{duplicate_patient_ids} duplicate prepared patient records were found.",
                duplicate_patient_ids,
                len(prepared_rows),
                "patient_id",
                "Restore one prepared record per patient before downstream engineering proceeds.",
            )
        )

    mapping_required = {"patient_id", "genomic_sample_id", "mapping_rule"}
    if not mapping_required.issubset(mapping_header):
        findings.append(
            _finding(
                "PATIENT_MAPPING_INCONSISTENT",
                DataQualitySeverity.ERROR,
                "Patient mapping is incomplete",
                "The patient/sample mapping is missing required columns.",
                0,
                None,
                "patient mapping",
                "Restore the canonical one-to-one patient/sample mapping.",
            )
        )
        mapping_rows = []
    mapping_patients = [row.get("patient_id", "").strip() for row in mapping_rows]
    mapping_samples = [row.get("genomic_sample_id", "").strip() for row in mapping_rows]
    mapping_problem_count = (
        mapping_patients.count("")
        + mapping_samples.count("")
        + sum(count - 1 for count in Counter(patient for patient in mapping_patients if patient).values() if count > 1)
        + sum(count - 1 for count in Counter(sample for sample in mapping_samples if sample).values() if count > 1)
    )
    if set(mapping_patients) - {""} != set(patient_counter) or mapping_problem_count:
        findings.append(
            _finding(
                "PATIENT_MAPPING_INCONSISTENT",
                DataQualitySeverity.ERROR,
                "Patient/sample mapping is not one-to-one",
                "Prepared patients and genomic samples do not form a complete one-to-one mapping.",
                mapping_problem_count or len(set(mapping_patients) ^ set(patient_counter)),
                len(prepared_rows),
                "patient mapping",
                "Restore the locked one-to-one patient/sample mapping.",
            )
        )

    manifest_required = {"patient_id", "data_source", "split"}
    split_by_patient: dict[str, str] = {}
    split_patient_counts = Counter({split: 0 for split in _ALLOWED_SPLITS})
    if not manifest_required.issubset(manifest_header):
        findings.append(
            _finding(
                "MANIFEST_INCONSISTENT",
                DataQualitySeverity.ERROR,
                "Locked split manifest is incomplete",
                "The manifest is missing required columns.",
                0,
                None,
                "locked manifest",
                "Restore the canonical locked manifest; do not regenerate it in R3.",
            )
        )
        manifest_rows = []
    invalid_splits = 0
    split_contamination = 0
    duplicate_manifest_rows = 0
    for row in manifest_rows:
        patient_id = row.get("patient_id", "").strip()
        split = row.get("split", "").strip()
        if split not in _ALLOWED_SPLITS:
            invalid_splits += 1
            continue
        split_patient_counts[split] += 1
        if patient_id in split_by_patient:
            duplicate_manifest_rows += 1
            if split_by_patient[patient_id] != split:
                split_contamination += 1
        else:
            split_by_patient[patient_id] = split
    if invalid_splits:
        findings.append(
            _finding(
                "SPLIT_NAME_INVALID",
                DataQualitySeverity.ERROR,
                "Manifest contains an unsupported split",
                f"{invalid_splits} manifest records are outside train, validation, and test.",
                invalid_splits,
                len(manifest_rows),
                "locked manifest",
                "Restore approved split names without regenerating the manifest.",
            )
        )
    if split_contamination:
        findings.append(
            _finding(
                "SPLIT_CONTAMINATION",
                DataQualitySeverity.ERROR,
                "Patients appear in more than one split",
                f"{split_contamination} patient assignments cross locked split boundaries.",
                split_contamination,
                len(prepared_rows),
                "locked manifest",
                "Restore one locked split assignment per patient before evaluation work.",
            )
        )
    elif duplicate_manifest_rows:
        findings.append(
            _finding(
                "MANIFEST_PATIENT_DUPLICATE",
                DataQualitySeverity.ERROR,
                "Manifest patient assignments are duplicated",
                f"{duplicate_manifest_rows} duplicate manifest records were found.",
                duplicate_manifest_rows,
                len(prepared_rows),
                "locked manifest",
                "Restore one locked manifest assignment per patient.",
            )
        )
    missing_splits = [split for split in _ALLOWED_SPLITS if split_patient_counts[split] == 0]
    if missing_splits:
        findings.append(
            _finding(
                "SPLIT_EMPTY",
                DataQualitySeverity.ERROR,
                f"Locked split is empty: {', '.join(missing_splits)}",
                "Each approved locked split must contain at least one patient.",
                len(missing_splits),
                len(_ALLOWED_SPLITS),
                "locked manifest",
                "Restore the locked split assignments; do not rebalance or regenerate them in R3.",
            )
        )
    manifest_patient_set = set(split_by_patient)
    prepared_patient_set = set(patient_counter)
    manifest_difference = len(prepared_patient_set ^ manifest_patient_set)
    if manifest_difference:
        findings.append(
            _finding(
                "MANIFEST_PATIENT_MISMATCH",
                DataQualitySeverity.ERROR,
                "Prepared and manifest patient sets disagree",
                "The locked manifest does not assign exactly the prepared cohort patients.",
                manifest_difference,
                len(prepared_rows),
                "locked manifest",
                "Restore the canonical manifest/patient alignment.",
            )
        )

    clinical_missingness: list[FieldQualitySummary] = []
    unknown_tumor_stage_count = 0
    for field_name in clinical_features:
        field_spec = clinical_schema.get(field_name)
        if not isinstance(field_spec, dict):
            findings.append(
                _finding(
                    "CLINICAL_SCHEMA_MISSING",
                    DataQualitySeverity.ERROR,
                    "Clinical schema is incomplete",
                    f"The clinical schema does not define {field_name}.",
                    1,
                    len(clinical_features),
                    field_name,
                    "Restore the canonical clinical schema before downstream engineering proceeds.",
                )
            )
            continue
        missing_count = 0
        invalid_count = 0
        categories = field_spec.get("categories")
        nullable = bool(field_spec.get("nullable"))
        expected_type = field_spec.get("type")
        for row in prepared_rows:
            value = row[field_name].strip()
            if not value:
                missing_count += 1
                continue
            if expected_type in {"float", "integer"}:
                numeric_value = _numeric(value)
                if numeric_value is None or math.isinf(numeric_value) or (
                    expected_type == "integer" and not numeric_value.is_integer()
                ):
                    invalid_count += 1
            elif expected_type == "categorical" and (
                not isinstance(categories, list) or value not in categories
            ):
                invalid_count += 1
            if field_name == "tumor_stage" and value == "Unknown":
                unknown_tumor_stage_count += 1
        clinical_missingness.append(
            FieldQualitySummary(field_name, len(prepared_rows), missing_count, invalid_count)
        )
        if missing_count:
            missing_recommendations = {
                "tumor_size": (
                    "R4 uses training-only median imputation while preserving original missingness with "
                    "tumor_size_was_missing. Validation and test rows are transform-only."
                ),
                "er_status_measured_by_ihc": (
                    "R4 uses training-only most-frequent imputation while preserving original missingness "
                    "with er_status_measured_by_ihc_was_missing. Validation and test rows are transform-only, "
                    "with unknown-safe categorical encoding."
                ),
            }
            findings.append(
                _finding(
                    "CLINICAL_VALUE_MISSING",
                    DataQualitySeverity.WARNING if nullable else DataQualitySeverity.ERROR,
                    f"Clinical values are missing: {field_name}",
                    f"{missing_count} values are missing for {field_name}.",
                    missing_count,
                    len(prepared_rows),
                    field_name,
                    missing_recommendations.get(
                        field_name,
                        "R4 evaluates task-specific eligibility without mutating canonical records; "
                        "no R3 imputation occurs.",
                    ),
                )
            )
        if invalid_count:
            findings.append(
                _finding(
                    "CLINICAL_SCHEMA_VIOLATION",
                    DataQualitySeverity.ERROR,
                    f"Clinical values violate the schema: {field_name}",
                    f"{invalid_count} values do not meet the declared type or category contract.",
                    invalid_count,
                    len(prepared_rows),
                    field_name,
                    "Restore canonical clinical values before downstream engineering proceeds.",
                )
            )
    if unknown_tumor_stage_count:
        findings.append(
            _finding(
                "TUMOR_STAGE_UNKNOWN",
                DataQualitySeverity.INFORMATION,
                "Unknown tumor stage is an accepted canonical category",
                f"{unknown_tumor_stage_count} records use the intentional Unknown tumor-stage category.",
                unknown_tumor_stage_count,
                len(prepared_rows),
                "tumor_stage",
                "R4 preserves Unknown as a valid categorical value without imputation or conversion to a numeric stage.",
            )
        )

    time_counts = Counter[str]()
    event_counts = Counter[str]()
    for row in prepared_rows:
        time_value = row[time_column].strip()
        numeric_time = _numeric(time_value)
        if not time_value:
            time_counts["missing"] += 1
        elif numeric_time is None:
            time_counts["non_numeric"] += 1
        elif math.isinf(numeric_time):
            time_counts["non_numeric"] += 1
        elif numeric_time < 0:
            time_counts["negative"] += 1
        else:
            if numeric_time == 0:
                time_counts["zero"] += 1
            if numeric_time > rules.suspicious_survival_months:
                time_counts["suspicious"] += 1
        event_value = row[event_column].strip()
        event_numeric = _numeric(event_value)
        if not event_value:
            event_counts["missing"] += 1
        elif event_numeric is None or math.isinf(event_numeric) or event_numeric not in {0.0, 1.0}:
            event_counts["invalid"] += 1
        elif event_numeric == 1:
            event_counts["event"] += 1
        else:
            event_counts["censored"] += 1
    survival = SurvivalQualitySummary(
        time_column=time_column,
        event_column=event_column,
        total_count=len(prepared_rows),
        event_count=event_counts["event"],
        censored_count=event_counts["censored"],
        missing_time_count=time_counts["missing"],
        non_numeric_time_count=time_counts["non_numeric"],
        negative_time_count=time_counts["negative"],
        zero_time_count=time_counts["zero"],
        suspicious_time_count=time_counts["suspicious"],
        missing_event_count=event_counts["missing"],
        invalid_event_count=event_counts["invalid"],
    )
    for code, count, title, message in (
        ("SURVIVAL_TIME_MISSING", time_counts["missing"], "Survival duration is missing", "survival durations are missing."),
        ("SURVIVAL_TIME_NON_NUMERIC", time_counts["non_numeric"], "Survival duration is non-numeric", "survival durations are not finite numbers."),
        ("SURVIVAL_TIME_NEGATIVE", time_counts["negative"], "Survival duration is negative", "survival durations are negative."),
        ("EVENT_VALUE_MISSING", event_counts["missing"], "Survival event indicator is missing", "event indicators are missing."),
        ("EVENT_VALUE_INVALID", event_counts["invalid"], "Survival event indicator is invalid", "event indicators are outside canonical 0/1 coding."),
    ):
        if count:
            findings.append(
                _finding(
                    code,
                    DataQualitySeverity.ERROR,
                    title,
                    f"{count} {message}",
                    count,
                    len(prepared_rows),
                    time_column if code.startswith("SURVIVAL") else event_column,
                    "Restore canonical survival target values before downstream engineering proceeds.",
                )
            )
    if time_counts["zero"]:
        findings.append(
            _finding(
                "SURVIVAL_TIME_ZERO",
                DataQualitySeverity.WARNING,
                "Survival duration is zero",
                f"{time_counts['zero']} records have zero survival duration.",
                time_counts["zero"],
                len(prepared_rows),
                time_column,
                "The canonical record remains unchanged. R4/R4D exclude it from survival Tracks A/B/D using "
                "NON_POSITIVE_SURVIVAL_DURATION; it remains independently eligible for Track C when Track C requirements pass.",
            )
        )
    if time_counts["suspicious"]:
        findings.append(
            _finding(
                "SURVIVAL_TIME_SUSPICIOUS",
                DataQualitySeverity.INFORMATION,
                "Survival duration exceeds the engineering review sentinel",
                f"{time_counts['suspicious']} durations exceed {rules.suspicious_survival_months:g} months.",
                time_counts["suspicious"],
                len(prepared_rows),
                time_column,
                "Review source units or entry values; this non-clinical sentinel does not reject records.",
            )
        )
    findings.append(
        _finding(
            "SURVIVAL_ENDPOINT_SUMMARY",
            DataQualitySeverity.INFORMATION,
            "Canonical survival endpoint summary",
            f"{event_counts['event']} events and {event_counts['censored']} censored records use canonical 1/0 coding.",
            len(prepared_rows),
            len(prepared_rows),
            "survival targets",
            "Use this aggregate context when defining later survival-model evaluation.",
        )
    )

    raw_to_canonical = subtype_labels.get("mapping")
    canonical_classes = subtype_labels.get("classes")
    nc_policy = subtype_labels.get("nc_policy")
    if not isinstance(raw_to_canonical, dict) or not isinstance(canonical_classes, list) or not isinstance(nc_policy, str):
        return _report(
            findings
            + [
                _finding(
                    "SUBTYPE_METADATA_INVALID",
                    DataQualitySeverity.ERROR,
                    "Subtype metadata is incomplete",
                    "The existing subtype mapping or policy cannot be used for quality validation.",
                    0,
                    None,
                    "subtype labels",
                    "Restore canonical subtype metadata before downstream engineering proceeds.",
                )
            ],
            len(prepared_rows),
            survival=survival,
            clinical_missingness=tuple(clinical_missingness),
        )
    subtype_counter: Counter[str] = Counter()
    split_events: dict[str, Counter[str]] = {split: Counter() for split in _ALLOWED_SPLITS}
    split_subtypes: dict[str, Counter[str]] = {split: Counter() for split in _ALLOWED_SPLITS}
    missing_subtype = 0
    unexpected_subtype = 0
    nc_count = 0
    for row in prepared_rows:
        raw_subtype = row[subtype_column].strip()
        if not raw_subtype:
            missing_subtype += 1
            normalized = "Missing"
        elif raw_subtype == "NC":
            nc_count += 1
            normalized = "NC"
        elif raw_subtype in raw_to_canonical:
            normalized = str(raw_to_canonical[raw_subtype])
            subtype_counter[normalized] += 1
        else:
            unexpected_subtype += 1
            normalized = "Unexpected"
        split = split_by_patient.get(row["patient_id"].strip())
        if split in _ALLOWED_SPLITS:
            event_numeric = _numeric(row[event_column].strip())
            if event_numeric == 1:
                split_events[split]["event"] += 1
            elif event_numeric == 0:
                split_events[split]["censored"] += 1
            split_subtypes[split][normalized] += 1
    subtype = SubtypeQualitySummary(
        taxonomy_column=subtype_column,
        class_counts=_category_counts(subtype_counter, len(prepared_rows), tuple(str(label) for label in canonical_classes)),
        nc_count=nc_count,
        missing_count=missing_subtype,
        unexpected_count=unexpected_subtype,
        nc_policy=nc_policy,
    )
    if missing_subtype:
        findings.append(
            _finding(
                "SUBTYPE_VALUE_MISSING",
                DataQualitySeverity.WARNING,
                "Subtype labels are missing",
                f"{missing_subtype} records have no subtype label.",
                missing_subtype,
                len(prepared_rows),
                subtype_column,
                "Retain these rows; define future Track C training eligibility in R4+.",
            )
        )
    if unexpected_subtype:
        findings.append(
            _finding(
                "SUBTYPE_VALUE_UNEXPECTED",
                DataQualitySeverity.ERROR,
                "Subtype labels are outside the declared policy",
                f"{unexpected_subtype} subtype labels are not declared by the canonical mapping or NC policy.",
                unexpected_subtype,
                len(prepared_rows),
                subtype_column,
                "Restore canonical subtype labels before downstream engineering proceeds.",
            )
        )
    findings.extend(
        (
            _finding(
                "SUBTYPE_DISTRIBUTION",
                DataQualitySeverity.INFORMATION,
                "Subtype distribution recorded",
                "Declared subtype counts are available for later class-balance planning; R3 does not rebalance records.",
                len(prepared_rows),
                len(prepared_rows),
                subtype_column,
                "Use the aggregate distribution when defining a future Track C evaluation plan.",
            ),
            _finding(
                "SUBTYPE_NC_POLICY",
                DataQualitySeverity.INFORMATION,
                "NC subtype policy preserved",
                f"{nc_count} NC records remain in the canonical cohort.",
                nc_count,
                len(prepared_rows),
                subtype_column,
                "Keep NC rows for eligible future survival work; exclude them only from future subtype-classifier training.",
            ),
        )
    )

    genomic_summaries: list[GenomicQualitySummary] = []
    for group_name, feature_names in (("mRNA", mrna_features), ("mutation", mutation_features)):
        numeric_values_expected = group_name == "mRNA"
        present_features = [feature for feature in feature_names if feature in header]
        missing_feature_count = len(feature_names) - len(present_features)
        total_values = len(prepared_rows) * len(present_features)
        missing_values = 0
        non_numeric_values = 0
        infinite_values = 0
        first_values: dict[str, float | str] = {}
        varies = {feature: False for feature in present_features}
        for row in prepared_rows:
            for feature in present_features:
                raw_value = row[feature].strip()
                if not raw_value:
                    missing_values += 1
                    continue
                if not numeric_values_expected:
                    if feature not in first_values:
                        first_values[feature] = raw_value
                    elif raw_value != first_values[feature]:
                        varies[feature] = True
                    continue
                numeric_value = _numeric(raw_value)
                if numeric_value is None:
                    non_numeric_values += 1
                    continue
                if math.isinf(numeric_value):
                    infinite_values += 1
                    continue
                if feature not in first_values:
                    first_values[feature] = numeric_value
                elif numeric_value != first_values[feature]:
                    varies[feature] = True
        zero_variance = sum(feature in first_values and not varies[feature] for feature in present_features)
        genomic_summaries.append(
            GenomicQualitySummary(
                group_name=group_name,
                expected_feature_count=len(feature_names),
                present_feature_count=len(present_features),
                total_value_count=total_values,
                missing_value_count=missing_values,
                non_numeric_value_count=non_numeric_values,
                infinite_value_count=infinite_values,
                zero_variance_feature_count=zero_variance,
            )
        )
        if missing_feature_count:
            findings.append(
                _finding(
                    "GENOMIC_FEATURE_MISSING",
                    DataQualitySeverity.ERROR,
                    f"Declared {group_name} feature columns are missing",
                    f"{missing_feature_count} declared {group_name} feature columns are absent.",
                    missing_feature_count,
                    len(feature_names),
                    f"{group_name} features",
                    "Restore the canonical feature-group contract before downstream engineering proceeds.",
                )
            )
        if missing_values:
            findings.append(
                _finding(
                    "GENOMIC_VALUE_MISSING",
                    DataQualitySeverity.WARNING,
                    f"{group_name} values are missing",
                    f"{missing_values} {group_name} feature values are blank.",
                    missing_values,
                    total_values,
                    f"{group_name} features",
                    "R4 evaluates task-specific eligibility without mutating canonical records; R3 does not impute values.",
                )
            )
        if non_numeric_values:
            findings.append(
                _finding(
                    "GENOMIC_VALUE_NON_NUMERIC",
                    DataQualitySeverity.ERROR,
                    f"{group_name} values are non-numeric",
                    f"{non_numeric_values} {group_name} values cannot be interpreted as numbers.",
                    non_numeric_values,
                    total_values,
                    f"{group_name} features",
                    "Restore numeric canonical feature values before downstream engineering proceeds.",
                )
            )
        if infinite_values:
            findings.append(
                _finding(
                    "GENOMIC_VALUE_INFINITE",
                    DataQualitySeverity.ERROR,
                    f"{group_name} values are infinite",
                    f"{infinite_values} {group_name} values are not finite.",
                    infinite_values,
                    total_values,
                    f"{group_name} features",
                    "Restore finite canonical feature values before downstream engineering proceeds.",
                )
            )
        if zero_variance:
            findings.append(
                _finding(
                    "GENOMIC_ZERO_VARIANCE",
                    DataQualitySeverity.WARNING,
                    f"{group_name} features have zero variance",
                    f"{zero_variance} {group_name} features are constant across available numeric values.",
                    zero_variance,
                    len(present_features),
                    f"{group_name} features",
                    "Record this limitation for R4; R3 does not remove or filter features.",
                )
            )
    findings.append(
        _finding(
            "COHORT_SIZE",
            DataQualitySeverity.INFORMATION,
            "Cohort size recorded",
            f"The quality scan evaluated {len(prepared_rows)} prepared records.",
            len(prepared_rows),
            len(prepared_rows),
            "cohort",
            "Use this aggregate count when planning later engineering work.",
        )
    )
    structural_split_codes = {
        "PATIENT_ID_MISSING",
        "PATIENT_ID_DUPLICATE",
        "PATIENT_MAPPING_INCONSISTENT",
        "MANIFEST_INCONSISTENT",
        "SPLIT_NAME_INVALID",
        "SPLIT_CONTAMINATION",
        "MANIFEST_PATIENT_DUPLICATE",
        "SPLIT_EMPTY",
        "MANIFEST_PATIENT_MISMATCH",
    }
    split_summaries = ()
    if not any(finding.code in structural_split_codes for finding in findings):
        split_summaries = tuple(
            SplitQualitySummary(
                split=split,
                patient_count=split_patient_counts[split],
                event_count=split_events[split]["event"],
                censored_count=split_events[split]["censored"],
                subtype_counts=_category_counts(
                    split_subtypes[split],
                    split_patient_counts[split],
                    tuple(str(label) for label in canonical_classes) + ("NC", "Missing", "Unexpected"),
                ),
            )
            for split in _ALLOWED_SPLITS
        )
    findings.append(
        _finding(
            "SPLIT_DISTRIBUTION",
            DataQualitySeverity.INFORMATION,
            "Locked split distributions recorded",
            "Aggregate event/censor and subtype distributions are available for the locked train, validation, and test partitions.",
            len(prepared_rows),
            len(prepared_rows),
            "locked manifest",
            "Preserve these assignments; do not regenerate or rebalance the manifest in R3.",
        )
    )
    return _report(
        findings,
        len(prepared_rows),
        survival=survival,
        clinical_missingness=tuple(clinical_missingness),
        split_summaries=split_summaries,
        subtype=subtype,
        genomic_summaries=tuple(genomic_summaries),
    )
