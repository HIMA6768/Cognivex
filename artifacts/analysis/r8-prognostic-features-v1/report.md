# R8 Prognostic Genomic Feature Analysis

## Boundary and source

This research-only analysis reports model-associated coefficients from the frozen R6 Track B experiment `r6-track-b-v1`. It does not fit, tune, select, or retrain a model and does not establish causality or clinical utility.

## Method

- All 68 genomic predictors are retained: 50 expression and 18 mutation-presence features.
- Activity uses the numerical rule `abs(beta) > 1e-06`.
- Rank uses descending absolute beta, followed by frozen genomic order for exact ties.
- Model-reported intervals and p-values are descriptive only and do not control rank, activity, filtering, or emphasis.

## Complete model-associated feature table

| Rank | Raw feature | Type | Beta | Hazard ratio | Direction | Active |
|---:|---|---|---:|---:|---|---|
| 1 | prkcz_mut | mutation_presence | 0.45635555858205129 | 1.5783114271848175 | Associated with higher modeled hazard | yes |
| 2 | klrg1_mut | mutation_presence | -0.34840681747939878 | 0.70581168127127891 | Associated with lower modeled hazard | yes |
| 3 | cbfb_mut | mutation_presence | -0.23514630340439624 | 0.79045519488256633 | Associated with lower modeled hazard | yes |
| 4 | gata3_mut | mutation_presence | -0.17336703420378949 | 0.84082894521950158 | Associated with lower modeled hazard | yes |
| 5 | lama2_mut | mutation_presence | -0.13721228818437423 | 0.87178513680280945 | Associated with lower modeled hazard | yes |
| 6 | gsk3b | expression | 0.10536603193012786 | 1.1111172403194625 | Associated with higher modeled hazard | yes |
| 7 | nr2f1 | expression | 0.055303724788904642 | 1.056861560987864 | Associated with higher modeled hazard | yes |
| 8 | ctnna1 | expression | 0.054127375902999784 | 1.0556190540221642 | Associated with higher modeled hazard | yes |
| 9 | cdk1 | expression | 0.045908106642058195 | 1.046978196194116 | Associated with higher modeled hazard | yes |
| 10 | mmp9 | expression | 0.042901284726590563 | 1.0438348473221661 | Associated with higher modeled hazard | yes |
| 11 | bcl2 | expression | -0.034545761591502376 | 0.96604413095807429 | Associated with lower modeled hazard | yes |
| 12 | ccnd2 | expression | -0.03149500328958247 | 0.96899579823304272 | Associated with lower modeled hazard | yes |
| 13 | map2 | expression | 0.030335673049279203 | 1.0308004878295205 | Associated with higher modeled hazard | yes |
| 14 | hla-g | expression | -0.028963756162834971 | 0.97145167296480406 | Associated with lower modeled hazard | yes |
| 15 | aurka | expression | 0.026020675157914886 | 1.0263621684539888 | Associated with higher modeled hazard | yes |
| 16 | cbfb | expression | 0.014344658966634109 | 1.0144480373046141 | Associated with higher modeled hazard | yes |
| 17 | klrg1 | expression | -0.012307475889221438 | 0.98776795133546968 | Associated with lower modeled hazard | yes |
| 18 | smad4 | expression | 0.0098670007034601399 | 1.009915840055374 | Associated with higher modeled hazard | yes |
| 19 | psenen | expression | -0.0095340445173239443 | 0.99051126039111426 | Associated with lower modeled hazard | yes |
| 20 | ctnna1_mut | mutation_presence | 0.0080874823788923914 | 1.0081202744065445 | Associated with higher modeled hazard | yes |
| 21 | erbb2_mut | mutation_presence | 0.0059704936760801176 | 1.0059883525979507 | Associated with higher modeled hazard | yes |
| 22 | igf1r | expression | -0.0037782837283164262 | 0.99622884500469799 | Associated with lower modeled hazard | yes |
| 23 | chek2 | expression | -0.0034389736795532506 | 0.99656693281772823 | Associated with lower modeled hazard | yes |
| 24 | lamb3 | expression | -0.0033784097231731335 | 0.99662729068171441 | Associated with lower modeled hazard | yes |
| 25 | chek2_mut | mutation_presence | -9.7202150550108833e-07 | 0.99999902797896689 | Effectively zero under the R8 numerical coefficient threshold | no |
| 26 | foxo1_mut | mutation_presence | 6.7459858775996434e-07 | 1.0000006745988153 | Effectively zero under the R8 numerical coefficient threshold | no |
| 27 | pten_mut | mutation_presence | -3.0724305708635704e-07 | 0.99999969275699008 | Effectively zero under the R8 numerical coefficient threshold | no |
| 28 | nr3c1_mut | mutation_presence | 2.9321221073513072e-07 | 1.0000002932122538 | Effectively zero under the R8 numerical coefficient threshold | no |
| 29 | nr2f1_mut | mutation_presence | 2.2665614278681325e-07 | 1.0000002266561685 | Effectively zero under the R8 numerical coefficient threshold | no |
| 30 | hras_mut | mutation_presence | 1.8524218932784186e-07 | 1.0000001852422065 | Effectively zero under the R8 numerical coefficient threshold | no |
| 31 | erbb3_mut | mutation_presence | -1.1423061927945844e-07 | 0.99999988576938725 | Effectively zero under the R8 numerical coefficient threshold | no |
| 32 | ttyh1_mut | mutation_presence | 1.0188263902887052e-07 | 1.0000001018826443 | Effectively zero under the R8 numerical coefficient threshold | no |
| 33 | tgfbr2 | expression | 9.3744281993613887e-08 | 1.0000000937442863 | Effectively zero under the R8 numerical coefficient threshold | no |
| 34 | prkd1 | expression | 7.7171995448552908e-08 | 1.0000000771719983 | Effectively zero under the R8 numerical coefficient threshold | no |
| 35 | mapt | expression | -7.3979364342550209e-08 | 0.99999992602063836 | Effectively zero under the R8 numerical coefficient threshold | no |
| 36 | egfr | expression | 7.2221935437529614e-08 | 1.000000072221938 | Effectively zero under the R8 numerical coefficient threshold | no |
| 37 | prkcz | expression | -6.8478654422725943e-08 | 0.99999993152134792 | Effectively zero under the R8 numerical coefficient threshold | no |
| 38 | egfr_mut | mutation_presence | -6.0166039830309016e-08 | 0.99999993983396196 | Effectively zero under the R8 numerical coefficient threshold | no |
| 39 | abcb1 | expression | -4.7308541883563235e-08 | 0.99999995269145925 | Effectively zero under the R8 numerical coefficient threshold | no |
| 40 | hdac2 | expression | 4.4674509579989155e-08 | 1.0000000446745105 | Effectively zero under the R8 numerical coefficient threshold | no |
| 41 | chek1 | expression | 4.4468657462925653e-08 | 1.0000000444686585 | Effectively zero under the R8 numerical coefficient threshold | no |
| 42 | smad4_mut | mutation_presence | -3.7459490936899486e-08 | 0.99999996254050971 | Effectively zero under the R8 numerical coefficient threshold | no |
| 43 | lamb3_mut | mutation_presence | 3.693174507709822e-08 | 1.0000000369317457 | Effectively zero under the R8 numerical coefficient threshold | no |
| 44 | csf1r | expression | 3.1382455004870227e-08 | 1.0000000313824555 | Effectively zero under the R8 numerical coefficient threshold | no |
| 45 | gata3 | expression | -3.0252588237370343e-08 | 0.99999996974741223 | Effectively zero under the R8 numerical coefficient threshold | no |
| 46 | foxo1 | expression | 2.8659878222816064e-08 | 1.0000000286598787 | Effectively zero under the R8 numerical coefficient threshold | no |
| 47 | ccne1 | expression | -2.4459464834626131e-08 | 0.99999997554053544 | Effectively zero under the R8 numerical coefficient threshold | no |
| 48 | nr3c1 | expression | -2.285589108293256e-08 | 0.99999997714410915 | Effectively zero under the R8 numerical coefficient threshold | no |
| 49 | erbb2 | expression | 2.2034233920783771e-08 | 1.0000000220342342 | Effectively zero under the R8 numerical coefficient threshold | no |
| 50 | pten | expression | 2.1875532978249286e-08 | 1.0000000218755332 | Effectively zero under the R8 numerical coefficient threshold | no |
| 51 | tsc2 | expression | -2.0812082991744292e-08 | 0.99999997918791728 | Effectively zero under the R8 numerical coefficient threshold | no |
| 52 | arrdc1 | expression | -1.7643578446450539e-08 | 0.99999998235642173 | Effectively zero under the R8 numerical coefficient threshold | no |
| 53 | sox9 | expression | 1.680190077824452e-08 | 1.000000016801901 | Effectively zero under the R8 numerical coefficient threshold | no |
| 54 | pdgfra | expression | -1.5584953183833088e-08 | 0.99999998441504689 | Effectively zero under the R8 numerical coefficient threshold | no |
| 55 | lama2 | expression | -1.4965067291913564e-08 | 0.99999998503493281 | Effectively zero under the R8 numerical coefficient threshold | no |
| 56 | akr1c4 | expression | 1.3246465811452361e-08 | 1.0000000132464657 | Effectively zero under the R8 numerical coefficient threshold | no |
| 57 | mlh1 | expression | -1.1543729704518581e-08 | 0.99999998845627025 | Effectively zero under the R8 numerical coefficient threshold | no |
| 58 | cdc25a | expression | 9.9618718596322715e-09 | 1.0000000099618718 | Effectively zero under the R8 numerical coefficient threshold | no |
| 59 | erbb3 | expression | -9.6903392463300453e-09 | 0.9999999903096608 | Effectively zero under the R8 numerical coefficient threshold | no |
| 60 | hras | expression | 9.5558931832812525e-09 | 1.0000000095558932 | Effectively zero under the R8 numerical coefficient threshold | no |
| 61 | hsd17b11 | expression | 9.4541758342038882e-09 | 1.0000000094541759 | Effectively zero under the R8 numerical coefficient threshold | no |
| 62 | ttyh1 | expression | -6.1877953912345869e-09 | 0.99999999381220461 | Effectively zero under the R8 numerical coefficient threshold | no |
| 63 | mmp1 | expression | -5.9675981835226095e-09 | 0.99999999403240181 | Effectively zero under the R8 numerical coefficient threshold | no |
| 64 | mmp15 | expression | -5.2965707090337766e-09 | 0.99999999470342926 | Effectively zero under the R8 numerical coefficient threshold | no |
| 65 | bmp6 | expression | 4.3981961431225759e-09 | 1.0000000043981963 | Effectively zero under the R8 numerical coefficient threshold | no |
| 66 | tgfbr3 | expression | -2.9410042744306559e-09 | 0.99999999705899567 | Effectively zero under the R8 numerical coefficient threshold | no |
| 67 | folr1 | expression | 2.7867733710281721e-09 | 1.0000000027867735 | Effectively zero under the R8 numerical coefficient threshold | no |
| 68 | rad51 | expression | 2.1452846741298123e-10 | 1.0000000002145284 | Effectively zero under the R8 numerical coefficient threshold | no |

## Interpretation limitations

An expression beta is the modeled association per one training-standardized expression unit, conditional on the other Track B predictors. A mutation beta is the modeled association for mutation presence versus absence; mutation inputs are unscaled binary indicators. Comparing absolute coefficients across these feature types is a model-scale association ranking, not biological unit equivalence.

These outputs do not establish causality, disease mechanisms, biomarkers, or treatment effects. They are descriptive outputs from one penalized Cox model and require external validation.
