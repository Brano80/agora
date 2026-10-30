# Phase 7 — Credibility fixes (from the 2026-10-28 review)

**Status:** IN PROGRESS (0, A, B, C done 2026-10-29; D, E done 2026-10-30). **Rule:** no README claim, outreach, post or Zenodo
version goes out until step G is done. Step 0 is the only exception.

All findings below were reproduced on the shipped engine (fbbe103) on 2026-10-28.
**Every one of these runs passes the consistency gate.** The books balance; the economics
doesn't. That is the gap this phase closes.

---

## Verified findings

| # | Finding | Evidence | Severity |
|---|---|---|---|
| 1 | **Output is purely demand-led: no capacity limit, no price level.** Moving income to workers (MPC 0.95) from owners (MPC 0.21, solved as a calibration residual) raises GDP mechanically. | Switching cash UBI on adds **+10.6% GDP in year 0**. DE year 29: UBC τ=50% 4.16×Y0, cash τ=50% 2.90×, no policy 2.28×. Already flagged as crux **C4** and in SCOPE.md, but README/launch copy state "predistribution needn't cost growth" without the caveat. | High |
| 2 | **Investment has no financing constraint.** Capex is an exogenous path (AI boom +6%/yr for 30 years). Owners fund it whatever their income, by running unlimited negative money balances (an interest-free overdraft at the state, since i_rate=0 by default). | DE UBC τ=40% year 29: owners' money −4.2×Y0 and net worth (incl. foreign assets) **−0.84×Y0: insolvent** while owning 21% of K. Owners' money minimum: SK −140×, PL −49×, SE −13×, ES −7× Y0. The **cash arm** runs negative owner money too (DE from year 27) but its capital keeps it solvent. Across all published runs: owner money < 0 in 61% of cash and 50% of UBC runs; net worth < 0 in 31% of UBC runs and 0% of cash runs. Monte Carlo (F12 bands, DE): **42/200 UBC draws insolvent**; 69 UBC and 84 cash draws with negative owner money; all counted. In RO and LV owners' money goes negative even in the **baseline**. No-policy investment reaches 50% of GDP. The plausibility law never checked sector money or net worth. *(Corrected after the step-A audit: the first review measured capital + money without foreign assets, which overstated insolvency and wrongly included the cash arm.)* | **Critical** |
| 3 | **No foreign ownership of domestic capital or AI rent.** All capital, AI capital included, is owned by domestic owners or the fund. | The capital row of the balance sheet has only `hh_owners` + `sovereign_fund`. For Europe, most frontier-AI rent is US-owned, and domestic dilution cannot reach it. Peer result: Wossnig 2026 (arXiv 2606.20649) finds the durable surplus is a foreign-held AI rent (~13% of output) that only source-based levies reach. | High (this *is* the Europe question) |
| 4 | **UBC equity is transferred at book value while the profit rate climbs from 11% to 28%.** The yearly transfer is equal in book terms (cumulative: UBC 13.2×Y0, cash 11.7×Y0), but the fund acquires assets far below their earnings value, so equal τ ≠ equal value. End state: the fund owns 59–100% of all capital within 30 years (gradual socialisation), which the docs never say plainly. | `contrib = tau*FP` added to `E_sf` at capital book value; profit/K path 0.114 → 0.280 (DE UBC). | Medium-high |
| 5 | **The public claims contradict the project's own findings.** README: "UBC policies dominate both cash UBI and inaction." F23 shows that is conditional on fixed investment. The frontier is near-degenerate (UBC τ=50% best or tied on 4/5 objectives; "no single best" survives only via growth volatility). Implausible end states pass the gate: personal Gini 0.056 (the lowest EU member in the data is SK at 0.228). | README; MANIFESTO F23; `run_policy_search()` output. | Medium |
| 6 | **The backtest is weak evidence for the headline.** It drives investment and government with *actual* paths, so ~2.3% GDP error tests the consumption function and the accounting, not the mechanisms the headline rests on (investment response, fund behaviour, capacity). There is no naive benchmark. | `backtest.py` docstring + method. | Medium |

**Affected outputs:** README headline and frontier chart (DE/FR/SK); manifesto v1.1; the
public dashboard; the MCP tools and agent crew (all default to the fixed-investment
regime); the LinkedIn queue; the Zenodo record.

---

## Order of work (and why)
Gate first, so every broken result becomes visible. Then the investment closure (the
critical defect, and cheapest). Then the supply side, then foreign ownership, then a fair
comparison. Then re-validate, correct the record, and relaunch. Effort figures are rough
estimates for focused work.

### 0. Stopgap (today, ~30 min)
- Add a dated "Known issues — results under revision" note to README listing findings 1–3.
- Pause outreach and the LinkedIn queue.

