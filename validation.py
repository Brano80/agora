"""Phase 7 step F validation: does the engine reproduce 2011-2019?

The model starts in 2010 from that year's data only (national accounts,
fiscal position, interest rates, capacity utilisation, external position and
capital stock, each summarised over the five years to 2010) and runs nine
years. It is fed what governments and the rest of the world decided:
    government spending  consumption P3_S13 + investment P51G (S13), nominal
    exports              P6, nominal (world demand)
    labour share         AMECO ALCD2
    policy rates         AMECO ISN (euro area for ECB followers, own for floaters)
Three variants separate the model's behaviour from its policy rules:
    fed          also the rate on new government borrowing (AMECO ILN, realised
                 long-term yields) and the net-tax ratio ((spending + primary
                 balance) / GDP, Eurostat) relative to 2010, scaling both tax
                 rates: tests private behaviour, prices and the external side
    spread_rule  as fed, but new borrowing pays the model's rule (policy rate +
                 2010 spread + premium on debt added beyond the realised
                 euro-area path)
    rules        as spread_rule, and taxes follow the model's fiscal rule (Bohn
                 0.034 toward the 2010 debt ratio): the policy rules the 30-year
                 projections use
Everything else is the model's: consumption, private investment, imports,
prices, output, debt, the current account.

Government investment is moved from investment into government spending for
the backtest: it is a budget decision, not private behaviour (the 30-year
projections still treat all investment as private behaviour; a residual).
Taxes start from the OBSERVED 2010 primary balance (the projections start from
the structural one). One-off capital transfers (bank rescues: IE 2010, ES 2012,
SI 2013, CY, EL; net capital transfers above their 2001-2008 average, Eurostat
gov_10a_main D9) are taken out of the fiscal stance - they recapitalised banks
and did not reach households - and out of the realised debt the model is
scored against (the raw debt error is reported too).

Every result is a change since 2010, so the base year matches by construction.
Errors: log points for levels (real GDP, real consumption, real private
investment), percentage points for inflation and for the change in ratios
(public debt, current account, private-sector balance). The private-sector
balance (current account minus government net lending) replaces the household
saving rate the plan named: the model has no corporate sector, so its owners'
saving includes firms' retained profits and has no household-only counterpart.

Two benchmarks:
    random walk   levels grow at their 2000-2010 average; ratios stay at their
                  2010 value; inflation at its 2000-2010 average
    static        same inputs as the model (spending, exports): GDP from the
                  expenditure identity with consumption, private investment,
                  inventories and imports at their 2010 shares of GDP; prices
                  at the 2000-2010 average inflation; debt from the 2010 net-tax
                  share and implicit rate; current account from trade plus the
                  2010 income balance; private balance from the two
"""
from __future__ import annotations

import math
import statistics
from typing import Dict, List, Optional

from data.connectors.fiscal import CACHE as FISCAL_CACHE, _load as _fiscal_load
from data.connectors.history import history_for
from data.connectors.rates import (CACHE as RATES_CACHE, ECB_FOLLOWERS, EURO_AREA,
                                   _load as _rates_load)
from contextlib import contextmanager

import modules.sfc_core as _core
from modules.interface import LeverPath, Scenario
from modules.sfc_core import SFCCore

# The engine as frozen for the blind run (step F4a: the capital stock from
# data, nothing else) and as it stands after the disclosed step F4b fixes.
ENGINE_CONFIGS = {
    "blind": {"flags": {"CAPITAL_FROM_DATA": True, "TREND_FROM_DATA": False,
                        "STAND_IN_BY_RULE": False},
              "core": {"legacy_loans": False, "consumption_adjustment": 1.0}},
    "final": {"flags": {}, "core": {}},
}


@contextmanager
def engine_config(name: str = "final"):
    """Run the block with the engine switched to a configuration."""
    cfg = ENGINE_CONFIGS[name]
    old = {k: getattr(_core, k) for k in cfg["flags"]}
    for k, v in cfg["flags"].items():
        setattr(_core, k, v)
    try:
        yield dict(cfg["core"])
    finally:
        for k, v in old.items():
            setattr(_core, k, v)


