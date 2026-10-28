"""Plausibility v2 (Phase 7 step A, 2026-10-28).

The accounting laws prove nothing leaks; they cannot prove a balance sheet is
POSSIBLE. The 2026-10-28 review found gate-clean runs in which capital owners
end deeply insolvent (financing capex with an unlimited, interest-free
overdraft), investment exceeds 40% of GDP and inequality falls below anything
observed. These tests pin those pathologies as CAUGHT in enforce mode, and pin
that audit mode (the default until Phase 7 step B) leaves every shipped
result's pass/fail unchanged.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calibration import calibrate
from consistency.checks import (ConsistencyError, check_distribution,
                                check_period, check_run,
                                MAX_INVESTMENT_SHARE, MIN_PERSONAL_GINI)
from data.connectors.dbnomics import DBnomicsConnector
from modules.interface import PeriodState, RunResult
from modules.sfc_core import SFCCore
from orchestrator import AgoraOrchestrator
from scenarios import build_custom, make_ubc_experiment
from uncertainty import PRIORS

UBC_ARM, CASH_ARM, NOPOL_ARM, BASE_ARM = 3, 2, 1, 0


def _arm(geo, idx, **orch_kw):
    o = AgoraOrchestrator(geo=geo, allow_live=False, **orch_kw)
    scen = make_ubc_experiment(o.params(), horizon=30)[idx]
    return o.run_scenario(scen)


def _failed_names(reports):
    return {c.name for r in reports for c in r.failures()}


def _advisory_names(reports):
    return {c.name for r in reports for c in r.advisories()}


# --------------------------------------------------------------------------- #
# audit mode (default): reported, never blocking
# --------------------------------------------------------------------------- #
def test_audit_mode_reports_but_does_not_block():
    run = _arm("DE", UBC_ARM)                 # orchestrator default: audit
    assert run.consistent, "audit mode must not change the shipped gate verdict"
    assert run.max_residual < 1e-3, "advisory checks must not leak into max_residual"
    assert "hh_net_worth_nonnegative" in _advisory_names(run.reports)


# --------------------------------------------------------------------------- #
# enforce mode catches the review's findings
# --------------------------------------------------------------------------- #
def test_enforce_catches_de_ubc_owner_insolvency():
    run = _arm("DE", UBC_ARM)
    reps = check_run(run.result, plausibility="enforce")
    assert "hh_net_worth_nonnegative" in _failed_names(reps)
    assert "money_split_shares_valid" in _failed_names(reps)
    with pytest.raises(ConsistencyError):
        check_run(run.result, strict=True, plausibility="enforce")


def test_enforce_catches_sk_ubc_owner_insolvency():
    run = _arm("SK", UBC_ARM)
    assert "hh_net_worth_nonnegative" in _failed_names(
        check_run(run.result, plausibility="enforce"))


def test_enforce_catches_cash_arm_negative_owner_money():
    """Not a UBC-only defect: the cash arm also runs owners' money negative."""
    run = _arm("DE", CASH_ARM)
    assert "money_split_shares_valid" in _failed_names(
        check_run(run.result, plausibility="enforce"))


def test_enforce_catches_insolvent_monte_carlo_draw():
    """A draw inside the published Monte-Carlo prior (uncertainty.PRIORS) that
    ends with insolvent owners - such draws were counted in the F12 bands."""
    draw = {"labour_share_end": 0.30, "capex_growth": 0.09,
            "inv_elasticity": 0.0, "a1_w": 0.95}
    for k, v in draw.items():
        lo, hi = PRIORS[k]
        assert lo <= v <= hi, f"{k}={v} outside the published prior"
    rows = DBnomicsConnector(allow_live=False).fetch("DE", 2019)
    data = {k: r["value"] for k, r in rows.items()}
    p = calibrate(data, geo="DE", base_year=2019, a1_w=draw["a1_w"])
    scen = build_custom(p, labour_share_end=draw["labour_share_end"],
                        capex_growth=draw["capex_growth"], capital_tax=0.40,
                        horizon=30, name="mc-draw", ubc=True)
    res = SFCCore(base_year=2019, inv_elasticity=draw["inv_elasticity"],
                  calib_kwargs={"a1_w": draw["a1_w"]}).run(scen, data)
    assert all(r.passed for r in check_run(res)), "audit: books still clean"
    assert "hh_net_worth_nonnegative" in _failed_names(
        check_run(res, plausibility="enforce"))


