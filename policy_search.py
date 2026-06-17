"""Phase 4 — multi-objective policy search & the trade-off (Pareto) frontier.

The principle (CLAUDE.md): there is NO single 'best' policy. AGORA reports the
multi-objective trade-off and leaves the values judgement to the user. This
layer sweeps the POLICY space against a fixed AI shock, runs every candidate
through the full module chain + consistency gate, scores five objectives, and
returns the non-dominated (Pareto-optimal) set.

Decision space (policy only; the shock is held fixed so the question is
"given the AI transition, which policy MIX is on the frontier?"):
  * form          — no policy | cash UBI | Universal Basic Capital
  * capital_tax τ — the public claim on capital income (shared intensity lever)

Objectives (each expressed so HIGHER = better, for clean dominance):
  * growth      — end-horizon GDP
  * equality    — −(personal Gini, end)
  * stability   — −(stdev of YoY GDP growth)         [lower volatility better]
  * fiscal      — −(government debt / GDP, end)       [lower debt better]
  * resilience  — −(at-risk-of-poverty rate, end)     [less poverty better]

Every candidate is gated; only consistency-passing points are ranked. Pure
stdlib. The orchestrator exposes `run_policy_search`; the dashboard renders the
frontier.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import pstdev
from typing import Dict, List, Optional, Tuple

from calibration import SFCParams
from scenarios import build_custom, LS_AI_END, CAPEX_AI_GROWTH

# objective key -> (human label, the raw reported metric it derives from)
OBJECTIVES: List[Tuple[str, str]] = [
    ("growth", "GDP (end, MEUR)"),
    ("equality", "Equality (1 − Gini)"),
    ("stability", "Stability (−growth volatility)"),
    ("fiscal", "Fiscal (−debt/GDP)"),
    ("resilience", "Resilience (−poverty)"),
]
DEFAULT_TAUS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]


@dataclass
class PolicyPoint:
    form: str                       # "none" | "cash_ubi" | "ubc"
    capital_tax: float
    name: str
    consistent: bool
    max_residual: float
    metrics: Dict[str, float] = field(default_factory=dict)      # raw, readable
    objectives: Dict[str, float] = field(default_factory=dict)   # higher = better
    on_frontier: bool = False

    def as_dict(self) -> Dict[str, object]:
        return {"form": self.form, "capital_tax": self.capital_tax,
                "name": self.name, "consistent": self.consistent,
                "on_frontier": self.on_frontier,
                "max_residual": self.max_residual,
                **{f"m_{k}": v for k, v in self.metrics.items()},
                **{f"o_{k}": v for k, v in self.objectives.items()}}


def _growth_volatility(gdp: List[float]) -> float:
    g = [(gdp[i] / gdp[i - 1] - 1.0) for i in range(1, len(gdp)) if gdp[i - 1]]
    return pstdev(g) if len(g) > 1 else 0.0


def _score(run) -> Tuple[Dict[str, float], Dict[str, float]]:
    macro = run.result
    gdp = [p.reported["gdp"] for p in macro.periods]
    end = macro.periods[-1].reported
    gini = (run.dist.periods[-1].reported["gini_personal"]
            if run.dist is not None else end["gini"])
    poverty = (run.dist.periods[-1].reported["poverty_rate"]
               if run.dist is not None else 0.0)
    vol = _growth_volatility(gdp)
    debt = end["gov_debt_gdp"]
    metrics = {"gdp_end": gdp[-1], "gini": gini, "growth_vol": vol,
               "debt_gdp": debt, "poverty": poverty,
               "swf_share": end.get("swf_share", 0.0)}
    objectives = {"growth": gdp[-1], "equality": -gini, "stability": -vol,
                  "fiscal": -debt, "resilience": -poverty}
    return metrics, objectives


def _dominates(a: Dict[str, float], b: Dict[str, float], eps: float = 1e-9) -> bool:
    """a Pareto-dominates b: >= on every objective and strictly > on one."""
    ge_all = all(a[k] >= b[k] - eps for k, _ in OBJECTIVES)
    gt_any = any(a[k] > b[k] + eps for k, _ in OBJECTIVES)
    return ge_all and gt_any


def pareto_front(points: List[PolicyPoint]) -> List[PolicyPoint]:
    """Mark and return the non-dominated consistent points."""
    cand = [p for p in points if p.consistent]
    for p in cand:
        p.on_frontier = not any(
            _dominates(q.objectives, p.objectives) for q in cand if q is not p)
    return [p for p in cand if p.on_frontier]


def search_policies(run_scenario, p: SFCParams, taus: Optional[List[float]] = None,
                    horizon: int = 30) -> List[PolicyPoint]:
    """Evaluate the policy grid. `run_scenario(scenario) -> ScenarioRun` is the
    gated runner (the orchestrator). Returns ALL points (frontier flagged)."""
    taus = DEFAULT_TAUS if taus is None else taus
    plans: List[Tuple[str, float, dict, str]] = [
        ("none", 0.0, dict(ubi=False, ubc=False), "No policy")]
    for tau in taus:
        if tau <= 0:
            continue
        plans.append(("cash_ubi", tau, dict(ubi=True, ubc=False),
                      f"Cash UBI τ={int(tau*100)}%"))
        plans.append(("ubc", tau, dict(ubi=False, ubc=True),
                      f"UBC τ={int(tau*100)}%"))

    points: List[PolicyPoint] = []
    for form, tau, kw, name in plans:
        scen = build_custom(p, labour_share_end=LS_AI_END,
                            capex_growth=CAPEX_AI_GROWTH, capital_tax=tau,
                            horizon=horizon, name=name, **kw)
        run = run_scenario(scen)
        metrics, objectives = _score(run)
        points.append(PolicyPoint(
            form=form, capital_tax=tau, name=name,
            consistent=run.consistent, max_residual=run.max_residual,
            metrics=metrics, objectives=objectives))
    pareto_front(points)                       # sets on_frontier in place
    return points
