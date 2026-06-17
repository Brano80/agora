# AGORA — Living Manifesto

*A living philosophical-economic document. It holds the ideas, possibilities,
problems, and engine findings behind AGORA. It is a record of thinking-in-
progress, not settled belief: claims here are hypotheses to be stress-tested,
and the model's job is to challenge them, not flatter them.*

**Maintained by:** Claude (the assistant), on Brano's direction. Brano sets the
direction and makes the values calls; Claude keeps this document current and
honest.

**Update protocol.** This file is updated when (a) an AGORA run produces a
finding worth recording, (b) we discuss or decide a new idea, problem, or
mechanism, or (c) the scout surfaces something conceptually relevant. Every
substantive change gets a dated changelog entry. Engine findings are always
labelled *illustrative / conditional* — AGORA is a sandbox, not an oracle.
Disagreement and open questions are kept visible, not resolved prematurely.

---

## 0. Why this document exists

AGORA is a tool for thinking clearly about the largest economic question of the
AI transition. The engine produces numbers; this document holds the *meaning* —
the questions worth asking, the mechanisms worth testing, the traps to avoid,
and what we actually learn as we run it. The engine and the manifesto co-evolve:
ideas here become scenarios to test; results there become entries here.

---

## 1. The central question

As AI and automation raise productivity, they may **decouple output from human
labour income**: GDP keeps rising while labour's share of it falls and the gains
pool with the owners of capital, compute, and data. Left alone, this widens
inequality even amid growing abundance — the **Great Decoupling**.

The hopeful counter-thesis — the **Abundance Settlement** — is that the right
institutional response can turn an abundance shock into broadly shared
prosperity instead of concentration. The open question is *which* response, at
*what scale*, through *what mechanism*.

---

## 2. Core theses we are exploring

1. **Decoupling is a real risk, not a certainty.** Whether it happens depends on
   institutions and on whether AI's gains are enclosed or diffused.
2. **Redistribution of a flow cannot offset concentration of a compounding
   stock.** (See §4.) This reframes the whole policy question from income to
   ownership.
3. **"Universal" should arguably mean *across humanity*, not within one nation.**
   An AI dividend rests on a common inheritance — collective human knowledge,
   data, decades of public research — not on any one country's effort. National-
   only schemes risk being locally progressive but globally regressive.
4. **No single "best."** The goals (growth, equality, poverty, fiscal
   sustainability, stability, resilience, global fairness) genuinely conflict.
   The work is to surface the trade-offs, not crown a winner.

---

## 3. Open cruxes (the make-or-break uncertainties)

These are the questions on which the whole picture hinges. We hold them open.

- **C1 — Enclosure vs diffusion.** Does AI value stay gated behind frontier
  training, proprietary data, compute and energy (enclosure → gap widens), or
  does it diffuse cheaply via open weights and on-device models (diffusion → gap
  can narrow)? *Working view (2026-06): the capability **floor** will diffuse
  (on-device LLMs, e.g. AI PCs), but the **rents** — frontier training, the data
  flywheel, platform/distribution lock-in — may stay concentrated. Both can be
  true at once. Unresolved.* (Epoch AI grounding now in the data layer: frontier training compute ~4.2x/yr — the *capability* side races ahead; whether *rents* diffuse is the open part.)
- **C2 — National vs global.** If each rich country taxes its own AI capital and
  pays its own citizens, the between-country gap widens even as within-country
  gaps narrow. Does a "truly universal" dividend require global scope? (Modelable
  only with the multi-region extension — see §6 / roadmap Phase 4+.)
- **C3 — Flow vs stock.** Can any income transfer (cash UBI) offset an advantage
  that compounds as a *stock* (capital + network effects)? Or must the *asset*
  itself be distributed? (See §4.)
- **C4 — Does redistribution raise or lower output?** AGORA's demand-led closure
  says recycling income to high-spending households can *raise* GDP. This depends
  on the closure assumptions and must be stress-tested, not trusted.

---

## 4. The mechanism question — beyond cash UBI

**The key insight (Brano, 2026-06-06):** cash UBI redistributes a *flow*
(income), but the AI advantage is a *compounding stock* (capital, network
effects, the data flywheel). Handing out a static flow leaves ownership — and
therefore the compounding — untouched: owners keep pulling away while recipients
get a drip that rent and inflation erode. **To distribute a compounding
advantage you must distribute the asset, not just the income.**

A menu of mechanisms, each with its case and its tension. AGORA's job is to let
us test them, not to pick.

