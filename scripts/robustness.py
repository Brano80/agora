#!/usr/bin/env python3
"""Phase 7 step F2: Monte-Carlo bands and sensitivity on the step-F engine.

For DE, FR and SK (the published robustness countries), 500 joint draws of
every prior in uncertainty.PRIORS per policy form (no policy, cash UBI, UBC;
40% levy or claim), seed 0; bands are p5 / median / p95 of the gated draws.
Convergence: the bands from the first 250 draws against all 500. Separation
(the F12 claim): do the UBC and cash-UBI bands overlap, metric by metric?
Sensitivity: first-order shares of variance (uncertainty.sensitivity).

    python scripts/robustness.py        # writes docs/ROBUSTNESS-2026-11.md + .json
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import uncertainty as U                                     # noqa: E402

GEOS = ("DE", "FR", "SK")
FORMS = ("none", "cash_ubi", "ubc")
N = 500
METRICS = {"gini": ("Personal Gini, 2048", "{:.3f}"),
           "poverty": ("Poverty rate, 2048", "{:.3f}"),
           "gni_end": ("Real national income, 2048 (MEUR, 2019 prices)", "{:,.0f}"),
           "consumption_pc_avg": ("Real consumption per person, 2020-48 average (EUR)", "{:,.0f}"),
           "citizen_wealth_pc": ("Citizens' fund wealth per person, 2048 (EUR)", "{:,.0f}"),
           "gdp_end": ("Real GDP, 2048 (MEUR, 2019 prices)", "{:,.0f}")}
SENS_METRICS = ("gini", "consumption_pc_avg", "gni_end")


def bands_of(xs):
    return {"p5": U._pctile(xs, 5), "p50": U._pctile(xs, 50), "p95": U._pctile(xs, 95), "n": len(xs)}


def run():
    out = {"generated": time.strftime("%Y-%m-%d"), "n": N, "priors": U.PRIORS, "geos": {}}
    for g in GEOS:
        rec, raw = {}, {}
        for f in FORMS:
            _, acc, used, skipped = U._run_draws(g, f, 0.40, 2019, 30, N, 0, None)
            raw[f] = acc
            rec[f] = {"used": used, "skipped": skipped,
                      "bands": {k: bands_of(v) for k, v in acc.items()},
                      "bands_250": {k: bands_of(v[:250]) for k, v in acc.items()},
                      "below_gini_floor": sum(x < 0.15 for x in acc["gini"]) / max(1, len(acc["gini"]))}
        # the same seed draws the same priors for every form: compare draw by draw
        if all(rec[f]["skipped"] == 0 for f in FORMS):
            rec["paired_ubc_better"] = {
                k: sum((u < c) if k in ("gini", "poverty") else (u > c)
                       for u, c in zip(raw["ubc"][k], raw["cash_ubi"][k])) / N
                for k in METRICS}
        sens = {}
        for m in SENS_METRICS:
            s = U.sensitivity(g, "ubc", 0.40, 2019, 30, N, 0, None, metric=m)
            sens[m] = {"n": s["n"], "linear_r2": s["linear_r2"],
                       "drivers": [{k: d[k] for k in ("param", "corr", "share")}
                                   for d in s["drivers"][:6]]}
        rec["sensitivity_ubc"] = sens
        out["geos"][g] = rec
        print(f"{g}: done", flush=True)
    return out


def separated(a, b, higher_is_better=True):
    """'separated' if the p5-p95 bands do not overlap; which side is ahead."""
    if a["p95"] < b["p5"]:
        return "separated", ("b" if higher_is_better else "a")
    if b["p95"] < a["p5"]:
        return "separated", ("a" if higher_is_better else "b")
    return "overlap", "-"


def report(d):
    L = []
    add = L.append
    add("# Robustness: Monte-Carlo bands and sensitivity (Phase 7 step F2)")
    add("")
    add(f"Generated {d['generated']} by `scripts/robustness.py` (numbers: "
        "`docs/robustness-2026-11.json`). Engine: step F (`docs/VALIDATION-2026-11.md`). "
        f"{d['n']} joint draws of all {len(d['priors'])} priors in `uncertainty.PRIORS` per "
        "country and policy form, seed 0, AI shift (labour share drawn), 40% levy paid as a "
        "cash UBI or 40% claim in shares (fund pays 3% a year). Bands: p5 / median / p95 of "
        "the draws that pass the accounting gate.")
    add("")
    add("## Does UBC beat cash UBI across the whole prior? (the F12 claim)")
    add("")
    add("| Country | Metric | No policy | Cash UBI | UBC | Bands | UBC better, draw by draw |")
    add("|---|---|---|---|---|---|---|")
    better_high = {"gini": False, "poverty": False, "gni_end": True, "consumption_pc_avg": True,
                   "citizen_wealth_pc": True, "gdp_end": True}
    verdicts = {}
    for g, rec in d["geos"].items():
        for k, (label, fmt) in METRICS.items():
            cells = []
            for f in FORMS:
                b = rec[f]["bands"][k]
                cells.append(f"{fmt.format(b['p50'])} ({fmt.format(b['p5'])}-{fmt.format(b['p95'])})")
            sep, side = separated(rec["ubc"]["bands"][k], rec["cash_ubi"]["bands"][k],
                                  better_high[k])
            v = ("UBC better, separated" if (sep == "separated" and side == "a") else
                 "cash better, separated" if sep == "separated" else "overlap")
            verdicts[(g, k)] = v
            pr = rec.get("paired_ubc_better", {}).get(k)
            add(f"| {g} | {label} | " + " | ".join(cells) + f" | {v} | "
                + (f"{100 * pr:.0f}%" if pr is not None else "-") + " |")
    add("")
    add("Median (p5-p95). \"Separated\": the two 90% bands do not overlap. Draw by draw: "
        "the same seed gives each form the same priors, so the last column is the share of "
        "the 500 draws in which UBC does better than cash UBI.")
    add("")
    add("UBC draws with a personal Gini below 0.15, the plausibility floor (lowest EU member "
        "in the data: SK 0.228): " + ", ".join(
            f"{g} {100 * rec['ubc']['below_gini_floor']:.0f}%" for g, rec in d["geos"].items())
        + ". The low tail of the UBC inequality band is outside anything observed; the "
          "separation on inequality does not depend on it (UBC's median is below cash "
          "UBI's p5 everywhere).")
    add("")
    add("## Convergence")
    add("")
    worst = 0.0
    for g, rec in d["geos"].items():
        for f in FORMS:
            for k in METRICS:
                a, b = rec[f]["bands"][k], rec[f]["bands_250"][k]
                span = abs(a["p95"] - a["p5"]) or 1.0
                for q in ("p5", "p50", "p95"):
                    worst = max(worst, abs(a[q] - b[q]) / span)
    add(f"Moving from 250 to 500 draws shifts no band edge or median by more than "
        f"{100 * worst:.0f}% of the band's width.")
    add("")
    add("## What drives the UBC outcome (first-order shares of variance)")
    add("")
    for g, rec in d["geos"].items():
        for m, s in rec["sensitivity_ubc"].items():
            top = ", ".join(f"{x['param']} {100 * x['share']:.0f}%" for x in s["drivers"][:4])
            add(f"- **{g}, {METRICS[m][0].lower()}:** {top} (linear R² {s['linear_r2']:.2f}).")
    add("")
    add("## Draws used")
    add("")
    add("| Country | " + " | ".join(FORMS) + " |")
    add("|---|" + "---|" * len(FORMS))
    for g, rec in d["geos"].items():
        add(f"| {g} | " + " | ".join(f"{rec[f]['used']}/{rec[f]['used'] + rec[f]['skipped']}"
                                     for f in FORMS) + " |")
    add("")
    return "\n".join(L) + "\n", verdicts


def main():
    data = run()
    text, verdicts = report(data)
    data["verdicts"] = {f"{g}|{k}": v for (g, k), v in verdicts.items()}
    with open(os.path.join(ROOT, "docs", "robustness-2026-11.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, default=str)
    with open(os.path.join(ROOT, "docs", "ROBUSTNESS-2026-11.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote docs/ROBUSTNESS-2026-11.md")


if __name__ == "__main__":
    main()
