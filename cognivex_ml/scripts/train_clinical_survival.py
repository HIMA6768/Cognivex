import os
import pandas as pd
import pickle
import logging
import numpy as np
from lifelines import CoxPHFitter
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
MODELS_DIR = os.path.join(BASE_DIR, "..", "models")

TRAIN_CSV = os.path.join(DATA_DIR, "train_dataset.csv")
VAL_CSV   = os.path.join(DATA_DIR, "validation_dataset.csv")
TEST_CSV  = os.path.join(DATA_DIR, "test_dataset.csv")

def load_split(path, split_name):
    df = pd.read_csv(path, low_memory=False)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    df = df.replace('Positve', 'Positive')
    df['tumor_stage'] = df['tumor_stage'].fillna('Unknown').astype(str)
    # overall_survival: 1=Living (censored), 0=Died → event = 1 - overall_survival
    df['event'] = 1 - pd.to_numeric(df['overall_survival'], errors='coerce')
    df['split'] = split_name
    return df

def train_clinical_model():
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)

    logging.info("Loading pre-split datasets for Track A (Clinical Survival)...")
    train_df = load_split(TRAIN_CSV, 'train')
    val_df   = load_split(VAL_CSV,   'validation')
    test_df  = load_split(TEST_CSV,  'test')

    logging.info(f"Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")

    # -------------------------------------------------------------------------
    # Expanded feature set for maximum Track A C-index
    # Added: nottingham_prognostic_index, neoplasm_histologic_grade,
    #        chemotherapy, hormone_therapy, radio_therapy, mutation_count
    # -------------------------------------------------------------------------
    continuous_features = [
        'age_at_diagnosis',
        'tumor_size',
        'lymph_nodes_examined_positive',
        'nottingham_prognostic_index',
        'mutation_count',
    ]
    categorical_features = [
        'tumor_stage',
        'er_status_measured_by_ihc',
        'pr_status',
        'her2_status',
        'cellularity',
        'neoplasm_histologic_grade',
        'inferred_menopausal_state',
        'type_of_breast_surgery',
    ]
    binary_features = [
        'chemotherapy',
        'hormone_therapy',
        'radio_therapy',
    ]
    survival_cols = ['overall_survival_months', 'event']

    all_features = continuous_features + categorical_features + binary_features

    def prepare(df):
        subset = df[all_features + survival_cols].copy()
        # One-hot encode categoricals
        subset = pd.get_dummies(subset, columns=categorical_features, drop_first=True)
        return subset

    train_prep = prepare(train_df)
    val_prep   = prepare(val_df)
    test_prep  = prepare(test_df)

    # Align columns (train is master)
    val_prep  = val_prep.reindex(columns=train_prep.columns, fill_value=0)
    test_prep = test_prep.reindex(columns=train_prep.columns, fill_value=0)

    # Impute continuous features on train, apply to val/test
    logging.info("Imputing missing values (train-fit only)...")
    cont_cols_encoded = [c for c in train_prep.columns
                         if any(c == f or c.startswith(f + '_') for f in continuous_features + binary_features)
                         and c not in survival_cols]
    imputer = SimpleImputer(strategy='median')
    train_prep[continuous_features] = imputer.fit_transform(train_prep[continuous_features])
    val_prep[continuous_features]   = imputer.transform(val_prep[continuous_features])
    test_prep[continuous_features]  = imputer.transform(test_prep[continuous_features])

    # -------------------------------------------------------------------------
    # Hyperparameter Tuning: broader search including ElasticNet
    # -------------------------------------------------------------------------
    logging.info("Tuning Cox PH penalizer on validation set...")

    configs = [
        # (penalizer, l1_ratio, label)
        (0.0001, 0.0, "Ridge-0.0001"),
        (0.001,  0.0, "Ridge-0.001"),
        (0.005,  0.0, "Ridge-0.005"),
        (0.01,   0.0, "Ridge-0.01"),
        (0.05,   0.0, "Ridge-0.05"),
        (0.1,    0.0, "Ridge-0.1"),
        (0.01,   0.5, "EN-0.01"),
        (0.05,   0.5, "EN-0.05"),
        (0.01,   1.0, "Lasso-0.01"),
        (0.05,   1.0, "Lasso-0.05"),
    ]

    best_c_index   = -1
    best_model     = None
    best_label     = None

    for (p, l1, label) in configs:
        try:
            cph = CoxPHFitter(penalizer=p, l1_ratio=l1)
            cph.fit(train_prep, duration_col='overall_survival_months', event_col='event',
                    fit_options={'step_size': 0.5})
            val_score = cph.score(val_prep, scoring_method="concordance_index")
            logging.info(f"  [{label}] Val C-Index: {val_score:.4f}")
            if val_score > best_c_index:
                best_c_index = val_score
                best_model   = cph
                best_label   = label
        except Exception as e:
            logging.warning(f"  [{label}] Failed: {e}")

    logging.info(f"Selected Best Config: {best_label} (Val C-Index: {best_c_index:.4f})")

    train_c_index = best_model.score(train_prep, scoring_method="concordance_index")
    test_c_index  = best_model.score(test_prep,  scoring_method="concordance_index")

    logging.info(f"Final Train C-Index: {train_c_index:.4f}")
    logging.info(f"Final Val   C-Index: {best_c_index:.4f}")
    logging.info(f"Final Test  C-Index: {test_c_index:.4f}")

    # Save artifacts
    model_path   = os.path.join(MODELS_DIR, "clinical_survival_model.pkl")
    imputer_path = os.path.join(MODELS_DIR, "clinical_imputer.pkl")

    with open(model_path, "wb") as f:
        pickle.dump(best_model, f)
    with open(imputer_path, "wb") as f:
        pickle.dump(imputer, f)

    # Also persist the column order for evaluate_survival.py
    col_order_path = os.path.join(MODELS_DIR, "clinical_train_cols.pkl")
    with open(col_order_path, "wb") as f:
        pickle.dump(list(train_prep.columns), f)

    logging.info(f"Saved optimal model, imputer, and column order to {MODELS_DIR}")

if __name__ == "__main__":
    train_clinical_model()