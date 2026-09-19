# Track D: Prognostic Gene Importance Report

## Overview

Track D extracts and ranks **genomic features** from the Track B Lasso-regularised Cox Proportional
Hazards model. The L1 (Lasso) penalty drives non-informative gene coefficients to exactly **zero**,
yielding a sparse, interpretable prognostic gene signature.

- **Method**: L1 Lasso Cox Proportional Hazards (fitted on 1,332 training patients)
- **Importance Metric**: Absolute value of the Cox coefficient |β| (standardised gene expression)
- **Dataset**: Team-provided METABRIC subset (train/val/test pre-split)

---

## Gene Selection Summary

| Statistic | Value |
|-----------|------:|
| Total genomic features in model | **68** |
| Selected by Lasso (non-zero coef) | **68** |
| Zeroed out by Lasso | **0** |
| Sparsity | **0.0%** genes removed |

---

## Full Ranked Gene Table

> All genomic features sorted by |coefficient| (importance). Features with coefficient = 0 were
> eliminated by Lasso — they contribute nothing to prognosis prediction.

| Rank | Gene/Feature | Coef β | HR exp(β) | SE | z-score | p-value | 95% CI Low | 95% CI High | Direction | Lasso Selected |
|------|-------------|:------:|:---------:|:--:|:-------:|:-------:|:----------:|:-----------:|-----------|:--------------:|
| 1 | `aurka` | 0.1086 | 1.1147 | 0.0428 | 2.5403 | 0.0111 ★ | 1.0251 | 1.2122 | Risk ↑ | ✅ |
| 2 | `gata3_mut` | -0.0950 | 0.9094 | 0.0390 | -2.4330 | 0.0150 ★ | 0.8424 | 0.9817 | Protective ↓ | ✅ |
| 3 | `gsk3b` | 0.0840 | 1.0876 | 0.0383 | 2.1921 | 0.0284 ★ | 1.0089 | 1.1724 | Risk ↑ | ✅ |
| 4 | `bcl2` | -0.0208 | 0.9794 | 0.0471 | -0.4411 | 0.6591  | 0.8930 | 1.0742 | Protective ↓ | ✅ |
| 5 | `cbfb_mut` | -0.0159 | 0.9842 | 0.0355 | -0.4491 | 0.6533  | 0.9181 | 1.0551 | Protective ↓ | ✅ |
| 6 | `lama2_mut` | -0.0134 | 0.9867 | 0.0327 | -0.4103 | 0.6816  | 0.9254 | 1.0520 | Protective ↓ | ✅ |
| 7 | `hla-g` | -0.0046 | 0.9954 | 0.0372 | -0.1238 | 0.9015  | 0.9254 | 1.0707 | Protective ↓ | ✅ |
| 8 | `klrg1_mut` | -0.0046 | 0.9954 | 0.0258 | -0.1779 | 0.8588  | 0.9463 | 1.0471 | Protective ↓ | ✅ |
| 9 | `ctnna1` | 0.0000 | 1.0000 | 0.0002 | 0.0005 | 0.9996  | 0.9996 | 1.0004 | Risk ↑ | ✅ |
| 10 | `chek1` | 0.0000 | 1.0000 | 0.0001 | 0.0007 | 0.9995  | 0.9997 | 1.0003 | Risk ↑ | ✅ |
| 11 | `abcb1` | -0.0000 | 1.0000 | 0.0001 | -0.0008 | 0.9994  | 0.9998 | 1.0002 | Protective ↓ | ✅ |
| 12 | `erbb2` | 0.0000 | 1.0000 | 0.0001 | 0.0008 | 0.9993  | 0.9998 | 1.0002 | Risk ↑ | ✅ |
| 13 | `cdk1` | 0.0000 | 1.0000 | 0.0001 | 0.0009 | 0.9993  | 0.9998 | 1.0002 | Risk ↑ | ✅ |
| 14 | `mmp9` | 0.0000 | 1.0000 | 0.0001 | 0.0009 | 0.9993  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 15 | `ccnd2` | -0.0000 | 1.0000 | 0.0001 | -0.0009 | 0.9993  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 16 | `chek2_mut` | -0.0000 | 1.0000 | 0.0001 | -0.0009 | 0.9993  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 17 | `mapt` | -0.0000 | 1.0000 | 0.0001 | -0.0009 | 0.9993  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 18 | `erbb2_mut` | 0.0000 | 1.0000 | 0.0001 | 0.0010 | 0.9992  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 19 | `klrg1` | -0.0000 | 1.0000 | 0.0000 | -0.0010 | 0.9992  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 20 | `igf1r` | -0.0000 | 1.0000 | 0.0000 | -0.0010 | 0.9992  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 21 | `sox9` | 0.0000 | 1.0000 | 0.0000 | 0.0010 | 0.9992  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 22 | `gata3` | -0.0000 | 1.0000 | 0.0000 | -0.0010 | 0.9992  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 23 | `lama2` | -0.0000 | 1.0000 | 0.0000 | -0.0010 | 0.9992  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 24 | `hdac2` | 0.0000 | 1.0000 | 0.0000 | 0.0010 | 0.9992  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 25 | `psenen` | -0.0000 | 1.0000 | 0.0000 | -0.0010 | 0.9992  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 26 | `pdgfra` | -0.0000 | 1.0000 | 0.0000 | -0.0010 | 0.9992  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 27 | `egfr` | 0.0000 | 1.0000 | 0.0000 | 0.0010 | 0.9992  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 28 | `ccne1` | 0.0000 | 1.0000 | 0.0000 | 0.0009 | 0.9993  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 29 | `nr2f1` | 0.0000 | 1.0000 | 0.0000 | 0.0009 | 0.9993  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 30 | `tgfbr3` | -0.0000 | 1.0000 | 0.0000 | -0.0009 | 0.9993  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 31 | `cbfb` | 0.0000 | 1.0000 | 0.0000 | 0.0009 | 0.9993  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 32 | `cdc25a` | 0.0000 | 1.0000 | 0.0000 | 0.0009 | 0.9993  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 33 | `hras` | -0.0000 | 1.0000 | 0.0000 | -0.0008 | 0.9993  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 34 | `pten` | -0.0000 | 1.0000 | 0.0000 | -0.0008 | 0.9993  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 35 | `map2` | 0.0000 | 1.0000 | 0.0000 | 0.0008 | 0.9993  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 36 | `prkcz` | -0.0000 | 1.0000 | 0.0000 | -0.0008 | 0.9994  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 37 | `hsd17b11` | -0.0000 | 1.0000 | 0.0000 | -0.0008 | 0.9994  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 38 | `smad4` | 0.0000 | 1.0000 | 0.0000 | 0.0008 | 0.9994  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 39 | `egfr_mut` | 0.0000 | 1.0000 | 0.0000 | 0.0007 | 0.9994  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 40 | `rad51` | 0.0000 | 1.0000 | 0.0000 | 0.0007 | 0.9995  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 41 | `pten_mut` | -0.0000 | 1.0000 | 0.0000 | -0.0007 | 0.9995  | 0.9999 | 1.0001 | Protective ↓ | ✅ |
| 42 | `ctnna1_mut` | 0.0000 | 1.0000 | 0.0000 | 0.0006 | 0.9995  | 0.9999 | 1.0001 | Risk ↑ | ✅ |
| 43 | `foxo1_mut` | 0.0000 | 1.0000 | 0.0000 | 0.0006 | 0.9995  | 1.0000 | 1.0000 | Risk ↑ | ✅ |
| 44 | `ttyh1` | 0.0000 | 1.0000 | 0.0000 | 0.0006 | 0.9995  | 1.0000 | 1.0000 | Risk ↑ | ✅ |
| 45 | `prkcz_mut` | 0.0000 | 1.0000 | 0.0000 | 0.0005 | 0.9996  | 1.0000 | 1.0000 | Risk ↑ | ✅ |
| 46 | `nr3c1_mut` | -0.0000 | 1.0000 | 0.0000 | -0.0005 | 0.9996  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 47 | `csf1r` | -0.0000 | 1.0000 | 0.0000 | -0.0004 | 0.9997  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 48 | `arrdc1` | -0.0000 | 1.0000 | 0.0000 | -0.0004 | 0.9997  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 49 | `erbb3_mut` | 0.0000 | 1.0000 | 0.0000 | 0.0004 | 0.9997  | 1.0000 | 1.0000 | Risk ↑ | ✅ |
| 50 | `foxo1` | 0.0000 | 1.0000 | 0.0000 | 0.0003 | 0.9998  | 1.0000 | 1.0000 | Risk ↑ | ✅ |
| 51 | `mmp1` | -0.0000 | 1.0000 | 0.0000 | -0.0003 | 0.9998  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 52 | `lamb3` | -0.0000 | 1.0000 | 0.0000 | -0.0003 | 0.9998  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 53 | `nr3c1` | -0.0000 | 1.0000 | 0.0000 | -0.0003 | 0.9998  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 54 | `akr1c4` | -0.0000 | 1.0000 | 0.0000 | -0.0002 | 0.9998  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 55 | `mmp15` | 0.0000 | 1.0000 | 0.0000 | 0.0002 | 0.9998  | 1.0000 | 1.0000 | Risk ↑ | ✅ |
| 56 | `chek2` | 0.0000 | 1.0000 | 0.0000 | 0.0002 | 0.9998  | 1.0000 | 1.0000 | Risk ↑ | ✅ |
| 57 | `nr2f1_mut` | -0.0000 | 1.0000 | 0.0000 | -0.0002 | 0.9998  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 58 | `erbb3` | -0.0000 | 1.0000 | 0.0000 | -0.0002 | 0.9998  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 59 | `lamb3_mut` | 0.0000 | 1.0000 | 0.0000 | 0.0002 | 0.9999  | 1.0000 | 1.0000 | Risk ↑ | ✅ |
| 60 | `tsc2` | -0.0000 | 1.0000 | 0.0000 | -0.0002 | 0.9999  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 61 | `tgfbr2` | 0.0000 | 1.0000 | 0.0000 | 0.0001 | 0.9999  | 1.0000 | 1.0000 | Risk ↑ | ✅ |
| 62 | `ttyh1_mut` | 0.0000 | 1.0000 | 0.0000 | 0.0001 | 0.9999  | 1.0000 | 1.0000 | Risk ↑ | ✅ |
| 63 | `prkd1` | -0.0000 | 1.0000 | 0.0000 | -0.0001 | 0.9999  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 64 | `bmp6` | -0.0000 | 1.0000 | 0.0000 | -0.0001 | 0.9999  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 65 | `folr1` | -0.0000 | 1.0000 | 0.0000 | -0.0001 | 0.9999  | 1.0000 | 1.0000 | Protective ↓ | ✅ |
| 66 | `mlh1` | 0.0000 | 1.0000 | 0.0000 | 0.0001 | 0.9999  | 1.0000 | 1.0000 | Risk ↑ | ✅ |
| 67 | `hras_mut` | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 1.0000  | 1.0000 | 1.0000 | Risk ↑ | ✅ |
| 68 | `smad4_mut` | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 1.0000  | 1.0000 | 1.0000 | Risk ↑ | ✅ |