def test_enforce_catches_investment_runaway():
    """Exogenous +6%/yr AI capex pushes investment above 40% of GDP."""
    run = _arm("DE", NOPOL_ARM)
    assert "investment_share_bounded" in _failed_names(
        check_run(run.result, plausibility="enforce"))


def test_enforce_catches_gini_below_floor():
    """The frontier's UBC tau=50% point ends at a personal Gini of ~0.056."""
    o = AgoraOrchestrator(geo="DE", allow_live=False)
    run = o.run_scenario(build_custom(o.params(), labour_share_end=0.30,
                                      capital_tax=0.50, ubc=True, name="ubc50"))
    end_gini = run.dist.periods[-1].reported["gini_personal"]
    assert end_gini < MIN_PERSONAL_GINI
    assert "gini_floor" in _failed_names(
        check_distribution(run.dist, plausibility="enforce"))


@pytest.mark.parametrize("geo", ["DE", "FR", "SK", "PL"])
def test_enforce_passes_baselines(geo):
    """The new laws must not fail an economy with no shock and no policy."""
    run = _arm(geo, BASE_ARM)
    reps = (check_run(run.result, plausibility="enforce")
            + check_distribution(run.dist, plausibility="enforce"))
    assert all(r.passed for r in reps), _failed_names(reps)


def test_env_var_switches_mode_process_wide(monkeypatch):
    monkeypatch.setenv("AGORA_PLAUSIBILITY", "enforce")
    run = _arm("DE", UBC_ARM, strict=False)
    assert not run.consistent
    monkeypatch.setenv("AGORA_PLAUSIBILITY", "audit")
    assert _arm("DE", UBC_ARM, strict=False).consistent


# --------------------------------------------------------------------------- #
# unit-level behaviour on synthetic states
# --------------------------------------------------------------------------- #
def _state(owners_money, capital=10.0, inv=10.0, gdp=100.0):
    return PeriodState(
        2030,
        bsm={"money": {"hh_workers": 50.0, "hh_owners": owners_money,
                       "government": -(50.0 + owners_money)},
             "capital": {"hh_owners": capital}},
        reported={"gdp": gdp, "investment": inv})


def test_net_worth_counts_capital_not_only_money():
    """Owners may borrow against capital (money < 0) and stay solvent; that
    fails only the money-split law, not the net-worth law."""
    rep = check_period(_state(owners_money=-5.0, capital=10.0), plausibility="enforce")
    names = {c.name for c in rep.failures()}
    assert "hh_net_worth_nonnegative" not in names
    assert "money_split_shares_valid" in names
    rep = check_period(_state(owners_money=-15.0, capital=10.0), plausibility="enforce")
    assert "hh_net_worth_nonnegative" in {c.name for c in rep.failures()}


def test_audit_vs_enforce_on_same_state():
    st = _state(owners_money=-15.0, capital=10.0, inv=0.5 * 100.0)
    audit = check_period(st, plausibility="audit")
    assert audit.passed and audit.advisories()
    assert not check_period(st, plausibility="enforce").passed
    assert MAX_INVESTMENT_SHARE == 0.40


def test_owners_mpc_must_lie_in_unit_interval():
    st = _state(owners_money=5.0)
    for a1_k, ok in ((0.3, True), (1.2, False), (-0.1, False)):
        res = RunResult(module="sfc_core", scenario="t", geo="DE", periods=[st],
                        meta={"params": {"a1_k": a1_k}})
        names = _failed_names(check_run(res, plausibility="enforce"))
        assert ("owners_mpc_in_unit_interval" not in names) is ok, a1_k


def test_invalid_mode_rejected():
    with pytest.raises(ValueError):
        check_period(_state(owners_money=5.0), plausibility="strictest")
