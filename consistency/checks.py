"""Generic stock-flow-consistency checks over TFM / BSM matrices.

The checker is model-agnostic: any module that emits well-formed matrices is
gated by exactly these laws. It enforces the Godley-Lavoie accounting identities

  1. Column budget       — every sector's column of the TFM sums to ~0
                           (sources = uses; nothing appears from nowhere).
  2. Financial row balance — each financial-change flow row sums to ~0 across
                           sectors (every asset acquired is a liability issued;
                           includes the "hidden equation" / Walras' law).
  3. Stock-flow articulation — Δstock == the flow that drives it, per sector
                           (the exact leak that killed v0).
  4. Balance-sheet closure — each FINANCIAL instrument nets to ~0 across sectors.
  5. Sectoral balances sum to zero — Σ net-lending across all sectors == 0.

Convention (AGORA TFM): tfm[flow][sector] is the signed contribution to that
sector's cash budget (inflow +, outflow -). For a stock-driving flow,
tfm[flow][sector] = -(Δ that sector's holding of the instrument), so that
columns balance. Hence: Δstock[sector] == -tfm[flow][sector].
"""
from __future__ import annotations

import math

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from schema.accounts import INSTRUMENTS


class ConsistencyError(AssertionError):
    """Raised by the orchestrator when the gate fails and strict mode is on."""


@dataclass
class CheckResult:
    name: str
    passed: bool
    max_residual: float
    detail: str = ""


@dataclass
class ConsistencyReport:
    year: int
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def max_residual(self) -> float:
        return max((c.max_residual for c in self.checks), default=0.0)

    def failures(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.passed]


def _is_financial(instrument: str) -> bool:
    inst = INSTRUMENTS.get(instrument)
    return bool(inst) and not inst.real


def _tol(scale: float, atol: float, rtol: float) -> float:
    return atol + rtol * max(1.0, abs(scale))


