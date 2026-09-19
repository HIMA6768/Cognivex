import os
import pandas as pd
import pickle
import logging
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "..", "data")
MODELS_DIR  = os.path.join(BASE_DIR, "..", "models")
RESULTS_DIR = os.path.join(BASE_DIR, "..", "results")

TEST_CSV = os.path.join(DATA_DIR, "test_dataset.csv")

NON_GENOMIC = [
    'patient_id', 'split', 'overall_survival', 'overall_survival_months', 'event',
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

def evaluate_subtype():
    logging.info("Evaluating Subtype Classifiers...")
    df = pd.read_csv(TEST_CSV, low_memory=False)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    target_col = 'pam50_+_claudin-low_subtype'
    df = df[df[target_col].notna() & (df[target_col] != 'NC')].copy()
    logging.info(f"Test set (after NC filter): {len(df)} patients")

    genomic_cols = [c for c in df.columns
                    if c not in NON_GENOMIC and pd.api.types.is_numeric_dtype(df[c])]

    X_test = df[genomic_cols].fillna(0)
    y_test = df[target_col]

    models = ["LogisticRegression", "RandomForest", "GradientBoosting"]
    results = []

    report_content  = "# Subtype Classification Evaluation (Track B Sub-Task)\n\n"
    report_content += "Evaluates three classifiers trained on the full genomic feature set to predict PAM50+Claudin-Low subtype.\n\n"

    for name in models:
        model_path = os.path.join(MODELS_DIR, f"subtype_classifier_{name.lower()}.pkl")
        if not os.path.exists(model_path):
            logging.warning(f"Model not found for {name}, skipping.")
            continue

        with open(model_path, "rb") as f:
            clf = pickle.load(f)

        y_pred      = clf.predict(X_test)
        acc         = accuracy_score(y_test, y_pred)
        macro_f1    = f1_score(y_test, y_pred, average='macro',    zero_division=0)
        weighted_f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)

        results.append((name, acc, macro_f1, weighted_f1))
        logging.info(f"{name} — Test Acc: {acc:.4f}, Macro F1: {macro_f1:.4f}")

        report_content += f"## Model: {name}\n\n"
        report_content += f"| Metric | Value |\n|--------|-------|\n"
        report_content += f"| Accuracy | {acc:.4f} |\n"
        report_content += f"| Macro F1 | {macro_f1:.4f} |\n"
        report_content += f"| Weighted F1 | {weighted_f1:.4f} |\n\n"

        cm = confusion_matrix(y_test, y_pred, labels=clf.classes_)
        cm_df = pd.DataFrame(cm, index=clf.classes_, columns=clf.classes_)
        report_content += "### Confusion Matrix\n\n"
        report_content += cm_df.to_markdown() + "\n\n"

    if results:
        best_model = max(results, key=lambda x: x[2])
        report_content += f"## Conclusion\n\nBest model by Macro F1: **{best_model[0]}** (Macro F1 = {best_model[2]:.4f}).\n"

    report_path = os.path.join(RESULTS_DIR, "track_c_subtype_evaluation_report.md")
    with open(report_path, "w") as f:
        f.write(report_content)
    logging.info(f"Generated subtype report at {report_path}")

if __name__ == "__main__":
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    evaluate_subtype()
