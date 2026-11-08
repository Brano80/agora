"""SFC core - self-contained two-class monetary stock-flow-consistent model.

Open economy (Phase 3): households (workers + capital owners), firms (pass-
through), government (issues money), rest-of-world (external counterparty), and
- when Universal Basic Capital is switched on - a sovereign/citizens' fund.
Financial instruments: government money + net foreign assets (fx); real stock:
fixed capital. Demand-led output.

Open-economy closure:
  Y = C + A + G + X - M           (exports inject, imports leak)
  X = export_ratio * Y_prev       (world demand proxied by lagged output)
  M = m_imp * Y                   (imports scale with output)
  Current account NX = X - M accumulates as domestic net foreign assets (fx),
  held by households (split by money wealth); rest-of-world is the counterpart.
  (Legacy closure only: the behavioural closure replaces this with the Phase 7
  D external sector described below.)
Setting export_ratio = m_imp = 0 recovers the closed Phase-1/2 economy.

Universal Basic Capital (the pinned experiment, Phase 3). Two policy arms share
the SAME intensity lever tau (the public claim on capital income), differing
only in FORM - the direct test of the flow-vs-stock thesis (MANIFESTO Q1):
  * CASH UBI (ubi_on): the levy tax_k = tau*FP is redistributed as an equal
    per-capita cash transfer THIS YEAR. Pure flow; builds no wealth.
  * UBC (ubc_on): an equal-valued claim Contrib = tau*FP is converted IN KIND
    each year into a citizens' capital endowment held by the sovereign_fund
    (owners are diluted, no cash levy). The fund owns share phi = E_sf/K of the
    capital stock, earns phi*FP of profits, and pays it out per capita as the
    sovereign-fund dividend. The endowment compounds, so the dividend grows and
    eventually exceeds the flat cash UBI, while citizens accumulate the stock.
Both arms leave the government's deficit path identical (dH_s = G - tax_w), so
the comparison is equal-cost. The fund holds no money (pure pass-through), so
only money + fx remain in the financial gate - the books still close exactly.

Investment closure (Phase 7 step B, 2026-10-29). Two switchable closures:
  * "behavioural" (default): investment is a DECISION. Each owner of capital
    invests on the stake it owns: private owners' desired gross investment is
    (1 - phi) * Y_prev * [i0 + gamma * (pi_eff_prev - pi0)], where pi_eff is the
    owners' net profit share after taxes and after equity given up (a cash levy
    or UBC dilution lower it symmetrically), i0 the base-year investment share
    and gamma the profit-share effect on investment/GDP (Onaran & Galanis 2014,
    Table 7: euro area-12 0.299, DE 0.376, FR 0.088, IT 0.130; 1962-2007). The AI
    boom then comes from the higher profit share, not an exogenous capex path.
    Financing follows a pecking order (Myers & Majluf 1984): saving first, liquid
    money down to a floor, then loans up to debt_cap x owned capital at
    loan_rate, and only then less investment (then fewer inventories). Owners'
    money therefore never goes negative. If owned capital shrinks below what
    the cap allows, the excess debt is repaid at the rate loans mature
    (deleverage_rate). Under UBC the fund takes NET equity: the diluted
    capital comes with its proportional share of the owners' loans, which the
    fund services (interest + repayment at the maturity rate) out of its
    profits before paying dividends. The citizens' fund invests the share
    of its profits it retains (ubc_reinvest / fund_payout).
    Lender: the public sector as a stand-in until the banks sector exists, so
    gov_debt is reported NET of these loans (gov_money = gross money issued).
    Supply side and prices (Phase 7 step C, 2026-10-29). Full-capacity real
    output = AI productivity level x installed capital / v, with v calibrated
    so the base year sits at the observed utilisation (EC survey,
    data/connectors/capacity.py). Real output cannot exceed the historical
    maximum utilisation; demand beyond it is met by extra imports. Values are
    in current euros with a price level P (2019 = 1): inflation = the ECB 2%
    target + a Phillips slope x last year's output gap (demand pressure). The
    real rules (government spending, the investment share) are indexed to
    P, exports lose competitiveness when P outruns the world's 2% path,
    capital is real and valued at P on balance sheets, and nominal money,
    loans and debt erode with inflation. Interest rates are fixed (no
    monetary-policy rule yet: the banks step). Policies switch on in year 1
    (2020) so the base year reproduces in every arm. Investment also responds
    to the output gap, so capacity keeps up with demand. The citizens' fund
    invests by the SAME rule on the stake it owns, up to what its payout
    policy lets it retain, and pays out the rest. Like any owner it first
    retains the depreciation allowance on its stake (replacement), so
    ubc_reinvest is the share of NET profits retained and a POMV draw cannot
    consume capital.
    External sector (Phase 7 step D, 2026-10-30). Foreign owners hold their
    observed share of domestic capital (equity income paid abroad / net
    profits, Eurostat), invest on it by the owners' rule (FDI), pay capital
    taxes at source, and cannot be diluted by UBC. Owners hold their observed
    equity abroad (world return, reinvested at world nominal growth). A share
    of the AI rent - the income the AI shift moves from labour - is paid abroad
    as licence/cloud fees (ai_foreign_share); a source levy on those fees is
    partly passed on to domestic buyers (levy_pass_through). Each country
    starts at its 2019 net international investment position; the part that is
    not equity is held by the public sector as a stand-in (no household holds
    it, replacing the v1.1 money-share rule), and fiscal debt is reported net
    of what the stand-in bought abroad since 2019. What the citizens' fund
    retains but does not need at home buys equity abroad.
  * "legacy": the v1.1 behaviour, exactly - an exogenous capex path (ai_capex
    lever, optionally scaled by inv_elasticity) financed by an unlimited,
    interest-free money overdraft. Kept ONLY to reproduce published v1.1
    numbers and for the backtest, which drives actual historical investment.

Emits a complete transaction-flow matrix (columns balance) + balance-sheet
matrix so the consistency gate validates money AND fx to machine precision.
TFM convention: tfm[flow][sector] is the signed cash-budget contribution
(inflow +, outflow -); stock-driving rows carry -(Δstock) so columns sum to 0.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from modules.interface import Module, Scenario, RunResult, PeriodState
from calibration import calibrate, SFCParams
from data.connectors.capacity import capacity_utilisation_for
from data.connectors.capital import capital_position_for
from data.connectors.loans import private_loans_for
from data.connectors.trend import mean_growth, trend_path
from data.connectors.consumption import consumption_differential_for
from data.connectors.external import R_WORLD, external_position_for
from data.connectors.fiscal import fiscal_position_for
from data.connectors.rates import (DEBT_MATURITY, DEPOSIT_BETA, EURO_AREA, NEUTRAL_RATE,
                                   RATE_FLOOR, RATE_SMOOTHING, RISK_PREMIUM,
                                   TAYLOR_GAP, TAYLOR_INFLATION, rates_for)


# --------------------------------------------------------------------------- #
# Phase 7 B parameters - sourced, inspectable, swappable (also MC priors).
# --------------------------------------------------------------------------- #
INVESTMENT_CLOSURES = ("behavioural", "legacy")
# Marginal effect of a 1-pp rise in the profit share on private investment/GDP
# (pp). Onaran & Galanis (2014), "Income Distribution and Growth: A Global
# Model", Environment and Planning A 46(10), Table 7 col. B; 1962-2007.
PROFIT_RESPONSE = {"DE": 0.376, "FR": 0.088, "IT": 0.130}
PROFIT_RESPONSE_DEFAULT = 0.299          # euro area-12 estimate, used elsewhere
# Cap on owners' NEW net borrowing since the base year, as a share of the
# capital they own. 0.10 ~ 30% of GDP at K/Y = 3, i.e. ~45% of today's whole
# euro-area NFC debt stock (67.2% of GDP, end-2024, ECB quarterly sector
# accounts). The base-year balance sheet already nets existing debt.
DEBT_CAP = 0.10
# Interest on those loans: ECB composite cost of borrowing for new loans to
# corporations, 3.57% (Dec 2025, ECB MFI interest rate statistics).
LOAN_RATE = 0.035
# Debt above the cap (when owned capital shrinks) is not called in at once: it
# is repaid as loans mature. 0.2/yr = an ASSUMED 5-year average maturity.
DELEVERAGE_RATE = 0.2
# Owners keep liquid money of at least this share of their base-year
# liquidity ratio (money / owned capital) before borrowing.
LIQUIDITY_FLOOR = 0.5


# Phase 7 C supply side and prices.
INFLATION_TARGET = 0.02      # ECB price-stability target
WORLD_GROWTH = 0.015         # world real growth (= calibrate()'s world_growth default)
# pp of inflation per pp of output gap: ECB WP 3133 (Beschin, Paredes,
# Polichetti & Renault 2025) regional euro-area slope ~0.19 per pp of
# unemployment, times an Okun coefficient of ~0.4 (Ball, Leigh & Loungani 2017).
PHILLIPS_SLOPE = 0.08
# Long-run export elasticity to the real exchange rate: ~0.8 goods, ~0.7
# services (Christodoulopoulou & Tkacevs 2013, ECB CompNet).
EXPORT_ELASTICITY = 0.75
# ASSUMPTION (no published coefficient found): pp of investment/GDP per pp of
# output gap. Utilisation drives short-run euro-area investment (Gallo &
# Barbieri Goes 2023, Economia Politica 40). Calibrated to a stylised fact:
# survey utilisation is stationary with small swings (DE sd 3.5 pp, 1985-2025,
# shocks included). At 0.25 every baseline stays within ~79-87%; from ~0.5 the
# multiplier-accelerator loop drives 15-year cycles of +-8 pp (FR, IT, ES),
# which the data rule out. MC range 0.1-0.35.
UTILISATION_RESPONSE = 0.25
POLICY_START = 1             # policies switch on in 2020: 2019 reproduces in every arm
# Baseline technical progress on capacity, calibrated per country so that the
# no-shock baseline grows in balance (capacity keeps pace with trend demand),
# bounded by the EU range of TFP growth: 0.1%/yr 2009-2019, 0.7%/yr 1996-2007
# (IMF WP/24/258, "Chasing the Dream", from EU-KLEMS).
TFP_BOUNDS = (0.001, 0.007)

# Phase 7 D: the external sector (behavioural closure only).
# Share of the AI rent (the income the AI shift moves from labour to capital)
# earned ABROAD as licence and cloud fees: US providers hold ~70% of the
# European cloud market and European providers ~15% (Synergy Research, 2025);
# frontier models are mostly US. MC range 0.5-0.9.
AI_FOREIGN_SHARE = 0.70
# Share of a source levy on those fees that the foreign provider passes on to
# domestic buyers: Amazon raised its fees by roughly the full digital services
# tax (Langenmayr & Muddasani 2026, CESifo WP 12713) and the platforms added
# DST surcharges to their invoices. MC range 0.5-1.0.
LEVY_PASS_THROUGH = 0.9

# Phase 7 E: the fiscal block (behavioural closure defaults; legacy keeps 0).
# Capital taxes / (labour + capital taxes) = 21.6 / (51.5 + 21.6), EU-27 2024
# (European Commission, DG TAXUD, tax revenue release of 31 March 2026).
CAPITAL_TAX_SHARE = 0.30
# Fiscal reaction (Bohn coefficient): +0.034 pp of primary balance per pp of
# debt/GDP (Checherita-Westphal & Zdarek 2017, ECB WP 2036, euro area 1970-2013;
# range 0.03-0.05). Applied to the tax rate on all taxed income (labour and
# capital alike), steering debt back to its 2019 level. MC range 0.03-0.05.
FISCAL_REACTION = 0.034 / 100.0
# Phase 7 E5: workers' propensity to consume out of income is capped at 1:
# above it they would dissave every year and run out of money (EL 2019).
MAX_WORKERS_MPC = 1.0
# Phase 7 F: each country's own net capital stock / GDP and depreciation rate
# (AMECO OKND, PIGT, UKCT, UVGD; data/connectors/capital.py) replace the
# uniform K/Y = 3 and 6%. False restores the uniform values (comparison only).
CAPITAL_FROM_DATA = True
# Phase 7 F: each country's trend growth path (2024 Ageing Report;
# data/connectors/trend.py) replaces the uniform 1.5% world growth for exports
# and for capacity. False restores the uniform path (comparison only).
TREND_FROM_DATA = True
GAP_CLOSE_YEARS = 3
# Phase 7 F: the public stand-in holds the foreign position wherever a class's
# deposits would start at or below zero (False: only the STAND_IN list, the
# Banks-step rule; comparison only)
STAND_IN_BY_RULE = True
# Phase 7 F: share of a temporary change in income that households spend in
# the same year. 0.48 = Jappelli & Pistaferri (2014, AEJ: Macro 6(4)), Italian
# survey of how much of an unexpected windfall households would spend;
# Fagereng, Holm & Natvik (2021, AEJ: Macro 13(4)) find just under half for
# liquid Norwegian lottery winners, all of it for illiquid small-prize ones,
# and spending back to normal within five years. Consumption closes the share
# lambda = IMPACT_MPC / (income-weighted long-run propensity) of the gap to its
# long-run level each year, so a permanent change is still spent in full.
# MC range 0.3-0.7.
IMPACT_MPC = 0.48


def fiscal_calibration(geo: Optional[str], closure: str,
                       i_rate: Optional[float] = None,
                       capital_tax_share: Optional[float] = None,
                       base_year: int = 2019, trend_draw: float = 0.0) -> dict:
    """calibrate() kwargs for a closure. Behavioural: each country's implicit
    interest rate (five years to the base year) and base-year primary balance
    (Eurostat), a 30% capital share of taxes, and (step F) the country's own
    capital-output ratio and depreciation rate (AMECO). Legacy: the v1.1
    defaults (0, 0, debt anchor, K/Y = 3, 6% depreciation)."""
    if closure == "behavioural":
        f = fiscal_position_for(geo, base_year=base_year)
        out = {"i_rate": float(f["implicit_rate"]) if i_rate is None else float(i_rate),
               "capital_tax_share": (CAPITAL_TAX_SHARE if capital_tax_share is None
                                     else float(capital_tax_share)),
               # nominal trend growth = the world's real growth at the ECB target
               "g_nominal": (1.0 + WORLD_GROWTH) * (1.0 + INFLATION_TARGET) - 1.0}
        if CAPITAL_FROM_DATA:
            cap = capital_position_for(geo, base_year=base_year)
            out.update(capital_output_ratio=float(cap["k_y"]), delta=float(cap["delta"]))
        if TREND_FROM_DATA:
            # step F: the country's trend (2024 Ageing Report) replaces the
            # uniform 1.5% for exports and for the debt-stabilising balance
            g_tr = mean_growth(trend_path(geo, base_year, 30, trend_draw))
            out["world_growth"] = g_tr
            out["g_nominal"] = (1.0 + g_tr) * (1.0 + INFLATION_TARGET) - 1.0
        return out
    return {"i_rate": 0.0 if i_rate is None else float(i_rate),
            "capital_tax_share": 0.0 if capital_tax_share is None else float(capital_tax_share)}


def profit_response_for(geo: Optional[str]) -> float:
    return PROFIT_RESPONSE.get((geo or "").upper(), PROFIT_RESPONSE_DEFAULT)


def _solve_linear(demand, scale: float) -> float:
    """Fixed point Y = demand(Y) for a demand LINEAR in Y: two evaluations give
    intercept and slope, so the solution is exact; a plain iteration guards any
    non-linear edge case."""
    f0 = demand(0.0)
    slope = (demand(scale) - f0) / scale
    Y = f0 / (1.0 - slope) if abs(1.0 - slope) > 1e-12 else scale
    if abs(demand(Y) - Y) <= 1e-8 * max(scale, abs(Y)):
        return Y
    Y = scale
    for _ in range(500):
        Y_new = demand(Y)
        if abs(Y_new - Y) <= 1e-10 * scale:
            return Y_new
        Y = Y_new
    return Y


def _two_class_gini(yd_w: float, yd_k: float, f_w: float) -> float:
    f_k = 1.0 - f_w
    total = yd_w + yd_k
    if total <= 0:
        return 0.0
    m_w = yd_w / f_w if f_w > 0 else 0.0
    m_k = yd_k / f_k if f_k > 0 else 0.0
    return f_w * f_k * abs(m_k - m_w) / total


class SFCCore(Module):
    name = "sfc_core"

    def __init__(self, base_year: int = 2019, calib_kwargs: Optional[dict] = None,
                 inv_elasticity: float = 0.0, fiscal_reaction: Optional[float] = None,
                 debt_target: Optional[float] = None, i_rate: Optional[float] = None,
                 fund_payout: float = 0.0, investment_closure: str = "behavioural",
                 profit_response: Optional[float] = None, debt_cap: float = DEBT_CAP,
                 loan_rate: Optional[float] = None, liquidity_floor: float = LIQUIDITY_FLOOR,
                 deleverage_rate: float = DELEVERAGE_RATE,
                 inflation_target: float = INFLATION_TARGET,
                 phillips_slope: float = PHILLIPS_SLOPE,
                 export_elasticity: float = EXPORT_ELASTICITY,
                 utilisation_response: float = UTILISATION_RESPONSE,
                 policy_start: int = POLICY_START,
                 capacity: Optional[dict] = None,
                 ai_foreign_share: float = AI_FOREIGN_SHARE,
                 levy_pass_through: float = LEVY_PASS_THROUGH,
                 r_world: float = R_WORLD,
                 external: Optional[dict] = None,
                 equity_valuation: str = "market",
                 consumption_differential: Optional[float] = None,
                 consumption_draw: float = 0.0,
                 banks: bool = True,
                 policy_rate_path: Optional[List[float]] = None,
                 neutral_rate: float = NEUTRAL_RATE,
                 risk_premium: float = RISK_PREMIUM,
                 deposit_beta: float = DEPOSIT_BETA,
                 loan_spread_shift: float = 0.0,
                 policy_rule: str = "neutral",
                 own_rate_path: Optional[List[float]] = None,
                 gov_rate_path: Optional[List[float]] = None,
                 euro_debt_path: Optional[List[float]] = None,
                 tax_scale_path: Optional[List[float]] = None,
                 labour_tax_shift_path: Optional[List[float]] = None,
                 capital_tax_shift_path: Optional[List[float]] = None,
                 legacy_loans: bool = True,
                 impact_mpc: float = IMPACT_MPC,
                 consumption_adjustment: Optional[float] = None,
                 trend_draw: float = 0.0):
        # every setting, so the euro-area reference run (Banks step) can copy them
        self._init_kwargs = {k: v for k, v in locals().items() if k not in ("self", "__class__")}
        self.base_year = base_year
        self.calib_kwargs = calib_kwargs or {}
        # C1 (enclosure-vs-diffusion): elasticity of investment to owners'
        # RETAINED capital-income share. 0.0 = autonomous capex (Phase 1-3
        # behaviour); >0 = socialising owners' returns (cash tax OR UBC
        # dilution) deters capex. An inspectable, swappable ASSUMPTION.
        self.inv_elasticity = float(inv_elasticity)
        # Phase 6 - proper fiscal block (all default OFF -> exact legacy behaviour):
        #   fiscal_reaction = tax-rate response per pp of debt/GDP gap (Taylor-style;
        #     lets the government consolidate or expand toward a debt target).
        #   debt_target = target debt/GDP in % (None -> the calibrated seed level).
        #   i_rate = override interest rate on gov debt (None -> calibrated p.i_rate,
        #     0 by default; set >0 to turn on the r-g snowball).
        # None = the closure default (behavioural: FISCAL_REACTION; legacy: 0)
        self.fiscal_reaction = None if fiscal_reaction is None else float(fiscal_reaction)
        self.debt_target = debt_target
        self.i_rate_override = i_rate
        # SWF calibration (default OFF -> legacy full-profit-share payout):
        #   fund_payout = the citizens' fund's percent-of-market-value (POMV) draw
        #   per year, grounded in real sovereign-wealth-fund rules - Norway GPFG's
        #   fiscal rule ~0.03 (3% of value, the expected real return) or the Alaska
        #   Permanent Fund's 0.05 (5% POMV, statute). The fund pays this out and
        #   REINVESTS the rest, so it COMPOUNDS like a real SWF and the dividend
        #   rests on the GPFG/Alaska track record, not the full domestic profit
        #   share. 0.0 keeps the legacy reinvest-split behaviour.
        self.fund_payout = float(fund_payout)
        # Phase 7 B investment closure (see module docstring).
        if investment_closure not in INVESTMENT_CLOSURES:
            raise ValueError(f"investment_closure must be one of {INVESTMENT_CLOSURES}, "
                             f"got {investment_closure!r}")
        self.investment_closure = investment_closure
        self.profit_response = (None if profit_response is None
                                else float(profit_response))   # None = country default
        self.debt_cap = float(debt_cap)
        # None = market rate (policy rate + spread) with banks; LOAN_RATE without
        self.loan_rate = None if loan_rate is None else float(loan_rate)
        self.liquidity_floor = float(liquidity_floor)
        self.deleverage_rate = float(deleverage_rate)
        # Phase 7 C supply side / prices (behavioural closure only)
        self.inflation_target = float(inflation_target)
        self.phillips_slope = float(phillips_slope)
        self.export_elasticity = float(export_elasticity)
        self.utilisation_response = float(utilisation_response)
        self.policy_start = int(policy_start)
        self.capacity = capacity          # {normal, base, max} override; None = data
        # Phase 7 D external sector (behavioural closure only)
        self.ai_foreign_share = float(ai_foreign_share)
        self.levy_pass_through = float(levy_pass_through)
        self.r_world = float(r_world)
        self.external = external          # {inward_gdp, outward_gdp, niip_gdp}; None = data
        # Phase 7 E1: UBC equity changes hands at MARKET value ("market", default)
        # or at the replacement cost of the capital ("book", the v1.1 rule)
        if equity_valuation not in ("market", "book"):
            raise ValueError("equity_valuation must be 'market' or 'book'")
        self.equity_valuation = equity_valuation
        # Phase 7 E5: MPC out of profits minus MPC out of wages (None = the
        # country's published estimate, data/connectors/consumption.py);
        # consumption_draw in [-1, 1] is the Monte-Carlo position in its range.
        self.consumption_differential = (None if consumption_differential is None
                                         else float(consumption_differential))
        self.consumption_draw = float(consumption_draw)
        # Banks step (behavioural only): a financial sector intermediates;
        # interest rates follow a policy rule (see docstring and rates.py)
        self.banks = bool(banks)
        self.policy_rate_path = None if policy_rate_path is None else list(policy_rate_path)
        self.neutral_rate = float(neutral_rate)
        self.risk_premium = float(risk_premium)
        self.deposit_beta = float(deposit_beta)
        self.loan_spread_shift = float(loan_spread_shift)
        if policy_rule not in ("taylor", "neutral"):
            raise ValueError("policy_rule must be 'taylor' or 'neutral'")
        # "neutral" (default, decided 2026-11-01): rates move from their 2019 level
        # to the neutral rate and do not react. A reacting rule has the wrong sign
        # here: higher rates raise households' interest income and nothing (no
        # mortgages, no asset prices) pushes the other way. "taylor" is kept for
        # step F, once those channels exist.
        self.policy_rule = policy_rule
        # Step F backtest inputs (None = the rules above): a floater's own policy
        # rate path; the rate on new government borrowing (realised long-term
        # yields, replacing policy + spread + premium); the euro area's debt
        # ratio path the risk premium is measured against (realised, replacing
        # the model's euro-area reference run)
        self.own_rate_path = None if own_rate_path is None else list(own_rate_path)
        self.gov_rate_path = None if gov_rate_path is None else list(gov_rate_path)
        self.euro_debt_path = None if euro_debt_path is None else list(euro_debt_path)
        # ... and the realised net-tax ratio relative to the base year, scaling
        # both calibrated tax rates in place of the fiscal rule
        self.tax_scale_path = None if tax_scale_path is None else list(tax_scale_path)
        # step F multiplier test: additive changes to the labour / capital tax
        # rate by year, on top of everything else
        self.labour_tax_shift_path = (None if labour_tax_shift_path is None
                                      else list(labour_tax_shift_path))
        self.capital_tax_shift_path = (None if capital_tax_shift_path is None
                                       else list(capital_tax_shift_path))
        # Phase 7 F (behavioural closure): firms' and households' existing loans
        # on the banks' books; the same-year share of a temporary income change
        # households spend (or the adjustment speed itself); the MC position in
        # the Ageing Report's TFP scenarios
        self.legacy_loans = bool(legacy_loans)
        self.impact_mpc = float(impact_mpc)
        self.consumption_adjustment = (None if consumption_adjustment is None
                                       else float(consumption_adjustment))
        self.trend_draw = float(trend_draw)
        self.params: Optional[SFCParams] = None

    def declares_inputs(self) -> List[str]:
        return [
            "gdp", "hh_consumption", "gov_consumption", "gfcf", "exports",
            "imports", "labour_share", "gov_debt_gdp", "gini_disp_income",
            "population",
        ]

    def declares_outputs(self) -> List[str]:
        return [
            "gdp", "consumption", "consumption_workers", "consumption_owners",
            "investment", "inventories", "intl_transfer",
            "gov_expenditure", "exports", "imports", "net_exports",
            "current_account", "wage_bill", "profits", "labour_share",
            "money_workers", "money_owners", "gov_debt", "gov_debt_gdp",
            "net_foreign_assets", "nfa_gdp", "capital", "gini", "ubi",
            "income_workers_pc", "income_owners_pc", "deficit",
            "net_wages", "net_profits", "hh_disposable", "transfer_pool",
            "swf_stake", "swf_share", "swf_dividend", "swf_dividend_pc",
            "owners_capital", "owners_capital_share", "citizen_wealth_pc",
            "inv_response", "swf_reinvest", "investment_private",
            "reinvest_rate", "capital_traditional", "capital_ai",
            "capital_ai_share", "gov_interest", "gov_interest_gdp",
            "gov_money", "gov_money_gdp", "loans_owners", "loans_owners_gdp",
            "owners_borrowing", "loan_interest", "investment_desired",
            "investment_cut", "financing_regime", "owners_liquidity_floor",
            "owners_net_profit_share", "loans_fund", "fund_debt_service",
            "debt_assumed_by_fund", "swf_net_assets",
            "gdp_real", "price_level", "inflation", "capacity", "utilisation",
            "output_gap", "excess_imports",
            "gni", "gni_real", "primary_income_net", "ai_rent", "ai_rent_abroad",
            "ai_rent_levy", "ai_rent_reached", "ai_rent_reached_share",
            "ai_rent_foreign_reached_share",
            "foreign_profits", "foreign_capital_share", "fdi_investment", "fdi_net_inflow",
            "owners_foreign_equity", "owners_foreign_income", "fund_foreign_equity",
            "fund_foreign_income", "public_external_position", "niip", "niip_gdp",
            "capital_income_hh_gross", "tax_rate_labour", "tax_rate_capital",
            "swf_market_value", "equity_q", "fund_seed", "ai_stake_income",
            "ai_stake_to_budget", "pledge_distributions", "broad_tax_rate",
        ]

    def _calibrate(self, geo, data):
        """calibrate() with this closure's fiscal settings -> (params, kwargs, reaction)."""
        ck = dict(self.calib_kwargs)
        fk = fiscal_calibration(geo, self.investment_closure,
                                i_rate=self.i_rate_override,
                                capital_tax_share=ck.get("capital_tax_share"),
                                base_year=self.base_year, trend_draw=self.trend_draw)
        if ck.get("capital_tax_share") is None:
            ck["capital_tax_share"] = fk["capital_tax_share"]
        if self.i_rate_override is not None or self.investment_closure == "behavioural":
            ck.setdefault("i_rate", fk["i_rate"])
        for k in ("g_nominal", "capital_output_ratio", "delta", "world_growth"):
            if k in fk:
                ck.setdefault(k, fk[k])
        if self.investment_closure == "behavioural" and self.banks:
            ck.setdefault("pb_rate", expected_gov_rate(geo, fk["i_rate"], self.neutral_rate,
                                                       base_year=self.base_year))
        p = calibrate(data, geo=geo, base_year=self.base_year,
                      sources=data.get("_sources", {}) if isinstance(data, dict) else {},
                      **ck)
        return p, ck

    def run(self, scenario: Scenario, data: Dict[str, float],
            context: Optional[dict] = None) -> RunResult:
        ck = dict(self.calib_kwargs)
        fk = fiscal_calibration(scenario.geo, self.investment_closure,
                                i_rate=self.i_rate_override,
                                capital_tax_share=ck.get("capital_tax_share"),
                                base_year=self.base_year, trend_draw=self.trend_draw)
        if ck.get("capital_tax_share") is None:
            ck["capital_tax_share"] = fk["capital_tax_share"]
        if self.i_rate_override is not None or self.investment_closure == "behavioural":
            ck.setdefault("i_rate", fk["i_rate"])         # calibration matches the run rate
        for k in ("g_nominal", "capital_output_ratio", "delta", "world_growth"):
            if k in fk:
                ck.setdefault(k, fk[k])
        if self.investment_closure == "behavioural" and self.banks:
            # Banks step: the structural primary balance holds the 2019 debt ratio
            # at the rate the government expects to pay on average over the
            # horizon (its 2015-19 rate rolling over into policy rate + spread)
            ck.setdefault("pb_rate", expected_gov_rate(scenario.geo, fk["i_rate"],
                                                       self.neutral_rate,
                                                       base_year=self.base_year))
        fiscal_reaction = (self.fiscal_reaction if self.fiscal_reaction is not None
                           else (FISCAL_REACTION if self.investment_closure == "behavioural"
                                 else 0.0))
        p = calibrate(data, geo=scenario.geo, base_year=self.base_year,
                      sources=data.get("_sources", {}) if isinstance(data, dict) else {},
                      **ck)
        self.params = p
        H = scenario.horizon
        f_w, f_k = p.f_workers, 1.0 - p.f_workers

        M_w, M_k, K = p.M_w0, p.M_k0, p.K0
        K_trad, K_ai = p.K0, 0.0      # AI capital starts ~0 and is built by the boom
        F_w, F_k = 0.0, 0.0           # net foreign assets start at 0 (accumulate CA)
        E_sf = 0.0                    # sovereign-fund capital stake (UBC); 0 = no fund
        Y_prev = p.Y0
        debt_target = (self.debt_target if self.debt_target is not None
                       else (100.0 * (p.M_w0 + p.M_k0) / p.Y0 if p.Y0 else 0.0))
        i_rate_eff = (self.i_rate_override if self.i_rate_override is not None
                      else p.i_rate)
        periods: List[PeriodState] = []
        behavioural = self.investment_closure == "behavioural"
        banks = behavioural and self.banks
        loan_fixed = (self.loan_rate if self.loan_rate is not None
                      else (None if banks else LOAN_RATE))
        r_l = loan_fixed if loan_fixed is not None else LOAN_RATE
        gamma = (self.profit_response if self.profit_response is not None
                 else profit_response_for(scenario.geo)) if behavioural else 0.0
        pi0 = (1.0 - p.ls0) * (1.0 - p.theta_k)   # base-year owners' net profit share
        pi_eff_prev = pi0                          # year 0 invests exactly as observed
        L = 0.0                                    # owners' loans (new net borrowing)
        L_sf = 0.0                                 # loans assumed by the fund with equity (UBC)
        liq_ratio = (self.liquidity_floor * p.M_k0 / p.K0) if p.K0 > 0 else 0.0
        # Phase 7 C: supply side and prices (behavioural only; legacy keeps P = 1)
        cu = (dict(self.capacity) if self.capacity else
              capacity_utilisation_for(scenario.geo, base_year=self.base_year))
        u_n, u_0, u_max = float(cu["normal"]), float(cu["base"]), float(cu["max"])
        v_cap = (u_0 * p.K0 / p.Y0) if p.Y0 else 1.0   # capital per unit of full-capacity output
        gap0 = u_0 / u_n - 1.0                          # base-year output gap (0 by default)
        gap_prev = gap0
        P = P_prev = 1.0
        ls_prev = p.ls0
        g_K0 = (p.a_ratio0 * p.Y0 / p.K0 - p.delta) if p.K0 else 0.0   # base-year capital growth
        g_tfp = min(max((1.0 + p.world_growth) / (1.0 + g_K0) - 1.0, TFP_BOUNDS[0]),
                    TFP_BOUNDS[1])
        # Phase 7 F: the country's trend (2024 Ageing Report). Exports grow at its
        # potential growth, and capacity per unit of capital drifts so that the
        # no-shock economy, investing its base-year share of output, grows at
        # exactly that path (the step C balance rule, now with the country's own
        # trend and capital stock instead of 1.5% and K/Y = 3). Capital deepens
        # (output per unit of capital falls) where the base year invests more
        # than the trend needs, as in the catching-up members.
        # The base year's output gap closes over GAP_CLOSE_YEARS, the Ageing
        # Report's own convention (gaps closed three years after the forecast),
        # so a 2019 boom or slack does not persist as permanent inflation and a
        # permanent real appreciation. Investment responds to departures of
        # utilisation from that expected path (firms expect the normalisation),
        # so the no-shock economy stays on trend.
        tp = (trend_path(scenario.geo, self.base_year, H, self.trend_draw)
              if (behavioural and TREND_FROM_DATA) else None)
        x_idx, a_idx = [1.0], [1.0]
        u_ref = [u_0] * H
        if tp:
            u_ref = [u_n + (u_0 - u_n) * max(0.0, 1.0 - t_ / GAP_CLOSE_YEARS) for t_ in range(H)]
            k_cur = p.K0 * (1.0 - p.delta) + p.a_ratio0 * p.Y0
        for t_ in range(1, H):
            gy = tp["growth"][t_] if tp else p.world_growth
            x_idx.append(x_idx[-1] * (1.0 + gy))
            if tp:
                # capacity at t rests on the stock at the end of t-1
                a_idx.append(x_idx[t_] * (u_0 / u_ref[t_]) / (k_cur / p.K0))
                k_cur = k_cur * (1.0 - p.delta) + p.a_ratio0 * p.Y0 * x_idx[t_]
            else:
                a_idx.append(a_idx[-1] * (1.0 + g_tfp))
        gap_ref = [u / u_n - 1.0 for u in u_ref]          # = gap0 throughout without a trend
        infl = self.inflation_target if behavioural else 0.0
        # Phase 7 D: the external sector (behavioural only; legacy keeps the v1.1
        # rule - the current account accrues to households by money shares).
        ext = (dict(self.external) if self.external is not None else
               external_position_for(scenario.geo, base_year=self.base_year))
        if behavioural:
            # foreign owners' stake = their share of NET profits: equity income
            # paid abroad (dividends + reinvested FDI earnings, a net-of-
            # depreciation concept, Eurostat) / (gross profits - depreciation)
            net_profit0 = max((1.0 - p.ls0) - p.delta * p.K0 / p.Y0, 0.05)
            psi0 = min(0.9, max(0.0, float(ext["inward_gdp"])) / net_profit0)
            E_row = psi0 * p.K0                          # real claim on domestic capital
            A_kf = max(0.0, float(ext["outward_gdp"])) * p.Y0 / self.r_world   # owners' equity abroad
            FX_s0 = float(ext["niip_gdp"]) * p.Y0 - A_kf + E_row   # the rest of the NIIP
        else:
            psi0 = E_row = A_kf = FX_s0 = 0.0
        FX_s, A_sff = FX_s0, 0.0                         # public stand-in / fund abroad
        # owners reinvest abroad at the WORLD's nominal growth (not their own country's)
        g_wn = ((1.0 + (WORLD_GROWTH if tp else p.world_growth)) * (1.0 + self.inflation_target)
                - 1.0)
        fpd_share_prev = 1.0 - p.ls0                     # profit share net of AI fees
        # E1: market value of a unit of capital relative to its replacement cost
        # (Tobin's q), priced on the after-tax net profit rate against 2019's
        # (a Gordon valuation with a constant required return; q = 1 in 2019)
        rprof0 = rprof_prev = None
        q = 1.0
        pi_row_prev = pi0
        # Banks step: a financial sector (banks, insurers, pension funds) with no
        # capital of its own holds the government's bonds, the owners' loans and
        # the country's foreign debt-type position, financed by households'
        # deposits; it pays its interest margin out as profit. IE and CY keep the
        # public stand-in for the foreign position (households would start with
        # no deposits). Rates follow a policy rule: the ECB path from the euro-
        # area aggregate under the same AI scenario (euro members, DK, BG, HR) or
        # the country's own Taylor rule (CZ, HU, PL, RO, SE).
        rc = rates_for(scenario.geo, base_year=self.base_year) if banks else None
        B = p.M_w0 + p.M_k0                              # government bonds (2019 debt)
        # Phase 7 F: the loans firms and households already owe, on the banks'
        # books (Eurostat financial accounts): the domestically owned firms' part
        # by the owners, household loans by both classes in proportion to their
        # base-year disposable income. Deposits gross up by the same amounts, so
        # each class's NET financial wealth is unchanged.
        Lw = Lc = Lhk = 0.0
        legacy = None
        if banks and self.legacy_loans:
            legacy = private_loans_for(scenario.geo, base_year=self.base_year)
            inc_w = p.ls0 * (1.0 - p.theta_w)
            inc_k = (1.0 - psi0) * (1.0 - p.ls0) * (1.0 - p.theta_k)
            s_hw = inc_w / (inc_w + inc_k) if (inc_w + inc_k) > 0 else f_w
            Lc = (1.0 - psi0) * float(legacy["nfc"]) * p.Y0
            Lw = s_hw * float(legacy["hh"]) * p.Y0
            Lhk = (1.0 - s_hw) * float(legacy["hh"]) * p.Y0
            legacy = dict(legacy, workers_share=s_hw)
        sh_w0 = (p.M_w0 / B) if B > 0 else 0.3
        D_net = B + FX_s0
        # the public stand-in takes the foreign position wherever a class's
        # deposits would start at or below zero (step F: the rule, not a list;
        # in 2019 it selects IE and CY, the list)
        fx_bank = bool(banks and not rc["stand_in"]
                       and (not STAND_IN_BY_RULE
                            or (sh_w0 * D_net + Lw > 0.0 and (1.0 - sh_w0) * D_net + Lc + Lhk > 0.0)))
        if fx_bank:
            M_w, M_k = sh_w0 * D_net, (1.0 - sh_w0) * D_net
        M_w, M_k = M_w + Lw, M_k + Lc + Lhk
        if fx_bank or legacy:
            liq_ratio = (self.liquidity_floor * M_k / p.K0) if p.K0 > 0 else 0.0
        i_g = i_rate_eff                                 # average rate on public debt
        i_p = r_dep = r_h = r_fx = i_new = 0.0
        ea_path, ea_ref = None, None
        ea_debt = None              # euro-area debt ratio path (relative risk premium)
        gov_debt_rep = B
        debt_ratio0 = (B / p.Y0) if p.Y0 else 0.0
        pi_b = tax_bank = bank_row = bank_own = 0.0
        if banks:
            geo_u = (scenario.geo or "").upper()
            if geo_u != EURO_AREA:
                if self.policy_rate_path is not None:
                    ea_path, ea_ref = list(self.policy_rate_path), "given"
                elif self.policy_rule == "neutral":
                    ea_path = _neutral_path(rc["ea_policy0"], self.neutral_rate, H)
                    ea_ref = "ECB rate: 2019 level to the neutral rate"
                else:
                    ref = _euro_reference(self, scenario, H)
                    ea_path, ea_ref = ref["policy"], ref["label"]
                if self.risk_premium:
                    # the premium estimate is a SPREAD over the euro area: only the
                    # debt a country adds beyond the euro area's own path counts
                    ea_debt = (list(self.euro_debt_path) if self.euro_debt_path is not None
                               else _euro_reference(self, scenario, H)["debt_ratio"])
            peg = rc["policy0"] - rc["ea_policy0"]       # DK's 2019 spread; 0 in the euro
            i_p = rc["policy0"]
            ea_rate = rc["ea_policy0"] if ea_path is None else ea_path[0]
            r_dep = rc["deposit_rate0"]
            r_h = rc["deposit_share"] * r_dep + (1.0 - rc["deposit_share"]) * i_g
            r_l = loan_fixed if loan_fixed is not None else (
                i_p + rc["loan_spread"] + self.loan_spread_shift)
            # a net creditor's foreign debt-type assets earn the euro-area long
            # rate; a net debtor's foreign liabilities are largely its government
            # debt held abroad, so they cost the government's average rate
            r_fx = (ea_rate + rc["ea_term"]) if FX_s0 >= 0 else i_g
            i_new = i_p + rc["gov_spread"]
            # year-0 bank profit (no new loans yet), paid to owners after tax
            pi_b0 = (i_g * B + (r_fx * FX_s0 if fx_bank else 0.0) - r_h * (M_w + M_k)
                     + r_l * (Lw + Lc + Lhk))
            bank_own0 = (1.0 - psi0) * pi_b0
        # Phase 7 E5: both classes' propensities to consume. Two facts pin them:
        # 2019 consumption (C0 - a2*M0, which calibrate() matched with its own
        # a1_w and residual a1_k) and the country's published effect of moving
        # one unit of pre-tax income from wages to profits on consumption,
        #   d = a1_k (1 - psi)(1 - theta_k) - a1_w (1 - theta_w)
        # (owners get only the domestically owned part, after tax). Owners
        # consume out of their income NET of depreciation on the capital they
        # own: replacing worn-out capital is firms' saving, not income to spend
        # (with it, workers' implied saving rates match the household saving
        # rates in the national accounts). The legacy closure keeps a1_w and
        # the residual a1_k on gross income.
        a1_w, a1_k = p.a1_w, p.a1_k
        cd = None
        if behavioural:
            cd = (consumption_differential_for(scenario.geo, self.consumption_draw)
                  if self.consumption_differential is None else
                  {"value": self.consumption_differential, "flag": "override",
                   "source": "SFCCore(consumption_differential=...)"})
            d_c = float(cd["value"])
            yd_w0 = p.ls0 * (1.0 - p.theta_w) * p.Y0 + i_rate_eff * p.M_w0
            yd_k0_old = (1.0 - p.ls0) * (1.0 - p.theta_k) * p.Y0 + i_rate_eff * p.M_k0
            yd_k0_new = ((1.0 - psi0) * (1.0 - p.ls0) * (1.0 - p.theta_k) * p.Y0
                         + i_rate_eff * p.M_k0 + self.r_world * A_kf)
            c_target = p.a1_w * yd_w0 + p.a1_k * yd_k0_old      # = C0 - a2 * M0
            if banks:      # deposits, their rate and the banks' margin change year-0 incomes
                # (consumption out of wealth is on NET money: deposits less loans)
                c_target += p.a2 * (p.M_w0 + p.M_k0 - (M_w - Lw)
                                    - max(0.0, M_k - Lc - Lhk))
                yd_w0 = p.ls0 * (1.0 - p.theta_w) * p.Y0 + r_h * M_w - r_l * Lw
                yd_k0_new = ((1.0 - psi0) * (1.0 - p.ls0) * (1.0 - p.theta_k) * p.Y0
                             + r_h * M_k - r_l * (Lc + Lhk) + self.r_world * A_kf + bank_own0)
            yd_k0_net = yd_k0_new - p.delta * (1.0 - psi0) * p.K0   # less owners' CFC
            k_d = (1.0 - psi0) * (1.0 - p.theta_k)
            if yd_k0_net > 0 and k_d > 0:
                a1_w = ((c_target - yd_k0_net * d_c / k_d)
                        / (yd_w0 + yd_k0_net * (1.0 - p.theta_w) / k_d))
                if a1_w > MAX_WORKERS_MPC:
                    # workers cannot spend more than their income every year
                    # without running out of money (EL dissaved in 2019); cap
                    # them and let the owners match 2019 consumption.
                    a1_w = MAX_WORKERS_MPC
                    a1_k = (c_target - a1_w * yd_w0) / yd_k0_net
                    cd = dict(cd, flag=cd["flag"] + "+workers_capped",
                              value=a1_k * k_d - a1_w * (1.0 - p.theta_w))
                else:
                    a1_k = (d_c + a1_w * (1.0 - p.theta_w)) / k_d
        # Phase 7 F: consumption adjusts to its long-run level (the propensities
        # above) by the share lam a year, so the same-year propensity to spend a
        # temporary change in income is lam * a1 (IMPACT_MPC on average)
        lam = 1.0
        if behavioural:
            if self.consumption_adjustment is not None:
                lam = min(1.0, max(0.05, self.consumption_adjustment))
            else:
                y_w, y_k = max(yd_w0, 0.0), max(yd_k0_net, 0.0)
                avg_a1 = ((a1_w * y_w + a1_k * y_k) / (y_w + y_k)) if (y_w + y_k) > 0 else a1_w
                lam = min(1.0, max(0.05, self.impact_mpc / avg_a1)) if avg_a1 > 0 else 1.0
        C_w_prev = C_k_prev = None                       # year 0 consumes its long-run level

        for t in range(H):
            infl_last = infl                            # last year's inflation (policy rule)
            gap_ref_prev = gap_ref[t - 1] if t > 0 else gap_ref[0]
            ls = scenario.labour_share.at(t, H)
            if behavioural:
                if t > 0:      # price setting reacts to last year's demand pressure
                    infl = self.inflation_target + self.phillips_slope * gap_prev
                    P = P_prev * (1.0 + infl)
                pfac = P / P_prev                       # real rules keep their real meaning
                P_world = (1.0 + self.inflation_target) ** t
            else:
                pfac = P_world = 1.0
            Pk = P                                      # 1.0 in legacy
            if banks and t > 0:
                if self.own_rate_path is not None and (ea_path is None or rc["regime"] == "own"):
                    i_p = self.own_rate_path[t]                 # backtest: realised rate
                elif ea_path is None or rc["regime"] == "own":
                    tgt = self.neutral_rate
                    if self.policy_rule == "taylor":
                        tgt += (TAYLOR_INFLATION * (infl_last - self.inflation_target)
                                + TAYLOR_GAP * (gap_prev - gap0))   # 2019 stance = 2019 slack
                    i_p = max(rc.get("rate_floor", RATE_FLOOR),
                              RATE_SMOOTHING * i_p + (1.0 - RATE_SMOOTHING) * tgt)
                else:
                    i_p = ea_path[t] + peg
                ea_rate = i_p if ea_path is None else ea_path[t]
                debt_ratio_prev = (gov_debt_rep / Y_prev) if Y_prev else debt_ratio0
                # new borrowing: policy rate + the country's term/credit spread +
                # a premium on the debt it added since 2019 beyond the euro area's
                # (Pamies et al. estimate spreads over Germany); the average rate
                # follows as debt rolls over
                excess = debt_ratio_prev - debt_ratio0
                if ea_debt is not None:
                    excess -= ea_debt[t - 1] - ea_debt[0]
                elif geo_u == EURO_AREA:
                    excess = 0.0            # the aggregate has no spread over itself
                i_new = i_p + rc["gov_spread"] + self.risk_premium * excess
                if self.gov_rate_path is not None:
                    i_new = self.gov_rate_path[t]               # backtest: realised yield
                i_g += (i_new - i_g) / DEBT_MATURITY
                r_dep = max(0.0, rc["deposit_rate0"] + self.deposit_beta * (i_p - rc["policy0"]))
                r_h = rc["deposit_share"] * r_dep + (1.0 - rc["deposit_share"]) * i_g
                if loan_fixed is None:
                    r_l = i_p + rc["loan_spread"] + self.loan_spread_shift
                r_fx = (ea_rate + rc["ea_term"]) if FX_s >= 0 else i_g
            base_A = scenario.ai_capex.at(t, H) * p.Y0   # autonomous AI-capex
            G = (scenario.gov_override.at(t, H)
                 if scenario.gov_override is not None
                 else scenario.gov_ratio.at(t, H) * Y_prev)
            # exports are driven by EXOGENOUS foreign demand, not own output:
            # X grows at the world-demand rate from the calibrated baseline level.
            # (Tying X to own output makes entrepot economies where trade > GDP
            # explode — the Luxembourg blow-up. This closure is stable for any
            # openness.) An explicit override from the trade linker wins if set.
            X = (scenario.exports_override.at(t, H)
                 if scenario.exports_override is not None
                 else p.export_ratio * p.Y0 * (x_idx[t] if behavioural
                                               else (1.0 + p.world_growth) ** t))
            if behavioural:
                if scenario.gov_override is None:
                    G *= pfac
                if scenario.exports_override is None:   # competitiveness vs the world's 2% path
                    X *= P * (P / P_world) ** (-self.export_elasticity)
            tau = scenario.tax_capital.at(t, H)
            ubi_on = scenario.ubi_on.at(t, H) >= 0.5
            ubc_on = scenario.ubc_on.at(t, H) >= 0.5
            if behavioural and t < self.policy_start:
                tau, ubi_on, ubc_on = 0.0, False, False
            # Phase 6 fiscal-reaction rule (default OFF): adjusts the LABOUR rate
            # (the usual marginal instrument) to steer debt/GDP toward target.
            if fiscal_reaction:
                debt_gdp_prev = ((100.0 * (M_w + M_k - L - L_sf - (FX_s - FX_s0)) / Y_prev)
                                 if Y_prev else debt_target)
                if banks:
                    debt_gdp_prev = (100.0 * gov_debt_rep / Y_prev) if Y_prev else debt_target
                delta_theta = fiscal_reaction * (debt_gdp_prev - debt_target)
            else:
                delta_theta = 0.0
            theta_w = min(0.95, max(0.0, p.theta_w + delta_theta))
            theta_k = p.theta_k
            if behavioural:      # E3: the rule moves the tax rate on ALL taxed income
                theta_k = min(0.95, max(0.0, p.theta_k + delta_theta))
            if self.tax_scale_path is not None:     # step F backtest: realised net taxes
                s_tax = self.tax_scale_path[min(t, len(self.tax_scale_path) - 1)]
                theta_w = min(0.95, max(0.0, p.theta_w * s_tax))
                theta_k = min(0.95, max(0.0, p.theta_k * s_tax))
            if self.labour_tax_shift_path is not None and t < len(self.labour_tax_shift_path):
                theta_w = min(0.95, max(0.0, theta_w + self.labour_tax_shift_path[t]))
            if self.capital_tax_shift_path is not None and t < len(self.capital_tax_shift_path):
                theta_k = min(0.95, max(0.0, theta_k + self.capital_tax_shift_path[t]))

            M_w_prev, M_k_prev, K_prev = M_w, M_k, K
            K_trad_prev, K_ai_prev = K_trad, K_ai
            F_w_prev, F_k_prev, E_sf_prev = F_w, F_k, E_sf
            L_prev, L_sf_prev = L, L_sf
            Lw_prev, Lc_prev, Lhk_prev = Lw, Lc, Lhk
            B_prev = B
            E_row_prev, A_kf_prev, A_sff_prev, FX_s_prev = E_row, A_kf, A_sff, FX_s
            # D1: foreign owners' share of domestic capital (UBC cannot dilute it)
            psi = (min(E_row_prev / K_prev, 1.0) if (behavioural and K_prev > 0) else 0.0)
            own_K_prev0 = max(K_prev - E_sf_prev - E_row_prev, 0.0)

            # fund's ownership share entering the period drives this year's dividend
            phi = (min(E_sf_prev / K_prev, 1.0 - psi)
                   if (ubc_on and K_prev > 0) else 0.0)

            # C1 investment feedback: owners fund capex and respond to the
            # share of capital income they still RETAIN. Cash tax and UBC
            # both extract tau*FP/yr, but UBC keeps socialising the STOCK, so
            # its signal (1-phi) keeps falling while the cash signal (1-tau)
            # is flat - the sharp test of whether predistribution chokes capex.
            inv_signal = (1.0 - phi) if ubc_on else (1.0 - tau)
            inv_mult = inv_signal ** self.inv_elasticity   # applied capex multiplier
            A_priv = base_A * inv_mult                      # privately-financed capex
            A_row = ai_row = 0.0                            # foreign owners' investment (D1)
            if behavioural:
                # B1: owners invest on the stake they own; the investment share
                # responds to last year's net profit share (see docstring).
                inv_share = max(0.0, p.a_ratio0 + gamma * (pi_eff_prev - pi0)
                                + self.utilisation_response * (gap_prev - gap_ref_prev))
                A_priv = (1.0 - phi - psi) * Y_prev * pfac * inv_share
                # the part driven by a HIGHER net profit share (the AI boom)
                ai_desired = (1.0 - phi - psi) * Y_prev * pfac * max(0.0, gamma * (pi_eff_prev - pi0))
                inv_mult = (inv_share / p.a_ratio0) if p.a_ratio0 else 1.0
                # D1: foreign owners invest on their stake by the same rule (FDI),
                # financed by their parents, so it is never cut for lack of cash.
                inv_share_row = max(0.0, p.a_ratio0 + gamma * (pi_row_prev - pi0)
                                    + self.utilisation_response * (gap_prev - gap_ref_prev))
                A_row = psi * Y_prev * pfac * inv_share_row
                ai_row = psi * Y_prev * pfac * max(0.0, gamma * (pi_row_prev - pi0))
            A_desired = A_priv
            on = behavioural and t >= self.policy_start          # E2 proposal levers
            seed = (scenario.fund_seed.at(t, H) * Y_prev * pfac
                    + scenario.fund_seed_eur.at(t, H)) if on else 0.0
            s_ai = scenario.ai_equity_stake.at(t, H) if on else 0.0
            ai_pay = scenario.ai_stake_payout.at(t, H) if on else 0.0
            pledge = scenario.pledge_share.at(t, H) if on else 0.0
            t_b = scenario.broad_tax.at(t, H) if on else 0.0
            if t_b > 0.0:
                ubi_on = True                     # a broad-base tax pays a cash UBI
            # the citizens' fund exists with a UBC stake, a seed, or assets abroad
            fund_on = behavioural and (ubc_on or seed > 0.0 or A_sff > 0.0)
            reinvest = scenario.ubc_reinvest.at(t, H) if (ubc_on or fund_on) else 0.0
            if behavioural and self.equity_valuation == "market" and rprof0:
                q = max(0.2, rprof_prev / rprof0)
            # the fund's payout rule: the engine setting, else the scenario's (E)
            payout = (self.fund_payout if self.fund_payout > 0.0
                      else (scenario.fund_payout.at(t, H) if behavioural else 0.0))
            fund_capex = fund_abroad = 0.0
            if fund_on:
                # the fund invests on its stake by the owners' rule (its return is
                # the gross profit share: it pays no levy on itself), up to the
                # budget its payout policy retains, planned on last year's profits.
                fund_share = max(0.0, p.a_ratio0
                                 + gamma * (fpd_share_prev * (1.0 - p.theta_k) - pi0)
                                 + self.utilisation_response * (gap_prev - gap_ref_prev))
                fund_desired = phi * Y_prev * pfac * fund_share
                expected_net = phi * fpd_share_prev * (1.0 - theta_k) * Y_prev * pfac - (
                    r_l + self.deleverage_rate) * L_sf_prev + self.r_world * A_sff_prev
                # Replacement comes out of the depreciation allowance (CFC) before
                # any dividend: owners do not pay out capital consumption and
                # neither does the fund, so `reinvest` applies to NET profits and
                # a POMV draw cannot eat into replacement.
                dep_prev = ((p.delta * K_trad_prev + p.delta_ai * K_ai_prev) / K_prev
                            if K_prev > 0 else p.delta)
                cfc_fund = dep_prev * Pk * E_sf_prev
                if payout > 0.0:          # POMV on the fund's MARKET value
                    budget = max(cfc_fund, expected_net
                                 - payout * (Pk * q * E_sf_prev - L_sf_prev + A_sff_prev))
                else:
                    budget = cfc_fund + reinvest * max(0.0, expected_net - cfc_fund)
                budget = min(budget, max(0.0, expected_net))   # cannot retain more than it earns
                fund_capex = max(0.0, min(budget, fund_desired))
                # D3: what it retains but does not need at home buys equity abroad
                fund_abroad = max(0.0, budget - fund_capex)
            # interest on government debt (gov money held by households),
            # predetermined from last period's debt; paid out by money share.
            gov_debt_prev = M_w_prev + M_k_prev
            sh_w_m = (M_w_prev / gov_debt_prev) if gov_debt_prev > 0 else 0.5
            interest = i_rate_eff * gov_debt_prev
            int_w, int_k = interest * sh_w_m, interest * (1.0 - sh_w_m)
            int_L = r_l * L_prev if behavioural else 0.0   # owners -> lender
            int_Lw = r_l * Lw_prev                          # step F: existing loans
            int_Lk = r_l * (Lc_prev + Lhk_prev)
            # nominal trend growth this year: the habit path of consumption
            g_hab = ((1.0 + (tp["growth"][t] if tp else p.world_growth))
                     * (1.0 + self.inflation_target) - 1.0)
            # the fund's assumed debt: interest + repayment as loans mature
            # (predetermined, so the demand solve stays linear)
            int_sf = r_l * L_sf_prev if behavioural else 0.0
            if banks:      # the government pays on its bonds; savers earn the household rate
                interest = i_g * B_prev
                int_w, int_k = r_h * M_w_prev, r_h * M_k_prev
            rep_sf = self.deleverage_rate * L_sf_prev if behavioural else 0.0
            fund_service = int_sf + rep_sf
            # D3: income on equity abroad (world return) and on the net external
            # position (the government-money rate; 0 by default). Owners reinvest
            # abroad at the world's nominal growth rate and bring the rest home.
            Y_kf = self.r_world * A_kf_prev if behavioural else 0.0
            dA_kf = g_wn * A_kf_prev if behavioural else 0.0
            Y_sf = self.r_world * A_sff_prev if behavioural else 0.0
            int_fx = i_rate_eff * FX_s_prev if behavioural else 0.0
            if banks:
                # the public stand-in (IE, CY) only holds the position: its income
                # belongs to the conduits' intra-group flows, not the budget
                int_fx = r_fx * FX_s_prev if fx_bank else 0.0
                # the financial sector's margin: paid out, the foreign-owned share
                # abroad (predetermined -> linear solve). Untaxed, like all interest
                # income in the model: the 2019 tax rates were set on wages and
                # profits alone, so taxing the margin would be revenue they never had
                pi_b = (interest + int_L + int_sf + (int_fx if fx_bank else 0.0)
                        - int_w - int_k + int_Lw + int_Lk)
                tax_bank = 0.0
                bank_row = psi * (pi_b - tax_bank)
                bank_own = pi_b - tax_bank - bank_row
            s_lev = (scenario.source_levy.at(t, H)
                     if (behavioural and t >= self.policy_start) else 0.0)
            levy_to = "ubi" if ubi_on else ("fund" if ubc_on else "gov")
            # depreciation on foreign-owned capital: the balance of payments books
            # income and FDI net of it (gross flows net out to the same cash)
            cfc_row = ((((p.delta * K_trad_prev + p.delta_ai * K_ai_prev) / K_prev)
                        if K_prev > 0 else p.delta) * Pk * E_row_prev) if behavioural else 0.0
            # E5: depreciation on the capital domestic owners own (firms' saving)
            cfc_own = ((((p.delta * K_trad_prev + p.delta_ai * K_ai_prev) / K_prev)
                        if K_prev > 0 else p.delta)
                       * Pk * max(K_prev - E_sf_prev - E_row_prev, 0.0)) if behavioural else 0.0
            # inventories+valuables (P52+P53): constant autonomous, owner-
            # financed, NOT added to productive K (closes the identity).
            INV = p.inv0 * Pk
            INV_d = INV                                 # desired inventories (nominal)
            excess = 0.0                                # demand met by extra imports at the ceiling
            # cross-border secondary income (pooled global dividend), per capita
            T_int = (scenario.intl_transfer.at(t, H)
                     if scenario.intl_transfer is not None else 0.0)
            tr_w, tr_k = T_int * f_w, T_int * f_k

            def breakdown(Y: float):
                WB = ls * Y
                FP = (1.0 - ls) * Y
                tax_w = theta_w * WB
                tax_k_base = theta_k * FP            # P6 baseline capital tax (general revenue)
                if ubc_on:
                    # capital income socialised in kind: fund owns phi of it.
                    # The fund REINVESTS a fraction and pays out the rest, so as
                    # owners are diluted the fund sustains capex (resolves C1).
                    gross_fund = phi * FP
                    net_fund = gross_fund - fund_service   # after servicing assumed debt
                    if behavioural:
                        A_fund = fund_capex               # predetermined -> solve stays linear
                        div_total = net_fund - A_fund
                    elif self.fund_payout > 0.0:
                        # GPFG/Alaska POMV: pay out fund_payout of the fund's VALUE,
                        # reinvest the rest -> the fund compounds like a real SWF.
                        # E_sf_prev is predetermined, so the draw is constant within
                        # the period -> the demand solve stays exactly linear (gate clean).
                        div_total = self.fund_payout * (Pk * E_sf_prev - L_sf_prev)
                        A_fund = net_fund - div_total
                    else:
                        A_fund = reinvest * net_fund       # legacy reinvest split
                        div_total = net_fund - A_fund
                    owners_profit = (1.0 - phi) * FP
                    if behavioural:                  # P6 base taxes the owners' share only
                        tax_k_base = theta_k * owners_profit
                    tax_k = 0.0                      # no cash levy; dilution instead
                    ubi_pool = 0.0
                    transfer_pool = div_total
                    div_w, div_k = div_total * f_w, div_total * f_k
                    YD_w = WB - tax_w + div_w + int_w + tr_w
                    YD_k = owners_profit - tax_k_base + div_k + int_k + tr_k
                    net_profits = owners_profit - tax_k_base
                elif ubi_on:
                    tax_k = tau * FP
                    ubi_pool = tax_k
                    transfer_pool = ubi_pool
                    div_total = owners_profit = 0.0
                    div_w = div_k = 0.0
                    ubi_w, ubi_k = ubi_pool * f_w, ubi_pool * f_k
                    YD_w = WB - tax_w + ubi_w + int_w + tr_w
                    YD_k = FP - tax_k - tax_k_base + ubi_k + int_k + tr_k
                    net_profits = FP - tax_k - tax_k_base
                    gross_fund = A_fund = 0.0
                else:
                    tax_k = tau * FP
                    ubi_pool = transfer_pool = 0.0
                    div_total = owners_profit = 0.0
                    div_w = div_k = ubi_w = ubi_k = 0.0
                    YD_w = WB - tax_w + int_w + tr_w
                    YD_k = FP - tax_k - tax_k_base + int_k + tr_k
                    net_profits = FP - tax_k - tax_k_base
                    gross_fund = A_fund = 0.0
                if behavioural:
                    YD_k -= int_L                    # interest on owners' loans
                    wealth_k = max(0.0, M_k_prev + F_k_prev - L_prev)   # net of debt
                else:
                    wealth_k = M_k_prev + F_k_prev
                C_w = p.a1_w * YD_w + p.a2 * (M_w_prev + F_w_prev)
                C_k = p.a1_k * YD_k + p.a2 * wealth_k
                return dict(WB=WB, FP=FP, tax_w=tax_w, tax_k=tax_k, tax_k_base=tax_k_base,
                            ubi_pool=ubi_pool, transfer_pool=transfer_pool,
                            div_total=div_total, div_w=div_w, div_k=div_k,
                            owners_profit=owners_profit, net_profits=net_profits,
                            gross_fund=gross_fund, A_fund=A_fund,
                            YD_w=YD_w, YD_k=YD_k, C_w=C_w, C_k=C_k)

            def breakdown_beh(Y: float):
                """Phase 7 D income split (behavioural closure). LINEAR in Y."""
                WB = ls * Y
                R = max(0.0, p.ls0 - ls) * Y              # AI rent: income moved from labour
                F = self.ai_foreign_share * R              # earned abroad (licence / cloud fees)
                levy = s_lev * F                           # source levy, withheld on the fees
                F_gross = F + self.levy_pass_through * levy   # the passed-on part raises the fee
                FP_all = (1.0 - ls) * Y - F_gross          # domestic firms' profit after fees
                # E2: the fund's stake in the domestic AI firms takes s_ai of the
                # AI rent kept at home before the other holders (one-time levy)
                ai_inc = s_ai * max(0.0, R - F_gross)
                ai_net = ai_inc * (1.0 - theta_k)          # after corporate tax (at source)
                ai_div = min(ai_net, ai_pay * ai_net / self.r_world)   # % of its value
                ai_gov = ai_net - ai_div                   # the rest funds public goods
                FP = FP_all - ai_inc                       # profits of the other holders
                FP_row = psi * FP                          # foreign owners' share of it
                tax_w = (theta_w + t_b) * WB
                src = (0.0 if ubc_on else tau) + t_b       # cash levies are applied at source
                pledge_in = pledge * max(0.0, F_gross - levy)   # E2: returned by pledges
                FP_row_net = FP_row - (theta_k + src) * FP_row
                levy_fund = levy if levy_to == "fund" else 0.0
                if ubc_on:
                    gross_fund = phi * FP
                    owners_profit = (1.0 - phi - psi) * FP
                    A_fund = fund_capex                    # predetermined -> solve stays linear
                    own_fp = owners_profit
                    tax_k_own, tax_kb_own = t_b * owners_profit, theta_k * owners_profit
                    # E: corporate taxes are paid at source, whoever owns the firm
                    # (the fund pays no LEVY on itself, but its firms pay tax)
                else:
                    gross_fund = A_fund = owners_profit = 0.0
                    own_fp = (1.0 - psi) * FP
                    tax_k_own, tax_kb_own = (tau + t_b) * own_fp, theta_k * own_fp
                tax_fund = theta_k * (gross_fund + ai_inc)   # corporate tax on the fund's firms
                fund_div = ((gross_fund * (1.0 - theta_k) - fund_service + Y_sf - A_fund
                             - fund_abroad) if fund_on else 0.0)
                div_total = fund_div + ai_div
                ubi_pool = (((0.0 if ubc_on else tau) * FP + levy * (levy_to == "ubi")
                             + t_b * (WB + FP)) if ubi_on else 0.0)
                transfer_pool = ubi_pool + div_total + pledge_in
                div_w, div_k = div_total * f_w, div_total * f_k
                ubi_w, ubi_k = (ubi_pool + pledge_in) * f_w, (ubi_pool + pledge_in) * f_k
                tax_k = tax_k_own + src * FP_row
                tax_k_base = tax_kb_own + theta_k * FP_row + tax_fund
                YD_w = WB - tax_w + ubi_w + div_w + int_w + tr_w - int_Lw
                YD_k = (own_fp - tax_k_own - tax_kb_own + ubi_k + div_k + int_k + tr_k
                        + Y_kf - int_L - int_Lk + bank_own)
                net_profits = own_fp - tax_k_own - tax_kb_own + Y_kf
                wealth_k = max(0.0, M_k_prev - L_prev - Lc_prev - Lhk_prev)   # net of debt
                C_w = a1_w * YD_w + p.a2 * (M_w_prev - Lw_prev)
                C_k = a1_k * (YD_k - cfc_own) + p.a2 * wealth_k     # E5: net of CFC
                if C_w_prev is not None:      # F: partial adjustment to the long-run level
                    C_w = lam * C_w + (1.0 - lam) * C_w_prev * (1.0 + g_hab)
                    C_k = lam * C_k + (1.0 - lam) * C_k_prev * (1.0 + g_hab)
                if w_cap[0]:
                    # workers with no deposits left cannot keep spending at their
                    # habit level: they spend their income and what they have left
                    C_w = YD_w + M_w_prev + Lw_prev * (Y / Y_prev - 1.0)
                return dict(WB=WB, FP=FP, tax_w=tax_w, tax_k=tax_k, tax_k_base=tax_k_base,
                            ubi_pool=ubi_pool, transfer_pool=transfer_pool,
                            div_total=div_total, div_w=div_w, div_k=div_k,
                            owners_profit=owners_profit, net_profits=net_profits,
                            gross_fund=gross_fund, A_fund=A_fund,
                            YD_w=YD_w, YD_k=YD_k, C_w=C_w, C_k=C_k,
                            R=R, F_gross=F_gross, levy=levy, levy_fund=levy_fund,
                            FP_row=FP_row, FP_row_net=FP_row_net, own_fp=own_fp,
                            tax_k_own=tax_k_own, tax_kb_own=tax_kb_own,
                            ai_inc=ai_inc, ai_div=ai_div, ai_gov=ai_gov, fund_div=fund_div,
                            pledge_in=pledge_in, FP_all=FP_all, tax_fund=tax_fund)

            w_cap = [False]                      # F: workers liquidity-constrained this year
            if behavioural:
                breakdown = breakdown_beh

            # within-period demand: every term is LINEAR in Y, so two
            # evaluations determine intercept+slope and the fixed point is
            # exact (no silent non-convergence). Iteration kept as a guard.
            def demand(Yv: float) -> float:
                bb = breakdown(Yv)
                return (bb["C_w"] + bb["C_k"] + A_priv + bb["A_fund"]
                        + INV + G + X - p.m_imp * Yv)
            f0 = demand(0.0)
            slope = (demand(p.Y0) - f0) / p.Y0
            Y = f0 / (1.0 - slope) if abs(1.0 - slope) > 1e-12 else p.Y0
            if not (abs(demand(Y) - Y) <= 1e-8 * max(p.Y0, abs(Y))):
                Y = p.Y0
                for _ in range(500):
                    Y_new = demand(Y)
                    if abs(Y_new - Y) <= 1e-10 * p.Y0:
                        Y = Y_new
                        break
                    Y = Y_new
            b = breakdown(Y)
            dL, fin_regime, M_floor = 0.0, 0, 0.0
            if behavioural:
                # B2 pecking order. Regimes: 1 desired capex (borrow/repay as
                # needed), 2 loans at the cap and capex cut, 3 no capex and
                # inventories cut, 4 nothing left to cut. Each is LINEAR in Y,
                # so each is solved exactly; the first consistent regime holds.
                own_K_prev = max(K_prev - E_sf_prev - E_row_prev, 0.0) * Pk   # at current prices
                M_floor = liq_ratio * own_K_prev
                cap = self.debt_cap * own_K_prev
                # room for new borrowing; NEGATIVE = a required repayment of the
                # excess over the cap, at the rate loans mature
                headroom = (cap - L_prev if L_prev <= cap
                            else -self.deleverage_rate * (L_prev - cap))
                money_prev = M_w_prev + M_k_prev
                sh_w_fx = (M_w_prev / money_prev) if money_prev > 0 else 0.5

                def cash_before(Yv, bb):
                    # D3: owners no longer buy a share of the current account;
                    # they reinvest part of their income from equity abroad
                    return M_k_prev + bb["YD_k"] - bb["C_k"] - dA_kf

                def plan(Yv, regime):
                    bb = breakdown(Yv)
                    avail = cash_before(Yv, bb) + headroom - M_floor
                    if regime == 1:
                        return bb, A_desired, INV_d
                    if regime == 2:
                        return bb, avail - INV_d, INV_d
                    if regime == 3:
                        return bb, 0.0, avail
                    return bb, 0.0, 0.0

                def demand_r(Yv, regime):
                    bb, ip, iv = plan(Yv, regime)
                    return (bb["C_w"] + bb["C_k"] + ip + bb["A_fund"] + iv
                            + A_row + G + X - p.m_imp * Yv)

                tol_f = 1e-9 * max(p.Y0, 1.0)
                # C1 ceiling: real output <= max utilisation x full capacity
                y_cap = (a_idx[t] * scenario.ai_productivity.at(t, H)
                         * (K_trad_prev + K_ai_prev) / v_cap)
                Y_ceiling = P * u_max * y_cap
                for w_try in (False, True):
                    w_cap[0] = w_try
                    for fin_regime in (1, 2, 3, 4):
                        Y = _solve_linear(lambda v, r=fin_regime: demand_r(v, r), p.Y0)
                        capped = Y > Y_ceiling
                        if capped:
                            Y = Y_ceiling
                        b, A_priv, INV = plan(Y, fin_regime)
                        excess = (demand_r(Y, fin_regime) - Y) if capped else 0.0
                        if fin_regime == 1:
                            needed = M_floor - (cash_before(Y, b) - A_priv - INV)
                            if needed <= headroom + tol_f:
                                dL = max(-L_prev, needed)
                                break
                        elif fin_regime == 2:
                            if A_priv >= -tol_f:
                                dL = headroom
                                break
                        elif fin_regime == 3:
                            if INV >= -tol_f:
                                dL = headroom
                                break
                        else:
                            dL = headroom
                    # F: would the workers end the year overdrawn? then they are
                    # liquidity-constrained this year (solve again)
                    m_w_end = M_w_prev + b["YD_w"] - b["C_w"] + Lw_prev * (Y / Y_prev - 1.0)
                    if w_try or C_w_prev is None or lam >= 1.0 or m_w_end >= -tol_f:
                        break
                # D: an owner with no cash left stops reinvesting abroad and, if
                # need be, sells equity abroad rather than run an overdraft
                # (dA_kf is a financial use of cash: it does not move demand)
                m_end = cash_before(Y, b) - A_priv - INV + dL
                if m_end < M_floor - tol_f:
                    dA_kf = max(-A_kf_prev, dA_kf - (M_floor - m_end))
            if behavioural:
                u_d = ((Y + excess) / P) / y_cap if y_cap > 0 else u_0   # demand pressure
                gap_now = u_d / u_n - 1.0
            A = A_priv + b["A_fund"] + A_row        # total investment (incl. FDI)
            C = b["C_w"] + b["C_k"]
            M_imp = p.m_imp * Y + excess           # imports (+ excess demand met abroad)
            NX = X - M_imp                          # trade balance
            CA = NX + T_int                         # current account (incl. transfers)
            if behavioural:                         # D: + net primary income
                prim_net = (Y_kf + Y_sf + int_fx - (b["FP_row_net"] - cfc_row)
                            - (b["F_gross"] - b["levy"]) - bank_row)
                CA = NX + T_int + prim_net + b["pledge_in"]
            else:
                prim_net = 0.0
            # step F: existing loans stay a constant share of GDP (old loans are
            # repaid and new ones taken at the same pace); the new lending is cash
            # to the borrower
            g_Y = (Y / Y_prev) if Y_prev else 1.0
            dLw, dLc_g, dLhk = (Lw_prev * (g_Y - 1.0), Lc_prev * (g_Y - 1.0),
                                Lhk_prev * (g_Y - 1.0))
            Y_prev = Y

            # sectoral net financial saving (NAFA). The fund holds no money: its
            # profit share equals the dividend it pays, so it nets to zero.
            nafa_w = b["YD_w"] - b["C_w"]
            nafa_k = b["YD_k"] - b["C_k"] - A_priv - INV
            dH_s = (G + b["ubi_pool"] + interest) - (b["tax_w"] + b["tax_k"] + b["tax_k_base"])  # gov money issued (incl. debt interest)
            if behavioural:
                if not banks:
                    dH_s += dL - int_L - fund_service   # the public lender issues money to lend
                dH_s += b["levy_fund"] - b["levy"] - (0.0 if fx_bank else int_fx)
                dH_s += seed - b["ai_gov"] - tax_bank          # E2: fund seed, AI-stake surplus

            # current account accrues as net foreign assets, split by money wealth
            tot_money = M_w_prev + M_k_prev
            sh_w = (M_w_prev / tot_money) if tot_money > 0 else 0.5
            dfx_w = CA * sh_w
            dfx_k = CA * (1.0 - sh_w)
            dA_sff = dFX_s = 0.0
            if behavioural:      # D3: no household holds the external position
                dfx_w = dfx_k = 0.0
            dM_w = nafa_w - dfx_w
            dM_k = nafa_k - dfx_k
            if behavioural:
                dM_k += dL - dA_kf + dLc_g + dLhk
                dM_w += dLw
                L = L_prev + dL
                # the public stand-in holds the net external position: the
                # current account plus FDI inflows less purchases of equity abroad
                dA_sff = fund_abroad + b["levy_fund"] + seed
                dFX_s = CA + (A_row - cfc_row) - dA_kf - dA_sff
                if not fx_bank:
                    dH_s += dFX_s           # the public stand-in buys the position
                FX_s = FX_s_prev + dFX_s
                A_kf = A_kf_prev + dA_kf
                A_sff = A_sff_prev + dA_sff
            if banks:
                B = B_prev + dH_s           # bonds issued to cover the deficit

            M_w = M_w_prev + dM_w
            M_k = M_k_prev + dM_k
            F_w = F_w_prev + dfx_w
            F_k = F_k_prev + dfx_k
            # capital deepening with depreciation, split into traditional vs AI.
            # Investment that keeps the baseline investment ratio maintains/grows
            # the traditional stock; the EXCESS (the AI-capex boom) builds AI
            # capital, which obsolesces fast (delta_ai). Both are real stocks.
            trad_target = p.a_ratio0 * Y          # baseline investment ratio of output
            ai_A = max(0.0, A - trad_target)
            if behavioural:
                # only the profit-driven (AI-boom) part builds fast-obsolescing AI
                # capital; capacity-driven and fund investment is traditional
                ai_A = min(A, (ai_desired * (A_priv / A_desired)
                               if A_desired > 0 else 0.0) + ai_row)
            trad_A = A - ai_A
            K_trad = K_trad_prev * (1.0 - p.delta) + trad_A / Pk     # real stocks
            K_ai = K_ai_prev * (1.0 - p.delta_ai) + ai_A / Pk
            K = K_trad + K_ai
            # UBC: convert an equal-valued claim (tau*FP) into the citizens'
            # endowment in kind each year; capped at full ownership of K. The
            # fund's stake depreciates at the capital-weighted blended rate.
            blended_delta = ((p.delta * K_trad_prev + p.delta_ai * K_ai_prev) / K_prev
                             if K_prev > 0 else p.delta)
            contrib = (tau * (1.0 - psi) * b["FP"]) if ubc_on else 0.0   # domestic profits only
            # behavioural: contrib is NET equity - the capital moves with its
            # share of the owners' debt (lev = owners' leverage). legacy: lev = 0.
            lev = (min((L_prev + Lc_prev) / (Pk * own_K_prev0), 0.95)
                   if (behavioural and ubc_on and own_K_prev0 > 0) else 0.0)
            E_pre = E_sf_prev * (1.0 - blended_delta) + b["A_fund"] / Pk
            if behavioural:      # D1: foreign owners' stake depreciates, grows with FDI
                E_row = E_row_prev * (1.0 - blended_delta) + A_row / Pk
            if behavioural:      # E1: the claim buys units of capital at market value
                units = contrib / (Pk * max(q - lev, 0.05))
            else:
                units = contrib / Pk / (1.0 - lev)
            E_sf = min(E_pre + units, K - E_row)          # real claim on capital
            d_tr = lev * Pk * max(0.0, E_sf - E_pre)       # debt assumed by the fund (nominal)
            if behavioural and ubc_on and K - E_sf - E_row <= 1e-12 * max(K, 1.0):
                d_tr = max(d_tr, L + Lc_prev + dLc_g)   # the last owned capital goes with all its debt
            if behavioural:
                # the debt moves pro rata from the owners' new and existing firm loans
                Lc_g = Lc_prev + dLc_g
                d_tr_c = d_tr * (Lc_g / (L + Lc_g)) if (L + Lc_g) > 0 else 0.0
                L -= d_tr - d_tr_c
                Lc = Lc_g - d_tr_c
                L_sf = L_sf_prev - rep_sf + d_tr
                Lw, Lhk = Lw_prev + dLw, Lhk_prev + dLhk
            owners_K = K - E_sf - E_row
            # owners' net profit share this year (drives next year's investment):
            # capital income after taxes and after equity/levy given up.
            own_share = 1.0 - phi - psi
            if behavioural:
                own_income = ((b["owners_profit"] - b["tax_kb_own"] - contrib) if ubc_on
                              else (b["own_fp"] - b["tax_k_own"] - b["tax_kb_own"]))
            elif ubc_on:
                own_income = b["owners_profit"] - b["tax_k_base"] - contrib
            else:
                own_income = b["FP"] - b["tax_k"] - b["tax_k_base"]
            pi_eff = (own_income / (own_share * Y)) if (own_share > 1e-9 and Y > 0) else -1.0
            if behavioural:
                pi_eff_prev = pi_eff
                C_w_prev, C_k_prev = b["C_w"], b["C_k"]     # F: the habit level

            tfm = {
                "wages":           {"hh_workers": b["WB"], "firms": -b["WB"]},
                "consumption":     {"firms": C, "hh_workers": -b["C_w"],
                                    "hh_owners": -b["C_k"]},
                "investment":      {"firms": A + INV,
                                    "hh_owners": -(A_priv + INV)},
                "gov_expenditure": {"firms": G, "government": -G},
                "exports":         {"firms": X, "rest_of_world": -X},
                "imports":         {"firms": -M_imp, "rest_of_world": M_imp},
                "tax_income":      {"government": b["tax_w"], "hh_workers": -b["tax_w"]},
                "money_chg":       {"hh_workers": -dM_w, "hh_owners": -dM_k,
                                    "government": dH_s},
                "fx_chg":          {"hh_workers": -dfx_w, "hh_owners": -dfx_k,
                                    "rest_of_world": dfx_w + dfx_k},
            }
            if interest and not banks:
                tfm["interest"] = {"hh_workers": int_w, "hh_owners": int_k,
                                   "government": -interest}
            if banks:      # the financial sector's rows
                tfm["money_chg"] = {"hh_workers": -dM_w, "hh_owners": -dM_k,
                                    "banks": dM_w + dM_k}
                tfm["bonds_chg"] = {"government": dH_s, "banks": -dH_s}
                if int_w or int_k:
                    tfm["interest"] = {"hh_workers": int_w, "hh_owners": int_k,
                                       "banks": -(int_w + int_k)}
                if interest:
                    tfm["gov_interest"] = {"government": -interest, "banks": interest}
                if pi_b:
                    tfm["bank_profits"] = {"banks": -pi_b, "government": tax_bank,
                                           "hh_owners": bank_own, "rest_of_world": bank_row}
            if b["tax_k_base"]:
                tfm["tax_capital_base"] = {"government": b["tax_k_base"],
                                           "hh_owners": -b["tax_k_base"]}
            if T_int:
                tfm["transfer_intl"] = {"hh_workers": tr_w, "hh_owners": tr_k,
                                        "rest_of_world": -T_int}
            if ubc_on:
                # profits split between diluted owners and the citizens' fund
                tfm["profits"] = {"hh_owners": b["owners_profit"],
                                  "sovereign_fund": b["gross_fund"],
                                  "firms": -b["FP"]}
                tfm["dividend_swf"] = {"hh_workers": b["div_w"],
                                       "hh_owners": b["div_k"],
                                       "sovereign_fund": -b["div_total"]}
                if b["A_fund"]:
                    tfm["investment"]["sovereign_fund"] = -b["A_fund"]
            else:
                tfm["profits"] = {"hh_owners": b["FP"], "firms": -b["FP"]}
                if b["tax_k"]:
                    tfm["tax_capital"] = {"government": b["tax_k"],
                                          "hh_owners": -b["tax_k"]}
                if b["ubi_pool"]:
                    tfm["transfer_ubi"] = {"hh_workers": b["ubi_pool"] * f_w,
                                           "hh_owners": b["ubi_pool"] * f_k,
                                           "government": -b["ubi_pool"]}

            if behavioural:      # D: the external sector rows
                tfm["investment"] = {"firms": A + INV, "hh_owners": -(A_priv + INV)}
                if b["A_fund"]:
                    tfm["investment"]["sovereign_fund"] = -b["A_fund"]
                if A_row:
                    tfm["investment"]["rest_of_world"] = -A_row
                prof = {"firms": -b["FP_all"], "hh_owners": b["own_fp"]}
                if b["gross_fund"] or b["ai_inc"]:
                    prof["sovereign_fund"] = b["gross_fund"] + b["ai_inc"]
                if b["FP_row"]:
                    prof["rest_of_world"] = b["FP_row"]
                tfm["profits"] = prof
                tfm.pop("tax_capital", None)
                tfm.pop("tax_capital_base", None)
                if b["tax_k"]:
                    tfm["tax_capital"] = {"government": b["tax_k"], "hh_owners": -b["tax_k_own"],
                                          "rest_of_world": -(b["tax_k"] - b["tax_k_own"])}
                if b["tax_k_base"]:
                    tfm["tax_capital_base"] = {"government": b["tax_k_base"],
                                               "hh_owners": -b["tax_kb_own"],
                                               "rest_of_world": -(b["tax_k_base"] - b["tax_kb_own"]
                                                                  - b["tax_fund"])}
                    if b["tax_fund"]:
                        tfm["tax_capital_base"]["sovereign_fund"] = -b["tax_fund"]
                if b["F_gross"]:
                    tfm["ai_licence_fees"] = {"firms": -b["F_gross"], "rest_of_world": b["F_gross"]}
                if b["levy"]:
                    tfm["tax_source_levy"] = {"rest_of_world": -b["levy"], "government": b["levy"]}
                if b["levy_fund"]:
                    tfm["transfer_levy_fund"] = {"government": -b["levy_fund"],
                                                 "sovereign_fund": b["levy_fund"]}
                if Y_kf or Y_sf:
                    tfm["equity_income_abroad"] = {"hh_owners": Y_kf,
                                                   "rest_of_world": -(Y_kf + Y_sf)}
                    if Y_sf:
                        tfm["equity_income_abroad"]["sovereign_fund"] = Y_sf
                if int_fx:
                    tfm["fx_interest"] = {("banks" if fx_bank else "government"): int_fx, "rest_of_world": -int_fx}
                if b["div_total"]:
                    tfm["dividend_swf"] = {"hh_workers": b["div_w"], "hh_owners": b["div_k"],
                                           "sovereign_fund": -b["div_total"]}
                if b["ai_gov"]:
                    tfm["fund_to_budget"] = {"sovereign_fund": -b["ai_gov"],
                                             "government": b["ai_gov"]}
                if seed:
                    tfm["transfer_fund_seed"] = {"government": -seed, "sovereign_fund": seed}
                if b["pledge_in"]:
                    tfm["pledge_transfers"] = {"hh_workers": b["pledge_in"] * f_w,
                                               "hh_owners": b["pledge_in"] * f_k,
                                               "rest_of_world": -b["pledge_in"]}
                if b["ubi_pool"]:
                    tfm["transfer_ubi"] = {"hh_workers": b["ubi_pool"] * f_w,
                                           "hh_owners": b["ubi_pool"] * f_k,
                                           "government": -b["ubi_pool"]}
                tfm["tax_income"] = {"government": b["tax_w"], "hh_workers": -b["tax_w"]}
                if dA_kf or dA_sff:
                    tfm["foreign_equity_chg"] = {"hh_owners": -dA_kf,
                                                 "rest_of_world": dA_kf + dA_sff}
                    if dA_sff:
                        tfm["foreign_equity_chg"]["sovereign_fund"] = -dA_sff
                tfm["fx_chg"] = {("banks" if fx_bank else "government"): -dFX_s, "rest_of_world": dFX_s}
                tfm["loans_chg"] = {"hh_owners": dL - d_tr + dLc_g + dLhk,
                                    ("banks" if banks else "government"):
                                        -(dL - rep_sf) - dLc_g - dLhk - dLw}
                if Lw or Lw_prev:
                    tfm["loans_chg"]["hh_workers"] = dLw
                if L_sf_prev or d_tr:
                    tfm["loans_chg"]["sovereign_fund"] = d_tr - rep_sf
                if d_tr:
                    tfm["debt_assumption"] = {"hh_owners": d_tr, "sovereign_fund": -d_tr}
                if int_L or int_sf or int_Lw or int_Lk:
                    tfm["loan_interest"] = {"hh_owners": -(int_L + int_Lk),
                                            ("banks" if banks else "government"):
                                                int_L + int_sf + int_Lw + int_Lk}
                    if int_Lw:
                        tfm["loan_interest"]["hh_workers"] = -int_Lw
                    if int_sf:
                        tfm["loan_interest"]["sovereign_fund"] = -int_sf

            bsm = {
                "money": {"hh_workers": M_w, "hh_owners": M_k,
                          "government": -(M_w + M_k)},
                "fx_assets": {"hh_workers": F_w, "hh_owners": F_k,
                              "rest_of_world": -(F_w + F_k)},
                "capital": ({"hh_owners": Pk * owners_K, "sovereign_fund": Pk * E_sf}
                            if E_sf > 0 else {"hh_owners": Pk * K}),   # at current prices
            }

            if behavioural:
                bsm["fx_assets"] = {("banks" if fx_bank else "government"): FX_s,
                                    "rest_of_world": -FX_s}
                fe = {"hh_owners": A_kf, "rest_of_world": -(A_kf + A_sff)}
                if A_sff or A_sff_prev:
                    fe["sovereign_fund"] = A_sff
                bsm["foreign_equity"] = fe
                capr = {"hh_owners": Pk * owners_K}
                if E_sf > 0:
                    capr["sovereign_fund"] = Pk * E_sf
                if E_row > 0:
                    capr["rest_of_world"] = Pk * E_row
                bsm["capital"] = capr
                bsm["loans"] = {"hh_owners": -(L + Lc + Lhk),
                                ("banks" if banks else "government"): L + L_sf + Lc + Lhk + Lw}
                if Lw or Lw_prev:
                    bsm["loans"]["hh_workers"] = -Lw
                if Lw or Lhk:      # dwellings at the household loans' face value
                    bsm["housing"] = {"hh_workers": Lw, "hh_owners": Lhk}
                if L_sf or L_sf_prev:
                    bsm["loans"]["sovereign_fund"] = -L_sf
            if banks:      # deposits are the financial sector's liability; it holds the bonds
                bsm["money"] = {"hh_workers": M_w, "hh_owners": M_k, "banks": -(M_w + M_k)}
                bsm["bonds"] = {"banks": B, "government": -B}
            gov_money = M_w + M_k
            gov_debt = gov_money - L - L_sf   # net of the public lender's loans (0 in legacy)
            nfa = F_w + F_k
            if behavioural:      # D: fiscal debt excludes the stand-in's external position
                gov_debt -= (FX_s - FX_s0)
                nfa = FX_s + A_kf + A_sff - Pk * E_row          # NIIP (equity at book value)
            if banks:            # Banks step: the government's debt is its bonds
                gov_debt = B - (0.0 if fx_bank else (FX_s - FX_s0))
                gov_debt_rep = gov_debt
            interest_gdp = 100.0 * interest / Y if Y else 0.0
            pop = p.population or 1.0
            reported = {
                "gdp": Y, "consumption": C, "consumption_workers": b["C_w"],
                "consumption_owners": b["C_k"], "investment": A,
                "gov_expenditure": G, "exports": X, "imports": M_imp,
                "net_exports": NX, "current_account": CA,
                "inventories": INV, "intl_transfer": T_int,
                "wage_bill": b["WB"], "profits": b["FP"], "labour_share": ls * 100.0,
                "money_workers": M_w, "money_owners": M_k, "gov_debt": gov_debt,
                "gov_debt_gdp": 100.0 * gov_debt / Y if Y else 0.0,
                "net_foreign_assets": nfa, "nfa_gdp": 100.0 * nfa / Y if Y else 0.0,
                "gov_interest": interest, "gov_interest_gdp": interest_gdp,
                "capital": K, "capital_traditional": K_trad,
                "capital_ai": K_ai,
                "capital_ai_share": (K_ai / K if K else 0.0),
                "gini": _two_class_gini(b["YD_w"], b["YD_k"], f_w),
                "ubi": b["ubi_pool"], "transfer_pool": b["transfer_pool"],
                "deficit": dH_s,
                "net_wages": b["WB"] - b["tax_w"], "net_profits": b["net_profits"],
                "hh_disposable": b["YD_w"] + b["YD_k"],
                "swf_stake": E_sf, "swf_share": (E_sf / K if K else 0.0),
                "swf_dividend": b["div_total"],
                "swf_dividend_pc": b["div_total"] / pop,
                "owners_capital": owners_K,
                "owners_capital_share": (owners_K / K if K else 0.0),
                "citizen_wealth_pc": (Pk * E_sf - L_sf) / Pk / pop,   # real (2019 prices)
                "inv_response": inv_mult,
                "swf_reinvest": b["A_fund"], "investment_private": A_priv,
                "reinvest_rate": reinvest,
                "income_workers_pc": b["YD_w"] / (f_w * p.population)
                if p.population else b["YD_w"] / f_w,
                "income_owners_pc": b["YD_k"] / (f_k * p.population)
                if p.population else b["YD_k"] / f_k,
                "gov_money": gov_money,
                "gov_money_gdp": 100.0 * gov_money / Y if Y else 0.0,
                "loans_owners": L, "loans_owners_gdp": 100.0 * L / Y if Y else 0.0,
                "owners_borrowing": dL, "loan_interest": int_L + int_sf,
                "loans_fund": L_sf, "fund_debt_service": fund_service,
                "debt_assumed_by_fund": d_tr, "swf_net_assets": Pk * E_sf - L_sf,
                "gdp_real": Y / Pk, "price_level": P, "inflation": infl,
                "investment_desired": A_desired,
                "investment_cut": A_desired - A_priv,
                "financing_regime": fin_regime,
                "owners_liquidity_floor": M_floor,
                "owners_net_profit_share": pi_eff,
            }
            if behavioural:
                reported.update({"capacity": y_cap,
                                 "utilisation": ((Y / P) / y_cap) if y_cap > 0 else 0.0,
                                 "output_gap": gap_now, "excess_imports": excess})
                dom_ai = max(0.0, b["R"] - b["F_gross"])          # AI rent kept at home
                claim = (phi if ubc_on else tau) + t_b          # the public claim on the rest
                reached = (b["levy"] + b["ai_inc"] + claim * (dom_ai - b["ai_inc"])
                           + b["pledge_in"])
                gni = Y + prim_net
                reported.update({
                    "deficit": dH_s - (0.0 if fx_bank else dFX_s),
                    "gni": gni, "gni_real": gni / Pk, "primary_income_net": prim_net,
                    "ai_rent": b["R"], "ai_rent_abroad": b["F_gross"] - b["levy"],
                    "ai_rent_levy": b["levy"], "ai_rent_reached": reached,
                    "ai_rent_reached_share": (reached / b["R"]) if b["R"] > 0 else 0.0,
                    # the bite on the FOREIGN part: only the levy share providers absorb
                    "ai_rent_foreign_reached_share": (
                        (((1.0 - self.levy_pass_through) * b["levy"] + b["pledge_in"])
                         / (self.ai_foreign_share * b["R"]))
                        if self.ai_foreign_share * b["R"] > 0 else 0.0),
                    "foreign_profits": b["FP_row_net"] - cfc_row,     # net, as in the BoP
                    "fdi_net_inflow": A_row - cfc_row,
                    "foreign_capital_share": (E_row / K) if K else 0.0,
                    "fdi_investment": A_row,
                    "owners_foreign_equity": A_kf, "owners_foreign_income": Y_kf,
                    "fund_foreign_equity": A_sff, "fund_foreign_income": Y_sf,
                    "public_external_position": FX_s,
                    "niip": nfa, "niip_gdp": 100.0 * nfa / Y if Y else 0.0,
                    # E: owners' capital income BEFORE capital taxes and levies
                    # (drives MARKET inequality in the distribution layer)
                    "capital_income_hh_gross": b["own_fp"] + Y_kf + (1.0 - psi) * pi_b,
                    "tax_rate_labour": theta_w, "tax_rate_capital": theta_k,
                    "swf_net_assets": Pk * E_sf - L_sf + A_sff,
                    # E1: what the fund's holdings are worth at market prices
                    "swf_market_value": (Pk * q * E_sf - L_sf + A_sff
                                         + b["ai_inc"] / self.r_world), "equity_q": q,
                    "citizen_wealth_pc": ((Pk * q * E_sf - L_sf + A_sff
                                           + b["ai_inc"] / self.r_world) / Pk / pop),
                    "fund_seed": seed, "ai_stake_income": b["ai_inc"],
                    "ai_stake_to_budget": b["ai_gov"], "pledge_distributions": b["pledge_in"],
                    "broad_tax_rate": t_b,
                })
                if banks:
                    reported.update({
                        "policy_rate": i_p, "gov_rate_avg": i_g, "gov_rate_new": i_new,
                        "deposit_rate": r_dep, "household_rate": r_h, "loan_rate": r_l,
                        "fx_rate": r_fx, "bank_profits": pi_b, "bank_profits_abroad": bank_row,
                        "bank_tax": tax_bank, "gov_bonds": B, "deposits": M_w + M_k,
                        "bank_net_worth": (B + L + L_sf + Lc + Lhk + Lw
                                           + (FX_s if fx_bank else 0.0) - (M_w + M_k)),
                        "loans_firms_existing": Lc, "loans_households": Lw + Lhk,
                        "loans_households_workers": Lw,
                        "existing_loan_interest": int_Lw + int_Lk,
                    })
                pi_row_prev = (b["FP_row_net"] / (psi * Y)) if (psi > 0 and Y > 0) else pi0
                # E1: after-tax net profit rate on capital, for next year's q
                rprof_prev = ((b["FP"] * (1.0 - theta_k) - blended_delta * Pk * K_prev)
                              / (Pk * K_prev)) if K_prev > 0 else 0.0
                if rprof0 is None:
                    rprof0 = max(rprof_prev, 0.01)
                fpd_share_prev = (b["FP"] / Y) if Y > 0 else fpd_share_prev
                gap_prev, P_prev = gap_now, P
                ls_prev = ls
            periods.append(PeriodState(year=p.base_year + t, tfm=tfm, bsm=bsm,
                                       reported=reported))

        return RunResult(
            module=self.name, scenario=scenario.name, geo=scenario.geo,
            periods=periods,
            meta={
                "stock_flow_map": (({"money": "money_chg", "fx_assets": "fx_chg",
                                     "loans": "loans_chg",
                                     "foreign_equity": "foreign_equity_chg"}
                                    | ({"bonds": "bonds_chg"} if banks else {}))
                                   if behavioural
                                   else {"money": "money_chg", "fx_assets": "fx_chg"}),
                "investment_closure": self.investment_closure,
                "profit_response": gamma, "debt_cap": self.debt_cap,
                "loan_rate": (loan_fixed if loan_fixed is not None else "market"),
                "liquidity_floor": self.liquidity_floor,
                "banks": banks, "rates": rc, "ecb_reference": ea_ref,
                "fx_holder": ("banks" if fx_bank else ("government" if behavioural else None)),
                "deleverage_rate": self.deleverage_rate,
                "inflation_target": self.inflation_target,
                "phillips_slope": self.phillips_slope,
                "export_elasticity": self.export_elasticity,
                "utilisation_response": self.utilisation_response,
                "policy_start": self.policy_start,
                "capacity_utilisation": cu if behavioural else None,
                "baseline_tfp_growth": (None if not behavioural else
                                        (a_idx[1] - 1.0 if (tp and H > 1) else g_tfp)),
                "trend": ({"flag": tp["flag"], "source": tp["source"], "growth": tp["growth"],
                           "capacity_efficiency": a_idx} if tp else None),
                "private_loans": legacy,
                "consumption_adjustment": lam if behavioural else None,
                "impact_mpc": self.impact_mpc if behavioural else None,
                "fiscal_reaction": fiscal_reaction, "debt_target": debt_target,
                "i_rate": i_rate_eff, "capital_tax_share": ck.get("capital_tax_share"),
                "g_nominal": ck.get("g_nominal"),
                "observed_primary_balance": (fiscal_position_for(
                    scenario.geo, base_year=self.base_year)["primary_balance"]
                                             if behavioural else None),
                "external": ext if behavioural else None,
                "foreign_stake0": psi0, "ai_foreign_share": self.ai_foreign_share,
                "levy_pass_through": self.levy_pass_through, "r_world": self.r_world,
                "owners_mpc": a1_k, "workers_mpc": a1_w, "fx_stand_in0": FX_s0,
                "consumption_differential": (cd["value"] if cd else None),
                "consumption_differential_flag": (cd["flag"] if cd else None),
                "consumption_differential_source": (cd["source"] if cd else None),
                "equity_valuation": self.equity_valuation if behavioural else "book",
                "params": p.as_dict(), "targets": p.targets,
                "sources": p.sources, "notes": p.notes, "nx_gap": p.nx_gap,
            },
        )


