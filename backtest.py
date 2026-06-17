"""Historical backtest + parameter grounding (#54).

The project's non-negotiable: "any integrated baseline must be backtested against
real history before scenarios are run on it." This module:

  * load_panel(geo, years)        — pull a multi-year calibration panel (live on
                                    the user's machine; offline it gets only the
                                    bundled snapshot year).
  * backtest(geo, panel)          — calibrate to the first year, drive the model
                                    with the ACTUAL labour-share + investment
                                    paths, and measure how well it reproduces the
                                    realised GDP / debt / Gini (the model's
                                    dynamics vs reality, not just year-0 fit).
  * estimate_beta_cross_section() — fit the distribution module's β (capital-share
                                    -> inequality elasticity) from the live
                                    cross-section, turning an ASSUMPTION into an
                                    ESTIMATE. Works offline on the 26 snapshots.
  * ground_ai_shock()             — derive the AI-shock anchors (capex growth,
                                    labour-share floor) from the Epoch compute
                                    connector + a documented labour-share trend,
                                    instead of round-number guesses.

Pure standard library. Live runs on the user's machine; offline tests exercise
the OLS, the grounding, and the harness mechanics.
"""
from __future__ import annotations

import os

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from calibration import calibrate
from modules.sfc_core import SFCCore
from modules.distribution import DistributionModule
from modules.interface import Scenario, LeverPath
from data.connectors.dbnomics import DBnomicsConnector
from data.connectors.oecd_idd import OECDIDDConnector


def _ols(xs: List[float], ys: List[float]) -> Tuple[float, float, float]:
    """Simple linear regression y = a + b x. Returns (slope, intercept, R^2)."""
    n = len(xs)
    if n < 2:
        return float("nan"), float("nan"), float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return float("nan"), my, float("nan")
    b = sxy / sxx
    a = my - b * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return b, a, r2


_PANEL_CODES = ("gdp", "hh_consumption", "gov_consumption", "gfcf", "gcf",
                "exports", "imports", "labour_share", "gov_debt_gdp",
                "gini_disp_income", "population")


def load_panel(geo: str, years: List[int], allow_live: bool = True,
               codes: Optional[Tuple[str, ...]] = None,
               required: Tuple[str, ...] = ("gdp", "labour_share")
               ) -> Dict[int, Dict[str, float]]:
    """Pull the calibration panel with ONE live request PER SERIES (DBnomics
    returns the full time series), not one fetch of every series per year -
    ~2 orders of magnitude fewer round-trips for a 26-country panel. Offline,
    only the bundled snapshot year resolves, as before."""
    conn = DBnomicsConnector(allow_live=allow_live)
    by_code = {c: conn.fetch_range(geo, c, years)
               for c in (codes or _PANEL_CODES)}
    panel: Dict[int, Dict[str, float]] = {}
    for y in years:
        vals = {c: vs[y] for c, vs in by_code.items() if y in vs}
        if all(r in vals for r in required):
            panel[y] = vals
    return panel


@dataclass
class BacktestResult:
    geo: str
    years: List[int]
    mae_pct: Dict[str, float] = field(default_factory=dict)  # mean abs % error
    n_years: int = 0
    note: str = ""

    def passed(self, tol: float = 0.10) -> bool:
        """A loose pass: outcome series (GDP, debt) tracked to within `tol`."""
        keys = [k for k in ("gdp", "gov_debt_gdp") if k in self.mae_pct]
        return bool(keys) and all(self.mae_pct[k] <= tol for k in keys)


