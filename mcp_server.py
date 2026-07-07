#!/usr/bin/env python3
"""AGORA MCP server — a thin stdio shim over `mcp_api` (see docs/MCP.md).

Run:      python mcp_server.py            (from the repo root)
Requires: pip install "mcp[cli]"          (the engine itself stays pure stdlib)

All tools are READ-ONLY. The guardrails live in mcp_api and cannot be bypassed
here: every result passes the stock-flow consistency gate (failing runs return
an error payload with NO series), and every payload carries the sandbox-not-
oracle disclaimer, the resolved scenario assumptions, and data provenance.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from mcp.server.fastmcp import FastMCP, Context
    from mcp import types
except ImportError:
    raise SystemExit('The MCP SDK is required to serve AGORA over MCP:\n'
                     '    pip install "mcp[cli]"\n'
                     '(mcp_api works without it — this shim is the only '
                     'dependent file.)')

import mcp_api

mcp = FastMCP("agora_mcp")

_READ_ONLY = {"readOnlyHint": True, "destructiveHint": False,
              "idempotentHint": True, "openWorldHint": False}


def _dump(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=1, default=str)


@mcp.tool(name="agora_run_scenario",
          annotations={"title": "Run a gated AGORA scenario", **_READ_ONLY})
def agora_run_scenario(geo: str = "DE", horizon: int = 30,
                       labour_share_end: Optional[float] = None,
                       capex_growth: float = 0.015, capital_tax: float = 0.0,
                       ubi: bool = False, ubc: bool = False,
                       ubc_reinvest: float = 0.0,
                       series: Optional[List[str]] = None,
                       name: Optional[str] = None,
                       allow_live: bool = False,
                       fiscal_reaction: float = 0.0,
                       debt_target: Optional[float] = None,
                       i_rate: Optional[float] = None,
                       capital_tax_share: float = 0.0) -> str:
    """Run ONE scenario on a country's calibrated 2019 baseline and return the
    consistency-gated result.

    Defaults reproduce the no-shock Baseline. The AI shock is
    labour_share_end=0.30 + capex_growth=0.06. Policy: capital_tax (rate on
    distributed profits, 0-1) recycled either as cash UBI (ubi=true) or into a
    citizens' capital fund (ubc=true; ubc_reinvest = fraction of the fund's
    profit share reinvested into capex). The Phase-6 fiscal block
    (fiscal_reaction, debt_target, i_rate, capital_tax_share) defaults OFF.

    `series` selects reported series (default: gdp, consumption, investment,
    labour_share, gini_personal, poverty_rate, top10_wealth_share); unknown
    names return the available catalogue. Data is the validated snapshot by
    default; allow_live=true pulls live DBnomics with snapshot fallback.

    Returns JSON: {disclaimer, geo, scenario, gate{passed,max_residual},
    years[], series{name:[...]}, summary{*_end}, assumptions{levers},
    data_sources} — or {error, gate} if the consistency gate failed (results
    are withheld rather than returned untrusted).
    """
    return _dump(mcp_api.run_scenario(
        geo=geo, horizon=horizon, labour_share_end=labour_share_end,
        capex_growth=capex_growth, capital_tax=capital_tax, ubi=ubi, ubc=ubc,
        ubc_reinvest=ubc_reinvest, series=series, name=name,
        allow_live=allow_live, fiscal_reaction=fiscal_reaction,
        debt_target=debt_target, i_rate=i_rate,
        capital_tax_share=capital_tax_share))


@mcp.tool(name="agora_compare",
          annotations={"title": "Compare AGORA scenarios side by side",
                       **_READ_ONLY})
def agora_compare(geo: str = "DE", preset: Optional[str] = None,
                  scenarios: Optional[List[Dict[str, Any]]] = None,
                  horizon: int = 30, series: Optional[List[str]] = None,
                  reinvest: float = 0.0, allow_live: bool = False) -> str:
    """Run several scenarios on the same calibrated baseline and return the
    aligned, gated results.

    Use preset='triad' (Baseline / AI-shift-no-policy / Abundance Settlement)
    or preset='ubc' (the pinned 4-arm cash-UBI-vs-Universal-Basic-Capital
    experiment; `reinvest` = the UBC fund's capex-reinvestment fraction) — or
    pass scenarios=[{name, labour_share_end, capex_growth, capital_tax, ubi,
    ubc, ubc_reinvest}, ...] using the agora_run_scenario lever names.

    Returns JSON: {disclaimer, geo, years[], data_sources, runs:[{scenario,
    gate, assumptions, series, summary}]}. Any arm that fails the consistency
    gate has its series withheld and an error attached — the other arms still
    return. There is deliberately no single 'winner' field: compare the
    trade-offs.
    """
    return _dump(mcp_api.compare(geo=geo, preset=preset, scenarios=scenarios,
                                 horizon=horizon, series=series,
                                 reinvest=reinvest, allow_live=allow_live))


@mcp.tool(name="agora_list_modules",
          annotations={"title": "List AGORA's module chain", **_READ_ONLY})
def agora_list_modules() -> str:
    """List the pluggable module chain (SFC macro core, decile distribution,
    Leontief input-output) with each module's declared schema inputs and
    outputs. Returns JSON: {modules:[{name, doc, inputs[], outputs[]}], note}.
    """
    return _dump(mcp_api.list_modules())


@mcp.tool(name="agora_get_series",
          annotations={"title": "Inspect the data-series catalogue",
                       **_READ_ONLY})
def agora_get_series(code: Optional[str] = None) -> str:
    """Inspect the canonical schema series. Without `code`: compact catalogue
    of all series (code, label, unit, provider, live). With `code` (e.g.
    'gdp', 'labour_share', 'top10_wealth_share'): full provenance — provider,
    dataset, dimensions, source URL, note, live/snapshot mode. Returns JSON.
    """
    return _dump(mcp_api.get_series(code=code))


@mcp.tool(name="agora_list_geos",
          annotations={"title": "List available countries", **_READ_ONLY})
def agora_list_geos() -> str:
    """List the countries with validated calibration snapshots (EU members +
    EA20 aggregate). Returns JSON: {geos:[{geo, aggregate, io_matrix}], note}.
    io_matrix=true means a real Eurostat FIGARO input-output matrix is cached
    for the sectoral module.
    """
    return _dump(mcp_api.list_geos())


@mcp.tool(name="agora_validate_baseline",
          annotations={"title": "Validate a country baseline", **_READ_ONLY})
def agora_validate_baseline(geo: str = "DE", allow_live: bool = False) -> str:
    """'Validate before trusting': check that a country's calibrated baseline
    reproduces its observed national accounts (GDP components, labour share,
    debt seed, baseline Gini). Returns JSON: {all_ok, rows:[{metric, target,
    model, rel_error, ok}], gate, data_sources}. Run this before drawing
    conclusions from scenarios on a geo you haven't used yet.
    """
    return _dump(mcp_api.validate_baseline(geo=geo, allow_live=allow_live))


@mcp.tool(name="agora_preview_scenario",
          annotations={"title": "Preview & approve scenario assumptions",
                       **_READ_ONLY})
def agora_preview_scenario(geo: str = "DE", horizon: int = 30,
                           labour_share_end: Optional[float] = None,
                           capex_growth: float = 0.015, capital_tax: float = 0.0,
                           ubi: bool = False, ubc: bool = False,
                           ubc_reinvest: float = 0.0,
                           name: Optional[str] = None,
                           allow_live: bool = False) -> str:
    """Resolve a scenario's assumptions WITHOUT running the model — the
    approval (elicitation) step. Call this first, show `approval_prompt` to the
    human, and only call agora_run_scenario once they sign off: the values
    judgement stays with the user, and nobody approves one thing while the
    engine runs another (the resolved lever paths returned here are exactly what
    agora_run_scenario will use). No numbers are computed. Returns JSON:
    {disclaimer, geo, scenario, assumptions{levers}, approval_prompt}.
    """
    return _dump(mcp_api.preview_scenario(
        geo=geo, horizon=horizon, labour_share_end=labour_share_end,
        capex_growth=capex_growth, capital_tax=capital_tax, ubi=ubi, ubc=ubc,
        ubc_reinvest=ubc_reinvest, name=name, allow_live=allow_live))


@mcp.tool(name="agora_narrate",
          annotations={"title": "Narrate a gated result via the client's model",
                       **_READ_ONLY})
async def agora_narrate(ctx: Context, geo: str = "DE",
                        preset: Optional[str] = None,
                        scenarios: Optional[List[Dict[str, Any]]] = None,
                        horizon: int = 30, series: Optional[List[str]] = None,
                        reinvest: float = 0.0, allow_live: bool = False) -> str:
    """Run a scenario (or comparison) through the gated engine, then narrate it
    in plain prose using the CLIENT's own model via MCP sampling — AGORA ships
    no model of its own. The numbers stay authoritative (they come from the
    gated engine); the borrowed model only phrases them and is instructed to
    invent nothing and declare no single 'winner'.

    Pass preset='triad'/'ubc' or scenarios=[{...}] (like agora_compare); with
    neither, narrates the plain baseline run. If the client does not support
    sampling, the numeric payload is returned with a `narrative_unavailable`
    note (never an error). Returns the run/compare JSON plus `narrative`.
    """
    if preset or scenarios:
        payload = mcp_api.compare(geo=geo, preset=preset, scenarios=scenarios,
                                  horizon=horizon, series=series,
                                  reinvest=reinvest, allow_live=allow_live)
    else:
        payload = mcp_api.run_scenario(geo=geo, horizon=horizon, series=series,
                                       allow_live=allow_live)
    prompt = mcp_api.narration_prompt(payload)
    try:
        msg = await ctx.session.create_message(
            messages=[types.SamplingMessage(
                role="user",
                content=types.TextContent(type="text", text=prompt))],
            max_tokens=400)
        content = getattr(msg, "content", None)
        payload["narrative"] = getattr(content, "text", str(content))
    except Exception as exc:  # client without sampling capability -> graceful
        payload["narrative_unavailable"] = (
            "This client does not support MCP sampling; numbers returned "
            "without narration (%s)." % type(exc).__name__)
    return _dump(payload)


@mcp.tool(name="agora_policy_frontier",
          annotations={"title": "Compute the policy trade-off frontier",
                       **_READ_ONLY})
def agora_policy_frontier(geo: str = "DE", horizon: int = 30,
                          taus: Optional[List[float]] = None,
                          allow_live: bool = False) -> str:
    """The Phase-4 optimiser as a tool: sweep policy form x capital-tax intensity
    against the AI shock, gate every candidate, and return the Pareto
    (non-dominated) set on five objectives (growth, equality, stability, fiscal,
    resilience). Deliberately returns a MENU, not a winner -- the frontier IS the
    'no single best' answer. `taus` overrides the levy grid. Returns JSON:
    {disclaimer, geo, horizon, objectives[], frontier[], n_frontier, n_dominated,
    n_gated_out, note, data_sources}.
    """
    return _dump(mcp_api.policy_frontier(geo=geo, horizon=horizon, taus=taus,
                                         allow_live=allow_live))


if __name__ == "__main__":
    mcp.run()
