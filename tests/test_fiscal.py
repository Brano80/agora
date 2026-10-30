"""Phase 7 step E (E3, 2026-10-30): a realistic government, and the
distribution layer's double count removed.

Pins the MECHANICS:
  * each country pays its own implicit interest rate (Eurostat, 2015-19);
  * net taxes are set to the structural primary balance that holds debt/GDP at
    its 2019 level, so the baseline does not drift by construction;
  * a Bohn fiscal rule (0.034, ECB WP 2036) moves the tax rate on all taxed
    income when debt deviates; capital taxes are 30% of the tax take;
  * the legacy closure keeps the v1.1 fiscal block (all off);
  * market inequality follows the capital share BEFORE taxes and levies, so a
    cash levy counts once (as the transfer), not twice.
"""
import json
import os
import statistics
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.connectors import fiscal as fc
from modules.sfc_core import CAPITAL_TAX_SHARE, FISCAL_REACTION
from orchestrator import AgoraOrchestrator
from scenarios import LS_AI_END, build_custom

MEMBERS = ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR",
           "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"]


def _orch(geo, **kw):
    o = AgoraOrchestrator(geo=geo, allow_live=False, strict=True, **kw)
    o.load_data()
    return o


def _run(o, name="x", **kw):
    return o.run_scenario(build_custom(o.params(), name=name, **kw))


def test_connector_summary_and_default(tmp_path):
    ser = {"GD": {str(y): 100.0 for y in range(2013, 2020)},
           "B9": {"2019": -1.0}, "D41PAY": {str(y): 2.0 for y in range(2013, 2020)}}
    s = fc.summarise(ser)
    assert s["implicit_rate"] == 0.02 and s["primary_balance"] == 0.01 and s["debt"] == 1.0
    assert fc.summarise({**ser, "B9": {}}) is None
    assert fc.fiscal_position_for("XX", cache_path=str(tmp_path / "no.json"))["flag"] == "default"
    for g in MEMBERS:
        f = fc.fiscal_position_for(g)
        assert f["flag"] == "live" and 0.0 < f["implicit_rate"] < 0.05, g
    assert fc.fiscal_position_for("DE")["implicit_rate"] == pytest.approx(0.0155, abs=1e-4)
    assert fc.fiscal_position_for("IT")["primary_balance"] == pytest.approx(0.018, abs=1e-6)


def test_behavioural_defaults_and_legacy_off():
    beh = _run(_orch("DE"), "b").result.meta
    assert beh["i_rate"] == pytest.approx(fc.fiscal_position_for("DE")["implicit_rate"])
    assert beh["capital_tax_share"] == CAPITAL_TAX_SHARE == 0.30
    assert beh["fiscal_reaction"] == FISCAL_REACTION == pytest.approx(0.00034)
    leg = _run(_orch("DE", investment_closure="legacy"), "l").result
    assert all(p.reported["gov_interest"] == 0.0 for p in leg.periods)
    # explicit overrides still win
    o = _orch("DE", i_rate=0.03, fiscal_reaction=0.0, capital_tax_share=0.0)
    m = _run(o, "o").result.meta
    assert m["i_rate"] == 0.03 and m["fiscal_reaction"] == 0.0 and m["capital_tax_share"] == 0.0


@pytest.mark.parametrize("geo", ["DE", "FR", "IT", "PL", "ES"])
def test_baseline_debt_holds_near_its_2019_level(geo):
    o = _orch(geo)
    per = _run(o, "base").result.periods
    d0 = per[0].reported["gov_debt_gdp"]
    path = [s.reported["gov_debt_gdp"] for s in per]
    assert max(abs(x - d0) for x in path) < 20.0, (geo, d0, min(path), max(path))
    assert all(s.reported["gov_interest"] > 0 for s in per[1:])


def test_fiscal_rule_raises_tax_rates_on_all_income_when_debt_rises():
    o = _orch("DE")
    ai = _run(o, "ai", labour_share_end=LS_AI_END).result.periods
    r0, rT = ai[0].reported, ai[-1].reported
    assert rT["gov_debt_gdp"] > r0["gov_debt_gdp"]           # the AI shift erodes wage taxes
    dl = rT["tax_rate_labour"] - r0["tax_rate_labour"]
    dk = rT["tax_rate_capital"] - r0["tax_rate_capital"]
    assert dl > 0 and dk == pytest.approx(dl, rel=1e-9)        # the same move on both
    want = FISCAL_REACTION * (ai[-2].reported["gov_debt_gdp"] - ai[0].reported["gov_debt_gdp"])
    # (the rule uses last year's ratio against the 2019 level)
    assert dl == pytest.approx(want, rel=0.05)
    off = _run(_orch("DE", fiscal_reaction=0.0), "off", labour_share_end=LS_AI_END)
    assert off.result.periods[-1].reported["gov_debt_gdp"] > rT["gov_debt_gdp"]


def test_cash_levy_is_counted_once_in_inequality():
    """Market inequality must not move with a cash levy that is fully paid back
    as a transfer: the levy shows only through the transfer."""
    o = _orch("DE")
    nop = _run(o, "ai", labour_share_end=LS_AI_END)
    cash = _run(o, "cash", labour_share_end=LS_AI_END, capital_tax=0.4, ubi=True)
    t = 1                                           # first policy year, same capital stock
    gm_nop = nop.dist.periods[t].reported["gini_market"]
    gm_cash = cash.dist.periods[t].reported["gini_market"]
    assert abs(gm_cash - gm_nop) < 0.01             # the levy no longer lowers MARKET inequality
    assert (cash.dist.periods[t].reported["gini_personal"]
            < nop.dist.periods[t].reported["gini_personal"] - 0.02)   # the transfer does
    assert cash.result.periods[t].reported["capital_income_hh_gross"] == pytest.approx(
        nop.result.periods[t].reported["capital_income_hh_gross"], rel=0.10)   # only the demand boost