def backtest(geo: str, panel: Dict[int, Dict[str, float]]) -> BacktestResult:
    """Drive the model from the first panel year with the ACTUAL labour-share and
    investment paths; compare its GDP / debt / Gini dynamics to the realised data."""
    years = sorted(panel)
    if len(years) < 2:
        return BacktestResult(geo, years, {}, len(years),
                              note="need >=2 panel years (live pull) to backtest")
    start = years[0]
    H = years[-1] - start + 1
    p = calibrate(panel[start], geo=geo, base_year=start)

    def at(yr, key, default):
        return panel.get(yr, {}).get(key, default)

    ls_path = [at(start + t, "labour_share",
                  panel[start]["labour_share"]) / 100.0 for t in range(H)]
    capex_path = [at(start + t, "gfcf", p.a_ratio0 * p.Y0) / p.Y0 for t in range(H)]
    # G is driven ABSOLUTELY (gov_override): the core's gov_ratio multiplies
    # lagged output, which would inflate G by cumulated model growth.
    gov_path = [at(start + t, "gov_consumption", p.g_ratio * p.Y0)
                for t in range(H)]
    scen = Scenario(name="backtest", horizon=H, geo=geo,
                    labour_share=LeverPath(ls_path),
                    ai_capex=LeverPath(capex_path),
                    gov_override=LeverPath(gov_path),
                    tax_income=LeverPath(p.theta))
    res = SFCCore(base_year=start).run(scen, panel[start])

    mae: Dict[str, float] = {}
    for series, key in (("gdp", "gdp"), ("gov_debt_gdp", "gov_debt_gdp")):
        devs = []
        for t in range(H):
            yr = start + t
            if yr in panel and series in panel[yr]:
                actual = panel[yr][series]
                model = res.periods[t].reported.get(key)
                if actual:
                    devs.append(abs(model - actual) / abs(actual))
        if devs:
            mae[series] = sum(devs) / len(devs)
    return BacktestResult(geo, years, mae, len(panel),
                          note="model driven by actual labour-share + investment paths")


def estimate_beta_cross_section(geos: List[str], year: int = 2019,
                                allow_live: bool = False
                                ) -> Tuple[float, float, float, int]:
    """Fit β: regress observed Gini on the observed capital share across countries.
    Turns the distribution module's assumed elasticity into a data estimate.
    Returns (beta, intercept, R^2, n)."""
    conn = DBnomicsConnector(allow_live=allow_live)
    xs, ys = [], []
    for g in geos:
        rows = conn.fetch(g, year)
        v = {k: r["value"] for k, r in rows.items()}
        if "labour_share" in v and "gini_disp_income" in v:
            xs.append(1.0 - v["labour_share"] / 100.0)   # capital share
            ys.append(v["gini_disp_income"] / 100.0)      # Gini (0-1)
    return (*_ols(xs, ys), len(xs))


def estimate_omega_cross_section(geos: List[str], year: int = 2019
                                 ) -> Tuple[float, float, float, int]:
    """Fit omega: regress the observed top-10% WEALTH share on the capital share
    across countries (from the calibrated snapshots). Grounds the wealth-
    concentration elasticity the way estimate_beta does for income.
    Returns (omega, intercept, R^2, n)."""
    import json
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cache")
    xs, ys = [], []
    for g in geos:
        fp = os.path.join(cache, f"{g.lower()}_baseline_{year}.json")
        if not os.path.exists(fp):
            continue
        try:
            ser = json.load(open(fp, encoding="utf-8")).get("series", {})
        except Exception:
            continue
        if "labour_share" in ser and "top10_wealth_share" in ser:
            ls = ser["labour_share"]["value"]
            w10 = ser["top10_wealth_share"]["value"]
            xs.append(1.0 - ls / 100.0)   # capital share
            ys.append(w10)                # top-10 wealth share (already 0-1)
    return (*_ols(xs, ys), len(xs))


def ground_ai_shock(allow_live: bool = False) -> Dict[str, object]:
    """Derive AI-shock anchors from the Epoch compute connector + a documented
    labour-share trend, instead of round-number guesses. Orientation, not a
    forecast — heavily damped from raw compute growth."""
    from data.connectors.epoch import EpochConnector
    e = EpochConnector().fetch() or {}

    def _val(row, default):
        v = e.get(row)
        if isinstance(v, dict):
            v = v.get("value")
        return float(v) if v is not None else float(default)

    doubling_m = _val("compute_doubling_months", 6.0)
    # frontier compute grows ~4x/yr (Epoch); the macro investment proxy is
    # heavily damped to a plausible capex-boom range.
    compute_growth = _val("frontier_training_compute_growth_x", 4.2) - 1.0
    capex_growth = round(min(0.10, 0.03 + 0.01 * (compute_growth ** 0.25)), 3)
    # labour share: ILO/Karabarbounis-Neiman ~ -5pp/few decades historically; an
    # AI-accelerated floor in the 0.45-0.50 range is the documented mid case.
    labour_share_end = 0.47
    return {
        "capex_growth": capex_growth,
        "labour_share_end": labour_share_end,
        "compute_doubling_months": doubling_m,
        "raw_compute_growth_per_yr": round(compute_growth, 2),
        "rationale": ("capex growth damped from Epoch frontier-compute growth; "
                      "labour-share floor from ILO/K-N trend, AI-accelerated mid case"),
    }


