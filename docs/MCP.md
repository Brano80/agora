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

## Verified (2026-07-07)
- Sandbox: 219 tests green (18 new for the tool layer + shim registration);
  end-to-end through the FastMCP protocol layer (gated payload, object-array
  `scenarios` argument, unknown-geo refusal).
- **User's Windows machine: `python scripts/verify_mcp.py` PASS** — real
  spawned stdio subprocess, protocol 2025-11-25, all 11 checks green
  (handshake, 6 tools listed, gated UBC run with disclaimer/assumptions/
  provenance, no-series refusal, 4-arm compare gate-clean). Re-run this
  script after any change to mcp_api.py / mcp_server.py.

## Deferred (next increments, per the brief)
- **Elicitation** (server→user approval of assumptions before a run) — direct
  fit for "the values judgment stays with the user"; +~1 day.
- **Sampling** (Report step borrows the client's model to narrate) — +~1 day.
- **MCP Apps** (dashboard inside the client) — out of scope; Streamlit stands.
- **MCP Registry** publication — after the server has real mileage.
- Spec note: built against the current stable SDK; re-check the 2026-07-28 RC
  (stateless core + Extensions) when it lands.
