# R6-P0 engineer compatibility audit

**Status:** PASS
**Recommendation:** READY FOR R6 TRACK B

## Active Cognivex authority

- Prepared dataset: `data/metabric/prepared/METABRIC_prepared.csv` (1904 patients, 693 columns)
- Manifest: `data/metabric/metadata/manifest.csv`
- Split: train 1332, validation 286, test 286
- Path selector: `src.data.metabric.MetabricPaths.prepared_csv`

## Survival contract

- Raw source `overall_survival`: 0=Deceased; 1=Living.
- Active prepared `overall_survival`: 0=Living / Censored; 1=Deceased (Event).
- Model event-observed value: `1`.
- Hazard: Engineer loaders invert 1=living/0=deceased split files. Active prepared data is already 1=deceased event/0=living-censored and must not be inverted again.

## Selected-feature compatibility

- Expression present: 50/50; missing: []
- Mutation present: 18/18; missing: []
- Total exact-name matches: 68/68
- Alias candidates (not applied): []

## Mutation encoding

Direct numeric/boolean 0/1: 0/18. Requires future transformation: 18/18.
Approved Track B contract: preserve source annotations; map trimmed numeric zero to 0 and valid non-zero annotations to 1 through `src.preprocessing.mutations.classify_mutation_annotation`; reject missing or malformed values; fit no encoding statistics.

| Feature | dtype | Representation | Nulls | Unique | Direct 0/1 |
| --- | --- | --- | --- | --- | --- |
| gata3_mut | object | mutation_annotation_string | 0 | 128 | False |
| egfr_mut | object | mutation_annotation_string | 0 | 26 | False |
| erbb2_mut | object | mutation_annotation_string | 0 | 37 | False |
| erbb3_mut | object | mutation_annotation_string | 0 | 39 | False |
| lamb3_mut | object | mutation_annotation_string | 0 | 51 | False |
| nr2f1_mut | object | mutation_annotation_string | 0 | 6 | False |
| chek2_mut | object | mutation_annotation_string | 0 | 13 | False |
| hras_mut | object | mutation_annotation_string | 0 | 3 | False |
| pten_mut | object | mutation_annotation_string | 0 | 73 | False |
| cbfb_mut | object | mutation_annotation_string | 0 | 66 | False |
| klrg1_mut | object | mutation_annotation_string | 0 | 6 | False |
| smad4_mut | object | mutation_annotation_string | 0 | 22 | False |
| foxo1_mut | object | mutation_annotation_string | 0 | 11 | False |
| prkcz_mut | object | mutation_annotation_string | 0 | 14 | False |
| ctnna1_mut | object | mutation_annotation_string | 0 | 12 | False |
| lama2_mut | object | mutation_annotation_string | 0 | 87 | False |
| ttyh1_mut | object | mutation_annotation_string | 0 | 18 | False |
| nr3c1_mut | object | mutation_annotation_string | 0 | 10 | False |

## Expression compatibility

Compatible numeric/non-null/finite/non-constant features: 50/50.
Issue features: []

## Subtype compatibility

- Target: `pam50_+_claudin-low_subtype`
- Counts: {'Basal': 199, 'Her2': 220, 'LumA': 679, 'LumB': 461, 'NC': 6, 'Normal': 140, 'claudin-low': 199}
- NC: 6; missing: 0
- Six engineer classes present: True

## Engineer script reuse matrix

| Script | Classification | Reason |
| --- | --- | --- |
| train_clinical_survival.py | REFERENCE ONLY | Cox tuning structure is informative, but it replaces frozen R5 predictors with an expanded clinical set, assumes engineer split CSVs, reinverts survival status, and scores test. |
| train_genomic_survival.py | REUSE PARTIALLY / REFACTOR | Train-fit imputation/scaling and penalized Cox search are useful, but all numeric columns are selected dynamically, mutation annotations are mishandled, active event status would be inverted, and test is evaluated during development. |
| train_subtype_classifier.py | REUSE PARTIALLY / REFACTOR | Classifier candidates and validation metrics are useful for R7, but the script discovers all numeric genomic columns, uses engineer split CSVs, and does not preserve the current subtype contract. |
| train_track_c.py | REUSE PARTIALLY / REFACTOR | Only its subtype-classification ideas are candidates for R7. Its survival section selects the best Cox model using test C-index, expands the clinical contract, and must not be retained. |
| validate_data.py | REFERENCE ONLY | Its split-overlap checks are valid ideas, but current R2/R3 validation is stronger, checksum-aware, and bound to the authoritative manifest. |
| evaluate_subtype.py | REUSE PARTIALLY / REFACTOR | Accuracy, macro-F1, and confusion-matrix reporting are useful for R7, but feature discovery is dynamic, artifacts are untrusted pickles, and final test evaluation needs a later explicit gate. |
| evaluate_survival.py | DO NOT USE | It fits a new SimpleImputer on test data, reconstructs columns ad hoc, reinverts active survival status if pointed at Cognivex data, and includes placeholder/hard-coded performance values. |
| generate_feature_importance.py | REUSE PARTIALLY / REFACTOR | Coefficient extraction can inform R8, but genomic identification is prefix-based, exact-zero Lasso selection is brittle, pickles are loaded without a trust gate, and causal/biological claims are unsupported. |
| prepare_data.py | DO NOT USE | It targets the rejected 1332/191/381 split, regenerates manifest/mapping files, and creates an event column by inversion. Active R2 preparation and the locked manifest remain authoritative. |

## Dependencies

- Installed: {'pandas': '2.3.3', 'scikit-learn': '1.9.1', 'lifelines': '0.30.3', 'numpy': '2.5.3'}
- Missing: ['tabulate']
- Conflicts: []

## Blockers

- None.

## Confirmations

- Existing Cognivex R2-R5 data lineage was preserved.
- ai_handoff_data/v1 was not made the active dataset.
- No new model was trained.
- R6 Track B implementation was not started.
- R7 and R8 were not started.
