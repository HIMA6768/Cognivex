# Model integration boundary

R1 contains no fitted model, model adapter, artifact loader, mock prediction, or evaluation result.

Future survival and subtype adapters must return the framework-independent contracts in `src/contracts/analysis.py`. Their exact inputs cannot be frozen until the selected cohort supplies verified clinical fields, genomic identifiers, outcome definitions, subtype labels, and preprocessing requirements.

The survival baseline is expected to use a censoring-aware method such as Cox proportional hazards. The clinical-plus-genomic model must be evaluated on a fair, leak-safe comparison. Subtype classification is a separate multi-class task. These statements describe future boundaries, not completed models or results.

Model names, versions, experiment IDs, preprocessing versions, artifacts, hyperparameters, and metrics remain pending verified handoff.
