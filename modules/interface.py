"""The module interface — the contract every model adapter implements.

A module:
  * declares_inputs()  -> the schema series + scenario levers it needs
  * declares_outputs() -> the schema items / series it produces
  * run(scenario, data) -> RunResult

A RunResult carries, per period, the transaction-flow matrix (TFM) and the
balance-sheet matrix (BSM) expressed in *schema* names, plus the reported
series. The consistency checker operates generically on TFM/BSM, so any module
that emits well-formed matrices is automatically gated — no per-module check
code. New engine = new adapter implementing this interface; it just slots in.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Union

Number = float
LeverValue = Union[Number, Callable[[int, int], Number]]


# --------------------------------------------------------------------------- #
# Levers
# --------------------------------------------------------------------------- #
class LeverPath:
    """A scenario lever that may be constant or a function of time.

    Resolved as path(t, horizon) -> value. Accepts a constant, an explicit
    list/array, or a callable. This keeps scenarios declarative and inspectable.
    """

    def __init__(self, spec: Union[Number, List[Number], Callable[[int, int], Number]],
                 label: str = ""):
        self.spec = spec
        self.label = label

    def at(self, t: int, horizon: int) -> Number:
        spec = self.spec
        if callable(spec):
            return float(spec(t, horizon))
        if isinstance(spec, (list, tuple)):
            idx = min(t, len(spec) - 1)
            return float(spec[idx])
        return float(spec)

    @staticmethod
    def ramp(start: Number, end: Number, label: str = "") -> "LeverPath":
        """Linear drift from `start` (t=0) to `end` (t=horizon-1)."""
        def f(t: int, horizon: int) -> Number:
            if horizon <= 1:
                return float(end)
            return float(start) + (float(end) - float(start)) * (t / (horizon - 1))
        return LeverPath(f, label)

    @staticmethod
    def grow(base: Number, rate: Number, label: str = "") -> "LeverPath":
        """Compound growth: base * (1 + rate) ** t."""
        def f(t: int, horizon: int) -> Number:
            return float(base) * (1.0 + float(rate)) ** t
        return LeverPath(f, label)


# --------------------------------------------------------------------------- #
# Scenario
# --------------------------------------------------------------------------- #
@dataclass
class Scenario:
    """A scenario = horizon + lever paths. Every lever is inspectable & swappable.

    Levers (Phase 1, all mapped to schema flows):
      labour_share   — wage share of output (drifts under the AI shift)
      ai_capex       — autonomous investment injection A as a *ratio of baseline GDP*
      gov_ratio      — government expenditure as a ratio of LAGGED output
                       (= baseline GDP at t=0, then grows with the economy)
      tax_income     — income-tax rate on wages
      tax_capital    — capital-tax rate on distributed profits (settlement lever)
      ubi_on         — recycle capital-tax revenue as a per-capita UBI (1/0)
      ubc_on         — channel the capital levy into a citizens' capital fund
                       that pays a per-capita dividend (Universal Basic Capital, 1/0)
      ubc_reinvest   — fraction of the fund's profit share it REINVESTS into
                       capex (vs pays out); sustains investment as owners dilute
    """
    name: str
    horizon: int = 30
    geo: str = "DE"
    labour_share: LeverPath = field(default_factory=lambda: LeverPath(0.61))
    ai_capex: LeverPath = field(default_factory=lambda: LeverPath.grow(0.21, 0.015))
    gov_ratio: LeverPath = field(default_factory=lambda: LeverPath(0.20))
    tax_income: LeverPath = field(default_factory=lambda: LeverPath(0.20))
    tax_capital: LeverPath = field(default_factory=lambda: LeverPath(0.0))
    ubi_on: LeverPath = field(default_factory=lambda: LeverPath(0.0))
    ubc_on: LeverPath = field(default_factory=lambda: LeverPath(0.0))
    ubc_reinvest: LeverPath = field(default_factory=lambda: LeverPath(0.0))
    # absolute exports path (MEUR), set by the multi-region trade linker to
    # tie one country's exports to its partners' imports; None = autonomous.
    exports_override: Optional[LeverPath] = None
    # absolute government-expenditure path (MEUR); the backtest uses it to
    # drive G with the realised series. None = gov_ratio * lagged output.
    gov_override: Optional[LeverPath] = None
    # net cross-border transfer to households (MEUR, + = receipts), set by the
    # multi-region pooled-dividend arm; enters the current account vs RoW.
    intl_transfer: Optional[LeverPath] = None
    description: str = ""

    def levers(self) -> Dict[str, LeverPath]:
        return {
            "labour_share": self.labour_share,
            "ai_capex": self.ai_capex,
            "gov_ratio": self.gov_ratio,
            "tax_income": self.tax_income,
            "tax_capital": self.tax_capital,
            "ubi_on": self.ubi_on,
            "ubc_on": self.ubc_on,
            "ubc_reinvest": self.ubc_reinvest,
        }

    def snapshot(self) -> Dict[str, List[float]]:
        """Resolve every lever across the horizon — for the assumptions panel."""
        return {
            name: [lev.at(t, self.horizon) for t in range(self.horizon)]
            for name, lev in self.levers().items()
        }


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
@dataclass
class PeriodState:
    """One period of a run, expressed in schema names.

    tfm[flow][sector]   : transaction-flow value (source +, use -), each flow
                          row must sum to ~0 across sectors.
    bsm[instrument][sector] : stock at end of period (asset +, liability -),
                          each financial instrument must sum to ~0 across sectors.
    reported[name]      : reported series values (gdp, consumption, gini, ...).
    """
    year: int
    tfm: Dict[str, Dict[str, float]] = field(default_factory=dict)
    bsm: Dict[str, Dict[str, float]] = field(default_factory=dict)
    reported: Dict[str, float] = field(default_factory=dict)


@dataclass
class RunResult:
    module: str
    scenario: str
    geo: str
    periods: List[PeriodState] = field(default_factory=list)
    meta: Dict[str, object] = field(default_factory=dict)

    def series(self, name: str) -> List[float]:
        """Time path of one reported series across the horizon."""
        return [p.reported.get(name, float("nan")) for p in self.periods]

    def years(self) -> List[int]:
        return [p.year for p in self.periods]


# --------------------------------------------------------------------------- #
# Module ABC
# --------------------------------------------------------------------------- #
class Module:
    """Base class every engine adapter implements. Loose coupling: a module
    declares the schema names it needs and produces; the orchestrator wires
    them and runs the consistency gate on the emitted matrices."""

    name: str = "module"

    def declares_inputs(self) -> List[str]:
        raise NotImplementedError

    def declares_outputs(self) -> List[str]:
        raise NotImplementedError

    def run(self, scenario: Scenario, data: Dict[str, float]) -> RunResult:
        raise NotImplementedError
