#!/usr/bin/env python3
"""STANDALONE STUDY — validation UNDER STRESS (not wired into the engine/dashboard).

Drives the model with the REALIZED exogenous paths (actual labour share, investment
and government spending, year by year) over 2010-2023, then measures how far the
ENDOGENOUS variables it computes (GDP, government debt/GDP, personal Gini) deviate
from what was actually observed. This is the driven backtest extended past the
clean 2010-2019 window into the 2020-2023 shock window (COVID / inflation / rates) -
NOT a forecast. Large 2020-2022 errors are expected and informative: they show where
the structural relationships strain under shocks the model deliberately omits.

Run on a NETWORKED machine (live DBnomics):
    python scripts/study_backtest_stress.py
    python scripts/study_backtest_stress.py --geos DE FR IT ES NL --start 2010 --end 2023

Writes study_backtest_stress.md (paste it back). Changes nothing in the engine.
"""
import sys, os, argparse, statistics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from calibration import calibrate
from modules.sfc_core import SFCCore
from modules.distribution import DistributionModule
from modules.interface import Scenario, LeverPath
from backtest import load_panel

CLEAN_END = 2019   # boundary between the validated window and the stress window
# keys calibrate() needs in the base year (load_panel keeps years with only
# gdp+labour_share, so early years can be incomplete -> calibrate to first complete one)
CALIB_KEYS = ("hh_consumption", "gfcf", "gov_consumption", "gdp",
              "labour_share", "gini_disp_income", "gov_debt_gdp")


def drive(geo, panel):
    """Replicate backtest()'s driving logic, but keep the full per-year paths and
    also run the distribution module so we can score Gini. Calibrates to the first
    year that has the full series set (early live years can be incomplete)."""
    years = sorted(panel)
    complete = [y for y in years if all(k in panel[y] for k in CALIB_KEYS)]
    if not complete:
        miss = {y: [k for k in CALIB_KEYS if k not in panel[y]] for y in years}
        return [], f"no complete calibration year; missing per year: {miss}"
    start, end = complete[0], years[-1]
    dropped = [y for y in years if y < start]
    H = end - start + 1
    p = calibrate(panel[start], geo=geo, base_year=start)
    at = lambda yr, k, d: panel.get(yr, {}).get(k, d)
    ls_path  = [at(start+t, "labour_share", panel[start]["labour_share"])/100.0 for t in range(H)]
    cap_path = [at(start+t, "gfcf", p.a_ratio0*p.Y0)/p.Y0 for t in range(H)]
    gov_path = [at(start+t, "gov_consumption", p.g_ratio*p.Y0) for t in range(H)]
    scen = Scenario(name="stress-backtest", horizon=H, geo=geo,
                    labour_share=LeverPath(ls_path), ai_capex=LeverPath(cap_path),
                    gov_override=LeverPath(gov_path), tax_income=LeverPath(p.theta))
    res = SFCCore(base_year=start).run(scen, panel[start])
    try:
        dist = DistributionModule(base_year=start).run(scen, panel[start], {"sfc_core": res})
    except Exception:
        dist = None
    rows = []
    for t in range(H):
        yr = start + t
        if yr not in panel:
            continue
        m = res.periods[t].reported
        row = {"year": yr}
        if "gdp" in panel[yr] and panel[yr]["gdp"]:
            row["gdp_act"] = panel[yr]["gdp"]; row["gdp_mod"] = m.get("gdp")
            row["gdp_dev"] = 100*(m.get("gdp")-panel[yr]["gdp"])/panel[yr]["gdp"]
        if "gov_debt_gdp" in panel[yr]:
            row["debt_act"] = panel[yr]["gov_debt_gdp"]; row["debt_mod"] = m.get("gov_debt_gdp")
            row["debt_dev"] = m.get("gov_debt_gdp") - panel[yr]["gov_debt_gdp"]   # pp
        if dist and "gini_disp_income" in panel[yr]:
            gm = dist.periods[t].reported.get("gini_personal", 0)*100
            row["gini_act"] = panel[yr]["gini_disp_income"]; row["gini_mod"] = gm
            row["gini_dev"] = gm - panel[yr]["gini_disp_income"]                  # pp
        rows.append(row)
    note = (f"calibrated to {start}; dropped incomplete early years {dropped}"
            if dropped else f"calibrated to {start}")
    return rows, note