# --------------------------------------------------------------------------- #
# Banks step: the euro-area reference - the euro-area aggregate run under the
# SAME AI scenario with no national policy. Its debt path nets the common
# shock out of each country's risk premium (the estimate is a spread over the
# euro area); under policy_rule="taylor" its rule also gives the ECB path.
# --------------------------------------------------------------------------- #
def expected_gov_rate(geo, i_g0: float, neutral: float = NEUTRAL_RATE,
                      horizon: int = 30, base_year: int = 2019) -> float:
    """Average rate on public debt over the standard 30-year horizon with no risk
    premium: the 2015-19 rate rolling over (1/DEBT_MATURITY a year) into the
    policy path (2019 level to neutral) + the country's spread. The structural
    primary balance is set at it (Banks step)."""
    rc = rates_for(geo, base_year=base_year)
    own = (geo or "").upper() == EURO_AREA or rc["regime"] == "own"
    path = _neutral_path(rc["policy0"] if own else rc["ea_policy0"], neutral, horizon)
    peg = 0.0 if own else rc["policy0"] - rc["ea_policy0"]
    i_g, acc = float(i_g0), []
    for t in range(1, horizon):
        i_g += (path[t] + peg + rc["gov_spread"] - i_g) / DEBT_MATURITY
        acc.append(i_g)
    return sum(acc) / len(acc) if acc else float(i_g0)


