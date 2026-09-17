# R3 Biomedical Data Quality Validation

R3 is a read-only engineering-quality scan that begins only after R2 returns `DATA_READY`. It evaluates the canonical prepared dataset plus the existing clinical schema, feature groups, subtype policy, patient mapping, and locked manifest. It does not modify the cohort or make a clinical-quality judgment.

## Status meanings

- `DATA_QUALITY_BLOCKED`: one or more structural errors would make downstream engineering unsafe.
- `DATA_QUALITY_READY_WITH_WARNINGS`: no structural error, but R4 must decide how to handle documented limitations.
- `DATA_QUALITY_READY`: no errors or warnings were observed by the defined R3 rules.

These statuses describe downstream data-engineering readiness only. They do not establish clinical validity, prognostic value, or suitability for patient care.

## Findings

`ERROR` findings include failed R2 validation, missing/duplicate identifiers, mapping or locked-split inconsistencies, missing required columns, invalid survival targets, unexpected clinical/subtype categories, and invalid numeric mRNA values.

`WARNING` findings include zero survival durations, missing nullable clinical values, missing genomic values, missing subtype labels, and zero-variance features. R3 reports these facts and leaves all handling to R4.

`INFORMATION` findings include cohort size, event/censor counts, aggregate locked-split distribution, subtype distribution and NC policy, accepted `Unknown` tumor-stage frequency, and feature-group counts.

## Survival endpoint

The prepared canonical coding is fixed: `1` is deceased/event and `0` is living/censored. R3 validates missing, non-numeric, negative, and out-of-set values without reinterpreting the original source coding. A zero duration is a warning. Durations above the centralized 1,200-month engineering sentinel are information only: it is a 100-year data-review prompt, not a clinical abnormality threshold and never rejects a record.

## Clinical, genomic, and subtype checks

Clinical fields are checked against `clinical_schema.json`; `Unknown` tumor stage is accepted as the intentional canonical category and reported separately. R3 reports missingness and schema violations without imputing or encoding values.

Declared mRNA features are numeric measurements and are checked for missing, non-numeric, infinite, and zero-variance values. The handoff's `*_mut` fields are mutation annotations, not numeric mutation scores; R3 checks their presence and variation without inventing a numeric encoding. No genomic feature is removed or selected.

Subtype labels are checked against `subtype_labels.json`. `NC` rows remain in the canonical cohort. They remain eligible for later survival tracks if survival data is valid, and are excluded only from later subtype-classifier training.

## R3/R4 boundary

R3 never imputes, scales, encodes, filters, selects, rebalances, regenerates splits, fits a model, estimates a metric, or predicts an outcome. R4 must define and validate any training-split-only preprocessing policy using these aggregate findings.
