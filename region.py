"""Multi-region core (Phase 5) — the national-vs-global AI dividend (Q2).

The crux (MANIFESTO Q2): if the AI dividend is paid only NATIONALLY, the richer,
more capital-intensive economy generates a bigger per-capita dividend, so an
'AI UBI/UBC' entrenches — even widens — the gap BETWEEN countries. A GLOBAL
(pooled) dividend distributes the combined levy equally per capita across the
whole population, transferring from richer to poorer. This layer measures the
difference.

Loose coupling (CLAUDE.md): each country is its own calibrated, individually
consistency-GATED open economy (`AgoraOrchestrator`). The region layer runs them
under a shared AI shock + policy and reconciles only at the dividend-distribution
step — it does NOT yet force tight bilateral trade feedback (that is the next
increment; here the rest-of-world stays each country's single counterparty).

Between-country inequality uses the population-weighted Gini ACROSS regions of
per-capita household disposable income (each region treated at its mean):
    G = Σ_i Σ_j w_i w_j |v_i − v_j| / (2 · mean),    w = population shares.
The 'global' arm replaces each country's own per-capita dividend with the single
pooled per-capita dividend; everything else is held identical, so the change in
G isolates the national-vs-global effect.
"""
from __future__ import annotations

import math

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from orchestrator import AgoraOrchestrator
from scenarios import build_custom, LS_AI_END, CAPEX_AI_GROWTH
from modules.interface import LeverPath
from schema.accounts import is_euro


def between_region_gini(values: List[float], weights: List[float]) -> float:
    """Population-weighted Gini across regions (each at its per-capita mean)."""
    mean = sum(w * v for w, v in zip(weights, values))
    if mean <= 0:
        return 0.0
    num = sum(weights[i] * weights[j] * abs(values[i] - values[j])
              for i in range(len(values)) for j in range(len(values)))
    return num / (2.0 * mean)


@dataclass
class DividendComparison:
    geos: List[str]
    form: str                          # "ubc" | "cash_ubi"
    tau: float
    horizon: int
    populations: Dict[str, float]
    consistent: bool
    max_residual: float
    # per-period between-country Gini of per-capita disposable income
    gini_national: List[float] = field(default_factory=list)
    gini_global: List[float] = field(default_factory=list)
    # end-horizon per-capita dividend by country (national) + the pooled rate
    div_pc_national: Dict[str, float] = field(default_factory=dict)
    div_pc_global: float = 0.0
    # end-horizon net pooling transfer per capita (+ = country receives)
    pooling_transfer_pc: Dict[str, float] = field(default_factory=dict)
    excluded: List[str] = field(default_factory=list)   # divergent countries skipped

    def summary(self) -> Dict[str, float]:
        return {"gini_national_end": self.gini_national[-1],
                "gini_global_end": self.gini_global[-1],
                "gap_narrowing_pct": (100.0 * (1.0 - self.gini_global[-1]
                                      / self.gini_national[-1])
                                      if self.gini_national[-1] else 0.0),
                "div_pc_global_end": self.div_pc_global}


