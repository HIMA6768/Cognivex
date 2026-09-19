# Model integration boundary

R5A and R6 provide Track A/Track B model adapters and trusted local artifact boundaries. They do not expose model output through Streamlit and do not create patient-specific predictions.

Track A supplies 12 reference-coded clinical features. The finalized R6 Track B pipeline supplies those same 12 clinical outputs plus 50 scaled selected expression features and 18 binary selected mutation-presence features, in a persisted 80-feature order. Track C supplies 489 unscaled canonical expression Z-scores, and Track D supplies scaled continuous clinical/burden features plus unscaled full one-hot, missing-indicator, and fit-selected mutation-presence features.

The future Track D penalized Cox pipeline must include the entire Track D preprocessor so the 5% selector, imputers, and scalers refit inside every CV fold. Tracks A, B, and D must be compared on the same eligible evaluation population. The current 27 retained genes and 44 outputs describe only the full locked-training fit. Track D model fitting remains deferred and unapproved.

`artifacts/models/track_a/<experiment-id>/` contains the frozen R5 evidence. `artifacts/models/track_b/<experiment-id>/` contains `metadata.json`, `metrics.json`, `feature_contract.json`, `validation_leaderboard.csv`, `report.md`, `audit.json`, `checksums.sha256`, and trusted local `preprocessor.pkl`/`cox_model.pkl`. Pickles are gitignored and must never be loaded from an untrusted source. Machine-readable evidence contains aggregate counts and cohort fingerprints, not patient identifiers or row-level predictions.

Track C target normalization remains outside X. If R7 selects a scale-sensitive classifier, scaling must be added inside that future estimator pipeline and fitted within training/CV folds. Track D modeling remains pending.

The imported `cognivex_ml/` directory is not on the active runtime path. Its data loaders must not consume canonical prepared data because they invert a source-status convention that canonical preparation has already inverted. Its saved models are untrusted reference artifacts and are gitignored. R6 preserves the annotation columns and derives exactly 18 binary mutation-presence predictors through `src.preprocessing.mutations.classify_mutation_annotation`: trimmed numeric zero is absent; a valid non-zero annotation is present; missing, boolean, blank, and non-finite malformed values are rejected. This deterministic conversion has no fitted statistics and is applied identically across splits.

## R7 Track C artifact boundary

The canonical bundle is `artifacts/models/track_c/r7-track-c-v1/`. `pipeline.pkl` is a trusted local artifact and is Git-ignored; it must never be loaded from an untrusted source. Committed files contain only aggregate metadata, feature/class contracts, validation leaderboard, final winner metrics, confusion matrix, classification report, report, checksums, and audit evidence. No patient identifiers, row predictions, or row probabilities are persisted.

Use `scripts/verify_track_c_artifacts.py --bundle artifacts/models/track_c/r7-track-c-v1` for read-only reload verification. R7 does not integrate the classifier into Streamlit or a patient-facing inference service; that boundary remains a later approved increment.

## R8 frozen R6 analysis boundary

R8 loads only the checksum-verified trusted-local R6 Track B artifacts. It analyzes the 68 genomic coefficients already fitted by R6—50 standardized expression and 18 unscaled mutation-presence features—and excludes all 12 encoded clinical outputs. It never calls model or preprocessor fitting, never loads engineer historical pickles, and never reads patient rows.

The persisted table keeps every coefficient. `abs(beta) > 1e-6` is a numerical activity label; rank is descending absolute beta with frozen genomic order for ties. Inferential values are descriptive and never affect selection or emphasis. Use `scripts/verify_prognostic_feature_artifacts.py` for read-only reproduction.
