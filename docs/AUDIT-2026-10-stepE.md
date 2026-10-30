# Plausibility audit — 2026-10-30 (Phase 7, step E)

The same scenario families, countries and laws as the step-A to D audits, re-run on the engine with a **realistic government and fair prices**: each country borrows at its own 2015-2019 implicit interest rate, starts from the primary balance that holds its 2019 debt ratio, and corrects deviations from that ratio by the estimated EU fiscal reaction (Bohn rule); profits are taxed at source, including the citizens' fund's share; the fund buys its shares at market value (Tobin's q) and the 40% benchmark pays out 3% of the fund a year (Norway's rule). A new family, **proposals**, runs six real or announced proposals against no policy and the two 40% benchmarks, and the policy frontier now keeps implausible runs off. Reproduce: `python scripts/audit_plausibility.py` (step A: `--closure legacy`).

| Law | Fails when |
|---|---|
| `hh_net_worth_nonnegative` | a household class owes more than it owns (money + foreign assets + capital) |
| `money_split_shares_valid` | a household class holds negative money (an interest-free overdraft at the state) |
| `investment_share_bounded` | investment exceeds 40% of GDP |
| `gini_floor` | the personal Gini falls below 0.15 (lowest EU member in the data: SK 0.228) |
| `owners_mpc_in_unit_interval` | the owners' marginal propensity to consume, solved as a calibration residual, lies outside [0, 1] |

## Headline