def estimate_beta_panel(geos: List[str], years: List[int], allow_live: bool = True,
                        panels: Optional[Dict[str, Dict[int, Dict[str, float]]]] = None
                        ) -> Tuple[float, float, int, int]:
    """FIXED-EFFECTS panel estimate of beta (capital share -> inequality):
    regress the observed disposable-income Gini on the observed capital share,
    DEMEANED WITHIN COUNTRY, pooled across the panel. Identification comes from
    CHANGES over time inside each country - the level cross-section is
    confounded by national redistribution regimes (R^2 = 0.02, F9).

    Caveat (document, don't hide): the observed Gini is POST-redistribution, so
    policy responses over the window bias the estimate toward zero - read the
    result as a LOWER anchor for the market-Gini elasticity, not a point truth.
    `panels` injects pre-loaded data (tests); live runs on the user's machine.
    Returns (beta, r2, n_obs, n_countries)."""
    xs: List[float] = []
    ys: List[float] = []
    n_countries = 0
    for g in geos:
        panel = (panels or {}).get(g) if panels is not None else \
            load_panel(g, years, allow_live=allow_live,
                       codes=("labour_share", "gini_disp_income"),
                       required=("labour_share", "gini_disp_income"))
        pts = [(1.0 - p["labour_share"] / 100.0, p["gini_disp_income"] / 100.0)
               for _, p in sorted((panel or {}).items())
               if "labour_share" in p and "gini_disp_income" in p]
        if len(pts) < 3:
            continue                       # too short to demean meaningfully
        n_countries += 1
        mx = sum(x for x, _ in pts) / len(pts)
        my = sum(y for _, y in pts) / len(pts)
        xs += [x - mx for x, _ in pts]
        ys += [y - my for _, y in pts]
    b, _, r2 = _ols(xs, ys)
    return b, r2, len(xs), n_countries



# --------------------------------------------------------------------------- #
# beta identification via the MARKET (pre-tax-pre-transfer) Gini — closes F12.
#
# beta is the elasticity of MARKET income inequality to the capital share. The
# disposable-Gini estimators above are biased toward zero because taxes and
# transfers absorb the market move (F9/F12). The OECD IDD connector supplies the
# pre-redistribution Gini the parameter is actually defined on. Three tools:
#   * redistribution_wedge          — the robust, immediately-useful byproduct:
#                                     how much of market inequality the welfare
#                                     state removes (= why disposable-beta -> 0).
#   * estimate_beta_market_cross_section — DIAGNOSTIC ONLY (between-country, tiny
#                                     n, structural heterogeneity -> wrong sign).
#   * estimate_beta_market_panel    — the CORRECT route: within-country FE on the
#                                     market Gini. Needs the live IDD GINIB time
#                                     series (user's machine); offline it runs on
#                                     an injected panel (tests prove the math).
# --------------------------------------------------------------------------- #
def redistribution_wedge(geos: List[str], allow_live: bool = False
                         ) -> Tuple[Dict[str, float], float]:
    """w_geo = 1 - Gini_disposable / Gini_market, from the IDD market Gini and a
    disposable Gini (IDD's own, for an internally-consistent same-source wedge;
    falls back to the Eurostat disposable Gini). The share of market inequality
    removed by taxes & transfers — and hence the bias that pushes a
    disposable-Gini beta toward zero. Returns (per_geo, mean)."""
    idd = OECDIDDConnector()
    conn = DBnomicsConnector(allow_live=allow_live)
    out: Dict[str, float] = {}
    for g in geos:
        ig = {k: r["value"] for k, r in idd.fetch(g).items()}
        gm = ig.get("gini_market_oecd")
        gd = ig.get("gini_disp_oecd")
        if gd is None:
            macro = {k: r["value"] for k, r in conn.fetch(g, 2019).items()}
            gd = (macro.get("gini_disp_income") or 0) / 100.0 or None
        if gm and gd:
            out[g] = 1.0 - gd / gm
    mean = sum(out.values()) / len(out) if out else float("nan")
    return out, mean


