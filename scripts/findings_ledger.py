#!/usr/bin/env python3
"""Phase 7 step F3: the findings ledger. Re-runs the claims behind findings
F1-F23, Q2 and the README headline on the step-F engine and writes the
numbers to docs/findings-ledger-2026-11.json; docs/FINDINGS-LEDGER.md reads
them (written by hand from this output, so every number in it is traceable).

    python scripts/findings_ledger.py
"""
import json
import os
import statistics as st
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from orchestrator import AgoraOrchestrator                  # noqa: E402
from proposals import run_library                            # noqa: E402
from region import MultiRegion                               # noqa: E402
from schema.accounts import AGGREGATE_GEOS                   # noqa: E402
from schema.coverage import usable                           # noqa: E402
from scout.checks import snapshot_geos                       # noqa: E402

OUT = os.path.join(ROOT, "docs", "findings-ledger-2026-11.json")


def _arm(run):
    per, dist = run.result.periods, run.dist.periods
    p0, e = per[0].reported, per[-1].reported
    d0, de = dist[0].reported, dist[-1].reported
    pop = run.result.meta["params"]["population"] or 1.0
    return {
        "gini0": d0["gini_personal"], "gini_end": de["gini_personal"],
        "gini_10y": dist[10].reported["gini_personal"],
        "poverty0": d0["poverty_rate"], "poverty_end": de["poverty_rate"],
        "poverty_10y": dist[10].reported["poverty_rate"],
        "top10_wealth0": d0["top10_wealth_share"], "top10_wealth_end": de["top10_wealth_share"],
        "fund_share_end": e.get("swf_share", 0.0), "fund_share_10y": per[10].reported.get("swf_share", 0.0),
        "gdp_real_index": e["gdp_real"] / p0["gdp_real"],
        "gni_real_index": e["gni_real"] / p0["gni_real"],
        "debt0": p0["gov_debt_gdp"], "debt_end": e["gov_debt_gdp"],
        "niip0": p0["niip_gdp"], "niip_end": e["niip_gdp"],
        "transfer_pc_real": [s.reported["transfer_pool"] / s.reported["price_level"] * 1e6 / pop
                             for s in per],
        "consumption_pc_avg": st.mean(s.reported["consumption"] / s.reported["price_level"] * 1e6 / pop
                                      for s in per[1:]),
        "capital_index": e["capital"] / p0["capital"],
    }


def pinned(geo):
    o = AgoraOrchestrator(geo=geo, allow_live=False)
    o.load_data()
    arms = {r.scenario: _arm(r) for r in o.run_ubc_experiment()}
    cash, ubc = arms["AI + Cash UBI"], arms["AI + Universal Basic Capital"]
    cross = next((t for t, (u, c) in enumerate(zip(ubc["transfer_pc_real"], cash["transfer_pc_real"]))
                  if t > 1 and u > c), None)
    ladder = {}
    for rv in (0.0, 0.3, 0.6, 1.0):
        rr = {r.scenario: _arm(r) for r in o.run_ubc_experiment(inv_elasticity=0.75, reinvest=rv)}
        ladder[str(rv)] = {"gdp_ubc_over_cash": rr["AI + Universal Basic Capital"]["gdp_real_index"]
                           / rr["AI + Cash UBI"]["gdp_real_index"],
                           "gini_ubc": rr["AI + Universal Basic Capital"]["gini_end"],
                           "gini_cash": rr["AI + Cash UBI"]["gini_end"],
                           "top10_wealth_ubc": rr["AI + Universal Basic Capital"]["top10_wealth_end"]}
    for a in arms.values():
        a["transfer_pc_end"] = a["transfer_pc_real"][-1]
        a["transfer_pc_10y"] = a["transfer_pc_real"][10]
        del a["transfer_pc_real"]
    return {"arms": arms, "dividend_overtakes_cash_year": (2019 + cross) if cross else None,
            "c1_ladder": ladder}


