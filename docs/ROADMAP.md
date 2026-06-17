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
