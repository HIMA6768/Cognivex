# R6-P0 engineer compatibility audit

R6-P0 imports the AI-engineer `cognivex_ml/` implementation as disconnected reference material and audits its explicit 68-feature contract against active Cognivex data. It does not train Track B, change R5, evaluate the held-out test split, or activate engineer models.

## Authority preserved

- Active prepared data: `data/metabric/prepared/METABRIC_prepared.csv`
- Cohort: 1,904 patients and 693 columns
- Locked split: 1,332 train, 286 validation, 286 test
- Active manifest: `data/metabric/metadata/manifest.csv`
- Active event convention: `overall_survival=1` means deceased/event; `0` means living/censored
- Imported engineer source: `origin/anay/prediction_pipelines` at `f4af52c862575f47089f2d90e89676c54d240fe6`

The engineer split CSVs used the opposite source-status convention and their loaders calculate `event = 1 - overall_survival`. That operation must never be applied to active prepared Cognivex data because it would reverse every event label.

## Compatibility outcome

The canonical `ai_handoff_data/v1/selected_features.txt` contains exactly 50 expression and 18 mutation names with no duplicates. All 68 names exist exactly in active data; there are no case, whitespace, suffix, alias, duplicate-column, or index-column findings.

All 50 expression features are numeric, non-null, finite, and non-constant. All 18 mutation features are non-null annotation-string fields containing `"0"` for absence and variant annotations for presence. None is directly numeric/boolean 0/1.

The review decision approves reuse of the existing R4D mutation-presence contract for only the selected 18 mutation fields. Track B will keep the prepared annotations unchanged and derive binary predictors through `src.preprocessing.mutations.classify_mutation_annotation`: trimmed numeric zero maps to 0, a valid non-zero annotation maps to 1, and missing/malformed values fail clearly rather than being coerced. The conversion uses no fitted statistics and must be identical for train, validation, and test. No conversion or model fitting has been performed in R6-P0.

## Detailed artifacts

- `artifacts/r6_p0/engineer_compatibility_report.json`
- `artifacts/r6_p0/engineer_compatibility_report.md`

The detailed report includes per-feature mutation representation and expression quality, subtype counts, script reuse classifications, dependency differences, imported-file inventory, blockers, and confirmations.
