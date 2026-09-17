# Model training boundary

Predictive training is not implemented in R4.

R4 uses the immutable patient-level manifest and fits approved imputation, encoding, and Track B scaling on training data only. Validation/test data are transform-only. Future cross-validation must receive the complete preprocessing-plus-model pipeline so each fold fits its preprocessing independently; preprocessing must not be fitted once on the entire locked training partition before cross-validation.

The clinical-only survival baseline, clinical-plus-genomic prognosis model, subtype classifier, and gene-level interpretation each require a versioned experiment record. R4 performs no outcome-driven feature selection and includes no mutation features.
