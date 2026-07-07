#!/usr/bin/env python3
"""End-to-end MCP verification: spawns mcp_server.py as a REAL stdio
subprocess and drives it through the MCP protocol with the SDK client.
This is the test that backs the claim "AGORA runs as an MCP server".

Run from anywhere:
    python scripts/verify_mcp.py
Requires: pip install "mcp[cli]"   (same dependency as the server itself)

Checks:
  1. initialize handshake + server identity (agora_mcp)
  2. tools/list exposes the 9 agora_* tools
  3. tools/call agora_run_scenario (AI shock + UBC, DE) -> gate passed,
     disclaimer + resolved assumptions + data provenance present,
     series length == horizon
  4. unknown-geo refusal is an actionable error payload with NO series
  5. agora_compare preset='ubc' -> 4 arms, every arm gate-clean

Exit code 0 = PASS, 1 = at least one check failed.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    raise SystemExit('The MCP SDK is required: pip install "mcp[cli]"')

FAILURES = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print("  [%s] %s%s" % ("OK " if ok else "FAIL", label,
                           (" -- " + detail) if (detail and not ok) else ""))
    if not ok:
        FAILURES.append(label)


def payload(result) -> dict:
    """Tool results carry a JSON text block."""
    return json.loads(result.content[0].text)


async def main() -> int:
    params = StdioServerParameters(command=sys.executable,
                                   args=[os.path.join(ROOT, "mcp_server.py")],
                                   cwd=ROOT)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("connected: %s (protocol %s)"
                  % (init.serverInfo.name, init.protocolVersion))
            check("initialize handshake, server = agora_mcp",
                  init.serverInfo.name == "agora_mcp")

            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            expected = {"agora_run_scenario", "agora_compare",
                        "agora_list_modules", "agora_get_series",
                        "agora_list_geos", "agora_validate_baseline",
                        "agora_preview_scenario", "agora_narrate",
                        "agora_policy_frontier"}
            check("tools/list exposes the 9 agora_* tools",
                  expected <= names, "missing: %s" % (expected - names))

            r = await session.call_tool("agora_run_scenario", {
                "geo": "DE", "horizon": 5, "labour_share_end": 0.30,
                "capex_growth": 0.06, "capital_tax": 0.40, "ubc": True})
            p = payload(r)
            check("UBC run: consistency gate passed",
                  p.get("gate", {}).get("passed") is True)
            check("UBC run: disclaimer travels",
                  "sandbox" in p.get("disclaimer", "").lower())
            check("UBC run: assumptions fully resolved",
                  "labour_share" in p.get("assumptions", {}).get("levers", {}))
            check("UBC run: data provenance attached", "data_sources" in p)
            check("UBC run: series length == horizon",
                  len(p.get("series", {}).get("gdp", [])) == 5)

            r = await session.call_tool("agora_run_scenario", {"geo": "XX"})
            p = payload(r)
            check("refusal path: unknown geo is an actionable error",
                  "Unknown geo" in p.get("error", ""))
            check("refusal path: no series leaked", "series" not in p)

            r = await session.call_tool("agora_compare", {
                "geo": "DE", "preset": "ubc", "horizon": 5,
                "series": ["gini_personal", "top10_wealth_share"]})
            p = payload(r)
            runs = p.get("runs", [])
            check("compare preset=ubc: 4 arms", len(runs) == 4,
                  "got %d" % len(runs))
            check("compare preset=ubc: every arm gate-clean",
                  bool(runs) and all(x.get("gate", {}).get("passed")
                                     for x in runs))

            # increment 2 -- elicitation (preview) + sampling (narrate)
            r = await session.call_tool("agora_preview_scenario", {
                "geo": "DE", "labour_share_end": 0.30, "capex_growth": 0.06,
                "capital_tax": 0.40, "ubc": True})
            p = payload(r)
            check("preview: assumptions resolved, nothing computed",
                  "approval_prompt" in p and "gate" not in p
                  and "series" not in p)

            r = await session.call_tool("agora_narrate", {
                "geo": "DE", "preset": "ubc", "horizon": 5})
            p = payload(r)
            check("narrate: gated numbers returned (narration optional)",
                  bool(p.get("runs")) and ("narrative" in p
                                           or "narrative_unavailable" in p))

            r = await session.call_tool("agora_policy_frontier",
                                        {"geo": "DE", "horizon": 10})
            p = payload(r)
            check("frontier: gated Pareto menu, no single winner",
                  p.get("n_frontier", 0) >= 2 and p.get("n_gated_out") == 0)

    print()
    if FAILURES:
        print("FAIL - %d check(s) failed: %s"
              % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("PASS - AGORA answers over real MCP stdio "
          "(subprocess + initialize + tools/list + tools/call).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
