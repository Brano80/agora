# Plausibility audit — 2026-11-08 (Phase 7, step F)

The Banks-step engine (`docs/AUDIT-2026-10-stepBanks.md`) after the step F re-validation (`docs/VALIDATION-2026-11.md`): each country's own capital stock and depreciation (AMECO); firms' and households' existing loans on the banks' books (Eurostat financial accounts); households spend about half of a temporary income change in its first year and the rest over the following years; each country grows at its 2024 Ageing Report trend, with the 2019 output gap closing in three years; the public stand-in for the foreign position applies by rule. EL, IE and LU are excluded from published results (`schema/coverage.py`) but still audited. Same families, countries and laws. Reproduce: `python scripts/audit_plausibility.py --step F`.

| Law | Fails when |
|---|---|
| `hh_net_worth_nonnegative` | a household class owes more than it owns (money + foreign assets + capital) |
| `money_split_shares_valid` | a household class holds negative money (an interest-free overdraft at the state) |
| `investment_share_bounded` | investment exceeds 40% of GDP |
| `gini_floor` | the personal Gini falls below 0.15 (lowest EU member in the data: SK 0.228) |
| `owners_mpc_in_unit_interval` | the owners' marginal propensity to consume, solved as a calibration residual, lies outside [0, 1] |

## Headline

