# Validation: does the engine reproduce 2011-2019? (Phase 7 step F)

Generated 2026-11-08 by `scripts/validate.py` (numbers: `docs/validation-2026-11.json`). Two tests: a nine-year historical backtest against two naive benchmarks, and the engine's fiscal multipliers against the published evidence. Both ran first on the engine as frozen after the data-only fixes (**blind**), then on the engine after the structural fixes the tests exposed (**final**, step F4b, decided 2026-11-08). No parameter was fitted to either test.

## The backtest

- **Start:** 2010, from 2010 data only. Every calibration window is the five years to 2010 (fiscal position, interest rates, external position, capital stock); capacity utilisation is 2010's own (a trough). Trend growth is 2000-2010's.
- **Fed in (decided outside the economy):** government spending (consumption plus investment), exports (world demand), the wage share, policy rates; in the main variant also new-borrowing yields and the net-tax ratio. Government investment is moved from investment into government spending. One-off bank rescues (net capital transfers above their 2001-08 average: IE 2010, ES 2012, SI 2013, CY, EL) are kept out of the fiscal stance and out of the debt the engine is scored on.
- **Left to the engine:** consumption, private investment, imports, prices, output, debt, the current account.
- **Scored:** every result as a change since 2010. Real GDP, consumption and private investment in % (log points); inflation, and the change in public debt, the current account and the private-sector balance, in percentage points of GDP. The private-sector balance replaces the household saving rate: the engine has no separate corporate sector.
- **Benchmarks:** a random walk (levels grow at their 2000-2010 average, ratios stay at 2010) and a static multiplier that gets the engine's inputs (GDP from the expenditure identity with every other component at its 2010 share; debt from the 2010 tax share and rate).
- **Bar (set before the run):** beat both benchmarks for most countries and variables.
- **Countries:** 24 (EL, IE and LU are reported separately: `schema/coverage.py`).

### Result: the bar is not met

Main variant (policy fed), final engine: the engine beats the random walk in 92/168 (55%) of country-variable cells, the static multiplier in 85/168 (51%) and **both in 62/168 (37%)**. The blind engine: 87/168 (52%), 85/168 (51%) and 60/168 (36%). The structural fixes did not change the tracking; they were made for the multipliers and the balance sheets, not for it.

| Variable | Unit | Engine | Random walk | Static | Beats RW | Beats static | Beats both | Engine, blind |
|---|---|---|---|---|---|---|---|---|
| real GDP | % | 3.9 | 4.0 | 5.5 | 13/24 | 17/24 | 10/24 | 4.1 |
| real consumption | % | 5.0 | 5.5 | 5.7 | 16/24 | 12/24 | 8/24 | 6.3 |
| real private investment | % | 12.2 | 17.3 | 11.9 | 13/24 | 9/24 | 5/24 | 11.9 |
| inflation | pp/yr | 1.1 | 1.8 | 1.8 | 17/24 | 17/24 | 17/24 | 1.1 |
| public debt / GDP | pp | 8.4 | 7.3 | 7.6 | 10/24 | 12/24 | 8/24 | 8.6 |
| current account / GDP | pp | 2.8 | 2.6 | 2.0 | 11/24 | 5/24 | 2/24 | 3.2 |
| private-sector balance / GDP | pp | 2.8 | 2.6 | 2.5 | 12/24 | 13/24 | 12/24 | 3.0 |

Median across countries of the mean absolute error, 2011-2019.

**What it gets right and wrong:**
- **Inflation** is the engine's best variable (beats both benchmarks in 17 of 24 countries).
- **Public debt** is underpredicted in 19 of 24 countries (median 2019 error -9.6 pp). The engine's inflation sits near the 2% target; euro-area GDP inflation averaged 1.25% in 2011-19, so nominal GDP runs high and debt ratios low. Asset sales of bad banks (DE, AT) and cash buffers (PT, IE) also moved debt outside the deficit.
- **The current account** is the weakest: the static benchmark beats the engine in 19 of 24 countries. Imports follow output with one propensity; there is no exchange-rate or price channel on imports.
- **The euro-crisis years** (2011-13) are not worse than 2014-19 (real GDP 3.8% against 3.8%): fed-in spending and yields carry the austerity and the spreads.

### The policy rules

| Variant | What the engine decides | Beats RW | Beats static | Beats both | Real GDP | Debt |
|---|---|---|---|---|---|---|
| fed | behaviour only (spending, yields, net taxes fed) | 92/168 (55%) | 85/168 (51%) | 62/168 (37%) | 3.9 | 8.4 |
| spread_rule | + the rate on new borrowing (spread rule) | 95/168 (57%) | 86/168 (51%) | 64/168 (38%) | 4.0 | 7.8 |
| rules | + taxes (fiscal rule toward the 2010 debt ratio) | 97/168 (58%) | 81/168 (48%) | 62/168 (37%) | 3.8 | 7.4 |

The projections' own rules (spread and fiscal rule) score about as well as feeding in actual policy: the 2011-19 errors come from behaviour and prices, not from them.

### By country (main variant, final engine; MAE; **bold** = beats both benchmarks)

