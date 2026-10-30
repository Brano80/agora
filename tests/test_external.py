"""Phase 7 step D (2026-10-30): the external sector.

Pins the MECHANICS (findings are re-validated in step F):
  * the calibration: foreign owners' stake = equity income paid abroad / gross
    profits; owners' equity abroad sized from what they receive; the 2019 net
    international investment position; conduit countries flagged;
  * the balance of payments closes and fiscal debt excludes the stand-in's
    external position; no household holds the external position any more;
  * foreign owners invest on their stake (FDI), are taxed at source by a cash
    levy, and cannot be diluted by UBC;
  * a share of the AI rent is paid abroad as licence/cloud fees; a source levy
    reaches it only to the extent providers do not pass it on;
  * the fund invests what it retains but cannot use at home in equity abroad;
  * an 80%-foreign AI scenario runs gated in every usable country.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.connectors import external as ext
from modules.sfc_core import AI_FOREIGN_SHARE, LEVY_PASS_THROUGH
from orchestrator import AgoraOrchestrator
from scenarios import LS_AI_END, build_custom

USABLE = ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR",
          "HU", "IT", "LT", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SK"]


def _orch(geo, **kw):
    o = AgoraOrchestrator(geo=geo, allow_live=False, strict=True, **kw)
    o.load_data()
    return o


def _run(o, name="x", **kw):
    return o.run_scenario(build_custom(o.params(), name=name, **kw))


def test_connector_window_conduits_and_default(tmp_path):
    ser = {"inward": {str(y): 10.0 for y in range(2010, 2020)},
           "outward": {str(y): 5.0 for y in range(2010, 2020)},
           "gdp": {str(y): 100.0 for y in range(2010, 2020)},
           "niip_pc_gdp": {"2019": -40.0}}
    s = ext.summarise(ser)
    assert s["inward_gdp"] == 0.10 and s["outward_gdp"] == 0.05 and s["niip_gdp"] == -0.40
    assert s["window"] == "2015-2019"
    assert ext.summarise({**ser, "niip_pc_gdp": {}}) is None
    f = tmp_path / "x.json"
    conduit = {**ser, "inward": {str(y): 30.0 for y in range(2010, 2020)}}
    f.write_text(json.dumps({"countries": {"AA": {"series": ser}, "BB": {"series": conduit}}}))
    assert ext.external_position_for("AA", cache_path=str(f))["flag"] == "live"
    bb = ext.external_position_for("BB", cache_path=str(f))
    assert bb["flag"] == "conduit" and bb["inward_gdp"] == ext.DEFAULT["inward_gdp"]
    assert bb["observed_inward_gdp"] == 0.30 and bb["niip_gdp"] == -0.40
    assert ext.external_position_for("ZZ", cache_path=str(tmp_path / "no.json"))["flag"] == "default"
    docs = [{"dimensions": {"geo": "AA", "direct": d, "na_item": i},
             "period": ["2018", "2019"], "value": [1.0, 2.0]}
            for d in ("RECV", "PAID") for i in ("D42", "D43")]
    rec = ext.from_dbnomics(docs, [{"dimensions": {"geo": "AA"}, "period": ["2019"],
                                    "value": [50.0]}],
                            [{"dimensions": {"geo": "AA", "unit": "PC_GDP"},
                              "period": ["2019"], "value": [12.0]}])
    assert rec["AA"]["series"]["inward"] == {"2018": 2.0, "2019": 4.0}   # D42 + D43


def test_cache_covers_members_and_flags_the_conduits():
    for g in USABLE + ["IE", "LU", "SI"]:
        e = ext.external_position_for(g)
        assert e["flag"] in ("live", "conduit"), g
    assert {g for g in USABLE + ["IE", "LU"]
            if ext.external_position_for(g)["flag"] == "conduit"} == {"CY", "IE", "LU", "MT", "NL"}
    assert ext.R_WORLD == 0.066


@pytest.mark.parametrize("geo", ["DE", "CZ", "ES"])
def test_year0_calibration_matches_the_data(geo):
    o = _orch(geo)
    p = o.params()
    e = ext.external_position_for(geo)
    run = _run(o, "base").result
    r0 = run.periods[0].reported
    psi0 = e["inward_gdp"] / ((1.0 - p.ls0) - p.delta * p.K0 / p.Y0)   # of NET profits
    assert run.meta["foreign_stake0"] == pytest.approx(psi0)
    assert r0["foreign_capital_share"] == pytest.approx(psi0, rel=0.02)
    # equity income paid abroad in 2019 = the observed share of GDP, less the
    # capital tax the model levies at source on the foreign stake (step E)
    assert r0["foreign_profits"] / r0["gdp"] == pytest.approx(
        e["inward_gdp"] - psi0 * p.theta_k * (1.0 - p.ls0), rel=1e-9)
    assert r0["owners_foreign_income"] / r0["gdp"] == pytest.approx(e["outward_gdp"], rel=1e-9)
    # the 2019 NIIP plus the year's current account (no revaluation in year 0)
    assert r0["niip_gdp"] == pytest.approx(
        100.0 * e["niip_gdp"] + 100.0 * r0["current_account"] / r0["gdp"], rel=1e-9)


@pytest.mark.parametrize("geo", ["DE", "RO", "PL"])
def test_books_close_and_no_household_holds_the_external_position(geo):
    o = _orch(geo)
    runs = o.run_ubc_experiment() + [
        _run(o, "levy", labour_share_end=LS_AI_END, capital_tax=0.4, ubi=True, source_levy=0.1),
        _run(o, "ubcL", labour_share_end=LS_AI_END, capital_tax=0.4, ubc=True,
             ubc_reinvest=0.6, source_levy=0.1)]
    for run in runs:
        assert run.consistent and run.max_residual < 1e-3, (geo, run.scenario)
        fx0 = run.result.meta["fx_stand_in0"]
        for s in run.result.periods:
            r = s.reported
            assert set(s.bsm["fx_assets"]) == {"government", "rest_of_world"}
            assert r["gov_debt"] == pytest.approx(
                r["gov_money"] - r["loans_owners"] - r["loans_fund"]
                - (r["public_external_position"] - fx0))
            assert r["gni"] == pytest.approx(r["gdp"] + r["primary_income_net"])


def test_foreign_owners_invest_are_taxed_at_source_and_cannot_be_diluted():
    o = _orch("CZ")                                    # foreign owners: ~21% of capital
    cash = _run(o, "cash", labour_share_end=LS_AI_END, capital_tax=0.4, ubi=True).result
    ubc = _run(o, "ubc", labour_share_end=LS_AI_END, capital_tax=0.4, ubc=True,
               ubc_reinvest=0.6).result
    assert all(s.reported["fdi_investment"] > 0 for s in cash.periods)
    # a cash levy is a source tax: foreign owners pay their share
    t5 = cash.periods[5].tfm
    assert t5["tax_capital"]["rest_of_world"] < 0
    # UBC dilutes domestic owners only: the foreign stake survives, the fund
    # never owns more than the domestic part
    for s in ubc.periods:
        r = s.reported
        assert r["swf_stake"] <= r["capital"] * (1.0 - r["foreign_capital_share"]) * (1 + 1e-9)
    assert ubc.periods[-1].reported["foreign_capital_share"] > 0.15


def test_ai_rent_abroad_and_the_source_levy():
    o = _orch("DE")
    nolevy = _run(o, "ai", labour_share_end=LS_AI_END).result.periods
    r = nolevy[-1].reported
    assert r["ai_rent"] > 0.2 * r["gdp"]
    assert r["ai_rent_abroad"] == pytest.approx(AI_FOREIGN_SHARE * r["ai_rent"])
    assert nolevy[0].reported["ai_rent"] == 0.0          # no shift in 2019
    base = _run(o, "base").result.periods
    assert all(s.reported["ai_rent"] == 0.0 for s in base)

    def levy(rho, s=0.10):
        oo = _orch("DE", levy_pass_through=rho)
        return _run(oo, "lv", labour_share_end=LS_AI_END, source_levy=s).result.periods[-1].reported
    full, none = levy(1.0), levy(0.0)
    for x in (full, none):
        assert x["ai_rent_levy"] == pytest.approx(0.10 * AI_FOREIGN_SHARE * x["ai_rent"])
    # fully passed on: the provider keeps its whole fee; not at all: it absorbs the levy
    assert full["ai_rent_abroad"] == pytest.approx(AI_FOREIGN_SHARE * full["ai_rent"])
    assert none["ai_rent_abroad"] == pytest.approx(0.9 * AI_FOREIGN_SHARE * none["ai_rent"])
    assert full["ai_rent_foreign_reached_share"] == pytest.approx(0.0)
    assert none["ai_rent_foreign_reached_share"] == pytest.approx(0.10)
    assert LEVY_PASS_THROUGH == 0.9


def test_which_policies_reach_the_ai_rent():
    """Wossnig (2026), qualitatively: taxes on domestic capital and dilution do
    not reach the foreign-held AI rent; a source levy does, but with the observed
    pass-through it mostly taxes domestic AI users instead."""
    o = _orch("DE")
    end = lambda **kw: _run(o, "p", labour_share_end=LS_AI_END, **kw).result.periods[-1].reported
    cash, ubc = end(capital_tax=0.4, ubi=True), end(capital_tax=0.4, ubc=True, ubc_reinvest=0.6)
    levy = end(capital_tax=0.4, ubi=True, source_levy=0.10)
    dom = 1.0 - AI_FOREIGN_SHARE
    assert cash["ai_rent_reached_share"] == pytest.approx(0.4 * dom)
    assert ubc["ai_rent_reached_share"] <= dom + 1e-9
    assert cash["ai_rent_foreign_reached_share"] == ubc["ai_rent_foreign_reached_share"] == 0.0
    assert levy["ai_rent_reached_share"] > cash["ai_rent_reached_share"]
    assert levy["ai_rent_foreign_reached_share"] == pytest.approx(
        (1.0 - LEVY_PASS_THROUGH) * 0.10)


def test_fund_invests_abroad_what_it_cannot_use_at_home():
    o = _orch("DE")
    per = _run(o, "ubc", labour_share_end=LS_AI_END, capital_tax=0.4, ubc=True,
               ubc_reinvest=0.6).result.periods
    for prev, s in zip(per, per[1:]):
        r = s.reported
        assert r["fund_foreign_income"] == pytest.approx(
            ext.R_WORLD * prev.reported["fund_foreign_equity"])
    assert per[-1].reported["fund_foreign_equity"] > 0.5 * per[-1].reported["gdp"]
    assert per[-1].reported["gni_real"] > per[-1].reported["gdp_real"] * 0.8


@pytest.mark.parametrize("geo", USABLE)
def test_80_percent_foreign_ai_runs_gated(geo):
    o = _orch(geo, ai_foreign_share=0.80)
    for kw in (dict(), dict(capital_tax=0.4, ubi=True),
               dict(capital_tax=0.4, ubc=True, ubc_reinvest=0.6, source_levy=0.1)):
        run = _run(o, "f80", labour_share_end=LS_AI_END, **kw)
        assert run.consistent and run.max_residual < 1e-3, (geo, kw)
        r = run.result.periods[-1].reported
        assert r["ai_rent_abroad"] <= 0.80 * r["ai_rent"] * (1 + 1e-9)