| Mechanism | The idea | The tension |
|---|---|---|
| **Cash UBI** | Unconditional income to all. | Redistributes flow not stock; partly captured by asset owners via rents/inflation; framed as "welfare". *Case for:* simple, dignified, no paternalism, evidence from trials. |
| **Universal Basic Capital** (citizens' equity / sovereign-citizens' fund) | Everyone owns a share of the AI capital stock; the dividend *grows with the network effect*. | Governance & political capture of the fund; valuation; transition (how is the stake acquired?). *Directly targets the flow-vs-stock problem.* |
| **Universal Basic Compute / Services** | Distribute the productive capability (compute, AI access) or essential services, not cash. | Can be paternalistic/bureaucratic; defining the basket; provisioning at scale. *Gives agency, not just purchasing power.* |
| **Data dividends / data-as-labour** | Pay people for the data that trains AI (data dignity). | Per-capita value may be small; measurement & market design hard. |
| **Commons / public-option AI** (predistribution) | Build & run AI as a public utility / open commons so surplus is never enclosed. | Who funds the frontier? Governance, quality, and the same training-cost concentration. *Predistribution beats redistribution if achievable.* |

**Cross-cutting:** "predistribution" (change who owns the assets up front) is
structurally different from "redistribution" (tax-and-transfer after the fact).
The flow-vs-stock insight pushes toward predistribution / asset distribution.

---

## 5. Problems, risks, and traps

- **Governance & collective action (global).** No world taxing authority; capital
  and compute relocate to non-taxing jurisdictions; coordination is brutally hard
  (cf. the OECD 15% minimum tax — years for a partial deal).
- **Capital mobility.** Any uncoordinated capital tax leaks; worse globally.
- **Confidently-wrong risk.** The danger isn't that the model can't compute — it's
  that it produces a plausible-but-wrong answer. The consistency gate, sensitivity
  analysis, and human judgment are the only guards.
- **Model artifacts vs real mechanisms.** An optimiser can "game" a reduced-form
  model (exploit the demand closure or the distribution elasticities) rather than
  reality. Always report sensitivity; treat any optimum as conditional.
- **Inflation / positional goods.** Cash transfers can be absorbed by fixed-supply
  assets (housing, land) → captured as rent. Argues for land-value taxes and for
  distributing assets, not just income.

---

## 6. Findings from the engine

*Illustrative and conditional — calibrated to the stated assumptions, gated for
consistency, never a forecast.*

- **F1 (2026-06, DE & FR).** The decoupling reproduces at the household level:
  with no policy, a labour-share collapse drives the personal Gini from ~0.30 to
  ~0.47 and at-risk-of-poverty from ~17% to ~28%; the top decile's share jumps
  while the bottom 40%'s collapses. A capital-tax-funded UBI ("Abundance
  Settlement") contains both. *Mechanism demonstration, not a prediction.*
- **F2 (2026-06).** As the labour share falls, the wage-tax base erodes and
  government deficits/debt rise — a structural fiscal signal of the AI transition,
  independent of the inequality result.
- **F3 (2026-06, DE & FR).** Opening the economy (rest-of-world + net foreign
  assets) is stock-flow consistent to ~1e-4 MEUR. A persistent current-account
  surplus (DE ~5% of GDP) accumulates a large net-creditor position (~117% of
  GDP over 30y) — the savings-glut dynamic, the mirror of another region's
  debt. This is exactly why the **national-vs-global** question (Q2) needs the
  multi-region extension: one economy's surplus is another's deficit.
- **F4 (2026-06, DE & FR).** With a sector input-output layer, the AI labour-
  share shock lands very unevenly: high-exposure sectors (ICT/finance/business,
  industry) shed labour share fastest while low-exposure sectors (construction,
  agriculture) barely move. The aggregate decoupling is the sum of a few sectors
  automating hard, not a uniform drift — relevant for *targeted* policy (which
  sectors to tax / retrain / socialise). Sectoral VA reconciles to GDP.
