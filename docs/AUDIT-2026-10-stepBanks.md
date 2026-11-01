# Plausibility audit — 2026-11-01 (Phase 7, Banks step)

The step-E5 engine (`docs/AUDIT-2026-10-stepE5.md`) with a **financial sector**: households hold deposits at banks, insurers and pension funds (one sector with no capital of its own), which hold the government's bonds, the owners' loans and the country's foreign debt-type position and pay their interest margin to owners. The government pays interest only on its bonds; rates move from their 2019 level to a 2% neutral rate without reacting; new public borrowing pays the country's spread plus 3 bp per point of debt added beyond the euro area's. IE and CY keep the public stand-in for the foreign position. Same families, countries and laws. Reproduce: `python scripts/audit_plausibility.py --step banks`.

| Law | Fails when |
|---|---|
| `hh_net_worth_nonnegative` | a household class owes more than it owns (money + foreign assets + capital) |
| `money_split_shares_valid` | a household class holds negative money (an interest-free overdraft at the state) |
| `investment_share_bounded` | investment exceeds 40% of GDP |
| `gini_floor` | the personal Gini falls below 0.15 (lowest EU member in the data: SK 0.228) |
| `owners_mpc_in_unit_interval` | the owners' marginal propensity to consume, solved as a calibration residual, lies outside [0, 1] |

## Headline