- **Scenario runs:** 3,455 across 27 countries. **3,455 (100%) pass the accounting gate; 3,054 (88%) also pass the plausibility laws.**
- **Monte-Carlo draws** (the F12 robustness bands' priors, seed 0): 6,824 of 10,792 used draws (63%) are plausible.
- **Errors / exclusions:** 7 (listed at the end).

## By scenario family (all countries)

| Family | Runs | Accounting OK | Solvent | Plausible | net worth < 0 | money < 0 | I/Y > 0.40 | Gini < 0.15 | MPC out of [0,1] |
|---|---|---|---|---|---|---|---|---|---|
| triad | 81 | 81 | 81 (100%) | 75 (93%) | 0 | 0 | 3 | 0 | 3 |
| ubc_experiment | 108 | 108 | 107 (99%) | 98 (91%) | 0 | 1 | 4 | 3 | 4 |
| frontier | 513 | 513 | 510 (99%) | 461 (90%) | 0 | 3 | 19 | 19 | 19 |
| rich_frontier | 1965 | 1965 | 1951 (99%) | 1701 (87%) | 7 | 14 | 73 | 168 | 67 |
| c1_ladder | 431 | 431 | 430 (100%) | 395 (92%) | 0 | 1 | 16 | 8 | 15 |
| proposals | 243 | 243 | 242 (100%) | 223 (92%) | 0 | 1 | 9 | 3 | 9 |
| pooling | 114 | 114 | 113 (99%) | 101 (89%) | 0 | 1 | 0 | 11 | 4 |
| mc_ubc (draws) | 5392 | 5392 | — | 1904 (35%) | 87 | 126 | 200 | 3368 | 272 |
| mc_cash_ubi (draws) | 5400 | 5400 | — | 4920 (91%) | 0 | 0 | 200 | 35 | 280 |

*Solvent = no household class with negative net worth or negative money. Check columns count runs failing that law at least once (a run can fail several).*

### Insolvency by policy form (deterministic runs, all countries)

| Policy form | Runs | Owners' money < 0 | Workers' money < 0 | Net worth < 0 |
|---|---|---|---|---|
| none | 324 | 0 (0%) | 0 (0%) | 0 (0%) |
| cash | 926 | 0 (0%) | 0 (0%) | 0 (0%) |
| ubc | 1531 | 19 (1%) | 0 (0%) | 7 (0%) |

Monte Carlo: net worth < 0 in 87/5,392 UBC draws and 0/5,400 cash draws.

### Baselines (no AI shift, no policy)

25 of 27 baselines pass. Failing:

- **EL:** MPC out of [0,1] from 2019 (owners' MPC 1.2726, owners' money min 0.558 x Y0, max I/Y 0.1158)
- **IE:** I/Y > 0.40 from 2019 (owners' MPC 0.2994, owners' money min 2.0806 x Y0, max I/Y 0.5359)

## Published numbers

| Surface | Runs behind it | Plausible | First failing laws (runs) |
|---|---|---|---|
| README headline + manifesto §III (DE: cash UBI vs UBC, wealth + growth) | 2 | 2/2 | none |
| README frontier chart (DE/FR/SK, frontier points) | 40 | 40/40 | none |
| Manifesto + dashboard frontier (DE, all 13 points) | 19 | 19/19 | none |
| Manifesto C1 ladder (DE, endogenous investment, cash vs UBC) | 8 | 8/8 | none |
| LinkedIn posts (DE/FR/SK cash vs UBC) | 6 | 5/6 | Gini < 0.15 (1) |
| Dashboard (all countries: triad + UBC experiment + frontier) | 702 | 634/702 | MPC out of [0,1] (26), I/Y > 0.40 (26), Gini < 0.15 (22), money < 0 (4) |
| F23 rich frontier (DE, all regimes) | 73 | 73/73 | none |
| Proposal library (DE) | 9 | 9/9 | none |
| Proposal library (all countries) | 243 | 223/243 | MPC out of [0,1] (9), I/Y > 0.40 (9), Gini < 0.15 (3), money < 0 (1) |
| Pooled dividend, EU bloc (manifesto/dashboard), cash_ubi (26/26 countries viable) | 52 | 50/52 | MPC out of [0,1] (2) |
| Pooled dividend, EU bloc (manifesto/dashboard), ubc (26/26 countries viable) | 52 | 41/52 | Gini < 0.15 (11), MPC out of [0,1] (2), money < 0 (1) |
| Pooled dividend, DE+FR+SK (posts), cash_ubi (3/3 countries viable) | 6 | 6/6 | none |
| Pooled dividend, DE+FR (posts), cash_ubi (2/2 countries viable) | 4 | 4/4 | none |
| F12 robustness bands (DE Monte Carlo, ubc) | 200 draws | 92/200 | Gini < 0.15 (108) |
| F12 robustness bands (DE Monte Carlo, cash_ubi) | 200 draws | 200/200 | none |

The MCP tools and the agent crew use the orchestrator defaults, so they inherit the UBC-experiment and frontier rows above.

### The README headline runs (DE)

| Run | Plausible | First failing law (year) | Owners' net worth, min (x Y0) | Owners' money, min (x Y0) | Max I/Y | Min Gini |
|---|---|---|---|---|---|---|
| Baseline | yes | — | 3.9291 | 1.2945 | 0.2185 | 0.297 |
| AI shift, no policy | yes | — | 3.9291 | 1.2945 | 0.2191 | 0.297 |
| AI + Cash UBI | yes | — | 3.9291 | 1.2882 | 0.2115 | 0.2417 |
| AI + Universal Basic Capital | yes | — | 3.2853 | 1.2945 | 0.2176 | 0.2016 |

## By country (plausible / runs)

| Country | Owners' MPC | Triad | UBC exp. | Frontier | Rich frontier | C1 ladder | Proposals | MC UBC | MC cash | Worst owners' net worth (x Y0) |
|---|---|---|---|---|---|---|---|---|---|---|
| AT | 0.5237 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 66/200 | 200/200 | 2.0585 |
| BE | 0.9518 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 91/200 | 120/200 | 2.4665 |
| BG | 0.6716 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 160/200 | 200/200 | 0.0503 |
| CY | 0.6078 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 69/200 | 200/200 | 2.6633 |
| CZ | 0.6501 | 3/3 | 4/4 | 18/19 | 51/73 | 16/16 | 9/9 | 30/200 | 200/200 | 1.2274 |
| DE | 0.3816 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 92/200 | 200/200 | 2.4796 |
| DK | 0.6169 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 89/200 | 200/200 | 2.7581 |
| EE | 0.5842 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 90/200 | 200/200 | 1.0557 |
| EL | 1.2726 | 0/3 | 0/4 | 0/19 | 0/67 | 0/15 | 0/9 | 0/192 | 0/200 | 0.004 |
| ES | 0.4844 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 93/200 | 200/200 | 2.0597 |
| FI | 0.6463 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 66/200 | 200/200 | 2.0679 |
| FR | 0.5336 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 107/200 | 200/200 | 1.8375 |
| HR | 0.5934 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 62/200 | 200/200 | 0.9293 |
| HU | 0.6135 | 3/3 | 4/4 | 18/19 | 71/73 | 16/16 | 9/9 | 60/200 | 200/200 | 1.2748 |
| IE | 0.2994 | 0/3 | 0/4 | 0/19 | 0/73 | 0/16 | 0/9 | 0/200 | 0/200 | 2.4068 |
| IT | 0.4874 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 80/200 | 200/200 | 2.5059 |
| LT | 0.5875 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 80/200 | 200/200 | 0.9267 |
| LU | 0.3275 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 108/200 | 200/200 | 3.0061 |
| LV | 0.737 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 140/200 | 200/200 | 0.4966 |
| MT | 0.3376 | 3/3 | 4/4 | 19/19 | 53/73 | 16/16 | 9/9 | 39/200 | 200/200 | 2.7028 |
| NL | 0.3465 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 67/200 | 200/200 | 2.8171 |
| PL | 0.6378 | 3/3 | 3/4 | 15/19 | 43/73 | 14/16 | 8/9 | 22/200 | 200/200 | 0.369 |
| PT | 0.7878 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 83/200 | 200/200 | 1.325 |
| RO | 0.9401 | 3/3 | 4/4 | 19/19 | 62/73 | 16/16 | 9/9 | 38/200 | 200/200 | -0.0098 |
| SE | 0.412 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 110/200 | 200/200 | 2.947 |
| SI | 0.5293 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 62/200 | 200/200 | 1.1302 |
| SK | 0.876 | 3/3 | 3/4 | 11/19 | 34/73 | 13/16 | 8/9 | 0/200 | 200/200 | 0.1277 |

## Errors and exclusions

- **EL / rich_frontier:** refused: [sfc_core/UBC t=35% reinv=100% [endo]] year 2048 FAILED: economic_plausibility(inf: gini not in [0,1] (1.13))
- **EL / rich_frontier:** refused: [sfc_core/UBC t=40% reinv=100% [endo]] year 2048 FAILED: economic_plausibility(inf: gini not in [0,1] (3.12))
- **EL / rich_frontier:** refused: [sfc_core/UBC t=45% reinv=100% [endo]] year 2047 FAILED: economic_plausibility(inf: gini not in [0,1] (1.37))
- **EL / rich_frontier:** refused: [sfc_core/UBC t=50% reinv=100% [endo]] year 2047 FAILED: economic_plausibility(inf: gini not in [0,1] (2.97))
- **EL / rich_frontier:** refused: [sfc_core/UBC t=55% reinv=100% [endo]] year 2046 FAILED: economic_plausibility(inf: gini not in [0,1] (1.19))
- **EL / rich_frontier:** refused: [sfc_core/UBC t=60% reinv=100% [endo]] year 2046 FAILED: economic_plausibility(inf: gini not in [0,1] (1.84))
- **EL / c1_ladder:** ConsistencyError: [sfc_core/AI + Universal Basic Capital] year 2048 FAILED: economic_plausibility(inf: gini not in [0,1] (3.12))

## Reading

- **Accounting:** 3,455 of 3,455 runs balance their books.
- **Insolvency:** 7 runs and 87 Monte-Carlo draws (step B: 2 runs; Banks step: 35 runs and 200 draws, all EL), RO 7. Owners now also owe their share of firms' and households' existing loans, so a fund that takes all of RO's capital leaves its owners a sliver below zero. External positions are no longer split among households by their money, so no household carries the country's foreign debt.
- **Negative money:** owners in 21 runs (EL, RO), workers in 0 runs (none); Monte-Carlo draws: EL 64, RO 62. Workers with no deposits left now spend only their income and what they have, so no worker overdraft arises. The law stays advisory (Banks step: owners in 37 runs, all EL).
- **Investment above 40% of GDP:** 124 runs (60 of them UBC), all in IE (step B: 385 in the rich frontier alone). The fund now invests by the owners' rule, which responds to profitability and spare capacity, instead of sinking every retained euro into domestic capital.
- **Gini below 0.15:** 212 runs (UBC 193, cash 19, other 0) and 3,403 draws, 35 cash UBI and 3,368 UBC (Banks step: 214 runs, 200 UBC; 3,531 draws, 22 cash). Market inequality now follows households' pre-tax capital income, so the levy is counted once, as a transfer. What remains is UBC at high claim rates: a fund that owns most domestic capital and pays an equal dividend compresses personal income below anything observed. The law stays advisory: it flags an implausible distribution, not an accounting fault, and the frontier keeps those runs off.
- **Calibration:** owners' MPC outside [0, 1] in EL; those countries' results stay unusable under this closure. (Banks step: EL.) Step F's review excluded EL, IE and LU from published results for reasons in their data (`schema/coverage.py`): Greek households dissaved every year 2012-19, Irish accounts are dominated by multinationals, and Luxembourg's cross-border income by pass-through companies.
- **Prices:** peak inflation above 5% in 71 of 3,050 runs and above 10% in 0; deflation in 14 runs, all in EL, ES.
- **Capacity ceiling binds** (demand met by extra imports): none 12/378 (6 for over a quarter of the years); cash 287/1034 (115 for over a quarter of the years); ubc 430/1638 (259 for over a quarter of the years). Baselines at the ceiling: RO (Banks step: BE, EL, IT. The cause was the uniform 1.5% trend, not K/Y: each country now grows at its own Ageing Report trend with capacity set to match it.)
- **Utilisation below the country's 2005-2019 trough** (the 2009 slump): 638 runs (AT 4, DK 22, EL 105, ES 82, FR 110, HR 47, IE 32, IT 40, NL 17, PL 22, PT 85, RO 71, SE 1); by policy: UBC 440, cash 152, none 46. Under UBC with retained profits the fund keeps building as the profit share climbs (the profit response is applied far outside its sample: a remaining limitation; Banks step: 736 runs); with no policy, demand falls short under the AI shift.
- Policy rates move from 2019 to the neutral rate and do not react. Existing loans now give higher rates a borrower side (workers and owners pay the loan rate on them), but the model still has no asset prices or housing market, so a reacting rule stays off.
- **External positions (baselines):** NIIP -22% of GDP in 2019 (median) and +7% in 2049; largest moves: LU +81 to +477, IE -186 to +34, MT +116 to +280. Exports follow world demand while imports follow domestic output, so surplus countries keep accumulating; there is no exchange-rate or risk-premium feedback (the 2011-19 backtest's weakest variable).
- **Current account beyond +-10% of GDP** in some year: none 62; cash 273; ubc 756 runs. Mostly UBC: a fund that retains profits it cannot invest at home saves them abroad, as Norway's fund does.
- **AI rent reached (none):** median 0% of the AI rent by 2049 (216 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.76.
- **AI rent reached (cash):** median 12% of the AI rent by 2049 (1034 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.78.
- **AI rent reached (ubc):** median 21% of the AI rent by 2049 (1638 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.77.
- None of these families includes the source levy; its reach is pinned in `tests/test_external.py` (with 90% pass-through a 10% levy reaches 1% of the foreign rent).
- **Public debt with no policy (AI shift), 24 usable countries:** median 55% of GDP in 2019 and 127% in 2049; above 150% in 7 of 24 countries (BE, ES, FI, FR, HR, IT, PT). Largest rises: IT 136 to 300, FR 100 to 256, PT 119 to 247. Each government corrects by the estimated EU fiscal reaction (0.034 of the debt gap a year), which is too slow for a shock of this size: 70% of the AI rent is paid abroad as licence and cloud fees, so the profits it replaces wages with are largely outside the domestic tax base. No austerity or tax rise beyond the estimated reaction is assumed, and rates move from 2019 to the 2% neutral rate; new borrowing pays the country's spread plus 3 bp per point of debt added beyond the euro area's; each country grows at its Ageing Report trend (Banks step: median 127% in 2049, 7 of 25 countries above 150%, at 1.5% growth everywhere).
- **Rates (no policy, AI shift, 2049):** policy rate 2.0% everywhere (2019 level to the neutral rate, no reaction); average rate on public debt median 2.5% (1.4-6.0%), new borrowing median 2.4%.
- **Financial sector:** households' deposits start at public debt plus the foreign debt-type position plus firms' and households' existing loans (step F; Banks step: median 68%), median 155% of GDP; its margin, paid to owners, is a median 4.0% of GDP in 2049; its balance sheet closes in every run. The foreign position no longer runs through the budget, which had been charging net debtors' governments the interest on their private sector's foreign debt (and crediting creditors'). Public stand-in kept for CY, IE.
- **Propensities to consume (27 countries):** workers median 0.90 (0.50-1.00), owners median 0.59 (0.30-1.27) out of income net of depreciation. Workers are capped at 1 in EL, IT, PT, RO, SK, where 2019 consumption is too high for the published gap (households dissaved or nearly so); there owners take the remainder and the gap is smaller than estimated. The EU15 median gap is used for BG, CY, CZ, EE, HR, HU, LT, LV, MT, RO, SI, SK.
- **Fair prices (UBC benchmark):** the fund buys shares at market value; Tobin's q ends at a median 1.18 (2019 = 1) as AI raises profits, so each euro of the 40% claim buys fewer shares than at book value. It still ends up owning most domestic capital: the claim is large relative to new investment, whatever the price.

### Proposals against no policy (AI shift), median across the 24 countries whose no-policy run is plausible (EL, IE, LU excluded)

| Proposal | Plausible | Real GNI 2049 | Consumption per head 2020-49 | Gini 2049 | Debt 2049 (pp) | AI rent reached 2049 | of the part paid abroad |
|---|---|---|---|---|---|---|---|
| No policy (AI shift) | 24/24 | level | level | 0.318 | 127% of GDP | 0% | 0% |
| One-time stock levy on AI firms (Sanders) | 24/24 | +0.8% | +0.9% | 0.300 | -13 | 15% | 0% |
| Voluntary AI pledges, best case (Anthropic-style) | 24/24 | +2.7% | +3.2% | 0.304 | -3 | 9% | 13% |
| Borrowing-financed citizens' fund | 24/24 | +2.4% | +1.4% | 0.312 | +27 | 0% | 0% |
| Child accounts (Fruehstart-Rente) | 24/24 | +0.0% | -0.0% | 0.318 | +1 | 0% | 0% |
| Levy on AI fees paid abroad (3%) | 24/24 | +0.2% | -0.4% | 0.317 | -7 | 2% | 0% |
| Cash UBI on a broad tax base | 24/24 | -0.6% | +4.5% | 0.258 | -1 | 5% | 0% |
| Benchmark: 40% capital levy, cash UBI | 24/24 | -3.6% | +13.1% | 0.220 | -3 | 12% | 0% |
| Benchmark: 40% claim in shares, fund pays 3% | 22/24 | -1.8% | -4.8% | 0.196 | +1 | 23% | 0% |

*GNI and consumption: % difference from no policy in the same country; debt: percentage-point difference in 2049. Benchmarks are the stylised 40% levy (cash) and 40% claim in shares (UBC); the pledge row is a best case.*

- **Frontier:** 52 of 513 frontier-search points fail a plausibility law and are kept off the frontier. Proposals on the frontier: stock_levy 25/27, pledge 25/27, debt_fund 18/27, child_accounts 6/27, source_levy 13/27, broad_ubi 25/27 countries. A sixth objective, average real consumption per person 2020-2049, sits beside growth (national income), equality, stability, fiscal space and resilience.
- **Caveats:** the pledge row assumes every foreign AI provider pays out like Anthropic's pledge and in proportion to its European fees; the stock levy has no valuation, relocation or compensation response; the debt-financed fund earns the world equity return (6.6%) while the state borrows at its market rate (policy rate + spread + premium). All of it rests on an engine whose short-run responses are upper bounds (`docs/VALIDATION-2026-11.md`).
