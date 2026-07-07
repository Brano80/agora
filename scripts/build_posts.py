#!/usr/bin/env python3
"""Audit the LinkedIn post queue against the CURRENT gated engine.

Every quantitative claim in LINKEDIN_POSTS_READY.md is recomputed here from the
consistency-gated engine (same calls as build_manifesto.py), for Germany, France
and Slovakia, and compared to the number written in the post. Drift is FLAGGED.
Mirrors the manifesto builder's rule: published numbers come from the engine,
never hand-typed. Catches the Post-5 pooling inversion automatically.

Usage:  python scripts/build_posts.py           # -> POST_NUMBERS.md + audit
Not auto-audited (heavy / networked): Post 7 (100+ Monte-Carlo draws -> run
uncertainty.py) and Post 9 backtest MAE (needs a networked panel; documented
constant in build_manifesto.py).
"""
from __future__ import annotations
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GEOS = ["DE", "FR", "SK"]
def pct(x): return round(100.0 * float(x), 1)

def _endg(r):  return r.dist.periods[-1].reported["gini_personal"]
def _endp(r):  return r.dist.periods[-1].reported["poverty_rate"]
def _endgdp(r):
    rep = r.result.periods[-1].reported
    return rep.get("gdp", rep.get("Y", 0.0))

def compute_geo(geo):
    from orchestrator import AgoraOrchestrator
    from scenarios import build_custom, LS_AI_END
    o = AgoraOrchestrator(geo=geo, year=2019, allow_live=False, strict=True)
    o.load_data(); p = o.params()
    S = {"geo": geo}
    runs = {r.scenario: r for r in o.run_ubc_experiment(horizon=30)}
    nopol, cash, ubc = (runs["AI shift, no policy"], runs["AI + Cash UBI"],
                        runs["AI + Universal Basic Capital"])
    S["gated"] = all(r.consistent for r in runs.values())
    # Post 1 — end Gini / poverty / GDP ratio (tau=0.40)
    S["gini"] = {"none": round(_endg(nopol),2), "cash": round(_endg(cash),2), "ubc": round(_endg(ubc),2)}
    S["pov"]  = {"none": pct(_endp(nopol)),     "cash": pct(_endp(cash)),     "ubc": pct(_endp(ubc))}
    S["gdp_ubc_vs_cash"] = round(_endgdp(ubc)/_endgdp(cash), 3) if _endgdp(cash) else None
    # Post 2 — tau sweep: UBC end-GDP at 0.40/0.50/0.60
    tg = {}
    for t in (0.40, 0.50, 0.60):
        r = o.run_scenario(build_custom(p, labour_share_end=LS_AI_END, capital_tax=t, ubc=True, name=f"UBC{t}"))
        tg[f"{t:.2f}"] = round(_endgdp(r), 1)
    S["tau_gdp"] = tg
    S["tau_peak"] = max(tg, key=tg.get)
    S["tau_still_rising"] = tg["0.60"] >= tg["0.50"] >= tg["0.40"]
    # Post 3 — reinstatement race: emergent end labour share at r=0.005 vs 0.04
    ls_reinst = {}
    for rr in (0.005, 0.04):
        r = o.run_scenario(build_custom(p, labour_share_end=None, automation_rate=0.08,
                                        reinstatement_rate=rr, name=f"race{rr}"))
        v = float(r.result.periods[-1].reported["labour_share"])
        ls_reinst[str(rr)] = round(v if v > 1.5 else v*100, 1)
    S["ls_reinst"] = ls_reinst
    # Post 4 — shock speed: nopol end poverty, ramp vs scurve
    sp = {}
    for ad in ("ramp", "scurve"):
        r = o.run_scenario(build_custom(p, labour_share_end=LS_AI_END, adoption=ad, name=f"sp{ad}"))
        sp[ad] = pct(_endp(r))
    S["pov_ramp_scurve"] = sp
    # Post 6/11 — sector labour share collapse (real FIGARO I-O)
    io = nopol.io
    if io is not None and io.periods:
        n = io.meta["n_sectors"]; secs = io.meta["sectors"]
        ls0 = [io.periods[0].reported[f"lshare_{s+1}"]*100 for s in range(n)]
        lsH = [io.periods[-1].reported[f"lshare_{s+1}"]*100 for s in range(n)]
        # the sector that sheds the most labour share
        drop = [ls0[i]-lsH[i] for i in range(n)]
        j = drop.index(max(drop))
        S["top_sector"] = {"name": secs[j], "ls0": round(ls0[i],0) if False else round(ls0[j],0),
                           "lsH": round(lsH[j],1), "real": io.meta.get("matrix_source")=="real"}
    # Post 8 — investment-regime ladder (UBC/cash end-GDP)
    lad = o.c1_closure(horizon=30, inv_elasticity=0.75, reinvest=0.6)
    S["c1"] = {k: round(v["ubc_vs_cash_gdp"], 2) for k, v in lad.items()}
    return S

