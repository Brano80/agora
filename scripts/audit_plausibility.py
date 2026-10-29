#!/usr/bin/env python3
"""Plausibility audit (Phase 7 step A, 2026-10-28).

Re-runs every scenario family behind AGORA's published numbers, for every
snapshot country, and records which runs pass the accounting gate AND the
plausibility-v2 laws (consistency/checks.py, law 7):

  hh_net_worth_nonnegative     household net worth >= 0 (per class)
  money_split_shares_valid     household money holdings >= 0
  investment_share_bounded     investment / GDP <= MAX_INVESTMENT_SHARE (0.40)
  gini_floor                   personal Gini >= MIN_PERSONAL_GINI (0.15)
  owners_mpc_in_unit_interval  calibrated owners' MPC in [0, 1]

Read-only: the engine runs in its default (audit) mode, so nothing it ships
changes; the audit reads the advisory results.

  python scripts/audit_plausibility.py                      # full sweep -> docs/
  python scripts/audit_plausibility.py --geos DE,FR --part parts/a.json
  python scripts/audit_plausibility.py --pooling --part parts/pool.json
  python scripts/audit_plausibility.py --assemble parts/    # merge -> docs/
  python scripts/audit_plausibility.py --mc 50              # smaller Monte Carlo

Families (all 30-year horizon, the published settings):
  triad, ubc_experiment, frontier, rich_frontier (F23),
  c1_ladder (manifesto: endogenous investment 0.75 x reinvest 0/0.6/0.8/1.0),
  mc_ubc / mc_cash (uncertainty.PRIORS, seed 0 - the F12 bands' draws),
  pooling (multi-region dividend: EU bloc, DE+FR+SK, DE+FR).
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import random
import sys
import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# the audit READS every law's verdict, so nothing may be refused mid-run
os.environ["AGORA_PLAUSIBILITY"] = "audit"

from calibration import calibrate                                    # noqa: E402
from consistency.checks import (check_distribution, check_run,      # noqa: E402
                                MAX_INVESTMENT_SHARE, MIN_PERSONAL_GINI)
from data.connectors.dbnomics import DBnomicsConnector              # noqa: E402
from modules.distribution import DistributionModule                 # noqa: E402
from modules.sfc_core import SFCCore                                # noqa: E402
from orchestrator import AgoraOrchestrator                          # noqa: E402
from scenarios import build_custom                                  # noqa: E402
from schema.accounts import AGGREGATE_GEOS                          # noqa: E402
from scout.checks import snapshot_geos                              # noqa: E402
from scenarios import CAPEX_AI_GROWTH                               # noqa: E402
from uncertainty import LEGACY_PRIORS, PRIORS, core_kwargs          # noqa: E402

CHECKS = ("hh_net_worth_nonnegative", "money_split_shares_valid",
          "investment_share_bounded", "gini_floor", "owners_mpc_in_unit_interval")
SHORT = {"hh_net_worth_nonnegative": "net worth < 0",
         "money_split_shares_valid": "money < 0",
         "investment_share_bounded": "I/Y > 0.40",
         "gini_floor": "Gini < 0.15",
         "owners_mpc_in_unit_interval": "MPC out of [0,1]"}
C1_LADDER = (0.0, 0.6, 0.8, 1.0)
UBC_ARMS = ("AI + Cash UBI", "AI + Universal Basic Capital")

# --- capture every gated run the orchestrator makes ----------------------- #
_CAPTURE: Optional[list] = None
_orig_run = AgoraOrchestrator.run_scenario


def _capturing_run(self, scenario):
    run = _orig_run(self, scenario)
    if _CAPTURE is not None:
        _CAPTURE.append((self.geo, run))
    return run


AgoraOrchestrator.run_scenario = _capturing_run


def _r(x, nd=4):
    return None if x is None or not math.isfinite(x) else round(float(x), nd)


def _row(family, geo, name, res, dist, reports, **extra):
    params = res.meta.get("params", {}) or {}
    Y0 = float(params.get("Y0") or 1.0)
    first: Dict[str, int] = {}
    for rep in reports:
        for c in rep.advisories():
            first.setdefault(c.name, rep.year)
    accounting_ok = all(rep.passed for rep in reports)
    nw = [sum(float(col.get("hh_owners", 0.0)) for col in p.bsm.values())
          for p in res.periods]
    mk = [float(p.bsm.get("money", {}).get("hh_owners", 0.0)) for p in res.periods]
    mw = [float(p.bsm.get("money", {}).get("hh_workers", 0.0)) for p in res.periods]
    neg_money = [c for c, v in (("workers", min(mw)), ("owners", min(mk))) if v < 0]
    iy = [p.reported["investment"] / p.reported["gdp"] for p in res.periods
          if p.reported.get("gdp")]
    gi = ([p.reported["gini_personal"] for p in dist.periods
           if "gini_personal" in p.reported] if dist is not None else [])
    row = dict(family=family, geo=geo, scenario=name,
               accounting_ok=accounting_ok,
               plausible=accounting_ok and not first, first_fail=first,
               min_owner_nw_y0=_r(min(nw) / Y0), min_owner_money_y0=_r(min(mk) / Y0),
               max_inv_share=_r(max(iy)) if iy else None,
               min_gini=_r(min(gi)) if gi else None,
               a1_k=_r(params.get("a1_k")), neg_money=neg_money)
    if res.periods and "utilisation" in res.periods[0].reported:   # step C supply side
        infl = [p.reported["inflation"] for p in res.periods[1:]]
        row.update(max_inflation=_r(max(infl)) if infl else None,
                   min_inflation=_r(min(infl)) if infl else None,
                   ceiling_share=_r(sum(p.reported["excess_imports"] > 0
                                        for p in res.periods) / len(res.periods)),
                   min_utilisation=_r(min(p.reported["utilisation"] for p in res.periods)))
    row.update(extra)
    return row


def _family(rows, errors, geo, family, fn, points=False, rename=None):
    global _CAPTURE
    _CAPTURE = []
    out = None
    try:
        out = fn()
    except Exception as e:                      # a strict accounting failure etc.
        errors.append(dict(geo=geo, family=family,
                           error=f"{type(e).__name__}: {str(e)[:240]}"))
    caps, _CAPTURE = _CAPTURE, None
    flags = {}
    if points and out is not None:
        if len(out) != len(caps):
            raise RuntimeError(f"{geo}/{family}: {len(out)} points vs {len(caps)} runs")
        flags = {id(run): bool(pt.on_frontier) for (_, run), pt in zip(caps, out)}
    for g, run in caps:
        name = rename(run.scenario) if rename else run.scenario
        extra = {"on_frontier": flags.get(id(run))} if points else {}
        rows.append(_row(family, g, name, run.result, run.dist, run.reports, **extra))


def _mc(geo, n, seed=0, tau=0.40, year=2019, horizon=30, closure="behavioural"):
    """Mirror uncertainty._run_draws (same priors, seed and order) so these are
    the draws behind the published bands; aggregate per form."""
    rows = DBnomicsConnector(allow_live=False).fetch(geo, year)
    data = {k: r["value"] for k, r in rows.items()}
    out = {}
    for form, pol in (("ubc", dict(ubc=True)), ("cash_ubi", dict(ubi=True))):
        rng = random.Random(seed)
        agg = dict(n=n, used=0, skipped=0, plausible=0, fails=Counter(),
                   worst_owner_nw_y0=None, worst_owner_money_y0=None)
        for _ in range(n):
            d = {k: rng.uniform(*v) for k, v in
                 (PRIORS if closure == "behavioural" else LEGACY_PRIORS).items()}
            try:
                p = calibrate(data, geo=geo, base_year=year, a1_w=d["a1_w"])
                scen = build_custom(p, labour_share_end=d["labour_share_end"],
                                    capex_growth=d.get("capex_growth", CAPEX_AI_GROWTH),
                                    ai_productivity=d.get("ai_productivity"),
                                    capital_tax=tau, horizon=horizon, name="mc", **pol)
                res = SFCCore(base_year=year, calib_kwargs={"a1_w": d["a1_w"]},
                              **core_kwargs(d)).run(scen, data)
                reps = check_run(res, strict=False)
                if max(r.max_residual for r in reps) > 1.0:   # uncertainty.py's skip rule
                    agg["skipped"] += 1
                    continue
                dist = DistributionModule(beta=d["beta"], omega=d.get("omega", 0.15),
                                          base_year=year).run(scen, data, {"sfc_core": res})
                reps += check_distribution(dist)
            except Exception:
                agg["skipped"] += 1
                continue
            row = _row("mc_" + form, geo, "draw", res, dist, reps)
            agg["used"] += 1
            agg["plausible"] += int(row["plausible"])
            for c in row["first_fail"]:
                agg["fails"][c] += 1
            for k in ("owner_nw_y0", "owner_money_y0"):
                v = row["min_" + k]
                if v is not None and (agg["worst_" + k] is None or v < agg["worst_" + k]):
                    agg["worst_" + k] = v
        agg["fails"] = dict(agg["fails"])
        out[form] = agg
    return out


def member_geos() -> List[str]:
    return [g for g in snapshot_geos() if g.upper() not in AGGREGATE_GEOS]


def run_geos(geos, mc_n, closure="behavioural"):
    rows, errors, mc = [], [], {}
    for geo in geos:
        t0 = time.time()
        o = AgoraOrchestrator(geo=geo, allow_live=False, strict=True,
                              investment_closure=closure)
        try:
            o.load_data()
            o.params()
        except Exception as e:
            errors.append(dict(geo=geo, family="calibrate",
                               error=f"{type(e).__name__}: {str(e)[:240]}"))
            print(f"{geo}: calibration failed: {e}", flush=True)
            continue
        _family(rows, errors, geo, "triad", o.run_triad)
        _family(rows, errors, geo, "ubc_experiment", o.run_ubc_experiment)
        _family(rows, errors, geo, "frontier", o.run_policy_search, points=True)
        _family(rows, errors, geo, "rich_frontier", o.rich_policy_search, points=True)
        for rv in C1_LADDER:
            _family(rows, errors, geo, "c1_ladder",
                    lambda rv=rv: o.run_ubc_experiment(inv_elasticity=0.75, reinvest=rv),
                    rename=(lambda s, rv=rv: f"{s} [inv 0.75, reinvest {rv:g}]") if closure == "legacy"
                    else (lambda s, rv=rv: f"{s} [endogenous investment, reinvest {rv:g}]"))
        if mc_n:
            mc[geo] = _mc(geo, mc_n, closure=closure)
        print(f"{geo}: done in {time.time() - t0:.1f}s", flush=True)
    return rows, errors, mc


def run_pooling(closure="behavioural"):
    from region import MultiRegion
    rows, errors, summary = [], [], []
    bloc = tuple(g for g in member_geos() if g.upper() != "IE")   # manifesto bloc
    for tag, geos, forms in (("EU bloc (manifesto/dashboard)", bloc, ("cash_ubi", "ubc")),
                             ("DE+FR+SK (posts)", ("DE", "FR", "SK"), ("cash_ubi",)),
                             ("DE+FR (posts)", ("DE", "FR"), ("cash_ubi",))):
        mr = MultiRegion(geos=geos, allow_live=False, investment_closure=closure)
        for form in forms:
            global _CAPTURE
            _CAPTURE = []
            try:
                c = mr.dividend_comparison(form=form, tau=0.40, horizon=30)
                consistent, viable = bool(c.consistent), list(c.geos)
            except Exception as e:
                errors.append(dict(geo=tag, family="pooling",
                                   error=f"{type(e).__name__}: {str(e)[:240]}"))
                consistent, viable = False, []
            caps, _CAPTURE = _CAPTURE, None
            last = {}
            for g, run in caps:                  # keep the FINAL (converged) run per name
                last[run.scenario] = (g, run)
            fam_rows = [_row("pooling", g, name, run.result, run.dist, run.reports,
                             bloc=tag, form=form)
                        for name, (g, run) in last.items()]
            rows += fam_rows
            pooled = [r for r in fam_rows if r["scenario"].endswith("pooled")]
            summary.append(dict(bloc=tag, form=form, n_geos=len(geos),
                                n_viable=len(viable), gate_consistent=consistent,
                                pooled_runs=len(pooled),
                                pooled_plausible=sum(r["plausible"] for r in pooled),
                                national_runs=len(fam_rows) - len(pooled),
                                national_plausible=sum(r["plausible"] for r in fam_rows
                                                       if not r["scenario"].endswith("pooled"))))
            print(f"pooling {tag} {form}: done", flush=True)
    return rows, errors, summary


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
SOLVENCY = ("hh_net_worth_nonnegative", "money_split_shares_valid")


def policy_form(name: str) -> str:
    """cash / ubc / none, from the scenario name (all families' naming)."""
    n = name.lower()
    if "ubc" in n or "universal basic capital" in n:
        return "ubc"
    if "cash" in n or "settlement" in n:
        return "cash"
    return "none"


def _solvent(r) -> bool:
    return not any(k in r["first_fail"] for k in SOLVENCY)


def _pct(a, b):
    return f"{100.0 * a / b:.0f}%" if b else "n/a"


def _frac(rs):
    return f"{sum(r['plausible'] for r in rs)}/{len(rs)}"


def _firsts(rs):
    c = Counter(k for r in rs for k in r["first_fail"])
    return ", ".join(f"{SHORT[k]} ({v})" for k, v in c.most_common()) or "none"


def build_report(data, date=None):
    closure = data.get("closure", "legacy")
    step = data.get("step", "B")
    date = date or ("2026-10-28" if closure == "legacy" else "2026-10-29")
    rows, mc, pool, errors = data["rows"], data["mc"], data["pooling"], data["errors"]
    geos = sorted({r["geo"] for r in rows if r["family"] != "pooling"})
    fams = ["triad", "ubc_experiment", "frontier", "rich_frontier", "c1_ladder", "pooling"]
    by = defaultdict(list)
    for r in rows:
        by[r["family"]].append(r)
    L = []
    add = L.append
    n_all = len(rows)
    n_acc = sum(r["accounting_ok"] for r in rows)
    n_pl = sum(r["plausible"] for r in rows)
    mc_used = sum(v[f]["used"] for v in mc.values() for f in v)
    mc_pl = sum(v[f]["plausible"] for v in mc.values() for f in v)
    if closure == "legacy":
        add(f"# Plausibility audit — {date} (Phase 7, step A)\n")
        add("Every scenario family behind AGORA's published numbers, re-run for every "
            "snapshot country with the engine **unchanged** (commit after 8884d7c), and "
            "checked against the new plausibility-v2 laws in `consistency/checks.py`. "
            "The laws run in *audit* mode, so nothing shipped changes; this file reads "
            "what they flag. Reproduce: `python scripts/audit_plausibility.py`.\n")
    elif step == "C":
        add(f"# Plausibility audit — {date} (Phase 7, step C)\n")
        add("The same scenario families, countries and laws as the step-A audit "
            "(`docs/AUDIT-2026-10.md`, the v1.1 engine) and the step-B audit "
            "(`docs/AUDIT-2026-10-stepB.md`), re-run on the engine with a **supply "
            "side and prices**: real output is capped by installed capital, excess "
            "demand leaks into imports, inflation follows a Phillips curve around "
            "the ECB 2% target, AI raises productivity, and policies switch on in "
            "2020 so 2019 reproduces in every arm. Reproduce: "
            "`python scripts/audit_plausibility.py` (step A: `--closure legacy`).\n")
    else:
        add(f"# Plausibility audit — {date} (Phase 7, step B)\n")
        add("The same scenario families, countries and laws as the step-A audit "
            "(`docs/AUDIT-2026-10.md`, the v1.1 engine), re-run on the **behavioural "
            "investment closure**: investment responds to owners' net profit share, "
            "is financed saving-first with capped, interest-bearing loans, and owners "
            "invest only on the capital they own. Reproduce: "
            "`python scripts/audit_plausibility.py` (step A: `--closure legacy`).\n")
    add("| Law | Fails when |\n|---|---|")
    add("| `hh_net_worth_nonnegative` | a household class owes more than it owns (money + foreign assets + capital) |")
    add("| `money_split_shares_valid` | a household class holds negative money (an interest-free overdraft at the state) |")
    add(f"| `investment_share_bounded` | investment exceeds {MAX_INVESTMENT_SHARE:.0%} of GDP |")
    add(f"| `gini_floor` | the personal Gini falls below {MIN_PERSONAL_GINI:.2f} (lowest EU member in the data: SK 0.228) |")
    add("| `owners_mpc_in_unit_interval` | the owners' marginal propensity to consume, solved as a calibration residual, lies outside [0, 1] |\n")

    add("## Headline\n")
    add(f"- **Scenario runs:** {n_all:,} across {len(geos)} countries. **{n_acc:,} "
        f"({_pct(n_acc, n_all)}) pass the accounting gate; {n_pl:,} ({_pct(n_pl, n_all)}) "
        f"also pass the plausibility laws.**")
    add(f"- **Monte-Carlo draws** (the F12 robustness bands' priors, seed 0): {mc_pl:,} of "
        f"{mc_used:,} used draws ({_pct(mc_pl, mc_used)}) are plausible.")
    if errors:
        add(f"- **Errors / exclusions:** {len(errors)} (listed at the end).")
    add("")

    add("## By scenario family (all countries)\n")
    hdr = ("| Family | Runs | Accounting OK | Solvent | Plausible | "
           + " | ".join(SHORT[c] for c in CHECKS) + " |")
    add(hdr)
    add("|" + "---|" * (5 + len(CHECKS)))
    for f in fams:
        rs = by.get(f, [])
        if not rs:
            continue
        cnt = Counter(k for r in rs for k in r["first_fail"])
        nsol = sum(_solvent(r) for r in rs)
        add(f"| {f} | {len(rs)} | {sum(r['accounting_ok'] for r in rs)} | "
            f"{nsol} ({_pct(nsol, len(rs))}) | "
            f"{sum(r['plausible'] for r in rs)} ({_pct(sum(r['plausible'] for r in rs), len(rs))}) | "
            + " | ".join(str(cnt.get(c, 0)) for c in CHECKS) + " |")
    for form in ("ubc", "cash_ubi"):
        used = sum(mc[g][form]["used"] for g in mc)
        pl = sum(mc[g][form]["plausible"] for g in mc)
        cnt = Counter()
        for g in mc:
            cnt.update(mc[g][form]["fails"])
        add(f"| mc_{form} (draws) | {used} | {used} | — | {pl} ({_pct(pl, used)}) | "
            + " | ".join(str(cnt.get(c, 0)) for c in CHECKS) + " |")
    add("\n*Solvent = no household class with negative net worth or negative money. "
        "Check columns count runs failing that law at least once (a run can fail several).*\n")

    # --- cash vs UBC: who goes insolvent --------------------------------- #
    det = [r for r in rows if r["family"] in ("triad", "ubc_experiment", "frontier",
                                              "rich_frontier", "pooling")]
    add("### Insolvency by policy form (deterministic runs, all countries)\n")
    if closure == "legacy":
        add("| Policy form | Runs | Owners' money < 0 | Net worth < 0 |")
        add("|---|---|---|---|")
    else:
        add("| Policy form | Runs | Owners' money < 0 | Workers' money < 0 | Net worth < 0 |")
        add("|---|---|---|---|---|")
    for f in ("none", "cash", "ubc"):
        rs = [r for r in det if policy_form(r["scenario"]) == f]
        m = sum("money_split_shares_valid" in r["first_fail"] for r in rs)
        n = sum("hh_net_worth_nonnegative" in r["first_fail"] for r in rs)
        if closure == "legacy":
            add(f"| {f} | {len(rs)} | {m} ({_pct(m, len(rs))}) | {n} ({_pct(n, len(rs))}) |")
        else:
            mo = sum("owners" in r.get("neg_money", []) for r in rs)
            mw_ = sum("workers" in r.get("neg_money", []) for r in rs)
            add(f"| {f} | {len(rs)} | {mo} ({_pct(mo, len(rs))}) | {mw_} ({_pct(mw_, len(rs))}) "
                f"| {n} ({_pct(n, len(rs))}) |")
    mcn = {f: sum(mc[g][f]["fails"].get("hh_net_worth_nonnegative", 0) for g in mc) for f in ("ubc", "cash_ubi")}
    mcu = {f: sum(mc[g][f]["used"] for g in mc) for f in ("ubc", "cash_ubi")}
    if closure == "legacy":
        add(f"\nMonte Carlo: net worth < 0 in {mcn['ubc']:,}/{mcu['ubc']:,} UBC draws "
            f"({_pct(mcn['ubc'], mcu['ubc'])}) and {mcn['cash_ubi']:,}/{mcu['cash_ubi']:,} "
            f"cash draws ({_pct(mcn['cash_ubi'], mcu['cash_ubi'])}). Cash-UBI owners run "
            "negative money (an overdraft at the state) but their capital keeps them "
            "solvent; under UBC the capital passes to the fund, so the overdraft becomes "
            "insolvency.\n")
    else:
        add(f"\nMonte Carlo: net worth < 0 in {mcn['ubc']:,}/{mcu['ubc']:,} UBC draws "
            f"and {mcn['cash_ubi']:,}/{mcu['cash_ubi']:,} cash draws.\n")

    # --- baselines -------------------------------------------------------- #
    bad = [r for r in by.get("triad", []) if r["scenario"] == "Baseline" and not r["plausible"]]
    add("### Baselines (no AI shift, no policy)\n")
    if bad:
        add(f"{len(geos) - len(bad)} of {len(geos)} baselines pass. Failing:\n")
        for r in sorted(bad, key=lambda r: r["geo"]):
            ff = ", ".join(f"{SHORT[k]} from {y}" for k, y in sorted(r["first_fail"].items(), key=lambda kv: kv[1]))
            add(f"- **{r['geo']}:** {ff} (owners' MPC {r['a1_k']}, owners' money min "
                f"{r['min_owner_money_y0']} x Y0, max I/Y {r['max_inv_share']})")
        add("")
    else:
        add(f"All {len(geos)} baselines pass.\n")

    # --- published surfaces ------------------------------------------------ #
    def sel(fam, geos_=None, names=None, frontier=None, contains=None):
        out = []
        for r in by.get(fam, []):
            if geos_ and r["geo"] not in geos_:
                continue
            if names and r["scenario"] not in names:
                continue
            if frontier is not None and r.get("on_frontier") is not frontier:
                continue
            if contains and contains not in r["scenario"]:
                continue
            out.append(r)
        return out

    add("## Published numbers\n")
    add("| Surface | Runs behind it | Plausible | First failing laws (runs) |")
    add("|---|---|---|---|")
    surf = []
    de_arms = sel("ubc_experiment", ["DE"], UBC_ARMS)
    surf.append(("README headline + manifesto §III (DE: cash UBI vs UBC, wealth + growth)", de_arms))
    surf.append(("README frontier chart (DE/FR/SK, frontier points)",
                 sel("frontier", ["DE", "FR", "SK"], frontier=True)))
    surf.append(("Manifesto + dashboard frontier (DE, all 13 points)", sel("frontier", ["DE"])))
    surf.append(("Manifesto C1 ladder (DE, endogenous investment, cash vs UBC)",
                 [r for r in sel("c1_ladder", ["DE"])
                  if r["scenario"].startswith(UBC_ARMS)]))
    surf.append(("LinkedIn posts (DE/FR/SK cash vs UBC)",
                 sel("ubc_experiment", ["DE", "FR", "SK"], UBC_ARMS)))
    surf.append(("Dashboard (all countries: triad + UBC experiment + frontier)",
                 sel("triad") + sel("ubc_experiment") + sel("frontier")))
    surf.append(("F23 rich frontier (DE, all regimes)", sel("rich_frontier", ["DE"])))
    for label, rs in surf:
        add(f"| {label} | {len(rs)} | {_frac(rs)} | {_firsts(rs)} |")
    for s in pool:
        rs = [r for r in by.get("pooling", []) if r.get("bloc") == s["bloc"] and r.get("form") == s["form"]]
        add(f"| Pooled dividend, {s['bloc']}, {s['form']} ({s['n_viable']}/{s['n_geos']} countries viable) "
            f"| {len(rs)} | {_frac(rs)} | {_firsts(rs)} |")
    if "DE" in mc:
        for form in ("ubc", "cash_ubi"):
            a = mc["DE"][form]
            add(f"| F12 robustness bands (DE Monte Carlo, {form}) | {a['used']} draws | "
                f"{a['plausible']}/{a['used']} | "
                + (", ".join(f"{SHORT[k]} ({v})" for k, v in sorted(a["fails"].items(), key=lambda kv: -kv[1])) or "none")
                + " |")
    add("\nThe MCP tools and the agent crew use the orchestrator defaults, so they "
        "inherit the UBC-experiment and frontier rows above.\n")

    # --- DE headline arms in detail --------------------------------------- #
    add("### The README headline runs (DE)\n")
    add("| Run | Plausible | First failing law (year) | Owners' net worth, min (x Y0) | Owners' money, min (x Y0) | Max I/Y | Min Gini |")
    add("|---|---|---|---|---|---|---|")
    for r in sel("ubc_experiment", ["DE"]):
        ff = ", ".join(f"{SHORT[k]} ({y})" for k, y in sorted(r["first_fail"].items(), key=lambda kv: kv[1])) or "—"
        add(f"| {r['scenario']} | {'yes' if r['plausible'] else '**no**'} | {ff} | "
            f"{r['min_owner_nw_y0']} | {r['min_owner_money_y0']} | {r['max_inv_share']} | {r['min_gini']} |")
    add("")

    # --- by country ------------------------------------------------------- #
    add("## By country (plausible / runs)\n")
    add("| Country | Owners' MPC | Triad | UBC exp. | Frontier | Rich frontier | C1 ladder | MC UBC | MC cash | Worst owners' net worth (x Y0) |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    for g in geos:
        rg = [r for r in rows if r["geo"] == g and r["family"] != "pooling"]
        a1k = next((r["a1_k"] for r in rg if r["a1_k"] is not None), None)
        cells = [_frac([r for r in rg if r["family"] == f]) for f in fams[:-1]]
        m = mc.get(g, {})
        mcc = [f"{m[f]['plausible']}/{m[f]['used']}" if f in m else "—" for f in ("ubc", "cash_ubi")]
        worst = min((r["min_owner_nw_y0"] for r in rg if r["min_owner_nw_y0"] is not None), default=None)
        add(f"| {g} | {a1k} | " + " | ".join(cells + mcc) + f" | {worst} |")
    add("")
    if errors:
        add("## Errors and exclusions\n")
        for e in errors:
            add(f"- **{e['geo']} / {e['family']}:** {e['error']}")
        add("")
    add("## Reading\n")
    if closure != "legacy":
        _reading_b(add, rows, mc, by, step)
        if step == "C":
            _reading_c(add, rows, mc)
        return "\n".join(L) + "\n"
    add("- Every run counted above passes (or fails) the **accounting** gate exactly as "
        "before; the plausibility laws only add information.")
    add("- The dominant failure is **investment financing**: capex follows an exogenous "
        "path (+6%/yr under the AI shift), so investment outgrows 40% of GDP, and "
        "capital owners pay for it out of negative money. Under UBC that overdraft "
        "turns into insolvency because the owners' capital passes to the fund. In LV "
        "and RO it shows up even in the baseline, so it is a property of the closure, "
        "not of the AI scenario. That is the Phase 7 step B fix.")
    add("- The Gini floor mostly fails under UBC (the two-class lognormal compresses "
        "personal income below anything observed); it is an implausible-outcome "
        "flag, not an accounting defect, and is revisited after steps B-E.")
    add("- LU and SI calibrate a negative owners' MPC and IE starts with investment "
        "above 40% of GDP: those three countries' results are unusable under the "
        "current closure regardless of scenario.")
    add("- Until step B lands, no number in the rows marked implausible should be "
        "quoted; step F re-runs this audit in enforce mode on the fixed engine.")
    return "\n".join(L) + "\n"


def _reading_b(add, rows, mc, by, step="B"):
    cnt = Counter(k for r in rows for k in r["first_fail"])
    mcc = Counter()
    mc_money = Counter()
    for g in mc:
        for f in mc[g]:
            mcc.update(mc[g][f]["fails"])
            if mc[g][f]["fails"].get("money_split_shares_valid"):
                mc_money[g] += mc[g][f]["fails"]["money_split_shares_valid"]
    n_acc = sum(r["accounting_ok"] for r in rows)
    add(f"- **Accounting:** {n_acc:,} of {len(rows):,} runs balance their books.")
    nw = [r for r in rows if "hh_net_worth_nonnegative" in r["first_fail"]]
    if step == "C":
        add(f"- **Insolvency:** {len(nw)} runs and "
            f"{mcc.get('hh_net_worth_nonnegative', 0)} Monte-Carlo draws (step B: 2 "
            "runs). The SK runs that failed in step B reinvested without limit; with a "
            "capacity ceiling the fund invests by the owners' rule and the "
            "current-account deficit no longer compounds. The external-position "
            "rule behind them is still replaced in step D.")
    else:
        add(f"- **Insolvency (the step-B target):** {len(nw)} runs and "
            f"{mcc.get('hh_net_worth_nonnegative', 0)} Monte-Carlo draws"
            + (": " + "; ".join(f"{r['geo']} {r['scenario']}" for r in nw) if nw else "")
            + ". In those runs the fund owns all the capital and reinvests everything at "
            "home, the current-account deficit widens, and the model still assigns the "
            "capital-less owners a share of the country's foreign debt (external "
            "positions are allocated by money shares). That rule is replaced in step D. "
            "The gate now refuses such runs (net worth is a blocking law).")
    own = sorted({r["geo"] for r in rows if "owners" in r.get("neg_money", [])})
    wrk = sorted({r["geo"] for r in rows if "workers" in r.get("neg_money", [])})
    add(f"- **Negative money:** owners in {sum('owners' in r.get('neg_money', []) for r in rows)} "
        f"runs ({', '.join(own) or 'none'}), workers in "
        f"{sum('workers' in r.get('neg_money', []) for r in rows)} runs "
        f"({', '.join(wrk) or 'none'}); Monte-Carlo draws: "
        + (", ".join(f"{g} {n}" for g, n in sorted(mc_money.items())) or "none")
        + ". No owner overdraft remains outside countries whose calibration is "
        "unusable. Workers' overdrafts arise there too, and in trade-linked runs "
        "from the external-position rule. This law stays advisory until step D.")
    iy = [r for r in rows if "investment_share_bounded" in r["first_fail"]]
    iy_fund = sum(1 for r in iy if policy_form(r["scenario"]) == "ubc")
    if step == "C":
        iy_geo = sorted({r["geo"] for r in iy})
        add(f"- **Investment above 40% of GDP:** {len(iy)} runs ({iy_fund} of them UBC), "
            f"all in {', '.join(iy_geo) or 'no country'} (step B: 385 in the rich "
            "frontier alone). The fund now invests by the owners' rule, which "
            "responds to profitability and spare capacity, instead of sinking every "
            "retained euro into domestic capital.")
    else:
        add(f"- **Investment above 40% of GDP:** {len(iy)} runs ({iy_fund} of them UBC). "
            "Where the citizens' fund retains its profits it can only reinvest them in "
            "domestic fixed capital; a real fund would also buy financial and foreign "
            "assets. That outlet arrives with step D (the fund may buy foreign equity).")
    gf = [r for r in rows if "gini_floor" in r["first_fail"]]
    if step == "C":
        cash_g = sum(mc[g]["cash_ubi"]["fails"].get("gini_floor", 0)
                     for g in mc if "cash_ubi" in mc[g])
        add(f"- **Gini below 0.15:** {len(gf):,} runs and {mcc.get('gini_floor', 0):,} "
            f"draws, {cash_g:,} of them cash UBI (step B: 1,039 runs; 35 cash draws). "
            "Not a supply-side effect: "
            "until now every policy arm anchored its distribution on a year 0 with "
            "the policy already on, so the observed 2019 Gini was assigned to an "
            "economy paying a 40% levy and a UBI. With policies from 2020 the anchor "
            "is the real 2019 economy, and a double count in the distribution layer "
            "shows: the levy lowers the net capital share that drives *market* "
            "inequality and is also counted as a transfer. Fixed in step E.")
    else:
        add(f"- **Gini below 0.15:** {len(gf)} runs and {mcc.get('gini_floor', 0)} draws, "
            "almost all UBC. This is the distribution layer (two-class lognormal), not "
            "financing; it is revisited with step E and re-checked in step F.")
    mpc = sorted({r["geo"] for r in rows if "owners_mpc_in_unit_interval" in r["first_fail"]})
    add(f"- **Calibration:** owners' MPC outside [0, 1] in {', '.join(mpc) or 'no country'}; "
        "those countries' results stay unusable under this closure.")


def _reading_c(add, rows, mc):
    sup = [r for r in rows if r.get("max_inflation") is not None]
    if not sup:
        return
    form = defaultdict(list)
    for r in sup:
        form[policy_form(r["scenario"])].append(r)
    base = [r for r in sup if r["family"] == "triad" and r["scenario"] == "Baseline"]
    hot = [r["geo"] for r in base if r["ceiling_share"] > 0.25]
    add(f"- **Prices:** peak inflation above 5% in "
        f"{sum(r['max_inflation'] > 0.05 for r in sup)} of {len(sup):,} runs and above "
        f"10% in {sum(r['max_inflation'] > 0.10 for r in sup)}; deflation in "
        f"{sum(r['min_inflation'] < 0 for r in sup)} runs, all in "
        f"{', '.join(sorted({r['geo'] for r in sup if r['min_inflation'] < 0})) or 'none'}.")
    cells = []
    for k in ("none", "cash", "ubc"):
        rs = form.get(k, [])
        if rs:
            cells.append(f"{k} {sum(r['ceiling_share'] > 0 for r in rs)}/{len(rs)} "
                         f"({sum(r['ceiling_share'] > 0.25 for r in rs)} for over a "
                         "quarter of the years)")
    add("- **Capacity ceiling binds** (demand met by extra imports): " + "; ".join(cells)
        + ". Baselines at the ceiling: " + (", ".join(hot) or "none")
        + " (uniform K/Y = 3 calibration; step F).")
    low = sorted({r["geo"] for r in sup if r["min_utilisation"] < 0.70})
    add(f"- **Utilisation below 0.70** (below the 2009 trough): "
        f"{sum(r['min_utilisation'] < 0.70 for r in sup)} runs, in {', '.join(low) or 'none'}.")
    add("- Interest rates are still fixed (no monetary-policy response until the "
        "banks step), so demand-led growth is not yet leaned against.")


def compact(data):
    """Small machine-readable summary for docs/ (full rows stay in the parts)."""
    agg = defaultdict(lambda: dict(runs=0, accounting_ok=0, plausible=0, fails=Counter()))
    for r in data["rows"]:
        k = f"{r['geo']}|{r['family']}"
        a = agg[k]
        a["runs"] += 1
        a["accounting_ok"] += int(r["accounting_ok"])
        a["plausible"] += int(r["plausible"])
        a["fails"].update(r["first_fail"].keys())
    return {"generated": data.get("generated"), "thresholds": {
                "max_investment_share": MAX_INVESTMENT_SHARE,
                "min_personal_gini": MIN_PERSONAL_GINI},
            "by_geo_family": {k: {**v, "fails": dict(v["fails"])} for k, v in sorted(agg.items())},
            "monte_carlo": data["mc"], "pooling": data["pooling"], "errors": data["errors"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--geos", help="comma-separated geos (default: all members)")
    ap.add_argument("--mc", type=int, default=200, help="Monte-Carlo draws per form (0 = skip)")
    ap.add_argument("--pooling", action="store_true", help="run only the multi-region pooling family")
    ap.add_argument("--part", help="write a partial JSON here instead of the docs")
    ap.add_argument("--assemble", help="merge all *.json parts in this directory into the docs")
    ap.add_argument("--closure", choices=("behavioural", "legacy"), default="behavioural",
                    help="investment closure to audit (legacy = the v1.1 engine, step A)")
    ap.add_argument("--step", default="C",
                    help="Phase 7 step the behavioural audit documents (file suffix)")
    ap.add_argument("--out", help="report path (default: docs/AUDIT-2026-10[-step<S>].md)")
    ap.add_argument("--json", help="summary path (default: docs/audit-2026-10[-step<S>].json)")
    a = ap.parse_args()
    sfx = "" if a.closure == "legacy" else f"-step{a.step}"
    a.out = a.out or os.path.join(ROOT, "docs", f"AUDIT-2026-10{sfx}.md")
    a.json = a.json or os.path.join(ROOT, "docs", f"audit-2026-10{sfx}.json")

    if a.assemble:
        data = dict(rows=[], errors=[], mc={}, pooling=[])
        for fp in sorted(glob.glob(os.path.join(a.assemble, "*.json"))):
            d = json.load(open(fp, encoding="utf-8"))
            for k in ("rows", "errors", "pooling"):
                data[k] += d.get(k, [])
            data["mc"].update(d.get("mc", {}))
    else:
        data = dict(rows=[], errors=[], mc={}, pooling=[])
        if a.pooling:
            data["rows"], data["errors"], data["pooling"] = run_pooling(a.closure)
        else:
            geos = [g.strip().upper() for g in a.geos.split(",")] if a.geos else member_geos()
            data["rows"], data["errors"], data["mc"] = run_geos(geos, a.mc, a.closure)
            if not a.geos and not a.part:
                pr, pe, ps = run_pooling(a.closure)
                data["rows"] += pr
                data["errors"] += pe
                data["pooling"] = ps
    data.setdefault("closure", a.closure)
    data.setdefault("step", a.step)
    data["generated"] = time.strftime("%Y-%m-%d %H:%M")
    if a.part:
        os.makedirs(os.path.dirname(os.path.abspath(a.part)), exist_ok=True)
        json.dump(data, open(a.part, "w", encoding="utf-8"))
        print(f"wrote part {a.part}: {len(data['rows'])} rows")
        return
    open(a.out, "w", encoding="utf-8").write(build_report(data))
    json.dump(compact(data), open(a.json, "w", encoding="utf-8"), indent=1, default=dict)
    print(f"wrote {a.out} and {a.json}")


if __name__ == "__main__":
    main()
