"""Phase 7 step C (2026-10-29): supply side and prices.

Pins the MECHANICS (findings are re-validated in step F):
  * real output never exceeds the capacity ceiling; excess demand leaks into
    imports and the books still close;
  * policies switch on in 2020, so 2019 is identical in every arm and there is
    no instant output jump at switch-on;
  * the baseline is anchored: inflation near the ECB 2% target, utilisation
    stationary; demand pressure raises inflation, slack lowers it;
  * AI raises capacity (a productivity LEVEL, phased with adoption);
  * exports lose competitiveness when domestic prices outrun the world's 2% path;
  * nominal GDP = real GDP x price level; legacy keeps P = 1;
  * the capacity-utilisation connector summarises the EC survey correctly and
    falls back to a FLAGGED default;
  * the citizens' fund invests by the owners' rule up to its payout budget.
"""
import json
import os
import statistics
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.connectors import capacity as cap
from modules.ai_shock import AI_PRODUCTIVITY, AI_PRODUCTIVITY_YEARS
from modules.sfc_core import (EXPORT_ELASTICITY, INFLATION_TARGET, SFCCore,
                              UTILISATION_RESPONSE)
from orchestrator import AgoraOrchestrator
from scenarios import LS_AI_END, build_custom, make_ubc_experiment


def _orch(geo, **kw):
    o = AgoraOrchestrator(geo=geo, allow_live=False, strict=True, **kw)
    o.load_data()
    return o


def _run(o, name="x", **kw):
    return o.run_scenario(build_custom(o.params(), name=name, **kw))


@pytest.mark.parametrize("geo", ["DE", "FR", "SK", "RO", "PL"])
def test_real_output_never_exceeds_the_capacity_ceiling(geo):
    o = _orch(geo)
    u_max = cap.capacity_utilisation_for(geo)["max"]
    runs = o.run_ubc_experiment() + [
        _run(o, "cash60", labour_share_end=LS_AI_END, capital_tax=0.60, ubi=True),
        _run(o, "ubc0", labour_share_end=LS_AI_END, capital_tax=0.40, ubc=True)]
    capped = 0
    for run in runs:
        assert run.consistent and run.max_residual < 1e-3, (geo, run.scenario)
        for s in run.result.periods:
            r = s.reported
            assert r["gdp_real"] <= u_max * r["capacity"] * (1 + 1e-9), (geo, run.scenario, s.year)
            if r["excess_imports"] > 0:
                capped += 1
                assert r["utilisation"] == pytest.approx(u_max)
    assert capped > 0                     # the ceiling is actually exercised


def test_switch_on_jump_is_bounded_by_capacity_headroom():
    o = _orch("DE")
    runs = o.run_ubc_experiment()
    y0 = {r.scenario: r.result.periods[0].reported["gdp"] for r in runs}
    assert max(y0.values()) == pytest.approx(min(y0.values()), rel=1e-12)   # 2019 identical
    cash = {r.scenario: r.result for r in runs}["AI + Cash UBI"].periods
    u = cap.capacity_utilisation_for("DE")
    jump = cash[1].reported["gdp_real"] / cash[0].reported["gdp_real"] - 1.0
    headroom = (u["max"] / u["base"]) * (cash[1].reported["capacity"]
                                          / cash[0].reported["capacity"]) - 1.0
    assert cash[1].reported["excess_imports"] > 0          # the demand boost hits the ceiling
    assert jump <= headroom + 1e-9                         # legacy: +10.6% with no bound


@pytest.mark.parametrize("geo", ["DE", "FR", "IT", "ES", "PL", "SK", "NL", "LT", "HU"])
def test_baseline_is_anchored(geo):
    per = _run(_orch(geo), "base").result.periods
    infl = [s.reported["inflation"] for s in per[1:]]
    util = [s.reported["utilisation"] for s in per]
    u = cap.capacity_utilisation_for(geo)
    assert abs(statistics.mean(infl) - INFLATION_TARGET) < 0.005, geo
    lo = u["min"] if u.get("min") is not None else 0.70     # the country's 2005-2019 trough
    assert lo <= min(util) and max(util) <= u["max"], geo
    assert statistics.pstdev(util) < 0.02, geo