BASE, END = 2010, 2019
PRE = (2000, 2010)                       # benchmark pre-sample
CRISIS = (2011, 2013)                    # euro-crisis years, reported separately
EA_MEMBERS = ["AT", "BE", "CY", "DE", "EE", "EL", "ES", "FI", "FR", "HR", "IE", "IT", "LT",
              "LU", "LV", "MT", "NL", "PT", "SI", "SK"]
LEVELS = ("gdp_real", "consumption_real", "investment_real")
RATIOS = ("debt_gdp", "ca_gdp", "private_balance")
VARIANTS = ("fed", "spread_rule", "rules")
VARIABLES = LEVELS + ("inflation",) + RATIOS
LABELS = {"gdp_real": "real GDP", "consumption_real": "real consumption",
          "investment_real": "real private investment", "inflation": "inflation",
          "debt_gdp": "public debt / GDP", "ca_gdp": "current account / GDP",
          "private_balance": "private-sector balance / GDP"}


def _fiscal_series(geo: str) -> Dict[str, Dict[int, float]]:
    import os
    rec = _fiscal_load(FISCAL_CACHE, os.path.getmtime(FISCAL_CACHE)).get(geo.upper(), {})
    return {k: {int(y): v for y, v in s.items()} for k, s in rec.get("series", {}).items()}


def _rate_series(geo: str) -> Dict[str, Dict[int, float]]:
    import os
    rec = _rates_load(RATES_CACHE, os.path.getmtime(RATES_CACHE)).get(geo.upper(), {})
    return {k: {int(y): v for y, v in s.items()} for k, s in rec.get("series", {}).items()}


def euro_debt_path(years: List[int]) -> List[float]:
    """Realised euro-area (EA20) debt / GDP, GDP-weighted over the 20 members."""
    out = []
    for y in years:
        num = den = 0.0
        for g in EA_MEMBERS:
            gd = _fiscal_series(g).get("GD", {}).get(y)
            gdp = history_for(g).get("gdp", {}).get(y)
            if gd is not None and gdp:
                num += gd / 100.0 * gdp
                den += gdp
        out.append(num / den if den else float("nan"))
    return out


def actuals(geo: str) -> Dict[str, Dict[int, float]]:
    """The realised paths in model units (levels in MEUR / volumes, ratios as fractions)."""
    h, f = history_for(geo), _fiscal_series(geo)
    out: Dict[str, Dict[int, float]] = {k: {} for k in VARIABLES}
    out["deflator"], out["debt_gdp_raw"] = {}, {}
    cum = 0.0                                  # one-offs since the base year, MEUR
    for y in range(PRE[0] - 1, END + 1):
        try:
            out["gdp_real"][y] = h["gdp_real"][y]
            out["consumption_real"][y] = h["hh_consumption_real"][y]
            priv = (h["gfcf"][y] - h["gov_gfcf"][y]) / h["gfcf"][y]   # private share, nominal
            out["investment_real"][y] = h["gfcf_real"][y] * priv
            out["deflator"][y] = h["gdp"][y] / h["gdp_real"][y]
        except KeyError:
            pass
        if y > BASE and y in h.get("gdp", {}):
            cum += one_off(geo, y) * h["gdp"][y]
        if y in f.get("GD", {}):
            out["debt_gdp_raw"][y] = f["GD"][y] / 100.0
            out["debt_gdp"][y] = f["GD"][y] / 100.0 - (cum / h["gdp"][y] if y > BASE else 0.0)
        if y in h.get("ca_gdp", {}):
            out["ca_gdp"][y] = h["ca_gdp"][y] / 100.0
        if y in h.get("ca_gdp", {}) and y in f.get("B9", {}):
            # the private sector's balance; one-off rescues are a transfer
            # between government and banks, so they cancel out of CA - B9
            out["private_balance"][y] = (h["ca_gdp"][y] / 100.0 - f["B9"][y] / 100.0
                                         - one_off(geo, y))
    d = out["deflator"]
    out["inflation"] = {y: d[y] / d[y - 1] - 1.0 for y in d if y - 1 in d}
    return out


