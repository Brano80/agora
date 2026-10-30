# Plausibility audit — 2026-10-29 (Phase 7, step D)

The same scenario families, countries and laws as the step-A, B and C audits, re-run on the engine with an **external sector**: foreign owners hold their observed share of domestic capital, owners hold their observed equity abroad, every country starts at its 2019 net international investment position, 70% of the AI rent is paid abroad as licence and cloud fees, the net external position is held by the public sector as a stand-in (no household carries it), and the citizens' fund invests abroad what it retains but cannot use at home. Reproduce: `python scripts/audit_plausibility.py` (step A: `--closure legacy`).

| Law | Fails when |
|---|---|
| `hh_net_worth_nonnegative` | a household class owes more than it owns (money + foreign assets + capital) |
| `money_split_shares_valid` | a household class holds negative money (an interest-free overdraft at the state) |
| `investment_share_bounded` | investment exceeds 40% of GDP |
| `gini_floor` | the personal Gini falls below 0.15 (lowest EU member in the data: SK 0.228) |
| `owners_mpc_in_unit_interval` | the owners' marginal propensity to consume, solved as a calibration residual, lies outside [0, 1] |

## Headline

- **Scenario runs:** 3,057 across 27 countries. **3,057 (100%) pass the accounting gate; 2,107 (69%) also pass the plausibility laws.**
- **Monte-Carlo draws** (the F12 robustness bands' priors, seed 0): 4,621 of 10,800 used draws (43%) are plausible.

## By scenario family (all countries)

| Family | Runs | Accounting OK | Solvent | Plausible | net worth < 0 | money < 0 | I/Y > 0.40 | Gini < 0.15 | MPC out of [0,1] |
|---|---|---|---|---|---|---|---|---|---|
| triad | 81 | 81 | 81 (100%) | 72 (89%) | 0 | 0 | 3 | 0 | 6 |
| ubc_experiment | 108 | 108 | 108 (100%) | 77 (71%) | 0 | 0 | 4 | 22 | 8 |
| frontier | 351 | 351 | 351 (100%) | 222 (63%) | 0 | 0 | 13 | 105 | 26 |
| rich_frontier | 1971 | 1971 | 1971 (100%) | 1313 (67%) | 0 | 0 | 73 | 516 | 146 |
| c1_ladder | 432 | 432 | 432 (100%) | 351 (81%) | 0 | 0 | 16 | 39 | 32 |
| pooling | 114 | 114 | 114 (100%) | 72 (63%) | 0 | 0 | 0 | 38 | 8 |
| mc_ubc (draws) | 5400 | 5400 | — | 508 (9%) | 0 | 0 | 200 | 4873 | 345 |
| mc_cash_ubi (draws) | 5400 | 5400 | — | 4113 (76%) | 0 | 0 | 200 | 914 | 345 |

*Solvent = no household class with negative net worth or negative money. Check columns count runs failing that law at least once (a run can fail several).*

### Insolvency by policy form (deterministic runs, all countries)

| Policy form | Runs | Owners' money < 0 | Workers' money < 0 | Net worth < 0 |
|---|---|---|---|---|
| none | 162 | 0 (0%) | 0 (0%) | 0 (0%) |
| cash | 926 | 0 (0%) | 0 (0%) | 0 (0%) |
| ubc | 1537 | 0 (0%) | 0 (0%) | 0 (0%) |

Monte Carlo: net worth < 0 in 0/5,400 UBC draws and 0/5,400 cash draws.

### Baselines (no AI shift, no policy)

24 of 27 baselines pass. Failing:

- **IE:** I/Y > 0.40 from 2019 (owners' MPC 0.0509, owners' money min 0.4424 x Y0, max I/Y 0.5357)
- **LU:** MPC out of [0,1] from 2019 (owners' MPC -0.1954, owners' money min 0.417 x Y0, max I/Y 0.1865)
- **SI:** MPC out of [0,1] from 2019 (owners' MPC -0.0536, owners' money min 0.5176 x Y0, max I/Y 0.1976)

## Published numbers

| Surface | Runs behind it | Plausible | First failing laws (runs) |
|---|---|---|---|
| README headline + manifesto §III (DE: cash UBI vs UBC, wealth + growth) | 2 | 1/2 | Gini < 0.15 (1) |
| README frontier chart (DE/FR/SK, frontier points) | 29 | 22/29 | Gini < 0.15 (7) |
| Manifesto + dashboard frontier (DE, all 13 points) | 13 | 9/13 | Gini < 0.15 (4) |
| Manifesto C1 ladder (DE, endogenous investment, cash vs UBC) | 8 | 7/8 | Gini < 0.15 (1) |
| LinkedIn posts (DE/FR/SK cash vs UBC) | 6 | 3/6 | Gini < 0.15 (3) |
| Dashboard (all countries: triad + UBC experiment + frontier) | 540 | 371/540 | Gini < 0.15 (127), MPC out of [0,1] (40), I/Y > 0.40 (20) |
| F23 rich frontier (DE, all regimes) | 73 | 58/73 | Gini < 0.15 (15) |
| Pooled dividend, EU bloc (manifesto/dashboard), cash_ubi (26/26 countries viable) | 52 | 48/52 | MPC out of [0,1] (4) |
| Pooled dividend, EU bloc (manifesto/dashboard), ubc (26/26 countries viable) | 52 | 14/52 | Gini < 0.15 (38), MPC out of [0,1] (4) |
| Pooled dividend, DE+FR+SK (posts), cash_ubi (3/3 countries viable) | 6 | 6/6 | none |
| Pooled dividend, DE+FR (posts), cash_ubi (2/2 countries viable) | 4 | 4/4 | none |
| F12 robustness bands (DE Monte Carlo, ubc) | 200 draws | 16/200 | Gini < 0.15 (184) |
| F12 robustness bands (DE Monte Carlo, cash_ubi) | 200 draws | 200/200 | none |

The MCP tools and the agent crew use the orchestrator defaults, so they inherit the UBC-experiment and frontier rows above.

### The README headline runs (DE)

| Run | Plausible | First failing law (year) | Owners' net worth, min (x Y0) | Owners' money, min (x Y0) | Max I/Y | Min Gini |
|---|---|---|---|---|---|---|
| Baseline | yes | — | 3.7681 | 0.4622 | 0.2115 | 0.2969 |
| AI shift, no policy | yes | — | 3.7681 | 0.4622 | 0.2207 | 0.297 |
| AI + Cash UBI | yes | — | 3.7681 | 0.4496 | 0.2115 | 0.2329 |
| AI + Universal Basic Capital | **no** | Gini < 0.15 (2041) | 2.9727 | 0.4622 | 0.2115 | 0.1376 |

## By country (plausible / runs)

| Country | Owners' MPC | Triad | UBC exp. | Frontier | Rich frontier | C1 ladder | MC UBC | MC cash | Worst owners' net worth (x Y0) |
|---|---|---|---|---|---|---|---|---|---|
| AT | 0.1857 | 3/3 | 3/4 | 9/13 | 54/73 | 15/16 | 8/200 | 174/200 | 1.8015 |
| BE | 0.2123 | 3/3 | 4/4 | 13/13 | 72/73 | 16/16 | 69/200 | 181/200 | 2.6559 |
| BG | 0.36 | 3/3 | 4/4 | 13/13 | 73/73 | 16/16 | 90/200 | 200/200 | 0.0328 |
| CY | 0.449 | 3/3 | 3/4 | 8/13 | 50/73 | 15/16 | 13/200 | 200/200 | 1.0122 |
| CZ | 0.2775 | 3/3 | 3/4 | 6/13 | 39/73 | 13/16 | 0/200 | 58/200 | 0.7587 |
| DE | 0.2073 | 3/3 | 3/4 | 9/13 | 58/73 | 15/16 | 16/200 | 200/200 | 2.0822 |
| DK | 0.2305 | 3/3 | 3/4 | 9/13 | 57/73 | 15/16 | 14/200 | 183/200 | 2.4805 |
| EE | 0.2675 | 3/3 | 4/4 | 13/13 | 66/73 | 16/16 | 34/200 | 200/200 | 0.7783 |
| EL | 0.5898 | 3/3 | 3/4 | 8/13 | 45/73 | 13/16 | 0/200 | 200/200 | 0.7564 |
| ES | 0.3362 | 3/3 | 3/4 | 9/13 | 57/73 | 15/16 | 28/200 | 200/200 | 1.8171 |
| FI | 0.3153 | 3/3 | 3/4 | 9/13 | 52/73 | 15/16 | 4/200 | 127/200 | 1.7892 |
| FR | 0.2552 | 3/3 | 3/4 | 9/13 | 59/73 | 15/16 | 31/200 | 200/200 | 1.856 |
| HR | 0.3711 | 3/3 | 3/4 | 9/13 | 49/73 | 14/16 | 5/200 | 192/200 | 0.5046 |
| HU | 0.2985 | 3/3 | 3/4 | 8/13 | 54/73 | 15/16 | 11/200 | 116/200 | 1.4223 |
| IE | 0.0509 | 0/3 | 0/4 | 0/13 | 0/73 | 0/16 | 0/200 | 0/200 | 1.7978 |
| IT | 0.356 | 3/3 | 3/4 | 8/13 | 48/73 | 14/16 | 9/200 | 200/200 | 1.4112 |
| LT | 0.421 | 3/3 | 3/4 | 9/13 | 57/73 | 15/16 | 27/200 | 200/200 | 0.7015 |
| LU | -0.1954 | 0/3 | 0/4 | 0/13 | 0/73 | 0/16 | 0/200 | 0/200 | 2.272 |
| LV | 0.3523 | 3/3 | 4/4 | 13/13 | 73/73 | 16/16 | 63/200 | 200/200 | 0.2284 |
| MT | 0.1916 | 3/3 | 3/4 | 8/13 | 46/73 | 13/16 | 0/200 | 135/200 | 1.4866 |
| NL | 0.1196 | 3/3 | 3/4 | 8/13 | 48/73 | 14/16 | 2/200 | 140/200 | 1.4748 |
| PL | 0.4418 | 3/3 | 3/4 | 8/13 | 45/73 | 13/16 | 0/200 | 145/200 | 0.1885 |
| PT | 0.4126 | 3/3 | 3/4 | 9/13 | 57/73 | 15/16 | 27/200 | 200/200 | 1.2152 |
| RO | 0.5554 | 3/3 | 3/4 | 8/13 | 46/73 | 14/16 | 10/200 | 195/200 | 0.0064 |
| SE | 0.2187 | 3/3 | 4/4 | 13/13 | 73/73 | 16/16 | 46/200 | 200/200 | 2.4863 |
| SI | -0.0536 | 0/3 | 0/4 | 0/13 | 0/73 | 0/16 | 1/200 | 42/200 | 1.0814 |
| SK | 0.457 | 3/3 | 3/4 | 6/13 | 35/73 | 13/16 | 0/200 | 25/200 | 0.1346 |

## Reading

- **Accounting:** 3,057 of 3,057 runs balance their books.
- **Insolvency:** 0 runs and 0 Monte-Carlo draws (step B: 2 runs; step C: 0). External positions are no longer split among households by their money, so no household carries the country's foreign debt.
- **Negative money:** owners in 0 runs (none), workers in 0 runs (none); Monte-Carlo draws: none. With the external position off household balance sheets (step D) the trade-linked overdrafts are gone. The law stays advisory until step F re-validates.
- **Investment above 40% of GDP:** 109 runs (59 of them UBC), all in IE (step B: 385 in the rich frontier alone). The fund now invests by the owners' rule, which responds to profitability and spare capacity, instead of sinking every retained euro into domestic capital.
- **Gini below 0.15:** 720 runs and 5,787 draws, 914 of them cash UBI (step B: 1,039 runs; 35 cash draws). Not a supply-side effect: until now every policy arm anchored its distribution on a year 0 with the policy already on, so the observed 2019 Gini was assigned to an economy paying a 40% levy and a UBI. With policies from 2020 the anchor is the real 2019 economy, and a double count in the distribution layer shows: the levy lowers the net capital share that drives *market* inequality and is also counted as a transfer. Fixed in step E.
- **Calibration:** owners' MPC outside [0, 1] in LU, SI; those countries' results stay unusable under this closure.
- **Prices:** peak inflation above 5% in 3 of 3,057 runs and above 10% in 0; deflation in 112 runs, all in IE, RO.
- **Capacity ceiling binds** (demand met by extra imports): none 19/378 (12 for over a quarter of the years); cash 636/1034 (201 for over a quarter of the years); ubc 237/1645 (127 for over a quarter of the years). Baselines at the ceiling: EL, RO (uniform K/Y = 3 calibration; step F).
- **Utilisation below the country's 2005-2019 trough** (the 2009 slump): 626 runs (AT 54, CZ 32, DE 5, DK 33, EL 3, ES 43, FI 3, FR 81, HR 18, IE 109, IT 8, MT 9, NL 21, PL 5, PT 90, RO 112); by policy: UBC 408, cash 152, none 66. Under UBC with retained profits the fund keeps building as the profit share climbs (the profit response is applied far outside its sample; step F); with no policy, demand falls short under the AI shift.
- Interest rates are still fixed (no monetary-policy response until the banks step), so demand-led growth is not yet leaned against.
- **External positions (baselines):** NIIP -23% of GDP in 2019 (median) and +12% in 2049; largest moves: IE -186 to +124, LU +81 to +390, MT +115 to +238. Exports follow world demand while imports follow domestic output, so surplus countries keep accumulating; there is no exchange-rate or risk-premium feedback yet (step F).
- **Current account beyond +-10% of GDP** in some year: none 49; cash 189; ubc 754 runs. Mostly UBC: a fund that retains profits it cannot invest at home saves them abroad, as Norway's fund does.
- **AI rent reached (none):** median 0% of the AI rent by 2049 (216 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.76.
- **AI rent reached (cash):** median 12% of the AI rent by 2049 (1034 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.79.
- **AI rent reached (ubc):** median 21% of the AI rent by 2049 (1645 runs with the AI shift); of the part earned abroad, 0% at most. National income / GDP: median 0.77.
- None of these families includes the source levy; its reach is pinned in `tests/test_external.py` (with 90% pass-through a 10% levy reaches 1% of the foreign rent).