def test_demand_pressure_raises_inflation_and_slack_lowers_it():
    o = _orch("DE")
    hot = _run(o, "cash60", labour_share_end=LS_AI_END, capital_tax=0.60, ubi=True).result
    slack = _run(o, "ai", labour_share_end=LS_AI_END).result
    assert max(s.reported["inflation"] for s in hot.periods) > INFLATION_TARGET + 0.005
    assert min(s.reported["inflation"] for s in slack.periods) < INFLATION_TARGET - 0.003


def test_ai_raises_capacity_as_a_phased_productivity_level():
    o = _orch("DE")
    p = o.params()
    with_ai = build_custom(p, labour_share_end=LS_AI_END, name="ai")
    without = build_custom(p, labour_share_end=LS_AI_END, ai_productivity=0.0, name="ai0")
    H = with_ai.horizon
    assert with_ai.ai_productivity.at(0, H) == 1.0
    assert with_ai.ai_productivity.at(H - 1, H) == pytest.approx(
        (1 + AI_PRODUCTIVITY) ** AI_PRODUCTIVITY_YEARS)
    assert build_custom(p, name="b").ai_productivity.at(H - 1, H) == 1.0   # no shift, no gain
    a = o.run_scenario(with_ai).result.periods
    b = o.run_scenario(without).result.periods
    # same capital entering year 1 -> capacity differs by exactly the multiplier
    assert a[1].reported["capacity"] / b[1].reported["capacity"] == pytest.approx(
        with_ai.ai_productivity.at(1, H) / without.ai_productivity.at(1, H))
    assert a[-1].reported["capacity"] > b[-1].reported["capacity"]


def test_exports_lose_competitiveness_when_prices_outrun_the_world():
    o = _orch("DE")
    p = o.params()
    per = _run(o, "cash60", labour_share_end=LS_AI_END, capital_tax=0.60, ubi=True).result.periods
    for t, s in enumerate(per):
        r = s.reported
        world = (1 + INFLATION_TARGET) ** t
        x_base = p.export_ratio * p.Y0 * (1 + p.world_growth) ** t
        want = x_base * (r["price_level"] / world) ** (-EXPORT_ELASTICITY)
        assert r["exports"] / r["price_level"] == pytest.approx(want, rel=1e-9)
    assert any(s.reported["price_level"] > (1 + INFLATION_TARGET) ** t
               for t, s in enumerate(per))


def test_nominal_is_real_times_prices_and_legacy_has_no_price_level():
    per = _run(_orch("FR"), "ubc", labour_share_end=LS_AI_END, capital_tax=0.4,
               ubc=True, ubc_reinvest=0.6).result.periods
    for s in per:
        r = s.reported
        assert r["gdp"] == pytest.approx(r["gdp_real"] * r["price_level"], rel=1e-12)
    legacy = _run(_orch("FR", investment_closure="legacy"), "b").result.periods
    assert all(s.reported["price_level"] == 1.0 and s.reported["gdp_real"] == s.reported["gdp"]
               and "capacity" not in s.reported for s in legacy)


def test_capacity_connector_summary_and_flagged_default(tmp_path):
    out = cap.summarise([str(y) for y in range(2015, 2022)],
                        [80, 82, 84, 86, 81, "NaN", 70], base_year=2019)
    assert out["base"] == 0.81 and out["max"] == 0.86 and out["min"] == 0.80
    assert out["normal"] == pytest.approx((80 + 82 + 84 + 86 + 81) / 5 / 100, abs=1e-4)
    assert "2020" not in out["series"] and "2021" not in out["series"]   # nothing after 2019
    assert cap.summarise(["2015", "2016"], [80, 81], base_year=2019) is None
    # "normal" is the recent window, not the transition years
    long = cap.summarise([str(y) for y in range(1990, 2020)],
                         [50] * 15 + [80] * 15, base_year=2019)
    assert long["normal"] == 0.80 and long["normal_window"] == "2005-2019"
    assert long["max"] == 0.80 and long["min"] == 0.80
    d = cap.capacity_utilisation_for("XX", cache_path=str(tmp_path / "missing.json"))
    assert d["flag"] == "default" and d["normal"] == 0.837 and d["max"] == 0.897
    f = tmp_path / "cu.json"
    f.write_text(json.dumps({"countries": {
        "DE": {"normal": 0.83, "base": 0.86, "max": 0.865, "source": "test"},
        "LT": {**long, "normal": 0.65, "source": "test"}}}))
    live = cap.capacity_utilisation_for("de", cache_path=str(f))
    assert live["flag"] == "live" and live["max"] == pytest.approx(0.86 + cap.MIN_HEADROOM)
    lt = cap.capacity_utilisation_for("LT", cache_path=str(f))
    assert lt["normal"] == 0.80          # re-derived from the stored series at load time


