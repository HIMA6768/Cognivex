import os
import pandas as pd
import pickle
import logging
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "..", "data")
MODELS_DIR = os.path.join(BASE_DIR, "..", "models")

TRAIN_CSV = os.path.join(DATA_DIR, "train_dataset.csv")
VAL_CSV   = os.path.join(DATA_DIR, "validation_dataset.csv")
TEST_CSV  = os.path.join(DATA_DIR, "test_dataset.csv")

NON_GENOMIC = [
    'patient_id', 'split', 'overall_survival', 'overall_survival_months',
    'death_from_cancer', 'cancer_type', 'cancer_type_detailed', 'oncotree_code',
    'pam50_+_claudin-low_subtype', 'integrative_cluster',
    'tumor_other_histologic_subtype', 'inferred_menopausal_state',
    'type_of_breast_surgery', 'primary_tumor_laterality',
    'cellularity', 'chemotherapy', 'hormone_therapy', 'radio_therapy',
    'neoplasm_histologic_grade', 'nottingham_prognostic_index', 'mutation_count',
    'cohort', 'her2_status_measured_by_snp6', 'er_status',
    '3-gene_classifier_subtype', 'age_at_diagnosis', 'tumor_size',
    'lymph_nodes_examined_positive', 'tumor_stage', 'er_status_measured_by_ihc',
    'pr_status', 'her2_status',
]

def load_split(path, split_name):
    df = pd.read_csv(path, low_memory=False)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    df = df.replace('Positve', 'Positive')
    df['split'] = split_name
    return df

def train_subtype_models():
    logging.info("Loading pre-split datasets for Subtype Classification...")
    train_df = load_split(TRAIN_CSV, 'train')
    val_df   = load_split(VAL_CSV,   'validation')
    test_df  = load_split(TEST_CSV,  'test')

    target_col = 'pam50_+_claudin-low_subtype'

    for name, df in [('train', train_df), ('val', val_df), ('test', test_df)]:
        df = df[df[target_col].notna() & (df[target_col] != 'NC')]
        if name == 'train': train_df = df
        elif name == 'val': val_df = df
        else: test_df = df

    logging.info(f"After filtering NC - Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")

    genomic_cols = [c for c in train_df.columns
                    if c not in NON_GENOMIC and pd.api.types.is_numeric_dtype(train_df[c])]
    logging.info(f"Genomic features: {len(genomic_cols)}")

    X_train = train_df[genomic_cols].fillna(0)
    y_train = train_df[target_col]
    X_val   = val_df[genomic_cols].fillna(0)
    y_val   = val_df[target_col]

    models = {
        "LogisticRegression": LogisticRegression(max_iter=2000, random_state=42, class_weight='balanced'),
        "RandomForest":       RandomForestClassifier(n_estimators=200, random_state=42,
                                                     n_jobs=-1, class_weight='balanced'),
        "GradientBoosting":   HistGradientBoostingClassifier(random_state=42, max_iter=200),
    }

    best_model_name = None
    best_macro_f1   = -1

    for name, model in models.items():
        logging.info(f"Training {name} on {len(genomic_cols)} genomic features...")
        model.fit(X_train, y_train)
        y_pred    = model.predict(X_val)
        macro_f1  = f1_score(y_val, y_pred, average='macro', zero_division=0)
        acc       = accuracy_score(y_val, y_pred)
        logging.info(f"  {name} Val — Acc: {acc:.4f}, Macro F1: {macro_f1:.4f}")

        model_path = os.path.join(MODELS_DIR, f"subtype_classifier_{name.lower()}.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(model, f)

        if macro_f1 > best_macro_f1:
            best_macro_f1   = macro_f1
            best_model_name = name

    logging.info(f"Best model (Validation Macro F1): {best_model_name} ({best_macro_f1:.4f})")

if __name__ == "__main__":
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
    train_subtype_models()