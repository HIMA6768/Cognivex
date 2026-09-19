# Limitations

R5A is a research-only development baseline, not a validated biomedical analysis or clinical prognosis system. It has one clinical-only Cox PH model and internal train/validation metrics, but no held-out test evaluation, external validation, calibration, subtype classifier, gene importance, biological validation, patient-facing prediction, production persistence, or monitoring integration.

The supplied clinical columns, genomic identifiers, survival endpoints, event definition, subtype labels, and mutation annotations are handoff metadata, not validated scientific conclusions. R3's 1,200-month duration sentinel is an engineering review prompt, not a medical threshold. R4/R4D preprocessing policies are engineering contracts rather than evidence of model validity. The 5% mutation threshold is frozen engineering policy, while the observed 27 genes and 44 outputs are dataset-specific evidence and may differ inside future CV folds.

The R5A validation C-index of 0.650696 is development evidence on one locked internal validation split. PH diagnostics flagged five terms, including age and three categorical contrasts, and Stage 4 has a wide confidence interval. No automatic remedy was authorized. The condition number (966.312676) records scale/conditioning evidence but is not by itself proof of instability or validity. Local pickle artifacts are trusted-machine-only and unsafe to load from unverified sources.

The application is a research and educational prototype. It is not validated for diagnosis, prognosis in patient care, treatment selection, or any clinical decision. It must not receive identifiable patient information.
