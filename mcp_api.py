"""AGORA over MCP — the tool layer (pure stdlib, fully testable offline).

Layering: this module exposes the orchestrator as plain functions returning
JSON-safe dicts; `mcp_server.py` is a thin FastMCP shim over it. The MCP
guardrails live HERE so no transport can bypass them:

  * CONSISTENCY GATE — every run is gated; a failing run returns an error
    payload with the failing checks and NO series (nothing untrusted leaves).
  * SANDBOX, NOT ORACLE — every payload carries the disclaimer, the resolved
    scenario assumptions (lever paths) and per-series data provenance.

Read-only by design. Snapshot data by default (reproducible offline);
`allow_live=True` enables the live-with-fallback DBnomics path.
"""
from __future__ import annotations

import functools
import glob
import math
import os
from typing import Any, Callable, Dict, List, Optional

from consistency.checks import ConsistencyError
from orchestrator import AgoraOrchestrator, ScenarioRun
from scenarios import (CAPEX_AI_GROWTH, CAPEX_BASE_GROWTH, LS_AI_END,
                       build_custom, make_triad, make_ubc_experiment)
from modules.interface import Scenario
from modules.sfc_core import SFCCore
from modules.distribution import DistributionModule
from modules.input_output import InputOutputModule
from schema.accounts import AGGREGATE_GEOS, SERIES

DISCLAIMER = (
    "AGORA is a policy sandbox, not an oracle: outputs compare internally-"
    "consistent scenarios under the stated, swappable assumptions below — "
    "they are NOT forecasts. Every result passed the stock-flow consistency "
    "gate before being returned.")

DEFAULT_SERIES = ["gdp", "consumption", "investment", "labour_share",
                  "gini_personal", "poverty_rate", "top10_wealth_share"]

_ROOT = os.path.dirname(os.path.abspath(__file__))
_CACHE_DIR = os.path.join(_ROOT, "data", "cache")
_ORCH: Dict[tuple, AgoraOrchestrator] = {}

_CUSTOM_LEVERS = {"labour_share_end", "capex_growth", "capital_tax", "ubi",
                  "ubc", "ubc_reinvest", "adoption", "automation_rate",
                  "reinstatement_rate"}

AI_SHOCK_PRESET = {"labour_share_end": LS_AI_END, "capex_growth": CAPEX_AI_GROWTH}


