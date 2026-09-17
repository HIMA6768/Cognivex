# Model integration boundary

R4 contains no fitted predictive model, model adapter, artifact loader, mock prediction, or evaluation result.

Future survival and subtype adapters must return the framework-independent contracts in `src/contracts/analysis.py` and consume the approved task-specific factories in `src/preprocessing/`. Track A supplies 16 transformed clinical features, Track B supplies 16 clinical plus 489 scaled mRNA features, and Track C supplies 489 unscaled canonical expression Z-scores.

The survival baseline is expected to use a censoring-aware method such as Cox proportional hazards. The clinical-plus-genomic model must be evaluated on a fair, leak-safe comparison. Subtype classification is a separate multi-class task. These statements describe future boundaries, not completed models or results.

Track C target normalization remains outside X. If R7 selects a scale-sensitive classifier, scaling must be added inside that future estimator pipeline and fitted within training/CV folds. Model names, versions, experiment IDs, fitted artifacts, hyperparameters, and metrics remain pending.