### A. Make the failures visible (gate first, ~1 day)
- **A1.** Extend the economic-plausibility law in `consistency/checks.py`:
  - per-class household net worth ≥ 0;
  - investment/GDP ≤ 0.40;
  - personal Gini ≥ 0.15;
  - wealth-split shares within [0,1];
  - a calibrated owners' MPC outside [0,1] becomes a failure, not a note.
  - Ship behind an `audit` flag (report, don't raise) until B lands.
- **A2.** Tests that pin today's pathologies as *caught*: DE UBC τ=0.4 fixed-investment, SK UBC, one insolvent Monte-Carlo draw.
- **A3.** Audit sweep: 27 geos × {triad, UBC experiment, frontier, rich frontier, MC n=200}. Write `docs/AUDIT-2026-10.md` with pass/fail counts and which published numbers fail.
- **Done when:** the known cases fail the gate and the audit table is committed.
- **Status: DONE 2026-10-28.** Law 7 in `consistency/checks.py` (5 checks, advisory by default, `plausibility="enforce"` or env `AGORA_PLAUSIBILITY=enforce` to block); 16 tests in `tests/test_plausibility_v2.py`; `scripts/audit_plausibility.py` -> `docs/AUDIT-2026-10.md` + `docs/audit-2026-10.json`. Result: all 3,057 runs balance; 13% are plausible; 22/27 baselines pass (IE, LU, SI unusable under this closure; RO, LV owners go negative with no shock).

### B. Fix investment financing (~2–3 days)
- **B1.** Replace the exogenous capex path with a behavioural investment function (standard Kaleckian SFC: accumulation responds to the expected profit rate on *owned* capital, and to capacity utilisation once C lands). The AI boom becomes a decaying shift in expected AI returns, not +6%/yr for 30 years.
- **B2.** Give owners a budget constraint: capex financed from retained profits plus borrowing up to a cap (debt ≤ λ × owned capital) at a positive interest rate. **Decision:** a simple cap now (recommended), or activate the reserved banks/loans/deposits layer in the schema.
- **B3.** Default investment response > 0, sourced from the investment/cost-of-capital elasticity literature. Keep fixed investment only as a labelled sensitivity.
- **B4.** Under UBC the fund invests its retained share, and private owners invest according to the return on what they still own. Total I = private + fund.
- **B5.** Revisit the Monte-Carlo prior: drop `inv_elasticity = 0` or justify it.
- **Done when:** there are zero insolvent owners across the A3 sweep and all MC draws, year 0 still reproduces, and the gate is exact.
- **Status: DONE 2026-10-29** (two runs remain, assigned to step D; see residuals). Audit: `docs/AUDIT-2026-10-stepB.md`.

#### What was built
- **Two switchable investment closures** in `modules/sfc_core.py`. `behavioural` is the new default; `legacy` is the v1.1 engine, kept only to reproduce published numbers and for the backtests, which feed in actual investment. The step-A audit still reproduces byte-for-byte with `--closure legacy`.
- **Investment rule (B1, B3, B4).** Owners invest on the stake they own: desired gross investment = (1 − fund share) × last year's output × [base-year investment share + γ × (owners' net profit share − its base-year value)]. A cash levy and UBC dilution lower the net profit share in the same way. The AI boom now comes from the higher profit share, not a fixed +6%/yr path. The fund invests the part of its profits it retains.
- **Financing (B2).** Pecking order: saving first, liquid money down to a floor, then loans up to a cap on owned capital at the loan rate, and only then less investment (then fewer inventories). Debt above the cap is repaid as loans mature. Each regime is linear in output and solved exactly.
- **Lender:** the public sector as a stand-in (decided 2026-10-29; banks replace it before step F). `gov_debt` is reported net of these loans; `gov_money` is the gross figure.
- **UBC takes net equity.** The diluted capital comes with its share of the owners' loans, and the fund services that debt from its profits. The schema gains the `loans` instrument plus the `loans_chg`, `loan_interest`, `debt_assumption` and `tax_capital_base` flows.
- **Staged gate** (`consistency/checks.py`). The net-worth law now blocks; the others stay advisory until their step lands (`ENFORCED_LAWS`, `STAGING`). Legacy runs default to audit mode. The policy search records refused candidates instead of aborting.
- **Monte-Carlo prior (B5).** The exogenous capex growth and the dilution elasticity are gone. Added: profit response, debt cap, loan rate. `LEGACY_PRIORS` reproduces the v1.1 bands.

#### Parameters and sources
| Parameter | Default | MC range | Source |
|---|---|---|---|
| Profit-share effect on investment/GDP (γ) | DE 0.376, FR 0.088, IT 0.130, others 0.299 (EA-12) | 0.088–0.376 | Onaran & Galanis (2014), *Environment and Planning A* 46(10), Table 7, 1962–2007 |
| Cap on new borrowing / owned capital | 0.10 (≈30% of GDP) | 0–0.22 | Euro-area NFC debt 67.2% of GDP end-2024 (ECB); upper bound = the size of today's stock |
| Loan rate | 3.5% | 1.5–5.5% | ECB composite cost of borrowing, new loans to corporations, 3.57% (Dec 2025) |
| Debt repaid above the cap | 20%/yr | — | **Assumption** (5-year average maturity); not sourced |
| Liquidity floor | 50% of base-year owners' money/capital | — | Assumption |

#### Result (DE, 30 years, legacy → behavioural)
| | v1.1 engine | Step B engine |
|---|---|---|
| GDP, AI shift with no policy (× 2019) | 2.28 | 1.63 |
| GDP, cash UBI / UBC (× 2019) | 2.75 / 3.51 | 1.80 / 1.92 |
| Investment/GDP at the end: no policy / cash / UBC | 0.50 / 0.42 / 0.33 | 0.33 / 0.23 / 0.00 |
| UBC: fund's share of capital | 79% | 100% (with no reinvestment, nobody else invests) |
| Frontier (13-point search) | UBC 20–50% only | 9 points: no policy, cash UBI 10–60%, UBC 20–30% |
| C1, endogenous investment: UBC GDP / cash GDP | 0.805 | 1.065 |
| All 27 countries: runs passing every plausibility law | 13% | 48% |
| Runs with an insolvent household class | 479 | 2 |

#### Findings changed by step B (input to the step-F ledger)
The tests that encode these now run on the legacy closure, which proves v1.1 still reproduces. They make no claim about the new engine.
- **"Doing nothing is never on the frontier"** fails: no policy is now non-dominated (stability axis).
- **"The frontier is UBC-only" (F20, fixed regime)** fails: cash UBI is on the frontier at every τ.
- **C1 / F6 "endogenous investment chokes UBC"** reverses: UBC ends larger than cash (1.065). Without a supply side, zero investment costs no output; step C decides this.
- **F20 "a responsive government compresses the debt spread"** no longer holds under the default parameters.
- **UBC endowment grows monotonically** fails: with no investment the fund's capital depreciates.
- **Unchanged:** the accounting, year 0 everywhere, and the wealth result (UBC top-10% wealth share 0.10 vs cash 0.61).

