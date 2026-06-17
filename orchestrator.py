"""Orchestrator + consistency gate (Layer 2).

Turns a scenario into an ordered run across the active modules, passing each
module a `context` of the results produced so far (loose coupling: the macro
core sets aggregates, downstream modules decompose them), reconciles their
outputs through the schema, and runs the consistency gate on every period.

Phase 2 default chain: SFC core -> distribution module. The gate now also runs
the reconciliation check (decile incomes sum to the macro household disposable
income).

Also owns calibration loading and the baseline validation ('validate before
trusting').
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from modules.interface import Module, Scenario, RunResult
from modules.sfc_core import SFCCore
from modules.distribution import DistributionModule
from modules.input_output import InputOutputModule
from calibration import calibrate, SFCParams
from consistency.checks import (check_run, check_distribution,
                                check_input_output, ConsistencyReport,
                                ConsistencyError)
from data.connectors.dbnomics import DBnomicsConnector
from data.store import Store
from scenarios import make_triad, make_ubc_experiment
from policy_search import search_policies, PolicyPoint


@dataclass
class ScenarioRun:
    scenario: str
    results: Dict[str, RunResult]            # module name -> result
    reports: List[ConsistencyReport]

    # Backward-compatible accessors --------------------------------------- #
    @property
    def result(self) -> RunResult:
        """The primary (macro) result."""
        return self.results.get("sfc_core") or next(iter(self.results.values()))

    @property
    def dist(self) -> Optional[RunResult]:
        return self.results.get("distribution")

    @property
    def io(self) -> Optional[RunResult]:
        return self.results.get("input_output")

    @property
    def consistent(self) -> bool:
        return all(r.passed for r in self.reports)

    @property
    def max_residual(self) -> float:
        return max((r.max_residual for r in self.reports), default=0.0)


@dataclass
class ValidationRow:
    metric: str
    target: float
    model: float
    rel_error: float
    ok: bool


class AgoraOrchestrator:
    def __init__(self, geo: str = "DE", year: int = 2019,
                 modules: Optional[List[Module]] = None,
                 store: Optional[Store] = None,
                 allow_live: bool = True, strict: bool = True,
                 inv_elasticity: float = 0.0):
        self.geo = geo
        self.year = year
        self.inv_elasticity = float(inv_elasticity)
        self.modules = modules or [SFCCore(base_year=year,
                                           inv_elasticity=inv_elasticity),
                                   DistributionModule(base_year=year),
                                   InputOutputModule(base_year=year)]
        self.store = store
        self.allow_live = allow_live
        self.strict = strict
        self._data: Optional[Dict[str, float]] = None
        self._sources: Dict[str, str] = {}

    def load_data(self) -> Dict[str, float]:
        conn = DBnomicsConnector(allow_live=self.allow_live)
        rows = conn.fetch(self.geo, self.year)
        self._data = {code: r["value"] for code, r in rows.items()}
        self._sources = {code: r["source"] for code, r in rows.items()}
        self._data["_sources"] = self._sources
        if self.store is not None and self.store.available:
            self.store.upsert_series([
                {"geo": self.geo, "series_code": c, "year": self.year,
                 "value": r["value"], "unit": r["unit"], "provider": r["provider"],
                 "provider_code": r["provider_code"], "source_url": r["source_url"],
                 "source": r["source"]}
                for c, r in rows.items()
            ])
        return self._data

    def params(self) -> SFCParams:
        if self._data is None:
            self.load_data()
        return calibrate(self._data, geo=self.geo, base_year=self.year,
                         sources=self._sources)

    def run_scenario(self, scenario: Scenario) -> ScenarioRun:
        if self._data is None:
            self.load_data()
        context: Dict[str, RunResult] = {}
        results: Dict[str, RunResult] = {}
        reports: List[ConsistencyReport] = []
        for module in self.modules:
            res = module.run(scenario, self._data, context)
            results[module.name] = res
            context[module.name] = res
            if module.name == "distribution":
                reports += check_distribution(res)             # reconciliation
            elif module.name == "input_output":
                reports += check_input_output(res)             # sectoral reconciliation
            else:
                reports += check_run(res, strict=self.strict)  # generic gate
        run_id = uuid.uuid4().hex[:12]
        if self.store is not None and self.store.available:
            for res in results.values():
                self.store.save_result(run_id, res)
            self.store.save_consistency(run_id, scenario.name, reports)
        return ScenarioRun(scenario.name, results, reports)

    def run_triad(self, horizon: int = 30) -> List[ScenarioRun]:
        p = self.params()
        return [self.run_scenario(s) for s in make_triad(p, horizon=horizon)]

    def run_ubc_experiment(self, horizon: int = 30,
                           inv_elasticity: Optional[float] = None,
                           reinvest: float = 0.0) -> List[ScenarioRun]:
        """The pinned experiment: Universal Basic Capital vs cash UBI.
        Runs all four arms through the full chain + consistency gate.

        `inv_elasticity` overrides the investment-feedback elasticity for this
        run (None = the orchestrator's own setting); `reinvest` sets the UBC
        fund's capex-reinvestment fraction. Together they run the C1 (enclosure-
        vs-diffusion) test: does endogenous investment choke UBC, and does fund
        reinvestment cure it?"""
        p = self.params()
        scens = make_ubc_experiment(p, horizon=horizon, reinvest=reinvest)
        if inv_elasticity is None or inv_elasticity == self.inv_elasticity:
            return [self.run_scenario(s) for s in scens]
        # Endogenous-investment override: swap in a module chain with the new
        # elasticity for the duration of this run, then restore.
        saved = self.modules
        self.modules = [
            SFCCore(base_year=self.year, inv_elasticity=float(inv_elasticity)),
            DistributionModule(base_year=self.year),
            InputOutputModule(base_year=self.year)]
        try:
            return [self.run_scenario(s) for s in scens]
        finally:
            self.modules = saved

    def c1_closure(self, horizon: int = 30, inv_elasticity: float = 0.75,
                   reinvest: float = 0.6) -> Dict[str, Dict[str, float]]:
        """Crux C1 (does predistribution choke investment?). Compares the cash-UBI
        and UBC arms' end-of-horizon economy size and inequality under three
        investment regimes: FIXED (autonomous capex, the legacy headline),
        ENDOGENOUS with no fund reinvestment (owners diluted -> capex falls), and
        ENDOGENOUS + fund REINVESTMENT (the fund sustains capex). Returns the
        numbers behind the closure finding. Every arm is gated by run_scenario."""
        def _end(runs: List[ScenarioRun]) -> Dict[str, ScenarioRun]:
            return {r.scenario: r for r in runs}

        def _metrics(by: Dict[str, ScenarioRun], arm: str) -> Dict[str, float]:
            run = by[arm]
            gdp = run.result.periods[-1].reported.get(
                "gdp", run.result.periods[-1].reported.get("Y", 0.0))
            rep = run.dist.periods[-1].reported
            return {"gdp_end": gdp, "gini_end": rep["gini_personal"],
                    "wealth_top10_end": rep["top10_wealth_share"],
                    "consistent": run.consistent}

        configs = {
            "fixed":            dict(inv_elasticity=0.0, reinvest=0.0),
            "endogenous":       dict(inv_elasticity=inv_elasticity, reinvest=0.0),
            "endogenous+reinvest": dict(inv_elasticity=inv_elasticity,
                                        reinvest=reinvest),
        }
        out: Dict[str, Dict[str, float]] = {}
        for name, kw in configs.items():
            by = _end(self.run_ubc_experiment(horizon=horizon, **kw))
            cash = _metrics(by, "AI + Cash UBI")
            ubc = _metrics(by, "AI + Universal Basic Capital")
            out[name] = {
                "cash_gdp_end": cash["gdp_end"], "ubc_gdp_end": ubc["gdp_end"],
                "ubc_vs_cash_gdp": ubc["gdp_end"] / cash["gdp_end"]
                if cash["gdp_end"] else float("nan"),
                "cash_gini_end": cash["gini_end"], "ubc_gini_end": ubc["gini_end"],
                "cash_wealth_top10_end": cash["wealth_top10_end"],
                "ubc_wealth_top10_end": ubc["wealth_top10_end"],
                "all_consistent": cash["consistent"] and ubc["consistent"],
            }
        return out

    def run_policy_search(self, taus=None, horizon: int = 30):
        """Phase 4: sweep the policy space and return all evaluated points
        (Pareto frontier flagged). Each candidate is run through the full
        gated chain, so the frontier is built only from consistent points."""
        p = self.params()
        return search_policies(self.run_scenario, p, taus=taus, horizon=horizon)

    def validate_baseline(self, horizon: int = 30,
                          rtol: float = 0.005) -> Tuple[List[ValidationRow], ScenarioRun]:
        """Backtest: does the baseline year-0 reproduce the national targets?"""
        p = self.params()
        baseline = make_triad(p, horizon=horizon)[0]
        run = self.run_scenario(baseline)
        m0 = run.result.periods[0].reported
        t = p.targets

        def row(metric, target, model, tol=rtol):
            denom = abs(target) if target else 1.0
            rel = abs(model - target) / denom
            return ValidationRow(metric, target, model, rel, rel <= tol)

        seed_debt_full = 100.0 * (p.M_w0 + p.M_k0) / t["gdp"]
        rows = [
            row("GDP (C+I+G+X-M)", t["gdp_expenditure"], m0["gdp"]),
            row("Exports", t["exports"], m0["exports"]),
            row("Imports", t["imports"], m0["imports"]),
            row("Net exports", t["net_exports"], m0["net_exports"]),
            row("Household consumption", t["hh_consumption"], m0["consumption"]),
            row("Investment (GFCF)", t["gfcf"], m0["investment"]),
            row("Government expenditure", t["gov_consumption"], m0["gov_expenditure"]),
            row("Labour share (%)", t["labour_share"], m0["labour_share"]),
            row("Gov debt seed / full GDP (%)", t["gov_debt_gdp"], seed_debt_full),
        ]
        # distribution anchor: year-0 personal Gini reproduces the observed Gini
        if run.dist is not None:
            d0 = run.dist.periods[0].reported
            rows.append(row("Gini personal (x100, baseline)",
                            t["gini_disp_income"], d0["gini_personal"] * 100.0,
                            tol=0.05))
        return rows, run


def build(geo: str = "DE", year: int = 2019, allow_live: bool = True,
          db_path: Optional[str] = None, strict: bool = True) -> AgoraOrchestrator:
    store = Store(db_path) if db_path is not None else None
    return AgoraOrchestrator(geo=geo, year=year, store=store,
                             allow_live=allow_live, strict=strict)