- **F5 (2026-06-07, DE & FR) — the flow-vs-stock crux, answered in the sandbox.** Running cash UBI against Universal Basic Capital at *equal cost* (same AI shock, same capital-levy intensity τ=40%, identical government deficit path), the trade-off is real and it **reverses over time**. Cash UBI compresses inequality immediately (macro Gini 0.30→0.14 in year 1) and helps most in the first decade. UBC starts slow — the early years build the endowment — but the citizens' fund stake compounds: its dividend **overtakes the cash transfer around year 11**, and by the 30-year horizon citizens own ~100% of the capital stock, the dividend is ~10× the cash transfer, the macro Gini falls to ~0.04 (vs cash UBI's ~0.33), and poverty is eliminated. *Redistribution (flow) is faster; predistribution (stock) compounds.* The activation of the `sovereign_fund` did not open an accounting leak — the gate closes to ~1e-4 MEUR every period. **Big caveat:** investment is held on the same path in both arms; endogenising owners' incentive response (C1) is the next stress test. **(Addressed 2026-06-14 — see F14: the verdict survives endogenous investment once the fund reinvests.)** Full write-up: `docs/UBC-EXPERIMENT.md`.
- **F6 (2026-06-07, DE) — does predistribution choke investment? (crux C1, quantified).** Endogenising investment as a response to owners' RETAINED capital-income share (elasticity ε, swappable), the UBC vs cash-UBI verdict splits cleanly. The *distributional* result is **robust**: the dividend still overtakes the cash transfer at ~year 11 and UBC ends far more equal (Gini ~0.04 vs ~0.33) at every ε, because the crossover happens before investment paths diverge. The *level* result is **not**: with a strong disincentive (ε=1) UBC ends with a capital stock ~40% below the cash path, because in the current model only private owners fund capex and the fund pays out 100% — so as owners are diluted out, nobody invests. The clean fix (and next thread): let the fund **reinvest** (it owns the capital), moving the investment function from departing owners to the public fund. Until then, read ε>0 as UBC's pessimistic bound. Gate stays clean at all ε. See `docs/UBC-EXPERIMENT.md`.
- **F6b (2026-06-07) — C1 resolved by fund reinvestment.** Letting the fund reinvest a fraction of its profit share (`ubc_reinvest`) removes the collapse entirely: even a modest rate (r≥0.3) leaves UBC with a LARGER capital stock than cash UBI under ε=1, because as private owners are diluted out the fund picks up the capex — by the late horizon all investment is fund-financed. C1 is therefore a *governance-design* question, not a refutation of predistribution: 'who invests when capital is socialised?' → the fund does. Gate clean at every reinvest rate.
- **F7 (2026-06-07, DE + FR) — national vs global AI dividend (Q2, first result).** With two countries modelled as separately-gated open economies, a purely NATIONAL cash dividend lets the between-country gap GROW under the AI shock (pop-weighted between-country Gini 0.019→0.048 over 30y, as richer DE throws off the bigger dividend); pooling the dividend GLOBALLY narrows it ~34% and transfers per-capita income DE→FR. Q2 confirmed in-sandbox: a national AI dividend entrenches the cross-country gap, a pooled one shrinks it. (UBC partly self-equalises across countries; cash does not.) **Update (increment 2): adding POLAND (~EUR14k/capita) nearly TRIPLES the national between-country Gini (0.048→0.138 for DE+FR→DE+FR+PL); pooling sends the largest transfer to Poland. Tight bilateral trade (gravity matrix + damped regional fixed point) now couples the bloc two-way: per-country gate intact, intra-bloc trade reconciles to ~1e-9, output propagates across borders.** Architecture is N-country; the path is to fill in toward EU27. `docs/MULTI-REGION.md`.
- **F8 (2026-06-07, DE) — only ownership touches WEALTH (the dimension that matters).** With wealth now a dynamic outcome: cash UBI and no-policy leave the top-10% WEALTH share parked at the observed ~60% (cash redistributes income, never the capital), while UBC collapses it to ~21% (wealth Gini 0.50->0.11) by socialising the capital itself. Robustness (Monte-Carlo, #53): across the full prior span UBC's inequality and poverty bands sit ENTIRELY below cash UBI's — the "owning beats receiving" verdict is not a point-estimate artifact. See `docs/FINDINGS.md`.
- **F9 (2026-06-07, DE + FR) — FIRST historical backtest: the demand core is validated, the fiscal block is not.** Driving the model with the ACTUAL labour-share, investment and government paths over 2014-2019 (and 2010-2019), it reproduces realised **GDP to ~1-1.6% mean error** — strong validation of the consumption / import / output mechanics. But **government debt/GDP is off by ~28-37%**: the income-tax rate theta is calibrated to the GINI, so it does double duty and the implied primary balance (hence the debt path) is arbitrary. IMPLICATION: the inequality, poverty and WEALTH results (demand+distribution side) are backtest-supported; the fiscal-sustainability claim (F2) is directional only until the government block is calibrated to the actual balance. The cross-section β fit is uninformative (R^2=0.02), as expected. This is exactly what "validate before trusting" is for. **FIXED (2026-06-07): theta is now calibrated to the FISCAL BALANCE (debt-stabilising, ~30% effective rate), not the Gini — which had forced it to ~47% and a 10%-of-GDP phantom surplus that crashed debt negative. Inequality is anchored by the distribution module's personal Gini instead. Government debt/GDP is now bounded and realistic (DE baseline holds ~56-60% vs the observed 58.7%). Live backtest CONFIRMS it: GDP error ~1% (DE 1.16%, FR 1.04%); gov-debt error fell from ~30-37% to FR 2.46% (PASS) and DE 12.78%. France (roughly debt-stabilising stance) is matched almost exactly; Germany's residual ~13% IS its discretionary austerity (black-zero surpluses cutting debt 75%->59%), which a constant-stance sandbox correctly does not invent. The model is now historically validated; F2 (fiscal) upgraded from directional-only to validated-for-constant-stance.** With the books realistic, the policy frontier shifts: UBC dominates cash UBI on the trade-offs too, so the remaining choice is the UBC levy's INTENSITY, not flow-vs-stock.
- *(future)* National vs global dividend on between-country inequality — **blocked
  on the multi-region extension**; logged as the headline Phase-4+ research
  question.

---

## 7. Key terms

- **Labour share** — fraction of output paid to labour (vs capital). Its fall is
  the engine of decoupling.
- **Predistribution vs redistribution** — changing ownership up front vs taxing
  and transferring after.
- **Universal Basic Capital** — citizens' ownership stake in the capital stock.
- **Rest of world (RoW)** — everything outside the modelled economy, as one
  accounting counterparty (not a model of other economies).
- **Sandbox, not oracle** — compares policies in a consistent world; does not
  forecast.

---

## 8. Open research questions (for the engine)

- Q1. Cash UBI vs Universal Basic Capital (citizens' fund dividend) — head to
  head on inequality, demand, and fiscal path. **✅ Answered (F5, 2026-06-07):**
  flow helps sooner, stock compounds and dominates by ~year 11; see
  `docs/UBC-EXPERIMENT.md`. *Open follow-up:* make investment respond to the
  owners' net return (C1) and test whether the verdict survives.
- Q2. National vs global AI dividend and the between-country gap. **▶ First result (F7, 2026-06-07):** national entrenches / widens it, global pooling narrows it ~34% (DE+FR). *Open:* add a low-income region + tight bilateral trade. `docs/MULTI-REGION.md`.
- Q3. Enclosure vs diffusion — model AI gains as concentrated rents vs a cheap
  general-purpose input, and compare distributional outcomes.
- Q4. Does the "redistribution raises GDP" result survive alternative model
  closures? (robustness of F1/C4)
- Q5. Land-value tax / positional-goods capture — does adding a fixed-supply
  asset change which mechanism wins?

---

## Changelog

- **2026-06-17 (engine credibility upgrades A/B/C)** — Three additions hardening the data. (A) **Endogenous wealth accumulation** (`omega`, default 0.15): no-policy & cash top-10% wealth share now CONCENTRATES with the rising capital share instead of staying flat (DE 55.5→60.7% over 30y) — removes the "flat baseline" objection and makes the UBC comparison conservative. The cross-section was uninformative (R² .06, wrong sign), so the default is a documented r>g value with a wide MC prior. (B) **Joint uncertainty + sensitivity**: the Monte-Carlo now samples all six assumptions together and the UBC-beats-cash verdict survives the FULL joint prior (UBC Gini p5–p95 0.01–0.20 vs cash 0.25–0.39, non-overlapping); a first-order sensitivity ranking shows the investment response (C1) drives ~50% of outcome variance, capex ~28%, β ~11%, ω ~0% on income (it acts on wealth). (C) **Sourced AI exposure**: sector exposure now from the OECD (2024) Sectoral Taxonomy of AI Intensity (NACE A38) + Felten-Raj-Seamans (2021) AIIE — exposure is *cognitive*, so Industry falls 0.70→0.45 and services rise. 196 tests, gate exact (~7e-9). Findings **F17–F19**. Dashboard regenerated.

- **2026-06-07 (fiscal fix, post-backtest)** — Re-calibrated theta to the fiscal balance (debt-stabilising) instead of the Gini, fixing the debt-crash F9 flagged. Government debt now bounded/realistic; personal Gini still anchored by the distribution module. Policy frontier now UBC-dominated across intensities. 127 tests.

- **2026-06-07 (first live backtest)** — Ran the model against real 2010-2019 history (DE, FR). GDP reproduced to ~1%; government debt off ~30% (theta over-loaded onto the Gini anchor). Added finding **F9**; flagged F2 (fiscal) as directional-only pending a proper government block. Demand/distribution findings hold.

- **2026-06-07 (model hardening 2/2)** — Monte-Carlo uncertainty bands; backtest harness + Epoch-grounded shock anchors + OLS β-estimator; Acemoglu-Restrepo labour-market task block (labour share emerges from automation); dynamic wealth distribution; real-trade-matrix injection + euro/non-euro FX channel. Added finding **F8** (wealth). 127 tests. All 9 improvements done.

- **2026-06-07 (model hardening 1/2)** — Gate gained an economic-plausibility law; depreciation turned on with a separate fast-obsolescing AI-capital stock; interest on government debt added (switchable); export closure made foreign-demand-driven (stable for entrepot openness). These MODERATE the headline UBC results toward credibility (30y citizen ownership ~78% not 100%, Gini ~0.11 not 0.04) — the old extremes were partly no-depreciation + output-coupled-export artifacts. 111 tests, gate exact. (Improvements 5-9 pending.)

- **2026-06-07 (exploration brief)** — Ran the live 26-country model. Headline 10-year findings (aggressive AI, τ=40%): do-nothing raises EU poverty +11pts avg (doubles in high-wage-share states); UBC pushes German poverty BELOW today's level and gives each citizen a ~EUR124k capital stake + ~EUR25k/yr; global pooling cuts the between-country gap a third and is worth ~EUR11k/yr to a Romanian. 'Do nothing' is off the policy frontier. Plain-English brief: `docs/FINDINGS.md`.

- **2026-06-07 (EU-wide Q2)** — Pulled all EU27 baselines live; 26 viable (Luxembourg excluded — entrepôt economy diverges; added a `MultiRegion` viability guard + made `build_snapshot --write` refuse failed validation). All-EU result: national between-country Gini 0.22 → global pooling 0.15 (−33%), transferring from DK/DE/SE to RO/HR/HU/PL. Ireland flagged (GDP multinational-distorted; EU-25 ex-IE: 0.21 → 0.14). 107 tests.

- **2026-06-07 (AMECO live + N-country Q2)** — Fixed AMECO wage-share live resolution (geo dimension is lowercase ISO3 on DBnomics); `labour_share` now pulls live for any EU member. Dashboard Q2 panel scaled to all loaded countries (bloc multiselect). 7-country bloc: a national AI dividend gives between-country Gini 0.22, global pooling cuts it ~32%, transferring DE/FR → BG/RO/EL/PL/PT. 107 tests.

- **2026-06-07 (EU27 on-ramp)** — Live multi-country snapshot builder (`snapshot_builder.py` + `scripts/build_snapshot.py`): pull any EU country from DBnomics with provenance, import reconciliation, flagged defaults, and validate-before-trust. Adding a member is now run·review·write. 107 tests. `docs/SNAPSHOT-BUILDER.md`.

- **2026-06-07 (multi-region increment 2)** — Added a low-income region (Poland, sourced snapshot) and TIGHT bilateral trade (`solve_trade`: gravity matrix + damped regional fixed point). The poor region ~triples the between-country gap; trade coupling keeps each country gated and reconciles intra-bloc trade to ~1e-9. 99 tests. `docs/MULTI-REGION.md`.

- **2026-06-07 (multi-region / Q2)** — Multi-region core (`region.py`): DE+FR as separately-gated open economies; national-vs-global dividend comparison. Finding **F7** — national dividend entrenches the between-country gap, global pooling narrows it ~34%. First in-sandbox result on Q2. 91 tests. `docs/MULTI-REGION.md`.

- **2026-06-07 (C1 resolved)** — Added sovereign-fund REINVESTMENT (`ubc_reinvest`): the fund reinvests part of its profit share into capex. Finding **F6b** — this removes the ε>0 capital collapse; UBC ends larger than cash UBI as the investment function migrates from owners to the fund. 84 tests. `docs/UBC-EXPERIMENT.md`.

- **2026-06-07 (Phase 4)** — Multi-objective POLICY SEARCH + Pareto frontier shipped (`policy_search.py`). 13 gated policies, 8 on the frontier; 'no policy' dominated; the frontier spans BOTH cash UBI (wins on stability) and UBC (wins on growth/equality/resilience) — the 'no single best' principle made operational. 79 tests. See `docs/PHASE4.md`.

- **2026-06-07 (C1 stress test)** — Endogenised investment against owners' retained capital-income share (`inv_elasticity` in the SFC core). Added finding **F6**: UBC's equality win is robust to the investment disincentive, but under a strong response it ends a more-equal *smaller* economy — pointing to fund reinvestment as the next refinement. 71 tests.

- **2026-06-07 (later)** — THE PINNED EXPERIMENT shipped: Universal Basic Capital vs cash UBI (`sovereign_fund` activated, in-kind dilution mechanism in the SFC core, gated). Added finding **F5** and marked **Q1 answered**. Flow-vs-stock trade-off demonstrated and reverses at ~year 11. 67 tests. New write-up `docs/UBC-EXPERIMENT.md`.

- **2026-06-07 (later)** — Phase 3 increment 3: specialist connectors. BIS household debt + WID top-10% wealth share (multi-provider, snapshot-sourced; wealth = UBC prep) and a bespoke Epoch AI-compute connector grounding the AI-shock assumptions. FIGARO live-matrix pull remains the one deferred connector.

- **2026-06-07** — Phase 3 increment 2: input-output module (Leontief sector decomposition, gated to GDP) + AI sectoral-exposure propagation. Added finding F4 (decoupling is sector-concentrated). New research angle: targeted (sectoral) vs uniform policy.

- **2026-06-06 (later)** — Phase 3 increment 1: open economy (rest-of-world + fx_assets) shipped & gated. Added finding F3 (surplus -> net-creditor / savings-glut dynamic). Reinforces Q2 (national vs global).

- **2026-06-06** — Document created. Seeded with: the central question and the
  Abundance Settlement; the flow-vs-stock insight and the mechanism menu beyond
  cash UBI (Universal Basic Capital, UBS/UBC, data dividends, commons/
  predistribution); the enclosure-vs-diffusion crux (incl. on-device LLM
  diffusion); the national-vs-global / common-inheritance argument; engine
  findings F1–F2; and research questions Q1–Q5.


---

## F10 (2026-06-11) — The poverty floor, made honest

The distribution module no longer assumes a transfer->compression elasticity
(gamma). Income is now modelled as a flat universal transfer PLUS lognormal
market income, so shares, Gini and poverty follow exactly from the transfer's
size: G = G_mkt*(1-t), and AROP has a HARD FLOOR — zero once the per-capita
transfer alone clears 60% of the median.

This re-scores the pinned experiment (DE, tau=40%, 30y): cash UBI's old
"poverty -> 0" disappears (ends at ~11.8% — a flat pool fixed at tau*FP never
clears the rising AROP line), while UBC's poverty -> 0 SURVIVES, because the
compounding dividend grows to ~60% of household income and clears the line
outright by the horizon. Q1's flow-vs-stock verdict is therefore STRONGER under
honest arithmetic: the stock instrument is the only one that abolishes relative
poverty in the model, and the claim no longer leans on an assumed elasticity.
(Caveat unchanged: beta — market-Gini sensitivity to the capital share — is
still an assumption pending the panel estimate.)


---

## F11 (2026-06-11) — Gated pooling: multipliers help cash, overshoot UBC

The Q2 pooled (global) dividend now runs through each country's books — a new
`intl_transfer` lever delivers the net pooling transfer to households with the
rest-of-world as counterpart, fx accumulating the full current account. Two
findings the old ex-post overlay could not see:

1. Cash pooling narrows the between-country gap MORE than previously reported
   (DE+FR+PL: ~71% vs ~32%), because the transfer carries a demand multiplier —
   the receiving country's income rises by more than the transfer itself.
2. UBC pooling still narrows the rich+poor bloc (~29%), but between two
   similar-income countries (DE-FR) the transfer's accumulated stock effects
   (fx/wealth -> consumption) OVERSHOOT the tiny residual gap. Pooling is an
   instrument for REAL income gaps; applied to near-equals it is neutral at
   best. Q2's policy conclusion is unchanged but now honestly derived; the
   second-order feedback of transfers onto dividend pools is a single
   corrective pass, not yet iterated to a fixed point.

Also: the expenditure identity now includes P52+P53 inventories (owner-
financed, non-productive), so the books close on published GDP and the
"statistical discrepancy" interpretation of nx_gap is retired where `gcf` is
available. Rebuild snapshots to activate.


---

## F12 (2026-06-12) — beta is unidentified in macro data; the verdict doesn't care

The within-country fixed-effects panel (25 EU countries x 2010-2024, 275 obs)
returns beta = 0.05 with R^2 = 0.006 — like the level cross-section before it
(R^2 = 0.02), it identifies nothing. The reading is NOT "beta is small": the
observed Gini is post-redistribution, and European welfare states absorbed the
(modest) capital-share movements of that window almost fully. The model's beta
maps the capital share to MARKET inequality under held policy — a counterfactual
invisible in post-tax macro data.

Decisions: (a) beta stays an explicit, swappable ASSUMPTION; (b) the Monte-Carlo
prior is widened downward to (0.1, 1.0) to honour the panel; (c) the headline
UBC-vs-cash ranking was re-verified band-separated (Gini AND poverty, p95 vs p5)
across the full widened span — the verdict does not hinge on beta because both
arms face the same decoupling and the transfer-incidence arithmetic dominates.
Next identification attempt, if wanted: WID *pretax* distribution series (DINA),
which see market income before redistribution — a connector away.


---

## F13 (2026-06-14) — the market-Gini connector lands; the redistribution wedge, quantified

The OECD IDD connector supplies the pre-tax/pre-transfer (MARKET) Gini that F12
said was "a connector away". It does two things. **(1)** It QUANTIFIES why
post-tax macro data can't see beta: the redistribution wedge (1 - disposable /
market Gini) averages **~0.37** across DE/FR/IT/ES/NL/PL (DE 0.41, FR 0.44) —
European welfare states erase about a third of market inequality, swamping the
capital-share signal. **(2)** It shows the CROSS-SECTION still fails to identify
beta even on market data: across the six countries the market-Gini-on-capital-
share slope is ~-0.43 (wrong sign), dominated by structural between-country
heterogeneity rather than the within-country mechanism. The clean route is a
within-country fixed-effects panel on the market Gini (GINIB) over time — the
estimator is built (`estimate_beta_market_panel`, proven on injected panels) and
waits only on the live IDD time-series pull (user's machine). beta stays a
swappable assumption; the verdict remains band-separated across its prior (F12).
A new OPTIONAL distribution mode anchors the model's reported `gini_market` at
the true pre-tax level (vs the legacy disposable-level anchor), reproducing the
observed disposable Gini via the measured wedge; OFF by default (headline-
affecting), gate-clean.

---

## F19 (2026-06-17) — AI exposure is cognitive, not robotic: grounding it moves the shock from factories to offices

Replacing the round-number sectoral exposure guess [0.30/0.70/0.20/0.50/0.90/0.40]
with sourced values from the OECD (2024) *Sectoral Taxonomy of AI Intensity* (NACE
A38 High/Medium/Low) cross-referenced with Felten-Raj-Seamans (2021) AIIE gives
[0.25/0.45/0.25/0.45/0.80/0.55]. The substantive correction: **Industry/manufacturing
falls 0.70→0.45 and cognitive services rise** — AI/ML exposure hits information,
finance, professional and public-service work, not the assembly line (that is robot
automation, a different measure). The sectoral decoupling story is now data-grounded
and the exposure column links to its source. Swappable; gate unaffected.

## F18 (2026-06-17) — the verdict survives the FULL joint assumption space, and we can name what drives it

Sampling all six uncertain assumptions JOINTLY (labour-share floor, capex growth,
investment response, β, ω, consumption propensity), UBC's Gini band (p5–p95 ≈
0.01–0.20) sits entirely below cash UBI's (≈ 0.25–0.39) — "owning beats receiving"
is not an artifact of any one prior. A first-order (correlation-based) sensitivity
decomposition ranks the drivers of the UBC outcome: the **investment response (C1)
~50%**, AI capex growth ~28%, β ~11%, labour-share floor ~10%; ω is ~0% on the
*income* Gini because it acts on the *wealth* stock. The single most important
parameter to pin down empirically is therefore the capex-dilution elasticity, not β.

## F17 (2026-06-17) — endogenising wealth concentration removes the "flat baseline" and strengthens UBC

The old model held the top-10% WEALTH share constant unless UBC acted, so no-policy
and cash were flat lines — a fair criticism ("why is the baseline conveniently
flat?"). Adding ω (capital-share → wealth-concentration, mirroring β on the stock,
default 0.15) makes wealth CONCENTRATE on its own as the capital share rises: DE
no-policy top-10% wealth share now drifts 55.5→60.7% over 30y, cash tracks it, and
only UBC collapses it (to ~20%). This makes the counterfactual *worse* without
policy, so it is conservative for UBC — the "only ownership touches wealth" result
is now shown against a deteriorating, not static, baseline. The cross-section is
uninformative (slope −0.26, R² .06, confounded like β), so ω is a documented r>g
default with a wide Monte-Carlo prior, not a spurious point estimate.

## F16 (2026-06-14) — grounding beta refines the headline: ownership is the durable UBC win, income compression is conditional

Lowering the default beta 0.6 -> 0.13 (F15) shrinks the no-policy AI inequality
(DE 30y gini_personal 0.50 -> 0.34, poverty 0.30 -> 0.21) and the cash-UBI gini
(0.35 -> 0.24): the old magnitudes were partly the high-beta assumption. The UBC
verdict then splits cleanly BY DIMENSION:

- **WEALTH (ownership) — beta-INDEPENDENT and regime-INDEPENDENT.** UBC collapses
  the top-10% wealth share 0.60 -> 0.10-0.21 in every case (fixed / endogenous /
  reinvest, any beta), because it socialises the capital STOCK; cash never moves
  it. This is the durable core of "owning beats receiving" (F8).
- **INCOME Gini — CONDITIONAL.** At the grounded beta UBC still ends more equal
  than cash when the fund PAYS OUT the dividend (DE fixed: 0.119 vs 0.238), but
  under full REINVESTMENT the dividend is plowed into capital + growth (F14)
  rather than compressing income, so UBC's income Gini rises to ~cash (0.241 vs
  0.238) even as wealth still collapses. A genuine dividend-vs-(ownership+growth)
  trade-off, not a dominance.

