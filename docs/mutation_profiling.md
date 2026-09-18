# R4D-P0 locked-training mutation profiling

R4D-P0 produces descriptive evidence from the immutable canonical METABRIC prepared dataset and locked manifest. It is not a Track D preprocessing contract, a mutation-feature selection step, or model training.

Run the profile from the repository root:

```powershell
.venv\Scripts\python.exe -m scripts.profile_mutations
```

The command first requires R2 `DATA_READY`, joins the prepared data to the locked manifest by `patient_id`, and uses only rows where `split == "train"`. The canonical manifest determines the count; R4D-P0 does not assign or regenerate splits.

## Annotation interpretation

The canonical scan found one no-mutation representation across all 173 declared mutation fields: `"0"`. Empty/NA values are missing; numeric zero equivalents are treated as no reported mutation; every non-zero annotation string is counted as a reported mutation for profiling only. The profile records missing counts and uses valid training annotations as each gene's prevalence denominator.

## Evidence artifacts

- `results/mutation_profile_train.csv`: one row per mutation field, retained in canonical `feature_groups.json` order, with train-only prevalence and candidate flags.
- `results/mutation_burden_train.csv`: aggregate training-cohort mutation-burden statistics only.
- `results/mutation_profile_summary.json`: machine-readable aggregate counts and burden summary.
- `results/mutation_profile_train.md`: a concise descriptive summary and top 15 training-prevalence genes.

The 1%, 2%, 5%, and 10% columns are candidate comparison flags only. R4D-P0 does not select, endorse, or freeze a frequency threshold, create a production mutation-burden feature, change Track B, or create Track D preprocessing. The next policy decision belongs to the AI engineer after reviewing the artifacts.