def proposals_de():
    o = AgoraOrchestrator(geo="DE", allow_live=False)
    o.load_data()
    out = {}
    for r in run_library(o):
        if r.metrics:
            out[r.key] = {k: v for k, v in r.metrics.items() if isinstance(v, (int, float))}
    return out


def pooling():
    bloc = tuple(g for g in snapshot_geos() if g not in AGGREGATE_GEOS and usable(g))
    out = {}
    for tag, geos, forms in (("EU", bloc, ("cash_ubi", "ubc")),
                             ("DE+FR+PL", ("DE", "FR", "PL"), ("cash_ubi", "ubc"))):
        mr = MultiRegion(geos=geos, allow_live=False)
        for f in forms:
            c = mr.dividend_comparison(form=f, tau=0.40, horizon=30)
            n0, n1 = c.gini_national[-1], c.gini_global[-1]
            out[f"{tag}|{f}"] = {"geos": list(c.geos), "consistent": c.consistent,
                                 "gini_national_end": n0, "gini_global_end": n1,
                                 "narrowing": 1.0 - n1 / n0 if n0 else None,
                                 "gini_national_10y": c.gini_national[10],
                                 "gini_global_10y": c.gini_global[10],
                                 # EUR per person per year (the engine works in MEUR)
                                 "transfer_pc": {k: v * 1e6 for k, v in
                                                 sorted(c.pooling_transfer_pc.items(),
                                                        key=lambda kv: kv[1])}}
    return out


def no_policy_all():
    out = {}
    for g in [x for x in snapshot_geos() if x not in AGGREGATE_GEOS and usable(x)]:
        o = AgoraOrchestrator(geo=g, allow_live=False)
        o.load_data()
        runs = {r.scenario: r for r in o.run_triad()}
        a = _arm(runs["AI shift, no policy"])
        b = _arm(runs["Baseline"])
        out[g] = {"poverty0": a["poverty0"], "poverty_10y": a["poverty_10y"],
                  "poverty_end": a["poverty_end"], "gini0": a["gini0"], "gini_end": a["gini_end"],
                  "debt0": a["debt0"], "debt_end": a["debt_end"],
                  "niip0_base": b["niip0"], "niip_end_base": b["niip_end"]}
    return out


def io_spread(geo="DE"):
    o = AgoraOrchestrator(geo=geo, allow_live=False)
    o.load_data()
    run = {r.scenario: r for r in o.run_triad()}["AI shift, no policy"]
    io = run.io
    if io is None:
        return None
    s0, e = io.periods[0].reported, io.periods[-1].reported
    keys = sorted(k for k in e if k.startswith("lshare_"))
    return {k: (s0.get(k), e.get(k)) for k in keys}


def frontier_de():
    from collections import Counter
    o = AgoraOrchestrator(geo="DE", allow_live=False)
    o.load_data()
    pts = o.run_policy_search()
    rich = o.rich_policy_search()
    return {"on_frontier": [p.name for p in pts if p.on_frontier],
            "off_frontier": [p.name for p in pts if not p.on_frontier],
            "rich_on": {f"{k[0]}|{k[1]}": v for k, v in
                        Counter((p.form, p.inv_regime) for p in rich if p.on_frontier).items()}}


def main():
    t0 = time.time()
    out = {"generated": time.strftime("%Y-%m-%d"),
           "pinned": {g: pinned(g) for g in ("DE", "FR")},
           "proposals_DE": proposals_de(),
           "no_policy": no_policy_all(),
           "pooling": pooling(),
           "io_DE": io_spread("DE"),
           "frontier_DE": frontier_de()}
    rob = os.path.join(ROOT, "docs", "robustness-2026-11.json")
    if os.path.exists(rob):
        r = json.load(open(rob, encoding="utf-8"))
        out["robustness_verdicts"] = r.get("verdicts")
        out["robustness_paired"] = {g: r["geos"][g].get("paired_ubc_better") for g in r["geos"]}
        out["sensitivity_DE_gini"] = r["geos"]["DE"]["sensitivity_ubc"]["gini"]["drivers"]
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(f"wrote {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
