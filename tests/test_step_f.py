"""Phase 7 step F (2026-11-08): the capital stock, existing loans, trend growth
and consumption from data; the 2011-2019 backtest and the multiplier test."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import validation as val
from data.connectors.capital import capital_position_for
from data.connectors.capacity import capacity_utilisation_for
from data.connectors.fiscal import fiscal_position_for
from data.connectors.history import history_for
from data.connectors.loans import private_loans_for
from data.connectors.rates import rates_for
from data.connectors.trend import POTENTIAL_GROWTH, trend_path
from modules.interface import LeverPath
from modules.sfc_core import IMPACT_MPC, SFCCore
from orchestrator import AgoraOrchestrator
from scenarios import make_triad
from schema.coverage import EXCLUDED, usable, usable_geos
from uncertainty import PRIORS, core_kwargs


def _orch(geo, **kw):
    o = AgoraOrchestrator(geo=geo, allow_live=False, strict=True, **kw)
    o.load_data()
    return o


def _base(geo, horizon=30, **core):
    o = _orch(geo)
    scen = make_triad(o.params(), horizon=horizon)[0]
    return o, scen, SFCCore(**core).run(scen, o._data)


# ------------------------------------------------------------------ data -- #
def test_capital_stock_from_ameco():
    de, pl, sk = capital_position_for("DE"), capital_position_for("PL"), capital_position_for("SK")
    assert de["k_y"] == pytest.approx(2.782) and de["delta"] == pytest.approx(0.0647)
    # depreciation x K/Y is the national accounts' depreciation share of GDP
    assert de["delta"] * de["k_y"] == pytest.approx(de["cfc_gdp"], abs=0.005)
    assert pl["real_stock_growth"] > 0.04 and 1.3 < sk["k_y"] < 1.5
    _, _, res = _base("DE", horizon=3)
    p = res.meta["params"]
    assert p["K0"] / p["Y0"] == pytest.approx(2.782) and p["delta"] == pytest.approx(0.0647)
    # the legacy closure keeps the uniform values
    leg = _orch("DE", investment_closure="legacy").params()
    assert leg.K0 / leg.Y0 == pytest.approx(3.0) and leg.delta == 0.06


def test_base_year_windows_are_the_five_years_to_it():
    assert fiscal_position_for("DE")["window"] == "2015-2019"
    f10 = fiscal_position_for("DE", base_year=2010)
    assert f10["window"] == "2006-2010" and f10["debt"] == pytest.approx(0.81)
    assert capital_position_for("DE", base_year=2010)["window"] == "2006-2010"
    assert rates_for("DE", base_year=2010)["policy0"] == pytest.approx(0.0081, abs=1e-4)
    cu = capacity_utilisation_for("DE", base_year=2010)
    assert cu["base"] < cu["normal"]                       # 2010: a trough
    assert private_loans_for("DE")["nfc"] == pytest.approx(0.521)


def test_exclusions_are_recorded_with_reasons():
    assert set(EXCLUDED) == {"EL", "IE", "LU"}
    assert not usable("el") and usable("DE")
    assert usable_geos(["DE", "IE", "FR", "LU"]) == ["DE", "FR"]
    assert all(len(r) > 100 for r in EXCLUDED.values())


# ------------------------------------------------------------------ trend -- #
def test_trend_is_the_ageing_report_and_the_baseline_grows_at_it():
    tp = trend_path("PL", 2019, 30)
    assert tp["growth"][1] == pytest.approx(0.026) and tp["growth"][25] == pytest.approx(0.010)
    assert POTENTIAL_GROWTH["DE"][0] == 0.8
    _, _, res = _base("PL")
    per = res.periods
    real = [s.reported["gdp_real"] for s in per]
    want = [math.prod(1 + g for g in tp["growth"][1:t + 1]) for t in range(len(per))]
    # the no-shock economy grows at the Ageing Report path (within 3% after 30
    # years: government spending and investment follow last year's output, a
    # lag that costs a fast grower a little level); the 2019 gap closes, so
    # utilisation returns to normal and inflation to target
    assert max(abs(r / real[0] / w - 1.0) for r, w in zip(real, want)) < 0.04
    assert abs(real[-1] / real[0] / want[-1] - 1.0) < 0.03
    cu = res.meta["capacity_utilisation"]
    assert abs(per[-1].reported["utilisation"] - cu["normal"]) < 0.01
    assert abs(per[-1].reported["inflation"] - 0.02) < 0.001
    lo, hi = trend_path("PL", 2019, 5, draw=-1.0), trend_path("PL", 2019, 5, draw=1.0)
    assert lo["growth"][1] == pytest.approx(0.024) and hi["growth"][1] == pytest.approx(0.027)
    # a base year before the report: the ten years to it, no look-ahead
    assert trend_path("DE", 2010, 3)["flag"] == "pre_sample"


# ------------------------------------------------------- existing loans -- #
def test_existing_loans_gross_up_deposits_and_keep_net_wealth():
    _, scen, res = _base("SK", horizon=3)
    off = SFCCore(legacy_loans=False).run(scen, _orch("SK")._data)
    r, r_off = res.periods[0].reported, off.periods[0].reported
    assert r_off["deposits"] / r_off["gdp"] < 0.05           # SK: bonds + foreign position ~ 0
    assert r["deposits"] / r["gdp"] > 0.6
    lo = res.periods[0].bsm["loans"]
    nw = {s: sum(col.get(s, 0.0) for k, col in res.periods[0].bsm.items()
                 if k in ("money", "loans")) for s in ("hh_workers", "hh_owners")}
    nw_off = {s: sum(col.get(s, 0.0) for k, col in off.periods[0].bsm.items()
                     if k in ("money", "loans")) for s in ("hh_workers", "hh_owners")}
    for s in nw:      # end of 2019: only the year's interest spread differs
        assert nw[s] == pytest.approx(nw_off[s], abs=0.005 * r["gdp"])
    assert res.periods[0].bsm["housing"]["hh_workers"] == pytest.approx(-lo["hh_workers"])
    # 2019 still reproduces, and the loans stay a constant share of GDP
    assert r["gdp"] == pytest.approx(r_off["gdp"], rel=1e-9)
    per = _base("SK")[2].periods
    sh = [s.reported["loans_households"] / s.reported["gdp"] for s in per]
    assert max(sh) - min(sh) < 1e-9


def test_2010_net_debtors_keep_positive_deposits():
    # the 12 members whose bonds + foreign position were negative in 2010 now
    # start with positive deposits, financed by the loans they actually owe
    for g in ("ES", "HU", "LV", "RO", "SE"):
        m = val.run_model(g, "fed")["meta"]
        assert m["fx_holder"] == "banks", g


# ------------------------------------------------------------ consumption -- #
def test_households_spend_about_half_of_a_windfall_in_its_first_year():
    o, scen, res = _base("DE", horizon=8)
    m = res.meta
    lam = m["consumption_adjustment"]
    assert 0.5 < lam < 0.8 and m["impact_mpc"] == IMPACT_MPC
    data = o._data
    G0 = [s.reported["gov_expenditure"] for s in res.periods]
    import copy
    pinned = copy.copy(scen)
    pinned.gov_override = LeverPath(G0)
    ref = SFCCore(fiscal_reaction=0.0).run(pinned, data)
    wb = res.periods[1].reported["wage_bill"]
    cut = [0.0, -0.01 * res.periods[1].reported["gdp"] / wb] + [0.0] * 6
    shock = SFCCore(fiscal_reaction=0.0, labour_tax_shift_path=cut).run(pinned, data)
    dC1 = (shock.periods[1].reported["consumption_workers"]
           - ref.periods[1].reported["consumption_workers"])
    pr = m["params"]
    dYD1 = ((shock.periods[1].reported["income_workers_pc"]
             - ref.periods[1].reported["income_workers_pc"])
            * pr["f_workers"] * pr["population"])          # workers' disposable income
    # first-year spending out of the extra income ~ lam x workers' propensity
    assert dC1 / dYD1 == pytest.approx(lam * m["workers_mpc"], abs=0.08)
    # and spending fades back toward the reference within five years
    late = (shock.periods[6].reported["consumption"] - ref.periods[6].reported["consumption"])
    assert abs(late) < 0.25 * dC1


def test_a_permanent_change_is_still_spent_in_full():
    o, scen, res = _base("DE", horizon=30, consumption_adjustment=1.0)
    slow = SFCCore().run(scen, o._data)
    a, b = res.periods[-1].reported, slow.periods[-1].reported
    assert b["consumption"] / a["consumption"] == pytest.approx(1.0, abs=0.01)


def test_priors_carry_the_new_assumptions():
    assert PRIORS["impact_mpc"] == (0.3, 0.7) and PRIORS["trend_draw"] == (-1.0, 1.0)
    kw = core_kwargs({"impact_mpc": 0.4, "trend_draw": -0.5})
    assert kw == {"impact_mpc": 0.4, "trend_draw": -0.5}


# ------------------------------------------------------------- validation -- #
def test_history_panel_and_backtest_mechanics():
    h = history_for("DE")
    assert h["gdp"][2010] == pytest.approx(2615260.0) and 2019 in h["gdp_real"]
    act = val.actuals("DE")
    rw, st = val.random_walk(act), val.static_multiplier("DE", act)
    # both benchmarks start from the base year exactly
    assert val.errors(rw, act)["gdp_real"].get(val.BASE) is None
    d = val.base_data("DE")
    Y0 = (d["hh_consumption"] + d["gfcf"] + d["gov_consumption"] + d["exports"] - d["imports"]
          + d["gcf"] - d["gfcf"])
    assert st["gdp_real"][val.BASE] == pytest.approx(Y0)
    r = val.backtest_country("DE")
    fed = r["model"]["fed"]
    assert fed["gdp_real"]["mae"] < 2.0 and fed["inflation"]["mae"] < 1.0
    assert set(r["model"]) == set(val.VARIANTS)


def test_one_offs_are_out_of_the_fiscal_stance():
    assert val.one_off("IE", 2010) > 0.15 and val.one_off("SI", 2013) > 0.05
    assert val.one_off("DE", 2015) == 0.0


def test_multipliers_sit_in_the_literature_ranges():
    r = val.multipliers("DE")["multipliers"]
    assert 0.5 < r["spending"]["year1"] < 1.1
    assert 0.2 < r["labour_tax"]["year1"] < r["spending"]["year1"] - 0.25
    assert 0.0 < r["capital_tax"]["year1"] < 0.4