def base_data(geo: str, year: int = BASE) -> Dict[str, float]:
    """The calibration inputs for the base year, government investment moved
    from investment to government spending."""
    h, f = history_for(geo), _fiscal_series(geo)
    gi = h["gov_gfcf"][year]
    gini = h.get("gini_disp_income", {})
    data = {"gdp": h["gdp"][year], "hh_consumption": h["hh_consumption"][year],
            "gov_consumption": h["gov_consumption"][year] + gi,
            "gfcf": h["gfcf"][year] - gi, "gcf": h["gcf"][year] - gi,
            "exports": h["exports"][year], "imports": h["imports"][year],
            "labour_share": h["labour_share"][year], "gov_debt_gdp": f["GD"][year],
            # the Gini only labels the calibration targets (the macro engine
            # does not use it); the earliest available year stands in
            "gini_disp_income": (gini.get(year) if year in gini
                                 else gini[min(gini)] if gini else 30.0)}
    data["_sources"] = {k: "history_panel" for k in data}
    return data


def _paths(geo: str, H: int) -> Dict[str, List[float]]:
    h = history_for(geo)
    yrs = range(BASE, BASE + H)
    own, ea = _rate_series(geo), _rate_series(EURO_AREA)
    return {"labour_share": [h["labour_share"][y] / 100.0 for y in yrs],
            "gov": [h["gov_consumption"][y] + h["gov_gfcf"][y] for y in yrs],
            "exports": [h["exports"][y] for y in yrs],
            "ea_policy": [ea["ISN"][y] / 100.0 for y in yrs],
            "own_policy": [own.get("ISN", {}).get(y, ea["ISN"][y]) / 100.0 for y in yrs],
            "yields": [own.get("ILN", {}).get(y, ea["ILN"][y]) / 100.0 for y in yrs],
            "net_tax": [_net_tax(geo, y) / _net_tax(geo, BASE) for y in yrs]}


ONE_OFF_NORM = (2001, 2008)              # "normal" net capital transfers


def one_off(geo: str, y: int) -> float:
    """One-off capital transfers (bank rescues), share of GDP: net capital
    transfers paid above their 2001-2008 average."""
    h = history_for(geo)
    pay, rec = h.get("gov_d9pay_gdp", {}), h.get("gov_d9rec_gdp", {})
    net = {t: (pay[t] - rec[t]) / 100.0 for t in pay if t in rec}
    norm = [net[t] for t in range(ONE_OFF_NORM[0], ONE_OFF_NORM[1] + 1) if t in net]
    if y not in net or not norm:
        return 0.0
    return max(0.0, net[y] - statistics.mean(norm))


def primary_balance(geo: str, y: int) -> float:
    """Primary balance excluding one-off capital transfers, share of GDP."""
    f = _fiscal_series(geo)
    return (f["B9"][y] + f["D41PAY"][y]) / 100.0 + one_off(geo, y)


def _net_tax(geo: str, y: int) -> float:
    """Net taxes (all revenue less all spending other than consumption,
    investment and one-off capital transfers) / GDP = (G + primary balance) / GDP."""
    h = history_for(geo)
    G = h["gov_consumption"][y] + h["gov_gfcf"][y]
    return G / h["gdp"][y] + primary_balance(geo, y)


