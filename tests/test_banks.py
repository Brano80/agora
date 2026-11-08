"""Phase 7 Banks step (2026-11-01): a financial sector intermediates, interest
rates move from their 2019 level to the neutral rate, the government pays
interest only on its own bonds, and its new borrowing carries a premium on the
debt it adds beyond the euro area's."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.connectors.rates import (DEBT_MATURITY, DEPOSIT_BETA, NEUTRAL_RATE,
                                   RATE_SMOOTHING, RISK_PREMIUM, rates_for)
from modules.sfc_core import SFCCore, expected_gov_rate
from orchestrator import AgoraOrchestrator
from proposals import LIBRARY
from scenarios import LS_AI_END, build_custom, make_triad, make_ubc_experiment
from uncertainty import PRIORS, core_kwargs


def _orch(geo, **kw):
    o = AgoraOrchestrator(geo=geo, allow_live=False, strict=True, **kw)
    o.load_data()
    return o


def _per(o, k=1):
    return o.run_scenario(make_triad(o.params())[k]).result


def test_rate_calibration_from_data():
    de, pl, ie, ea = rates_for("DE"), rates_for("PL"), rates_for("IE"), rates_for("EA20")
    assert de["regime"] == "ecb" and pl["regime"] == "own" and ea["regime"] == "own"
    assert de["policy0"] == pytest.approx(-0.0036, abs=1e-4)           # AMECO ISN 2019
    assert pl["policy0"] == pytest.approx(0.0172, abs=1e-4)
    assert ie["stand_in"] and rates_for("CY")["stand_in"] and not de["stand_in"]
    assert de["ea_term"] == pytest.approx(0.0115, abs=5e-4)           # EA 10y - 3M, 2015-19
    assert rates_for("IT")["gov_spread"] > rates_for("FR")["gov_spread"] > de["gov_spread"]
    assert 0.0 < de["deposit_share"] < 1.0 and de["flag"] == "data"
    assert "loan_spread=euro area" in pl["flag"]


@pytest.mark.parametrize("geo", ["DE", "ES", "RO", "NL"])
def test_the_financial_sector_balances_and_the_government_owes_only_its_bonds(geo):
    o = _orch(geo)
    for run in o.run_ubc_experiment():
        per = run.result.periods
        assert run.consistent
        for t, s in enumerate(per):
            r = s.reported
            assert r["bank_net_worth"] == pytest.approx(0.0, abs=1e-6 * r["gdp"])
            assert r["deposits"] == pytest.approx(
                r["gov_bonds"] + r["loans_owners"] + r["loans_fund"]
                + r["loans_firms_existing"] + r["loans_households"]
                + r["public_external_position"], rel=1e-9)
            assert r["gov_debt"] == pytest.approx(r["gov_bonds"])
            assert set(s.bsm["fx_assets"]) == {"banks", "rest_of_world"}
            assert "government" not in s.tfm.get("fx_interest", {})
            if t:
                assert r["gov_interest"] == pytest.approx(
                    r["gov_rate_avg"] * per[t - 1].reported["gov_bonds"])
                assert r["bank_profits"] == pytest.approx(
                    s.tfm["bank_profits"]["hh_owners"]
                    + s.tfm["bank_profits"].get("rest_of_world", 0.0))


def test_year0_deposits_are_debt_plus_the_foreign_position():
    o = _orch("DE")
    run = _per(o)
    m, r0 = run.meta, run.periods[0].reported
    p = o.params()
    assert run.periods[0].bsm["money"]["banks"] == pytest.approx(-r0["deposits"])
    # end of 2019: the 2019 stocks plus the year's flows
    assert r0["deposits"] - r0["gov_bonds"] - r0["public_external_position"] == pytest.approx(
        r0["loans_owners"] + r0["loans_fund"] + r0["loans_firms_existing"]
        + r0["loans_households"], abs=1e-6 * r0["gdp"])
    assert m["fx_holder"] == "banks" and m["banks"] is True
    # step F: existing loans from the financial accounts (DE 2019: firms 52.1%,
    # households 52.5% of GDP); firms' only for the domestically owned share
    lo = m["private_loans"]
    assert lo["nfc"] == pytest.approx(0.521) and lo["hh"] == pytest.approx(0.525)
    assert r0["loans_households"] == pytest.approx(0.525 * p.Y0, rel=1e-9)
    assert r0["loans_firms_existing"] == pytest.approx(
        (1.0 - m["foreign_stake0"]) * 0.521 * p.Y0, rel=1e-9)
    assert 0.5 < lo["workers_share"] < 0.8


def test_conduits_keep_the_public_stand_in_and_it_earns_nothing():
    run = _per(_orch("IE"))
    assert run.meta["fx_holder"] == "government"
    for s in run.periods:
        assert set(s.bsm["fx_assets"]) == {"government", "rest_of_world"}
        assert not s.tfm.get("fx_interest")
        r = s.reported
        assert r["gov_debt"] == pytest.approx(
            r["gov_bonds"] - (r["public_external_position"] - run.meta["fx_stand_in0"]))


def test_policy_rates_move_to_neutral_and_do_not_react():
    de, fr, dk, pl = (_orch(g) for g in ("DE", "FR", "DK", "PL"))
    pd = [s.reported["policy_rate"] for s in _per(de).periods]
    pf = [s.reported["policy_rate"] for s in _per(fr).periods]
    assert pd == pytest.approx(pf)                         # one ECB rate
    assert pd[0] == pytest.approx(-0.0036, abs=1e-4)
    for t in (1, 5, 29):
        assert pd[t] == pytest.approx(NEUTRAL_RATE + (pd[0] - NEUTRAL_RATE) * RATE_SMOOTHING ** t)
    pk = [s.reported["policy_rate"] for s in _per(dk).periods]
    assert [a - b for a, b in zip(pk, pd)] == pytest.approx([pk[0] - pd[0]] * len(pd))   # peg
    for o in (de, pl):                                     # no reaction to policy
        sc = make_ubc_experiment(o.params())
        paths = [[s.reported["policy_rate"] for s in o.run_scenario(x).result.periods]
                 for x in sc]
        assert all(p == pytest.approx(paths[0]) for p in paths)
    pp = [s.reported["policy_rate"] for s in _per(pl).periods]
    assert pp[0] == pytest.approx(0.0172, abs=1e-4) and pp[-1] == pytest.approx(NEUTRAL_RATE, abs=1e-5)


def test_government_rate_rolls_over_and_households_earn_the_blend():
    o = _orch("IT")
    rc = rates_for("IT")
    per = _per(o).periods
    for t in range(1, len(per)):
        r, rp = per[t].reported, per[t - 1].reported
        assert r["gov_rate_avg"] == pytest.approx(
            rp["gov_rate_avg"] + (r["gov_rate_new"] - rp["gov_rate_avg"]) / DEBT_MATURITY)
        assert r["deposit_rate"] == pytest.approx(
            max(0.0, rc["deposit_rate0"] + DEPOSIT_BETA * (r["policy_rate"] - rc["policy0"])))
        assert r["household_rate"] == pytest.approx(
            rc["deposit_share"] * r["deposit_rate"]
            + (1.0 - rc["deposit_share"]) * r["gov_rate_avg"])
        assert r["loan_rate"] == pytest.approx(r["policy_rate"] + rc["loan_spread"])


def test_premium_only_on_debt_added_beyond_the_euro_area():
    o = _orch("DE")
    nop = o.run_scenario(LIBRARY["none"].build(o.params(), 30)).result.periods
    fund = o.run_scenario(LIBRARY["debt_fund"].build(o.params(), 30)).result.periods
    t = 12
    # same ECB rate and same euro-area path: the extra borrowing alone costs more
    assert fund[t].reported["policy_rate"] == pytest.approx(nop[t].reported["policy_rate"])
    gap = (fund[t - 1].reported["gov_debt_gdp"] - nop[t - 1].reported["gov_debt_gdp"]) / 100.0
    assert gap > 0.1
    assert fund[t].reported["gov_rate_new"] - nop[t].reported["gov_rate_new"] == pytest.approx(
        RISK_PREMIUM * gap, rel=1e-6)
    flat = SFCCore(risk_premium=0.0).run(make_triad(o.params())[1], o._data).periods
    rc = rates_for("DE")
    for s in flat[1:]:
        assert s.reported["gov_rate_new"] == pytest.approx(s.reported["policy_rate"]
                                                           + rc["gov_spread"])


def test_structural_balance_is_set_at_the_expected_rate():
    o = _orch("IT")
    m = _per(o, 0).meta
    exp = expected_gov_rate("IT", m["i_rate"])
    assert m["i_rate"] < exp < NEUTRAL_RATE + rates_for("IT")["gov_spread"] + 1e-9
    base = [s.reported["gov_debt_gdp"] for s in _per(_orch("DE"), 0).periods]
    assert max(abs(x - base[0]) for x in base) < 15.0                # baseline anchored


def test_taylor_option_runs_on_the_euro_area_reference_and_banks_can_be_switched_off():
    o = _orch("DE")
    scen = make_triad(o.params())[1]
    tay = SFCCore(policy_rule="taylor").run(scen, o._data)
    assert "euro area" in tay.meta["ecb_reference"]
    assert min(s.reported["policy_rate"] for s in tay.periods) == pytest.approx(-0.005)
    off = SFCCore(banks=False).run(scen, o._data)
    assert off.meta["banks"] is False and "bank_profits" not in off.periods[3].reported
    assert off.meta["fx_holder"] == "government"


def test_monte_carlo_draws_the_rate_settings():
    for k in ("neutral_rate", "risk_premium", "deposit_beta", "loan_spread_shift"):
        assert k in PRIORS
    assert "loan_rate" not in PRIORS
    kw = core_kwargs({k: sum(v) / 2 for k, v in PRIORS.items()})
    assert kw["neutral_rate"] == pytest.approx(0.02) and kw["risk_premium"] == pytest.approx(0.03)