def check_period(
    state,
    prev_state=None,
    stock_flow_map: Optional[Dict[str, str]] = None,
    scale: Optional[float] = None,
    atol: float = 1e-6,
    rtol: float = 1e-9,
) -> ConsistencyReport:
    """Run all consistency laws on one PeriodState. `scale` defaults to GDP."""
    tfm = state.tfm
    bsm = state.bsm
    stock_flow_map = stock_flow_map or {}
    scale = scale if scale is not None else float(state.reported.get("gdp", 1.0))
    tol = _tol(scale, atol, rtol)

    rep = ConsistencyReport(year=state.year)

    # --- 1. column budget: each sector's TFM column sums to ~0 ---------- #
    sectors = sorted({s for cols in tfm.values() for s in cols})
    worst, worst_sec = 0.0, ""
    for sec in sectors:
        col_sum = sum(cols.get(sec, 0.0) for cols in tfm.values())
        if abs(col_sum) > abs(worst):
            worst, worst_sec = col_sum, sec
    rep.checks.append(CheckResult(
        "column_budget", abs(worst) <= tol, abs(worst),
        f"worst sector '{worst_sec}' residual {worst:.6g}"))

    # --- 2. financial row balance (incl. hidden equation) -------------- #
    financial_flows = {
        flow for inst, flow in stock_flow_map.items() if _is_financial(inst)
    }
    worst, worst_flow = 0.0, ""
    for flow in financial_flows:
        row_sum = sum(tfm.get(flow, {}).values())
        if abs(row_sum) > abs(worst):
            worst, worst_flow = row_sum, flow
    rep.checks.append(CheckResult(
        "financial_row_balance", abs(worst) <= tol, abs(worst),
        f"worst flow '{worst_flow}' residual {worst:.6g}"))

    # --- 2b. ALL TFM rows net to zero (every transaction has a payer and a
    # payee, not only the financial-driver rows). Catches sign errors that
    # cancel across rows within a column. ------------------------------- #
    worst, worst_flow = 0.0, ""
    for flow, cols in tfm.items():
        row_sum = sum(cols.values())
        if abs(row_sum) > abs(worst):
            worst, worst_flow = row_sum, flow
    rep.checks.append(CheckResult(
        "row_balance_all_flows", abs(worst) <= tol, abs(worst),
        f"worst flow '{worst_flow}' residual {worst:.6g}"))

    # --- 3. stock-flow articulation: Δstock == -tfm[driver][sector] ---- #
    worst, detail = 0.0, "no prior period"
    if prev_state is not None:
        for inst, flow in stock_flow_map.items():
            cur = bsm.get(inst, {})
            prv = prev_state.bsm.get(inst, {})
            secs = set(cur) | set(prv) | set(tfm.get(flow, {}))
            for sec in secs:
                d_stock = cur.get(sec, 0.0) - prv.get(sec, 0.0)
                driver = -tfm.get(flow, {}).get(sec, 0.0)
                resid = d_stock - driver
                if abs(resid) > abs(worst):
                    worst = resid
                    detail = f"{inst}/{sec}: Δstock {d_stock:.6g} vs flow {driver:.6g}"
    rep.checks.append(CheckResult(
        "stock_flow_articulation",
        abs(worst) <= tol if prev_state is not None else True,
        abs(worst), detail))

    # --- 4. balance-sheet closure: each financial instrument nets to 0 - #
    worst, worst_inst = 0.0, ""
    for inst, cols in bsm.items():
        if not _is_financial(inst):
            continue
        s = sum(cols.values())
        if abs(s) > abs(worst):
            worst, worst_inst = s, inst
    rep.checks.append(CheckResult(
        "balance_sheet_closure", abs(worst) <= tol, abs(worst),
        f"worst instrument '{worst_inst}' residual {worst:.6g}"))

    # --- 5. sectoral net-lending balances sum to zero ------------------ #
    # net lending of a sector = sum over financial driver flows of -tfm[flow][sec]
    net_lending: Dict[str, float] = {}
    for inst, flow in stock_flow_map.items():
        if not _is_financial(inst):
            continue
        for sec, v in tfm.get(flow, {}).items():
            net_lending[sec] = net_lending.get(sec, 0.0) + (-v)
    total = sum(net_lending.values())
    rep.checks.append(CheckResult(
        "sectoral_balances_sum_zero", abs(total) <= tol, abs(total),
        f"Σ net-lending {total:.6g}"))

    # --- 6. economic plausibility: books can balance and still be insane.
    # Accounting laws (1-5) verify nothing leaks; this verifies the numbers are
    # economically POSSIBLE (finite, non-negative levels, shares in [0,1], no
    # explosive growth). It is what turns the LU-type blow-up from "balanced
    # garbage" into a caught gate failure. ---------------------------------- #
    rv = state.reported
    issues: List[str] = []
    for k, v in rv.items():
        if isinstance(v, (int, float)) and not math.isfinite(v):
            issues.append(f"{k} not finite")
    for k in ("gdp", "consumption", "investment", "capital", "hh_disposable"):
        v = rv.get(k)
        if isinstance(v, (int, float)) and math.isfinite(v) and v < -tol:
            issues.append(f"{k}<0 ({v:.3g})")
    for k in ("gini", "swf_share", "owners_capital_share"):
        v = rv.get(k)
        if isinstance(v, (int, float)) and math.isfinite(v) and not (-1e-6 <= v <= 1.0 + 1e-6):
            issues.append(f"{k} not in [0,1] ({v:.3g})")
    g = rv.get("gdp")
    if isinstance(g, (int, float)) and math.isfinite(g) and abs(g) > 1e15:
        issues.append(f"gdp implausibly large ({g:.3g})")
    if prev_state is not None:
        g0, g1 = prev_state.reported.get("gdp"), rv.get("gdp")
        if (isinstance(g0, (int, float)) and isinstance(g1, (int, float))
                and math.isfinite(g0) and math.isfinite(g1) and g0 > 0
                and (g1 / g0 > 100.0 or g1 / g0 < 0.0)):
            issues.append(f"gdp growth implausible ({g0:.3g}->{g1:.3g})")
    rep.checks.append(CheckResult(
        "economic_plausibility", not issues,
        0.0 if not issues else float("inf"),
        "; ".join(issues) if issues else "ok"))

    return rep


