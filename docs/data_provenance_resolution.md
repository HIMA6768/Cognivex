# METABRIC provenance resolution

## Active R2 provenance

The canonical R2 package is **Breast Cancer Gene Expression Profiles (METABRIC)**, distributed through Kaggle:

- URL: `https://www.kaggle.com/datasets/raghadalharbi/breast-cancer-gene-expression-profiles-metabric`
- Kaggle owner: Raghad Alharbi
- Dataset file: `METABRIC_RNA_Mutation.csv`
- Dataset version: Version 1
- Cohort: 1,904 breast cancer patients
- Dataset structure: 693 columns, including 31 clinical attributes, mRNA gene-expression Z-score features, and gene-mutation features
- Kaggle license wording: Database: Open Database; Contents: Database Contents
- Original provenance: METABRIC clinical and genomic data sourced from cBioPortal

## Historical handoff metadata

`data/metabric/metadata/dataset_provenance.json` is preserved byte-for-byte from the corrected handoff package. It marks the URL, version, and license as pending because those details were absent from that earlier handoff artifact.

The direct user-provided provenance above is the active R2 resolution. This document resolves the discrepancy without silently rewriting the preserved historical metadata or its supplied checksum record.

## Research boundary

This provenance establishes a research-data source only. It does not establish clinical validity, authorize patient-care use, or provide any model result.
