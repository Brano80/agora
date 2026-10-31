# Plausibility audit — 2026-10-31 (Phase 7, step E5)

The step-E engine (`docs/AUDIT-2026-10-stepE.md`) with one change: both classes' propensities to consume are solved from 2019 consumption and each country's published effect of moving income from wages to profits on consumption (Onaran & Obst 2016 for the EU15, Kaczmarski 2024 for Poland, the EU15 median elsewhere), and owners consume out of their income net of depreciation on the capital they own. Before, workers were fixed at 0.95 and owners took the residual, which put them near zero or below. Same families, countries and laws. Reproduce: `python scripts/audit_plausibility.py --step E5`.

| Law | Fails when |
|---|---|
| `hh_net_worth_nonnegative` | a household class owes more than it owns (money + foreign assets + capital) |
| `money_split_shares_valid` | a household class holds negative money (an interest-free overdraft at the state) |
| `investment_share_bounded` | investment exceeds 40% of GDP |
| `gini_floor` | the personal Gini falls below 0.15 (lowest EU member in the data: SK 0.228) |
| `owners_mpc_in_unit_interval` | the owners' marginal propensity to consume, solved as a calibration residual, lies outside [0, 1] |

## Headline

- **Scenario runs:** 3,462 across 27 countries. **3,462 (100%) pass the accounting gate; 3,128 (90%) also pass the plausibility laws.**
- **Monte-Carlo draws** (the F12 robustness bands' priors, seed 0): 6,852 of 10,800 used draws (63%) are plausible.

## By scenario family (all countries)

| Family | Runs | Accounting OK | Solvent | Plausible | net worth < 0 | money < 0 | I/Y > 0.40 | Gini < 0.15 | MPC out of [0,1] |
|---|---|---|---|---|---|---|---|---|---|
| triad | 81 | 81 | 81 (100%) | 78 (96%) | 0 | 0 | 3 | 0 | 0 |
| ubc_experiment | 108 | 108 | 108 (100%) | 99 (92%) | 0 | 0 | 4 | 6 | 0 |
| frontier | 513 | 513 | 513 (100%) | 472 (92%) | 0 | 0 | 19 | 25 | 0 |
| rich_frontier | 1971 | 1971 | 1971 (100%) | 1743 (88%) | 0 | 0 | 73 | 184 | 0 |
| c1_ladder | 432 | 432 | 432 (100%) | 407 (94%) | 0 | 0 | 16 | 11 | 0 |
| proposals | 243 | 243 | 243 (100%) | 229 (94%) | 0 | 0 | 9 | 6 | 0 |
| pooling | 114 | 114 | 114 (100%) | 100 (88%) | 0 | 0 | 0 | 14 | 0 |
| mc_ubc (draws) | 5400 | 5400 | — | 1711 (32%) | 0 | 0 | 200 | 3645 | 59 |
| mc_cash_ubi (draws) | 5400 | 5400 | — | 5141 (95%) | 0 | 0 | 200 | 28 | 59 |

*Solvent = no household class with negative net worth or negative money. Check columns count runs failing that law at least once (a run can fail several).*

### Insolvency by policy form (deterministic runs, all countries)

| Policy form | Runs | Owners' money < 0 | Workers' money < 0 | Net worth < 0 |
|---|---|---|---|---|
| none | 324 | 0 (0%) | 0 (0%) | 0 (0%) |
| cash | 926 | 0 (0%) | 0 (0%) | 0 (0%) |
| ubc | 1537 | 0 (0%) | 0 (0%) | 0 (0%) |

Monte Carlo: net worth < 0 in 0/5,400 UBC draws and 0/5,400 cash draws.

### Baselines (no AI shift, no policy)

26 of 27 baselines pass. Failing:

- **IE:** I/Y > 0.40 from 2019 (owners' MPC 0.2582, owners' money min 0.2938 x Y0, max I/Y 0.5357)

## Published numbers

| Surface | Runs behind it | Plausible | First failing laws (runs) |
|---|---|---|---|
| README headline + manifesto §III (DE: cash UBI vs UBC, wealth + growth) | 2 | 2/2 | none |
| README frontier chart (DE/FR/SK, frontier points) | 40 | 40/40 | none |
| Manifesto + dashboard frontier (DE, all 13 points) | 19 | 19/19 | none |
| Manifesto C1 ladder (DE, endogenous investment, cash vs UBC) | 8 | 8/8 | none |
| LinkedIn posts (DE/FR/SK cash vs UBC) | 6 | 5/6 | Gini < 0.15 (1) |
| Dashboard (all countries: triad + UBC experiment + frontier) | 702 | 649/702 | Gini < 0.15 (31), I/Y > 0.40 (26) |
| F23 rich frontier (DE, all regimes) | 73 | 73/73 | none |
| Proposal library (DE) | 9 | 9/9 | none |
| Proposal library (all countries) | 243 | 229/243 | I/Y > 0.40 (9), Gini < 0.15 (6) |
| Pooled dividend, EU bloc (manifesto/dashboard), cash_ubi (26/26 countries viable) | 52 | 52/52 | none |
| Pooled dividend, EU bloc (manifesto/dashboard), ubc (26/26 countries viable) | 52 | 38/52 | Gini < 0.15 (14) |
| Pooled dividend, DE+FR+SK (posts), cash_ubi (3/3 countries viable) | 6 | 6/6 | none |
| Pooled dividend, DE+FR (posts), cash_ubi (2/2 countries viable) | 4 | 4/4 | none |
| F12 robustness bands (DE Monte Carlo, ubc) | 200 draws | 65/200 | Gini < 0.15 (135) |
| F12 robustness bands (DE Monte Carlo, cash_ubi) | 200 draws | 200/200 | none |

The MCP tools and the agent crew use the orchestrator defaults, so they inherit the UBC-experiment and frontier rows above.

### The README headline runs (DE)

| Run | Plausible | First failing law (year) | Owners' net worth, min (x Y0) | Owners' money, min (x Y0) | Max I/Y | Min Gini |
|---|---|---|---|---|---|---|
| Baseline | yes | — | 3.7397 | 0.4338 | 0.2157 | 0.2968 |
| AI shift, no policy | yes | — | 3.7397 | 0.4338 | 0.2115 | 0.297 |
| AI + Cash UBI | yes | — | 3.7397 | 0.4003 | 0.2115 | 0.239 |
| AI + Universal Basic Capital | yes | — | 2.9164 | 0.4338 | 0.2115 | 0.1823 |

## By country (plausible / runs)

| Country | Owners' MPC | Triad | UBC exp. | Frontier | Rich frontier | C1 ladder | Proposals | MC UBC | MC cash | Worst owners' net worth (x Y0) |
|---|---|---|---|---|---|---|---|---|---|---|
| AT | 0.5115 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 53/200 | 200/200 | 1.2595 |
| BE | 0.9453 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 72/200 | 141/200 | 1.7568 |
| BG | 0.7633 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 147/200 | 200/200 | 0.0362 |
| CY | 0.6496 | 3/3 | 4/4 | 19/19 | 66/73 | 16/16 | 9/9 | 57/200 | 200/200 | 1.2153 |
| CZ | 0.6255 | 3/3 | 3/4 | 15/19 | 47/73 | 15/16 | 8/9 | 21/200 | 200/200 | 0.6386 |
| DE | 0.389 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 65/200 | 200/200 | 1.8726 |
| DK | 0.6419 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 67/200 | 200/200 | 1.704 |
| EE | 0.631 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 82/200 | 200/200 | 0.543 |
| EL | 0.7803 | 3/3 | 3/4 | 15/19 | 51/73 | 14/16 | 8/9 | 26/200 | 200/200 | 0.9584 |
| ES | 0.4448 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 80/200 | 200/200 | 1.9308 |
| FI | 0.6132 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 53/200 | 200/200 | 1.4276 |
| FR | 0.5013 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 86/200 | 200/200 | 1.5348 |
| HR | 0.5799 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 50/200 | 200/200 | 0.6814 |
| HU | 0.5895 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 55/200 | 200/200 | 1.3038 |
| IE | 0.2582 | 0/3 | 0/4 | 0/19 | 0/73 | 0/16 | 0/9 | 0/200 | 0/200 | 0.8926 |
| IT | 0.4355 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 60/200 | 200/200 | 1.8048 |
| LT | 0.6384 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 74/200 | 200/200 | 0.9287 |
| LU | 0.3949 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 66/200 | 200/200 | 1.4111 |
| LV | 0.7223 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 117/200 | 200/200 | 0.3029 |
| MT | 0.4212 | 3/3 | 3/4 | 16/19 | 51/73 | 15/16 | 8/9 | 26/200 | 200/200 | 1.5151 |
| NL | 0.4145 | 3/3 | 4/4 | 19/19 | 68/73 | 16/16 | 9/9 | 43/200 | 200/200 | 1.0813 |
| PL | 0.6864 | 3/3 | 3/4 | 15/19 | 49/73 | 14/16 | 8/9 | 21/200 | 200/200 | 0.3048 |
| PT | 0.555 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 74/200 | 200/200 | 1.551 |
| RO | 0.8838 | 3/3 | 4/4 | 19/19 | 57/73 | 16/16 | 9/9 | 55/200 | 200/200 | 0.0047 |
| SE | 0.4142 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 105/200 | 200/200 | 2.1713 |
| SI | 0.5526 | 3/3 | 4/4 | 19/19 | 73/73 | 16/16 | 9/9 | 156/200 | 200/200 | 0.868 |
| SK | 0.678 | 3/3 | 3/4 | 12/19 | 40/73 | 13/16 | 8/9 | 0/200 | 200/200 | 0.1546 |

## Reading

- **Accounting:** 3,462 of 3,462 runs balance their books.
- **Insolvency:** 0 runs and 0 Monte-Carlo draws (step B: 2 runs; steps C to E: 0). External positions are no longer split among households by their money, so no household carries the country's foreign debt.
- **Negative money:** owners in 0 runs (none), workers in 0 runs (none); Monte-Carlo draws: none. With the external position off household balance sheets (step D) the trade-linked overdrafts are gone. The law stays advisory until step F re-validates.
- **Investment above 40% of GDP:** 124 runs (60 of them UBC), all in IE (step B: 385 in the rich frontier alone). The fund now invests by the owners' rule, which responds to profitability and spare capacity, instead of sinking every retained euro into domestic capital.
- **Gini below 0.15:** 246 runs (UBC 233, cash 13, other 0) and 3,673 draws, 28 cash UBI and 3,645 UBC (step E: 233 runs, 217 UBC; 3,654 draws, 34 cash). Market inequality now follows households' pre-tax capital income, so the levy is counted once, as a transfer. What remains is UBC at high claim rates: a fund that owns most domestic capital and pays an equal dividend compresses personal income below anything observed. The law is advisory until step F; the frontier already keeps those runs off.
- **Calibration:** owners' MPC outside [0, 1] in no country. (Step E: IE, LU, NL, SI.) Both propensities are now solved from 2019 consumption and the published wage/profit consumption gap, so no country needs a residual.
- **Prices:** peak inflation above 5% in 1 of 3,057 runs and above 10% in 0; deflation in 130 runs, all in IE, RO.
- **Capacity ceiling binds** (demand met by extra imports): none 26/378 (18 for over a quarter of the years); cash 548/1034 (131 for over a quarter of the years); ubc 213/1645 (103 for over a quarter of the years). Baselines at the ceiling: BE, EL, IT (uniform K/Y = 3 calibration; step F).
- **Utilisation below the country's 2005-2019 trough** (the 2009 slump): 684 runs (AT 53, CZ 42, DE 5, DK 28, EL 2, ES 51, FI 2, FR 109, HR 33, HU 8, IE 109, IT 13, MT 8, NL 15, PL 6, PT 88, RO 112); by policy: UBC 449, cash 170, none 65. Under UBC with retained profits the fund keeps building as the profit share climbs (the profit response is applied far outside its sample; step F); with no policy, demand falls short under the AI shift.
- Interest rates are still fixed (no monetary-policy response until the banks step), so demand-led growth is not yet leaned against.
- **External positions (baselines):** NIIP -21% of GDP in 2019 (median) and +22% in 2049; largest moves: LU +83 to +428, IE -190 to +112, MT +120 to +295. Exports follow world demand while imports follow domestic output, so surplus countries keep accumulating; there is no exchange-rate or risk-premium feedback yet (step F).
- **Current account beyond +-10% of GDP** in some year: none 74; cash 253; ubc 729 runs. Mostly UBC: a fund that retains profits it cannot invest at home saves them abroad, as Norway's fund does.
- **AI rent reached (none):** median 0% of the AI rent by 2049 (216 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.77.
- **AI rent reached (cash):** median 12% of the AI rent by 2049 (1034 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.79.
- **AI rent reached (ubc):** median 20% of the AI rent by 2049 (1645 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.79.
- None of these families includes the source levy; its reach is pinned in `tests/test_external.py` (with 90% pass-through a 10% levy reaches 1% of the foreign rent).
- **Public debt with no policy (AI shift), 26 usable countries:** median 55% of GDP in 2019 and 117% in 2049; above 150% in 8 of 26 countries (BE, CY, EL, ES, FR, HR, IT, PT). Largest rises: PT 122 to 250, EL 192 to 318, ES 103 to 224. Each government corrects by the estimated EU fiscal reaction (0.034 of the debt gap a year), which is too slow for a shock of this size: 70% of the AI rent is paid abroad as licence and cloud fees, so the profits it replaces wages with are largely outside the domestic tax base. No austerity or tax rise beyond the estimated reaction is assumed, and interest rates stay at each country's 2015-2019 rate (no risk premium until the banks step).
- **Propensities to consume (27 countries):** workers median 0.88 (0.55-1.00), owners median 0.59 (0.26-0.95) out of income net of depreciation. Workers are capped at 1 in EL, RO, SK, where 2019 consumption is too high for the published gap (households dissaved or nearly so); there owners take the remainder and the gap is smaller than estimated. The EU15 median gap is used for BG, CY, CZ, EE, HR, HU, LT, LV, MT, RO, SI, SK.
- **Fair prices (UBC benchmark):** the fund buys shares at market value; Tobin's q ends at a median 1.54 (2019 = 1) as AI raises profits, so each euro of the 40% claim buys fewer shares than at book value. It still ends up owning most domestic capital: the claim is large relative to new investment, whatever the price.

### Proposals against no policy (AI shift), median across the 26 countries whose no-policy run is plausible

| Proposal | Plausible | Real GNI 2049 | Consumption per head 2020-49 | Gini 2049 | Debt 2049 (pp) | AI rent reached 2049 | of the part paid abroad |
|---|---|---|---|---|---|---|---|
| No policy (AI shift) | 26/26 | level | level | 0.326 | 117% of GDP | 0% | 0% |
| One-time stock levy on AI firms (Sanders) | 26/26 | +0.4% | +1.1% | 0.304 | -11 | 15% | 0% |
| Voluntary AI pledges, best case (Anthropic-style) | 26/26 | +2.5% | +3.4% | 0.308 | -2 | 9% | 13% |
| Borrowing-financed citizens' fund | 26/26 | +3.3% | +1.1% | 0.319 | +13 | 0% | 0% |
| Child accounts (Fruehstart-Rente) | 26/26 | +0.1% | -0.0% | 0.326 | +1 | 0% | 0% |
| Levy on AI fees paid abroad (3%) | 26/26 | +0.1% | -0.3% | 0.325 | -6 | 2% | 0% |
| Cash UBI on a broad tax base | 26/26 | -0.7% | +5.2% | 0.262 | -1 | 5% | 0% |
| Benchmark: 40% capital levy, cash UBI | 26/26 | -4.1% | +14.5% | 0.223 | -3 | 12% | 0% |
| Benchmark: 40% claim in shares, fund pays 3% | 21/26 | -0.1% | -2.4% | 0.183 | +0 | 24% | 0% |

*GNI and consumption: % difference from no policy in the same country; debt: percentage-point difference in 2049. Benchmarks are the stylised 40% levy (cash) and 40% claim in shares (UBC); the pledge row is a best case.*

- **Frontier:** 41 of 513 frontier-search points fail a plausibility law and are kept off the frontier. Proposals on the frontier: stock_levy 26/27, pledge 26/27, debt_fund 25/27, child_accounts 5/27, source_levy 4/27, broad_ubi 26/27 countries. A sixth objective, average real consumption per person 2020-2049, sits beside growth (national income), equality, stability, fiscal space and resilience.
- **Caveats:** the pledge row assumes every foreign AI provider pays out like Anthropic's pledge and in proportion to its European fees; the stock levy has no valuation, relocation or compensation response; the debt-financed fund earns the world equity return (6.6%) while the state borrows at its 2015-2019 rate, a spread that a higher-rate world would narrow. Step F re-validates all of it.
