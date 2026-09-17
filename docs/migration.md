# Problem-statement migration

The official hackathon problem changed after P8 from an auto-insurance image-assessment prototype to Breast Cancer Prognosis & Subtype Classification.

The complete P8 state was checkpointed on `codex/r1-biomedical-domain-reset` as commit `3cb90f7` before migration. Superseded specifications, plans, and domain documents are stored under `docs/legacy/auto-insurance/`.

R1 deliberately preserves reusable Streamlit, configuration, contract, and test patterns while removing the former domain from the active application. This note records the change rather than rewriting project history.