def run_model(geo: str, variant: str = "fed", H: int = END - BASE + 1,
              **core_kwargs) -> Dict[str, Dict[int, float]]:
    """The model's 2010-2019 paths (same units as actuals())."""
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}")
    g = geo.upper()
    data = base_data(g)
    pth = _paths(g, H)
    pb_obs = primary_balance(g, BASE)
    kw = dict(base_year=BASE, investment_closure="behavioural", banks=True,
              calib_kwargs={"primary_balance": pb_obs})
    if g in ECB_FOLLOWERS:
        kw["policy_rate_path"] = pth["ea_policy"]
    else:
        kw["own_rate_path"] = pth["own_policy"]
    # the risk premium is measured against the realised euro-area debt path
    kw["euro_debt_path"] = euro_debt_path(list(range(BASE, BASE + H)))
    if variant == "fed":
        kw["gov_rate_path"] = pth["yields"]
    if variant in ("fed", "spread_rule"):
        kw["tax_scale_path"] = pth["net_tax"]
        kw["fiscal_reaction"] = 0.0
    kw.update(core_kwargs)
    core = SFCCore(**kw)
    p, _ = core._calibrate(g, data)
    scen = Scenario(name=f"backtest {variant}", horizon=H, geo=g,
                    labour_share=LeverPath(pth["labour_share"]),
                    ai_capex=LeverPath(p.a_ratio0), gov_ratio=LeverPath(p.g_ratio),
                    tax_income=LeverPath(p.theta),
                    gov_override=LeverPath(pth["gov"]),
                    exports_override=LeverPath(pth["exports"]))
    res = core.run(scen, data)
    out: Dict[str, Dict[int, float]] = {k: {} for k in VARIABLES}
    out["meta"] = res.meta
    out["result"] = res
    for t, per in enumerate(res.periods):
        r, y = per.reported, BASE + t
        P = r["price_level"]
        out["gdp_real"][y] = r["gdp_real"]
        out["consumption_real"][y] = r["consumption"] / P
        out["investment_real"][y] = r["investment"] / P
        out["inflation"][y] = r["inflation"]
        out["debt_gdp"][y] = r["gov_debt"] / r["gdp"]
        out["ca_gdp"][y] = r["current_account"] / r["gdp"]
        out["private_balance"][y] = (r["current_account"] + r["deficit"]) / r["gdp"]
    return out


def _cagr(ser: Dict[int, float], a: int, b: int) -> float:
    return (ser[b] / ser[a]) ** (1.0 / (b - a)) - 1.0


def random_walk(act: Dict[str, Dict[int, float]], H: int = END - BASE + 1) -> Dict[str, Dict[int, float]]:
    out: Dict[str, Dict[int, float]] = {k: {} for k in VARIABLES}
    pre = (max(PRE[0], min(act["gdp_real"])), PRE[1])
    infl = statistics.mean(act["inflation"][y] for y in range(pre[0] + 1, pre[1] + 1)
                           if y in act["inflation"])
    for k in LEVELS:
        g = _cagr(act[k], pre[0], pre[1])
        for t in range(H):
            out[k][BASE + t] = act[k][BASE] * (1.0 + g) ** t
    for t in range(H):
        out["inflation"][BASE + t] = infl
        for k in RATIOS:
            if BASE in act[k]:
                out[k][BASE + t] = act[k][BASE]
    return out


def static_multiplier(geo: str, act: Dict[str, Dict[int, float]],
                      H: int = END - BASE + 1) -> Dict[str, Dict[int, float]]:
    """GDP from the fed spending and exports with every other demand component
    at its 2010 share; debt from the 2010 net-tax share and implicit rate."""
    d = base_data(geo)
    pth = _paths(geo, H)
    f = _fiscal_series(geo)
    Y0 = d["hh_consumption"] + d["gfcf"] + d["gov_consumption"] + d["exports"] - d["imports"] \
        + (d["gcf"] - d["gfcf"])
    c, i, m = d["hh_consumption"] / Y0, d["gfcf"] / Y0, d["imports"] / Y0
    inv = (d["gcf"] - d["gfcf"]) / Y0
    pb0 = primary_balance(geo, BASE)
    tax = (d["gov_consumption"] + pb0 * d["gdp"]) / Y0             # net taxes / GDP
    i_g = f["D41PAY"][BASE] / f["GD"][BASE - 1]                    # 2010 implicit rate
    pre = (max(PRE[0], min(act["gdp_real"])), PRE[1])
    infl = statistics.mean(act["inflation"][y] for y in range(pre[0] + 1, pre[1] + 1)
                           if y in act["inflation"])
    inc0 = act["ca_gdp"].get(BASE, 0.0) - (d["exports"] - d["imports"]) / Y0   # income balance
    out: Dict[str, Dict[int, float]] = {k: {} for k in VARIABLES}
    B = d["gov_debt_gdp"] / 100.0 * d["gdp"]
    for t in range(H):
        y = BASE + t
        G, X = pth["gov"][t], pth["exports"][t]
        Y = (G + X) / (1.0 - c - i - inv + m)
        P = (1.0 + infl) ** t
        bal = tax * Y - G - i_g * B                                # government balance
        if t > 0:
            B = B - bal
        out["gdp_real"][y] = Y / P
        out["consumption_real"][y] = c * Y / P
        out["investment_real"][y] = i * Y / P
        out["inflation"][y] = infl
        out["debt_gdp"][y] = B / Y
        out["ca_gdp"][y] = (X - m * Y) / Y + inc0
        out["private_balance"][y] = out["ca_gdp"][y] - bal / Y
    return out


