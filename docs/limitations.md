# Limitations

R5A and R6 are research-only development models, not validated biomedical analyses or clinical prognosis systems. They provide one clinical-only and one clinical-plus-selected-genomic Cox model with one internal held-out comparison, but no external validation, calibration, subtype classifier, gene importance, biological validation, patient-facing prediction, production service, or monitoring integration.

The supplied clinical columns, genomic identifiers, survival endpoints, event definition, subtype labels, and mutation annotations are handoff metadata, not validated scientific conclusions. R3's 1,200-month duration sentinel is an engineering review prompt, not a medical threshold. R4/R4D preprocessing policies are engineering contracts rather than evidence of model validity. The 5% mutation threshold is frozen engineering policy, while the observed 27 genes and 44 outputs are dataset-specific evidence and may differ inside future CV folds.

The R5A validation C-index of 0.650696 is development evidence on one locked internal validation split. PH diagnostics flagged five terms, including age and three categorical contrasts, and Stage 4 has a wide confidence interval. No automatic remedy was authorized. The condition number (966.312676) records scale/conditioning evidence but is not by itself proof of instability or validity. Local pickle artifacts are trusted-machine-only and unsafe to load from unverified sources.

The imported engineer code and its reported metrics are reference evidence only. Its split, event loader, expanded clinical predictors, dynamic all-numeric feature discovery, test-driven survival selection, and saved pickle files are incompatible with direct adoption. The approved mutation-presence mapping resolves an input-contract decision only; it is not a trained feature effect, biological claim, or model-performance result.

R6 selected Track B from one small predefined regularization grid using one locked validation split. Track B underperformed Track A on validation by 0.006152 and outperformed it on the one-time test comparison by 0.015932. This mixed result does not prove genomic benefit, and test performance must not be used for retrospective model changes. The 68 selected genomic fields are an explicit engineer handoff contract, not a causal or biologically validated signature.

The application is a research and educational prototype. It is not validated for diagnosis, prognosis in patient care, treatment selection, or any clinical decision. It must not receive identifiable patient information.

## R7 limitations

- R7 reports internal locked-split performance only; it is not external validation, clinical validation, or evidence of diagnostic utility.
- The six classes and 68 predictors are dataset/handoff contracts, not causal biological findings.
- The Normal class has 24 eligible test examples and the lowest test F1 (0.523810); all per-class results require cautious interpretation.
- Candidate families and hyperparameters were predefined and intentionally small. The test result was not used to expand or revise them.
- NC exclusions apply only to Track C; no conclusion is made for those records.
- The persisted pickle pipeline is trusted-local only. No patient-facing inference, Streamlit result integration, calibration, deployment, or R8 feature-importance analysis exists.
