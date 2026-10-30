"""The library of real 2026 proposals (Phase 7 step E2).

Each proposal is mapped onto the engine's levers with its sourced parameters,
and every one faces the SAME AI shift (labour share to 30%, 70% of the AI rent
earned abroad) from the same policy start (2020), so they can be compared
like for like. Real-world dates are recorded; the escalator of the voluntary
pledge uses the real pledge date.

  stock_levy     One-time stock levy (Sanders, AI Sovereign Wealth Fund Act,
                 June 2026): 50% of the shares of firms with >= $200M of AI
                 sales, once; the fund pays a 5% annual dividend and the gains
                 fund public goods. Here: the fund owns half of the DOMESTIC AI
                 firms; it cannot reach the rent earned by foreign providers.
  pledge         Voluntary corporate pledge (Anthropic Public Benefit Fund,
                 19 Oct 2026): 5% of equity plus 2% per 50% rise in valuation,
                 at the board's discretion; uses unspecified. BEST CASE,
                 labelled an assumption: every foreign provider pledges alike
                 and pays out where the rent is earned.
  debt_fund      Borrowing-financed citizens' fund (UK Citizens' Wealth Fund
                 proposal: ~GBP 700bn in ten years ~ 30% of GDP; Norway GPFG 3%
                 / Alaska 5% payout rules): the government borrows 3% of GDP a
                 year for ten years; the fund buys world equity and pays out 3%
                 of its value a year.
  child_accounts Child accounts (German Fruehstart-Rente, passed by the
                 Bundestag 16 Oct 2026: EUR 10 a month per child aged 6-17 from
                 2027, invested until retirement; US Trump Accounts: $1,000 per
                 newborn 2025-28): paid into accounts invested in world equity,
                 nothing paid out within the horizon.
  source_levy    Levy on AI licence and cloud fees paid abroad, at the rate of
                 most EU digital services taxes (3%; FR, IT, ES 3%, AT 5%);
                 revenue to the budget. 90% is passed on (step D).
  broad_ubi      Cash UBI on a broad base: a flat tax on all income, paid back
                 as an equal payment, raising what the 40% capital levy raises
                 on 2019 incomes.
  cash_ubi_40    Benchmark (the AGORA experiment): 40% capital-income levy paid
                 back as a cash UBI.
  ubc_40         Benchmark: the same 40% claim taken in shares at market value
                 into a citizens' fund paying 3% of its value a year.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import mean
from typing import Callable, Dict, List, Optional

from calibration import SFCParams
from modules.interface import LeverPath, Scenario
from scenarios import CAPITAL_TAX, LS_AI_END, PINNED_FUND_PAYOUT, build_custom

POLICY_START_YEAR = 2020
SANDERS_STAKE = 0.50             # share of covered AI firms' stock, once
SANDERS_DIVIDEND = 0.05          # annual dividend, share of the fund's value
PLEDGE_BASE = 0.05               # Anthropic PBF: 5% of equity
PLEDGE_STEP = 0.02               # +2% per 50% valuation rise (board discretion)
PLEDGE_YEAR = 2026
DEBT_FUND_SEED = 0.03            # share of GDP a year
DEBT_FUND_YEARS = 10
DEBT_FUND_PAYOUT = PINNED_FUND_PAYOUT   # 3%, Norway's rule
CHILD_EUR_YEAR = 120.0           # EUR 10 a month
CHILD_SHARE = 0.11               # children aged 6-17, ~11% of the EU population
CHILD_START_YEAR = 2027
SOURCE_LEVY_RATE = 0.03          # most EU digital services taxes


@dataclass
class Proposal:
    key: str
    name: str
    source: str
    build: Callable[[SFCParams, int], Scenario]
    note: str = ""


def _years(p: SFCParams, horizon: int, start: int, stop: Optional[int] = None,
           value: float = 1.0) -> List[float]:
    return [value if (p.base_year + t >= start and (stop is None or p.base_year + t < stop))
            else 0.0 for t in range(horizon)]


def _ai(p, horizon, name, **kw) -> Scenario:
    return build_custom(p, labour_share_end=LS_AI_END, horizon=horizon, name=name, **kw)


def _pledge_path(p: SFCParams, horizon: int) -> List[float]:
    """5% + 2% per 50% rise of the AI rent (the valuation proxy) over its level
    in the pledge year; zero before the policy start (best case: always applied)."""
    probe = _ai(p, horizon, "probe")
    g = (1.0 + p.world_growth)
    rent = [max(0.0, p.ls0 - probe.labour_share.at(t, horizon)) * g ** t for t in range(horizon)]
    ref = rent[min(PLEDGE_YEAR - p.base_year, horizon - 1)] or 1e-12
    out = []
    for t in range(horizon):
        if p.base_year + t < POLICY_START_YEAR:
            out.append(0.0)
            continue
        steps = 0
        if p.base_year + t > PLEDGE_YEAR and rent[t] > ref:
            steps = int(math.floor(math.log(rent[t] / ref) / math.log(1.5)))
        out.append(PLEDGE_BASE + PLEDGE_STEP * max(0, steps))
    return out


def _child_seed(p: SFCParams, horizon: int) -> List[float]:
    """EUR 120 per child aged 6-17 a year from 2027, fixed in current euros
    (the Fruehstart-Rente is not indexed), MEUR."""
    eur = CHILD_EUR_YEAR * CHILD_SHARE * (p.population or 0.0) / 1e6
    return _years(p, horizon, CHILD_START_YEAR, value=eur)


LIBRARY: Dict[str, Proposal] = {}


def _add(key, name, source, build, note=""):
    LIBRARY[key] = Proposal(key, name, source, build, note)


_add("none", "No policy (AI shift)", "-",
     lambda p, H: _ai(p, H, "No policy"))
_add("stock_levy", "One-time stock levy on AI firms (Sanders)",
     "AI Sovereign Wealth Fund Act, Sen. Sanders, June 2026 (AP, 17 Jun 2026)",
     lambda p, H: _ai(p, H, "Stock levy", ai_equity_stake=SANDERS_STAKE,
                      ai_stake_payout=SANDERS_DIVIDEND),
     "50% of domestic AI firms; 5% dividend; the rest funds public goods")
_add("pledge", "Voluntary AI pledges, best case (Anthropic-style)",
     "Anthropic Public Benefit Fund, 19 Oct 2026 (Al Jazeera)",
     lambda p, H: _ai(p, H, "Pledges", pledge_share=LeverPath(_pledge_path(p, H))),
     "ASSUMPTION: every foreign provider pledges alike and pays out where the rent is earned")
_add("debt_fund", "Borrowing-financed citizens' fund",
     "UK Citizens' Wealth Fund proposal (Lansley, McCann & Schifferes 2018); "
     "Norway GPFG 3% rule",
     lambda p, H: _ai(p, H, "Debt-financed fund",
                      fund_seed=LeverPath(_years(p, H, POLICY_START_YEAR,
                                                 POLICY_START_YEAR + DEBT_FUND_YEARS,
                                                 DEBT_FUND_SEED)),
                      fund_payout=DEBT_FUND_PAYOUT),
     "3% of GDP a year for 10 years; pays out 3% of its value a year")
_add("child_accounts", "Child accounts (Fruehstart-Rente)",
     "Fruehstart-Rente, Bundestag 16 Oct 2026 (Deutsche Rentenversicherung); "
     "US Trump Accounts",
     lambda p, H: _ai(p, H, "Child accounts", fund_seed_eur=LeverPath(_child_seed(p, H)),
                      ubc_reinvest=1.0),
     "EUR 10/month per child 6-17 from 2027; no payouts before retirement")
_add("source_levy", "Levy on AI fees paid abroad (3%)",
     "EU digital services taxes (FR/IT/ES 3%, AT 5%); step D pass-through 0.9",
     lambda p, H: _ai(p, H, "Source levy 3%", source_levy=SOURCE_LEVY_RATE),
     "revenue to the budget")
_add("broad_ubi", "Cash UBI on a broad tax base",
     "flat tax on all income, revenue equal to the 40% capital levy on 2019 incomes",
     lambda p, H: _ai(p, H, "Broad-base UBI", broad_tax=CAPITAL_TAX * (1.0 - p.ls0)))
_add("cash_ubi_40", "Benchmark: 40% capital levy, cash UBI", "AGORA pinned experiment",
     lambda p, H: _ai(p, H, "Cash UBI 40%", capital_tax=CAPITAL_TAX, ubi=True))
_add("ubc_40", "Benchmark: 40% claim in shares, fund pays 3%", "AGORA pinned experiment",
     lambda p, H: _ai(p, H, "UBC 40%", capital_tax=CAPITAL_TAX, ubc=True,
                      fund_payout=PINNED_FUND_PAYOUT))


@dataclass
class ProposalResult:
    key: str
    name: str
    consistent: bool
    plausible: bool
    metrics: Dict[str, float] = field(default_factory=dict)


def _metrics(run, p: SFCParams) -> Dict[str, float]:
    per = run.result.periods
    pop = p.population or 1.0
    e, s0 = per[-1].reported, per[0].reported
    dist = run.dist.periods[-1].reported if run.dist is not None else {}
    cons_pc = [s.reported["consumption"] / s.reported["price_level"] / pop * 1e6
               for s in per[1:]]
    return {
        "gni_real_end": e["gni_real"], "gni_vs_2019": e["gni_real"] / s0["gni_real"],
        "consumption_pc_avg": mean(cons_pc),              # EUR (2019 prices), 2020-49
        "gini_end": dist.get("gini_personal", float("nan")),
        "poverty_end": dist.get("poverty_rate", float("nan")),
        "wealth_top10_end": dist.get("top10_wealth_share", float("nan")),
        "debt_gdp_end": e["gov_debt_gdp"],
        "ai_rent_reached": e["ai_rent_reached_share"],
        "ai_rent_foreign_reached": e["ai_rent_foreign_reached_share"],
        "citizen_wealth_pc_end": e["citizen_wealth_pc"] * 1e6,   # EUR (2019 prices)
        "dividend_pc_end": e["transfer_pool"] / e["price_level"] / pop * 1e6,
    }


def run_library(orch, horizon: int = 30, keys: Optional[List[str]] = None
                ) -> List[ProposalResult]:
    """Run every proposal through the full gated chain; a refused run is kept
    (consistent=False) rather than aborting the comparison."""
    from consistency.checks import ConsistencyError
    p = orch.params()
    out = []
    for key in (keys or list(LIBRARY)):
        prop = LIBRARY[key]
        try:
            run = orch.run_scenario(prop.build(p, horizon))
        except ConsistencyError:
            out.append(ProposalResult(key, prop.name, False, False))
            continue
        adv = {c.name for r in run.reports for c in r.advisories()}
        out.append(ProposalResult(key, prop.name, run.consistent,
                                  run.consistent and not adv, _metrics(run, p)))
    return out
