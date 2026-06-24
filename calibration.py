"""Calibration — fit the SFC core's structural parameters to a national baseline.

Closed-form, transparent, country-agnostic. Given the canonical calibration
series for a geo/year (GDP, consumption, investment, government, EXPORTS,
IMPORTS, labour share, gov debt, Gini, population), it derives the structural
parameters so the model's year-0 reproduces those targets.

Phase 3: the economy is OPEN. Baseline GDP is the full expenditure identity
Y0 = C + I + G + X - M; net exports are inside the books (rest_of_world +
fx_assets active). Setting exports = imports = 0 recovers the closed Phase-1/2
economy, so this generalises rather than replaces it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SFCParams:
    geo: str
    base_year: int
    Y0: float                # baseline GDP (open: C + I + G + X - M)
    gdp_full: float          # published GDP (B1GQ); == Y0 up to statistical discrepancy
    nx_gap: float            # statistical discrepancy gdp_full - Y0 (~0 when reconciled)
    ls0: float               # baseline labour share (fraction)
    a_ratio0: float          # baseline investment / Y0
    g_ratio: float           # government / Y0
    export_ratio: float      # exports / Y0 (openness; exports proxied vs lagged output)
    m_imp: float             # import propensity: imports = m_imp * Y
    theta: float             # total effective net-tax rate (calibrated to fiscal balance)
    theta_w: float           # P6: labour-income tax rate (on wage bill)
    theta_k: float           # P6: baseline capital-income tax rate (on profits); 0 = legacy
    f_workers: float
    a1_w: float
    a1_k: float
    a2: float                # propensity to consume out of (money + fx) wealth
    M_w0: float
    M_k0: float
    F0: float                # initial net foreign assets (0 at baseline; accumulates CA)
    K0: float
    delta: float                 # traditional/economy-wide depreciation
    i_rate: float              # interest rate on government debt (0 = off)
    world_growth: float        # exogenous foreign-demand growth (export closure)
    inv0: float                # inventories+valuables level (P52+P53, MEUR; owner-financed)
    tau_fisc: float            # proportional fiscal net-tax (anchors the debt path)
    delta_ai: float            # AI-capital depreciation (fast obsolescence)
    population: float
    targets: Dict[str, float] = field(default_factory=dict)
    sources: Dict[str, str] = field(default_factory=dict)
    notes: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, object]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__
                if k not in ("targets", "sources", "notes")}


def _theta_for_gini(ls: float, f_w: float, gini_target: float) -> float:
    f_k = 1.0 - f_w
    num = gini_target - f_w * (1.0 - ls) + f_k * ls
    den = ls * (f_k + gini_target)
    return max(0.0, min(0.95, num / den if den else 0.0))


def _norm_gini(raw: float) -> float:
    return raw / 100.0 if raw > 1.0 else raw


def calibrate(
    data: Dict[str, float],
    geo: str = "DE",
    base_year: int = 2019,
    *,
    f_workers: float = 0.80,
    a1_w: float = 0.95,
    a2: float = 0.03,
    wealth_share_owners: float = 0.70,
    capital_output_ratio: float = 3.0,
    delta: float = 0.06,        # ~consumption of fixed capital; with I/Y~0.21
                                # and g~1.5% this holds K/Y near the 3.0 target
    delta_ai: float = 0.25,     # AI capital obsolesces in ~4 years
    capital_tax_share: float = 0.0,  # P6 broad revenue base: share of base-year net
                                     # tax raised on CAPITAL (0 = legacy wage-only base)
    i_rate: float = 0.0,        # interest on gov debt; 0 keeps Phase 1-3 behaviour
    world_growth: float = 0.015,  # exports grow with FOREIGN demand, not own output
    g_fiscal: float = 0.015,    # debt-stabilising growth for the fiscal anchor
    gini_target: Optional[float] = None,
    sources: Optional[Dict[str, str]] = None,
) -> SFCParams:
    C = float(data["hh_consumption"])
    I = float(data["gfcf"])
    G = float(data["gov_consumption"])
    gdp_full = float(data["gdp"])
    X = float(data.get("exports", 0.0))
    M = float(data.get("imports", 0.0))
    # inventories + valuables (P52+P53) = gross capital formation - GFCF.
    # Missing gcf (older snapshots) -> 0, which reproduces the old behaviour
    # (the omitted component then shows up in nx_gap, as before).
    gcf = data.get("gcf")
    INV = (float(gcf) - I) if gcf is not None else 0.0

    Y0 = C + I + G + X - M + INV                # full expenditure identity
    nx_gap = gdp_full - Y0                       # statistical discrepancy (~0 reconciled)
    ls0 = float(data["labour_share"]) / 100.0
    a_ratio0 = I / Y0
    g_ratio = G / Y0
    export_ratio = X / Y0
    m_imp = M / Y0

    gt = _norm_gini(float(gini_target if gini_target is not None
                          else data["gini_disp_income"]))   # distribution anchor

    debt = float(data["gov_debt_gdp"]) / 100.0 * gdp_full
    M_k0 = wealth_share_owners * debt
    M_w0 = (1.0 - wealth_share_owners) * debt

    A0, G0, X0 = a_ratio0 * Y0, g_ratio * Y0, export_ratio * Y0
    Mtot = M_w0 + M_k0
    # theta is the effective tax rate, calibrated to the FISCAL BALANCE
    # (debt-stabilising: primary deficit = g_fiscal*debt), NOT the Gini. A
    # Gini-pinned theta comes out implausibly high (~47% for DE) and the
    # government runs a ~10%-of-GDP phantom SURPLUS that crashes debt negative —
    # the flaw the historical backtest caught (F9). Inequality is anchored
    # separately by the distribution module's personal Gini, so decoupling theta
    # costs nothing on the reported-inequality side. (tax_k0 = 0 at baseline.)
    target_deficit = g_fiscal * debt
    theta = max(0.05, min(0.60, (G0 - target_deficit) / (ls0 * Y0)))
    tau_fisc = 0.0   # theta now carries the fiscal balance; proportional top-up unused
    # Phase 6 broad revenue base: split the SAME total base-year net tax
    # (theta*WB0) into a labour rate (theta_w on wages) + a baseline CAPITAL rate
    # (theta_k on profits) per capital_tax_share. share=0 -> theta_w=theta,
    # theta_k=0 (exact legacy). Total base-year revenue is unchanged so the
    # baseline still reproduces; the COMPOSITION now responds to the capital
    # share going forward (fixes the wage-only-base under-taxation, F-debt).
    sk = max(0.0, min(0.9, capital_tax_share))
    theta_w = (1.0 - sk) * theta
    theta_k = (sk * theta * ls0 / (1.0 - ls0)) if (1.0 - ls0) > 1e-9 else 0.0
    # owners also finance the (non-productive) inventory accumulation INV.
    # a1_k recalibrated to the post-tax disposable split so year-0 demand still
    # reproduces baseline GDP for ANY capital_tax_share.
    a1_k = (Y0 * (1.0 + m_imp) - a1_w * ls0 * (1.0 - theta_w) * Y0
            - a2 * Mtot - A0 - INV - G0 - X0) / ((1.0 - ls0) * (1.0 - theta_k) * Y0)

    # PLAUSIBILITY GUARD (the Luxembourg lesson): a residually-solved owners'
    # MPC far outside [0, 1] means the national structure (entrepôt, trade >>
    # GDP) breaks this closure. Fail HERE with a diagnosable message instead of
    # letting the run diverge into a 1e+233 gate residual downstream.
    if not (-1.0 <= a1_k <= 1.5):
        raise ValueError(
            f"calibrate({geo}): implausible owners' MPC a1_k={a1_k:.3f} "
            f"(outside [-1.0, 1.5]); pathological national structure "
            f"(entrepot-type, trade>GDP?) - refusing to calibrate")

    pop = float(data.get("population", 0.0))
    K0 = capital_output_ratio * Y0

    params = SFCParams(
        geo=geo, base_year=base_year, Y0=Y0, gdp_full=gdp_full, nx_gap=nx_gap,
        ls0=ls0, a_ratio0=a_ratio0, g_ratio=g_ratio, export_ratio=export_ratio,
        m_imp=m_imp, theta=theta, theta_w=theta_w, theta_k=theta_k, f_workers=f_workers, a1_w=a1_w, a1_k=a1_k, a2=a2, inv0=INV,
        M_w0=M_w0, M_k0=M_k0, F0=0.0, K0=K0, delta=delta, delta_ai=delta_ai, i_rate=i_rate,
        world_growth=world_growth, tau_fisc=tau_fisc, population=pop,
        targets={
            "gdp": gdp_full, "gdp_expenditure": Y0, "hh_consumption": C,
            "gfcf": I, "gov_consumption": G, "exports": X, "imports": M,
            "net_exports": X - M, "inventories": INV, "labour_share": ls0 * 100.0,
            "gov_debt_gdp": float(data["gov_debt_gdp"]),
            "gini_disp_income": gt * 100.0,
        },
        sources=sources or {},
        notes={
            "open_economy": "Open economy: Y0 = C + I + G + X - M (net exports "
                            f"inside the books). Statistical discrepancy vs "
                            f"published GDP: {nx_gap:,.0f} MEUR.",
            "exports": "Exports proxied as a stable share of lagged output (world "
                       "demand grows with the economy); true RoW-GDP driver is the "
                       "multi-region extension.",
            "fx": "Net foreign assets accumulate the current account, held by "
                  "households (split by money wealth); RoW is the counterpart.",
            "theta": "Effective tax rate calibrated to the FISCAL BALANCE (debt-stabilising), not the Gini — the latter is anchored by the distribution module. Fixes the debt-crash flaw the backtest caught (F9).",
            "a1_k": "Owners' MPC solved so year-0 demand reproduces baseline GDP.",
        },
    )
    if not (0.0 <= a1_k <= 1.0):
        params.notes["a1_k_warning"] = (
            f"owners' MPC a1_k={a1_k:.3f} outside [0,1]; calibration is "
            "stretched - treat dynamics with caution")
    return params