def errors(path: Dict[str, Dict[int, float]], act: Dict[str, Dict[int, float]]
           ) -> Dict[str, Dict[int, float]]:
    """Per-year errors of the change since 2010: log points x 100 for levels,
    percentage points for inflation and ratios."""
    out: Dict[str, Dict[int, float]] = {}
    for k in VARIABLES:
        e = {}
        for y in range(BASE + 1, END + 1):
            if y not in path.get(k, {}) or y not in act.get(k, {}):
                continue
            mv, av = path[k][y], act[k][y]
            if k in LEVELS:
                if mv <= 0 or av <= 0:
                    continue
                e[y] = 100.0 * (math.log(mv / path[k][BASE]) - math.log(av / act[k][BASE]))
            elif k == "inflation":
                e[y] = 100.0 * (mv - av)
            else:
                if BASE not in path[k] or BASE not in act[k]:
                    continue
                e[y] = 100.0 * ((mv - path[k][BASE]) - (av - act[k][BASE]))
            if not math.isfinite(e[y]):
                del e[y]
        out[k] = e
    return out


def summary(err: Dict[str, Dict[int, float]]) -> Dict[str, Dict[str, Optional[float]]]:
    def mae(vals):
        vals = [abs(v) for v in vals]
        return statistics.mean(vals) if vals else None
    out = {}
    for k, e in err.items():
        out[k] = {"mae": mae(e.values()),
                  "mae_crisis": mae(v for y, v in e.items() if CRISIS[0] <= y <= CRISIS[1]),
                  "mae_after": mae(v for y, v in e.items() if y > CRISIS[1]),
                  "end": e.get(END)}
    return out


def backtest_country(geo: str, config: str = "final") -> Dict[str, object]:
    with engine_config(config) as core:
        return _backtest_country(geo, core)


def _backtest_country(geo: str, core: dict) -> Dict[str, object]:
    act = actuals(geo)
    rw, st = random_walk(act), static_multiplier(geo, act)
    out = {"geo": geo.upper(), "benchmarks": {"random_walk": summary(errors(rw, act)),
                                               "static": summary(errors(st, act))},
           "model": {}, "paths": {"actual": act, "random_walk": rw, "static": st}}
    for v in VARIANTS:
        try:
            mp = run_model(geo, v, **core)
        except Exception as e:                     # recorded, not hidden
            out["model"][v] = {"error": f"{type(e).__name__}: {e}"}
            continue
        res = mp.pop("result")
        meta = mp.pop("meta")
        out["model"][v] = summary(errors(mp, act))
        raw = dict(act, debt_gdp=act["debt_gdp_raw"])
        out["model"][v]["debt_gdp_raw"] = summary(errors(mp, raw))["debt_gdp"]
        out["paths"][v] = mp
        out.setdefault("calibration", {
            "owners_mpc": meta.get("owners_mpc"), "workers_mpc": meta.get("workers_mpc"),
            "capacity_base": (meta.get("capacity_utilisation") or {}).get("base"),
            "capacity_normal": (meta.get("capacity_utilisation") or {}).get("normal"),
            "theta": (meta.get("params") or {}).get("theta"),
            "accounting_ok": True})
        out.setdefault("min_utilisation", {})[v] = min(p.reported["utilisation"]
                                                       for p in res.periods)
    return out