def check_run(result, stock_flow_map=None, strict: bool = False, **tol):
    """Check every period of a RunResult. Returns the list of reports.

    If strict, raises ConsistencyError on the first failing period — the gate
    that prevents a leaky model from being trusted.
    """
    stock_flow_map = stock_flow_map or result.meta.get("stock_flow_map", {})
    reports: List[ConsistencyReport] = []
    prev = None
    for p in result.periods:
        rep = check_period(p, prev, stock_flow_map=stock_flow_map, **tol)
        reports.append(rep)
        if strict and not rep.passed:
            fails = "; ".join(f"{c.name}({c.max_residual:.3g}: {c.detail})"
                              for c in rep.failures())
            raise ConsistencyError(
                f"[{result.module}/{result.scenario}] year {p.year} FAILED: {fails}")
        prev = p
    return reports


# --------------------------------------------------------------------------- #
# Reconciliation: a downstream decomposition (e.g. the distribution module)
# must add back up to the macro aggregate it decomposes. This is the "reconcile
# through the schema" law extended to Phase-2 modules.
# --------------------------------------------------------------------------- #
def check_distribution(dist_result, n_deciles: int = 10,
                       atol: float = 1e-6, rtol: float = 1e-9):
    """Per period: Σ decile incomes == hh_disposable, and shares sum to 1."""
    reports = []
    for p in dist_result.periods:
        rep = p.reported
        yd = float(rep.get("hh_disposable", 0.0))
        inc = sum(float(rep.get(f"decile_income_{d}", 0.0))
                  for d in range(1, n_deciles + 1))
        sh = sum(float(rep.get(f"decile_share_{d}", 0.0))
                 for d in range(1, n_deciles + 1))
        tol = atol + rtol * max(1.0, abs(yd))
        r = ConsistencyReport(year=p.year, checks=[
            CheckResult("distribution_reconciles", abs(inc - yd) <= tol,
                        abs(inc - yd),
                        f"Σdecile {inc:.6g} vs hh_disposable {yd:.6g}"),
            CheckResult("decile_shares_sum_one", abs(sh - 1.0) <= 1e-9,
                        abs(sh - 1.0), f"Σshares {sh:.9g}"),
        ])
        reports.append(r)
    return reports


# --------------------------------------------------------------------------- #
# Input-output reconciliation: the sectoral decomposition must add back up to
# the macro aggregate (Σ sectoral value added == GDP). Same "reconcile through
# the schema" law, applied to the production-structure module.
# --------------------------------------------------------------------------- #
def check_input_output(io_result, atol: float = 1e-3, rtol: float = 1e-9):
    """Per period: Σ sectoral value added == GDP (gdp_ref), and the reported
    va_total matches the sum of the sectoral parts."""
    reports = []
    for p in io_result.periods:
        rep = p.reported
        gdp_ref = float(rep.get("gdp_ref", 0.0))
        va_total = float(rep.get("va_total", 0.0))
        n = sum(1 for k in rep if k.startswith("va_") and k != "va_total")
        sum_va = sum(float(rep.get(f"va_{i}", 0.0)) for i in range(1, n + 1))
        tol = atol + rtol * max(1.0, abs(gdp_ref))
        reports.append(ConsistencyReport(year=p.year, checks=[
            CheckResult("io_value_added_reconciles", abs(va_total - gdp_ref) <= tol,
                        abs(va_total - gdp_ref),
                        f"Σva {va_total:.6g} vs GDP {gdp_ref:.6g}"),
            CheckResult("io_sector_parts_sum", abs(sum_va - va_total) <= tol,
                        abs(sum_va - va_total), f"Σva_s {sum_va:.6g} vs va_total {va_total:.6g}"),
        ]))
    return reports
