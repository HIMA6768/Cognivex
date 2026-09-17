# Model training boundary

Training is not implemented in R1.

Future training must split at patient level and fit imputation, scaling, filtering, and feature selection on training data only. Test data must not influence genomic feature selection. Subtype labels and outcome-derived variables must not leak into prognosis inputs.

The clinical-only survival baseline, clinical-plus-genomic prognosis model, subtype classifier, and gene-level interpretation each require a versioned experiment record and an approved dataset schema.