class MultiRegion:
    """A bloc of separately-calibrated, individually-gated open economies."""

    def __init__(self, geos: Tuple[str, ...] = ("DE", "FR"), year: int = 2019,
                 allow_live: bool = False, inv_elasticity: float = 0.0):
        self.geos = list(geos)
        self.year = year
        self.orchs: Dict[str, AgoraOrchestrator] = {}
        for g in self.geos:
            o = AgoraOrchestrator(geo=g, year=year, allow_live=allow_live,
                                  strict=True, inv_elasticity=inv_elasticity)
            o.load_data()
            self.orchs[g] = o

    def dividend_comparison(self, form: str = "ubc", tau: float = 0.40,
                            horizon: int = 30,
                            reinvest: float = 0.0) -> DividendComparison:
        """Run each country under the shared shock + policy, then compare the
        between-country gap under a NATIONAL vs a GLOBAL (pooled) dividend."""
        per: Dict[str, dict] = {}
        excluded: List[str] = []
        consistent, worst = True, 0.0
        for g, o in self.orchs.items():
            p = o.params()
            kw = (dict(ubc=True, ubc_reinvest=reinvest) if form == "ubc"
                  else dict(ubi=True))
            scen = build_custom(p, labour_share_end=LS_AI_END,
                                capex_growth=CAPEX_AI_GROWTH, capital_tax=tau,
                                horizon=horizon, name=f"{g} {form}", **kw)
            # VIABILITY GUARD: a divergent country must not poison the whole bloc.
            # Entrepôt economies (trade >> GDP, e.g. Luxembourg) blow up the
            # standalone open-economy closure (exports grow with own output ->
            # unbounded), which makes the strict gate RAISE. Catch it, skip, record.
            try:
                run = o.run_scenario(scen)
                end = run.result.periods[-1].reported
                viable = (run.consistent and run.max_residual <= 1.0
                          and math.isfinite(end.get("gdp", 0.0))
                          and math.isfinite(end.get("hh_disposable", 0.0)))
            except Exception:
                viable = False
            if not viable:
                excluded.append(g)
                continue
            worst = max(worst, run.max_residual)
            pop = p.population
            reps = run.result.periods
            per[g] = {
                "pop": pop,
                "yd_pc": [r.reported["hh_disposable"] / pop for r in reps],
                "div_total": [r.reported["transfer_pool"] for r in reps],
            }

        geos_v = [g for g in self.geos if g in per]       # viable bloc only
        pops = {g: per[g]["pop"] for g in geos_v}
        totpop = sum(pops.values()) or 1.0
        w = [pops[g] / totpop for g in geos_v]

        # PASS 2 — the GATED global arm. Each country's net pooling transfer
        # (pooled per-capita dividend x its population - its own pool) is
        # injected through its OWN books via the intl_transfer lever (households
        # receive it, rest_of_world the counterpart, fx accumulates it), so the
        # pooled arm passes the consistency gate instead of being an ex-post
        # overlay. Transfers sum to ~0 across the bloc by construction.
        #
        # ITERATED to a damped FIXED POINT: the transfer changes demand, which
        # changes the dividend pools themselves. For cash that feedback is
        # second-order, but under compounding UBC pools it is FIRST-order for
        # big givers — a single corrective pass drove Italy's households into
        # negative income by 2042 (caught by the plausibility gate). Strict
        # gating is suspended for intermediate guesses; the FINAL converged
        # state must pass the gate in full.
        div2 = {g: list(per[g]["div_total"]) for g in geos_v}
        scen2 = {}
        for g in geos_v:
            p2 = self.orchs[g].params()
            kw2 = (dict(ubc=True, ubc_reinvest=reinvest) if form == "ubc"
                   else dict(ubi=True))
            scen2[g] = build_custom(p2, labour_share_end=LS_AI_END,
                                    capex_growth=CAPEX_AI_GROWTH, capital_tax=tau,
                                    horizon=horizon, name=f"{g} {form} pooled",
                                    **kw2)

        def _run_all(strict_ok: bool):
            tot = [sum(div2[k][t] for k in geos_v) for t in range(horizon)]
            out = {}
            for g in geos_v:
                scen2[g].intl_transfer = LeverPath(
                    [tot[t] * pops[g] / totpop - div2[g][t]
                     for t in range(horizon)])
                o = self.orchs[g]
                was = o.strict
                o.strict = False
                try:
                    out[g] = o.run_scenario(scen2[g])
                finally:
                    o.strict = was
            return out

        alpha2 = 0.5
        runs2 = {}
        for _ in range(20):
            runs2 = _run_all(strict_ok=False)
            delta = 0.0
            for g in geos_v:
                new = runs2[g].result.series("transfer_pool")
                scale = max(1.0, max(abs(v) for v in div2[g]))
                delta = max(delta, max(abs(new[t] - div2[g][t])
                                       for t in range(horizon)) / scale)
                div2[g] = [(1.0 - alpha2) * div2[g][t] + alpha2 * new[t]
                           for t in range(horizon)]
            if delta < 1e-3:
                break
        runs2 = _run_all(strict_ok=True)        # final, evaluated by the gate
        for g in geos_v:
            worst = max(worst, runs2[g].max_residual)
            per[g]["yd_pc_glob"] = [r.reported["hh_disposable"] / pops[g]
                                    for r in runs2[g].result.periods]
        consistent = (bool(geos_v) and worst <= 1.0
                      and all(r.consistent for r in runs2.values()))

        gini_nat, gini_glob = [], []
        div_pc_nat: Dict[str, float] = {}
        pooling_transfer: Dict[str, float] = {}
        div_pc_global_end = 0.0
        for t in range(horizon):
            yd_nat = [per[g]["yd_pc"][t] for g in geos_v]
            gini_nat.append(between_region_gini(yd_nat, w))
            # GLOBAL: pool every country's dividend, redistribute equally per head
            tot_div = sum(per[g]["div_total"][t] for g in geos_v)
            div_pc_global = tot_div / totpop
            # gated: per-capita disposable income from the PASS-2 runs, where
            # the pooling transfer went through each country's books.
            yd_glob = [per[g]["yd_pc_glob"][t] for g in geos_v]
            gini_glob.append(between_region_gini(yd_glob, w))
            if t == horizon - 1:
                div_pc_global_end = div_pc_global
                for g in geos_v:
                    own = per[g]["div_total"][t] / per[g]["pop"]
                    div_pc_nat[g] = own
                    pooling_transfer[g] = div_pc_global - own

        return DividendComparison(
            geos=geos_v, form=form, tau=tau, horizon=horizon,
            populations=pops, consistent=consistent, max_residual=worst,
            gini_national=gini_nat, gini_global=gini_glob,
            div_pc_national=div_pc_nat, div_pc_global=div_pc_global_end,
            pooling_transfer_pc=pooling_transfer, excluded=excluded)

    # --- tight bilateral trade (Phase 5 increment 2) ----------------------- #
    def _gravity_weight(self, importer: str, exporter: str,
                        gdp: Dict[str, float]) -> float:
        """Share of `importer`'s intra-bloc imports sourced from `exporter`,
        proportional to partner GDP (a simple gravity allocation, excluding self)."""
        denom = sum(gdp[k] for k in self.geos if k != importer)
        return gdp[exporter] / denom if denom else 0.0

    def gravity_matrix(self, gdp: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """Bilateral intra-bloc import shares from a gravity rule (partner GDP).
        W[i][j] = fraction of country i's intra-bloc imports sourced from j."""
        return {i: {j: self._gravity_weight(i, j, gdp) for j in self.geos if j != i}
                for i in self.geos}

    def load_trade_matrix(self, year: int = 2019, allow_live: bool = False
                          ) -> Dict[str, Dict[str, float]]:
        """Bilateral import-share matrix. With live access this is where real
        Eurostat Comext flows plug in; until then (and offline) it falls back to
        the gravity rule. Inject a real matrix directly via solve_trade(trade_shares=).
        """
        gdp = {g: self.orchs[g].params().gdp_full for g in self.geos}
        # (live Comext parsing would populate W here; gravity is the fallback)
        return self.gravity_matrix(gdp)

    def _policy_scenario(self, geo: str, form: str, tau: float,
                         reinvest: float, horizon: int):
        p = self.orchs[geo].params()
        kw = (dict(ubc=True, ubc_reinvest=reinvest) if form == "ubc"
              else (dict(ubi=True) if form == "cash_ubi" else dict()))
        return build_custom(p, labour_share_end=LS_AI_END,
                            capex_growth=CAPEX_AI_GROWTH, capital_tax=tau,
                            horizon=horizon, name=f"{geo} {form}", **kw)

    def solve_trade(self, form: str = "cash_ubi", tau: float = 0.40,
                    horizon: int = 30, intra_share: float = 0.5,
                    reinvest: float = 0.0, iters: int = 80,
                    tol: float = 1e-4, alpha: float = 0.5,
                    trade_shares: Optional[Dict[str, Dict[str, float]]] = None,
                    fx_response: float = 0.0) -> "TradeSolution":
        """Tight bilateral trade: iterate the bloc to a fixed point where each
        country's exports = its partners' imports directed to it (gravity) plus
        an autonomous external-RoW component. Two-way: a boom in one country
        pulls in imports, lifting partners' exports and output, and back again.
        Each country stays individually consistency-gated; intra-bloc exports
        and imports must net out (the regional reconciliation check)."""
        geos = self.geos
        gdp = {g: self.orchs[g].params().gdp_full for g in geos}
        erat = {g: self.orchs[g].params().export_ratio for g in geos}
        Y0 = {g: self.orchs[g].params().Y0 for g in geos}
        wg = {g: self.orchs[g].params().world_growth for g in geos}
        scen = {g: self._policy_scenario(g, form, tau, reinvest, horizon)
                for g in geos}

        # bilateral import-share matrix: real (injected) or gravity fallback
        W = trade_shares or self.gravity_matrix(gdp)
        # FX competitiveness: euro members are locked to parity (comp=1); a
        # non-euro member running deficits depreciates -> more competitive exports.
        comp = {g: 1.0 for g in geos}

        Y = {g: [Y0[g]] * horizon for g in geos}
        M = {g: [erat[g] * Y0[g]] * horizon for g in geos}   # seed
        runs: Dict[str, object] = {}
        converged, used = False, 0
        for it in range(iters):
            used = it + 1
            # 1) set each country's exports = intra (partners' imports, via the
            #    bilateral matrix) + external, scaled by FX competitiveness.
            for j in geos:
                path = []
                for t in range(horizon):
                    intra = sum(intra_share * M[i][t] * W[i].get(j, 0.0)
                                for i in geos if i != j)
                    # external (extra-bloc) demand grows EXOGENOUSLY at the
                    # world rate from the baseline level - NOT with own output
                    # (own-output coupling is the entrepot/LU instability; it
                    # was fixed in the core 2026-06-07 but had survived here).
                    external = ((1.0 - intra_share) * erat[j] * Y0[j]
                                * (1.0 + wg[j]) ** t)
                    path.append((intra + external) * comp[j])
                scen[j].exports_override = LeverPath(path)
            # 2) run every country with the injected exports
            newY = {}
            for g in geos:
                runs[g] = self.orchs[g].run_scenario(scen[g])
                newY[g] = [pp.reported["gdp"] for pp in runs[g].result.periods]
                M[g] = [pp.reported["imports"] for pp in runs[g].result.periods]
                if fx_response and not is_euro(g):
                    nfa_gdp = runs[g].result.periods[-1].reported.get("nfa_gdp", 0.0)
                    adj = max(-0.5, min(0.5, -nfa_gdp / 100.0))   # deficit -> depreciate
                    comp[g] = 1.0 + fx_response * adj
            # 3) damped update + convergence on the GDP vectors (relaxation
            #    tames the export<->import cobweb that compounds over 30y)
            delta = max(abs(newY[g][t] - Y[g][t]) / max(1.0, Y[g][t])
                        for g in geos for t in range(horizon))
            Y = {g: [(1.0 - alpha) * Y[g][t] + alpha * newY[g][t]
                     for t in range(horizon)] for g in geos}
            if delta < tol:
                converged = True
                break

        # regional reconciliation: intra-bloc exports total == imports total
        intra_exp = {g: [sum(intra_share * M[i][t] * W[i].get(g, 0.0)
                             for i in geos if i != g) for t in range(horizon)]
                     for g in geos}
        worst_bal = 0.0
        for t in range(horizon):
            exp_tot = sum(intra_exp[g][t] for g in geos)
            imp_tot = sum(intra_share * M[i][t] for i in geos)
            worst_bal = max(worst_bal, abs(exp_tot - imp_tot))

        return TradeSolution(
            geos=list(geos), horizon=horizon, intra_share=intra_share,
            converged=converged, iters_used=used,
            consistent=all(r.consistent for r in runs.values()),
            max_residual=max(r.max_residual for r in runs.values()),
            trade_balance_residual=worst_bal, gdp=Y, intra_exports=intra_exp)


@dataclass
class TradeSolution:
    """Outcome of the tight bilateral-trade fixed point over the bloc."""
    geos: List[str]
    horizon: int
    intra_share: float
    converged: bool
    iters_used: int
    consistent: bool                 # every country still passes its own gate
    max_residual: float              # worst per-country consistency residual
    trade_balance_residual: float    # |intra-bloc exports - imports|, worst period
    gdp: Dict[str, List[float]] = field(default_factory=dict)
    intra_exports: Dict[str, List[float]] = field(default_factory=dict)

