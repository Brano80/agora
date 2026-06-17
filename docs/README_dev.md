# AGORA

**A modular integration dashboard for modelling the European economic & financial structure — and testing scenarios for the coming AI economy.**

AGORA does *not* build economic engines from scratch. It joins existing, authoritative models and data behind one common interface, so the picture of Europe's economy sharpens as new sources plug in — then lets you run novel policy scenarios (UBI, Universal Basic Compute, capital/robot tax, land-value tax, sovereign-fund dividends, AI-driven productivity & deflation) and compare outcomes.

## The idea in one line
Same authoritative data everyone uses (Eurostat, ECB, IMF, BIS, WID…) → mapped into one shared accounting frame → run through pluggable models → compared on a dashboard. You don't ask anyone to "believe the numbers"; you show the mechanism and let every assumption be inspected and swapped.

## Architecture (5 layers)
1. **Dashboard** — scenario builder · results · module manager.
2. **Orchestrator + consistency check** — route · run · reconcile (becomes the agent crew later).
3. **Pluggable model modules** (common interface): SFC monetary core (Minsky/sfctools) · distribution (EUROMOD/PolicyEngine) · input–output (FIGARO) · agent-based (EconAgent) · AI-shock driver (Epoch/AI Index/ILO).
4. **Canonical accounts schema** — shared SNA sectors & flows. *The linchpin that makes plug-in real.*
5. **Data connectors → DuckDB store** — DBnomics (Eurostat/ECB/IMF/OECD/WB/BIS/AMECO/WID) + EU KLEMS, PWT, Epoch, AI Index, OWID, … "+ new" snaps in.

## Honest principles
- **A sandbox, not an oracle** — for comparing policies and stress-testing logic, never forecasting.
- **Coupling is the hard part** — v1 uses loose coupling (run modules in sequence, reconcile via the schema, consistency-check); tight two-way consistency is the research frontier.
- **More modules ≠ more precise** — precision comes from calibration + validation against history, plus the consistency layer. Add deliberately, validate each.
- **No single "best" model** — show the trade-offs (growth / inequality / stability / fiscal sustainability / resilience); the values call stays the user's.

## Stack
Python · DuckDB (store + schema) · Streamlit (dashboard) · engines as common-interface modules (MCP-wrappable) · DBnomics + specialist connectors · orchestrator in plain Python → LangGraph/n8n later.

## Build phases
1. **Skeleton** — schema + module interface + DBnomics connector + SFC core (German baseline) + minimal Streamlit dashboard with the scenario triad.
2. **+ distribution module + AI-shock driver** + scenario builder + comparison view.
3. **+ FIGARO I-O + more connectors** (EU KLEMS, WID, BIS, Epoch) + consistency reconciliation + sensitivity analysis.
4. **Agentic orchestration** (plain-language scenario → run → reconcile → report) + multi-country + shareable.

## Layout
- `docs/` — architecture, scope, data sources, prior art, build plan.
- `prototype/` — `econ_sim_v0` (illustrative toy proving the mechanism).
- `data/` — connectors + local store (to build).
- `modules/` — engine adapters behind the common interface (to build).
- `dashboard/` — Streamlit app (to build).

See `docs/INTEGRATION-ARCHITECTURE.md` for the full spec.