# --------------------------------------------------------------------------- #
# F1b: fiscal multipliers against the literature
# --------------------------------------------------------------------------- #
# A stimulus of 1% of baseline GDP in 2020 and 2021 (the design of Kilponen et
# al. 2015, NBB WP 278 / ECB WP 1760: temporary, two years, then the fiscal
# rule), in the 2019 calibration with no AI shift. Multiplier = change in real
# GDP / (1% of baseline real GDP), year by year.
MULT_SIZE = 0.01
MULT_YEARS = (1, 2)
INSTRUMENTS = ("spending", "labour_tax", "capital_tax")
# Reference ranges, first year (models) or cumulative (meta-analyses):
LITERATURE = {
    "spending": {
        "Kilponen et al. 2015, 15 European central-bank models, year 1, policy rate by rule":
            "0.50-0.98 (DE 0.52, FR 0.92, IT 0.79, ES 0.50, NL 0.74, euro area 0.98)",
        "same, policy rate fixed for two years": "euro area 1.39",
        "Gechert 2015, meta-analysis of 104 studies": "about 0.85 (public investment ~0.5 higher)",
        "Gechert & Rannenberg 2018, meta-regression": "0.4-0.7 in normal times; +0.6-0.8 in downturns",
        "Ilzetzki, Mendoza & Vegh 2013, 44 countries": "about 0 on impact in open or high-debt economies; above 1 in the long run under fixed exchange rates"},
    "labour_tax": {
        "Kilponen et al. 2015, year 1, policy rate by rule": "0.04-0.51 (DE 0.10, FR 0.13, IT 0.06, ES 0.13, NL 0.11, euro area 0.11)",
        "Gechert 2015": "tax and transfer multipliers 0.3-0.4 below spending (raw means: tax 0.54, transfers 0.39)",
        "Gechert & Rannenberg 2018": "transfers ~0.3 below spending in normal times, the largest in downturns"},
    "capital_tax": {
        "Kilponen et al. 2015, year 1, policy rate by rule": "0.02-0.65 (DE 0.05, FR 0.07, IT 0.08, ES 0.09, euro area 0.12)"},
}


def multipliers(geo: str, fiscal_rule: bool = True, horizon: int = 8,
                config: str = "final") -> Dict[str, object]:
    """Year-1 and year-2 real-GDP multipliers of the three instruments."""
    with engine_config(config) as core:
        return _multipliers(geo, fiscal_rule, horizon, core)


def _multipliers(geo: str, fiscal_rule: bool, horizon: int, core: dict) -> Dict[str, object]:
    from orchestrator import AgoraOrchestrator
    from scenarios import make_triad
    o = AgoraOrchestrator(geo=geo, allow_live=False)
    data = o.load_data()
    p = o.params()
    scen = make_triad(p, horizon=horizon)[0]                  # the no-shock baseline
    kw = dict(core) if fiscal_rule else dict(core, fiscal_reaction=0.0)
    base = SFCCore(**kw).run(scen, data)
    rb = [per.reported for per in base.periods]
    G0 = [r["gov_expenditure"] for r in rb]
    import copy
    pinned = copy.copy(scen)
    pinned.gov_override = LeverPath(G0)                        # the baseline, spending pinned
    ref = SFCCore(**kw).run(pinned, data)
    out = {"geo": geo, "fiscal_rule": fiscal_rule,
           "reproduces": max(abs(a.reported["gdp_real"] / b["gdp_real"] - 1.0)
                             for a, b in zip(ref.periods, rb))}
    shocks = {}
    for inst in INSTRUMENTS:
        sc, core_kw = copy.copy(pinned), dict(kw)
        if inst == "spending":
            sc.gov_override = LeverPath([G0[t] + (MULT_SIZE * rb[t]["gdp"] if t in MULT_YEARS else 0.0)
                                         for t in range(horizon)])
        elif inst == "labour_tax":
            core_kw["labour_tax_shift_path"] = [(-MULT_SIZE * rb[t]["gdp"] / rb[t]["wage_bill"])
                                                if t in MULT_YEARS else 0.0 for t in range(horizon)]
        else:
            core_kw["capital_tax_shift_path"] = [(-MULT_SIZE * rb[t]["gdp"] / rb[t]["profits"])
                                                 if t in MULT_YEARS else 0.0 for t in range(horizon)]
        res = SFCCore(**core_kw).run(sc, data)
        m = [(res.periods[t].reported["gdp_real"] / ref.periods[t].reported["gdp_real"] - 1.0)
             / MULT_SIZE for t in range(horizon)]
        shocks[inst] = {"year1": m[1], "year2": m[2], "year3": m[3],
                        "ceiling_years": sum(per.reported["excess_imports"] > 0
                                             for per in res.periods[1:3])}
    out["multipliers"] = shocks
    return out