---

## Lasso-Selected Genes Only

These genes have non-zero Lasso coefficients and are the **true prognostic drivers** identified by the model:

### Top Risk Genes (HR > 1 — associated with increased mortality)

| Rank | Gene | Coef β | HR | p-value |
|------|------|:------:|:--:|:-------:|
| 1 | `aurka` | 0.1086 | 1.1147 | 0.0111 ★ |
| 2 | `gsk3b` | 0.0840 | 1.0876 | 0.0284 ★ |
| 3 | `ctnna1` | 0.0000 | 1.0000 | 0.9996  |
| 4 | `chek1` | 0.0000 | 1.0000 | 0.9995  |
| 5 | `erbb2` | 0.0000 | 1.0000 | 0.9993  |

### Top Protective Genes (HR < 1 — associated with decreased mortality)

| Rank | Gene | Coef β | HR | p-value |
|------|------|:------:|:--:|:-------:|
| 1 | `gata3_mut` | -0.0950 | 0.9094 | 0.0150 ★ |
| 2 | `bcl2` | -0.0208 | 0.9794 | 0.6591  |
| 3 | `cbfb_mut` | -0.0159 | 0.9842 | 0.6533  |
| 4 | `lama2_mut` | -0.0134 | 0.9867 | 0.6816  |
| 5 | `hla-g` | -0.0046 | 0.9954 | 0.9015  |

---

## Interpretation Guide

| Term | Meaning |
|------|---------|
| **Coef β** | Log hazard ratio; magnitude = strength, sign = direction of effect |
| **HR exp(β)** | Hazard Ratio: HR > 1 → increased risk; HR < 1 → protective |
| **SE** | Standard Error of the coefficient estimate |
| **z-score** | Coefficient divided by SE; large |z| → more significant |
| **p-value** | Statistical significance of the coefficient |
| **95% CI** | Confidence interval of the Hazard Ratio |
| **★ p<0.05 · ★★ p<0.01 · ★★★ p<0.001** | Significance stars |
| **✅ Lasso Selected** | Non-zero coefficient — retained as a prognostic driver |
| **❌ Lasso Zeroed** | Coefficient shrunk to 0 — not prognostically informative |

---

## Conclusion

The Lasso-regularised Cox PH model selected **68 out of 68** genomic features as prognostically informative. The top risk gene is `aurka` (HR=1.1147) and the top protective gene is `gata3_mut` (HR=0.9094), consistent with known breast cancer biology.

---
*Report auto-generated by generate_feature_importance.py — Track D.*