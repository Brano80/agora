"""Phase 7 step B (2026-10-29): the behavioural investment closure.

Investment is a decision, and it has to be paid for. These tests pin the
MECHANICS, not findings (findings are re-validated in Phase 7 step F):
  * year 0 reproduces the observed base year in every arm (identical to legacy);
  * the gate stays exact with the new loans instrument;
  * owners never hold negative money and never go insolvent - across countries,
    policy arms and the whole Monte-Carlo prior;
  * investment responds to the owners' net profit share, and owners invest only
    on the stake they own (the fund on the profits it retains);
  * the pecking order binds: loans appear only when saving falls short, stay
    under the cap and pay interest to the stand-in public lender; with no credit
    the shortfall cuts investment instead;
  * the legacy closure still reproduces the published v1.1 numbers exactly.
"""
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calibration import calibrate
from consistency.checks import check_run
from data.connectors.dbnomics import DBnomicsConnector
from modules.sfc_core import (SFCCore, DEBT_CAP, DELEVERAGE_RATE, LOAN_RATE,
                              PROFIT_RESPONSE, PROFIT_RESPONSE_DEFAULT)
from orchestrator import AgoraOrchestrator
from scenarios import build_custom, make_triad, make_ubc_experiment
from uncertainty import PRIORS, core_kwargs

SOLVENCY = {"hh_net_worth_nonnegative", "money_split_shares_valid"}
# macro aggregates reproduce the legacy base year; household money and income
# differ by design from step D (foreign owners, equity abroad, no household fx)
# (gov_debt differs from step E: interest and the structural fiscal balance)
YEAR0_KEYS = ("gdp", "consumption", "investment", "wage_bill",
              "profits", "exports", "imports", "gov_expenditure")
YEAR0_ARM_KEYS = YEAR0_KEYS + ("gov_debt", "money_owners", "money_workers", "hh_disposable",
                               "current_account", "niip")


def _orch(geo, **kw):
    o = AgoraOrchestrator(geo=geo, allow_live=False, strict=True, **kw)
    o.load_data()
    return o


def _solvency_failures(res):
    return {c.name for r in check_run(res, plausibility="enforce")
            for c in r.failures()} & SOLVENCY


@pytest.mark.parametrize("geo", ["DE", "FR", "SK", "RO", "PL"])
def test_year0_identical_to_legacy(geo):
    """Every behavioural arm reproduces the observed base year: policies switch
    on in 2020 (Phase 7 C), so year 0 equals the legacy BASELINE in all arms."""
    ob, ol = _orch(geo), _orch(geo, investment_closure="legacy")
    vl = ol.run_scenario(make_ubc_experiment(ol.params())[0]).result.periods[0].reported
    arms = [ob.run_scenario(sb).result.periods[0].reported
            for sb in make_ubc_experiment(ob.params())]
    for vb in arms:
        for k in YEAR0_KEYS:
            assert vb[k] == pytest.approx(vl[k], rel=1e-12, abs=1e-6), (geo, k)
        for k in YEAR0_ARM_KEYS:        # and every arm is the same economy in 2019
            assert vb[k] == pytest.approx(arms[0][k], rel=1e-12, abs=1e-6), (geo, k)


@pytest.mark.parametrize("geo", ["DE", "FR", "IT", "ES", "PL", "SK", "RO", "NL", "SE"])
def test_gate_exact_and_owners_solvent_in_every_arm(geo):
    o = _orch(geo)
    for run in o.run_ubc_experiment() + o.run_triad():
        assert run.consistent and run.max_residual < 1e-3, (geo, run.scenario)
        assert not _solvency_failures(run.result), (geo, run.scenario)
        assert min(p.reported["money_owners"] for p in run.result.periods) >= 0.0


def test_every_monte_carlo_draw_keeps_owners_solvent():
    """The Phase 7 B prior (profit response, debt cap, loan rate, ...): no draw
    may put owners in an overdraft or into insolvency."""
    rows = DBnomicsConnector(allow_live=False).fetch("DE", 2019)
    data = {k: r["value"] for k, r in rows.items()}
    assert "inv_elasticity" not in PRIORS and "capex_growth" not in PRIORS
    for form, pol in (("ubc", dict(ubc=True)), ("cash", dict(ubi=True))):
        rng = random.Random(7)
        for i in range(60):
            d = {k: rng.uniform(*v) for k, v in PRIORS.items()}
            p = calibrate(data, geo="DE", base_year=2019, a1_w=d["a1_w"])
            scen = build_custom(p, labour_share_end=d["labour_share_end"],
                                capital_tax=0.40, horizon=30, name="mc", **pol)
            res = SFCCore(base_year=2019, calib_kwargs={"a1_w": d["a1_w"]},
                          **core_kwargs(d)).run(scen, data)
            assert all(r.passed for r in check_run(res)), (form, i)
            assert not _solvency_failures(res), (form, i, d)


