# Phase 7 — Credibility fixes (from the 2026-10-28 review)

**Status:** PLANNED (2026-10-28). **Rule:** no README claim, outreach, post or Zenodo
version goes out until step G is done. Step 0 is the only exception.

All findings below were reproduced on the shipped engine (fbbe103) on 2026-10-28.
**Every one of these runs passes the consistency gate.** The books balance; the economics
doesn't. That is the gap this phase closes.

---

## Verified findings

| # | Finding | Evidence | Severity |
|---|---|---|---|
| 1 | **Output is purely demand-led: no capacity limit, no price level.** Moving income to workers (MPC 0.95) from owners (MPC 0.21, solved as a calibration residual) raises GDP mechanically. | Switching cash UBI on adds **+10.6% GDP in year 0**. DE year 29: UBC τ=50% 4.16×Y0, cash τ=50% 2.90×, no policy 2.28×. Already flagged as crux **C4** and in SCOPE.md, but README/launch copy state "predistribution needn't cost growth" without the caveat. | High |
| 2 | **Investment has no financing constraint.** Capex is an exogenous path (AI boom +6%/yr for 30 years). Owners fund it whatever their income, by running unlimited negative money balances (an interest-free overdraft at the state, since i_rate=0 by default). | DE UBC τ=40% year 29: owners' money −4.2×Y0, owners' capital+money **−2.3×Y0 (insolvent)** while owning 21% of K. SK −140×, PL −49×, SE −13×, ES −7×. The **cash arm too** (DE negative from year 27). Monte Carlo (the F12 robustness bands): **58/200 UBC and 29/200 cash draws end with insolvent owners** and are counted. No-policy investment reaches 50% of GDP. The plausibility law never checks sector money or net worth. | **Critical** |
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

### B. Fix investment financing (~2–3 days)
- **B1.** Replace the exogenous capex path with a behavioural investment function (standard Kaleckian SFC: accumulation responds to the expected profit rate on *owned* capital, and to capacity utilisation once C lands). The AI boom becomes a decaying shift in expected AI returns, not +6%/yr for 30 years.
- **B2.** Give owners a budget constraint: capex financed from retained profits plus borrowing up to a cap (debt ≤ λ × owned capital) at a positive interest rate. **Decision:** a simple cap now (recommended), or activate the reserved banks/loans/deposits layer in the schema.
- **B3.** Default investment response > 0, sourced from the investment/cost-of-capital elasticity literature. Keep fixed investment only as a labelled sensitivity.
- **B4.** Under UBC the fund invests its retained share, and private owners invest according to the return on what they still own. Total I = private + fund.
- **B5.** Revisit the Monte-Carlo prior: drop `inv_elasticity = 0` or justify it.
- **Done when:** there are zero insolvent owners across the A3 sweep and all MC draws, year 0 still reproduces, and the gate is exact.

### C. Add a supply side and a price level (~3–5 days)
- **C1.** Capacity from the two capital stocks (traditional + AI) and labour; utilisation u = Y/Y*. **Decision:** Leontief capacity Y* = K/v (stays in the post-Keynesian SFC tradition, ~3 days; recommended now), or CES production fed by the Acemoglu–Restrepo task block already in `ai_shock.py` (more mainstream, ~1 week; a good later swappable module).
- **C2.** Markup pricing with demand-pull/conflict inflation when u is high. Report real and nominal values. Policies switch on at t=1, not t=0, so year 0 reproduces in every arm.
- **C3.** Re-answer crux C4: does redistribution raise *real* output once capacity binds? Record the answer as a finding either way.
- **Done when:** there is no instant GDP jump at policy switch-on, real GDP is bounded by capacity, and the triad and backtest still pass.

### D. Foreign ownership of capital and AI rent (~2–3 days)
- **D1.** Split capital ownership: domestic owners / rest of world / fund. Calibrate the foreign-owned share from Eurostat IIP/FDI positions and primary-income outflows (add these to DATA-SOURCES.md, plus a connector).
- **D2.** New lever: the share of AI capital/IP owned abroad (a scenario assumption with a sourced range). Profits on foreign-owned capital leave as primary income through the current account, and the gate covers the new flow.
- **D3.** Policies that reach foreign rent: a source-based levy or withholding on AI revenue (reuse the F22 study inputs). The fund may *buy* foreign equity with its own resources but cannot dilute what is foreign-owned.
- **D4.** Sanity check against Wossnig (2026): reproduce the qualitative result that flow taxes on domestic capital miss the foreign AI rent.
- **Done when:** a scenario with 80% foreign-owned AI capital runs gated, and the dashboard shows how much of the AI dividend each policy can still reach.

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
2. Credit: a borrowing cap (recommended), or the banks layer.
3. Step 0 stopgap README note today (recommended: yes).