def pooling():
    from region import MultiRegion
    out = {}
    for tag, bloc in (("DE+FR+SK", ("DE","FR","SK")), ("DE+FR", ("DE","FR"))):
        mr = MultiRegion(geos=bloc, allow_live=False)
        c = mr.dividend_comparison(form="cash_ubi", tau=0.40, horizon=30)
        cut = 100.0*(1 - c.gini_global[-1]/c.gini_national[-1]) if c.gini_national[-1] else None
        out[tag] = {"cut_pct": round(cut,1), "consistent": c.consistent}
    return out

def frontier_all_ubc():
    from orchestrator import AgoraOrchestrator
    o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True); o.load_data()
    pts = o.run_policy_search(horizon=30)
    dd = [pt.as_dict() for pt in pts]
    nd = [d for d in dd if d.get("on_frontier")]
    forms = sorted({d.get("form","?") for d in nd})
    return {"n_frontier": len(nd), "forms": forms, "n_pts": len(pts)}


# --------------------------------------------------------------------------- #
# AUDIT: claimed numbers (from LINKEDIN_POSTS_READY.md) vs the computed engine. #
# --------------------------------------------------------------------------- #
CLAIMS = {
    "gini":  {"DE": {"none":0.34,"cash":0.24,"ubc":0.12},
              "FR": {"none":0.34,"cash":0.24,"ubc":0.12},
              "SK": {"none":0.26,"cash":0.18,"ubc":0.12}},
    "pov":   {"DE": {"none":21,"cash":6,"ubc":0}, "FR": {"none":20,"cash":6,"ubc":0},
              "SK": {"none":14,"cash":3,"ubc":0}},
    "gdp":   {"DE":1.28,"FR":1.27,"SK":1.04},           # Post 1/8 fixed
    "reinst":{"DE":(9,23),"FR":(9,23),"SK":(7,19)},     # Post 3
    "sector":{"DE":(45,2),"FR":(50,2),"SK":(31,2)},     # Post 6/11
    "c1":    {"DE":{"fixed":1.28,"endogenous":0.81,"endogenous+reinvest":0.97},
              "FR":{"fixed":1.27,"endogenous":0.71,"endogenous+reinvest":0.88},
              "SK":{"fixed":1.04,"endogenous":0.79,"endogenous+reinvest":0.84}},
    "pool":  {"DE+FR+SK":61,"DE+FR":58},                # Post 5 (STALE)
}

