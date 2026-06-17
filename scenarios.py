"""The Phase-1 scenario triad + a custom-scenario builder, all composed through
the Phase-2 AI-shock driver so there is a single principled source of truth.

  1. Baseline                       — no AI shift; labour share held; slow capex.
  2. AI shift, no policy            — capex boom + labour share collapses; no
                                      redistribution (the 'Great Decoupling').
  3. AI shift + Abundance Settlement — same shock + capital tax recycled as UBI.

Levers are expressed as ratios of baseline GDP (country-agnostic); the SFC core
multiplies them by the calibrated Y0.
"""
from __future__ import annotations

from typing import List, Optional

from calibration import SFCParams
from modules.interface import Scenario
from modules.ai_shock import AIShock, Policy, to_scenario

# scenario shock constants (inspectable / swappable; consumed by the driver)
LS_AI_END = 0.30           # labour share collapses toward 30% under the AI shift
CAPEX_BASE_GROWTH = 0.015  # baseline investment growth
CAPEX_AI_GROWTH = 0.06     # AI capex boom growth
CAPITAL_TAX = 0.40         # settlement: capital/profit tax rate
LABELS = [
    "Baseline",
    "AI shift, no policy",
    "AI shift + Abundance Settlement",
]


def make_triad(p: SFCParams, horizon: int = 30) -> List[Scenario]:
    baseline = to_scenario(
        p, AIShock("Baseline", labour_share_end=None, capex_growth=CAPEX_BASE_GROWTH),
        Policy("baseline", capital_tax=0.0, ubi=False),
        name=LABELS[0], horizon=horizon)
    ai_no_policy = to_scenario(
        p, AIShock("AI shift", labour_share_end=LS_AI_END, capex_growth=CAPEX_AI_GROWTH),
        Policy("no policy", capital_tax=0.0, ubi=False),
        name=LABELS[1], horizon=horizon)
    settlement = to_scenario(
        p, AIShock("AI shift", labour_share_end=LS_AI_END, capex_growth=CAPEX_AI_GROWTH),
        Policy("Abundance Settlement", capital_tax=CAPITAL_TAX, ubi=True),
        name=LABELS[2], horizon=horizon)
    return [baseline, ai_no_policy, settlement]


def build_custom(p: SFCParams, *, labour_share_end: Optional[float] = None,
                 capex_growth: float = CAPEX_AI_GROWTH, capital_tax: float = 0.0,
                 ubi: bool = False, ubc: bool = False,
                 ubc_reinvest: float = 0.0, adoption: str = "ramp",
                 automation_rate: Optional[float] = None,
                 reinstatement_rate: float = 0.02,
                 horizon: int = 30, name: str = "Custom") -> Scenario:
    """Build a bespoke scenario from AI-shock + policy parameters (scenario
    builder). `labour_share_end=None` holds the baseline labour share."""
    return to_scenario(
        p,
        AIShock("AI shift", labour_share_end=labour_share_end,
                capex_growth=capex_growth, adoption=adoption,
                automation_rate=automation_rate,
                reinstatement_rate=reinstatement_rate),
        Policy("custom", capital_tax=capital_tax, ubi=ubi, ubc=ubc,
               ubc_reinvest=ubc_reinvest),
        name=name, horizon=horizon)


# --------------------------------------------------------------------------- #
# THE PINNED EXPERIMENT — Universal Basic Capital vs cash UBI (MANIFESTO Q1).
# Both policy arms face the SAME AI shock and apply the SAME intensity lever tau
# (= CAPITAL_TAX) on capital income; they differ ONLY in form:
#   * Cash UBI: tau*FP redistributed as an equal per-capita cash transfer (flow).
#   * UBC:      an equal-valued claim tau*FP converted in kind each year into a
#               citizens' capital endowment (sovereign_fund) whose profit share
#               is paid out per capita (stock). The endowment compounds.
# Equal-cost by construction (identical government deficit path); the direct
# test of the flow-vs-stock thesis.
# --------------------------------------------------------------------------- #
UBC_LABELS = [
    "Baseline",
    "AI shift, no policy",
    "AI + Cash UBI",
    "AI + Universal Basic Capital",
]


def make_ubc_experiment(p: SFCParams, horizon: int = 30,
                        reinvest: float = 0.0) -> List[Scenario]:
    """The four arms of the pinned UBC-vs-cash-UBI experiment (shared shock).
    `reinvest` sets the UBC fund's profit-reinvestment fraction (C1 closure: the
    fund sustains capex as owners are diluted); 0.0 = the legacy pay-out-all arm."""
    shock = dict(labour_share_end=LS_AI_END, capex_growth=CAPEX_AI_GROWTH)
    baseline = to_scenario(
        p, AIShock("Baseline", labour_share_end=None, capex_growth=CAPEX_BASE_GROWTH),
        Policy("baseline"), name=UBC_LABELS[0], horizon=horizon)
    no_policy = to_scenario(
        p, AIShock("AI shift", **shock),
        Policy("no policy"), name=UBC_LABELS[1], horizon=horizon)
    cash_ubi = to_scenario(
        p, AIShock("AI shift", **shock),
        Policy("Cash UBI", capital_tax=CAPITAL_TAX, ubi=True),
        name=UBC_LABELS[2], horizon=horizon)
    ubc = to_scenario(
        p, AIShock("AI shift", **shock),
        Policy("UBC", capital_tax=CAPITAL_TAX, ubc=True, ubc_reinvest=reinvest),
        name=UBC_LABELS[3], horizon=horizon)
    return [baseline, no_policy, cash_ubi, ubc]
