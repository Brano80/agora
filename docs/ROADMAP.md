# AGORA — roadmap

> Philosophy & open questions live in **docs/MANIFESTO.md** (a living document, updated as we learn).

Single source of truth for what's built and what's next. Every phase composes
through the canonical schema and is gated by the consistency checker; nothing is
trusted until it passes the gate + tests.

## Done

### Phase 1 — Skeleton ✅
Canonical SNA schema · module interface · DBnomics connector · self-contained
two-class SFC monetary core · the consistency gate (no money leaks) · minimal
Streamlit dashboard with the scenario triad. Calibrated to a German 2019
baseline (validated). See `docs/PHASE1.md`.

### Phase 1.5 — Live data + multi-country + the scout loop ✅
Dimension-based live DBnomics pull (per-series live→snapshot fallback) ·
France added as a second country · the **scout**: a daily, human-gated research
loop on local Qwen that proposes data revisions / coverage / connector gaps,
which a 09:10 review surfaces for approval. Patch drafts are grounded on the
real file tree + a deterministic hallucinated-path backstop. See `docs/SCOUT.md`.

### Phase 2 — Distribution + AI-shock + scenario tools ✅
Distribution module (10-decile personal income layer: Gini, poverty, Palma) with
a reconciliation gate (deciles must sum to the macro total) · AI-shock driver
(named, sourced shock parameters → scenario levers) · scenario builder + side-by-
side comparison view. See `docs/PHASE2.md`.

## Next

### Phase 3 — Breadth + coherence (open economy)
*Increment 1 (open economy / rest-of-world + fx_assets): ✅ (2026-06-06). Increment 2 (input-output / Leontief sector decomposition, illustrative structure): ✅ (2026-06-07). Remaining: live FIGARO/Eurostat naio pull + BIS/WID/Epoch connectors.*
- **FIGARO input-output module** — production structure & sector linkages, so an
  "AI hits sector X" shock propagates realistically.
- **Rest-of-world sector** — open the closed Phase-1/2 economy; bring net
  exports inside the books (activates the `rest_of_world` sector + `fx_assets`).
- **More connectors** (from the scout backlog): BIS (debt stocks), WID (wealth),
  Epoch / Stanford AI Index (compute & AI investment), EU KLEMS / PWT
  (productivity & labour share by industry).
- **Tighter reconciliation** across coupled modules + first sensitivity analysis.

### Phase 4 — Policy search & the trade-off frontier  ✅ (SHIPPED 2026-06-07)
Turn the sandbox from "compare a few scenarios" into "search the policy space".
- **Multi-objective optimiser** over the policy levers (capital tax, UBI, LVT,
  sovereign-fund dividend, …): given an objective the USER states (a target, or
  weights/constraints across growth / inequality / poverty / fiscal
  sustainability / stability / resilience), search consistency-gated runs and
  return the **best mix for that objective**.