def audit(out):
    R = []
    def chk(ok, label, got, claimed):
        R.append((("PASS" if ok else "FLAG"), label, got, claimed))
    G = out["geos"]
    for g in G:
        s = G[g]
        for k in ("none","cash","ubc"):
            chk(abs(s["gini"][k]-CLAIMS["gini"][g][k])<=0.02, f"P1 {g} Gini {k}", s["gini"][k], CLAIMS["gini"][g][k])
            chk(abs(s["pov"][k]-CLAIMS["pov"][g][k])<=1.5,  f"P1 {g} pov {k}",  s["pov"][k],  CLAIMS["pov"][g][k])
        chk(abs(s["gdp_ubc_vs_cash"]-CLAIMS["gdp"][g])<=0.03, f"P1/P8 {g} UBC/cash GDP", s["gdp_ubc_vs_cash"], CLAIMS["gdp"][g])
        # P2 tau shape
        de_fr = g in ("DE","FR")
        shape_ok = (str(s["tau_peak"]) in ("0.5","0.50")) if de_fr else s["tau_still_rising"]
        chk(shape_ok, f"P2 {g} tau shape", ("peak "+str(s["tau_peak"])) if de_fr else ("rising "+str(s["tau_still_rising"])), "peak~0.5" if de_fr else "still rising")
        # P3 reinstatement
        lo, hi = s["ls_reinst"]["0.005"], s["ls_reinst"]["0.04"]; clo,chi=CLAIMS["reinst"][g]
        chk(abs(lo-clo)<=2 and abs(hi-chi)<=2, f"P3 {g} labour-share race", (lo,hi), (clo,chi))
        # P4 shock speed
        chk(s["pov_ramp_scurve"]["ramp"]==s["pov_ramp_scurve"]["scurve"], f"P4 {g} ramp==scurve pov", s["pov_ramp_scurve"], "equal")
        # P6/11 sector
        ts=s.get("top_sector",{}); c0,cH=CLAIMS["sector"][g]
        chk(abs(ts.get("ls0",0)-c0)<=3 and abs(ts.get("lsH",99)-cH)<=2, f"P6/11 {g} {ts.get('name','?')}", (ts.get("ls0"),ts.get("lsH")), (c0,cH))
        # P8 ladder
        for r in ("fixed","endogenous","endogenous+reinvest"):
            chk(abs(s["c1"][r]-CLAIMS["c1"][g][r])<=0.03, f"P8 {g} {r}", s["c1"][r], CLAIMS["c1"][g][r])
    # P5 pooling
    for tag in ("DE+FR+SK","DE+FR"):
        got=out["pooling"][tag]["cut_pct"]
        chk(abs(got-CLAIMS["pool"][tag])<=3, f"P5 pooling {tag}", got, CLAIMS["pool"][tag])
    # Frontier (P1 claim)
    fr=out["frontier"]; chk(fr.get("forms")==["ubc"], "P1 frontier all-UBC", fr.get("forms"), ["ubc"])
    return R

def write_report(out):
    R = audit(out)
    flags=[r for r in R if r[0]=="FLAG"]
    L=["# POST_NUMBERS — engine audit of LINKEDIN_POSTS_READY.md","",
       f"Regenerated from the gated engine (DE/FR/SK, horizon 30). "
       f"**{len(R)-len(flags)}/{len(R)} checks PASS.**","",
       "Not auto-audited here: Post 7 (100+ Monte-Carlo draws, run `uncertainty.py`) "
       "and Post 9 backtest MAE (networked panel; constant in build_manifesto.py). "
       "Posts 10/12 carry no pre-audit engine numbers.",""]
    if flags:
        L+=["## FLAGGED (fix before posting)",""]
        for st,lab,got,cl in flags: L.append(f"- **{lab}** — engine `{got}` vs post `{cl}`")
        L.append("")
    L+=["## All checks",""]
    for st,lab,got,cl in R:
        mark="[PASS]" if st=="PASS" else "[FLAG]"
        L.append(f"- {mark} {lab}: engine `{got}` / post `{cl}`")
    open("POST_NUMBERS.md","w",encoding="utf-8").write("\n".join(L)+"\n")
    return R, flags

def main():
    res = {g: compute_geo(g) for g in GEOS}
    pool = pooling()
    try: fr = frontier_all_ubc()
    except Exception as e: fr = {"error": str(e)}
    out = {"geos": res, "pooling": pool, "frontier": fr}
    with open("POST_NUMBERS.json", "w", encoding="utf-8") as f: json.dump(out, f, indent=2)
    R, flags = write_report(out)
    print(f"AUDIT: {len(R)-len(flags)}/{len(R)} PASS; {len(flags)} FLAG")
    print("=== COMPUTED (current gated engine) ===")
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    if "--report-only" in sys.argv:
        o=json.load(open("POST_NUMBERS.json", encoding="utf-8")); R,flags=write_report(o)
        print(f"AUDIT: {len(R)-len(flags)}/{len(R)} PASS; {len(flags)} FLAG")
        [print(" FLAG:",f[1],f[2],"vs",f[3]) for f in flags]
    else: main()
