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
  6. Economic plausibility — finite, non-negative levels, shares in [0,1], no
                           explosive growth.
  7. Plausibility v2 (Phase 7 A) — solvency and scale: household net worth
                           >= 0 per class, investment/GDP bounded, household
                           money holdings >= 0, owners' calibrated MPC in [0,1],
                           personal Gini above a floor. Staged: each law
                           blocks once the Phase-7 step that fixes it lands
                           (see ENFORCED_LAWS); "audit" reports only,
                           "enforce" blocks all.

Convention (AGORA TFM): tfm[flow][sector] is the signed contribution to that
sector's cash budget (inflow +, outflow -). For a stock-driving flow,
tfm[flow][sector] = -(Δ that sector's holding of the instrument), so that
columns balance. Hence: Δstock[sector] == -tfm[flow][sector].
"""
from __future__ import annotations

import math
import os

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from schema.accounts import INSTRUMENTS


class ConsistencyError(AssertionError):
    """Raised by the orchestrator when the gate fails and strict mode is on."""


# --------------------------------------------------------------------------- #
# Plausibility v2 (Phase 7 step A, 2026-10-28). Books can balance while a
# sector runs an impossible balance sheet: the 2026-10-28 review found capital
# owners ending deeply insolvent (DE UBC: owners' money -4.2x GDP; SK -140x) in
# runs that passed every accounting law. These checks ALWAYS run; the MODE
# decides whether a failure blocks the gate:
#   "audit":   every failure is ADVISORY - listed by
#              ConsistencyReport.advisories() but changing neither .passed,
#              .max_residual nor strict raising;
#   "staged":  (default since Phase 7 step B) the laws in ENFORCED_LAWS block,
#              the rest stay advisory until the step that fixes them lands;
#   "enforce": every law blocks.
# Runs of the LEGACY investment closure default to "audit" so the published
# v1.1 numbers still reproduce (their pathologies are reported, not raised).
# Per call: plausibility="...". Process-wide: env AGORA_PLAUSIBILITY (wins).
# Thresholds are inspectable, swappable assumptions.
# --------------------------------------------------------------------------- #
PLAUSIBILITY_MODES = ("audit", "staged", "enforce")
DEFAULT_PLAUSIBILITY = "staged"
# Laws that block in "staged" mode, and when the others join (docs/PHASE7.md).
ENFORCED_LAWS = frozenset({
    "hh_net_worth_nonnegative",     # step B: investment is financed, nobody insolvent
})
# The rest stay advisory until the step that removes their remaining causes:
STAGING = {"money_split_shares_valid": "step D (external positions are no longer "
                                       "allocated to households by money shares)",
           "investment_share_bounded": "step D (the fund can invest abroad)",
           "gini_floor": "step E (distribution layer + real policy designs)",
           "owners_mpc_in_unit_interval": "step F (calibration review: LU, SI)"}
MAX_INVESTMENT_SHARE = 0.40   # investment/GDP; EU GFCF/GDP peaks ~0.25-0.30 (IE aside)
MIN_PERSONAL_GINI = 0.15      # lowest EU disposable Gini in the snapshots: SK 0.228 (2019)
HOUSEHOLD_SECTORS = ("hh_workers", "hh_owners")


def resolve_plausibility(mode: Optional[str] = None,
                         closure: Optional[str] = None) -> str:
    """Explicit mode > env AGORA_PLAUSIBILITY > closure default (legacy runs:
    audit; everything else: DEFAULT_PLAUSIBILITY)."""
    m = mode if mode is not None else (
        os.environ.get("AGORA_PLAUSIBILITY")
        or ("audit" if closure == "legacy" else DEFAULT_PLAUSIBILITY))
    if m not in PLAUSIBILITY_MODES:
        raise ValueError(f"plausibility mode must be one of {PLAUSIBILITY_MODES}, "
                         f"got {m!r}")
    return m


def _advisory(mode: str, law: str) -> bool:
    """True if a failure of `law` is reported only (does not block)."""
    if mode == "audit":
        return True
    if mode == "enforce":
        return False
    return law not in ENFORCED_LAWS


@dataclass
class CheckResult:
    name: str
    passed: bool
    max_residual: float
    detail: str = ""
    advisory: bool = False   # True = reported only (audit mode); never blocks the gate


@dataclass
class ConsistencyReport:
    year: int
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks if not c.advisory)

    @property
    def max_residual(self) -> float:
        return max((c.max_residual for c in self.checks if not c.advisory),
                   default=0.0)

    def failures(self) -> List[CheckResult]:
        """Failed checks that block the gate."""
        return [c for c in self.checks if not c.passed and not c.advisory]

    def advisories(self) -> List[CheckResult]:
        """Failed checks that were reported but did not block (audit mode)."""
        return [c for c in self.checks if not c.passed and c.advisory]


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
    plausibility: Optional[str] = None,
) -> ConsistencyReport:
    """Run all consistency laws on one PeriodState. `scale` defaults to GDP.
    `plausibility` = "audit" | "enforce" | None (env AGORA_PLAUSIBILITY, else
    DEFAULT_PLAUSIBILITY) sets whether law-7 failures block the gate."""
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

    # --- 7. plausibility v2: solvency + scale (Phase 7 A). A household class
    # may borrow, but one whose liabilities exceed everything it owns is
    # insolvent: the model is then financing its spending with an unlimited,
    # interest-free overdraft at the state. Advisory in audit mode. ------- #
    mode = resolve_plausibility(plausibility)
    gdp_scale = abs(scale) if scale else 1.0
    worst_nw, worst_sec, seen = 0.0, "", False
    for sec in HOUSEHOLD_SECTORS:
        if not any(sec in cols for cols in bsm.values()):
            continue
        seen = True
        nw = sum(float(cols.get(sec, 0.0)) for cols in bsm.values())
        if nw < worst_nw:
            worst_nw, worst_sec = nw, sec
    if seen:
        ok = worst_nw >= -tol
        rep.checks.append(CheckResult(
            "hh_net_worth_nonnegative", ok, 0.0 if ok else float("inf"),
            "ok" if ok else (f"'{worst_sec}' net worth {worst_nw:.6g} "
                             f"= {worst_nw / gdp_scale:.3g} x GDP"),
            advisory=_advisory(mode, "hh_net_worth_nonnegative")))

    inv, gdp = rv.get("investment"), rv.get("gdp")
    if (isinstance(inv, (int, float)) and isinstance(gdp, (int, float))
            and math.isfinite(inv) and math.isfinite(gdp) and gdp > 0):
        share = inv / gdp
        ok = share <= MAX_INVESTMENT_SHARE + 1e-12
        rep.checks.append(CheckResult(
            "investment_share_bounded", ok, 0.0 if ok else float("inf"),
            f"investment/GDP {share:.4f} (max {MAX_INVESTMENT_SHARE:.2f})",
            advisory=_advisory(mode, "investment_share_bounded")))

    money = bsm.get("money", {})
    if all(sec in money for sec in HOUSEHOLD_SECTORS):
        mw, mk = float(money["hh_workers"]), float(money["hh_owners"])
        ok = mw >= -tol and mk >= -tol and (mw + mk) > tol
        rep.checks.append(CheckResult(
            "money_split_shares_valid", ok, 0.0 if ok else float("inf"),
            f"money held: workers {mw:.6g}, owners {mk:.6g} (interest and the "
            "current account are split by these shares, so both must be >= 0)",
            advisory=_advisory(mode, "money_split_shares_valid")))

    return rep


def _calibration_check(result, mode: str) -> Optional[CheckResult]:
    """Owners' marginal propensity to consume is solved as a calibration
    RESIDUAL so that year 0 reproduces GDP (legacy closure), or from 2019
    consumption and the published wage/profit consumption gap (behavioural,
    Phase 7 E5: the propensity the run actually uses). Outside [0, 1] it is
    not a behaviour but a sign the closure does not fit the country."""
    meta = getattr(result, "meta", None) or {}
    params = meta.get("params") or {}
    a1_k = params.get("a1_k") if isinstance(params, dict) else None
    if meta.get("investment_closure") == "behavioural" and \
            isinstance(meta.get("owners_mpc"), (int, float)):
        a1_k = meta["owners_mpc"]
    if not isinstance(a1_k, (int, float)):
        return None
    ok = 0.0 <= a1_k <= 1.0
    return CheckResult(
        "owners_mpc_in_unit_interval", ok, 0.0 if ok else float("inf"),
        f"owners' MPC a1_k = {a1_k:.3f} (calibration residual; must lie in [0, 1])",
        advisory=_advisory(mode, "owners_mpc_in_unit_interval"))


def check_run(result, stock_flow_map=None, strict: bool = False,
              plausibility: Optional[str] = None, **tol):
    """Check every period of a RunResult. Returns the list of reports.

    If strict, raises ConsistencyError on the first failing period — the gate
    that prevents a leaky model from being trusted.
    """
    stock_flow_map = stock_flow_map or result.meta.get("stock_flow_map", {})
    plausibility = resolve_plausibility(plausibility,
                                        (result.meta or {}).get("investment_closure"))
    calib = _calibration_check(result, plausibility)
    reports: List[ConsistencyReport] = []
    prev = None
    for i, p in enumerate(result.periods):
        rep = check_period(p, prev, stock_flow_map=stock_flow_map,
                           plausibility=plausibility, **tol)
        if i == 0 and calib is not None:
            rep.checks.append(calib)
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
                       atol: float = 1e-6, rtol: float = 1e-9,
                       plausibility: Optional[str] = None):
    """Per period: Σ decile incomes == hh_disposable, and shares sum to 1.
    Plus (law 7, advisory in audit mode) the personal Gini stays above a floor
    no real economy has gone below."""
    mode = resolve_plausibility(plausibility)
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
        g = rep.get("gini_personal")
        if isinstance(g, (int, float)) and math.isfinite(g):
            ok = g >= MIN_PERSONAL_GINI
            r.checks.append(CheckResult(
                "gini_floor", ok, 0.0 if ok else float("inf"),
                f"personal Gini {g:.3f} (floor {MIN_PERSONAL_GINI:.2f}; lowest "
                "EU member in the 2019 snapshots: SK 0.228)",
                advisory=_advisory(mode, "gini_floor")))
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
