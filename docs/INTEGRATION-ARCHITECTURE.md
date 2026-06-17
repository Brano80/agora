---
title: AGORA — Modular Integration Dashboard for an EU Economy Model
created: 2026-06-03
note: The product is the integration layer, not the engines. Honest about the hard part (coupling) and what "more precise" really requires.
---

# AGORA — one modular dashboard over the existing engines

The goal (now crisp): **don't build engines — integrate them.** One coherent, modular dashboard that orchestrates the existing models + data behind a *common interface*, so any new data source or sub-model snaps in, the picture of Europe's economy sharpens over time, and you can run the AI-paradigm scenarios and compare outcomes. (See the diagram.)

## The five layers
1. **Dashboard (your control surface)** — scenario builder (set the levers), results views (GDP, Gini, sectoral balances, debt, employment), and a **module manager** to toggle which engines/data are active.
2. **Orchestrator + consistency check** — turns a scenario into an ordered run across the active modules, collects outputs, reconciles them, flags incoherence. (This is where the "agent crew" from the earlier diagram eventually lives; v1 can be plain Python.)
3. **Pluggable model modules** — each existing engine wrapped behind one **common interface**: `declares inputs · declares outputs · run(scenario, data) → results`. SFC core (Minsky/sfctools), distribution (EUROMOD/PolicyEngine), input–output (FIGARO), agent-based (EconAgent), AI-shock driver (parameterised from Epoch/AI Index/ILO). A new model = a new adapter implementing the interface → it just slots in.
4. **Canonical accounts schema — the glue.** A shared vocabulary based on the System of National Accounts (ESA/SNA): the same sectors (households, firms, banks, government, central bank, sovereign fund, RoW) and flows that every module reads/writes. **This is the linchpin** — without it, "plug-in" degenerates into spaghetti; with it, everything composes in one consistent accounting frame.
5. **Data connectors → local store** — each source (DBnomics, EU KLEMS, WID, BIS, Epoch, AI Index, OWID…) is a pluggable connector that maps its series into the schema and lands in a local DuckDB store. New source = new connector → more calibrated detail.

## The honest hard part (read this)
- **Model coupling is the real challenge, not the UI.** A *static* microsim (EUROMOD), a *dynamic* SFC model (Minsky), and an *agent-based* model (EconAgent) have different time steps, units, and assumptions. You cannot naively "plug them together" and get one consistent world. Realistic v1 = **loose coupling**: run modules in a sensible sequence (macro core sets aggregates → microsim distributes them → AI-shock module perturbs inputs), pass results through the schema, and let the consistency checker catch contradictions. **Tight two-way consistency between engines is the research frontier** — don't promise it early.
- **"More data/modules" ≠ automatically more precise.** Coupling adds error and inconsistency risk. What actually buys precision is **calibration + validation against history** (does the integrated baseline reproduce real EU data?) and the consistency layer keeping the books coherent — not the module count. Add modules deliberately, validate after each.
- **It stays a sandbox, not an oracle** (carried over). And **"best model for the AI economy" is multi-objective** — growth vs inequality vs stability vs fiscal sustainability vs resilience. The dashboard's job is to **show the trade-offs and which assumptions drive them**, not to crown a single winner (that's a values call, which stays yours).

## Stack (solo-friendly, runs on your machine)
- **Python** throughout. **DuckDB** as the local store/schema. **Streamlit** (or Plotly Dash) for the dashboard — fastest path to a real UI solo.
- Each engine = a Python module implementing the common interface (and optionally MCP-wrapped, matching your SAIN pattern). **Minsky** models can be driven via its file format/CLI; **PolicyEngine/EUROMOD** via their APIs.
- Orchestrator: plain Python first; LangGraph/n8n later when you automate the agent crew.

## Phased build
- **Phase 1 — Skeleton:** canonical schema + DuckDB + DBnomics connector + **one** module (SFC core, Minsky/sfctools) calibrated to a German baseline + a minimal Streamlit dashboard showing baseline vs the AI / Abundance-Settlement scenario triad. A working *modular skeleton with one plug fitted.*
- **Phase 2 — Plug in 2 more:** distribution module (PolicyEngine/EUROMOD) + AI-shock driver; scenario builder + side-by-side comparison view.
- **Phase 3 — Breadth + coherence:** FIGARO I-O module; more connectors (EU KLEMS, WID, BIS, Epoch); consistency reconciliation + sensitivity analysis.
- **Phase 4 — Agentic + reach:** the orchestrator becomes the agent crew (scenario→run→reconcile→report in plain language); multi-country; shareable dashboard.

## Next step
Build **Phase 1**: define the canonical schema + module interface, wire the DBnomics connector, fit the SFC core to a German baseline, and stand up the minimal Streamlit dashboard with the scenario toggle. That proves the plug-in contract end-to-end; every later module and data source hangs off it.