def test_investment_responds_to_owners_net_profit_share():
    # mechanism test with the AI rent kept at home (step D sends 70% abroad)
    o = _orch("DE", ai_foreign_share=0.0)
    runs = {r.scenario: r.result for r in o.run_ubc_experiment()}
    base, ai = runs["Baseline"], runs["AI shift, no policy"]
    cash = runs["AI + Cash UBI"]
    iy = lambda res, t: res.periods[t].reported["investment"] / res.periods[t].reported["gdp"]
    # the AI shift raises the profit share -> a higher investment share (no exogenous path)
    assert iy(ai, 15) > iy(base, 15) + 0.02
    # with the default foreign share, most of the boom's profit leaves the country
    ai70 = next(r.result for r in _orch("DE").run_ubc_experiment()
                if r.scenario == "AI shift, no policy")
    assert iy(ai70, 15) < iy(ai, 15) - 0.02
    # a 40% profit levy (from 2020) lowers owners' net profit share in year 1,
    # and with it next year's investment
    assert (cash.periods[1].reported["owners_net_profit_share"]
            < ai.periods[1].reported["owners_net_profit_share"])
    assert cash.periods[2].reported["investment"] < ai.periods[2].reported["investment"]
    # baseline: the investment share stays near the observed base-year share
    assert abs(iy(base, 29) - iy(base, 0)) < 0.02


def test_owners_invest_on_owned_stake_and_fund_on_retained_profits():
    o = _orch("DE")
    p = o.params()

    def ubc(reinvest):
        return o.run_scenario(build_custom(p, labour_share_end=0.30, capital_tax=0.40,
                                           ubc=True, ubc_reinvest=reinvest,
                                           name=f"ubc r={reinvest}")).result
    r0, r1 = ubc(0.0), ubc(1.0)
    priv = [s.reported["investment_private"] for s in r0.periods]
    share = [s.reported["swf_share"] for s in r0.periods]
    assert share[10] > share[2] and priv[10] < priv[2]       # diluted owners invest less
    # paying out all net profit: the fund only replaces what wears out (step C)
    dep = max(p.delta, p.delta_ai)
    assert all(s.reported["swf_reinvest"] <= dep * s.reported["price_level"]
               * prev.reported["swf_stake"] * (1 + 1e-9)
               for prev, s in zip(r0.periods, r0.periods[1:]))
    assert sum(s.reported["swf_reinvest"] for s in r1.periods) > 0.0
    assert r1.periods[15].reported["investment"] > r0.periods[15].reported["investment"]


def test_pecking_order_borrowing_is_capped_priced_and_netted():
    """Romania's owners save too little to fund their investment even with no
    shock: they borrow, up to the cap, and pay interest to the public lender."""
    o = _orch("RO")
    run = next(r for r in o.run_triad() if r.scenario == "Baseline").result
    per = run.periods
    loans = [s.reported["loans_owners"] for s in per]
    assert max(loans) > 0.0
    assert {s.reported["financing_regime"] for s in per} >= {1, 2}   # the cap binds
    for t in range(1, len(per)):
        # the cap is on owned capital valued at this year's prices
        cap = DEBT_CAP * per[t].reported["price_level"] * per[t - 1].reported["owners_capital"]
        # within the cap, or repaying the excess at the maturity rate
        allowed = (cap if loans[t - 1] <= cap
                   else loans[t - 1] - DELEVERAGE_RATE * (loans[t - 1] - cap))
        assert loans[t] <= allowed + 1e-6, t
        assert per[t].reported["loan_interest"] == pytest.approx(LOAN_RATE * loans[t - 1])
        assert per[t].reported["money_owners"] >= per[t].reported["owners_liquidity_floor"] - 1e-6
    for s in per:
        r = s.reported
        # fiscal debt = money issued less what the public stand-in lent and
        # bought abroad since 2019 (step D)
        fx_new = r["public_external_position"] - run.meta["fx_stand_in0"]
        assert r["gov_debt"] == pytest.approx(r["gov_money"] - r["loans_owners"] - fx_new)
        assert sum(s.bsm["loans"].values()) == pytest.approx(0.0, abs=1e-9)
    assert run.meta["stock_flow_map"]["loans"] == "loans_chg"


def test_without_credit_the_shortfall_cuts_investment():
    o = _orch("RO", debt_cap=0.0)
    run = next(r for r in o.run_triad() if r.scenario == "Baseline")
    per = run.result.periods
    assert run.consistent
    assert all(s.reported["loans_owners"] == 0.0 for s in per)
    assert max(s.reported["investment_cut"] for s in per) > 0.0
    assert min(s.reported["money_owners"] for s in per) >= 0.0


def test_profit_response_defaults_are_the_sourced_estimates():
    assert PROFIT_RESPONSE == {"DE": 0.376, "FR": 0.088, "IT": 0.130}
    assert PROFIT_RESPONSE_DEFAULT == 0.299
    for geo, want in (("DE", 0.376), ("FR", 0.088), ("IT", 0.130), ("ES", 0.299)):
        o = _orch(geo)
        meta = o.run_scenario(make_triad(o.params())[0]).result.meta
        assert meta["profit_response"] == want and meta["investment_closure"] == "behavioural"
    o = _orch("DE", profit_response=0.1)
    assert o.run_scenario(make_triad(o.params())[0]).result.meta["profit_response"] == 0.1


