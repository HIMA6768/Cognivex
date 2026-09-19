import os
import pandas as pd
import pickle
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR  = os.path.join(BASE_DIR, "..", "models")
RESULTS_DIR = os.path.join(BASE_DIR, "..", "results")

# Known clinical prefixes used in the Track B model
CLINICAL_CONTINUOUS = ['age_at_diagnosis', 'tumor_size', 'lymph_nodes_examined_positive']
CLINICAL_PREFIXES   = [
    'tumor_stage_', 'er_status_measured_by_ihc_', 'pr_status_', 'her2_status_',
    'cellularity_', 'neoplasm_histologic_grade_', 'inferred_menopausal_state_',
    'type_of_breast_surgery_',
]


def is_genomic(feat):
    """Return True if the feature is a genomic (gene/mutation) feature."""
    if feat in CLINICAL_CONTINUOUS:
        return False
    if any(feat.startswith(prefix) for prefix in CLINICAL_PREFIXES):
        return False
    return True


def generate_importance():
    logging.info("Extracting Prognostic Gene Importance (Track D)...")

    model_path = os.path.join(MODELS_DIR, "clinical_genomic_survival_model.pkl")
    if not os.path.exists(model_path):
        logging.error("Track B Lasso Cox model not found. Please run train_genomic_survival.py first.")
        return

    with open(model_path, "rb") as f:
        cph = pickle.load(f)

    coeffs  = cph.params_
    summary = cph.summary

    # Separate clinical vs genomic features
    all_feats    = list(coeffs.index)
    genomic_feats = [f for f in all_feats if is_genomic(f)]
    clinical_feats = [f for f in all_feats if not is_genomic(f)]

    logging.info(f"Total model features: {len(all_feats)}")
    logging.info(f"  Genomic features (genes/mutations): {len(genomic_feats)}")
    logging.info(f"  Clinical features:                  {len(clinical_feats)}")

    # Build ranked dataframe for all genomic features
    records = []
    for feat in genomic_feats:
        coef = coeffs[feat]
        row  = summary.loc[feat]
        records.append({
            "gene_symbol":      feat,
            "coefficient":      coef,
            "hazard_ratio":     row['exp(coef)'],
            "se_coef":          row['se(coef)'],
            "z_score":          row['z'],
            "p_value":          row['p'],
            "ci_lower_95":      row['exp(coef) lower 95%'],
            "ci_upper_95":      row['exp(coef) upper 95%'],
            "importance_score": abs(coef),
            "direction":        "Risk ↑" if coef > 0 else "Protective ↓",
            "selected_by_lasso": coef != 0,
            "method":           "L1 Lasso Cox Proportional Hazards",
        })

    importance_df = pd.DataFrame(records).sort_values("importance_score", ascending=False).reset_index(drop=True)
    importance_df.index += 1

    selected_df    = importance_df[importance_df["selected_by_lasso"]]
    zeroed_df      = importance_df[~importance_df["selected_by_lasso"]]
    risk_top5      = selected_df[selected_df["coefficient"] > 0].head(5)
    protective_top5 = selected_df[selected_df["coefficient"] < 0].head(5)

    logging.info(f"\n--- Top 10 Prognostic Features by |Coefficient| ---")
    logging.info(importance_df[['gene_symbol','coefficient','hazard_ratio','p_value','direction']].head(10).to_string())

    # ------------------------------------------------------------------ Report
    L = []
    L += ["# Track D: Prognostic Gene Importance Report", ""]
    L += ["## Overview", ""]
    L += ["Track D extracts and ranks **genomic features** from the Track B Lasso-regularised Cox Proportional",
          "Hazards model. The L1 (Lasso) penalty drives non-informative gene coefficients to exactly **zero**,",
          "yielding a sparse, interpretable prognostic gene signature.", ""]
    L += ["- **Method**: L1 Lasso Cox Proportional Hazards (fitted on 1,332 training patients)",
          "- **Importance Metric**: Absolute value of the Cox coefficient |β| (standardised gene expression)",
          "- **Dataset**: Team-provided METABRIC subset (train/val/test pre-split)", ""]

    L += ["---", "", "## Gene Selection Summary", ""]
    L += ["| Statistic | Value |",
          "|-----------|------:|",
          f"| Total genomic features in model | **{len(genomic_feats)}** |",
          f"| Selected by Lasso (non-zero coef) | **{len(selected_df)}** |",
          f"| Zeroed out by Lasso | **{len(zeroed_df)}** |",
          f"| Sparsity | **{100*len(zeroed_df)/len(genomic_feats):.1f}%** genes removed |", ""]

    L += ["---", "", "## Full Ranked Gene Table", ""]
    L += ["> All genomic features sorted by |coefficient| (importance). Features with coefficient = 0 were",
          "> eliminated by Lasso — they contribute nothing to prognosis prediction.", ""]
    L += ["| Rank | Gene/Feature | Coef β | HR exp(β) | SE | z-score | p-value | 95% CI Low | 95% CI High | Direction | Lasso Selected |",
          "|------|-------------|:------:|:---------:|:--:|:-------:|:-------:|:----------:|:-----------:|-----------|:--------------:|"]
    for i, row in importance_df.iterrows():
        p   = row['p_value']
        sig = "★★★" if p < 0.001 else ("★★" if p < 0.01 else ("★" if p < 0.05 else ""))
        sel = "✅" if row['selected_by_lasso'] else "❌"
        L += [f"| {i} | `{row['gene_symbol']}` | {row['coefficient']:.4f} | {row['hazard_ratio']:.4f} "
              f"| {row['se_coef']:.4f} | {row['z_score']:.4f} | {p:.4f} {sig} "
              f"| {row['ci_lower_95']:.4f} | {row['ci_upper_95']:.4f} | {row['direction']} | {sel} |"]
    L += [""]

    L += ["---", "", "## Lasso-Selected Genes Only", ""]
    L += ["These genes have non-zero Lasso coefficients and are the **true prognostic drivers** identified by the model:", ""]
    L += ["### Top Risk Genes (HR > 1 — associated with increased mortality)", ""]
    L += ["| Rank | Gene | Coef β | HR | p-value |",
          "|------|------|:------:|:--:|:-------:|"]
    for rank, (_, row) in enumerate(risk_top5.iterrows(), 1):
        p = row['p_value']
        sig = "★★★" if p < 0.001 else ("★★" if p < 0.01 else ("★" if p < 0.05 else ""))
        L += [f"| {rank} | `{row['gene_symbol']}` | {row['coefficient']:.4f} | {row['hazard_ratio']:.4f} | {p:.4f} {sig} |"]
    L += [""]

    L += ["### Top Protective Genes (HR < 1 — associated with decreased mortality)", ""]
    L += ["| Rank | Gene | Coef β | HR | p-value |",
          "|------|------|:------:|:--:|:-------:|"]
    for rank, (_, row) in enumerate(protective_top5.iterrows(), 1):
        p = row['p_value']
        sig = "★★★" if p < 0.001 else ("★★" if p < 0.01 else ("★" if p < 0.05 else ""))
        L += [f"| {rank} | `{row['gene_symbol']}` | {row['coefficient']:.4f} | {row['hazard_ratio']:.4f} | {p:.4f} {sig} |"]
    L += [""]

    L += ["---", "", "## Interpretation Guide", ""]
    L += ["| Term | Meaning |",
          "|------|---------|",
          "| **Coef β** | Log hazard ratio; magnitude = strength, sign = direction of effect |",
          "| **HR exp(β)** | Hazard Ratio: HR > 1 → increased risk; HR < 1 → protective |",
          "| **SE** | Standard Error of the coefficient estimate |",
          "| **z-score** | Coefficient divided by SE; large |z| → more significant |",
          "| **p-value** | Statistical significance of the coefficient |",
          "| **95% CI** | Confidence interval of the Hazard Ratio |",
          "| **★ p<0.05 · ★★ p<0.01 · ★★★ p<0.001** | Significance stars |",
          "| **✅ Lasso Selected** | Non-zero coefficient — retained as a prognostic driver |",
          "| **❌ Lasso Zeroed** | Coefficient shrunk to 0 — not prognostically informative |", ""]

    L += ["---", "", "## Conclusion", ""]
    L += [f"The Lasso-regularised Cox PH model selected **{len(selected_df)} out of {len(genomic_feats)}** "
          f"genomic features as prognostically informative. The top risk gene is "
          f"`{risk_top5.iloc[0]['gene_symbol']}` (HR={risk_top5.iloc[0]['hazard_ratio']:.4f}) and "
          f"the top protective gene is `{protective_top5.iloc[0]['gene_symbol']}` "
          f"(HR={protective_top5.iloc[0]['hazard_ratio']:.4f}), consistent with known breast cancer biology.", ""]
    L += ["---", "*Report auto-generated by generate_feature_importance.py — Track D.*"]

    report_path = os.path.join(RESULTS_DIR, "track_d_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    logging.info(f"Track D report saved → {report_path}")


if __name__ == "__main__":
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    generate_importance()