def mae(rows, key, lo, hi):
    vals = [abs(r[key]) for r in rows if key in r and lo <= r["year"] <= hi]
    return (sum(vals)/len(vals)) if vals else None


def fmt(x, d=1):
    return "—" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geos", nargs="+", default=["DE", "FR", "IT", "ES"])
    ap.add_argument("--start", type=int, default=2010)
    ap.add_argument("--end", type=int, default=2023)
    a = ap.parse_args()
    yrs = list(range(a.start, a.end+1))
    out = ["# AGORA — validation under stress (driven backtest %d-%d)\n" % (a.start, a.end),
           "_Standalone study. Model driven by REALIZED labour-share / investment / "
           "government paths; endogenous GDP, debt and Gini compared to observed. "
           "Not a forecast — the 2020-2022 window contains COVID/inflation/rate shocks "
           "the engine omits, so larger errors there are expected._\n"]
    summary = []
    for geo in a.geos:
        print(f"... pulling live panel {geo} {a.start}-{a.end}")
        panel = load_panel(geo, yrs, allow_live=True)
        got = sorted(panel)
        if len(got) < 2:
            out.append(f"## {geo}\n\nLive panel returned only {got} — needs networked DBnomics.\n")
            print(f"   {geo}: only {got} (no live access here)"); continue
        rows, dnote = drive(geo, panel)
        if not rows:
            out.append(f"## {geo}\n\n{dnote}\n"); print(f"   {geo}: {dnote}"); continue
        out.append(f"## {geo}  (panel {got[0]}–{got[-1]}, n={len(got)}; {dnote})\n")
        out.append("| Year | GDP act | GDP mod | GDP %dev | Debt act | Debt mod | Debt Δpp | Gini act | Gini mod | Gini Δpp |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            out.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                r["year"], fmt(r.get("gdp_act"),0), fmt(r.get("gdp_mod"),0), fmt(r.get("gdp_dev"),2),
                fmt(r.get("debt_act")), fmt(r.get("debt_mod")), fmt(r.get("debt_dev")),
                fmt(r.get("gini_act")), fmt(r.get("gini_mod")), fmt(r.get("gini_dev"))))
        sg = {"geo": geo}
        for key, lab in (("gdp_dev","GDP %"),("debt_dev","Debt pp"),("gini_dev","Gini pp")):
            sg[lab+"_clean"] = mae(rows, key, a.start, CLEAN_END)
            sg[lab+"_stress"] = mae(rows, key, CLEAN_END+1, a.end)
        summary.append(sg)
        out.append("\n**MAE — clean (%d–%d) vs stress (%d–%d):** GDP %s%% → %s%% · Debt %spp → %spp · Gini %spp → %spp\n" % (
            a.start, CLEAN_END, CLEAN_END+1, a.end,
            fmt(sg["GDP %_clean"],2), fmt(sg["GDP %_stress"],2),
            fmt(sg["Debt pp_clean"]), fmt(sg["Debt pp_stress"]),
            fmt(sg["Gini pp_clean"]), fmt(sg["Gini pp_stress"])))

    out.append("## Summary — mean abs error, clean vs stress window\n")
    out.append("| Geo | GDP% clean | GDP% stress | Debt pp clean | Debt pp stress | Gini pp clean | Gini pp stress |")
    out.append("|---|---|---|---|---|---|---|")
    for s in summary:
        out.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            s["geo"], fmt(s["GDP %_clean"],2), fmt(s["GDP %_stress"],2),
            fmt(s["Debt pp_clean"]), fmt(s["Debt pp_stress"]),
            fmt(s["Gini pp_clean"]), fmt(s["Gini pp_stress"])))
    report = "\n".join(out)
    with open("study_backtest_stress.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("\n" + report)
    print("\nwrote study_backtest_stress.md")


if __name__ == "__main__":
    main()
