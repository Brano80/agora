# Plausibility audit — 2026-10-29 (Phase 7, step B)

The same scenario families, countries and laws as the step-A audit (`docs/AUDIT-2026-10.md`, the v1.1 engine), re-run on the **behavioural investment closure**: investment responds to owners' net profit share, is financed saving-first with capped, interest-bearing loans, and owners invest only on the capital they own. Reproduce: `python scripts/audit_plausibility.py` (step A: `--closure legacy`).

| Law | Fails when |
|---|---|
| `hh_net_worth_nonnegative` | a household class owes more than it owns (money + foreign assets + capital) |
| `money_split_shares_valid` | a household class holds negative money (an interest-free overdraft at the state) |
| `investment_share_bounded` | investment exceeds 40% of GDP |
| `gini_floor` | the personal Gini falls below 0.15 (lowest EU member in the data: SK 0.228) |
| `owners_mpc_in_unit_interval` | the owners' marginal propensity to consume, solved as a calibration residual, lies outside [0, 1] |

## Headline

- **Scenario runs:** 3,057 across 27 countries. **3,057 (100%) pass the accounting gate; 1,469 (48%) also pass the plausibility laws.**
- **Monte-Carlo draws** (the F12 robustness bands' priors, seed 0): 4,860 of 10,800 used draws (45%) are plausible.

## By scenario family (all countries)

| Family | Runs | Accounting OK | Solvent | Plausible | net worth < 0 | money < 0 | I/Y > 0.40 | Gini < 0.15 | MPC out of [0,1] |
|---|---|---|---|---|---|---|---|---|---|
| triad | 81 | 81 | 79 (98%) | 72 (89%) | 0 | 2 | 3 | 0 | 6 |
| ubc_experiment | 108 | 108 | 105 (97%) | 72 (67%) | 0 | 3 | 4 | 27 | 8 |
| frontier | 351 | 351 | 344 (98%) | 192 (55%) | 0 | 7 | 13 | 134 | 26 |
| rich_frontier | 1971 | 1971 | 1918 (97%) | 786 (40%) | 2 | 51 | 385 | 756 | 146 |
| c1_ladder | 432 | 432 | 420 (97%) | 288 (67%) | 0 | 12 | 94 | 71 | 32 |
| pooling | 114 | 114 | 112 (98%) | 59 (52%) | 0 | 2 | 0 | 51 | 8 |
| mc_ubc (draws) | 5400 | 5400 | — | 3 (0%) | 0 | 136 | 200 | 5397 | 343 |
| mc_cash_ubi (draws) | 5400 | 5400 | — | 4857 (90%) | 0 | 22 | 200 | 35 | 343 |

*Solvent = no household class with negative net worth or negative money. Check columns count runs failing that law at least once (a run can fail several).*

### Insolvency by policy form (deterministic runs, all countries)

| Policy form | Runs | Owners' money < 0 | Workers' money < 0 | Net worth < 0 |
|---|---|---|---|---|
| none | 162 | 0 (0%) | 6 (4%) | 0 (0%) |
| cash | 926 | 0 (0%) | 2 (0%) | 0 (0%) |
| ubc | 1537 | 3 (0%) | 57 (4%) | 2 (0%) |

Monte Carlo: net worth < 0 in 0/5,400 UBC draws and 0/5,400 cash draws.

### Baselines (no AI shift, no policy)

24 of 27 baselines pass. Failing:

- **IE:** I/Y > 0.40 from 2019 (owners' MPC 0.0509, owners' money min 0.4084 x Y0, max I/Y 0.5357)
- **LU:** money < 0 from 2019, MPC out of [0,1] from 2019 (owners' MPC -0.1954, owners' money min 0.2058 x Y0, max I/Y 0.1805)
- **SI:** MPC out of [0,1] from 2019 (owners' MPC -0.0536, owners' money min 0.4767 x Y0, max I/Y 0.1976)

## Published numbers

| Surface | Runs behind it | Plausible | First failing laws (runs) |
|---|---|---|---|
| README headline + manifesto §III (DE: cash UBI vs UBC, wealth + growth) | 2 | 1/2 | Gini < 0.15 (1) |
| README frontier chart (DE/FR/SK, frontier points) | 27 | 20/27 | Gini < 0.15 (7) |
| Manifesto + dashboard frontier (DE, all 13 points) | 13 | 8/13 | Gini < 0.15 (5) |
| Manifesto C1 ladder (DE, endogenous investment, cash vs UBC) | 8 | 4/8 | Gini < 0.15 (3), I/Y > 0.40 (3) |
| LinkedIn posts (DE/FR/SK cash vs UBC) | 6 | 3/6 | Gini < 0.15 (3) |
| Dashboard (all countries: triad + UBC experiment + frontier) | 540 | 336/540 | Gini < 0.15 (161), MPC out of [0,1] (40), I/Y > 0.40 (20), money < 0 (12) |
| F23 rich frontier (DE, all regimes) | 73 | 33/73 | Gini < 0.15 (28), I/Y > 0.40 (12) |
| Pooled dividend, EU bloc (manifesto/dashboard), cash_ubi (26/26 countries viable) | 52 | 48/52 | MPC out of [0,1] (4) |
| Pooled dividend, EU bloc (manifesto/dashboard), ubc (26/26 countries viable) | 52 | 1/52 | Gini < 0.15 (51), MPC out of [0,1] (4), money < 0 (2) |
| Pooled dividend, DE+FR+SK (posts), cash_ubi (3/3 countries viable) | 6 | 6/6 | none |
| Pooled dividend, DE+FR (posts), cash_ubi (2/2 countries viable) | 4 | 4/4 | none |
| F12 robustness bands (DE Monte Carlo, ubc) | 200 draws | 0/200 | Gini < 0.15 (200) |
| F12 robustness bands (DE Monte Carlo, cash_ubi) | 200 draws | 200/200 | none |

The MCP tools and the agent crew use the orchestrator defaults, so they inherit the UBC-experiment and frontier rows above.

### The README headline runs (DE)

| Run | Plausible | First failing law (year) | Owners' net worth, min (x Y0) | Owners' money, min (x Y0) | Max I/Y | Min Gini |
|---|---|---|---|---|---|---|
| Baseline | yes | — | 3.4895 | 0.4187 | 0.2115 | 0.297 |
| AI shift, no policy | yes | — | 3.4895 | 0.4187 | 0.3343 | 0.297 |
| AI + Cash UBI | yes | — | 3.4217 | 0.3781 | 0.2324 | 0.2378 |
| AI + Universal Basic Capital | **no** | Gini < 0.15 (2033) | 2.1197 | 0.4187 | 0.2115 | 0.0559 |

## By country (plausible / runs)

| Country | Owners' MPC | Triad | UBC exp. | Frontier | Rich frontier | C1 ladder | MC UBC | MC cash | Worst owners' net worth (x Y0) |
|---|---|---|---|---|---|---|---|---|---|
| AT | 0.1857 | 3/3 | 3/4 | 8/13 | 34/73 | 12/16 | 0/200 | 200/200 | 0.6144 |
| BE | 0.2123 | 3/3 | 3/4 | 8/13 | 34/73 | 12/16 | 0/200 | 200/200 | 0.6417 |
| BG | 0.36 | 3/3 | 3/4 | 8/13 | 34/73 | 12/16 | 3/200 | 200/200 | 0.0498 |
| CY | 0.449 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.4448 |
| CZ | 0.2775 | 3/3 | 3/4 | 7/13 | 31/73 | 12/16 | 0/200 | 200/200 | 0.4567 |
| DE | 0.2073 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.6674 |
| DK | 0.2305 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.5029 |
| EE | 0.2675 | 3/3 | 3/4 | 9/13 | 36/73 | 12/16 | 0/200 | 200/200 | 0.4709 |
| EL | 0.5898 | 3/3 | 3/4 | 8/13 | 30/73 | 12/16 | 0/200 | 200/200 | 0.6091 |
| ES | 0.3362 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.5859 |
| FI | 0.3153 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.5254 |
| FR | 0.2552 | 3/3 | 3/4 | 8/13 | 34/73 | 12/16 | 0/200 | 200/200 | 0.4439 |
| HR | 0.3711 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.5175 |
| HU | 0.2985 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.2906 |
| IE | 0.0509 | 0/3 | 0/4 | 0/13 | 0/73 | 0/16 | 0/200 | 0/200 | 0.6016 |
| IT | 0.356 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.6949 |
| LT | 0.421 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.7708 |
| LU | -0.1954 | 0/3 | 0/4 | 0/13 | 0/73 | 0/16 | 0/200 | 0/200 | 1.0295 |
| LV | 0.3523 | 3/3 | 3/4 | 9/13 | 36/73 | 12/16 | 0/200 | 200/200 | 0.305 |
| MT | 0.1916 | 3/3 | 3/4 | 8/13 | 31/73 | 12/16 | 0/200 | 200/200 | 0.5792 |
| NL | 0.1196 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.6039 |
| PL | 0.4418 | 3/3 | 3/4 | 8/13 | 31/73 | 12/16 | 0/200 | 200/200 | 0.1841 |
| PT | 0.4126 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.6248 |
| RO | 0.5554 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.0451 |
| SE | 0.2187 | 3/3 | 3/4 | 8/13 | 33/73 | 12/16 | 0/200 | 200/200 | 0.4452 |
| SI | -0.0536 | 0/3 | 0/4 | 0/13 | 0/73 | 0/16 | 0/200 | 57/200 | 0.7409 |
| SK | 0.457 | 3/3 | 3/4 | 7/13 | 26/73 | 12/16 | 0/200 | 200/200 | -0.0203 |

## Reading

- **Accounting:** 3,057 of 3,057 runs balance their books.
- **Insolvency (the step-B target):** 2 runs and 0 Monte-Carlo draws: SK UBC t=55% reinv=100% [endo]; SK UBC t=60% reinv=100% [endo]. In those runs the fund owns all the capital and reinvests everything at home, the current-account deficit widens, and the model still assigns the capital-less owners a share of the country's foreign debt (external positions are allocated by money shares). That rule is replaced in step D. The gate now refuses such runs (net worth is a blocking law).
- **Negative money:** owners in 3 runs (LU), workers in 77 runs (LU); Monte-Carlo draws: IE 63, LU 95. No owner overdraft remains outside countries whose calibration is unusable. Workers' overdrafts arise there too, and in trade-linked runs from the external-position rule. This law stays advisory until step D.
- **Investment above 40% of GDP:** 499 runs (449 of them UBC). Where the citizens' fund retains its profits it can only reinvest them in domestic fixed capital; a real fund would also buy financial and foreign assets. That outlet arrives with step D (the fund may buy foreign equity).
- **Gini below 0.15:** 1039 runs and 5432 draws, almost all UBC. This is the distribution layer (two-class lognormal), not financing; it is revisited with step E and re-checked in step F.
- **Calibration:** owners' MPC outside [0, 1] in LU, SI; those countries' results stay unusable under this closure.
