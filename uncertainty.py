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
from scenarios import build_custom, CAPEX_AI_GROWTH
from modules.ai_shock import AI_PRODUCTIVITY
from consistency.checks import check_run
from data.connectors.dbnomics import DBnomicsConnector

# uncertain inputs -> (low, high) uniform priors. Swap freely; these are the
# assumptions the headline numbers are conditional on.
PRIORS: Dict[str, Tuple[float, float]] = {
    "labour_share_end": (0.30, 0.55),   # how deep the AI labour-share fall goes
    # Phase 7 B: investment is behavioural, so the exogenous capex growth and the
    # v1.1 dilution elasticity are gone. The investment assumptions are now:
    "profit_response":  (0.088, 0.376), # profit-share effect on I/Y, Onaran & Galanis
                                        # (2014) European range (FR 0.088 .. DE 0.376)
    "debt_cap":         (0.0, 0.22),    # owners' new borrowing / owned capital: 0 (no
                                        # credit) .. the size of today's NFC debt stock
    "loan_rate":        (0.015, 0.055), # +-2pp around the ECB NFC cost of borrowing (3.57%)
    # Phase 7 C: supply side and prices
    "ai_productivity":  (0.0, 0.006),   # AI pp/yr while adopting: 0 .. OECD 2024 US upper 0.6
    "phillips_slope":   (0.01, 0.15),   # ECB WP 3133 slope range (0.02-0.19 per pp u) x Okun
    "export_elasticity": (0.3, 1.0),    # Christodoulopoulou & Tkacevs 2013 country range
    "utilisation_response": (0.1, 0.35),  # assumption; >~0.5 gives cycles the data rule out
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
    # omega = capital-share -> WEALTH-concentration elasticity (Phase A). The
    # cross-section is uninformative (R^2 .06, wrong sign), so the prior is WIDE
    # and includes 0 (no endogenous concentration) up to a strong r>g regime.
    "omega":            (0.0, 0.40),
    # (gamma removed 2026-06-11: transfer incidence is now EXACT in the
    # distribution module, not an assumed compression elasticity)
    "a1_w":             (0.90, 0.98),   # workers' marginal propensity to consume
}
# The v1.1 prior (published F12 bands), kept to reproduce them with the legacy
# investment closure: core_kwargs() routes any draw carrying inv_elasticity to it.
LEGACY_PRIORS: Dict[str, Tuple[float, float]] = {
    "labour_share_end": (0.30, 0.55), "capex_growth": (0.03, 0.09),
    "inv_elasticity": (0.0, 1.5), "beta": (0.1, 1.0), "omega": (0.0, 0.40),
    "a1_w": (0.90, 0.98)}
_OUT_KEYS = ("gini", "poverty", "citizen_wealth_pc", "dividend_pc", "gdp_end")
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


def core_kwargs(d: Dict[str, float]) -> Dict[str, object]:
    """SFC-core settings for one draw. A prior set that still carries the v1.1
    `inv_elasticity` runs the legacy closure (reproduces the published bands)."""
    if "inv_elasticity" in d:
        return {"investment_closure": "legacy", "inv_elasticity": d["inv_elasticity"]}
    return {k: d[k] for k in ("profit_response", "debt_cap", "loan_rate",
                              "phillips_slope", "export_elasticity",
                              "utilisation_response") if k in d}


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


def _run_draws(geo: str, form: str, tau: float, year: int, horizon: int,
               n: int, seed: int, priors: Optional[dict]):
    """Sample the JOINT prior, run the gated model per draw, and return
    (input_samples, {metric: [outputs]}, n_used, n_skipped). One sampling loop
    shared by the bands (monte_carlo) and the sensitivity ranking."""
    rng = random.Random(seed)
    priors = priors or PRIORS
    pol = _POLICY[form]
    rows = DBnomicsConnector(allow_live=False).fetch(geo, year)
    data = {k: v["value"] for k, v in rows.items()}
    inputs: List[Dict[str, float]] = []
    acc: Dict[str, List[float]] = {k: [] for k in _OUT_KEYS}
    used, skipped = 0, 0
    for _ in range(n):
        d = {k: rng.uniform(*v) for k, v in priors.items()}
        try:
            p = calibrate(data, geo=geo, base_year=year, a1_w=d["a1_w"])
            scen = build_custom(p, labour_share_end=d["labour_share_end"],
                                capex_growth=d.get("capex_growth", CAPEX_AI_GROWTH),
                                ai_productivity=d.get("ai_productivity"),
                                capital_tax=tau, horizon=horizon, name="mc", **pol)
            core = SFCCore(base_year=year, calib_kwargs={"a1_w": d["a1_w"]},
                           **core_kwargs(d))
            res = core.run(scen, data)
            if max(r.max_residual for r in check_run(res, strict=False)) > 1.0:
                skipped += 1
                continue
            dist = DistributionModule(beta=d["beta"], omega=d.get("omega", 0.15),
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
        acc["dividend_pc"].append(m["transfer_pool"] / m.get("price_level", 1.0) * 1e6 / pop)
        acc["gdp_end"].append(m.get("gdp_real", m["gdp"]))      # real (Phase 7 C)
        inputs.append(d)
        used += 1
    return inputs, acc, used, skipped


def monte_carlo(geo: str = "DE", form: str = "ubc", tau: float = 0.40,
                year: int = 2019, horizon: int = 30, n: int = 200,
                seed: int = 0, priors: Optional[dict] = None
                ) -> Tuple[Dict[str, Band], int, int]:
    """Return ({metric: Band}, n_draws_used, n_skipped) over the JOINT prior."""
    _, acc, used, skipped = _run_draws(geo, form, tau, year, horizon, n, seed, priors)
    bands = {k: Band(k, _pctile(v, 5), _pctile(v, 50), _pctile(v, 95), len(v))
             for k, v in acc.items()}
    return bands, used, skipped


def _pearson(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    den = (sxx * syy) ** 0.5
    return (sxy / den) if den > 0 else 0.0


def sensitivity(geo: str = "DE", form: str = "ubc", tau: float = 0.40,
                year: int = 2019, horizon: int = 30, n: int = 400,
                seed: int = 0, priors: Optional[dict] = None,
                metric: str = "gini") -> Dict[str, object]:
    """First-order (correlation-based) global sensitivity: across the JOINT
    draws, how much does each prior input move the chosen output? Returns each
    input's correlation (sign + strength) and its share of explained variance
    (squared correlation, normalised), ranked - i.e. WHICH assumption drives the
    verdict. Honest first-order approximation (independent uniform inputs)."""
    priors = priors or PRIORS
    inputs, acc, used, skipped = _run_draws(geo, form, tau, year, horizon, n, seed, priors)
    ys = acc.get(metric, [])
    drivers = []
    for k in priors:
        xs = [d[k] for d in inputs]
        r = _pearson(xs, ys)
        drivers.append({"param": k, "corr": r, "r2": r * r})
    tot = sum(x["r2"] for x in drivers) or 1.0
    for x in drivers:
        x["share"] = x["r2"] / tot
    drivers.sort(key=lambda x: -x["r2"])
    return {"metric": metric, "n": used, "skipped": skipped,
            "drivers": drivers, "linear_r2": min(1.0, sum(x["r2"] for x in drivers))}