def _neutral_path(i0: float, neutral: float, H: int) -> List[float]:
    """Policy rate from its 2019 level to neutral, closing 1 - RATE_SMOOTHING of
    the gap a year (~92% in five years); no reaction to booms or slumps."""
    return [neutral + (i0 - neutral) * RATE_SMOOTHING ** t for t in range(H)]


_ECB_CACHE: Dict[tuple, List[float]] = {}
_ECB_CACHE_MAX = 512


def _euro_reference(core: "SFCCore", scenario: Scenario, H: int) -> Dict[str, object]:
    from modules.ai_shock import AIShock, Policy, to_scenario
    from data.connectors.dbnomics import DBnomicsConnector
    ai = getattr(scenario, "ai_shock", None)
    label = "euro area under the scenario's AI shock" if ai is not None else \
        "euro area baseline (the scenario carries no AI shock)"
    if ai is None:
        ai = AIShock("Baseline", labour_share_end=None)
    kw = dict(core._init_kwargs)
    kw.update(policy_rate_path=None, consumption_differential=None, capacity=None,
              external=None, own_rate_path=None, gov_rate_path=None, euro_debt_path=None,
              tax_scale_path=None, labour_tax_shift_path=None, capital_tax_shift_path=None)
    key = (repr(ai), H, core.base_year,
           tuple(sorted((k, repr(v)) for k, v in kw.items())))
    if key not in _ECB_CACHE:
        rows = DBnomicsConnector(allow_live=False).fetch(EURO_AREA, core.base_year)
        data = {c: r["value"] for c, r in rows.items()}
        data["_sources"] = {c: r["source"] for c, r in rows.items()}
        ref = SFCCore(**kw)
        p_ea, _ = ref._calibrate(EURO_AREA, data)
        scen = to_scenario(p_ea, ai, Policy("none"), name="euro-area reference",
                           horizon=H, geo=EURO_AREA)
        res = ref.run(scen, data)
        if len(_ECB_CACHE) >= _ECB_CACHE_MAX:
            _ECB_CACHE.clear()
        _ECB_CACHE[key] = {
            "policy": [per.reported["policy_rate"] for per in res.periods],
            "debt_ratio": [per.reported["gov_debt"] / per.reported["gdp"]
                           for per in res.periods],
            "label": label}
    out = dict(_ECB_CACHE[key])
    return {"policy": list(out["policy"]), "debt_ratio": list(out["debt_ratio"]),
            "label": out["label"]}