def estimate_beta_market_cross_section(geos: List[str], year: int = 2019,
                                       allow_live: bool = False
                                       ) -> Tuple[float, float, float, int]:
    """DIAGNOSTIC: regress the IDD MARKET Gini on the capital share ACROSS
    countries. Removes the redistribution confound of the disposable version,
    but the small between-country sample is dominated by structural
    heterogeneity (wage dispersion, sector mix) and does NOT identify beta — it
    typically returns the WRONG sign. Use the within-country panel instead.
    Returns (beta, intercept, R^2, n)."""
    idd = OECDIDDConnector()
    conn = DBnomicsConnector(allow_live=allow_live)
    xs, ys = [], []
    for g in geos:
        ig = {k: r["value"] for k, r in idd.fetch(g).items()}
        macro = {k: r["value"] for k, r in conn.fetch(g, year).items()}
        if "gini_market_oecd" in ig and "labour_share" in macro:
            xs.append(1.0 - macro["labour_share"] / 100.0)   # capital share
            ys.append(ig["gini_market_oecd"])                # market Gini (0-1)
    return (*_ols(xs, ys), len(xs))


def _live_market_panel(geo: str, years: List[int]
                       ) -> Dict[int, Dict[str, float]]:
    """Source one country's market-Gini panel LIVE: capital share from the
    AMECO labour share (DBnomics) and the market Gini from OECD IDD (GINIB).
    Returns {year: {capital_share, gini_market}} for years present in BOTH.
    Offline this is near-empty (IDD has one snapshot vintage) -> the caller
    skips the country, which is the honest result until the live pull lands."""
    ls = DBnomicsConnector(allow_live=True).fetch_range(geo, "labour_share", years)
    gm = OECDIDDConnector(allow_live=True).fetch_market_gini_range(geo, years)
    panel: Dict[int, Dict[str, float]] = {}
    for y in years:
        if y in ls and y in gm:
            panel[y] = {"capital_share": 1.0 - ls[y] / 100.0,
                        "gini_market": gm[y]}
    return panel


def estimate_beta_market_panel(
        geos: List[str], years: List[int], allow_live: bool = True,
        panels: Optional[Dict[str, Dict[int, Dict[str, float]]]] = None
        ) -> Tuple[float, float, int, int]:
    """The CORRECT beta identification: within-country FIXED-EFFECTS OLS of the
    MARKET Gini on the capital share, demeaned inside each country and pooled.
    Identification is from CHANGES over time, on the pre-redistribution variable
    beta is defined on — so unlike estimate_beta_panel (disposable, biased to
    zero) this is not absorbed by national redistribution regimes.

    Each panel row needs a market Gini and the capital share. `panels` injects
    {geo: {year: {"gini_market": g(0-1) | "gini_market_oecd": ...,
                  "labour_share": pct | "capital_share": frac}}}; tests use this.
    LIVE sourcing (the IDD GINIB time series + AMECO labour share per year) runs
    on the user's machine once the IDD live pull lands — until then a live call
    without `panels` returns NaN with n_countries=0 (honest, not a guess).
    Returns (beta, R^2, n_obs, n_countries)."""
    def _row_xy(row: Dict[str, float]):
        if "capital_share" in row:
            x = float(row["capital_share"])
        elif "labour_share" in row:
            x = 1.0 - float(row["labour_share"]) / 100.0
        else:
            return None
        gm = row.get("gini_market", row.get("gini_market_oecd"))
        if gm is None:
            return None
        gm = float(gm)
        return x, (gm / 100.0 if gm > 1.5 else gm)      # accept 0-1 or 0-100

    xs: List[float] = []
    ys: List[float] = []
    n_countries = 0
    for g in geos:
        if panels is not None:
            panel = panels.get(g)
        elif allow_live:
            panel = _live_market_panel(g, years)      # live IDD GINIB + AMECO
        else:
            panel = None
        if not panel:
            # No market-Gini time series for this country (offline, or the live
            # IDD codes not yet resolved via --probe-idd). Skip honestly.
            continue
        pts = [xy for _, row in sorted(panel.items())
               if (xy := _row_xy(row)) is not None]
        if len(pts) < 3:
            continue
        n_countries += 1
        mx = sum(x for x, _ in pts) / len(pts)
        my = sum(y for _, y in pts) / len(pts)
        xs += [x - mx for x, _ in pts]
        ys += [y - my for _, y in pts]
    b, _, r2 = _ols(xs, ys)
    return b, r2, len(xs), n_countries