| | real GDP | real consumption | real private investment | inflation | public debt / GDP | current account / GDP | private-sector balance / GDP |
|---|---|---|---|---|---|---|---|
| AT | 1.2 | 3.7 | 10.9 | 0.3 | **3.0** | 3.8 | **3.1** |
| BE | **2.0** | 4.5 | 10.7 | 0.5 | 5.6 | 3.7 | **2.8** |
| BG | 14.9 | 13.9 | 11.1 | **2.2** | 21.9 | 4.0 | 2.3 |
| CY | 4.9 | 7.2 | **25.9** | **1.0** | 28.3 | 5.7 | 6.1 |
| CZ | **3.4** | **6.1** | 6.9 | **2.5** | 11.8 | 1.2 | 2.2 |
| DE | **1.2** | **0.9** | 7.0 | 0.5 | **4.5** | **0.7** | **1.0** |
| DK | **2.9** | 2.7 | **12.0** | **1.3** | 7.2 | 1.5 | **1.1** |
| EE | 8.5 | 8.2 | **21.2** | **1.6** | 8.2 | 2.4 | 3.0 |
| EL (excluded) | 5.7 | 9.5 | **25.8** | **1.1** | 74.0 | 9.7 | 4.5 |
| ES | **5.4** | 5.3 | 22.4 | **0.9** | **6.5** | 1.9 | 2.8 |
| FI | **2.6** | 3.0 | 10.4 | **0.7** | 7.6 | 2.9 | **3.3** |
| FR | 1.8 | **1.8** | 7.7 | 1.0 | **2.3** | 3.1 | **1.7** |
| HR | **2.2** | 5.7 | 14.0 | **1.1** | **2.6** | 1.9 | 2.3 |
| HU | 3.2 | **2.5** | **12.4** | **1.4** | 8.9 | 1.6 | 1.3 |
| IE (excluded) | **9.1** | **7.8** | **38.8** | 2.9 | 23.3 | 8.8 | **6.6** |
| IT | **1.9** | 2.9 | 9.2 | **0.7** | **8.8** | 2.3 | 3.1 |
| LT | 6.1 | 10.4 | 37.6 | **2.0** | 10.7 | 5.7 | **4.7** |
| LU (excluded) | 11.5 | 20.6 | 16.5 | **1.3** | 20.7 | 4.6 | 6.7 |
| LV | 9.8 | 11.3 | 19.8 | 1.9 | 9.9 | 7.2 | **4.4** |
| MT | **5.8** | **3.9** | 28.1 | 1.6 | **8.6** | 10.8 | 11.5 |
| NL | 4.8 | 8.6 | 12.0 | **1.1** | 13.8 | 3.2 | **1.4** |
| PL | 2.5 | **1.0** | 21.7 | **1.8** | 6.2 | 1.6 | **1.5** |
| PT | 3.3 | 7.4 | 14.8 | **0.8** | 13.2 | 4.3 | 3.6 |
| RO | 5.1 | **2.3** | **6.9** | **1.4** | **1.1** | **1.6** | **1.3** |
| SE | 4.5 | 4.6 | 15.0 | 3.0 | 7.8 | 2.7 | **2.3** |
| SI | 7.4 | 11.6 | 11.1 | **0.7** | 29.0 | 1.6 | 4.5 |
| SK | **5.2** | **10.7** | 13.6 | **1.1** | 17.3 | 4.3 | 3.3 |

## The multipliers

A stimulus of 1% of GDP in 2020 and 2021 (the design of Kilponen et al. 2015), 2019 calibration, no AI shift, the projections' fiscal rule and rate path; change in real GDP per unit, median of the 24 usable countries.

| Instrument | Year 1 (range) | Year 2 | Two-year average | Blind, year 1 | Literature |
|---|---|---|---|---|---|
| Government spending | 0.82 (0.58-1.07) | 1.16 | 0.99 | 1.02 | 0.50-0.98 in year 1 across 15 European central-bank models (euro area 1.39 with rates fixed); about 0.85 cumulative in the meta-analysis |
| Labour tax cut / transfer to wage earners | 0.42 (0.29-0.61) | 0.76 | 0.59 | 0.89 | 0.04-0.51 in those models; 0.3-0.4 below spending in the meta-analyses |
| Capital tax cut | 0.22 (0.15-0.39) | 0.63 | 0.43 | 0.48 | 0.02-0.65, mostly about 0.1 |

Blind, households spent any change in income at their average propensity at once, so a tax cut or transfer moved GDP almost as much as spending (0.89 against 1.02). Final, they spend about half of a temporary change in its first year (Jappelli & Pistaferri 2014; Fagereng, Holm & Natvik 2021): all three year-1 multipliers sit inside the published ranges. **Year 2 is above them:** the engine has no forward-looking smoothing, so consumption keeps adjusting through the shock's second year, and the investment response to profits adds to the capital-tax effect. Read the engine's short-run responses as upper bounds.

## What the tests changed (step F4b, disclosed)

- **Consumption** adjusts to its long-run level by about half the gap a year (`modules/sfc_core.py`, IMPACT_MPC 0.48; MC 0.3-0.7); workers with no deposits left spend only their income. Permanent changes are still spent in full.
- **Existing loans** of firms and households (Eurostat financial accounts) sit on the banks' books at their 2019 share of GDP; deposits gross up by the same amount (SK 2019: 0% to 76% of GDP), net wealth is unchanged, borrowers pay the loan rate. Dwellings are carried at the household loans' face value (housing is not modelled).
- **Trend growth** is each country's 2024 Ageing Report path instead of 1.5% for all; the 2019 output gap closes in three years (the report's convention).
- **The public stand-in** for the foreign position applies wherever a class's deposits would start at or below zero, by rule rather than by list (in 2019 it still selects IE and CY).
- **Luxembourg** is excluded from published results, with Greece and Ireland.

With every step F switch off, the engine reproduces the Banks-step engine to 1e-8 (checked on the triad and the UBC experiment for seven countries).

## Limits

- The backtest is conditional: it is fed the policy and the world demand that actually happened. It tests behaviour, not forecasting.
- The consumption-gap estimates (Onaran & Obst 2016) use data to 2013, inside the window: not fully out of sample.
- Floaters (CZ, HU, PL, RO, SE) are scored in euros; their exchange-rate moves sit in the deflator.
- Nine years cannot test a 30-year projection: the multipliers and the plausibility audit carry that part.

