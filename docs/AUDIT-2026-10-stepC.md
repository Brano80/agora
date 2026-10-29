# Plausibility audit — 2026-10-29 (Phase 7, step C)

The same scenario families, countries and laws as the step-A audit (`docs/AUDIT-2026-10.md`, the v1.1 engine) and the step-B audit (`docs/AUDIT-2026-10-stepB.md`), re-run on the engine with a **supply side and prices**: real output is capped by installed capital, excess demand leaks into imports, inflation follows a Phillips curve around the ECB 2% target, AI raises productivity, and policies switch on in 2020 so 2019 reproduces in every arm. Reproduce: `python scripts/audit_plausibility.py` (step A: `--closure legacy`).

| Law | Fails when |
|---|---|
| `hh_net_worth_nonnegative` | a household class owes more than it owns (money + foreign assets + capital) |
| `money_split_shares_valid` | a household class holds negative money (an interest-free overdraft at the state) |
| `investment_share_bounded` | investment exceeds 40% of GDP |
| `gini_floor` | the personal Gini falls below 0.15 (lowest EU member in the data: SK 0.228) |
| `owners_mpc_in_unit_interval` | the owners' marginal propensity to consume, solved as a calibration residual, lies outside [0, 1] |

## Headline

- **Scenario runs:** 3,057 across 27 countries. **3,057 (100%) pass the accounting gate; 1,482 (48%) also pass the plausibility laws.**
- **Monte-Carlo draws** (the F12 robustness bands' priors, seed 0): 3,960 of 10,800 used draws (37%) are plausible.

## By scenario family (all countries)

| Family | Runs | Accounting OK | Solvent | Plausible | net worth < 0 | money < 0 | I/Y > 0.40 | Gini < 0.15 | MPC out of [0,1] |
|---|---|---|---|---|---|---|---|---|---|
| triad | 81 | 81 | 78 (96%) | 72 (89%) | 0 | 3 | 3 | 0 | 6 |
| ubc_experiment | 108 | 108 | 104 (96%) | 72 (67%) | 0 | 4 | 4 | 27 | 8 |
| frontier | 351 | 351 | 338 (96%) | 185 (53%) | 0 | 13 | 13 | 144 | 26 |
| rich_frontier | 1971 | 1971 | 1898 (96%) | 805 (41%) | 0 | 73 | 73 | 1066 | 146 |
| c1_ladder | 432 | 432 | 416 (96%) | 288 (67%) | 0 | 16 | 16 | 108 | 32 |
| pooling | 114 | 114 | 110 (96%) | 60 (53%) | 0 | 4 | 0 | 50 | 8 |
| mc_ubc (draws) | 5400 | 5400 | — | 24 (0%) | 0 | 187 | 200 | 5376 | 346 |
| mc_cash_ubi (draws) | 5400 | 5400 | — | 3936 (73%) | 0 | 148 | 200 | 1094 | 346 |

*Solvent = no household class with negative net worth or negative money. Check columns count runs failing that law at least once (a run can fail several).*

### Insolvency by policy form (deterministic runs, all countries)

| Policy form | Runs | Owners' money < 0 | Workers' money < 0 | Net worth < 0 |
|---|---|---|---|---|
| none | 162 | 0 (0%) | 6 (4%) | 0 (0%) |
| cash | 926 | 0 (0%) | 34 (4%) | 0 (0%) |
| ubc | 1537 | 0 (0%) | 57 (4%) | 0 (0%) |

Monte Carlo: net worth < 0 in 0/5,400 UBC draws and 0/5,400 cash draws.

### Baselines (no AI shift, no policy)

24 of 27 baselines pass. Failing:

- **IE:** I/Y > 0.40 from 2019 (owners' MPC 0.0509, owners' money min 0.4084 x Y0, max I/Y 0.5357)
- **LU:** money < 0 from 2019, MPC out of [0,1] from 2019 (owners' MPC -0.1954, owners' money min 0.2053 x Y0, max I/Y 0.1887)
- **SI:** MPC out of [0,1] from 2019 (owners' MPC -0.0536, owners' money min 0.4767 x Y0, max I/Y 0.1978)

## Published numbers

| Surface | Runs behind it | Plausible | First failing laws (runs) |
|---|---|---|---|
| README headline + manifesto §III (DE: cash UBI vs UBC, wealth + growth) | 2 | 1/2 | Gini < 0.15 (1) |
| README frontier chart (DE/FR/SK, frontier points) | 30 | 16/30 | Gini < 0.15 (14) |
| Manifesto + dashboard frontier (DE, all 13 points) | 13 | 8/13 | Gini < 0.15 (5) |
| Manifesto C1 ladder (DE, endogenous investment, cash vs UBC) | 8 | 4/8 | Gini < 0.15 (4) |
| LinkedIn posts (DE/FR/SK cash vs UBC) | 6 | 3/6 | Gini < 0.15 (3) |
| Dashboard (all countries: triad + UBC experiment + frontier) | 540 | 329/540 | Gini < 0.15 (171), MPC out of [0,1] (40), I/Y > 0.40 (20), money < 0 (20) |
| F23 rich frontier (DE, all regimes) | 73 | 35/73 | Gini < 0.15 (38) |
| Pooled dividend, EU bloc (manifesto/dashboard), cash_ubi (26/26 countries viable) | 52 | 48/52 | MPC out of [0,1] (4), money < 0 (2) |
| Pooled dividend, EU bloc (manifesto/dashboard), ubc (26/26 countries viable) | 52 | 2/52 | Gini < 0.15 (50), MPC out of [0,1] (4), money < 0 (2) |
| Pooled dividend, DE+FR+SK (posts), cash_ubi (3/3 countries viable) | 6 | 6/6 | none |
| Pooled dividend, DE+FR (posts), cash_ubi (2/2 countries viable) | 4 | 4/4 | none |
| Pooled dividend, EU bloc (manifesto/dashboard), cash_ubi (26/26 countries viable) | 52 | 48/52 | MPC out of [0,1] (4), money < 0 (2) |
| Pooled dividend, EU bloc (manifesto/dashboard), ubc (26/26 countries viable) | 52 | 2/52 | Gini < 0.15 (50), MPC out of [0,1] (4), money < 0 (2) |
| Pooled dividend, DE+FR+SK (posts), cash_ubi (3/3 countries viable) | 6 | 6/6 | none |
| Pooled dividend, DE+FR (posts), cash_ubi (2/2 countries viable) | 4 | 4/4 | none |
| F12 robustness bands (DE Monte Carlo, ubc) | 200 draws | 0/200 | Gini < 0.15 (200) |
| F12 robustness bands (DE Monte Carlo, cash_ubi) | 200 draws | 200/200 | none |

The MCP tools and the agent crew use the orchestrator defaults, so they inherit the UBC-experiment and frontier rows above.

### The README headline runs (DE)

| Run | Plausible | First failing law (year) | Owners' net worth, min (x Y0) | Owners' money, min (x Y0) | Max I/Y | Min Gini |
|---|---|---|---|---|---|---|
| Baseline | yes | — | 3.4895 | 0.4187 | 0.2115 | 0.297 |
| AI shift, no policy | yes | — | 3.4895 | 0.4187 | 0.308 | 0.297 |
| AI + Cash UBI | yes | — | 3.4895 | 0.3863 | 0.2211 | 0.2271 |
| AI + Universal Basic Capital | **no** | Gini < 0.15 (2034) | 2.2179 | 0.4187 | 0.2115 | 0.0664 |

## By country (plausible / runs)

| Country | Owners' MPC | Triad | UBC exp. | Frontier | Rich frontier | C1 ladder | MC UBC | MC cash | Worst owners' net worth (x Y0) |
|---|---|---|---|---|---|---|---|---|---|
| AT | 0.1857 | 3/3 | 3/4 | 8/13 | 35/73 | 12/16 | 0/200 | 155/200 | 1.3488 |
| BE | 0.2123 | 3/3 | 3/4 | 7/13 | 33/73 | 12/16 | 0/200 | 112/200 | 1.365 |
| BG | 0.36 | 3/3 | 3/4 | 8/13 | 37/73 | 12/16 | 17/200 | 200/200 | 0.6184 |
| CY | 0.449 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.9685 |
| CZ | 0.2775 | 3/3 | 3/4 | 7/13 | 29/73 | 12/16 | 0/200 | 59/200 | 1.0352 |
| DE | 0.2073 | 3/3 | 3/4 | 8/13 | 35/73 | 12/16 | 0/200 | 200/200 | 1.3615 |
| DK | 0.2305 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 153/200 | 1.194 |
| EE | 0.2675 | 3/3 | 3/4 | 8/13 | 37/73 | 12/16 | 0/200 | 199/200 | 0.8397 |
| EL | 0.5898 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 1.254 |
| ES | 0.3362 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 1/200 | 200/200 | 1.2772 |
| FI | 0.3153 | 3/3 | 3/4 | 7/13 | 32/73 | 12/16 | 0/200 | 114/200 | 0.9977 |
| FR | 0.2552 | 3/3 | 3/4 | 8/13 | 37/73 | 12/16 | 0/200 | 198/200 | 1.2241 |
| HR | 0.3711 | 3/3 | 3/4 | 8/13 | 35/73 | 12/16 | 0/200 | 187/200 | 0.8946 |
| HU | 0.2985 | 3/3 | 3/4 | 7/13 | 31/73 | 12/16 | 0/200 | 112/200 | 0.9896 |
| IE | 0.0509 | 0/3 | 0/4 | 0/13 | 0/73 | 0/16 | 0/200 | 0/200 | 1.5555 |
| IT | 0.356 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 1/200 | 200/200 | 1.5314 |
| LT | 0.421 | 3/3 | 3/4 | 8/13 | 35/73 | 12/16 | 2/200 | 200/200 | 0.9721 |
| LU | -0.1954 | 0/3 | 0/4 | 0/13 | 0/73 | 0/16 | 0/200 | 0/200 | 2.7964 |
| LV | 0.3523 | 3/3 | 3/4 | 8/13 | 37/73 | 12/16 | 2/200 | 200/200 | 0.6452 |
| MT | 0.1916 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 134/200 | 1.6399 |
| NL | 0.1196 | 3/3 | 3/4 | 7/13 | 31/73 | 12/16 | 0/200 | 133/200 | 1.6155 |
| PL | 0.4418 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 153/200 | 0.7268 |
| PT | 0.4126 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 1.1833 |
| RO | 0.5554 | 3/3 | 3/4 | 8/13 | 35/73 | 12/16 | 1/200 | 200/200 | 0.1569 |
| SE | 0.2187 | 3/3 | 3/4 | 8/13 | 35/73 | 12/16 | 0/200 | 152/200 | 1.0655 |
| SI | -0.0536 | 0/3 | 0/4 | 0/13 | 0/73 | 0/16 | 0/200 | 35/200 | 1.9889 |
| SK | 0.457 | 3/3 | 3/4 | 6/13 | 27/73 | 12/16 | 0/200 | 40/200 | 0.506 |

## Reading

- **Accounting:** 3,057 of 3,057 runs balance their books.
- **Insolvency:** 0 runs and 0 Monte-Carlo draws (step B: 2 runs). The SK runs that failed in step B reinvested without limit; with a capacity ceiling the fund invests by the owners' rule and the current-account deficit no longer compounds. The external-position rule behind them is still replaced in step D.
- **Negative money:** owners in 0 runs (none), workers in 113 runs (LU); Monte-Carlo draws: IE 119, LU 216. No owner overdraft remains outside countries whose calibration is unusable. Workers' overdrafts arise there too, and in trade-linked runs from the external-position rule. This law stays advisory until step D.
- **Investment above 40% of GDP:** 109 runs (59 of them UBC), all in IE (step B: 385 in the rich frontier alone). The fund now invests by the owners' rule, which responds to profitability and spare capacity, instead of sinking every retained euro into domestic capital.
- **Gini below 0.15:** 1,395 runs and 6,470 draws, 1,094 of them cash UBI (step B: 1,039 runs; 35 cash draws). Not a supply-side effect: until now every policy arm anchored its distribution on a year 0 with the policy already on, so the observed 2019 Gini was assigned to an economy paying a 40% levy and a UBI. With policies from 2020 the anchor is the real 2019 economy, and a double count in the distribution layer shows: the levy lowers the net capital share that drives *market* inequality and is also counted as a transfer. Fixed in step E.
- **Calibration:** owners' MPC outside [0, 1] in LU, SI; those countries' results stay unusable under this closure.
- **Prices:** peak inflation above 5% in 13 of 3,057 runs and above 10% in 0; deflation in 109 runs, all in IE.
- **Capacity ceiling binds** (demand met by extra imports): none 14/378 (14 for over a quarter of the years); cash 551/1034 (253 for over a quarter of the years); ubc 1106/1645 (822 for over a quarter of the years). Baselines at the ceiling: EL (uniform K/Y = 3 calibration; step F).
- **Utilisation below 0.70** (below the 2009 trough): 128 runs, in IE, SI.
- Interest rates are still fixed (no monetary-policy response until the banks step), so demand-led growth is not yet leaned against.
