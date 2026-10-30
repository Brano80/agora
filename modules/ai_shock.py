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

# Phase 7 C: AI's contribution to annual productivity growth while it is being
# adopted. OECD (Filippucci, Gal & Schief 2024, "Miracle or Myth?", OECD AI
# Papers No. 29): 0.25-0.6 pp/yr of TFP growth in the US over the next decade,
# "somewhat lower" elsewhere -> 0.3 pp/yr for Europe. Acemoglu (2024, "The
# Simple Macroeconomics of AI") is far lower (~0.07 pp/yr). The total LEVEL gain
# is a decade of that growth, phased in with adoption (the labour-share path).
AI_PRODUCTIVITY = 0.003
AI_PRODUCTIVITY_YEARS = 10


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
    ai_productivity_gain: float = AI_PRODUCTIVITY   # pp/yr of productivity growth while adopting
    ai_productivity_years: int = AI_PRODUCTIVITY_YEARS
    note: str = ""


@dataclass
class Policy:
    name: str = "no policy"
    capital_tax: float = 0.0
    ubi: bool = False
    ubc: bool = False                           # Universal Basic Capital (sovereign fund)
    ubc_reinvest: float = 0.0                   # fraction of fund profits reinvested
    source_levy: float = 0.0                    # Phase 7 D: levy on AI fees paid abroad
    fund_payout: float = 0.0                    # Phase 7 E: fund's POMV draw (0 = reinvest rule)
    # Phase 7 E2 proposal levers (a float, a per-year list, or a LeverPath)
    fund_seed: object = 0.0
    fund_seed_eur: object = 0.0                 # MEUR, current euros
    ai_equity_stake: object = 0.0
    ai_stake_payout: object = 0.05
    pledge_share: object = 0.0
    broad_tax: object = 0.0
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


def _ai_productivity_path(p: SFCParams, ai: AIShock, ls_path: LeverPath) -> LeverPath:
    """Capacity multiplier (1 + g)^(years * adoption), adoption = how far the
    labour share has travelled toward its end point (0 with no AI shift)."""
    g, years = float(ai.ai_productivity_gain), float(ai.ai_productivity_years)
    if g == 0.0:
        return LeverPath(1.0, "AI productivity (off)")

    def f(t: int, H: int) -> float:
        drop = p.ls0 - ls_path.at(H - 1, H)
        if drop <= 1e-9:
            return 1.0
        s = min(max((p.ls0 - ls_path.at(t, H)) / drop, 0.0), 1.0)
        return (1.0 + g) ** (years * s)
    return LeverPath(f, "AI productivity (level, phased with adoption)")


def _lever(v, label: str) -> LeverPath:
    return v if isinstance(v, LeverPath) else LeverPath(v, label)


def to_scenario(p: SFCParams, ai: AIShock, pol: Policy,
                name: Optional[str] = None, horizon: int = 30,
                geo: Optional[str] = None) -> Scenario:
    """Compose an (AIShock, Policy) into a Scenario the SFC core can run."""
    ls_path = _labour_share_path(p, ai)
    return Scenario(
        name=name or f"{ai.name} + {pol.name}",
        horizon=horizon, geo=geo or p.geo,
        labour_share=ls_path,
        ai_productivity=_ai_productivity_path(p, ai, ls_path),
        ai_capex=LeverPath.grow(p.a_ratio0, ai.capex_growth, "AI capex"),
        gov_ratio=LeverPath(p.g_ratio, "gov / Y0"),
        tax_income=LeverPath(p.theta, "income tax (calibrated)"),
        tax_capital=LeverPath(pol.capital_tax, "capital tax"),
        ubi_on=LeverPath(1.0 if pol.ubi else 0.0, "UBI"),
        ubc_on=LeverPath(1.0 if pol.ubc else 0.0, "UBC"),
        ubc_reinvest=LeverPath(pol.ubc_reinvest, "UBC reinvest"),
        source_levy=LeverPath(pol.source_levy, "source levy on AI fees abroad"),
        fund_payout=LeverPath(pol.fund_payout, "citizens' fund POMV payout"),
        fund_seed=_lever(pol.fund_seed, "fund seed (share of GDP)"),
        fund_seed_eur=_lever(pol.fund_seed_eur, "fund seed (MEUR)"),
        ai_equity_stake=_lever(pol.ai_equity_stake, "fund stake in domestic AI firms"),
        ai_stake_payout=_lever(pol.ai_stake_payout, "dividend on the AI stake"),
        pledge_share=_lever(pol.pledge_share, "AI rent returned by pledges"),
        broad_tax=_lever(pol.broad_tax, "flat tax on all income for a UBI"),
        description=(f"AI shock: labour share -> "
                     f"{ai.labour_share_end if ai.labour_share_end is not None else p.ls0:.2f}, "
                     f"capex +{ai.capex_growth*100:.0f}%/yr ({ai.adoption}); "
                     f"policy: capital levy {pol.capital_tax*100:.0f}%, "
                     f"UBI {'on' if pol.ubi else 'off'}, "
                     f"UBC {'on' if pol.ubc else 'off'}."),
    )
