"""Monte-Carlo uncertainty bands (precision improvement #53).

Every headline so far has been a single point estimate, which over-states
precision. Real precision is a RANGE. This sweeps the uncertain inputs — the AI
shock's depth/speed, the distribution elasticities, the investment response, the
MPC — over plausible priors, runs the gated model for each draw, and reports
percentile bands (p5 / median / p95) for the outputs that matter.

Priors are inspectable, swappable assumptions (not estimates — that is what the
historical backtest, #54, is for). Divergent draws are skipped via the gate, so
bands are built only from consistent runs. Pure standard library.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from calibration import calibrate
from modules.sfc_core import SFCCore
from modules.distribution import DistributionModule
from scenarios import build_custom
from consistency.checks import check_run
from data.connectors.dbnomics import DBnomicsConnector

# uncertain inputs -> (low, high) uniform priors. Swap freely; these are the
# assumptions the headline numbers are conditional on.
PRIORS: Dict[str, Tuple[float, float]] = {
    "labour_share_end": (0.30, 0.55),   # how deep the AI labour-share fall goes
    "capex_growth":     (0.03, 0.09),   # how big the AI investment boom is
    "inv_elasticity":   (0.0, 1.5),     # how much diluting owners deters capex (C1)
    # beta is UNIDENTIFIED in macro data (disposable-Gini cross-section R2=.02;
    # FE panel 2010-24 beta=.05 R2=.006 - redistribution absorbs the shift). The
    # OECD IDD market Gini (2026-06-14) removes that confound and QUANTIFIES it:
    # the redistribution wedge averages ~0.37 (DE .41, FR .44), i.e. the welfare
    # state erases ~37% of market inequality - which is exactly why the post-tax
    # beta is biased to zero. The market CROSS-section still mis-identifies
    # (between-country heterogeneity, wrong sign, n=6); the clean closer is the
    # within-country market-Gini (GINIB) FE panel, pending the live IDD pull.
    # The model DEFAULT beta is now 0.13 (the market FE estimate, F15); the
    # Monte-Carlo prior stays WIDE here to carry the structural-shock uncertainty
    # the weak R^2 reflects. UBC-vs-cash band-separated across the span (F12).
    "beta":             (0.1, 1.0),
    # (gamma removed 2026-06-11: transfer incidence is now EXACT in the
    # distribution module, not an assumed compression elasticity)
    "a1_w":             (0.90, 0.98),   # workers' marginal propensity to consume
}
_POLICY = {"ubc": dict(ubc=True), "cash_ubi": dict(ubi=True), "none": dict()}


@dataclass
class Band:
    metric: str
    p5: float
    p50: float
    p95: float
    n: int

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.p5, self.p50, self.p95)


def _pctile(xs: List[float], q: float) -> float:
    if not xs:
        return float("nan")
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    pos = (q / 100.0) * (len(xs) - 1)
    lo = int(pos)
    frac = pos - lo
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + frac * (xs[hi] - xs[lo])


def monte_carlo(geo: str = "DE", form: str = "ubc", tau: float = 0.40,
                year: int = 2019, horizon: int = 30, n: int = 200,
                seed: int = 0, priors: Optional[dict] = None
                ) -> Tuple[Dict[str, Band], int, int]:
    """Return ({metric: Band}, n_draws_used, n_skipped). Each draw samples the
    priors, builds + runs the gated model, and contributes to the bands."""
    rng = random.Random(seed)
    priors = priors or PRIORS
    pol = _POLICY[form]
    rows = DBnomicsConnector(allow_live=False).fetch(geo, year)
    data = {k: v["value"] for k, v in rows.items()}

    keys = ("gini", "poverty", "citizen_wealth_pc", "dividend_pc", "gdp_end")
    acc: Dict[str, List[float]] = {k: [] for k in keys}
    used, skipped = 0, 0
    for _ in range(n):
        d = {k: rng.uniform(*v) for k, v in priors.items()}
        try:
            p = calibrate(data, geo=geo, base_year=year, a1_w=d["a1_w"])
            scen = build_custom(p, labour_share_end=d["labour_share_end"],
                                capex_growth=d["capex_growth"], capital_tax=tau,
                                horizon=horizon, name="mc", **pol)
            core = SFCCore(base_year=year, inv_elasticity=d["inv_elasticity"],
                           calib_kwargs={"a1_w": d["a1_w"]})
            res = core.run(scen, data)
            if max(r.max_residual for r in check_run(res, strict=False)) > 1.0:
                skipped += 1
                continue
            dist = DistributionModule(beta=d["beta"],
                                      base_year=year).run(scen, data,
                                                          {"sfc_core": res})
        except Exception:
            skipped += 1
            continue
        m, dd = res.periods[-1].reported, dist.periods[-1].reported
        pop = p.population or 1.0
        acc["gini"].append(dd["gini_personal"])
        acc["poverty"].append(dd["poverty_rate"])
        acc["citizen_wealth_pc"].append(m["swf_stake"] * 1e6 / pop)
        acc["dividend_pc"].append(m["transfer_pool"] * 1e6 / pop)
        acc["gdp_end"].append(m["gdp"])
        used += 1
    bands = {k: Band(k, _pctile(v, 5), _pctile(v, 50), _pctile(v, 95), len(v))
             for k, v in acc.items()}
    return bands, used, skipped
