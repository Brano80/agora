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

Emits a complete transaction-flow matrix (columns balance) + balance-sheet
matrix so the consistency gate validates money AND fx to machine precision.
TFM convention: tfm[flow][sector] is the signed cash-budget contribution
(inflow +, outflow -); stock-driving rows carry -(Δstock) so columns sum to 0.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from modules.interface import Module, Scenario, RunResult, PeriodState
from calibration import calibrate, SFCParams


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
                 inv_elasticity: float = 0.0):
        self.base_year = base_year
        self.calib_kwargs = calib_kwargs or {}
        # C1 (enclosure-vs-diffusion): elasticity of investment to owners'
        # RETAINED capital-income share. 0.0 = autonomous capex (Phase 1-3
        # behaviour); >0 = socialising owners' returns (cash tax OR UBC
        # dilution) deters capex. An inspectable, swappable ASSUMPTION.
        self.inv_elasticity = float(inv_elasticity)
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
        ]

    def run(self, scenario: Scenario, data: Dict[str, float],
            context: Optional[dict] = None) -> RunResult:
        p = calibrate(data, geo=scenario.geo, base_year=self.base_year,
                      sources=data.get("_sources", {}) if isinstance(data, dict) else {},
                      **self.calib_kwargs)
        self.params = p
        H = scenario.horizon
        f_w, f_k = p.f_workers, 1.0 - p.f_workers

        M_w, M_k, K = p.M_w0, p.M_k0, p.K0
        K_trad, K_ai = p.K0, 0.0      # AI capital starts ~0 and is built by the boom
        F_w, F_k = 0.0, 0.0           # net foreign assets start at 0 (accumulate CA)
        E_sf = 0.0                    # sovereign-fund capital stake (UBC); 0 = no fund
        Y_prev = p.Y0
        periods: List[PeriodState] = []

        for t in range(H):
            ls = scenario.labour_share.at(t, H)
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
                 else p.export_ratio * p.Y0 * (1.0 + p.world_growth) ** t)
            tau = scenario.tax_capital.at(t, H)
            ubi_on = scenario.ubi_on.at(t, H) >= 0.5
            ubc_on = scenario.ubc_on.at(t, H) >= 0.5
            theta = p.theta

            M_w_prev, M_k_prev, K_prev = M_w, M_k, K
            K_trad_prev, K_ai_prev = K_trad, K_ai
            F_w_prev, F_k_prev, E_sf_prev = F_w, F_k, E_sf

            # fund's ownership share entering the period drives this year's dividend
            phi = (min(E_sf_prev / K_prev, 1.0)
                   if (ubc_on and K_prev > 0) else 0.0)

            # C1 investment feedback: owners fund capex and respond to the
            # share of capital income they still RETAIN. Cash tax and UBC
            # both extract tau*FP/yr, but UBC keeps socialising the STOCK, so
            # its signal (1-phi) keeps falling while the cash signal (1-tau)
            # is flat - the sharp test of whether predistribution chokes capex.
            inv_signal = (1.0 - phi) if ubc_on else (1.0 - tau)
            inv_mult = inv_signal ** self.inv_elasticity   # applied capex multiplier
            A_priv = base_A * inv_mult                      # privately-financed capex
            reinvest = scenario.ubc_reinvest.at(t, H) if ubc_on else 0.0
            # interest on government debt (gov money held by households),
            # predetermined from last period's debt; paid out by money share.
            gov_debt_prev = M_w_prev + M_k_prev
            sh_w_m = (M_w_prev / gov_debt_prev) if gov_debt_prev > 0 else 0.5
            interest = p.i_rate * gov_debt_prev
            int_w, int_k = interest * sh_w_m, interest * (1.0 - sh_w_m)
            # inventories+valuables (P52+P53): constant autonomous, owner-
            # financed, NOT added to productive K (closes the identity).
            INV = p.inv0
            # cross-border secondary income (pooled global dividend), per capita
            T_int = (scenario.intl_transfer.at(t, H)
                     if scenario.intl_transfer is not None else 0.0)
            tr_w, tr_k = T_int * f_w, T_int * f_k

            def breakdown(Y: float):
                WB = ls * Y
                FP = (1.0 - ls) * Y
                tax_w = theta * WB
                if ubc_on:
                    # capital income socialised in kind: fund owns phi of it.
                    # The fund REINVESTS a fraction and pays out the rest, so as
                    # owners are diluted the fund sustains capex (resolves C1).
                    gross_fund = phi * FP
                    A_fund = reinvest * gross_fund         # fund-financed capex
                    div_total = gross_fund - A_fund        # paid out per capita
                    owners_profit = (1.0 - phi) * FP
                    tax_k = 0.0                      # no cash levy; dilution instead
                    ubi_pool = 0.0
                    transfer_pool = div_total
                    div_w, div_k = div_total * f_w, div_total * f_k
                    YD_w = WB - tax_w + div_w + int_w + tr_w
                    YD_k = owners_profit + div_k + int_k + tr_k
                    net_profits = owners_profit
                elif ubi_on:
                    tax_k = tau * FP
                    ubi_pool = tax_k
                    transfer_pool = ubi_pool
                    div_total = owners_profit = 0.0
                    div_w = div_k = 0.0
                    ubi_w, ubi_k = ubi_pool * f_w, ubi_pool * f_k
                    YD_w = WB - tax_w + ubi_w + int_w + tr_w
                    YD_k = FP - tax_k + ubi_k + int_k + tr_k
                    net_profits = FP - tax_k
                    gross_fund = A_fund = 0.0
                else:
                    tax_k = tau * FP
                    ubi_pool = transfer_pool = 0.0
                    div_total = owners_profit = 0.0
                    div_w = div_k = ubi_w = ubi_k = 0.0
                    YD_w = WB - tax_w + int_w + tr_w
                    YD_k = FP - tax_k + int_k + tr_k
                    net_profits = FP - tax_k
                    gross_fund = A_fund = 0.0
                C_w = p.a1_w * YD_w + p.a2 * (M_w_prev + F_w_prev)
                C_k = p.a1_k * YD_k + p.a2 * (M_k_prev + F_k_prev)
                return dict(WB=WB, FP=FP, tax_w=tax_w, tax_k=tax_k,
                            ubi_pool=ubi_pool, transfer_pool=transfer_pool,
                            div_total=div_total, div_w=div_w, div_k=div_k,
                            owners_profit=owners_profit, net_profits=net_profits,
                            gross_fund=gross_fund, A_fund=A_fund,
                            YD_w=YD_w, YD_k=YD_k, C_w=C_w, C_k=C_k)

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
            A = A_priv + b["A_fund"]                # total investment
            C = b["C_w"] + b["C_k"]
            M_imp = p.m_imp * Y                    # imports
            NX = X - M_imp                          # trade balance
            CA = NX + T_int                         # current account (incl. transfers)
            Y_prev = Y

            # sectoral net financial saving (NAFA). The fund holds no money: its
            # profit share equals the dividend it pays, so it nets to zero.
            nafa_w = b["YD_w"] - b["C_w"]
            nafa_k = b["YD_k"] - b["C_k"] - A_priv - INV
            dH_s = (G + b["ubi_pool"] + interest) - (b["tax_w"] + b["tax_k"])  # gov money issued (incl. debt interest)

            # current account accrues as net foreign assets, split by money wealth
            tot_money = M_w_prev + M_k_prev
            sh_w = (M_w_prev / tot_money) if tot_money > 0 else 0.5
            dfx_w = CA * sh_w
            dfx_k = CA * (1.0 - sh_w)
            dM_w = nafa_w - dfx_w
            dM_k = nafa_k - dfx_k

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
            trad_A = A - ai_A
            K_trad = K_trad_prev * (1.0 - p.delta) + trad_A
            K_ai = K_ai_prev * (1.0 - p.delta_ai) + ai_A
            K = K_trad + K_ai
            # UBC: convert an equal-valued claim (tau*FP) into the citizens'
            # endowment in kind each year; capped at full ownership of K. The
            # fund's stake depreciates at the capital-weighted blended rate.
            blended_delta = ((p.delta * K_trad_prev + p.delta_ai * K_ai_prev) / K_prev
                             if K_prev > 0 else p.delta)
            contrib = (tau * b["FP"]) if ubc_on else 0.0
            E_sf = min(E_sf_prev * (1.0 - blended_delta) + contrib + b["A_fund"], K)
            owners_K = K - E_sf

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
            if interest:
                tfm["interest"] = {"hh_workers": int_w, "hh_owners": int_k,
                                   "government": -interest}
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
                if b["A_fund"] > 0:
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

            bsm = {
                "money": {"hh_workers": M_w, "hh_owners": M_k,
                          "government": -(M_w + M_k)},
                "fx_assets": {"hh_workers": F_w, "hh_owners": F_k,
                              "rest_of_world": -(F_w + F_k)},
                "capital": ({"hh_owners": owners_K, "sovereign_fund": E_sf}
                            if E_sf > 0 else {"hh_owners": K}),
            }

            gov_debt = M_w + M_k
            nfa = F_w + F_k
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
                "citizen_wealth_pc": E_sf / pop, "inv_response": inv_mult,
                "swf_reinvest": b["A_fund"], "investment_private": A_priv,
                "reinvest_rate": reinvest,
                "income_workers_pc": b["YD_w"] / (f_w * p.population)
                if p.population else b["YD_w"] / f_w,
                "income_owners_pc": b["YD_k"] / (f_k * p.population)
                if p.population else b["YD_k"] / f_k,
            }
            periods.append(PeriodState(year=p.base_year + t, tfm=tfm, bsm=bsm,
                                       reported=reported))

        return RunResult(
            module=self.name, scenario=scenario.name, geo=scenario.geo,
            periods=periods,
            meta={
                "stock_flow_map": {"money": "money_chg", "fx_assets": "fx_chg"},
                "params": p.as_dict(), "targets": p.targets,
                "sources": p.sources, "notes": p.notes, "nx_gap": p.nx_gap,
            },
        )