def test_invalid_closure_rejected():
    with pytest.raises(ValueError):
        SFCCore(investment_closure="optimistic")


def test_legacy_closure_reproduces_published_v11_numbers():
    """README v1.1 crew output: the DE frontier's UBC points, to the euro."""
    o = _orch("DE", investment_closure="legacy")
    pts = {pt.name: pt for pt in o.run_policy_search(horizon=30)}
    assert round(pts["UBC τ=40%"].metrics["gdp_end"]) == 12414605
    assert round(pts["UBC τ=50%"].metrics["gdp_end"]) == 14699402
    assert {n for n, pt in pts.items() if pt.on_frontier} == {
        "UBC τ=20%", "UBC τ=30%", "UBC τ=40%", "UBC τ=50%"}
    legacy = o.run_scenario(make_triad(o.params())[0]).result
    assert "loans" not in legacy.periods[-1].bsm


# --------------------------------------------------------------------------- #
# UBC takes NET equity; the staged gate; refused candidates in the search
# --------------------------------------------------------------------------- #
def test_fund_takes_net_equity_with_its_share_of_debt():
    """Romanian owners borrow; when UBC dilutes them the fund takes the capital
    together with its share of their loans and services that debt."""
    o = _orch("RO")
    run = o.run_scenario(build_custom(o.params(), labour_share_end=None, capital_tax=0.10,
                                      ubc=True, name="ubc10"))
    per = run.result.periods
    assert run.consistent
    assert sum(s.reported["debt_assumed_by_fund"] for s in per) > 0.0
    assert max(s.reported["loans_fund"] for s in per) > 0.0
    for t in range(1, len(per)):
        r, rp = per[t].reported, per[t - 1].reported
        assert r["fund_debt_service"] == pytest.approx(
            (LOAN_RATE + DELEVERAGE_RATE) * rp["loans_fund"])
        fx_new = r["public_external_position"] - run.result.meta["fx_stand_in0"]
        assert r["gov_debt"] == pytest.approx(
            r["gov_money"] - r["loans_owners"] - r["loans_fund"] - fx_new)
        assert r["swf_net_assets"] == pytest.approx(
            r["price_level"] * r["swf_stake"] - r["loans_fund"]
            + r["fund_foreign_equity"])                              # stake is real
        assert sum(per[t].bsm["loans"].values()) == pytest.approx(0.0, abs=1e-9)


def test_gate_is_staged_for_behavioural_runs_and_audit_for_legacy(monkeypatch):
    from consistency.checks import (ENFORCED_LAWS, resolve_plausibility,
                                    check_period)
    from modules.interface import PeriodState
    monkeypatch.delenv("AGORA_PLAUSIBILITY", raising=False)
    assert resolve_plausibility(None, "behavioural") == "staged"
    assert resolve_plausibility(None, "legacy") == "audit"
    assert ENFORCED_LAWS == {"hh_net_worth_nonnegative"}
    monkeypatch.setenv("AGORA_PLAUSIBILITY", "enforce")
    assert resolve_plausibility(None, "legacy") == "enforce"      # env wins
    monkeypatch.delenv("AGORA_PLAUSIBILITY")

    def state(owners_money, inv):
        return PeriodState(2030, bsm={
            "money": {"hh_workers": 50.0, "hh_owners": owners_money,
                      "government": -(50.0 + owners_money)},
            "capital": {"hh_owners": 10.0}}, reported={"gdp": 100.0, "investment": inv})
    insolvent = check_period(state(-15.0, 10.0), plausibility="staged")
    assert not insolvent.passed                                    # blocks
    heavy_capex = check_period(state(5.0, 50.0), plausibility="staged")
    assert heavy_capex.passed and heavy_capex.advisories()        # reported only


def test_behavioural_ubc_passes_the_staged_gate_with_advisories():
    # SK: the most equal member, where the fund's dividends push the Gini below
    # the 0.15 floor (an advisory law until step F); the gate still passes
    o = _orch("SK")                                 # strict orchestrator, default mode
    ubc = next(r for r in o.run_ubc_experiment() if "Universal Basic Capital" in r.scenario)
    assert ubc.consistent
    assert "gini_floor" in {c.name for r in ubc.reports for c in r.advisories()}


def test_policy_search_records_refused_candidates_without_aborting():
    """A candidate the gate refuses (strict ConsistencyError) is recorded as
    inconsistent, never reaches the frontier, and does not abort the search."""
    from consistency.checks import ConsistencyError
    from policy_search import search_policies
    o = _orch("DE")

    def runner(scen):
        if scen.name == "UBC τ=30%":
            raise ConsistencyError("[sfc_core/test] year 2030 FAILED: hh_net_worth_nonnegative(inf)")
        return o.run_scenario(scen)
    pts = search_policies(runner, o.params(), horizon=30)
    refused = [p for p in pts if not p.consistent]
    assert [p.name for p in refused] == ["UBC τ=30%"]
    assert refused[0].refusal.startswith("[sfc_core/test]") and not refused[0].on_frontier
    assert len(pts) == 13 and any(p.on_frontier for p in pts)
