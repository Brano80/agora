# Robustness: Monte-Carlo bands and sensitivity (Phase 7 step F2)

Generated 2026-11-08 by `scripts/robustness.py` (numbers: `docs/robustness-2026-11.json`). Engine: step F (`docs/VALIDATION-2026-11.md`). 500 joint draws of all 19 priors in `uncertainty.PRIORS` per country and policy form, seed 0, AI shift (labour share drawn), 40% levy paid as a cash UBI or 40% claim in shares (fund pays 3% a year). Bands: p5 / median / p95 of the draws that pass the accounting gate.

## Does UBC beat cash UBI across the whole prior? (the F12 claim)

| Country | Metric | No policy | Cash UBI | UBC | Bands | UBC better, draw by draw |
|---|---|---|---|---|---|---|
| DE | Personal Gini, 2049 | 0.412 (0.327-0.543) | 0.295 (0.248-0.362) | 0.146 (0.079-0.213) | UBC better, separated | 100% |
| DE | Poverty rate, 2049 | 0.253 (0.196-0.313) | 0.129 (0.091-0.158) | 0.013 (0.000-0.070) | UBC better, separated | 100% |
| DE | Real national income, 2049 (MEUR, 2019 prices) | 3,687,444 (2,925,815-4,379,136) | 3,716,532 (2,906,933-4,516,319) | 3,596,286 (2,879,743-4,215,650) | overlap | 6% |
| DE | Real consumption per person, 2020-49 average (EUR) | 19,108 (16,495-21,820) | 25,501 (22,323-28,579) | 22,630 (20,137-25,009) | overlap | 0% |
| DE | Citizens' fund wealth per person, 2049 (EUR) | 0 (0-0) | 0 (0-0) | 178,178 (132,245-246,134) | UBC better, separated | 100% |
| DE | Real GDP, 2049 (MEUR, 2019 prices) | 3,813,243 (3,375,811-4,284,646) | 4,122,644 (3,598,672-4,682,038) | 4,026,608 (3,605,856-4,419,228) | overlap | 16% |
| FR | Personal Gini, 2049 | 0.405 (0.320-0.535) | 0.289 (0.240-0.357) | 0.158 (0.090-0.220) | UBC better, separated | 100% |
| FR | Poverty rate, 2049 | 0.248 (0.191-0.310) | 0.121 (0.080-0.149) | 0.021 (0.000-0.078) | UBC better, separated | 98% |
| FR | Real national income, 2049 (MEUR, 2019 prices) | 2,107,732 (1,645,111-2,530,477) | 2,107,801 (1,576,897-2,592,768) | 2,025,287 (1,559,713-2,371,709) | overlap | 8% |
| FR | Real consumption per person, 2020-49 average (EUR) | 13,623 (11,432-15,836) | 19,191 (16,580-21,705) | 16,853 (14,691-18,635) | overlap | 0% |
| FR | Citizens' fund wealth per person, 2049 (EUR) | 0 (0-0) | 0 (0-0) | 122,464 (82,382-182,755) | UBC better, separated | 100% |
| FR | Real GDP, 2049 (MEUR, 2019 prices) | 2,275,548 (1,955,948-2,594,636) | 2,483,888 (2,142,326-2,806,828) | 2,417,100 (2,150,977-2,616,129) | overlap | 17% |
| SK | Personal Gini, 2049 | 0.289 (0.240-0.386) | 0.190 (0.170-0.237) | 0.039 (0.032-0.122) | UBC better, separated | 100% |
| SK | Poverty rate, 2049 | 0.164 (0.118-0.237) | 0.037 (0.021-0.061) | 0.000 (0.000-0.004) | UBC better, separated | 100% |
| SK | Real national income, 2049 (MEUR, 2019 prices) | 111,216 (92,291-132,110) | 108,452 (88,347-130,541) | 133,206 (113,643-150,073) | overlap | 100% |
| SK | Real consumption per person, 2020-49 average (EUR) | 8,707 (7,581-10,028) | 11,599 (10,338-12,914) | 8,836 (7,769-9,898) | cash better, separated | 0% |
| SK | Citizens' fund wealth per person, 2049 (EUR) | 0 (0-0) | 0 (0-0) | 93,775 (87,126-109,343) | UBC better, separated | 100% |
| SK | Real GDP, 2049 (MEUR, 2019 prices) | 121,956 (105,990-135,092) | 125,181 (105,446-139,873) | 130,295 (120,723-139,193) | overlap | 66% |

Median (p5-p95). "Separated": the two 90% bands do not overlap. Draw by draw: the same seed gives each form the same priors, so the last column is the share of the 500 draws in which UBC does better than cash UBI.

UBC draws with a personal Gini below 0.15, the plausibility floor (lowest EU member in the data: SK 0.228): DE 53%, FR 44%, SK 100%. The low tail of the UBC inequality band is outside anything observed; the separation on inequality does not depend on it (UBC's median is below cash UBI's p5 everywhere).

## Convergence

Moving from 250 to 500 draws shifts no band edge or median by more than 18% of the band's width.

## What drives the UBC outcome (first-order shares of variance)

- **DE, personal gini, 2049:** beta 91%, labour_share_end 5%, ai_foreign_share 3%, loan_spread_shift 0% (linear R² 1.00).
- **DE, real consumption per person, 2020-49 average (eur):** labour_share_end 80%, ai_foreign_share 11%, profit_response 5%, trend_draw 2% (linear R² 0.93).
- **DE, real national income, 2049 (meur, 2019 prices):** labour_share_end 73%, ai_foreign_share 19%, profit_response 2%, phillips_slope 2% (linear R² 0.96).
- **FR, personal gini, 2049:** beta 85%, labour_share_end 8%, ai_foreign_share 6%, loan_spread_shift 0% (linear R² 1.00).
- **FR, real consumption per person, 2020-49 average (eur):** labour_share_end 82%, ai_foreign_share 12%, phillips_slope 2%, levy_pass_through 1% (linear R² 0.95).
- **FR, real national income, 2049 (meur, 2019 prices):** labour_share_end 77%, ai_foreign_share 19%, levy_pass_through 1%, beta 1% (linear R² 0.97).
- **SK, personal gini, 2049:** beta 97%, ai_foreign_share 1%, labour_share_end 1%, utilisation_response 0% (linear R² 0.72).
- **SK, real consumption per person, 2020-49 average (eur):** labour_share_end 96%, ai_foreign_share 1%, levy_pass_through 1%, trend_draw 1% (linear R² 0.98).
- **SK, real national income, 2049 (meur, 2019 prices):** labour_share_end 84%, ai_foreign_share 8%, trend_draw 3%, phillips_slope 1% (linear R² 0.94).

## Draws used

| Country | none | cash_ubi | ubc |
|---|---|---|---|
| DE | 500/500 | 500/500 | 500/500 |
| FR | 500/500 | 500/500 | 500/500 |
| SK | 500/500 | 500/500 | 500/500 |

