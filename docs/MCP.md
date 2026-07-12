# AGORA over MCP — the model as a server

**Status: spike SHIPPED 2026-07-07** (increment 1 of `docs/BRIEF-mcp-integration.md`).
AGORA's orchestrator is now exposed over the Model Context Protocol, so any MCP
client (Claude Desktop / Claude Code / VS Code / the planned Phase-5 agent crew)
can drive gated scenario runs directly.

## Files
- **`mcp_api.py`** — the tool layer (pure stdlib, zero new dependencies,
  fully tested offline in `tests/test_mcp_api.py`). The guardrails live here
  so no transport can bypass them.
- **`mcp_server.py`** — a thin FastMCP stdio shim over `mcp_api`. The only
  file that needs the MCP SDK.

## Tools (all read-only)
| Tool | What it does |
|---|---|
| `agora_run_scenario` | One gated scenario on a country's calibrated baseline (levers: labour_share_end, capex_growth, capital_tax, ubi / ubc + ubc_reinvest; Phase-6 fiscal block optional). |
| `agora_compare` | Several scenarios side by side: `preset='triad'`, `preset='ubc'` (the pinned 4-arm experiment), or custom lever sets. No 'winner' field by design. |
| `agora_list_modules` | The module chain + declared schema inputs/outputs. |
| `agora_get_series` | Series catalogue / full provenance (provider, dataset, dimensions, source URL, live/snapshot). |
| `agora_list_geos` | Available snapshot countries (+ aggregate + FIGARO-matrix flags). |
| `agora_validate_baseline` | The validate-before-trusting scorecard for a geo. |
| `agora_preview_scenario` | **Elicitation / approval step**: resolve a scenario's assumptions *without running it*, so the human signs off on the lever paths before any numbers are computed. What it shows is exactly what `agora_run_scenario` will run. |
| `agora_narrate` | **Sampling**: run a gated scenario/comparison, then narrate it in prose using the *client's own model* (AGORA bundles none). Numbers stay authoritative; the borrowed model only phrases them, told to invent nothing and name no 'winner'. Degrades to numbers-only if the client lacks sampling. |
| `agora_policy_frontier` | **Optimiser as a tool**: sweep policy form x tax intensity against the AI shock, gate every candidate, return the Pareto (non-dominated) set on 5 objectives. A trade-off menu, not a winner. |
| `agora_crew` | **The run-time agent crew as one tool**: a plain-language request -> plan -> approve -> gated run -> report (single / comparison / frontier / robustness). The natural-language front door; pair with `agora_narrate` for model-written prose. |
| `agora_sensitivity` | **Robustness / Analysis**: Monte-Carlo over the joint prior (gated per draw) -> 5-95% outcome bands + the ranked drivers of a metric. Answers 'is the result just your parameters?'. |

## Guardrails (enforced in `mcp_api`, not the shim)
1. **Consistency gate on every result** — a failing run returns an error
   payload with the failing checks and **no series**. Both refusal paths are
   covered: the strict-mode `ConsistencyError` raise and report-level failures.
2. **Sandbox, not oracle** — every payload carries the disclaimer, the fully
   resolved lever assumptions, and per-series data provenance.
3. **Read-only, snapshot-by-default** — reproducible offline; `allow_live=true`
   opts into live DBnomics with snapshot fallback. Localhost stdio only; if
   this is ever exposed remotely, add auth + capability scoping first.

## Setup (user's machine)
```
pip install "mcp[cli]"
```
Claude Desktop — add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "agora": {
      "command": "python",
      "args": ["C:\\Users\\brano\\Projects\\AGORA\\mcp_server.py"]
    }
  }
}
```
(Use the full interpreter path if `python` isn't on PATH — same gotcha as Task
Scheduler.) Quick test without a client:
```
npx @modelcontextprotocol/inspector python mcp_server.py
```

## Verified
- Sandbox: 246 tests green (tool layer + shim registration + increment-2
  elicitation/sampling helpers); end-to-end through the FastMCP protocol layer
  (gated payload, object-array `scenarios` argument, unknown-geo refusal).
- **User's Windows machine: `python scripts/verify_mcp.py`** — real spawned
  stdio subprocess, protocol 2025-11-25 (handshake, tools listed, gated UBC run
  with disclaimer/assumptions/provenance, no-series refusal, 4-arm compare
  gate-clean). Increment 1 (6 tools) PASSED 2026-07-07; re-run after the
  i