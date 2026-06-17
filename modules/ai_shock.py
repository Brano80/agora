"""AI-shock driver (Phase 2) - turns interpretable AI / automation parameters
into the scenario lever paths the SFC core consumes.

The docs call for "an AI-shock driver parameterised from Epoch / AI Index / ILO".
The AI shock enters the modelled economy through the two channels the core
represents:
  * the LABOUR SHARE trajectory - automation/AI displaces labour, so the wage
    share of output drifts down (optionally along an S-curve adoption path);
  * the autonomous AI-CAPEX injection growth - the buildout investment boom.

A `Policy` bundles the response levers (capital tax, UBI). The driver composes
an (AIShock, Policy) pair into a Scenario.

All parameters are scenario ASSUMPTIONS, not forecasts - inspectable and
swappable. Sourced anchors are documented; the scout can refine them later.
Empirical anchors (for orientation, not prediction):
  * Labour share: the EU/global wage share fell ~5pp over recent decades
    (Karabarbounis-Neiman; ILO World Employment reports). An aggressive AI
    scenario posits a faster, deeper fall (e.g. toward 0.30).
  * AI investment: Stanford AI Index reports very high (volatile) growth in
    private AI investment; Epoch AI shows training compute growing several-fold
    per year. The capex-growth lever is a macro-investment proxy for that
    acceleration, deliberately conservative versus raw compute growth.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from modules.interface import Scenario, LeverPath
from calibration import SFCParams


@dataclass
class AIShock:
    name: str = "AI shift"
    labour_share_end: Optional[float] = None   # target wage share at horizon; None = hold baseline
    capex_growth: float = 0.06                  # annual growth of the AI-capex injection
    adoption: str = "ramp"                      # 'ramp' (linear) | 'scurve' (logistic)
    # Acemoglu-Restrepo task block: if automation_rate is set, the labour-share
    # path EMERGES from task displacement vs reinstatement instead of an assumed
    # end-point. theta_t = AI-automated task share (starts 0); labour share falls
    # toward ls0*(1 - theta*), theta* = automation/(automation + reinstatement).
    automation_rate: Optional[float] = None     # tasks AI automates per year
    reinstatement_rate: float = 0.02            # new labour tasks created per year
    note: str = ""


@dataclass
class Policy:
    name: str = "no policy"
    capital_tax: float = 0.0
    ubi: bool = False
    ubc: bool = False                           # Universal Basic Capital (sovereign fund)
    ubc_reinvest: float = 0.0                   # fraction of fund profits reinvested
    note: str = ""


def _task_labour_share_path(p: SFCParams, ai: AIShock) -> LeverPath:
    """Acemoglu-Restrepo: labour share emerges from task displacement vs
    reinstatement. theta evolves theta+ = theta + a(1-theta) - r·theta; the wage
    share is ls0·(1-theta). The floor is ls0·(1 - a/(a+r))."""
    a, r = float(ai.automation_rate), float(ai.reinstatement_rate)

    def f(t: int, H: int) -> float:
        theta = 0.0
        for _ in range(t):
            theta = theta + a * (1.0 - theta) - r * theta
            theta = min(max(theta, 0.0), 0.999)
        return p.ls0 * (1.0 - theta)
    return LeverPath(f, "labour share (task displacement)")


def _labour_share_path(p: SFCParams, ai: AIShock) -> LeverPath:
    if ai.automation_rate is not None:
        return _task_labour_share_path(p, ai)
    start = p.ls0
    end = ai.labour_share_end
    if end is None or abs(end - start) < 1e-12:
        return LeverPath(start, "labour share (held)")
    if ai.adoption == "scurve":
        def f(t: int, H: int) -> float:
            if H <= 1:
                return float(end)
            # logistic over the horizon, normalised to hit start at t=0 and end at t=H-1
            k = 10.0 / (H - 1)
            mid = (H - 1) / 2.0
            def L(x):
                return 1.0 / (1.0 + math.exp(-k * (x - mid)))
            lo, hi = L(0), L(H - 1)
            s = (L(t) - lo) / (hi - lo) if hi != lo else (t / (H - 1))
            return start + (end - start) * s
        return LeverPath(f, "labour share (S-curve)")
    return LeverPath.ramp(start, end, "labour share (ramp)")


def to_scenario(p: SFCParams, ai: AIShock, pol: Policy,
                name: Optional[str] = None, horizon: int = 30,
                geo: Optional[str] = None) -> Scenario:
    """Compose an (AIShock, Policy) into a Scenario the SFC core can run."""
    return Scenario(
        name=name or f"{ai.name} + {pol.name}",
        horizon=horizon, geo=geo or p.geo,
        labour_share=_labour_share_path(p, ai),
        ai_capex=LeverPath.grow(p.a_ratio0, ai.capex_growth, "AI capex"),
        gov_ratio=LeverPath(p.g_ratio, "gov / Y0"),
        tax_income=LeverPath(p.theta, "income tax (calibrated)"),
        tax_capital=LeverPath(pol.capital_tax, "capital tax"),
        ubi_on=LeverPath(1.0 if pol.ubi else 0.0, "UBI"),
        ubc_on=LeverPath(1.0 if pol.ubc else 0.0, "UBC"),
        ubc_reinvest=LeverPath(pol.ubc_reinvest, "UBC reinvest"),
        description=(f"AI shock: labour share -> "
                     f"{ai.labour_share_end if ai.labour_share_end is not None else p.ls0:.2f}, "
                     f"capex +{ai.capex_growth*100:.0f}%/yr ({ai.adoption}); "
                     f"policy: capital levy {pol.capital_tax*100:.0f}%, "
                     f"UBI {'on' if pol.ubi else 'off'}, "
                     f"UBC {'on' if pol.ubc else 'off'}."),
    )
