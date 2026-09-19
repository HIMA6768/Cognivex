# Breast Cancer Survival & Subtype Analysis — AI Handoff

Multi-track machine learning pipeline for breast cancer prognosis using the METABRIC dataset (team-curated subset).

---

## Project Structure

```
ai_handoff/
├── data/
│   ├── train_dataset.csv          # 1,332 patients (training split)
│   ├── validation_dataset.csv     # 191 patients (validation split)
│   ├── test_dataset.csv           # 381 patients (test split)
│   ├── manifest.csv               # Patient-split index
│   ├── patient_mapping.csv        # Patient ID mapping
│   ├── selected_features.txt      # 68 team-selected genes & mutations (Track C)
│   └── clinical_schema.json       # Clinical column schema
│
├── scripts/
│   ├── prepare_data.py            # Generates manifest & patient_mapping from pre-split CSVs
│   ├── train_clinical_survival.py # Track A: Clinical Cox PH training
│   ├── train_genomic_survival.py  # Track B: Clinical + Genomic Lasso Cox PH training
│   ├── train_track_c.py           # Track C: Selected genes Cox PH + 5 subtype classifiers
│   ├── train_subtype_classifier.py# Subtype classifier training (full genomic feature set)
│   ├── evaluate_survival.py       # Evaluates Track A & B → track_a_report.md / track_b_report.md
│   ├── evaluate_subtype.py        # Evaluates subtype classifiers
│   ├── generate_feature_importance.py  # Track D: Gene importance → track_d_report.md
│   └── validate_data.py           # Data quality checks
│
├── models/                        # Saved model artifacts (.pkl)
├── results/
│   ├── track_a_report.md          # Track A detailed report
│   ├── track_b_report.md          # Track B detailed report
│   ├── track_c_report.md          # Track C detailed report (Cox + 5 classifiers)
│   └── track_d_report.md          # Track D gene importance report
│
├── docs/
│   └── data_strategy.md           # Modeling strategy & design decisions
├── requirements-train.txt         # Python dependencies
└── .gitignore
```

---

## Setup

```bash
pip install -r requirements-train.txt
```

**Required packages:** `pandas`, `scikit-learn`, `lifelines`, `tabulate`

---

## Running the Pipeline

Run scripts in order:

```bash
# 1. Generate manifest & patient mapping
python scripts/prepare_data.py

# 2. Train survival models
python scripts/train_clinical_survival.py   # Track A
python scripts/train_genomic_survival.py    # Track B

# 3. Train Track C (selected genes + mutations)
python scripts/train_track_c.py

# 4. Train subtype classifiers (full genomic feature set)
python scripts/train_subtype_classifier.py

# 5. Evaluate and generate reports
python scripts/evaluate_survival.py         # → track_a_report.md, track_b_report.md
python scripts/evaluate_subtype.py
python scripts/generate_feature_importance.py  # → track_d_report.md
```

---

## Results Summary

| Track | Model | Test Metric |
|-------|-------|-------------|
| **A** | Clinical Cox PH (Ridge) | C-Index = **0.6652** |
| **B** | Clinical + Genomic Lasso Cox PH | C-Index = **0.6712** (+0.006 lift) |
| **C** | Random Forest (selected 68 features) | Macro F1 = **0.8030**, Acc = **82.4%** |
| **D** | Top risk gene: `aurka` (HR=1.11) | Top protective: `gata3_mut` (HR=0.91) |

---

## Track C Feature Set

Track C uses **68 team-validated genomic features** (`data/selected_features.txt`):
- **50 gene expression features**: `gata3`, `aurka`, `egfr`, `erbb2`, `bcl2`, `pten`, ...
- **18 mutation binary flags**: `gata3_mut`, `egfr_mut`, `pten_mut`, `hras_mut`, ...

---

## Notes

- **Survival event encoding:** `event = 1 − overall_survival` (1=Deceased, 0=Censored/Living)
- All preprocessing transformations (imputer, scaler, one-hot encoder) are fitted **only on the training split** to prevent data leakage.
- Large model files and raw CSVs are excluded via `.gitignore`. Share datasets via secure file transfer or DVC.
