# Data Strategy & Modeling Plan

## Dataset
- **Source:** METABRIC (team-provided pre-split subset, 1,904 patients total)
- **Splits:**
  - `train_dataset.csv` — 1,332 patients (70%)
  - `validation_dataset.csv` — 191 patients (10%)
  - `test_dataset.csv` — 381 patients (20%)
- **Features:** 68 curated genomic features (50 gene expression + 18 mutation binary flags) listed in `selected_features.txt`, plus 30 clinical columns.

## Evaluation Protocol
Splits are **pre-defined by the research team** and locked to prevent data leakage. All preprocessing (imputation, scaling, one-hot encoding) is fitted **strictly on the train split** and applied to validation/test.

> **Survival event encoding**: `event = 1 - overall_survival` (1=Deceased, 0=Living/Censored)

## Track Descriptions

| Track | Script | Task | Primary Metric |
|-------|--------|------|---------------|
| **A** | `train_clinical_survival.py` | Clinical-only Cox PH survival | C-Index |
| **B** | `train_genomic_survival.py` | Clinical + Genomic Lasso Cox PH survival | C-Index (lift over A) |
| **C** | `train_track_c.py` | Selected genes + mutations: Cox PH + 5 subtype classifiers | C-Index / Macro F1 |
| **D** | `generate_feature_importance.py` | Ranked prognostic gene importance from Track B Lasso | |β| coefficient |

## Results (Test Set)
- **Track A:** C-Index = 0.6652
- **Track B:** C-Index = 0.6712 (+0.0061 lift)
- **Track C (Cox):** C-Index = 0.6598
- **Track C (Classification):** Random Forest Macro F1 = 0.8030, Acc = 82.4%
- **Track D:** Top risk gene = `aurka` (HR=1.11), top protective = `gata3_mut` (HR=0.91)

## Limitations
- Gene importance rankings are correlational, not proof of biological causality.
- Lasso Cox coefficients are sensitive to regularisation strength; p-values should be interpreted cautiously.