Net: grounding the one free parameter makes the story more honest and more
interesting. UBC's robust advantage is WHO OWNS the capital (and, with
reinvestment, a larger economy); its income-inequality edge depends on beta and
on how much of the dividend is paid out vs reinvested. "No single best" holds.
Gate clean; 187 tests. `orchestrator.c1_closure()` now reports wealth alongside
GDP and income Gini.

---

## F15 (2026-06-14) — the market-Gini identifier resolves, and beta is unidentified even PRE-tax

F12 proposed the pre-tax (market) Gini as the clean identifier; the live OECD IDD
market-Gini (INC_MRKT_GINI, OECD/DSD_WISE_IDD@DF_IDD, AGE=_T) within-country FE
panel now runs end to end: **beta = 0.128, R^2 = 0.024** (71 obs, 6 countries,
2010-2024). Removing the redistribution confound does NOT rescue identification:
even on pre-tax inequality the aggregate capital share explains ~2% of
within-country variation. The reason is structural, not just redistribution — the
2010-2024 capital-share variation is small and swamped by other inequality
drivers (composition, cycle, sector), while the model's beta is the response to a
labour-share-HALVING shock far outside that historical range, unobservable by
construction. **Triangulation:** every empirical anchor is low and weak —
disposable FE panel 0.16-0.20 (R^2 .04-.07), market FE panel 0.13 (R^2 .02); the
between-country cross-sections are confounded (market cross-section is the wrong
sign, -0.43). The correct (positive) sign finally appears in the market FE panel.
**Verdict impact: none** — the UBC-vs-cash ranking is band-separated across the
whole beta prior (F12), so an unidentified beta cannot move it. **Decision (user, 2026-06-14):** the model DEFAULT beta is lowered
from 0.6 to the market FE estimate **0.13** — the conceptually-correct (pre-tax)
anchor and the value every data estimate clusters near — while the Monte-Carlo
prior stays WIDE (0.1, 1.0) to carry the large structural-shock uncertainty the
weak R^2 reflects. beta remains explicit and swappable. The OECD/IDD market-Gini
live fetch path is confirmed working (probe-resolved dataset OECD/DSD_WISE_IDD@DF_IDD,
INC_MRKT_GINI, self-relaxing dimension filter).

