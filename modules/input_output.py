"""Input-output module (Phase 3) - the production-structure layer (FIGARO-style).

Loose coupling, the firm-side analogue of the distribution module: the SFC core
sets aggregate output / final demand, this module decomposes it across sectors
via a Leontief input-output structure, so an "AI hits sector X" shock propagates
through the supply chain.

Mechanism:
  * sectoral final demand   f_s = final_demand_share_s * GDP
  * gross output            x = (I - A)^-1 f          (Leontief)
  * value added by sector   VA_s = va_coeff_s * x_s   (sums to GDP by identity)
  * output multipliers      column sums of (I - A)^-1
  * AI sectoral exposure: the macro labour-share fall is distributed across
    sectors weighted by automation exposure (VA-weighted to track the aggregate),
    so high-exposure sectors (ICT/finance/business, industry) shed labour share
    fastest - the sectoral face of the decoupling.

A is built from the snapshot as A[i,j] = (1 - va_coeff[j]) * supply_shares[i]
(common-supplier simplification): a valid productive matrix. Pure standard
library (small hand-rolled linear algebra). The illustrative coarse structure is
swappable for a live FIGARO / Eurostat naio pull behind this same interface.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from modules.interface import Module, Scenario, RunResult, PeriodState
from modules.sfc_core import SFCCore

_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "cache")


# --- tiny linear algebra (stdlib) ----------------------------------------- #
def _solve(M: List[List[float]], b: List[float]) -> List[float]:
    """Gaussian elimination with partial pivoting; solves M x = b."""
    n = len(b)
    a = [row[:] + [b[i]] for i, row in enumerate(M)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        a[col], a[piv] = a[piv], a[col]
        pv = a[col][col]
        for j in range(col, n + 1):
            a[col][j] /= pv
        for r in range(n):
            if r != col and a[r][col] != 0.0:
                f = a[r][col]
                for j in range(col, n + 1):
                    a[r][j] -= f * a[col][j]
    return [a[i][n] for i in range(n)]


def _inverse(M: List[List[float]]) -> List[List[float]]:
    n = len(M)
    cols = [_solve(M, [1.0 if i == j else 0.0 for i in range(n)]) for j in range(n)]
    return [[cols[j][i] for j in range(n)] for i in range(n)]   # transpose


def load_io(geo: str) -> Optional[dict]:
    path = os.path.join(_CACHE, f"io_{geo.lower()}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class InputOutputModule(Module):
    name = "input_output"

    def __init__(self, base_year: int = 2019, sfc: Optional[SFCCore] = None):
        self.base_year = base_year
        self._sfc = sfc

    def declares_inputs(self) -> List[str]:
        return ["gdp", "labour_share"]   # consumes the SFC core's aggregates

    def declares_outputs(self) -> List[str]:
        return ["va_total", "gdp_ref", "ai_exposed_va_share",
                "va_<s>", "output_<s>", "lshare_<s>", "multiplier_<s>"]

    def run(self, scenario: Scenario, data: Dict[str, float],
            context: Optional[dict] = None) -> RunResult:
        sfc_res = (context or {}).get("sfc_core")
        if sfc_res is None:
            sfc_res = (self._sfc or SFCCore(base_year=self.base_year)).run(scenario, data)

        io = load_io(scenario.geo)
        if io is None:                                   # no I-O structure -> no-op
            return RunResult(self.name, scenario.name, scenario.geo, [], meta={})

        sectors = io["sectors"]
        n = len(sectors)
        va = io["va_coeff"]
        fd = io["final_demand_shares"]
        ls0 = io["labour_share_sector"]
        expo = io["automation_exposure"]

        # REAL technical coefficients (FIGARO/Eurostat naio, via the figaro
        # connector) when present; else the legacy common-supplier construction
        # A[i][j] = (1 - va_coeff[j]) * supply_shares[i].
        A = io.get("A")
        if A is None:
            sup = io["supply_shares"]
            A = [[(1.0 - va[j]) * sup[i] for j in range(n)] for i in range(n)]
        M = [[(1.0 if i == j else 0.0) - A[i][j] for j in range(n)] for i in range(n)]
        Linv = _inverse(M)
        mult = [sum(Linv[i][j] for i in range(n)) for j in range(n)]   # column sums

        # baseline VA shares (to rescale sectoral labour shares onto the macro one)
        Y0 = float(sfc_res.periods[0].reported["gdp"])
        f0 = [fd[s] * Y0 for s in range(n)]
        x0 = _solve(M, f0)
        va0 = [va[s] * x0[s] for s in range(n)]
        w0 = [v / sum(va0) for v in va0]
        ls_macro0 = float(sfc_res.periods[0].reported["labour_share"]) / 100.0
        denom0 = sum(w0[s] * ls0[s] for s in range(n))
        alpha = (ls_macro0 / denom0) if denom0 else 1.0
        ls_base = [min(0.95, alpha * ls0[s]) for s in range(n)]   # reconciled baseline

        periods: List[PeriodState] = []
        for per in sfc_res.periods:
            Y = float(per.reported["gdp"])
            ls_macro = float(per.reported["labour_share"]) / 100.0
            f = [fd[s] * Y for s in range(n)]
            x = _solve(M, f)
            va_s = [va[s] * x[s] for s in range(n)]
            va_total = sum(va_s)
            w = [v / va_total if va_total else 0.0 for v in va_s]

            # distribute the macro labour-share onto sectors by exposure (VA-weighted)
            ww_base = sum(w[s] * ls_base[s] for s in range(n))
            ww_expo = sum(w[s] * expo[s] for s in range(n))
            kappa = ((ww_base - ls_macro) / ww_expo) if ww_expo else 0.0
            ls_sec = [min(0.98, max(0.02, ls_base[s] - expo[s] * kappa))
                      for s in range(n)]

            reported: Dict[str, float] = {"va_total": va_total, "gdp_ref": Y}
            exposed_va = 0.0
            for s in range(n):
                reported[f"va_{s+1}"] = va_s[s]
                reported[f"output_{s+1}"] = x[s]
                reported[f"lshare_{s+1}"] = ls_sec[s]
                reported[f"multiplier_{s+1}"] = mult[s]
                if expo[s] >= 0.6:
                    exposed_va += w[s]
            reported["ai_exposed_va_share"] = exposed_va

            periods.append(PeriodState(year=per.year, tfm={}, bsm={},
                                       reported=reported))

        return RunResult(
            self.name, scenario.name, scenario.geo, periods,
            meta={"sectors": sectors, "n_sectors": n,
                  "matrix_source": ("real" if io.get("A") is not None
                                    else "supply-shares construction"),
                  "multipliers": dict(zip(sectors, mult)),
                  "automation_exposure": dict(zip(sectors, expo)),
                  "notes": io.get("_meta", {})})