#### Residuals and which step owns them
- **SK, UBC τ=55–60% with full fund reinvestment (2 runs).** Owners hold no capital, yet still carry a share of the country's foreign debt, because external positions are allocated by money shares. The staged gate refuses these runs. **Step D.**
- **Negative money** (advisory): LU (unusable calibration), IE Monte-Carlo draws, and trade-linked runs caused by the same external-position rule. **Step D.**
- **Investment above 40% of GDP** (499 runs, mostly UBC): a fund that retains profits can only reinvest at home. **Step D** (the fund may buy foreign assets). The same applies to the Norway-style payout option (`fund_payout`), which pushes investment to 59% of GDP.
- **Gini below 0.15** (mostly UBC): the distribution layer. **Step E.**
- **LU, SI** (owners' MPC < 0) and **IE** (investment above 40% of GDP in 2019): unusable under this closure. **Step F** calibration review.
- **Romania's owners save too little** to fund baseline investment and hit the borrowing cap. Real financing comes from FDI and EU funds. **Step D.**
- The backtests stay on the legacy closure (**step F1**). The Streamlit slider `inv_elasticity` has no effect under the behavioural closure (**step G**).

### C. Add a supply side and a price level (~3–5 days)
- **C1.** Capacity from the two capital stocks (traditional + AI) and labour; utilisation u = Y/Y*. **Decision:** Leontief capacity Y* = K/v (stays in the post-Keynesian SFC tradition, ~3 days; recommended now), or CES production fed by the Acemoglu–Restrepo task block already in `ai_shock.py` (more mainstream, ~1 week; a good later swappable module).
- **C2.** Markup pricing with demand-pull/conflict inflation when u is high. Report real and nominal values. Policies switch on at t=1, not t=0, so year 0 reproduces in every arm.
- **C3.** Re-answer crux C4: does redistribution raise *real* output once capacity binds? Record the answer as a finding either way.
- **Done when:** there is no instant GDP jump at policy switch-on, real GDP is bounded by capacity, and the triad and backtest still pass.
- **Status: DONE 2026-10-29, one criterion partly met** (the switch-on jump is now capped, not removed; see "Done-when check"). Audit: `docs/AUDIT-2026-10-stepC.md`.

#### What was built
- **Capacity (C1, Leontief as decided).** Full-capacity real output = baseline TFP level × AI productivity level × (traditional + AI capital) / v. v is set so that 2019 sits at the observed utilisation. Real output cannot exceed the historical maximum utilisation; demand beyond it is met by extra imports (`excess_imports`), and the gate stays exact.
- **Prices (C2).** The accounts are nominal, with a price level P (2019 = 1). Inflation = 2% + slope × last year's output gap (utilisation against its long-run normal).
  - Government spending and the investment share are real rules indexed to P.
  - Exports lose competitiveness when P outruns the world's 2% path.
  - Capital is a real stock valued at P. Money, loans and debt are nominal, so inflation erodes them.
  - New outputs: `gdp_real`, `price_level`, `inflation`, `capacity`, `utilisation`, `output_gap`, `excess_imports`. The policy search, Monte-Carlo bands, C1 ladder, MCP tools and agent crew now report real GDP.
- **Policies switch on in 2020** (`POLICY_START = 1`), so 2019 is identical in every arm.
- **Investment responds to the output gap** as well as to profitability, so capacity keeps up with demand. Baseline TFP is calibrated per country for balanced growth, within EU-KLEMS bounds.
- **AI productivity (included, as decided).** 0.3 pp/yr for 10 years, phased in with adoption: a level gain of (1.003)^10 ≈ +3.0% at full adoption. Monte-Carlo range 0–0.6 pp.
- **AI capital reclassified.** Only the profit-driven part of investment counts as AI capital. Before, all private investment under the AI shift counted, and AI capital's fast obsolescence drove the baseline into the ceiling.
- **Citizens' fund.** It invests by the owners' rule on its stake, up to what its payout policy retains. Like any owner, it first retains the depreciation allowance on its stake. So `ubc_reinvest` is the share of *net* profit retained, and a POMV draw cannot consume capital. This fixes two problems:
  - Before, `reinvest = 0` paid out gross profit, depreciation included, so the fund's capital wore out (DE real GDP 0.39× by 2049 with 8% inflation).
  - Before, `reinvest = 1` sank every retained euro into domestic capital, with investment up to 70% of GDP.
- **Utilisation data.** `data/connectors/capacity.py` and `scripts/build_capacity.py` read EC business-survey manufacturing capacity utilisation for all 27 members in one call: Eurostat `ei_bsin_q_r2`, indicator BS-ICU-PC, seasonally adjusted, via DBnomics. The Bundesbank mirror and the Eurostat API are fallbacks; the Bundesbank's annual values equal the Eurostat annual means for the 21 members both cover. The cache keeps the annual series to 2019, and the calibration is derived from it at load time:
  - **Normal** is the 2005–2019 mean, not the full history. In BG, LT and LV the 1990s transition years sit 10–25 pp below anything seen since. A full-history mean would read 2019 as a 20% boom and give those baselines ~3.5% inflation for 30 years.
  - **Max** is the historical maximum, and at least 2019 + 2 pp.
  - **Min** is the 2005–2019 trough (2009). It is used only as a plausibility range.
- **Monte-Carlo priors added:** AI productivity, Phillips slope, export elasticity, utilisation response.
- **Monetary policy is deferred to the banks step** (decided). Rates stay fixed; the audit flags it.

#### Parameters and sources
| Parameter | Default | MC range | Source |
|---|---|---|---|
| Inflation target | 2% | — | ECB price-stability target |
| Phillips slope (pp inflation per pp output gap) | 0.08 | 0.01–0.15 | ECB WP 3133 (Beschin, Paredes, Polichetti & Renault 2025): ~0.19 per pp of unemployment, × Okun ~0.4 (Ball, Leigh & Loungani 2017) |
| Export price elasticity | 0.75 | 0.3–1.0 | Christodoulopoulou & Tkačevs (2013), ECB/CompNet: ~0.8 goods, ~0.7 services |
| Investment/GDP response per pp of output gap | 0.25 | 0.1–0.35 | **Assumption.** Utilisation drives euro-area investment (Gallo & Barbieri Goes 2023, *Economia Politica* 40), but no coefficient is published. Set so that baselines stay inside the observed utilisation range; from ~0.5, FR, IT and ES run ±8 pp 15-year cycles the data rule out |
| AI productivity | 0.3 pp/yr for 10 years | 0–0.6 pp | OECD, Filippucci, Gal & Schief (2024): 0.25–0.6 pp/yr in the US, lower in Europe. Acemoglu (2024): ~0.07 |
| Normal / maximum utilisation | per country: 2005–2019 mean / historical maximum (DE 84.1% / 89.6%) | — | EC BCS manufacturing survey, Eurostat `ei_bsin_q_r2` BS-ICU-PC (SA), via DBnomics, retrieved 2026-10-29 |
| Baseline TFP growth | balanced growth, bounded 0.1–0.7%/yr | — | IMF WP/24/258 (EU-KLEMS) |

#### Result (DE, 30 years, real GDP × 2019)
| | v1.1 engine | Step B | Step C |
|---|---|---|---|
| AI shift, no policy | 2.28 | 1.63 | 1.64 |
| Cash UBI / UBC (pinned experiment: the fund pays out all its profit) | 2.75 / 3.51 | 1.80 / 1.92 | 1.63 / 1.14 |
| Cash UBI at switch-on vs no policy | +10.6% (2019, unbounded) | — | +7.5% (2020, at the capacity ceiling) |
| Investment/GDP at the end: no policy / cash / UBC | 0.50 / 0.42 / 0.33 | 0.33 / 0.23 / 0.00 | 0.31 / 0.22 / 0.14 |
| Peak inflation: no policy / cash / UBC | — | — | 2.0% / 2.7% / 3.8% |
| C1, endogenous investment: UBC GDP / cash GDP, fund retains none | 0.805 | 1.065 | 0.70 |
| C1, fund retains 60% | — | — | 1.26 |
| Frontier (13-point search) | UBC 20–50% only | 9 points | 11 points: cash 10, 20, 40–60%; UBC 10–60% |
| All 27 countries: runs passing every plausibility law | 13% | 48% | 48% |
| Runs with an insolvent household class | 479 | 2 | 0 |
| Runs with investment above 40% of GDP | 1,914 | 499 | 109 (all IE) |

#### C3: does redistribution raise *real* output once capacity binds? (crux C4)
**Answer:**
- The switch-on boost is capped by spare capacity.
- Over 30 years, cash UBI is roughly neutral to negative for real output.
- For UBC, the answer turns on whether the fund reinvests.

Figures: 24 usable countries (IE, LU and SI excluded), τ = 40%, AI shift, real GDP in 2049 against no policy.

- **Cash UBI:** median −2%.
  - Range: EL −20% to FR +18%. Clearly higher only in the wage-led FR (+18%), IT (+9%) and SE (+2%).
  - In the switch-on year: median +4.9%, capped by each country's spare capacity. Peak inflation: median 2.8%, max 3.8%.
  - Mechanism: the levy cuts owners' retained profit and hence investment. Where investment responds strongly to profits, that costs more capacity than the demand boost adds.
- **UBC, the fund pays out all its net profit** (the pinned experiment): median −28%.
  - Range −38% to −10%; higher in 0 of 24.
  - The fund owns all capital by about 2034 and only replaces it. Its dividends push demand into the ceiling in 70% of years.
- **UBC, the fund retains 60% and invests by the owners' rule:** median +10%.
  - Range: RO −5% to FR +37%; higher in 23 of 24.
  - A Norway/Alaska POMV draw (3–5%) gives the same path here, because the investment rule binds before the budget does.
- **Recorded finding:** "redistribution raises GDP" was a property of the demand-only closure. With capacity, the cash result is roughly neutral and the UBC result depends on the fund's payout rule.
- **Caveats, carried into step F:**
  - Rates do not yet respond (banks step).
  - The profit response γ is estimated on 1962–2007 data and applied here to a labour share falling to 30%, about 30 pp outside that sample.
  - At τ = 40% the fund owns all capital within ~15 years (finding 4).
  - The workers/owners consumption gap (MPC 0.95 vs a calibrated residual 0.21) still drives the boost.

#### Done-when check
- **Real GDP bounded by capacity:** met (tested in `tests/test_supply_side.py`).
- **Triad and backtest pass:** met. The backtests stay on the legacy closure until F1.
- **No instant GDP jump at switch-on: partly met.** 2019 is identical in every arm, and the jump is capped by spare capacity (DE cash: +7.5% in 2020, at the ceiling, against +10.6% unbounded before). What still drives it is the MPC gap with no monetary response. Owners: the banks step (policy rate) and step F (owners' MPC calibration).

#### Findings changed by step C (input to the step-F ledger)
- **Crux C4:** answered above.
- **C1 / F6:** step B's open question is decided by the fund's payout rule.
  - A fund that pays out everything shrinks the economy (UBC/cash 0.70).
  - A fund that retains 60% grows it (1.26).
  - Step E should pin a real payout rule (Norway 3% / Alaska 5% POMV).
- **UBC endowment:** a fund that pays out everything now holds its capital roughly constant (it replaces depreciation) instead of letting it wear out.
- **Frontier:** UBC 10% gives the highest GDP. UBC at τ ≥ 20% shows Gini 0.066 and zero poverty, which is implausible (distribution layer, step E).
- **Distribution anchoring:** every published policy arm anchored its distribution on a 2019 with the policy already on.
  - With the correct anchor, a double count in the distribution layer shows: the levy lowers the net capital share behind *market* inequality and is also counted as a transfer.
  - Effect: cash-UBI Monte-Carlo draws below Gini 0.15 rise from 35 to 1,094.
  - Step E.
- **Debt:** with no fiscal reaction, the AI shift takes DE debt to 151% of GDP by 2049 (step B: 183%; inflation now erodes nominal debt). The fiscal block stays off by default until E3.

#### Residuals and which step owns them
- **Utilisation below the country's 2009 trough** in 497 runs. 381 are UBC with retained profits: the fund keeps building as the profit share climbs, because the profit response is extrapolated far outside its sample. 56 have no policy: demand falls short under the AI shift. **Step F** (profit-response sensitivity) and **step D** (the fund can invest abroad).
- **EL baseline** sits at the ceiling in 90% of years (uniform K/Y = 3 calibration). **Step F.**
- **IE:** deflation and utilisation below 0.70 (unusable calibration). **Step F.**
- **No monetary policy.** **Banks step.**
- **The fund cannot hold financial or foreign assets.** **Step D.**
- **Multi-region comparisons are still nominal.** **Step D.**
- **Gini / distribution double count.** **Step E.**
- **Profit response applied far outside its sample.** MC covers 0.088–0.376. **Step F** sensitivity.
- **The Streamlit `inv_elasticity` slider has no effect.** **Step G.**


### D. Foreign ownership of capital and AI rent (~2–3 days)
- **D1.** Split capital ownership: domestic owners / rest of world / fund. Calibrate the foreign-owned share from Eurostat IIP/FDI positions and primary-income outflows (add these to DATA-SOURCES.md, plus a connector).
- **D2.** New lever: the share of AI capital/IP owned abroad (a scenario assumption with a sourced range). Profits on foreign-owned capital leave as primary income through the current account, and the gate covers the new flow.
- **D3.** Policies that reach foreign rent: a source-based levy or withholding on AI revenue (reuse the F22 study inputs). The fund may *buy* foreign equity with its own resources but cannot dilute what is foreign-owned.
- **D4.** Sanity check against Wossnig (2026): reproduce the qualitative result that flow taxes on domestic capital miss the foreign AI rent.
- **Done when:** a scenario with 80% foreign-owned AI capital runs gated, and the dashboard shows how much of the AI dividend each policy can still reach.
- **Status: DONE 2026-10-30, one criterion moved to step G** (the dashboard shows the reach metric once it is regenerated; the metric exists in the engine and the MCP tools now). Audit: `docs/AUDIT-2026-10-stepD.md`.

#### What was built
- **Foreign owners of domestic capital (D1).** The rest of the world owns a share ψ of the capital stock. ψ = equity income paid abroad (dividends + reinvested FDI earnings, a net-of-depreciation concept) / net profits, 2015–19 (Eurostat `nasa_10_nf_tr` D42+D43 vs the rest of the world).
  - Foreign owners invest on their stake by the owners' rule (FDI), financed by their parents, so it is never cut for lack of cash.
  - They pay the baseline capital tax, and a cash levy, at source.
  - UBC cannot dilute them: the fund's stake is capped at the domestically owned capital.
- **Owners' equity abroad.** Sized from what owners actually receive from abroad (outward D42+D43 / the world return). It earns the world return; owners reinvest abroad at world nominal growth and bring the rest home. An owner who runs out of cash stops reinvesting abroad and, if needed, sells, rather than run an overdraft.
- **The 2019 net international investment position** (Eurostat `tipsii10`). The part that is not equity is held by **the public sector as a stand-in** until the banks step, as with loans in step B. It earns the government-money rate (0 by default). Fiscal debt is reported net of what the stand-in bought abroad since 2019, so a current-account surplus is not counted as government debt.
- **No household holds the external position any more.** The v1.1 rule split the current account between workers and owners by their money. It caused the step-B insolvency and the workers' overdrafts, and it is gone.
- **AI rent abroad (D2).** The AI rent is the income the AI shift moves from labour to capital, (ls₂₀₁₉ − ls)·Y. A share α of it is paid abroad every year as licence and cloud fees, booked as primary income: GDP is unchanged and national income (GNI) is lower. Both are reported.
- **Source levy (D3).** A new lever, `source_levy`, is withheld on the fees.
  - A share ρ of it is passed on to domestic buyers. The provider receives F·(1 − (1−ρ)s); domestic firms pay F·(1 + ρs).
  - The revenue funds the cash UBI, seeds the citizens' fund, or else goes to general revenue.
- **The fund abroad (D3).** Whatever the fund retains but does not need at home buys foreign equity at the world return, as Norway's fund does. A POMV draw is on its total value.
- **Reach metric (D4).** `ai_rent_reached_share` is the public's claim on the AI rent: levy revenue plus the cash levy rate, or the fund's stake, times the rent kept at home. `ai_rent_foreign_reached_share` is the bite on the foreign part.
- **Balance of payments.** The current account includes net primary income, booked net of depreciation on foreign-owned capital, as in the statistics. The current account plus net FDI equals the change in the external position held at home; this is tested every period. Year 0 starts exactly at the observed NIIP.
- **Year 0 still reproduces.** Owners now receive only their own share of profits plus their income from abroad. Their consumption residual (MPC) is rescaled once so that 2019 consumption and GDP are unchanged. The new values stay within [0.14, 0.62] for the usable members.
- **Conduits.** NL, IE, LU, MT and CY show equity income above 15% of GDP in both directions; that is money passing through shell companies. They get the median of the other members, flagged. Their NIIP is kept.
- **Also changed.**
  - The policy search's growth objective is now real national income (GNI), not GDP.
  - Multi-region comparisons are in real terms. In the trade linker, external demand is nominal and responds to each country's prices, as in the core.
  - The Monte Carlo draws α and ρ.
  - `scripts/build_external.py` rebuilds the cache in three DBnomics calls.

#### Parameters and sources
| Parameter | Default | MC range | Source |
|---|---|---|---|
| Foreign owners' stake ψ | per country, e.g. DE 9%, FR 15%, IT 6%, ES 12%, PL 15%, RO 10%, SK 17%, CZ 36%, HU 37%, SE 34%, BE 49% | — | Eurostat `nasa_10_nf_tr` D42+D43 (S2, RECV) / net profits, 2015–19, via DBnomics (retrieved 2026-10-30) |
| Owners' equity abroad | outward D42+D43 / world return (DE 53% of GDP) | — | Eurostat `nasa_10_nf_tr` (S2, PAID) |
| Initial NIIP | per country (DE +59%, ES −72%, PL −49%, EL −157% of GDP) | — | Eurostat `tipsii10`, 2019 |
| World return on equity | 6.6% nominal | — | Norway GPFG, annualised 6.64% since 1998 (net real 4.34% + 2.13% inflation), NBIM Annual Report 2025 |
| AI rent earned abroad α | 0.70 | 0.5–0.9 | US providers ~70% of the European cloud market, European ~15% (Synergy Research, 2025) |
| Source-levy pass-through ρ | 0.9 | 0.5–1.0 | Amazon raised its fees by roughly the full DST (Langenmayr & Muddasani 2026, CESifo WP 12713) |
| Conduit threshold | inward equity income > 15% of GDP | — | Design (separates NL, IE, LU, MT, CY from all others) |

#### Result
| DE, 30 years | v1.1 | Step B | Step C | Step D |
|---|---|---|---|---|
| AI shift, no policy: real GDP / real GNI (× 2019) | 2.28 | 1.63 | 1.64 | 1.25 / 0.96 |
| Cash UBI / UBC (pinned experiment, fund pays out all), real GDP | 2.75 / 3.51 | 1.80 / 1.92 | 1.63 / 1.14 | 1.18 / 1.14 |
| … real GNI | — | — | — | 0.91 / 0.82 |
| C1, endogenous: UBC / cash, fund retains none / 60% | 0.805 / — | 1.065 / — | 0.70 / 1.26 | 0.96 / 1.01 |
| Frontier (13 points) | UBC 20–50% only | 9 points | 11 points | 8 points: no policy, cash 10/30/40/60%, UBC 10–30% |
| All 27 countries: runs passing every plausibility law | 13% | 48% | 48% | 69% |
| Runs with an insolvent household / with negative household money | 479 / over half of policy runs | 2 / ~80 (LU) | 0 / 113 (LU) | 0 / 0 |

**Across 24 countries** (IE, LU and SI excluded; τ = 40%; AI shift; 2049):
- With no policy, AI fees abroad reach a median 22% of GDP. Real GDP rises to 1.27× (the baseline is 1.46×). Real national income stays flat (0.98×, range 0.80–1.26) and real consumption falls to 0.89×.
- **Cash UBI** against no policy:
  - National income: median −3%, higher in 8 of 24.
  - Consumption: +17%, higher in 21 of 24.
- **UBC, the fund pays out all its net profit:** national income −14% (higher in 0 of 24), consumption −5%.
- **UBC, the fund keeps 60%:** national income +8% (higher in 24 of 24). Consumption is −15%, because the fund saves abroad.
- **A 10% source levy** adds 1–2 pp of national income in either form.
- **The public's claim on the AI rent** (median): cash 12%; UBC 22% if it pays out everything, 24% if it keeps 60%; with the levy, 16% and 26%. Of the part earned abroad, the cash levy and dilution reach **0%**. A 10% levy at 90% pass-through reaches **1%**; it would reach 10% with no pass-through.

#### D4: check against Wossnig (2026)
**Qualitatively reproduced.** Taxes on domestic capital and dilution do not reach the foreign-held AI rent; only a source-based levy does (`tests/test_external.py::test_which_policies_reach_the_ai_rent`).

**One difference.** With the observed pass-through, the levy mostly becomes a tax on European AI users rather than on the foreign rent. Wossnig assumes the levy reaches the rent. His steady-state foreign rent is ~13% of output; ours reaches ~22% of GDP because AGORA's AI shift is more extreme (the labour share falls to 30%). That is within his rising-rent range (up to about a quarter of output).

#### Findings changed by step D (input to the step-F ledger)
- **The headline welfare measure changes.** With 70% of the AI rent abroad, GDP overstates residents' income by about a quarter by 2049. Compare policies on national income and consumption, not GDP; the policy search now does.
- **"UBC vs cash" becomes a choice between now and later.**
  - Cash UBI raises consumption almost everywhere and leaves national income roughly unchanged.
  - A fund that retains profits raises national income and citizens' wealth everywhere, but lowers consumption for 30 years, because it saves abroad.
  - A fund that pays out everything is worse than doing nothing on national income.
  - Step E puts this on the frontier explicitly.
- **C3 is revised.** The step-C result "UBC retaining 60% +10% GDP" does not survive. In GDP it is now −6% against no policy; in GNI it is +8%. The domestic-investment part is unchanged; the difference is that what the fund cannot use at home now goes abroad instead of being paid out.
- **Romania's baseline** is now capacity-constrained from about 2030. Under the v1.1 money-share rule, the owners' share of the current-account deficit had acted as a hidden foreign credit line; without it, the borrowing cap binds. Real investment financing (FDI beyond the owners' rule, EU funds, bank credit) is **step F**.
- **Debt.** With no fiscal reaction, the AI shift takes DE debt to ~170% of GDP by 2049 in every policy arm. Labour taxes collapse, and the AI fees deduct from the capital tax base. **E3**.

#### Residuals and which step owns them
- **Baseline current accounts drift.** Exports follow world demand while imports follow domestic output, so surplus countries keep accumulating: baseline NIIP median −23% → +12% of GDP, DE +66% → +145%. There is no exchange-rate or risk-premium feedback. **Step F.**
- **Large UBC surpluses.** A fund that retains profits it cannot invest at home runs current-account surpluses above 10% of GDP in 754 runs. That is Norway-like, but extreme for weak economies such as EL (+24% of GDP). **Step E** (payout rules) and **step F**.
- **BE** has a 49% foreign stake: it is a semi-conduit (treasury centres) below the 15% threshold. **Step F.**
- **Romania** investment financing. **Step F.**
- **The fund's foreign equity is held at book value**, with no revaluation.
- **The external position earns the government-money rate**, which is 0 by default. **Banks step.**
- **The source levy is not in the audit families or the frontier yet.** **Step E** (the proposal library).
- **The dashboard reach panel.** **Step G.**


### E. Fair comparison and real proposals (~2 days)
- **E1.** Value transferred equity at market value (PV of expected profits / Tobin's q), not book value. Compare policies at equal present value of the burden on owners, and also show the equal-government-cost view.
- **E2.** Replace the perpetual 40%/yr dilution with a library of real 2026 proposals, each with sourced parameters:
  - a one-time stock levy (Sanders: 50% on AI firms);
  - a voluntary corporate pledge (Anthropic Public Benefit Fund: 5%, plus 2% per 50% valuation rise);
  - a debt-financed POMV fund (Norway 3% / Alaska 5%, the Berggruen loan model; `fund_payout` already exists);
  - child accounts (DE Frühstart-Rente €10/month; US Trump Accounts $1,000);
  - the source-based AI levy from D3;
  - cash UBI on a broad tax base.
- **E3.** Turn the Phase-6 fiscal block ON by default (broad base + fiscal reaction), so debt comparisons mean something.
- **E4.** Frontier: filtered for plausibility, with the investment regime shown explicitly. Flag any point that wins on ≥4/5 objectives, since that signals a missing cost.
- **Done when:** the frontier shows genuine trade-offs and every lever is sourced.
- **Status: DONE 2026-10-30, two items narrowed** (E1's equal-present-value and equal-cost views are replaced by the library, where each proposal runs at its announced size; and the investment regime is shown on the rich frontier only). Audit: `docs/AUDIT-2026-10-stepE.md`.
- **Decided 2026-10-30:** debt target = each country's 2019 ratio; keep the 40% experiment as a priced benchmark that pays out 3% a year; include the Anthropic-style pledge as a labelled best case; add a sixth objective (living standards); order E3, E1, E2 + E4.

#### What was built
- **A realistic government (E3).** It is on by default in the behavioural closure; the legacy closure is unchanged.
  - Each country borrows at its own implicit interest rate: interest paid / previous year's debt, 2015–19.
  - The base-year tax rate is set so the primary balance holds the 2019 debt ratio on the trend path: pb* = (i − g)·debt, with g = 1.5% real world growth at 2% inflation. Using the observed 2019 balance instead would have DE paying off its whole debt.
  - **Fiscal reaction (Bohn rule):** every year the tax rate on all taxed income moves by 0.034 pp per pp of debt above or below the 2019 ratio.
  - **Broad base:** 30% of base-year tax is raised on capital income, and profits are taxed at source. That includes the citizens' fund's share and the AI-stake income, so a fund no longer escapes tax.
  - **Distribution fix:** market inequality is driven by households' pre-tax capital income, so a capital levy is counted once, as a transfer (step C's double count).
- **Fair prices (E1).** Shares are valued at market prices, through Tobin's q = this year's net profit rate / 2019's (floored at 0.2).
  - The UBC claim buys shares at market value, not book value, and the fund's draw is on its market value.
  - The pinned 40% UBC arm now pays out 3% of the fund a year (Norway's rule) instead of all its profit. The C1 ladder keeps the old reinvestment rule.
  - The Monte-Carlo UBC draws use the same 3% rule.
  - Reported: `swf_market_value`, `equity_q`.
- **The proposal library (E2, `proposals.py`).** Six real or announced proposals, each run gated through the whole chain against no policy and the two 40% benchmarks:
  - **One-time stock levy (Sanders):** the fund takes 50% of the domestic AI firms in 2020 and pays citizens 5% of the stake's value a year. The rest of the stake's net income goes to the budget.
  - **Voluntary pledges, best case (Anthropic-style):** 5% of the AI rent paid abroad comes back as distributions to European households, plus 2 pp for each 50% rise in the rent after 2026. This assumes every foreign provider pledges and pays out in proportion to its European fees.
  - **Debt-financed fund (UK Citizens' Wealth Fund proposal, Norway's rule):** the state borrows 3% of GDP a year for 10 years to seed a fund. The fund buys world equity and pays out 3% of its value a year.
  - **Child accounts (Frühstart-Rente):** €10 a month per child aged 6–17 from 2027, fixed in euros, invested, with no payouts before retirement.
  - **Source levy:** 3% on the AI fees paid abroad.
  - **Cash UBI on a broad tax base:** a flat tax on all income, paid back as an equal UBI. Its rate raises what the 40% capital levy raises in 2019.
  - **Benchmarks:** the stylised 40% capital levy paid as cash UBI, and the 40% claim in shares, paying 3%.
  - Each enters as a lever on the scenario: `fund_seed`, `fund_seed_eur`, `ai_equity_stake`, `ai_stake_payout`, `pledge_share` and `broad_tax`, all behavioural-only, from 2020.
  - `run_library()` reports national income, consumption, inequality, poverty, wealth, debt and the AI rent reached for each.
- **The frontier (E4).**
  - A sixth objective, `living`: average real consumption per person 2020–49.
  - Points that fail a plausibility law are kept off the frontier.
  - The library's proposals are frontier points.
  - `near_dominant` flags a point that is best on all but one objective, which would signal a missing cost.
  - The MCP `policy_frontier` tool reports `n_implausible` and the flags.
- **Audit.** A new `proposals` family, and the UBC Monte Carlo at the 3% rule. The legacy audit (`docs/AUDIT-2026-10.md`) still reproduces byte for byte.

#### Parameters and sources
| Parameter | Default | MC range | Source |
|---|---|---|---|
| Interest rate on public debt | per country, 2015–19 implicit (DE 1.6%, FR 1.8%, IT 2.8%, EU median 2.5%) | — | Eurostat `gov_10dd_edpt1` D41PAY / GD(t−1), via DBnomics (retrieved 2026-10-30) |
| Debt target | each country's 2019 ratio | — | Eurostat `gov_10dd_edpt1` GD, 2019 |
| Fiscal reaction (Bohn) | 0.034 | 0.03–0.05 | Checherita-Westphal & Žďárek 2017, ECB WP 2036 (euro area 1970–2013) |
| Capital share of tax revenue | 0.30 | — | DG TAXUD tax revenue release, 31 March 2026: capital 21.6 / (labour 51.5 + capital 21.6), EU-27 2024 |
| Fund payout (benchmark, debt fund) | 3% of market value a year | — | Norway's fiscal rule (3% expected real return) |
| Stock levy | 50% of domestic AI firms, 5% dividend | — | AI Sovereign Wealth Fund Act, Sen. Sanders, June 2026 (AP, 17 Jun 2026) |
| Pledge | 5% + 2% per 50% rise | — | Anthropic Public Benefit Fund, 19 Oct 2026 (Al Jazeera); every provider pledging alike is an assumption |
| Debt fund | 3% of GDP a year, 10 years | — | UK Citizens' Wealth Fund proposal (Lansley, McCann & Schifferes 2018); the size is an assumption |
| Child accounts | €10/month per child 6–17 (11% of population), from 2027 | — | Frühstart-Rente, Bundestag 16 Oct 2026 (Deutsche Rentenversicherung); Eurostat population structure |
| Source levy | 3% | — | EU digital services taxes (FR, IT, ES 3%; AT 5%) |

#### Result
| DE, 30 years | Step D | Step E |
|---|---|---|
| AI shift, no policy: real GDP / real GNI (× 2019) | 1.25 / 0.96 | 1.18 / 0.94 |
| … real consumption (× 2019) | — | 0.72 |
| … public debt 2049 (% of GDP, 2019: 60) | ~170 | 128 |
| Cash UBI / UBC (pinned experiment), real GNI | 0.91 / 0.82 (fund pays out all) | 0.87 / 0.87 (fund pays 3%) |
| Tobin's q in 2049, UBC arm | book value (1) | 2.05 |
| Frontier | 8 points | 14 points: cash 10–60%, UBC 10–40%, stock levy, pledge, debt fund, broad-base UBI; none near-dominant |
| All 27 countries: runs passing every plausibility law | 69% | 80% |
| Runs with Gini below 0.15 | 720 | 233 (217 UBC) |

**DE proposals against no policy (AI shift, 2049):**

| Proposal | Real GNI | Consumption per head, 2020–49 average | Gini | Debt (% of GDP) | AI rent reached (of the part abroad) |
|---|---|---|---|---|---|
| No policy | — | — | 0.331 | 128 | 0% |
| Stock levy (Sanders) | +0.2% | +3.0% | 0.311 | 116 | 15% (0%) |
| Pledge, best case | +3.0% | +3.7% | 0.315 | 125 | 9% (13%) |
| Debt-financed fund | +3.8% | +1.4% | 0.325 | 141 | 0% |
| Child accounts | ≈0 | ≈0 | 0.331 | 129 | 0% |
| Source levy 3% | ≈0 | −0.2% | 0.331 | 121 | 2% (0.3%) |
| Broad-base cash UBI | −1.4% | +6.5% | 0.279 | 128 | 4% |
| Benchmark: 40% levy, cash UBI | −7.1% | +27.2% | 0.239 | 129 | 12% |
| Benchmark: 40% claim in shares, 3% payout | −7.6% | +11.4% | 0.183 | 120 | 25% |

**Across the 23 countries with a usable calibration** (median against no policy, 2049): see the proposals table in `docs/AUDIT-2026-10-stepE.md`.
- With no policy, debt goes from 60% to 128% of GDP. It passes 150% in 9 countries: BE, CY, EL, ES, FI, FR, HR, IT, PT.
- **Stock levy:** GNI +0.5%, consumption +1.9%, debt −11 pp. It reaches 15% of the AI rent but none of the part paid abroad.
- **Pledge (best case):** GNI +2.5%, consumption +3.2%. It is the only proposal that reaches the foreign rent (13%), and only if every provider pledges.
- **Debt fund:** GNI +3.4%, the largest gain, because the fund earns the world return. Consumption +1.1%, debt +14 pp.
- **Child accounts and the 3% source levy** are too small to move the aggregates.
- **Broad-base cash UBI:** consumption +6.6%, GNI −0.8%.
- **40% levy as cash:** consumption +22%, GNI −5%.
- **40% claim in shares:** GNI +0.9%, consumption −1.2%, plausible in 18 of 23 countries.

#### Findings changed by step E (input to the step-F ledger)
- **The fiscal comparison now means something.** Every policy arm faces the same government. The AI shift still drives debt up, because the profits that replace wages are partly paid abroad and outside the tax base, and the estimated fiscal reaction is slow.
- **The 40% experiment is a benchmark, not a proposal.** Priced at market value with a 3% payout, the UBC arm loses half as much national income against no policy as in step D (DE −7.6%, was −15%), about the same as cash (−7.1%). It is far larger than anything on the table: it takes 25% of the AI rent; the largest real proposal takes 15%.
- **Real proposals are an order of magnitude smaller.** None moves real national income by more than about 4%. None but the best-case pledge reaches the part of the rent paid abroad.
- **The trade-off is now / later and here / abroad.** Cash and the broad-base UBI raise consumption. Funds (the debt fund, the 40% claim) raise national income by saving abroad, and lower or barely raise consumption for decades.
- **No proposal dominates.** Four of the six are on the DE frontier (child accounts and the source levy are too small to matter), and no point is best on five of the six objectives.

#### Residuals and which step owns them
- **Owners' consumption propensity (the largest).** It is solved as the base-year residual. Taxing capital at its observed share moves base-year tax off wages, and workers, with a propensity of 0.95, then account for almost all consumption. The owners' residual falls (DE 0.21 → 0.04) and turns negative in IE and NL, which join LU and SI as unusable.
  - The results are sensitive to it. With no capital tax (owners' propensity 0.19), DE's UBC benchmark changes from GNI −7.6% / consumption +11% to −1.0% / +1.7%; cash UBI's consumption gain changes from +27% to +22%.
  - **Step F** (calibration review): replace the residual with observed saving rates by income group (Eurostat ICW) and treat corporate retained earnings as firms' saving.
- **Equal-present-value and equal-cost comparisons** (the original E1 wording) are not built. Each proposal runs at its own announced size. **Step F**, if the ledger needs it.
- **Interest rates are fixed** at each country's 2015–19 rate, with no risk premium as debt passes 150%. **Banks step.**
- **No behavioural response to the stock levy:** no relocation, valuation drop or compensation. **Step F** (sensitivity).
- **The debt fund's spread:** it earns 6.6% and borrows at 1.6–2.8%. **Banks step** (the rates) and **step F**.
- **Large UBC current-account surpluses** are unchanged (749 runs beyond ±10% of GDP). The 3% payout keeps most profit in the fund. **Step F.**
- **The investment regime is shown only on the rich frontier**, where both regimes run. The standard frontier runs the behavioural closure only.

### Banks (between E and F, ~2–3 days; added 2026-10-29)
- Replace the public-sector stand-in lender with a banking sector, activating the reserved `banks` sector and the `deposits` instrument. Loans equal deposits, households hold deposits next to (or instead of) government money, and loan interest goes to banks and depositors, not the state.
- Re-check the fiscal accounts once the government no longer carries the loans, and re-run the step-B tests.
- **Done when:** loans have a private counterpart, the gate is exact, and the step-B solvency results hold.

### F. Re-validate (~2 days)
- **F1.** Backtest with investment and consumption endogenous, driving only government spending and world demand. Report GDP, I, C and debt errors against a naive trend/random-walk benchmark; the model must beat it.
- **F2.** Re-run the Monte Carlo and sensitivity analysis, and test whether the F12 band separation survives.
- **F3.** Findings ledger: re-run F5–F23 and mark each one survives / changed / retracted in MANIFESTO.md.
- **Done when:** the validation report and the ledger are committed.

### G. Correct the public record (~1 day)
- **G1.** Rewrite the README headline to what survives, with its conditions stated.
- **G2.** Regenerate the manifesto (`build_manifesto.py`), the dashboard (`build_dashboard.py`) and the post audit (`build_posts.py`).
- **G3.** Publish Zenodo v1.2 with a correction note (same process as v1.1), plus a GitHub release.
- **G4.** Update CLAUDE.md "Current status" (stale since Phase 3), ROADMAP and STATE.

### H. Housekeeping (~0.5 day, any time)
- **H1.** Scout: pause the 08:00 and 09:10 tasks until G, or fix them:
  - delete the hard-coded "Prioritise the next module (distribution / AI-shock)" proposal (`scout/checks.py:128`);
  - keep LIVE_FAIL findings out of the novelty fingerprint, or require two consecutive failures. Transient fetch failures are what keep re-triggering reports (e.g. 2026-10-21: 9 LIVE_FAILs).
- **H2.** MCP: migrate to the 2026-07-28 spec (the initialize handshake is removed and sampling is deprecated). Replace `agora_narrate`'s sampling with a direct API call or drop it, then re-run `verify_mcp.py`. Tool payloads must carry the new regime labels.
- **H3.** Repo hygiene: the stray `pytest-cache-files-*` dir, the untracked social PNGs, and the uncommitted `.gitignore` / `POST_NUMBERS.md` changes.

### I. Relaunch (after G)
- **I1.** Anthropic Economic Futures via Strategic Partnerships (Research Awards are still closed). Hook: model the Public Benefit Fund mechanism for Europe.
- **I2.** Send AGORA to Wossnig (UCL) for cross-review.
- **I3.** Work the P1 targets in the outreach tracker and restart the metrics log.

---

## Estimate
A–G: about 2.5–3.5 focused weeks. A+B alone (~4 days) remove the critical defect.

## Decisions for Brano
1. Supply side: Leontief capacity now (recommended), or CES now.
2. Credit: a borrowing cap (recommended), or the banks layer. **Decided 2026-10-29:** borrowing cap with a public-sector stand-in lender now; banks as their own step before F.
3. Step 0 stopgap README note today (recommended: yes).
