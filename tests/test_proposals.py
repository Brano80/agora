"""Phase 7 step E (E1, E2, E4; 2026-10-30): fair prices, the real-proposal
library, and a plausibility-filtered frontier with a living-standards objective.
Pins the MECHANICS; the findings are re-validated in step F."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.connectors.external import R_WORLD
from modules.sfc_core import AI_FOREIGN_SHARE, SFCCore
from orchestrator import AgoraOrchestrator
from policy_search import PolicyPoint, pareto_front
from proposals import (CHILD_EUR_YEAR, CHILD_SHARE, DEBT_FUND_SEED, DEBT_FUND_YEARS,
                       LIBRARY, PLEDGE_BASE, PLEDGE_STEP, SANDERS_DIVIDEND, SANDERS_STAKE,
                       _pledge_path, run_library)
from scenarios import (CAPITAL_TAX, LS_AI_END, PINNED_FUND_PAYOUT, build_custom,
                       make_ubc_experiment)


def _orch(geo="DE", **kw):
    o = AgoraOrchestrator(geo=geo, allow_live=False, strict=True, **kw)
    o.load_data()
    return o


@pytest.fixture(scope="module")
def de():
    return _orch("DE")


def _prop(o, key, H=30):
    return o.run_scenario(LIBRARY[key].build(o.params(), H))


# ---------------------------------------------------------------- E1 ---- #
def test_market_valuation_prices_the_claim_at_market_value(de):
    p = de.params()
    scen = build_custom(p, labour_share_end=LS_AI_END, capital_tax=CAPITAL_TAX, ubc=True,
                        fund_payout=PINNED_FUND_PAYOUT, name="ubc")
    mkt = SFCCore(equity_valuation="market").run(scen, de._data).periods
    book = SFCCore(equity_valuation="book").run(scen, de._data).periods
    assert mkt[1].reported["equity_q"] == 1.0                       # 2020 prices at book
    assert mkt[1].reported["swf_stake"] == pytest.approx(book[1].reported["swf_stake"])
    assert all(s.reported["equity_q"] == 1.0 for s in book)
    t = 15                                                          # profits up -> q > 1
    assert mkt[t].reported["equity_q"] > 1.2
    assert mkt[t].reported["swf_stake"] < book[t].reported["swf_stake"]
    with pytest.raises(ValueError):
        SFCCore(equity_valuation="fair")


def test_pinned_ubc_arm_pays_3pc_of_market_value(de):
    scens = make_ubc_experiment(de.params())
    assert scens[3].fund_payout.at(5, 30) == PINNED_FUND_PAYOUT == 0.03
    per = de.run_scenario(scens[3]).result.periods
    draws = [s.reported["swf_dividend"] / prev.reported["swf_market_value"]
             for prev, s in zip(per[10:], per[11:])]
    assert all(0.02 < d < 0.045 for d in draws)
    legacy = make_ubc_experiment(de.params(), fund_payout=0.0)[3]
    assert legacy.fund_payout.at(5, 30) == 0.0


# ---------------------------------------------------------------- E2 ---- #
def test_every_proposal_runs_gated_and_plausible_in_de(de):
    res = run_library(de)
    assert [r.key for r in res] == list(LIBRARY)
    assert all(r.consistent and r.plausible for r in res), [(r.key, r.plausible) for r in res]
    for prop in LIBRARY.values():
        assert prop.source and prop.name


def test_stock_levy_reaches_half_the_domestic_ai_rent(de):
    e = _prop(de, "stock_levy").result.periods[-1].reported
    assert e["ai_rent_reached_share"] == pytest.approx(SANDERS_STAKE * (1 - AI_FOREIGN_SHARE),
                                                       rel=1e-6)
    assert e["ai_rent_foreign_reached_share"] == 0.0                # foreign providers untouched
    net = e["ai_stake_income"] * (1 - e["tax_rate_capital"])
    assert e["swf_dividend"] == pytest.approx(SANDERS_DIVIDEND / R_WORLD * net, rel=1e-6)
    assert e["ai_stake_to_budget"] == pytest.approx(net - e["swf_dividend"], rel=1e-6)


def test_pledge_path_and_its_reach(de):
    p = de.params()
    path = _pledge_path(p, 30)
    assert path[0] == 0.0 and path[1] == PLEDGE_BASE
    assert path[7] == PLEDGE_BASE                                    # 2026, the pledge year
    steps = {round((x - PLEDGE_BASE) / PLEDGE_STEP, 9) for x in path[1:]}
    assert all(float(s).is_integer() and s >= 0 for s in steps)
    assert path[10] == PLEDGE_BASE < path[15] < path[-1]             # rises with the rent
    per = _prop(de, "pledge").result.periods
    for t in (5, 20, 29):
        assert per[t].reported["ai_rent_foreign_reached_share"] == pytest.approx(path[t])


def test_debt_financed_fund(de):
    per = _prop(de, "debt_fund").result.periods
    nop = _prop(de, "none").result.periods
    for t, s in enumerate(per):
        seed = s.reported["fund_seed"] / per[t - 1].reported["gdp"] if t else 0.0
        want = DEBT_FUND_SEED if 1 <= t <= DEBT_FUND_YEARS else 0.0
        assert seed == pytest.approx(want * per[t].reported["price_level"]
                                     / per[t - 1].reported["price_level"], rel=1e-9), t
    assert per[-1].reported["fund_foreign_equity"] > 0.2 * per[-1].reported["gdp"]
    assert per[-1].reported["gov_debt_gdp"] > nop[-1].reported["gov_debt_gdp"]
    assert per[-1].reported["gni_real"] > nop[-1].reported["gni_real"]


def test_child_accounts_cost_and_no_payouts(de):
    per = _prop(de, "child_accounts").result.periods
    p = de.params()
    t27 = 2027 - p.base_year
    cost = per[t27].reported["fund_seed"]                            # MEUR, nominal
    assert cost == pytest.approx(CHILD_EUR_YEAR * CHILD_SHARE * p.population / 1e6)
    assert per[-1].reported["fund_seed"] == pytest.approx(cost)       # not indexed
    assert all(s.reported["fund_seed"] == 0.0 for s in per[:t27])
    assert all(s.reported["swf_dividend"] == 0.0 for s in per)       # paid at retirement


def test_broad_base_ubi(de):
    p = de.params()
    per = _prop(de, "broad_ubi").result.periods
    r = per[5].reported
    assert r["broad_tax_rate"] == pytest.approx(CAPITAL_TAX * (1 - p.ls0))
    assert r["ubi"] == pytest.approx(r["broad_tax_rate"] * (r["wage_bill"] + r["profits"]),
                                     rel=1e-9)


# ---------------------------------------------------------------- E4 ---- #
def test_frontier_keeps_implausible_points_off_and_adds_living_standards():
    o = _orch("PL")
    pts = o.run_policy_search()
    bad = [q for q in pts if q.consistent and not q.plausible]
    assert bad and not any(q.on_frontier for q in bad)
    assert all("living" in q.objectives for q in pts if q.consistent)
    assert any(q.form == "proposal" and q.on_frontier for q in pts)
    leg = _orch("DE", investment_closure="legacy").run_policy_search()
    assert all("living" not in q.objectives for q in leg)
    assert all(q.form != "proposal" for q in leg)


def test_near_dominant_flag():
    keys = ["growth", "equality", "stability", "fiscal", "resilience", "living"]

    def pt(name, vals):
        return PolicyPoint(form="x", capital_tax=0.0, name=name, consistent=True,
                           max_residual=0.0, objectives=dict(zip(keys, vals)))
    a = pt("a", [9, 9, 9, 9, 9, 1])          # best on five of six
    b = pt("b", [1, 1, 1, 1, 1, 9])
    c = pt("c", [5, 5, 5, 5, 5, 5])
    front = pareto_front([a, b, c])
    assert {q.name for q in front} == {"a", "b", "c"}
    assert a.near_dominant and not b.near_dominant and not c.near_dominant
