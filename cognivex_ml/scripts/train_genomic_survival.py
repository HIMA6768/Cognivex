import os
import pandas as pd
import pickle
import logging
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

def train_genomic_model():
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)

    logging.info("Loading pre-split datasets for Track B (Genomic Survival)...")
    train_df = load_split(TRAIN_CSV, 'train')
    val_df   = load_split(VAL_CSV,   'validation')
    test_df  = load_split(TEST_CSV,  'test')

    logging.info(f"Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")

    continuous_clinical  = ['age_at_diagnosis', 'tumor_size', 'lymph_nodes_examined_positive']
    categorical_clinical = ['tumor_stage', 'er_status_measured_by_ihc', 'pr_status', 'her2_status']
    survival_cols        = ['overall_survival_months', 'event']

    non_genomic_cols = (continuous_clinical + categorical_clinical + survival_cols +
                        ['patient_id', 'split', 'overall_survival', 'death_from_cancer',
                         'cancer_type', 'cancer_type_detailed', 'oncotree_code',
                         'pam50_+_claudin-low_subtype', 'integrative_cluster',
                         'tumor_other_histologic_subtype', 'inferred_menopausal_state',
                         'type_of_breast_surgery', 'primary_tumor_laterality',
                         'cellularity', 'chemotherapy', 'hormone_therapy', 'radio_therapy',
                         'neoplasm_histologic_grade', 'nottingham_prognostic_index',
                         'mutation_count', 'cohort', 'her2_status_measured_by_snp6',
                         'er_status', '3-gene_classifier_subtype'])

    genomic_cols = [c for c in train_df.columns
                    if c not in non_genomic_cols and pd.api.types.is_numeric_dtype(train_df[c])]
    logging.info(f"Identified {len(genomic_cols)} genomic features.")

    # Clinical preprocessing
    logging.info("Applying leak-safe clinical preprocessing...")
    imputer = SimpleImputer(strategy='median')
    train_clin_cont = pd.DataFrame(imputer.fit_transform(train_df[continuous_clinical]),
                                   columns=continuous_clinical, index=train_df.index)
    val_clin_cont   = pd.DataFrame(imputer.transform(val_df[continuous_clinical]),
                                   columns=continuous_clinical, index=val_df.index)
    test_clin_cont  = pd.DataFrame(imputer.transform(test_df[continuous_clinical]),
                                   columns=continuous_clinical, index=test_df.index)

    train_clin_cat = pd.get_dummies(train_df[categorical_clinical], drop_first=True)
    val_clin_cat   = pd.get_dummies(val_df[categorical_clinical],   drop_first=True)
    test_clin_cat  = pd.get_dummies(test_df[categorical_clinical],  drop_first=True)
    val_clin_cat   = val_clin_cat.reindex(columns=train_clin_cat.columns, fill_value=0)
    test_clin_cat  = test_clin_cat.reindex(columns=train_clin_cat.columns, fill_value=0)

    # Genomic standardization
    logging.info("Applying leak-safe genomic standardization (Lasso)...")
    scaler = StandardScaler()
    train_genomic_scaled = pd.DataFrame(scaler.fit_transform(train_df[genomic_cols].fillna(0)),
                                        columns=genomic_cols, index=train_df.index)
    val_genomic_scaled   = pd.DataFrame(scaler.transform(val_df[genomic_cols].fillna(0)),
                                        columns=genomic_cols, index=val_df.index)
    test_genomic_scaled  = pd.DataFrame(scaler.transform(test_df[genomic_cols].fillna(0)),
                                        columns=genomic_cols, index=test_df.index)

    train_final = pd.concat([train_clin_cont, train_clin_cat, train_genomic_scaled, train_df[survival_cols]], axis=1)
    val_final   = pd.concat([val_clin_cont,   val_clin_cat,   val_genomic_scaled,   val_df[survival_cols]],   axis=1)
    test_final  = pd.concat([test_clin_cont,  test_clin_cat,  test_genomic_scaled,  test_df[survival_cols]],  axis=1)

    logging.info("Tuning Regularized (Lasso) Clinical + Genomic Cox PH Model...")
    penalizers = [0.05, 0.1, 0.2, 0.5]
    best_c_index = -1
    best_model   = None
    best_penalizer = None

    for p in penalizers:
        try:
            cph = CoxPHFitter(penalizer=p, l1_ratio=1.0)
            cph.fit(train_final, duration_col='overall_survival_months', event_col='event',
                    fit_options={'step_size': 0.1})
            val_score = cph.score(val_final, scoring_method="concordance_index")
            logging.info(f"  Lasso p={p} -> Val C-Index: {val_score:.4f}")
            if val_score > best_c_index:
                best_c_index   = val_score
                best_model     = cph
                best_penalizer = p
        except Exception as e:
            logging.warning(f"  Lasso p={p} failed: {e}")

    if best_model is None:
        logging.error("Failed to fit any models!")
        return

    logging.info(f"Selected Best Penalizer: {best_penalizer} (Val C-Index: {best_c_index:.4f})")

    train_c_index = best_model.score(train_final, scoring_method="concordance_index")
    test_c_index  = best_model.score(test_final,  scoring_method="concordance_index")
    logging.info(f"Final Train C-Index: {train_c_index:.4f}")
    logging.info(f"Final Val   C-Index: {best_c_index:.4f}")
    logging.info(f"Final Test  C-Index: {test_c_index:.4f}")

    model_path  = os.path.join(MODELS_DIR, "clinical_genomic_survival_model.pkl")
    scaler_path = os.path.join(MODELS_DIR, "genomic_scaler.pkl")

    with open(model_path, "wb") as f:
        pickle.dump(best_model, f)
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)

    logging.info(f"Saved Lasso model and genomic scaler to {MODELS_DIR}")

if __name__ == "__main__":
    train_genomic_model()