- **Pareto frontier view** — when no single objective is given, return the set of
  non-dominated trade-offs (can't improve one goal without sacrificing another)
  rather than a false "winner".
- **Sensitivity analysis on every result** — how fragile the optimum is to the
  shaky assumptions (β, γ, labour-share path, calibration). The guardrail against
  an optimiser "gaming" a reduced-form model.
- **Honesty contract:** any optimum is *best given these assumptions and this
  internally-consistent sandbox* — conditional, gated, never presented as a
  real-world guarantee. The values call (which point on the frontier) stays the
  user's. This upholds the project's "no single best — show the trade-offs"
  principle.

### Phase 5 — Agentic orchestration + reach
The orchestrator becomes the full agent crew (describe a scenario or objective in
plain language → route → run → reconcile → report) · more countries / euro-area ·
shareable dashboard. The scout loop and the Phase-4 optimiser become tools the
crew calls.
**Increment 1 SHIPPED 2026-07-07** — `agent_crew.py`: run-time pipeline
(Scenario→approve→Runner→Critic(gate)→Report) over the `mcp_api` tool layer.
Deterministic rule-based planner + template reporter (offline, 9 tests, 233
total); human-approval gate (elicitation) can veto before compute; comparisons
declare no 'winner'; LLM planner/reporter pluggable. `docs/PHASE5.md`. Next:
LLM steps via MCP sampling + wire scout/optimiser as crew tools.

### Phase 6 — Proper government / fiscal block  (increments 1+2 SHIPPED 2026-06-24)

**Increment 1 (shipped).** Switchable, default-OFF, gate-exact (~2e-9), 197 tests. `SFCCore(fiscal_reaction=, debt_target=, i_rate=)`: (a) a **fiscal-reaction rule** — `theta` drifts to steer debt/GDP toward a target, so the model can now represent a CONSOLIDATION or EXPANSION stance (verified: steers DE debt to ~40 / ~70 / ~90 on demand) instead of a fixed stabilising path; (b) the **interest switch** (`i_rate`>0) turns on the r-g snowball. Default OFF reproduces shipped results exactly. **Increment 2 (SHIPPED).** Broad revenue base: the base-year net tax is split into a labour rate (`theta_w` on wages) + a baseline CAPITAL rate (`theta_k` on profits) via `capital_tax_share` (calibrate) — same total at the base year, so year-0 reproduces EXACTLY (a1_k recalibrated to the post-tax split), and revenue now follows the capital share (capital-tax base +363% under the AI shift). Wired through `AgoraOrchestrator(... capital_tax_share=, fiscal_reaction=, debt_target=, i_rate=)` + `build(...)`, all default OFF. End-to-end: broad base + reaction turns the AI-shock debt RUNAWAY (DE 60->162% with no block) into a CONTROLLED path (60->82%), gate exact (~6e-9), 198 tests. **DONE (i):** the frontier now scores fiscal sustainability with the proper block (finding F20 — under a responsive government debt is controlled to ~80%% and becomes policy-INVARIANT, so fiscal stops being the binding trade-off; UBC still on the frontier). **DONE (ii):** year-0 interest income folded into the calibration AND `SFCCore.run` now calibrates at its own run rate, so the interest switch reproduces year-0 too. This also fixed a latent wiring bug — `capital_tax_share` now reaches the run via `calib_kwargs` (it previously only affected `params()`), so the broad base GENUINELY applies: it alone tames the AI-shock debt 162->85%. **Phase 6 COMPLETE.** Default OFF keeps the shipped dashboard/study unchanged.

**Why.** The 2014-2023 driven stress-backtest (standalone study, `scripts/study_backtest_stress.py`) validated the two channels the UBC thesis rests on — GDP tracks real history to <1% in calm years (DE 0.84%, FR 0.73%, IT 0.48%) and bounds the 2020-22 shocks (model over-predicts GDP +4-9% in 2020 with no COVID, under-predicts the 2023 inflation rebound), and disposable Gini reproduces to <1pp. The ONE dimension that fails is government debt/GDP (clean 1.5-7pp, stress 17-21pp). Diagnosed precisely: it is NOT a calibration bug (baseline DE deleverages -9.5pp on its own; `i_rate=0`, no interest compounding). It is a **revenue stub**:

- government revenue = `theta x wage bill` ONLY — no capital-income tax (tau=0 with no policy), no VAT/consumption tax, no other base;
- `theta` is frozen at its base-year debt-stabilising value (primary deficit = `g_fiscal`*debt), with NO fiscal-reaction / primary-balance path;
- so when fed a country's ACTUAL (rising) spending, the narrow frozen revenue can't respond, and the block cannot represent a fiscal STANCE — it misses Germany's primary surpluses (debt held ~flat 75.6->76.3% while DE actually deleveraged 74.5->62.3%) and the COVID fiscal spikes (FR/IT/ES +15-22pp in 2020). This is the F9/F2 "fiscal block is directional-only" caveat, now localized.

**Crucially this does NOT touch the UBC thesis.** In the SFC core both policy arms share an identical deficit path (`dH_s = G - tax_w`; the cash levy `tax_k` is redistributed and cancels, UBC dilutes in-kind), so the debt-block error is COMMON to cash and UBC and cancels exactly in the comparison. Debt is also not one of the swept Monte-Carlo parameters. The UBC-vs-cash verdict rests on output + distribution (both validated), not on absolute fiscal levels.

**Build (next session).**
1. **Broaden the revenue base** — add capital-income tax and a consumption/VAT base alongside `theta x wage bill`, each calibrated to the base-year revenue split (OECD/AMECO revenue-by-base shares). Keep the consistency gate exact.
2. **Fiscal-stance path** — let the primary balance be an input/leverpath (so a country's actual net-lending stance — surplus or deficit — can be driven), and add a switchable **fiscal-reaction rule** (theta drifts toward a target debt/GDP each period, Taylor-style). Default OFF so it cannot change shipped headline results unless enabled.
3. **Interest block** — turn on `i_rate` with a (switchable) effective rate so debt dynamics include the snowball/`r-g` term.
4. **Re-validate** — re-run the stress study; debt/GDP should then track within a sensible tolerance and become a FOURTH validation dimension (currently excluded from the headline). Add per-year debt to the validation report + a test.
5. **Then** debt/fiscal sustainability becomes a credible Pareto objective (it is currently directional-only on the frontier).

**Interim option (smaller, if needed before the full block):** the minimal fiscal-reaction rule alone (step 2's theta-drift) — self-contained, gated, default-off — would make debt track far better without building the full tax system.

### Phase-4 enabler (spike) — AGORA over MCP  ▶ increment 1 SHIPPED 2026-07-07

**Status: minimal read-only server SHIPPED** (`mcp_api.py` + `mcp_server.py`, 6 tools, gate-refusal + disclaimer/provenance enforced in the tool layer, 18 tests; see `docs/MCP.md`). Deferred increments: Elicitation (assumption approval), Sampling (narration), MCP Apps, Registry. Full brief: `docs/BRIEF-mcp-integration.md`.

**Ask.** Wrap the existing `orchestrator` as an MCP server so AGORA can be driven by the planned agent crew and any MCP client (Claude, VS Code, Hermes): minimal read-only tools `run_scenario(geo, levers)` + `compare(scenarios)` first; then Elicitation (assumption/scenario approval — fits "the values judgment stays with the user") and Sampling (let the Report step borrow the client's model to narrate, no bundled model) as small increments. Defer MCP Apps. Build to the stable 2025-11-25 spec; note the 2026-07-28 RC (stateless core + Extensions); consider the official MCP Registry.

**Guardrails (non-negotiable).** The consistency gate still gates every MCP result (no accounting leaks). The "sandbox, not oracle" disclaimer + assumption sources travel with every output. If ever exposed beyond localhost: auth + capability scoping.

**Effort.** investigate ~0.5-1d · minimal server ~2-3d · Elicitation/Sampling +~1d each · MCP Apps out of spike scope. Record the outcome here + in `STATE.md` when run.

## Standing principles (apply to every phase)
Sandbox, not an oracle · transparency over authority (every parameter sourced &
swappable) · validate before trusting (the consistency gate + backtests) · loose
coupling through the schema · no single "best" — report the trade-offs · the
human stays the decision-maker; agents draft, the gate guards, you decide.

---

## Committed experiments (pinned — run as soon as the enabling build lands)

1. ✅ **Universal Basic Capital vs cash UBI** — *the direct test of the flow-vs-stock
   insight* (Manifesto §4, Q1). **DONE 2026-06-07.** `sovereign_fund` activated; UBC
   modelled as annual in-kind dilution (τ·FP) into a citizens' endowment paying a
   per-capita dividend; gate-clean. Result: cash helps sooner, UBC compounds and
   overtakes ~year 11, ending ~100% citizen ownership / Gini ~0.04 / poverty 0
   (finding F5; write-up `docs/UBC-EXPERIMENT.md`; tests `test_ubc.py`). *Open
   follow-up:* endogenise investment vs owners' net return (crux C1).


### Multi-region core — Q2 (national vs global dividend)  ▶ increment 1 SHIPPED 2026-06-07
DE+FR as separately-gated open economies; national-vs-global AI-dividend comparison (`region.py`, `docs/MULTI-REGION.md`, finding F7). National dividend widens the between-country gap under the shock; global pooling narrows it ~34%. **Next:** add a low-income region (the real rich-vs-poor test) + tight bilateral trade feedback.

### Study — AI-levy-base sizing (SHIPPED 2026-06-30)
`scripts/study_ai_levy_base.py`: sizes an AI-specific levy (EU-wide DST + data-centre/compute
levy) vs an ownership-funded dividend. Finding F22 — levy raises ~€35/person/yr today (~1/25th
of the ownership route) and does not catch up before ~2050; ownership is the engine, the levy a
seed. Sourced inputs (hyperscaler capex guidance, Tax Foundation DST, CEPS, AGORA counterfactual).
Output `study_ai_levy_base.md` gitignored; chart `social_ai_levy.png`.

### Richer policy search (SHIPPED 2026-07-07)
`orchestrator.rich_policy_search` adds the investment-regime x fund-reinvestment axes to the
Phase-4 frontier (opt-in; default frontier unchanged). Finding F23: the UBC-dominates-cash
frontier is conditional on fixed investment; under endogenous investment the cash-vs-UBC form
trade-off re-opens. Gate-clean, +1 test. Feeds Phase 5 (agent crew over the MCP tools).
