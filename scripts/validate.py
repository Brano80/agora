#!/usr/bin/env python3
"""Phase 7 step F validation report: the 2011-2019 backtest and the
fiscal-multiplier test, for the engine as frozen (blind) and as it stands.

    python scripts/validate.py              # writes docs/VALIDATION-2026-11.md + .json
    python scripts/validate.py --json-only  # numbers only
"""
import argparse
import json
import os
import statistics as st
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import validation as val                                    # noqa: E402
from data.connectors.history import GEOS                    # noqa: E402
from schema.accounts import AGGREGATE_GEOS                  # noqa: E402
from schema.coverage import EXCLUDED, usable                # noqa: E402
from scout.checks import snapshot_geos                      # noqa: E402

DOC = os.path.join(ROOT, "docs", "VALIDATION-2026-11.md")
JSON = os.path.join(ROOT, "docs", "validation-2026-11.json")
UNITS = {"gdp_real": "%", "consumption_real": "%", "investment_real": "%", "inflation": "pp/yr",
         "debt_gdp": "pp", "ca_gdp": "pp", "private_balance": "pp"}


def run_all():
    members = [g for g in GEOS if g != "EA20"]
    out = {"generated": time.strftime("%Y-%m-%d"), "backtest": {}, "multipliers": {}}
    for cfg in ("blind", "final"):
        bt = {}
        for g in members:
            try:
                r = val.backtest_country(g, cfg)
                r.pop("paths", None)
                bt[g] = r
            except Exception as e:                          # recorded, not hidden
                bt[g] = {"error": f"{type(e).__name__}: {e}"}
        out["backtest"][cfg] = bt
        mu = {}
        for g in [x for x in snapshot_geos() if x not in AGGREGATE_GEOS]:
            try:
                mu[g] = val.multipliers(g, config=cfg)["multipliers"]
            except Exception as e:
                mu[g] = {"error": f"{type(e).__name__}: {e}"}
        out["multipliers"][cfg] = mu
    return out


def _usable(bt):
    return [g for g, r in bt.items() if "error" not in r and usable(g)]


def summarise(bt, variant="fed"):
    geos = [g for g in _usable(bt) if "error" not in bt[g]["model"].get(variant, {"error": 1})]
    rows, tot = {}, [0, 0, 0, 0]
    for k in val.VARIABLES:
        gs = [g for g in geos if bt[g]["model"][variant][k]["mae"] is not None]
        m = [bt[g]["model"][variant][k]["mae"] for g in gs]
        rw = [bt[g]["benchmarks"]["random_walk"][k]["mae"] for g in gs]
        sm = [bt[g]["benchmarks"]["static"][k]["mae"] for g in gs]
        b1 = sum(a < b for a, b in zip(m, rw))
        b2 = sum(a < c for a, c in zip(m, sm))
        b3 = sum(a < b and a < c for a, b, c in zip(m, rw, sm))
        tot = [tot[0] + b1, tot[1] + b2, tot[2] + b3, tot[3] + len(gs)]
        rows[k] = {"model": st.median(m), "rw": st.median(rw), "static": st.median(sm),
                   "beats_rw": b1, "beats_static": b2, "beats_both": b3, "n": len(gs),
                   "crisis": st.median(bt[g]["model"][variant][k]["mae_crisis"] for g in gs),
                   "after": st.median(bt[g]["model"][variant][k]["mae_after"] for g in gs),
                   "end_signed": st.median(bt[g]["model"][variant][k]["end"] for g in gs),
                   "end_positive": sum(bt[g]["model"][variant][k]["end"] > 0 for g in gs)}
    return {"rows": rows, "cells": tot[3], "beats_rw": tot[0], "beats_static": tot[1],
            "beats_both": tot[2], "n_countries": len(geos)}


def mult_summary(mu):
    gs = [g for g, r in mu.items() if "error" not in r and usable(g)]
    out = {}
    for inst in val.INSTRUMENTS:
        y1 = [mu[g][inst]["year1"] for g in gs]
        y2 = [mu[g][inst]["year2"] for g in gs]
        cum = [(a + b) / 2.0 for a, b in zip(y1, y2)]
        out[inst] = {"year1": st.median(y1), "year1_min": min(y1), "year1_max": max(y1),
                     "year2": st.median(y2), "cum2": st.median(cum), "n": len(gs)}
    return out


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "-"


