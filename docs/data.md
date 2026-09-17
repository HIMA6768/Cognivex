# Canonical R2 data handoff

The corrected `Breast_Cancer_Data_Handoff_Corrected.zip` is the canonical R2 handoff. It is extracted once under `data/metabric/`; the application never depends on the original ZIP or an absolute machine path.

`raw/METABRIC_RNA_Mutation.csv` is immutable source data. `prepared/METABRIC_prepared.csv` is the canonical prepared dataset used for application cohort records. The service validates the preserved SHA-256 evidence for immutable source artifacts before trusting aggregate cohort summaries.

The service validates 693 declared columns, clinical/survival/subtype metadata, unique identifiers, one-to-one patient/sample mapping, and the locked 1,332/286/286 train/validation/test partition. It renders aggregate counts only.

The original `dataset_provenance.json` and `SHA256SUMS.txt` are preserved as received. The direct verified Kaggle provenance is recorded separately in [data_provenance_resolution.md](data_provenance_resolution.md). The R2 preparation script reproduces dataset semantics, not cross-version byte-identical serialization.

Use de-identified public research data only unless explicitly authorized otherwise. Do not upload, log, or render personally identifiable health information.