- **Scenario runs:** 3,462 across 27 countries. **3,462 (100%) pass the accounting gate; 2,767 (80%) also pass the plausibility laws.**
- **Monte-Carlo draws** (the F12 robustness bands' priors, seed 0): 5,937 of 10,800 used draws (55%) are plausible.

## By scenario family (all countries)

| Family | Runs | Accounting OK | Solvent | Plausible | net worth < 0 | money < 0 | I/Y > 0.40 | Gini < 0.15 | MPC out of [0,1] |
|---|---|---|---|---|---|---|---|---|---|
| triad | 81 | 81 | 81 (100%) | 69 (85%) | 0 | 0 | 3 | 0 | 12 |
| ubc_experiment | 108 | 108 | 108 (100%) | 87 (81%) | 0 | 0 | 4 | 6 | 16 |
| frontier | 513 | 513 | 513 (100%) | 416 (81%) | 0 | 0 | 19 | 26 | 76 |
| rich_frontier | 1971 | 1971 | 1971 (100%) | 1541 (78%) | 0 | 0 | 73 | 173 | 292 |
| c1_ladder | 432 | 432 | 432 (100%) | 360 (83%) | 0 | 0 | 16 | 10 | 64 |
| proposals | 243 | 243 | 243 (100%) | 202 (83%) | 0 | 0 | 9 | 6 | 36 |
| pooling | 114 | 114 | 114 (100%) | 92 (81%) | 0 | 0 | 0 | 12 | 12 |
| mc_ubc (draws) | 5400 | 5400 | — | 1464 (27%) | 0 | 0 | 200 | 3620 | 792 |
| mc_cash_ubi (draws) | 5400 | 5400 | — | 4473 (83%) | 0 | 0 | 200 | 34 | 792 |

*Solvent = no household class with negative net worth or negative money. Check columns count runs failing that law at least once (a run can fail several).*

### Insolvency by policy form (deterministic runs, all countries)

| Policy form | Runs | Owners' money < 0 | Workers' money < 0 | Net worth < 0 |
|---|---|---|---|---|
| none | 324 | 0 (0%) | 0 (0%) | 0 (0%) |
| cash | 926 | 0 (0%) | 0 (0%) | 0 (0%) |
| ubc | 1537 | 0 (0%) | 0 (0%) | 0 (0%) |

Monte Carlo: net worth < 0 in 0/5,400 UBC draws and 0/5,400 cash draws.

### Baselines (no AI shift, no policy)

23 of 27 baselines pass. Failing:

- **IE:** I/Y > 0.40 from 2019, MPC out of [0,1] from 2019 (owners' MPC -0.0021, owners' money min 0.4547 x Y0, max I/Y 0.5357)
- **LU:** MPC out of [0,1] from 2019 (owners' MPC -0.3621, owners' money min 0.4271 x Y0, max I/Y 0.1866)
- **NL:** MPC out of [0,1] from 2019 (owners' MPC -0.0924, owners' money min 0.4225 x Y0, max I/Y 0.2091)
- **SI:** MPC out of [0,1] from 2019 (owners' MPC -0.2721, owners' money min 0.5433 x Y0, max I/Y 0.1976)

## Published numbers

| Surface | Runs behind it | Plausible | First failing laws (runs) |
|---|---|---|---|
| README headline + manifesto §III (DE: cash UBI vs UBC, wealth + growth) | 2 | 2/2 | none |
| README frontier chart (DE/FR/SK, frontier points) | 39 | 39/39 | none |
| Manifesto + dashboard frontier (DE, all 13 points) | 19 | 19/19 | none |
| Manifesto C1 ladder (DE, endogenous investment, cash vs UBC) | 8 | 8/8 | none |
| LinkedIn posts (DE/FR/SK cash vs UBC) | 6 | 5/6 | Gini < 0.15 (1) |
| Dashboard (all countries: triad + UBC experiment + frontier) | 702 | 572/702 | MPC out of [0,1] (104), Gini < 0.15 (32), I/Y > 0.40 (26) |
| F23 rich frontier (DE, all regimes) | 73 | 73/73 | none |
| Proposal library (DE) | 9 | 9/9 | none |
| Proposal library (all countries) | 243 | 202/243 | MPC out of [0,1] (36), I/Y > 0.40 (9), Gini < 0.15 (6) |
| Pooled dividend, EU bloc (manifesto/dashboard), cash_ubi (26/26 countries viable) | 52 | 46/52 | MPC out of [0,1] (6) |
| Pooled dividend, EU bloc (manifesto/dashboard), ubc (26/26 countries viable) | 52 | 36/52 | Gini < 0.15 (12), MPC out of [0,1] (6) |
| Pooled dividend, DE+FR+SK (posts), cash_ubi (3/3 countries viable) | 6 | 6/6 | none |
| Pooled dividend, DE+FR (posts), cash_ubi (2/2 countries viable) | 4 | 4/4 | none |
| F12 robustness bands (DE Monte Carlo, ubc) | 200 draws | 61/200 | Gini < 0.15 (136), MPC out of [0,1] (20) |
| F12 robustness bands (DE Monte Carlo, cash_ubi) | 200 draws | 180/200 | MPC out of [0,1] (20) |

The MCP tools and the agent crew use the orchestrator defaults, so they inherit the UBC-experiment and frontier rows above.

### The README headline runs (DE)

| Run | Plausible | First failing law (year) | Owners' net worth, min (x Y0) | Owners' money, min (x Y0) | Max I/Y | Min Gini |
|---|---|---|---|---|---|---|
| Baseline | yes | — | 3.7821 | 0.4762 | 0.2128 | 0.2968 |
| AI shift, no policy | yes | — | 3.7821 | 0.4762 | 0.2117 | 0.297 |
| AI + Cash UBI | yes | — | 3.7821 | 0.4604 | 0.2115 | 0.2389 |
| AI + Universal Basic Capital | yes | — | 3.7262 | 0.4762 | 0.2117 | 0.1831 |

## By country (plausible / runs)

| Country | Owners' MPC | Triad | UBC exp. | Frontier | Rich frontier | C1 ladder | Proposals | MC UBC | MC cash | Worst owners' net worth (x Y0) |
|---|---|---|---|---|---|---|---|---|---|---|
| AT | 0.0369 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 52/200 | 184/200 | 2.1055 |
| BE | 0.0271 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 110/200 | 173/200 | 3.3917 |
| BG | 0.2592 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 147/200 | 200/200 | 0.0478 |
| CY | 0.3627 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 57/200 | 200/200 | 1.2533 |
| CZ | 0.1718 | 3/3 | 3/4 | 15/19 | 47/73 | 15/16 | 8/9 | 22/200 | 200/200 | 0.9685 |
| DE | 0.0398 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 61/200 | 180/200 | 2.4704 |
| DK | 0.0448 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 67/200 | 196/200 | 3.0656 |
| EE | 0.1458 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 82/200 | 200/200 | 0.8622 |
| EL | 0.4712 | 3/3 | 3/4 | 16/19 | 51/73 | 15/16 | 8/9 | 28/200 | 200/200 | 1.0568 |
| ES | 0.2224 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 83/200 | 200/200 | 2.1049 |
| FI | 0.1599 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 53/200 | 200/200 | 1.9812 |
| FR | 0.0538 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 86/200 | 199/200 | 2.0281 |
| HR | 0.238 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 51/200 | 200/200 | 0.7129 |
| HU | 0.1998 | 3/3 | 4/4 | 19/19 | 72/73 | 16/16 | 9/9 | 55/200 | 200/200 | 1.6964 |
| IE | -0.0021 | 0/3 | 0/4 | 0/19 | 0/73 | 0/16 | 0/9 | 0/200 | 0/200 | 1.6062 |
| IT | 0.242 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 60/200 | 200/200 | 1.9377 |
| LT | 0.3441 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 76/200 | 200/200 | 0.8966 |
| LU | -0.3621 | 0/3 | 0/4 | 0/19 | 0/73 | 0/16 | 0/9 | 0/200 | 0/200 | 3.2068 |
| LV | 0.2257 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 118/200 | 200/200 | 0.3875 |
| MT | 0.0978 | 3/3 | 3/4 | 16/19 | 51/73 | 15/16 | 8/9 | 24/200 | 200/200 | 2.2516 |
| NL | -0.0924 | 0/3 | 0/4 | 0/19 | 0/73 | 0/16 | 0/9 | 0/200 | 0/200 | 2.1573 |
| PL | 0.3642 | 3/3 | 3/4 | 15/19 | 49/73 | 14/16 | 8/9 | 23/200 | 200/200 | 0.349 |
| PT | 0.3106 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 75/200 | 200/200 | 1.5503 |
| RO | 0.4951 | 3/3 | 4/4 | 19/19 | 64/73 | 16/16 | 9/9 | 56/200 | 200/200 | 0.0062 |
| SE | 0.0093 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 78/200 | 150/200 | 2.8527 |
| SI | -0.2721 | 0/3 | 0/4 | 0/19 | 0/73 | 0/16 | 0/9 | 0/200 | 0/200 | 2.8511 |
| SK | 0.3726 | 3/3 | 3/4 | 12/19 | 39/73 | 13/16 | 8/9 | 0/200 | 191/200 | 0.1493 |

## Reading

- **Accounting:** 3,462 of 3,462 runs balance their books.
- **Insolvency:** 0 runs and 0 Monte-Carlo draws (step B: 2 runs; steps C and D: 0). External positions are no longer split among households by their money, so no household carries the country's foreign debt.
- **Negative money:** owners in 0 runs (none), workers in 0 runs (none); Monte-Carlo draws: none. With the external position off household balance sheets (step D) the trade-linked overdrafts are gone. The law stays advisory until step F re-validates.
- **Investment above 40% of GDP:** 124 runs (60 of them UBC), all in IE (step B: 385 in the rich frontier alone). The fund now invests by the owners' rule, which responds to profitability and spare capacity, instead of sinking every retained euro into domestic capital.
- **Gini below 0.15:** 233 runs (UBC 217, cash 16, other 0) and 3,654 draws, 34 cash UBI and 3,620 UBC (step D: 720 runs; 5,787 draws, 914 cash). Market inequality now follows households' pre-tax capital income, so the levy is counted once, as a transfer. What remains is UBC at high claim rates: a fund that owns most domestic capital and pays an equal dividend compresses personal income below anything observed. The law is advisory until step F; the frontier already keeps those runs off.
- **Calibration:** owners' MPC outside [0, 1] in IE, LU, NL, SI; those countries' results stay unusable under this closure. (Step D: LU, SI.) Taxing capital at its observed 30% share of revenue moves base-year tax off wages; workers, with a consumption propensity of 0.95, then account for nearly all of household consumption, and the owners' propensity, solved as the residual, falls (DE 0.21 to 0.04) and turns negative in IE and NL. Step F's calibration review replaces the residual with observed saving rates.
- **Prices:** peak inflation above 5% in 3 of 3,057 runs and above 10% in 0; deflation in 113 runs, all in IE, RO.
- **Capacity ceiling binds** (demand met by extra imports): none 12/378 (6 for over a quarter of the years); cash 697/1034 (182 for over a quarter of the years); ubc 192/1645 (99 for over a quarter of the years). Baselines at the ceiling: EL (uniform K/Y = 3 calibration; step F).
- **Utilisation below the country's 2005-2019 trough** (the 2009 slump): 702 runs (AT 61, CZ 44, DE 15, DK 40, EL 2, ES 56, FI 3, FR 106, HR 18, HU 9, IE 109, IT 10, MT 9, NL 17, PL 3, PT 88, RO 112); by policy: UBC 449, cash 180, none 73. Under UBC with retained profits the fund keeps building as the profit share climbs (the profit response is applied far outside its sample; step F); with no policy, demand falls short under the AI shift.
- Interest rates are still fixed (no monetary-policy response until the banks step), so demand-led growth is not yet leaned against.
- **External positions (baselines):** NIIP -21% of GDP in 2019 (median) and +30% in 2049; largest moves: LU +83 to +513, IE -190 to +113, MT +120 to +351. Exports follow world demand while imports follow domestic output, so surplus countries keep accumulating; there is no exchange-rate or risk-premium feedback yet (step F).
- **Current account beyond +-10% of GDP** in some year: none 93; cash 258; ubc 749 runs. Mostly UBC: a fund that retains profits it cannot invest at home saves them abroad, as Norway's fund does.
- **AI rent reached (none):** median 0% of the AI rent by 2049 (216 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.78.
- **AI rent reached (cash):** median 12% of the AI rent by 2049 (1034 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.79.
- **AI rent reached (ubc):** median 20% of the AI rent by 2049 (1645 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.79.
- None of these families includes the source levy; its reach is pinned in `tests/test_external.py` (with 90% pass-through a 10% levy reaches 1% of the foreign rent).
- **Public debt with no policy (AI shift), 23 usable countries:** median 60% of GDP in 2019 and 128% in 2049; above 150% in 9 of 23 countries (BE, CY, EL, ES, FI, FR, HR, IT, PT). Largest rises: PT 122 to 252, EL 192 to 318, ES 103 to 228. Each government corrects by the estimated EU fiscal reaction (0.034 of the debt gap a year), which is too slow for a shock of this size: 70% of the AI rent is paid abroad as licence and cloud fees, so the profits it replaces wages with are largely outside the domestic tax base. No austerity or tax rise beyond the estimated reaction is assumed, and interest rates stay at each country's 2015-2019 rate (no risk premium until the banks step).
- **Fair prices (UBC benchmark):** the fund buys shares at market value; Tobin's q ends at a median 1.54 (2019 = 1) as AI raises profits, so each euro of the 40% claim buys fewer shares than at book value. It still ends up owning most domestic capital: the claim is large relative to new investment, whatever the price.

### Proposals against no policy (AI shift), median across the 23 countries whose no-policy run is plausible

| Proposal | Plausible | Real GNI 2049 | Consumption per head 2020-49 | Gini 2049 | Debt 2049 (pp) | AI rent reached 2049 | of the part paid abroad |
|---|---|---|---|---|---|---|---|
| No policy (AI shift) | 23/23 | level | level | 0.328 | 128% of GDP | 0% | 0% |
| One-time stock levy on AI firms (Sanders) | 23/23 | +0.5% | +1.9% | 0.307 | -11 | 15% | 0% |
| Voluntary AI pledges, best case (Anthropic-style) | 23/23 | +2.5% | +3.2% | 0.310 | -3 | 9% | 13% |
| Borrowing-financed citizens' fund | 23/23 | +3.4% | +1.1% | 0.320 | +14 | 0% | 0% |
| Child accounts (Fruehstart-Rente) | 23/23 | +0.1% | -0.0% | 0.328 | +1 | 0% | 0% |
| Levy on AI fees paid abroad (3%) | 23/23 | +0.1% | -0.2% | 0.327 | -6 | 2% | 0% |
| Cash UBI on a broad tax base | 23/23 | -0.8% | +6.6% | 0.262 | -1 | 5% | 0% |
| Benchmark: 40% capital levy, cash UBI | 23/23 | -5.0% | +21.8% | 0.225 | -2 | 12% | 0% |
| Benchmark: 40% claim in shares, fund pays 3% | 18/23 | +0.9% | -1.2% | 0.183 | -1 | 24% | 0% |

*GNI and consumption: % difference from no policy in the same country; debt: percentage-point difference in 2049. Benchmarks are the stylised 40% levy (cash) and 40% claim in shares (UBC); the pledge row is a best case.*

- **Frontier:** 97 of 513 frontier-search points fail a plausibility law and are kept off the frontier. Proposals on the frontier: stock_levy 23/27, pledge 22/27, debt_fund 23/27, child_accounts 3/27, source_levy 3/27, broad_ubi 23/27 countries. A sixth objective, average real consumption per person 2020-2049, sits beside growth (national income), equality, stability, fiscal space and resilience.
- **Caveats:** the pledge row assumes every foreign AI provider pays out like Anthropic's pledge and in proportion to its European fees; the stock levy has no valuation, relocation or compensation response; the debt-financed fund earns the world equity return (6.6%) while the state borrows at its 2015-2019 rate, a spread that a higher-rate world would narrow. Step F re-validates all of it.
