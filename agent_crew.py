"""Phase 5 -- the run-time agent crew over the AGORA MCP tool layer.

Threads a plain-language request through the run-time pipeline from
docs/AGENTIC-BUILD-PLAN.md:

    Scenario(plan) -> approve(elicitation) -> Runner -> Critic(gate)
                   -> Analysis -> Report

Every stage calls the SAME gated tool layer (`mcp_api`) the MCP server exposes,
so nothing bypasses the consistency gate (the Critic is non-negotiable) and the
sandbox/provenance guardrails travel with every result. Pure stdlib and
DETERMINISTIC by default -- a rule-based planner + template reporter -- so the
whole loop runs offline and is testable. The planner and reporter are pluggable
for an LLM (the client's model via MCP sampling, or the local Qwen the scout
uses). No bundled model.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import mcp_api

CREW_SERIES = list(mcp_api.DEFAULT_SERIES) + ["gov_debt_gdp"]

# --------------------------------------------------------------------------- #
# Scenario agent -- plain language -> levers (deterministic, rule-based).
# --------------------------------------------------------------------------- #
_GEO_NAMES = {
    "germany": "DE", "deutschland": "DE", "france": "FR", "slovakia": "SK",
    "slovak": "SK", "italy": "IT", "spain": "ES", "netherlands": "NL",
    "holland": "NL", "poland": "PL", "austria": "AT", "belgium": "BE",
    "bulgaria": "BG", "cyprus": "CY", "czechia": "CZ", "czech": "CZ",
    "denmark": "DK", "estonia": "EE", "greece": "EL", "finland": "FI",
    "croatia": "HR", "hungary": "HU", "ireland": "IE", "lithuania": "LT",
    "luxembourg": "LU", "latvia": "LV", "malta": "MT", "portugal": "PT",
    "romania": "RO", "sweden": "SE", "slovenia": "SI", "euro area": "EA20",
    "eurozone": "EA20", "euro-area": "EA20",
}


def _valid_geos() -> set:
    try:
        return {g["geo"] for g in mcp_api.list_geos()["geos"]}
    except Exception:
        return set(_GEO_NAMES.values())


@dataclass
class CrewPlan:
    geo: str
    mode: str                                   # "single" | "compare"
    preset: Optional[str] = None
    scenarios: List[Dict[str, Any]] = field(default_factory=list)
    levers: Dict[str, Any] = field(default_factory=dict)
    horizon: int = 30
    note: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {"geo": self.geo, "mode": self.mode, "preset": self.preset,
                "scenarios": self.scenarios, "levers": self.levers,
                "horizon": self.horizon, "note": self.note}


def _find_geo(t: str, valid: set) -> str:
    for name, code in _GEO_NAMES.items():
        if name in t and code in valid:
            return code
    for tok in re.findall(r"\b[a-z]{2}\b", t):
        if tok.upper() in valid:
            return tok.upper()
    return "DE"


def _find_tau(t: str) -> Optional[float]:
    m = re.search(r"(\d{1,3})\s*%", t)
    if m:
        return max(0.0, min(1.0, int(m.group(1)) / 100.0))
    m = re.search(r"(?:tau|τ)\s*=?\s*(0?\.\d+)", t)
    if m:
        return max(0.0, min(1.0, float(m.group(1))))
    return None


def plan(request: str, valid: Optional[set] = None) -> CrewPlan:
    """Scenario agent: map a plain-language request to a gated run plan.

    Recognises: a country (name or 2-letter code; default DE), an AI shock
    ('AI shock/shift/automation'), a policy form (UBC / cash UBI), a tax rate
    ('40%', 'tau 0.4'), fund reinvestment ('reinvest 50%'), and comparison intent
    ('compare', ' vs ', 'ubc vs cash', 'triad'). Unknown phrasing degrades to the
    no-shock baseline for the detected country.
    """
    valid = _valid_geos() if valid is None else valid
    t = " " + request.lower().strip() + " "
    geo = _find_geo(t, valid)
    tau = _find_tau(t)
    shock = any(w in t for w in (" ai shock", " ai shift", "automation",
                                 " ai transition", " ai-", " ai ", " a.i"))
    wants_ubc = any(w in t for w in ("ubc", "universal basic capital",
                                     "citizens' fund", "citizens fund",
                                     "sovereign fund", "ownership"))
    wants_cash = any(w in t for w in ("cash ubi", "cash transfer", "basic income",
                                      " ubi", "cash "))
    m = re.search(r"reinvest\w*\s*(?:=|of)?\s*(\d{1,3})\s*%", t)
    reinvest = (int(m.group(1)) / 100.0) if m else 0.0

    shock_levers = {"labour_share_end": 0.30, "capex_growth": 0.06} if shock else {}

    # --- optimiser intent (the Phase-4 frontier as a crew tool) ---
    if any(w in t for w in ("frontier", "pareto", "optimis", "optimiz",
                            "best policy", "best mix", "which policy",
                            "policy mix", "trade-off frontier",
                            "trade off frontier")):
        return CrewPlan(geo=geo, mode="frontier",
                        note="policy trade-off frontier")

    # --- comparison intent ---
    compare = any(w in t for w in (" vs ", " versus ", " against ", "compare"))
    if "ubc vs cash" in t or "cash vs ubc" in t or "pinned" in t \
            or ("ubc" in t and "cash" in t):
        return CrewPlan(geo=geo, mode="compare", preset="ubc",
                        note="pinned UBC-vs-cash experiment")
    if "triad" in t or ("baseline" in t and "settlement" in t):
        return CrewPlan(geo=geo, mode="compare", preset="triad",
                        note="triad: baseline / AI-no-policy / settlement")
    if compare:
        tt = tau if tau is not None else 0.40
        scens = [
            {"name": "AI + Cash UBI", "capital_tax": tt, "ubi": True, **shock_levers},
            {"name": "AI + UBC", "capital_tax": tt, "ubc": True,
             "ubc_reinvest": reinvest, **shock_levers}]
        return CrewPlan(geo=geo, mode="compare", scenarios=scens,
                        note="cash vs UBC at tau=%.2f" % tt)

    # --- single scenario ---
    levers: Dict[str, Any] = dict(shock_levers)
    if wants_ubc:
        levers.update(capital_tax=tau if tau is not None else 0.40, ubc=True,
                      ubc_reinvest=reinvest)
        note = "AI shock + UBC" if shock else "UBC policy"
    elif wants_cash:
        levers.update(capital_tax=tau if tau is not None else 0.40, ubi=True)
        note = "AI shock + cash UBI" if shock else "cash UBI"
    elif tau is not None:
        levers.update(capital_tax=tau)
        note = "capital tax only"
    else:
        note = "AI shock, no policy" if shock else "no-shock baseline"
    return CrewPlan(geo=geo, mode="single", levers=levers, note=note)


# --------------------------------------------------------------------------- #
# Report agent -- deterministic template (no 'winner'; pluggable for an LLM).
# --------------------------------------------------------------------------- #
def _fmt(v: Any) -> str:
    if isinstance(v, (int, float)):
        return f"{v:,.3f}" if abs(v) < 100 else f"{v:,.0f}"
    return str(v)


def template_report(payload: Dict[str, Any]) -> str:
    if payload.get("mode") == "frontier":
        nf, nd = payload.get("n_frontier", 0), payload.get("n_dominated", 0)
        lines = [f"AGORA crew -- policy frontier on {payload.get('geo')} "
                 f"({payload.get('horizon', '?')}y). {nf} non-dominated "
                 f"policies out of {nf + nd}; no single 'best' -- each trades one "
                 f"objective for another."]
        for pt in payload.get("frontier", []):
            lines.append(
                f"  - {pt.get('name')}: GDP {_fmt(pt.get('m_gdp_end'))}, "
                f"Gini {_fmt(pt.get('m_gini'))}, poverty {_fmt(pt.get('m_poverty'))}, "
                f"debt/GDP {_fmt(pt.get('m_debt_gdp'))}.")
        lines.append("  Sandbox, not a forecast; every candidate passed the "
                     "consistency gate. The choice is yours.")
        return "\n".join(lines)
    if payload.get("mode") == "compare" or "runs" in payload:
        lines = [f"AGORA crew -- comparison on {payload.get('geo')} "
                 f"({payload.get('horizon', '?')}y). No single 'winner': the "
                 f"trade-offs are shown, the values judgement stays with you."]
        for r in payload.get("runs", []):
            if not r.get("gate", {}).get("passed"):
                lines.append(f"  - {r['scenario']}: GATE FAILED, numbers withheld.")
                continue
            s = r.get("summary", {})
            lines.append(
                f"  - {r['scenario']}: GDP {_fmt(s.get('gdp_end'))}, "
                f"Gini {_fmt(s.get('gini_personal_end'))}, "
                f"poverty {_fmt(s.get('poverty_rate_end'))}, "
                f"top10 wealth {_fmt(s.get('top10_wealth_share_end'))}.")
        lines.append("  Sandbox, not a forecast; every number passed the "
                     "consistency gate.")
        return "\n".join(lines)
    # single
    if "error" in payload:
        return (f"AGORA crew -- {payload.get('geo')}: run REFUSED. "
                f"{payload['error']}")
    s = payload.get("summary", {})
    g = payload.get("gate", {})
    return (f"AGORA crew -- {payload.get('scenario')} on {payload.get('geo')} "
            f"({len(payload.get('years', []))}y). Gate passed "
            f"(residual {g.get('max_residual', 0):.1e}). End state: "
            f"GDP {_fmt(s.get('gdp_end'))}, Gini {_fmt(s.get('gini_personal_end'))}, "
            f"poverty {_fmt(s.get('poverty_rate_end'))}, "
            f"debt/GDP {_fmt(s.get('gov_debt_gdp_end'))}. "
            f"Sandbox, not a forecast.")


# --------------------------------------------------------------------------- #
# LLM adapters -- borrow a model (the client's via MCP sampling, or the scout's
# local Qwen); AGORA bundles none. Both fall back to the deterministic agents on
# ANY failure, so the crew never hard-depends on a model and the gate always guards.
# --------------------------------------------------------------------------- #
def make_llm_reporter(model_call: Callable[[str], Optional[str]]
                      ) -> Callable[[Dict[str, Any]], str]:
    """Reporter that narrates a gated payload via `model_call(prompt)->str|None`.
    Numbers come from the payload (`mcp_api.narration_prompt`); the model only
    phrases them. Falls back to `template_report` on any failure."""
    def reporter(payload: Dict[str, Any]) -> str:
        try:
            out = model_call(mcp_api.narration_prompt(payload))
            if out and out.strip():
                return out.strip()
        except Exception:
            pass
        return template_report(payload)
    return reporter


_PLANNER_SYSTEM = (
    'You are AGORA\'s scenario planner. Map the request to a JSON plan and output '
    'ONLY JSON, no prose. Schema: {"geo": <2-letter EU code>, "mode": '
    '"single"|"compare"|"frontier", "levers": {"labour_share_end": 0-1 or null, '
    '"capex_growth": 0-1, "capital_tax": 0-1, "ubi": bool, "ubc": bool, '
    '"ubc_reinvest": 0-1}}. The AI shock is labour_share_end=0.30, '
    'capex_growth=0.06. "frontier" = the trade-off menu (no levers). "compare" = '
    'cash UBI vs UBC. Use only the levers in the schema.')


def make_llm_planner(model_call: Callable[[str], Optional[str]],
                     valid: Optional[set] = None
                     ) -> Callable[[str], CrewPlan]:
    """Planner backed by `model_call`. The model proposes a JSON plan; it is
    parsed and VALIDATED (geo in the snapshot set, taus clamped to [0,1],
    ubi/ubc exclusivity) into a CrewPlan. Falls back to the deterministic
    rule-based `plan()` on any failure -- model down, unparseable, or invalid."""
    vg = _valid_geos() if valid is None else valid

    def planner(request: str) -> CrewPlan:
        try:
            raw = model_call(_PLANNER_SYSTEM + "\n\nRequest: " + request)
            m = re.search(r"\{.*\}", raw or "", re.S)
            spec = json.loads(m.group(0))
            geo = str(spec.get("geo", "DE")).upper()
            geo = geo if geo in vg else "DE"
            mode = spec.get("mode", "single")
            if mode == "frontier":
                return CrewPlan(geo=geo, mode="frontier", note="policy frontier (llm)")
            if mode == "compare":
                return CrewPlan(geo=geo, mode="compare", preset="ubc",
                                note="cash vs UBC (llm)")
            lv = spec.get("levers", {}) or {}
            levers: Dict[str, Any] = {}

            def clamp(x):
                return max(0.0, min(1.0, float(x)))
            if lv.get("labour_share_end") is not None:
                levers["labour_share_end"] = clamp(lv["labour_share_end"])
            if lv.get("capex_growth") is not None:
                levers["capex_growth"] = float(lv["capex_growth"])
            if lv.get("capital_tax") is not None:
                levers["capital_tax"] = clamp(lv["capital_tax"])
            if lv.get("ubc"):
                levers["ubc"] = True
            elif lv.get("ubi"):
                levers["ubi"] = True
            if lv.get("ubc_reinvest") is not None:
                levers["ubc_reinvest"] = clamp(lv["ubc_reinvest"])
            return CrewPlan(geo=geo, mode="single", levers=levers, note="llm plan")
        except Exception:
            return plan(request, valid=vg)
    return planner


def qwen_model_call(prompt: str, temperature: float = 0.2,
                    max_tokens: int = 500) -> Optional[str]:
    """Optional local-model adapter: route a prompt to the scout's local Qwen
    (Ollama, OpenAI-compatible). Returns None if the endpoint is down -- the
    adapters read that as 'fall back to deterministic'."""
    try:
        from scout.llm import QwenClient
        c = QwenClient()
        if not c.available():
            return None
        return c.chat([{"role": "user", "content": prompt}],
                      temperature=temperature, max_tokens=max_tokens)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# The crew loop.
# --------------------------------------------------------------------------- #
@dataclass
class CrewResult:
    request: str
    plan: Dict[str, Any]
    assumptions: Optional[Dict[str, Any]]
    approved: bool
    gate_passed: bool
    payload: Dict[str, Any]
    report: str
    stages: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {"request": self.request, "plan": self.plan,
                "assumptions": self.assumptions, "approved": self.approved,
                "gate_passed": self.gate_passed, "report": self.report,
                "stages": self.stages, "payload": self.payload}


def run_crew(request: str, *, horizon: int = 30, allow_live: bool = False,
             approver: Optional[Callable[[Dict[str, Any]], bool]] = None,
             planner: Optional[Callable[[str], CrewPlan]] = None,
             reporter: Optional[Callable[[Dict[str, Any]], str]] = None
             ) -> CrewResult:
    """Run the full run-time crew for one plain-language request.

    approver(preview)->bool is the HUMAN GATE (elicitation): it sees the resolved
    assumptions BEFORE compute and may veto (default: auto-approve). planner and
    reporter default to the deterministic rule-based / template agents and can be
    swapped for LLM-backed ones. Returns a full, traceable transcript. The
    consistency gate (the Critic) is always enforced by mcp_api and cannot be
    turned off here.
    """
    stages: List[str] = []
    p = (planner or plan)(request)
    p.horizon = horizon
    stages.append("scenario: " + p.note)

    # --- approve (elicitation) -- single runs preview their assumptions ---
    assumptions = None
    approved = True
    if p.mode == "single":
        preview = mcp_api.preview_scenario(geo=p.geo, horizon=horizon,
                                           allow_live=allow_live, **p.levers)
        assumptions = preview.get("assumptions")
        stages.append("approve: assumptions resolved for sign-off")
        if approver is not None:
            approved = bool(approver(preview))
    if not approved:
        stages.append("approve: DECLINED by human gate -- nothing run")
        return CrewResult(request, p.as_dict(), assumptions, False, False,
                          {"declined": True}, "Run declined at the approval "
                          "gate; no numbers computed.", stages)

    # --- run (gated) ---
    if p.mode == "frontier":
        payload = mcp_api.policy_frontier(geo=p.geo, horizon=horizon,
                                          allow_live=allow_live)
        payload["mode"] = "frontier"
        gate_passed = (payload.get("n_gated_out", 1) == 0
                       and payload.get("n_frontier", 0) >= 1)
    elif p.mode == "compare":
        payload = (mcp_api.compare(geo=p.geo, preset=p.preset, horizon=horizon,
                                   series=CREW_SERIES, allow_live=allow_live)
                   if p.preset else
                   mcp_api.compare(geo=p.geo, scenarios=p.scenarios,
                                   horizon=horizon, series=CREW_SERIES,
                                   allow_live=allow_live))
        payload["mode"] = "compare"
        gate_passed = bool(payload.get("runs")) and all(
            r.get("gate", {}).get("passed") for r in payload["runs"])
    else:
        payload = mcp_api.run_scenario(geo=p.geo, horizon=horizon,
                                       allow_live=allow_live, series=CREW_SERIES,
                                       name=p.note, **p.levers)
        gate_passed = bool(payload.get("gate", {}).get("passed"))
    stages.append("runner: gated execution")
    stages.append("critic: gate " + ("PASSED" if gate_passed else "FAILED"))

    # --- report ---
    report = (reporter or template_report)(payload)
    stages.append("report: drafted")
    return CrewResult(request, p.as_dict(), assumptions, approved, gate_passed,
                      payload, report, stages)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Run an AI shock with UBC at 40% in Germany"
    res = run_crew(q)
    print("REQUEST:", res.request)
    print("PLAN   :", res.plan["note"], "->", res.plan["geo"], res.plan["mode"])
    print("STAGES :", " | ".join(res.stages))
    print("REPORT :\n" + res.report)