def test_capacity_parsers_quarterly_jsonstat_and_dbnomics():
    q = [f"{y}-Q{i}" for y in (2018, 2019) for i in (1, 2, 3, 4)] + ["2017-Q4"]
    v = [80, 81, 82, 83, 84, None, 86, 88, 70]
    ann = cap.annualise(q, v)
    assert ann[2018] == pytest.approx(81.5) and ann[2019] == pytest.approx(86.0)
    assert 2017 not in ann                               # one quarter is not a year
    js = {"id": ["freq", "indic", "s_adj", "geo", "time"], "size": [1, 1, 1, 1, 8],
          "dimension": {"time": {"category": {"index": {p: i for i, p in enumerate(q[:8])}}}},
          "value": {str(i): x for i, x in enumerate(v[:8]) if x is not None}}
    per, val = cap.parse_jsonstat(js)
    assert per == q[:8] and val[5] is None and val[7] == 88
    docs = [{"dimensions": {"geo": "PL"}, "period": q[:8], "value": v[:8]},
            {"dimensions": {"geo": "XX"}, "period": ["2018-Q1"], "value": [80]}]
    recs = cap.from_dbnomics_docs(docs, 2019)
    assert set(recs) == {"PL"} and recs["PL"]["base"] == 0.86
    assert recs["PL"]["route"] == "Eurostat/DBnomics SA" and "ei_bsin_q_r2" in recs["PL"]["source"]


def test_capacity_cache_covers_every_member_from_one_source():
    doc = json.load(open(cap.CACHE, encoding="utf-8"))
    members = {"AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR",
               "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"}
    assert set(doc["countries"]) == members
    for g, rec in doc["countries"].items():
        assert rec["series"] and max(int(y) for y in rec["series"]) == 2019, g
        u = cap.capacity_utilisation_for(g)
        assert u["flag"] == "live" and 0.40 < u["min"] <= u["normal"] < u["max"] < 1.0, g


def test_fund_invests_by_rule_up_to_its_payout_budget():
    o = _orch("DE")
    p = o.params()

    def per(orch, rv):
        return orch.run_scenario(build_custom(
            p, labour_share_end=LS_AI_END, capital_tax=0.4, ubc=True, ubc_reinvest=rv,
            name=f"ubc r{rv}")).result.periods

    pay_all, retain = per(o, 0.0), per(o, 1.0)
    # paying out all NET profit still replaces worn-out capital (CFC is retained) ...
    assert all(s.reported["swf_reinvest"] > 0.0 for s in pay_all[2:])
    assert pay_all[-1].reported["capacity"] >= 0.95 * pay_all[0].reported["capacity"]
    # ... but adds none: retaining lets the fund invest by the owners' rule
    assert sum(s.reported["swf_reinvest"] for s in retain) > sum(
        s.reported["swf_reinvest"] for s in pay_all)
    assert retain[-1].reported["gdp_real"] > pay_all[-1].reported["gdp_real"]
    # a rule, not "all retained profits": the fund still pays a dividend, and
    # investment stays inside the plausibility bound
    assert retain[-1].reported["swf_dividend"] > 0.0
    assert max(s.reported["investment"] / s.reported["gdp"] for s in retain) < 0.40
    # an excessive POMV draw cannot consume the capital stock either
    greedy = per(_orch("DE", fund_payout=0.20), 0.0)
    assert greedy[-1].reported["capacity"] >= 0.95 * greedy[0].reported["capacity"]
    assert UTILISATION_RESPONSE == 0.25
