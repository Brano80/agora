"""How consumption responds to the split of income between wages and profits
(Phase 7 step E5, 2026-10-31).

DIFFERENTIAL[geo] is the change in consumption, as a share of GDP, when one
percentage point of GDP moves from wages to (gross, pre-tax) profits: the
marginal propensity to consume out of profits minus that out of wages. The
behavioural closure solves BOTH classes' propensities from this estimate and
2019 consumption, instead of fixing the workers' propensity and taking the
owners' as a residual (which put DE's owners at 0.04 and LU, SI, IE, NL below 0).

Sources (published estimates, not re-estimated here):
  Onaran, O. and Obst, T. (2016), "Wage-led growth in the EU15 member-states:
    the effects of income distribution on growth, investment, trade balance
    and inflation", Cambridge Journal of Economics 40(6); working paper PKSG
    WP 1602, Table 7 column A. Annual 1961-2013; dlog C on dlog profits and
    dlog wages, converted to marginal effects at sample means.
  Kaczmarski, D. (2024), "Wage- or Profit-Led Regime? The Case of Poland",
    The Polish Journal of Economics (Gospodarka Narodowa). Quarterly
    2001Q1-2022Q4, same method.
Countries without an estimate get the EU15 median (flagged).

Monte Carlo: a draw u in [-1, 1] moves the value by up to +-0.10 around a
country estimate, or across the full EU15 range (-0.564 .. -0.151) for a
median-filled country (u = 0 is the default in both cases).
"""
from __future__ import annotations

from statistics import median
from typing import Dict, Optional

ONARAN_OBST_2016 = "Onaran & Obst 2016, Camb. J. Econ. 40(6), Table 7 col. A (1961-2013)"
KACZMARSKI_2024 = "Kaczmarski 2024, Polish Journal of Economics (2001Q1-2022Q4)"

DIFFERENTIAL: Dict[str, tuple] = {
    "AT": (-0.277, ONARAN_OBST_2016), "BE": (-0.151, ONARAN_OBST_2016),
    "DK": (-0.155, ONARAN_OBST_2016), "FI": (-0.243, ONARAN_OBST_2016),
    "FR": (-0.324, ONARAN_OBST_2016), "DE": (-0.397, ONARAN_OBST_2016),
    "EL": (-0.564, ONARAN_OBST_2016), "IE": (-0.229, ONARAN_OBST_2016),
    "IT": (-0.410, ONARAN_OBST_2016), "LU": (-0.153, ONARAN_OBST_2016),
    "NL": (-0.322, ONARAN_OBST_2016), "PT": (-0.402, ONARAN_OBST_2016),
    "ES": (-0.410, ONARAN_OBST_2016), "SE": (-0.388, ONARAN_OBST_2016),
    "PL": (-0.255, KACZMARSKI_2024),
}
_EU15 = [v for g, (v, s) in DIFFERENTIAL.items() if s == ONARAN_OBST_2016]
EU15_MEDIAN = round(median(_EU15), 4)          # -0.323
EU15_RANGE = (min(_EU15), max(_EU15))          # (-0.564, -0.151)
DRAW_HALF_WIDTH = 0.10                         # MC +- around a country estimate


def consumption_differential_for(geo: Optional[str], draw: float = 0.0) -> Dict[str, object]:
    """{value, flag, source, range} for a country; `draw` in [-1, 1] picks a
    point in the Monte-Carlo range (0 = the estimate)."""
    u = max(-1.0, min(1.0, float(draw)))
    g = (geo or "").upper()
    if g in DIFFERENTIAL:
        v, src = DIFFERENTIAL[g]
        lo, hi = v - DRAW_HALF_WIDTH, v + DRAW_HALF_WIDTH
        return {"value": v + u * DRAW_HALF_WIDTH, "flag": "estimate", "source": src,
                "range": (lo, hi)}
    lo, hi = EU15_RANGE
    v = EU15_MEDIAN + (u * (EU15_MEDIAN - lo) if u < 0 else u * (hi - EU15_MEDIAN))
    return {"value": v, "flag": "eu15_median",
            "source": f"no estimate: EU15 median of {ONARAN_OBST_2016}", "range": (lo, hi)}