---

## F14 (2026-06-14) — crux C1 closed on the pinned experiment: endogenous investment, cured by reinvestment

F5's caveat ("investment held on the same path in both arms") is now lifted.
Running the actual cash-vs-UBC arms with investment ENDOGENOUS (elasticity to
owners' retained capital-income share, eps=0.75), gated end to end:
**(a) FIXED** investment (legacy headline) — UBC ends more equal and not smaller;
**(b) ENDOGENOUS, fund pays out everything** — UBC's economy is choked to ~0.81x
(DE) / 0.71x (FR) of the cash path, reproducing F6 (diluting owners deters
capex); **(c) ENDOGENOUS + fund REINVESTMENT** — output recovers monotonically
with the reinvest rate and UBC matches/exceeds the cash economy (DE crosses 1.0x
near reinvest~0.8, reaches 1.11x at full reinvest; FR ~1.04x at full). Across ALL
regimes the EQUALITY verdict is untouched: UBC ends far more equal than cash
(Gini ~0.01-0.05 vs ~0.35). So C1 is a GOVERNANCE-DESIGN question, not a
refutation: predistribution does deter private capex, but a fund that replows its
profits is the investor of last resort — and the equality dividend never depends
on sacrificing the economy. Every arm gate-clean; `orchestrator.c1_closure()`
reproduces the numbers.


---

## F11 amendment (2026-06-12) — the overshoot was the solver, not the economics

Running the all-EU pooled UBC arm exposed it: the single corrective pass drove
Italy (a large giver under compounding UBC pools) into negative household
income by 2042 — caught by the plausibility gate, exactly as designed. The
transfer->demand->pool feedback is FIRST-order for big givers, so pass-2 is now
iterated to a damped fixed point (strict gating suspended for intermediate
guesses, the converged state gated in full).

At the fixed point the F11 'overshoot' between near-equal countries DISAPPEARS
(DE+FR, both forms: pooling narrows) and the single-pass magnitudes are
superseded: DE+FR+PL narrowing is ~50% under cash and ~58% under UBC (the
single pass had overstated cash at 71% and understated UBC at 25%). Standing
honest conclusion: globally pooled dividends narrow between-country gaps under
BOTH forms, slightly more under UBC, and the books close to ~1e-9 throughout.
All-EU magnitudes: re-run `scripts/q2_all_eu.py` (the UBC arm previously
crashed mid-script; cash-only numbers from that run are superseded too).


---

## Q2 ANSWERED (2026-06-12) — the all-EU national-vs-global dividend

Definitive run: 25 countries (IE dropped as MNC-distorted), tau=40%, 30y, both
arms gated end-to-end (worst residual ~1e-8), pooling iterated to the fixed
point. Result:

* Cash UBI: between-country Gini 0.207 (national) -> 0.102 (global) = **51%
  narrowing**. Givers DK/SE/FI (~13-15k EUR/capita); receivers BG/RO/PL
  (~14-18k).
* UBC: 0.209 -> 0.100 = **52% narrowing**. Givers IT/DE/DK; receivers BG/HU/LV.
  Per-capita magnitudes are ~3x cash (35-49k EUR/capita at horizon) because the
  pooled claims COMPOUND — pooling a stock instrument moves far more value than
  pooling a flow, for the same narrowing percentage.

Answer to Q2: a purely national AI dividend entrenches a between-country Gini of
~0.21 across the EU; pooling halves it under EITHER form. The form choice
matters less for BETWEEN-country equality than for within-country wealth (F5/F10)
— but UBC pooling implies much larger cross-border transfer volumes, which is
where the political constraint will bind. Magnitudes are model-scale under the
stated shock, not forecasts.