class ToolError(Exception):
    """User-facing tool failure; message must be actionable."""

    def __init__(self, message: str, extra: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.extra = extra or {}


def _public(fn: Callable) -> Callable:
    """Boundary decorator: ToolError / gate raise -> error payload (never a
    traceback, never ungated series)."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ToolError as e:
            payload = {"error": str(e), "disclaimer": DISCLAIMER}
            payload.update(e.extra)
            return payload
        except ConsistencyError as e:
            # strict-mode gate raise: same refusal contract as _require_gate
            return {"error": "Consistency gate FAILED — result withheld "
                             f"(accounting leak): {e}",
                    "gate": {"passed": False},
                    "disclaimer": DISCLAIMER}
    return wrapper


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _known_geos() -> List[str]:
    out = []
    for p in sorted(glob.glob(os.path.join(_CACHE_DIR, "*_baseline_*.json"))):
        out.append(os.path.basename(p).split("_baseline_")[0].upper())
    return out


def _orchestrator(geo: str = "DE", year: int = 2019, allow_live: bool = False,
                  fiscal_reaction: float = 0.0,
                  debt_target: Optional[float] = None,
                  i_rate: Optional[float] = None,
                  capital_tax_share: float = 0.0) -> AgoraOrchestrator:
    geo = (geo or "DE").upper()
    known = _known_geos()
    if geo not in known:
        raise ToolError(
            f"Unknown geo '{geo}'. Available snapshot geos: {', '.join(known)}. "
            "New EU members can be added with scripts/build_snapshot.py.")
    fiscal = (float(fiscal_reaction), debt_target, i_rate,
              float(capital_tax_share))
    default_fiscal = fiscal == (0.0, None, None, 0.0)
    key = (geo, year, bool(allow_live))
    if default_fiscal and key in _ORCH:
        return _ORCH[key]
    orch = AgoraOrchestrator(geo=geo, year=year, allow_live=allow_live,
                             fiscal_reaction=fiscal[0], debt_target=debt_target,
                             i_rate=i_rate, capital_tax_share=fiscal[3])
    orch.load_data()
    if default_fiscal:
        _ORCH[key] = orch
    return orch


def _round(v: Any) -> Any:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, 1) if abs(f) >= 1000 else round(f, 6)


def _gate(run: ScenarioRun) -> Dict[str, Any]:
    failures = []
    for rep in run.reports:
        for c in rep.failures():
            failures.append({"year": rep.year, "check": c.name,
                             "max_residual": _round(c.max_residual)})
    return {"passed": run.consistent,
            "max_residual": float(f"{run.max_residual:.3e}"),
            "reports": len(run.reports), "failures": failures}


def _require_gate(run: ScenarioRun) -> Dict[str, Any]:
    gate = _gate(run)
    if not gate["passed"]:
        raise ToolError(
            f"Consistency gate FAILED for scenario '{run.scenario}' — result "
            "withheld (accounting leak; nothing untrusted leaves the sandbox). "
            "Failing checks attached under 'gate'.",
            extra={"gate": gate, "scenario": run.scenario})
    return gate


def _assumptions(scenario: Scenario) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    snap = scenario.snapshot()
    for name, path in snap.items():
        start, end = path[0], path[-1]
        constant = all(abs(v - start) < 1e-12 for v in path)
        out[name] = {"start": _round(start), "end": _round(end),
                     "path": "constant" if constant else "varies"}
    return {"levers": out, "description": scenario.description,
            "note": ("Macro-layer assumption set, fully resolved. Module-level "
                     "defaults (e.g. the distribution beta) are documented in "
                     "docs/MANIFESTO.md and swappable in code.")}


def _sources(orch: AgoraOrchestrator) -> Dict[str, List[str]]:
    by_source: Dict[str, List[str]] = {}
    for code, src in sorted(orch._sources.items()):
        by_source.setdefault(str(src), []).append(code)
    by_source["note"] = ["call agora_get_series(code) for provider, dataset "
                         "dimensions and source URL"]
    return by_source


def _available_reported(run: ScenarioRun) -> List[str]:
    names: set = set()
    for res in run.results.values():
        if res.periods:
            names.update(res.periods[0].reported.keys())
    return sorted(names)


def _series(run: ScenarioRun, names: List[str]) -> Dict[str, Any]:
    found: Dict[str, List[Any]] = {}
    missing: List[str] = []
    for name in names:
        vals = None
        for res in run.results.values():
            if res.periods and name in res.periods[0].reported:
                vals = [_round(v) for v in res.series(name)]
                break
        if vals is None:
            missing.append(name)
        else:
            found[name] = vals
    out: Dict[str, Any] = {"series": found}
    if missing:
        out["series_not_found"] = {
            "requested": missing,
            "available": _available_reported(run)}
    return out


def _summary(series: Dict[str, List[Any]]) -> Dict[str, Any]:
    return {f"{k}_end": v[-1] for k, v in series.items() if v}


def _run_payload(orch: AgoraOrchestrator, run: ScenarioRun,
                 names: List[str]) -> Dict[str, Any]:
    gate = _require_gate(run)
    ser = _series(run, names)
    payload = {"disclaimer": DISCLAIMER, "geo": orch.geo,
               "base_year": orch.year, "scenario": run.scenario,
               "gate": gate, "years": run.result.years(),
               "summary": _summary(ser["series"])}
    payload.update(ser)
    return payload


def _validate_levers(spec: Dict[str, Any]) -> Dict[str, Any]:
    unknown = set(spec) - _CUSTOM_LEVERS - {"name"}
    if unknown:
        raise ToolError(
            f"Unknown scenario lever(s): {', '.join(sorted(unknown))}. "
            f"Allowed: {', '.join(sorted(_CUSTOM_LEVERS))} (plus 'name').")
    if spec.get("ubi") and spec.get("ubc"):
        raise ToolError("A scenario cannot set both ubi and ubc — they are "
                        "alternative forms of the same capital levy. Run two "
                        "scenarios (or compare with preset='ubc').")
    ct = float(spec.get("capital_tax", 0.0) or 0.0)
    if not 0.0 <= ct <= 1.0:
        raise ToolError("capital_tax must be in [0, 1] (a rate on distributed "
                        "profits).")
    rv = float(spec.get("ubc_reinvest", 0.0) or 0.0)
    if not 0.0 <= rv <= 1.0:
        raise ToolError("ubc_reinvest must be in [0, 1] (fraction of the fund's "
                        "profit share reinvested into capex).")
    return spec


def _check_horizon(horizon: int) -> int:
    horizon = int(horizon)
    if not 2 <= horizon <= 100:
        raise ToolError("horizon must be between 2 and 100 periods (years).")
    return horizon


# --------------------------------------------------------------------------- #
# Public tools (wrapped by mcp_server.py)
# --------------------------------------------------------------------------- #
@_public
def run_scenario(geo: str = "DE", horizon: int = 30,
                 labour_share_end: Optional[float] = None,
                 capex_growth: float = CAPEX_BASE_GROWTH,
                 capital_tax: float = 0.0, ubi: bool = False, ubc: bool = False,
                 ubc_reinvest: float = 0.0, adoption: str = "ramp",
                 automation_rate: Optional[float] = None,
                 reinstatement_rate: float = 0.02,
                 series: Optional[List[str]] = None,
                 name: Optional[str] = None, allow_live: bool = False,
                 fiscal_reaction: float = 0.0,
                 debt_target: Optional[float] = None,
                 i_rate: Optional[float] = None,
                 capital_tax_share: float = 0.0,
                 year: int = 2019) -> Dict[str, Any]:
    """Run ONE gated scenario; defaults = the no-shock baseline.

    AI-shock preset: labour_share_end=0.30, capex_growth=0.06 (see
    mcp_api.AI_SHOCK_PRESET). Policy levers: capital_tax (+ ubi=True for cash
    redistribution, or ubc=True for the citizens' capital fund with optional
    ubc_reinvest). Fiscal block (Phase 6, default OFF): fiscal_reaction,
    debt_target, i_rate, capital_tax_share.
    """
    horizon = _check_horizon(horizon)
    spec = _validate_levers({"labour_share_end": labour_share_end,
                             "capex_growth": capex_growth,
                             "capital_tax": capital_tax, "ubi": ubi, "ubc": ubc,
                             "ubc_reinvest": ubc_reinvest, "adoption": adoption,
                             "automation_rate": automation_rate,
                             "reinstatement_rate": reinstatement_rate})
    orch = _orchestrator(geo=geo, year=year, allow_live=allow_live,
                         fiscal_reaction=fiscal_reaction,
                         debt_target=debt_target, i_rate=i_rate,
                         capital_tax_share=capital_tax_share)
    p = orch.params()
    scen = build_custom(p, horizon=horizon, name=name or "Custom", **spec)
    run = orch.run_scenario(scen)
    payload = _run_payload(orch, run, series or DEFAULT_SERIES)
    payload["assumptions"] = _assumptions(scen)
    payload["data_sources"] = _sources(orch)
    if fiscal_reaction or debt_target is not None or i_rate is not None \
            or capital_tax_share:
        payload["fiscal_block"] = {"fiscal_reaction": fiscal_reaction,
                                   "debt_target": debt_target, "i_rate": i_rate,
                                   "capital_tax_share": capital_tax_share}
    return payload


@_public
def compare(geo: str = "DE", preset: Optional[str] = None,
            scenarios: Optional[List[Dict[str, Any]]] = None,
            horizon: int = 30, series: Optional[List[str]] = None,
            reinvest: float = 0.0, allow_live: bool = False,
            year: int = 2019) -> Dict[str, Any]:
    """Run several scenarios side by side (all gated).

    Either preset='triad' (Baseline / AI-no-policy / Abundance Settlement) or
    preset='ubc' (the pinned 4-arm cash-UBI-vs-UBC experiment; `reinvest` sets
    the fund's reinvestment fraction), or scenarios=[{name, levers...}, ...]
    with the run_scenario lever names.
    """
    horizon = _check_horizon(horizon)
    orch = _orchestrator(geo=geo, year=year, allow_live=allow_live)
    p = orch.params()
    if preset:
        kind = preset.strip().lower()
        if kind == "triad":
            scens = make_triad(p, horizon=horizon)
        elif kind == "ubc":
            scens = make_ubc_experiment(p, horizon=horizon,
                                        reinvest=float(reinvest))
        else:
            raise ToolError(f"Unknown preset '{preset}'. Use 'triad', 'ubc', "
                            "or pass scenarios=[{...}, ...].")
    elif scenarios:
        scens = []
        for i, spec in enumerate(scenarios):
            if not isinstance(spec, dict):
                raise ToolError("Each scenario must be an object of levers, "
                                "e.g. {'name': 'AI + UBC', 'labour_share_end': "
                                "0.3, 'capital_tax': 0.4, 'ubc': true}.")
            spec = _validate_levers(dict(spec))
            nm = spec.pop("name", f"Scenario {i + 1}")
            scens.append(build_custom(p, horizon=horizon, name=nm, **spec))
    else:
        raise ToolError("Nothing to compare: pass preset='triad'/'ubc' or "
                        "scenarios=[{...}, ...].")
    names = series or DEFAULT_SERIES
    runs: List[Dict[str, Any]] = []
    years: List[int] = []
    for scen in scens:
        try:
            run = orch.run_scenario(scen)
            gate = _gate(run)
        except ConsistencyError as e:
            runs.append({"scenario": scen.name,
                         "gate": {"passed": False},
                         "error": f"Consistency gate FAILED — series withheld "
                                  f"for this arm: {e}"})
            continue
        entry: Dict[str, Any] = {"scenario": run.scenario, "gate": gate,
                                 "assumptions": _assumptions(scen)}
        if gate["passed"]:
            ser = _series(run, names)
            entry.update(ser)
            entry["summary"] = _summary(ser["series"])
            years = run.result.years()
        else:
            entry["error"] = ("Consistency gate FAILED — series withheld for "
                              "this arm.")
        runs.append(entry)
    return {"disclaimer": DISCLAIMER, "geo": orch.geo, "base_year": orch.year,
            "horizon": horizon, "years": years,
            "data_sources": _sources(orch), "runs": runs}


@_public
def list_modules() -> Dict[str, Any]:
    """The pluggable module chain: names + declared schema inputs/outputs."""
    mods = [SFCCore(base_year=2019), DistributionModule(base_year=2019),
            InputOutputModule(base_year=2019)]
    return {"disclaimer": DISCLAIMER,
            "modules": [{"name": m.name,
                         "doc": (m.__class__.__doc__ or "").strip().split("\n")[0],
                         "inputs": m.declares_inputs(),
                         "outputs": m.declares_outputs()} for m in mods],
            "note": ("Modules run in this order; each receives the upstream "
                     "results as context and every emitted matrix passes the "
                     "consistency gate.")}


@_public
def get_series(code: Optional[str] = None) -> Dict[str, Any]:
    """Schema series catalogue. Without `code`: the full compact list. With
    `code`: provider, dataset, dimensions, source URL and live/snapshot mode."""
    if code is None:
        return {"disclaimer": DISCLAIMER,
                "series": [{"code": s.code, "label": s.label, "unit": s.unit,
                            "provider": s.provider, "live": s.live}
                           for s in SERIES.values()]}
    key = code.strip()
    if key not in SERIES:
        raise ToolError(f"Unknown series '{code}'. Known codes: "
                        f"{', '.join(sorted(SERIES))}.")
    s = SERIES[key]
    return {"disclaimer": DISCLAIMER, "code": s.code, "label": s.label,
            "unit": s.unit, "provider": s.provider, "dataset": s.dataset,
            "dimensions": s.dimensions, "source_url": s.source_url,
            "note": s.note, "live": s.live, "geo_dim": s.geo_dim,
            "scale": s.scale}


@_public
def list_geos() -> Dict[str, Any]:
    """Snapshot countries available to run (EU members + aggregates)."""
    geos = []
    for g in _known_geos():
        geos.append({"geo": g, "aggregate": g in AGGREGATE_GEOS,
                     "io_matrix": os.path.exists(
                         os.path.join(_CACHE_DIR, f"io_{g.lower()}.json"))})
    return {"disclaimer": DISCLAIMER, "geos": geos,
            "note": ("Aggregates (EA20/EU27) are valid standalone geos but "
                     "never bloc members. io_matrix=True means a real Eurostat "
                     "FIGARO input-output matrix is cached for the sectoral "
                     "module.")}


@_public
def validate_baseline(geo: str = "DE", allow_live: bool = False,
                      year: int = 2019) -> Dict[str, Any]:
    """'Validate before trusting': does the calibrated baseline reproduce the
    observed national accounts? Returns the per-metric scorecard + gate."""
    orch = _orchestrator(geo=geo, year=year, allow_live=allow_live)
    rows, run = orch.validate_baseline()
    gate = _require_gate(run)
    return {"disclaimer": DISCLAIMER, "geo": orch.geo, "base_year": orch.year,
            "gate": gate, "all_ok": all(r.ok for r in rows),
            "rows": [{"metric": r.metric, "target": _round(r.target),
                      "model": _round(r.model),
                      "rel_error": _round(r.rel_error), "ok": r.ok}
                     for r in rows],
            "data_sources": _sources(orch)}