- **Scenario runs:** 3,462 across 27 countries. **3,462 (100%) pass the accounting gate; 3,061 (88%) also pass the plausibility laws.**
- **Monte-Carlo draws** (the F12 robustness bands' priors, seed 0): 6,805 of 10,800 used draws (63%) are plausible.

## By scenario family (all countries)

| Family | Runs | Accounting OK | Solvent | Plausible | net worth < 0 | money < 0 | I/Y > 0.40 | Gini < 0.15 | MPC out of [0,1] |
|---|---|---|---|---|---|---|---|---|---|
| triad | 81 | 81 | 81 (100%) | 75 (93%) | 0 | 0 | 3 | 0 | 3 |
| ubc_experiment | 108 | 108 | 107 (99%) | 98 (91%) | 1 | 1 | 4 | 3 | 4 |
| frontier | 513 | 513 | 509 (99%) | 463 (90%) | 4 | 4 | 19 | 16 | 19 |
| rich_frontier | 1971 | 1971 | 1945 (99%) | 1707 (87%) | 24 | 26 | 73 | 172 | 73 |
| c1_ladder | 432 | 432 | 429 (99%) | 395 (91%) | 3 | 3 | 16 | 8 | 16 |
| proposals | 243 | 243 | 242 (100%) | 223 (92%) | 1 | 1 | 9 | 3 | 9 |
| pooling | 114 | 114 | 112 (98%) | 100 (88%) | 2 | 2 | 0 | 12 | 4 |
| mc_ubc (draws) | 5400 | 5400 | — | 1834 (34%) | 200 | 200 | 200 | 3509 | 229 |
| mc_cash_ubi (draws) | 5400 | 5400 | — | 4971 (92%) | 0 | 0 | 200 | 22 | 229 |

*Solvent = no household class with negative net worth or negative money. Check columns count runs failing that law at least once (a run can fail several).*

### Insolvency by policy form (deterministic runs, all countries)

| Policy form | Runs | Owners' money < 0 | Workers' money < 0 | Net worth < 0 |
|---|---|---|---|---|
| none | 324 | 0 (0%) | 0 (0%) | 0 (0%) |
| cash | 926 | 0 (0%) | 0 (0%) | 0 (0%) |
| ubc | 1537 | 33 (2%) | 0 (0%) | 31 (2%) |

Monte Carlo: net worth < 0 in 200/5,400 UBC draws and 0/5,400 cash draws.

### Baselines (no AI shift, no policy)

25 of 27 baselines pass. Failing:

- **EL:** MPC out of [0,1] from 2019 (owners' MPC 1.4685, owners' money min 0.0996 x Y0, max I/Y 0.1477)
- **IE:** I/Y > 0.40 from 2019 (owners' MPC 0.2594, owners' money min 0.2974 x Y0, max I/Y 0.5357)

## Published numbers

| Surface | Runs behind it | Plausible | First failing laws (runs) |
|---|---|---|---|
| README headline + manifesto §III (DE: cash UBI vs UBC, wealth + growth) | 2 | 2/2 | none |
| README frontier chart (DE/FR/SK, frontier points) | 38 | 38/38 | none |
| Manifesto + dashboard frontier (DE, all 13 points) | 19 | 19/19 | none |
| Manifesto C1 ladder (DE, endogenous investment, cash vs UBC) | 8 | 8/8 | none |
| LinkedIn posts (DE/FR/SK cash vs UBC) | 6 | 5/6 | Gini < 0.15 (1) |
| Dashboard (all countries: triad + UBC experiment + frontier) | 702 | 636/702 | MPC out of [0,1] (26), I/Y > 0.40 (26), Gini < 0.15 (19), net worth < 0 (5), money < 0 (5) |
| F23 rich frontier (DE, all regimes) | 73 | 73/73 | none |
| Proposal library (DE) | 9 | 9/9 | none |
| Proposal library (all countries) | 243 | 223/243 | MPC out of [0,1] (9), I/Y > 0.40 (9), Gini < 0.15 (3), net worth < 0 (1), money < 0 (1) |
| Pooled dividend, EU bloc (manifesto/dashboard), cash_ubi (26/26 countries viable) | 52 | 50/52 | MPC out of [0,1] (2) |
| Pooled dividend, EU bloc (manifesto/dashboard), ubc (26/26 countries viable) | 52 | 40/52 | Gini < 0.15 (12), MPC out of [0,1] (2), net worth < 0 (2), money < 0 (2) |
| Pooled dividend, DE+FR+SK (posts), cash_ubi (3/3 countries viable) | 6 | 6/6 | none |
| Pooled dividend, DE+FR (posts), cash_ubi (2/2 countries viable) | 4 | 4/4 | none |
| F12 robustness bands (DE Monte Carlo, ubc) | 200 draws | 72/200 | Gini < 0.15 (128) |
| F12 robustness bands (DE Monte Carlo, cash_ubi) | 200 draws | 200/200 | none |

The MCP tools and the agent crew use the orchestrator defaults, so they inherit the UBC-experiment and frontier rows above.

### The README headline runs (DE)

| Run | Plausible | First failing law (year) | Owners' net worth, min (x Y0) | Owners' money, min (x Y0) | Max I/Y | Min Gini |
|---|---|---|---|---|---|---|
| Baseline | yes | — | 3.9645 | 0.6586 | 0.217 | 0.297 |
| AI shift, no policy | yes | — | 3.9645 | 0.6586 | 0.2115 | 0.297 |
| AI + Cash UBI | yes | — | 3.9645 | 0.6205 | 0.2115 | 0.2415 |
| AI + Universal Basic Capital | yes | — | 3.4305 | 0.6586 | 0.2115 | 0.1899 |

## By country (plausible / runs)

| Country | Owners' MPC | Triad | UBC exp. | Frontier | Rich frontier | C1 ladder | Proposals | MC UBC | MC cash | Worst owners' net worth (x Y0) |
|---|---|---|---|---|---|---|---|---|---|---|
| AT | 0.5075 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 59/200 | 200/200 | 1.4027 |
| BE | 0.8812 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 127/200 | 171/200 | 2.0286 |
| BG | 0.7448 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 153/200 | 200/200 | 0.0462 |
| CY | 0.6675 | 3/3 | 4/4 | 19/19 | 66/73 | 16/16 | 9/9 | 52/200 | 200/200 | 1.2075 |
| CZ | 0.5832 | 3/3 | 4/4 | 18/19 | 51/73 | 16/16 | 9/9 | 28/200 | 200/200 | 1.0465 |
| DE | 0.3746 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 72/200 | 200/200 | 2.2306 |
| DK | 0.6195 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 71/200 | 200/200 | 1.978 |
| EE | 0.604 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 82/200 | 200/200 | 0.8293 |
| EL | 1.4685 | 0/3 | 0/4 | 0/19 | 0/73 | 0/16 | 0/9 | 0/200 | 0/200 | -0.4082 |
| ES | 0.5233 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 74/200 | 200/200 | 1.3289 |
| FI | 0.6203 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 56/200 | 200/200 | 1.4326 |
| FR | 0.5346 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 85/200 | 200/200 | 1.3361 |
| HR | 0.5983 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 43/200 | 200/200 | 0.6119 |
| HU | 0.5978 | 3/3 | 4/4 | 19/19 | 72/73 | 16/16 | 9/9 | 54/200 | 200/200 | 1.313 |
| IE | 0.2594 | 0/3 | 0/4 | 0/19 | 0/73 | 0/16 | 0/9 | 0/200 | 0/200 | 0.9367 |
| IT | 0.4531 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 69/200 | 200/200 | 2.0024 |
| LT | 0.6298 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 67/200 | 200/200 | 1.0401 |
| LU | 0.3549 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 114/200 | 200/200 | 2.2527 |
| LV | 0.7009 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 129/200 | 200/200 | 0.493 |
| MT | 0.3628 | 3/3 | 4/4 | 19/19 | 58/73 | 16/16 | 9/9 | 32/200 | 200/200 | 2.3957 |
| NL | 0.3483 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 44/200 | 200/200 | 1.8915 |
| PL | 0.6974 | 3/3 | 3/4 | 15/19 | 49/73 | 14/16 | 8/9 | 21/200 | 200/200 | 0.2647 |
| PT | 0.7916 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 67/200 | 200/200 | 0.7529 |
| RO | 0.9436 | 3/3 | 4/4 | 19/19 | 57/73 | 16/16 | 9/9 | 47/200 | 200/200 | 0.0036 |
| SE | 0.4093 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 109/200 | 200/200 | 2.2939 |
| SI | 0.5195 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 179/200 | 200/200 | 1.3124 |
| SK | 0.7457 | 3/3 | 3/4 | 12/19 | 40/73 | 13/16 | 8/9 | 0/200 | 200/200 | 0.1055 |

## Reading

- **Accounting:** 3,462 of 3,462 runs balance their books.
- **Insolvency:** 35 runs and 200 Monte-Carlo draws (step B: 2 runs; steps C to E5: 0), EL 35 - the economy whose calibration fails below. External positions are no longer split among households by their money, so no household carries the country's foreign debt.
- **Negative money:** owners in 37 runs (EL), workers in 0 runs (none); Monte-Carlo draws: EL 200. With the external position off household balance sheets (step D) the trade-linked overdrafts are gone. The law stays advisory until step F re-validates.
- **Investment above 40% of GDP:** 124 runs (60 of them UBC), all in IE (step B: 385 in the rich frontier alone). The fund now invests by the owners' rule, which responds to profitability and spare capacity, instead of sinking every retained euro into domestic capital.
- **Gini below 0.15:** 214 runs (UBC 200, cash 14, other 0) and 3,531 draws, 22 cash UBI and 3,509 UBC (step E5: 246 runs, 233 UBC; 3,673 draws, 28 cash). Market inequality now follows households' pre-tax capital income, so the levy is counted once, as a transfer. What remains is UBC at high claim rates: a fund that owns most domestic capital and pays an equal dividend compresses personal income below anything observed. The law is advisory until step F; the frontier already keeps those runs off.
- **Calibration:** owners' MPC outside [0, 1] in EL; those countries' results stay unusable under this closure. (Step E5: none.) Households now earn interest only on their deposits (step E5 paid them the government's rate on all public debt), so where 2019 consumption is high relative to income the propensities rise. In EL, where households spent more than their income in 2019, the owners' propensity exceeds 1: EL is unusable until step F reviews its calibration.
- **Prices:** peak inflation above 5% in 20 of 3,057 runs and above 10% in 0; deflation in 140 runs, all in EL, IE, RO.
- **Capacity ceiling binds** (demand met by extra imports): none 26/378 (26 for over a quarter of the years); cash 541/1034 (138 for over a quarter of the years); ubc 216/1645 (115 for over a quarter of the years). Baselines at the ceiling: BE, EL, IT (uniform K/Y = 3 calibration; step F).
- **Utilisation below the country's 2005-2019 trough** (the 2009 slump): 736 runs (AT 52, CZ 45, DE 5, DK 29, EL 40, ES 61, FI 2, FR 107, HR 36, HU 8, IE 109, IT 12, MT 9, NL 15, PL 6, PT 88, RO 112); by policy: UBC 474, cash 196, none 66. Under UBC with retained profits the fund keeps building as the profit share climbs (the profit response is applied far outside its sample; step F); with no policy, demand falls short under the AI shift.
- Policy rates move from 2019 to the neutral rate and do not react (decided 2026-11-01): with no mortgages or asset prices in the model, higher rates raise households' interest income and would feed a boom, not cool it. A reacting rule waits for step F.
- **External positions (baselines):** NIIP -21% of GDP in 2019 (median) and +21% in 2049; largest moves: LU +82 to +483, IE -186 to +84, MT +117 to +311. Exports follow world demand while imports follow domestic output, so surplus countries keep accumulating; there is no exchange-rate or risk-premium feedback yet (step F).
- **Current account beyond +-10% of GDP** in some year: none 90; cash 255; ubc 782 runs. Mostly UBC: a fund that retains profits it cannot invest at home saves them abroad, as Norway's fund does.
- **AI rent reached (none):** median 0% of the AI rent by 2049 (216 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.77.
- **AI rent reached (cash):** median 12% of the AI rent by 2049 (1034 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.79.
- **AI rent reached (ubc):** median 20% of the AI rent by 2049 (1645 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.78.
- None of these families includes the source levy; its reach is pinned in `tests/test_external.py` (with 90% pass-through a 10% levy reaches 1% of the foreign rent).
- **Public debt with no policy (AI shift), 25 usable countries:** median 50% of GDP in 2019 and 127% in 2049; above 150% in 7 of 25 countries (BE, ES, FI, FR, HR, IT, PT). Largest rises: IT 137 to 286, FR 101 to 241, PT 120 to 236. Each government corrects by the estimated EU fiscal reaction (0.034 of the debt gap a year), which is too slow for a shock of this size: 70% of the AI rent is paid abroad as licence and cloud fees, so the profits it replaces wages with are largely outside the domestic tax base. No austerity or tax rise beyond the estimated reaction is assumed, and rates move from 2019 to the 2% neutral rate; new borrowing pays the country's spread plus 3 bp per point of debt added beyond the euro area's (step E5: median 117% in 2049, 8 countries above 150%).
- **Rates (no policy, AI shift, 2049):** policy rate 2.0% everywhere (2019 level to the neutral rate, no reaction); average rate on public debt median 2.7% (1.5-5.9%), new borrowing median 2.5%.
- **Financial sector:** households' deposits start at public debt plus the foreign debt-type position, median 68% of GDP; its margin, paid to owners, is a median 1.8% of GDP in 2049; its balance sheet closes in every run. The foreign position no longer runs through the budget, which had been charging net debtors' governments the interest on their private sector's foreign debt (and crediting creditors'). Public stand-in kept for CY, IE.
- **Propensities to consume (27 countries):** workers median 0.88 (0.51-1.00), owners median 0.60 (0.26-1.47) out of income net of depreciation. Workers are capped at 1 in CY, EL, ES, PT, RO, SK, where 2019 consumption is too high for the published gap (households dissaved or nearly so); there owners take the remainder and the gap is smaller than estimated. The EU15 median gap is used for BG, CY, CZ, EE, HR, HU, LT, LV, MT, RO, SI, SK.
- **Fair prices (UBC benchmark):** the fund buys shares at market value; Tobin's q ends at a median 1.53 (2019 = 1) as AI raises profits, so each euro of the 40% claim buys fewer shares than at book value. It still ends up owning most domestic capital: the claim is large relative to new investment, whatever the price.

### Proposals against no policy (AI shift), median across the 25 countries whose no-policy run is plausible

| Proposal | Plausible | Real GNI 2049 | Consumption per head 2020-49 | Gini 2049 | Debt 2049 (pp) | AI rent reached 2049 | of the part paid abroad |
|---|---|---|---|---|---|---|---|
| No policy (AI shift) | 25/25 | level | level | 0.324 | 127% of GDP | 0% | 0% |
| One-time stock levy on AI firms (Sanders) | 25/25 | +0.8% | +0.9% | 0.303 | -13 | 15% | 0% |
| Voluntary AI pledges, best case (Anthropic-style) | 25/25 | +2.6% | +3.3% | 0.307 | -3 | 9% | 13% |
| Borrowing-financed citizens' fund | 25/25 | +2.4% | +1.6% | 0.318 | +27 | 0% | 0% |
| Child accounts (Fruehstart-Rente) | 25/25 | +0.0% | -0.0% | 0.324 | +1 | 0% | 0% |
| Levy on AI fees paid abroad (3%) | 25/25 | +0.2% | -0.4% | 0.324 | -8 | 2% | 0% |
| Cash UBI on a broad tax base | 25/25 | -0.6% | +4.9% | 0.262 | -1 | 5% | 0% |
| Benchmark: 40% capital levy, cash UBI | 25/25 | -3.7% | +13.1% | 0.221 | -2 | 12% | 0% |
| Benchmark: 40% claim in shares, fund pays 3% | 23/25 | -1.8% | -2.7% | 0.189 | +0 | 24% | 0% |

*GNI and consumption: % difference from no policy in the same country; debt: percentage-point difference in 2049. Benchmarks are the stylised 40% levy (cash) and 40% claim in shares (UBC); the pledge row is a best case.*

- **Frontier:** 50 of 513 frontier-search points fail a plausibility law and are kept off the frontier. Proposals on the frontier: stock_levy 25/27, pledge 25/27, debt_fund 21/27, child_accounts 5/27, source_levy 6/27, broad_ubi 25/27 countries. A sixth objective, average real consumption per person 2020-2049, sits beside growth (national income), equality, stability, fiscal space and resilience.
- **Caveats:** the pledge row assumes every foreign AI provider pays out like Anthropic's pledge and in proportion to its European fees; the stock levy has no valuation, relocation or compensation response; the debt-financed fund earns the world equity return (6.6%) while the state borrows at its market rate (policy rate + spread + premium). Step F re-validates all of it.
