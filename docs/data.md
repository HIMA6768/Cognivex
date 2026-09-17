# Canonical METABRIC data handoff and R3 quality layer

The corrected `Breast_Cancer_Data_Handoff_Corrected.zip` is the canonical R2 handoff. It is extracted once under `data/metabric/`; the application never depends on the original ZIP or an absolute machine path.

`raw/METABRIC_RNA_Mutation.csv` is immutable source data. `prepared/METABRIC_prepared.csv` is the canonical prepared dataset used for application cohort records. The service validates the preserved SHA-256 evidence for immutable source artifacts before trusting aggregate cohort summaries.

The service validates 693 declared columns, clinical/survival/subtype metadata, unique identifiers, one-to-one patient/sample mapping, and the locked 1,332/286/286 train/validation/test partition. It renders aggregate counts only.

R3 begins only after that R2 result is `DATA_READY`. It reads the prepared data and existing R2 metadata/mapping/manifest without mutation, and reports aggregate engineering-quality findings. The canonical scan reports no errors, 3 warnings (20 missing tumor-size values, 30 missing ER-IHC values, and one zero survival duration), and 6 information findings. See [data_quality.md](data_quality.md) for the complete rule set and boundary.

R4 reads the same prepared dataset and locked manifest after the R2/R3 gates. It computes separate Track A/B/C eligibility, selects predictors by explicit metadata allowlists, and fits preprocessing only on eligible locked-training rows. It does not write transformed matrices or modify source artifacts. See [preprocessing.md](preprocessing.md).

The original `dataset_provenance.json` and `SHA256SUMS.txt` are preserved as received. The direct verified Kaggle provenance is recorded separately in [data_provenance_resolution.md](data_provenance_resolution.md). The R2 preparation script reproduces dataset semantics, not cross-version byte-identical serialization.

Use de-identified public research data only unless explicitly authorized otherwise. Do not upload, log, or render personally identifiable health information.