def report(data):
    bt_f, bt_b = data["backtest"]["final"], data["backtest"]["blind"]
    s_f, s_b = summarise(bt_f), summarise(bt_b)
    var = {v: summarise(bt_f, v) for v in val.VARIANTS}
    m_f, m_b = mult_summary(data["multipliers"]["final"]), mult_summary(data["multipliers"]["blind"])
    L = []
    add = L.append
    add("# Validation: does the engine reproduce 2011-2019? (Phase 7 step F)")
    add("")
    add(f"Generated {data['generated']} by `scripts/validate.py` (numbers: "
        "`docs/validation-2026-11.json`). Two tests: a nine-year historical backtest "
        "against two naive benchmarks, and the engine's fiscal multipliers against the "
        "published evidence. Both ran first on the engine as frozen after the data-only "
        "fixes (**blind**), then on the engine after the structural fixes the tests "
        "exposed (**final**, step F4b, decided 2026-11-08). No parameter was fitted to "
        "either test.")
    add("")
    add("## The backtest")
    add("")
    add("- **Start:** 2010, from 2010 data only. Every calibration window is the five years "
        "to 2010 (fiscal position, interest rates, external position, capital stock); "
        "capacity utilisation is 2010's own (a trough). Trend growth is 2000-2010's.")
    add("- **Fed in (decided outside the economy):** government spending (consumption plus "
        "investment), exports (world demand), the wage share, policy rates; in the main "
        "variant also new-borrowing yields and the net-tax ratio. Government investment "
        "is moved from investment into government spending. One-off bank rescues (net "
        "capital transfers above their 2001-08 average: IE 2010, ES 2012, SI 2013, CY, EL) "
        "are kept out of the fiscal stance and out of the debt the engine is scored on.")
    add("- **Left to the engine:** consumption, private investment, imports, prices, output, "
        "debt, the current account.")
    add("- **Scored:** every result as a change since 2010. Real GDP, consumption and private "
        "investment in % (log points); inflation, and the change in public debt, the current "
        "account and the private-sector balance, in percentage points of GDP. The private-"
        "sector balance replaces the household saving rate: the engine has no separate "
        "corporate sector.")
    add("- **Benchmarks:** a random walk (levels grow at their 2000-2010 average, ratios stay "
        "at 2010) and a static multiplier that gets the engine's inputs (GDP from the "
        "expenditure identity with every other component at its 2010 share; debt from the "
        "2010 tax share and rate).")
    add("- **Bar (set before the run):** beat both benchmarks for most countries and variables.")
    add(f"- **Countries:** {s_f['n_countries']} (EL, IE and LU are reported separately: "
        "`schema/coverage.py`).")
    add("")
    add("### Result: the bar is not met")
    add("")
    add(f"Main variant (policy fed), final engine: the engine beats the random walk in "
        f"{pct(s_f['beats_rw'], s_f['cells'])} of country-variable cells, the static multiplier "
        f"in {pct(s_f['beats_static'], s_f['cells'])} and **both in "
        f"{pct(s_f['beats_both'], s_f['cells'])}**. The blind engine: "
        f"{pct(s_b['beats_rw'], s_b['cells'])}, {pct(s_b['beats_static'], s_b['cells'])} and "
        f"{pct(s_b['beats_both'], s_b['cells'])}. The structural fixes did not change the "
        "tracking; they were made for the multipliers and the balance sheets, not for it.")
    add("")
    add("| Variable | Unit | Engine | Random walk | Static | Beats RW | Beats static | Beats both | Engine, blind |")
    add("|---|---|---|---|---|---|---|---|---|")
    for k in val.VARIABLES:
        r, rb = s_f["rows"][k], s_b["rows"][k]
        add(f"| {val.LABELS[k]} | {UNITS[k]} | {r['model']:.1f} | {r['rw']:.1f} | {r['static']:.1f} "
            f"| {r['beats_rw']}/{r['n']} | {r['beats_static']}/{r['n']} | {r['beats_both']}/{r['n']} "
            f"| {rb['model']:.1f} |")
    add("")
    add("Median across countries of the mean absolute error, 2011-2019.")
    add("")
    r = s_f["rows"]
    add("**What it gets right and wrong:**")
    add(f"- **Inflation** is the engine's best variable (beats both benchmarks in "
        f"{r['inflation']['beats_both']} of {r['inflation']['n']} countries).")
    add(f"- **Public debt** is underpredicted in {r['debt_gdp']['n'] - r['debt_gdp']['end_positive']} "
        f"of {r['debt_gdp']['n']} countries (median 2019 error {r['debt_gdp']['end_signed']:+.1f} pp). "
        "The engine's inflation sits near the 2% target; euro-area GDP inflation averaged "
        "1.25% in 2011-19, so nominal GDP runs high and debt ratios low. Asset sales of "
        "bad banks (DE, AT) and cash buffers (PT, IE) also moved debt outside the deficit.")
    add(f"- **The current account** is the weakest: the static benchmark beats the engine "
        f"in {r['ca_gdp']['n'] - r['ca_gdp']['beats_static']} of {r['ca_gdp']['n']} countries. "
        "Imports follow output with one propensity; there is no exchange-rate or price "
        "channel on imports.")
    add(f"- **The euro-crisis years** (2011-13) are not worse than 2014-19 (real GDP "
        f"{r['gdp_real']['crisis']:.1f}% against {r['gdp_real']['after']:.1f}%): fed-in spending "
        "and yields carry the austerity and the spreads.")
    add("")
    add("### The policy rules")
    add("")
    add("| Variant | What the engine decides | Beats RW | Beats static | Beats both | Real GDP | Debt |")
    add("|---|---|---|---|---|---|---|")
    desc = {"fed": "behaviour only (spending, yields, net taxes fed)",
            "spread_rule": "+ the rate on new borrowing (spread rule)",
            "rules": "+ taxes (fiscal rule toward the 2010 debt ratio)"}
    for v in val.VARIANTS:
        s = var[v]
        add(f"| {v} | {desc[v]} | {pct(s['beats_rw'], s['cells'])} | {pct(s['beats_static'], s['cells'])} "
            f"| {pct(s['beats_both'], s['cells'])} | {s['rows']['gdp_real']['model']:.1f} "
            f"| {s['rows']['debt_gdp']['model']:.1f} |")
    add("")
    add("The projections' own rules (spread and fiscal rule) score about as well as feeding "
        "in actual policy: the 2011-19 errors come from behaviour and prices, not from them.")
    add("")
    add("### By country (main variant, final engine; MAE; **bold** = beats both benchmarks)")
    add("")
    add("| | " + " | ".join(val.LABELS[k] for k in val.VARIABLES) + " |")
    add("|---|" + "---|" * len(val.VARIABLES))
    for g in sorted(bt_f):
        rr = bt_f[g]
        if "error" in rr or "error" in rr["model"].get("fed", {"error": 1}):
            add(f"| {g} | " + " | ".join("err" for _ in val.VARIABLES) + " |")
            continue
        cells = []
        for k in val.VARIABLES:
            a = rr["model"]["fed"][k]["mae"]
            b = rr["benchmarks"]["random_walk"][k]["mae"]
            c = rr["benchmarks"]["static"][k]["mae"]
            cells.append("-" if a is None else (f"**{a:.1f}**" if (a < b and a < c) else f"{a:.1f}"))
        add(f"| {g}{' (excluded)' if not usable(g) else ''} | " + " | ".join(cells) + " |")
    add("")
    add("## The multipliers")
    add("")
    add("A stimulus of 1% of GDP in 2020 and 2021 (the design of Kilponen et al. 2015), "
        "2019 calibration, no AI shift, the projections' fiscal rule and rate path; change "
        f"in real GDP per unit, median of the {m_f['spending']['n']} usable countries.")
    add("")
    add("| Instrument | Year 1 (range) | Year 2 | Two-year average | Blind, year 1 | Literature |")
    add("|---|---|---|---|---|---|")
    lit = {"spending": "0.50-0.98 in year 1 across 15 European central-bank models (euro area "
                       "1.39 with rates fixed); about 0.85 cumulative in the meta-analysis",
           "labour_tax": "0.04-0.51 in those models; 0.3-0.4 below spending in the meta-analyses",
           "capital_tax": "0.02-0.65, mostly about 0.1"}
    names = {"spending": "Government spending", "labour_tax": "Labour tax cut / transfer to "
             "wage earners", "capital_tax": "Capital tax cut"}
    for inst in val.INSTRUMENTS:
        a, b = m_f[inst], m_b[inst]
        add(f"| {names[inst]} | {a['year1']:.2f} ({a['year1_min']:.2f}-{a['year1_max']:.2f}) "
            f"| {a['year2']:.2f} | {a['cum2']:.2f} | {b['year1']:.2f} | {lit[inst]} |")
    add("")
    add(f"Blind, households spent any change in income at their average propensity at once, "
        f"so a tax cut or transfer moved GDP almost as much as spending "
        f"({m_b['labour_tax']['year1']:.2f} against {m_b['spending']['year1']:.2f}). Final, they "
        "spend about half of a temporary change in its first year (Jappelli & Pistaferri 2014; "
        "Fagereng, Holm & Natvik 2021): all three year-1 multipliers sit inside the published "
        "ranges. **Year 2 is above them:** the engine has no forward-looking smoothing, so "
        "consumption keeps adjusting through the shock's second year, and the investment "
        "response to profits adds to the capital-tax effect. Read the engine's short-run "
        "responses as upper bounds.")
    add("")
    add("## What the tests changed (step F4b, disclosed)")
    add("")
    add("- **Consumption** adjusts to its long-run level by about half the gap a year "
        "(`modules/sfc_core.py`, IMPACT_MPC 0.48; MC 0.3-0.7); workers with no deposits left "
        "spend only their income. Permanent changes are still spent in full.")
    add("- **Existing loans** of firms and households (Eurostat financial accounts) sit on "
        "the banks' books at their 2019 share of GDP; deposits gross up by the same amount "
        "(SK 2019: 0% to 76% of GDP), net wealth is unchanged, borrowers pay the loan rate. "
        "Dwellings are carried at the household loans' face value (housing is not modelled).")
    add("- **Trend growth** is each country's 2024 Ageing Report path instead of 1.5% for "
        "all; the 2019 output gap closes in three years (the report's convention).")
    add("- **The public stand-in** for the foreign position applies wherever a class's "
        "deposits would start at or below zero, by rule rather than by list (in 2019 it "
        "still selects IE and CY).")
    add("- **Luxembourg** is excluded from published results, with Greece and Ireland.")
    add("")
    add("With every step F switch off, the engine reproduces the Banks-step engine to 1e-8 "
        "(checked on the triad and the UBC experiment for seven countries).")
    add("")
    add("## Limits")
    add("")
    add("- The backtest is conditional: it is fed the policy and the world demand that "
        "actually happened. It tests behaviour, not forecasting.")
    add("- The consumption-gap estimates (Onaran & Obst 2016) use data to 2013, inside the "
        "window: not fully out of sample.")
    add("- Floaters (CZ, HU, PL, RO, SE) are scored in euros; their exchange-rate moves sit "
        "in the deflator.")
    add("- Nine years cannot test a 30-year projection: the multipliers and the plausibility "
        "audit carry that part.")
    add("")
    return "\n".join(L) + "\n", {"final": s_f, "blind": s_b, "variants": var,
                                 "multipliers": {"final": m_f, "blind": m_b}}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--from-json", help="rebuild the report from a saved JSON")
    a = ap.parse_args()
    if a.from_json:
        with open(a.from_json, encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        data = run_all()
    text, summ = report(data)
    data["summary"] = summ
    with open(JSON, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, default=str)
    print(f"wrote {JSON}")
    if not a.json_only:
        with open(DOC, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {DOC}")


if __name__ == "__main__":
    main()
