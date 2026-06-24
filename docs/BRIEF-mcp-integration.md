# Brief — Investigate MCP integration for AGORA

**Owner:** AGORA PM  **Date:** 2026-06-24  **Type:** time-boxed spike
**Priority:** P2 — Phase-4 *enabler*. Do **not** preempt Phase 3 (FIGARO + connectors) or the pinned UBC experiment.

## Ask
Investigate (and thin-prototype) exposing AGORA over the **Model Context Protocol (MCP)** so the model can be driven by the planned agent crew and by any MCP client (Hermes, Claude, VS Code) — and adopt MCP's newer interaction features where they fit our principles.

## Why now
- The roadmap already commits to "tools as MCP" + an agent crew (Phase 4). MCP has matured past basic tools; several new features map directly onto AGORA principles (human-in-the-loop, transparency).
- Cheap to investigate; the answer shapes how we build Phase-4 orchestration.

## Investigate (concrete)
1. **AGORA-as-MCP-server** — wrap the existing `orchestrator` as MCP tools: `run_scenario(geo, levers)`, `compare(scenarios)`, `list_modules()`, `get_series(schema_name)`. Every result must still pass the **consistency gate** before return.
2. **Elicitation** (server→user prompt) — use for scenario approval / confirming swappable assumptions before a run. Direct fit for "the values judgment stays with the user."
3. **Sampling** (server→host LLM) — let the *Report* step borrow the client's model to narrate results, with no bundled model.
4. **MCP Apps** — feasibility of shipping the dashboard as an interactive app *inside* the client vs standalone Streamlit. Likely **defer**.
5. **Spec / future-proofing** — build to the stable **2025-11-25** spec; note the **2026-07-28 RC** (stateless core + Extensions); consider publishing to the official **MCP Registry**.

## Recommendation (prior, pre-investigation)
- Build a **minimal read-only AGORA MCP server** (`run_scenario` + `compare`) as the Phase-4 substrate. Add **Elicitation** (approvals) and **Sampling** (narration) as small increments. **Defer MCP Apps.**
- Keep it a spike — no diversion from Phase 3 or the UBC experiment.

## Guardrails (non-negotiable)
- Consistency gate still gates every MCP result (no accounting leaks).
- "Sandbox, not oracle" disclaimer + assumption sources travel with every output.
- If ever exposed beyond localhost: auth + capability scoping.

## Effort (rough)
- Investigation ~0.5–1 day · minimal server (wrap orchestrator) ~2–3 days · Elicitation/Sampling +~1 day each · MCP App = separate, larger (out of spike scope).

## Decision needed
Approve a **time-boxed spike** (investigate + prototype the `run_scenario` MCP tool), scheduled as a Phase-4 enabler **after** Phase 3 and the UBC experiment. Record the outcome in `STATE.md` / `docs/ROADMAP.md`.

## References
MCP intro (modelcontextprotocol.io) · spec 2025-11-25 (sampling / roots / elicitation) · 2026-07-28 release candidate (stateless core + Extensions) · MCP Apps (/extensions/apps/overview).
