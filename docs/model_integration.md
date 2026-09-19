# Model integration boundary

R5A provides a Track A model adapter and trusted local artifact boundary. It does not expose model output through Streamlit and does not create patient-specific predictions.

Track A supplies 12 reference-coded clinical features. Track B remains 16 full-category clinical features plus 489 scaled mRNA features, Track C supplies 489 unscaled canonical expression Z-scores, and Track D supplies scaled continuous clinical/burden features plus unscaled full one-hot, missing-indicator, and fit-selected mutation-presence features.

The future Track D penalized Cox pipeline must include the entire Track D preprocessor so the 5% selector, imputers, and scalers refit inside every CV fold. Tracks A, B, and D must be compared on the same eligible evaluation population. The current 27 retained genes and 44 outputs describe only the full locked-training fit.

`artifacts/models/track_a/<experiment-id>/` contains `experiment.json`, `metrics.json`, `coefficients.csv`, `ph_diagnostics.csv`, `checksums.sha256`, and trusted local `preprocessor.pkl`/`cox_model.pkl`. Pickles are gitignored and must never be loaded from an untrusted source. Machine-readable evidence contains aggregate counts and cohort fingerprints, not patient identifiers.

Track C target normalization remains outside X. If R7 selects a scale-sensitive classifier, scaling must be added inside that future estimator pipeline and fitted within training/CV folds. Track B/D models and their model-specific artifacts remain pending.
