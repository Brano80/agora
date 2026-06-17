"""SFC core: consistency over the full horizon for all three scenarios,
baseline reproduces German 2019 targets, and the decoupling result holds."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from orchestrator import AgoraOrchestrator
from scenarios import make_triad
from consistency.checks import check_run


@pytest.fixture(scope="module")
def orch():
    o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True)
    o.load_data()
    return o


def test_snapshot_loaded(orch):
    assert orch._data["gdp"] > 3_000_000          # German GDP in MEUR
    assert all(v == "snapshot" for v in orch._sources.values())


def test_all_scenarios_consistent(orch):
    p = orch.params()
    for scen in make_triad(p, horizon=30):
        result = orch.modules[0].run(scen, orch._data)
        reports = check_run(result, strict=False)
        worst = max(r.max_residual for r in reports)
        assert all(r.passed for r in reports), \
            f"{scen.name}: worst residual {worst:.3e}"
        # books close to well under one euro on a multi-trillion economy
        assert worst < 1.0


def test_baseline_reproduces_targets(orch):
    rows, _ = orch.validate_baseline(horizon=30)
    failures = [r.metric for r in rows if not r.ok]
    assert not failures, f"calibration off for: {failures}"


def test_capital_accumulation_identity(orch):
    """Real capital articulation with the two-stock split: total capital equals
    last period's stock, less depreciation on each component (traditional at δ,
    AI at δ_ai), plus this period's investment.
        K_t == K_{t-1} - (δ·K_trad_{t-1} + δ_ai·K_ai_{t-1}) + investment_t
    """
    p = orch.params()
    scen = make_triad(p, horizon=30)[1]   # AI boom
    res = orch.modules[0].run(scen, orch._data)
    for i in range(1, len(res.periods)):
        cur, prv = res.periods[i].reported, res.periods[i - 1].reported
        dep = p.delta * prv["capital_traditional"] + p.delta_ai * prv["capital_ai"]
        expected = prv["capital"] - dep + cur["investment"]
        assert abs(cur["capital"] - expected) < 1e-6
    # AI capital is built only by the boom (excess over the baseline ratio) and
    # obsolesces fast, so it stays a minority of the stock here.
    assert res.periods[-1].reported["capital_ai_share"] < 1.0
    assert res.periods[-1].reported["capital_ai"] > 0   # the boom did build some


def test_decoupling_mechanism(orch):
    """The thesis: AI-no-policy raises inequality vs baseline; the settlement
    contains inequality and lifts consumption above the no-policy path."""
    runs = {r.scenario: r for r in orch.run_triad(horizon=30)}
    base = runs["Baseline"].result.periods[-1].reported
    nopol = runs["AI shift, no policy"].result.periods[-1].reported
    settle = runs["AI shift + Abundance Settlement"].result.periods[-1].reported

    # decoupling: inequality explodes without policy
    assert nopol["gini"] > base["gini"]
    # settlement contains inequality relative to no-policy
    assert settle["gini"] < nopol["gini"]
    # settlement sustains demand: consumption above the no-policy path
    assert settle["consumption"] > nopol["consumption"]


# --- second country: France ------------------------------------------------ #
@pytest.fixture(scope="module")
def orch_fr():
    o = AgoraOrchestrator(geo="FR", year=2019, allow_live=False, strict=True)
    o.load_data()
    return o


def test_fr_snapshot_loaded(orch_fr):
    assert orch_fr._data["gdp"] > 2_000_000          # French GDP in MEUR
    assert all(v == "snapshot" for v in orch_fr._sources.values())


def test_fr_baseline_reproduces_targets(orch_fr):
    rows, _ = orch_fr.validate_baseline(horizon=30)
    failures = [r.metric for r in rows if not r.ok]
    assert not failures, f"FR calibration off for: {failures}"


def test_fr_all_scenarios_consistent(orch_fr):
    p = orch_fr.params()
    for scen in make_triad(p, horizon=30):
        result = orch_fr.modules[0].run(scen, orch_fr._data)
        reports = check_run(result, strict=False)
        worst = max(r.max_residual for r in reports)
        assert all(r.passed for r in reports), f"FR {scen.name}: {worst:.3e}"
        assert worst < 1.0


def test_fr_decoupling_mechanism(orch_fr):
    runs = {r.scenario: r for r in orch_fr.run_triad(horizon=30)}
    base = runs["Baseline"].result.periods[-1].reported
    nopol = runs["AI shift, no policy"].result.periods[-1].reported
    settle = runs["AI shift + Abundance Settlement"].result.periods[-1].reported
    assert nopol["gini"] > base["gini"]
    assert settle["gini"] < nopol["gini"]
    assert settle["consumption"] > nopol["consumption"]


def test_interest_on_gov_debt_is_gated_and_optional(orch):
    """Interest on government debt (i_rate): default off reproduces the no-interest
    path; switched on it pays debt service, stays consistency-gated, and changes
    the fiscal trajectory (the F2 finding hardened)."""
    from modules.sfc_core import SFCCore
    from calibration import calibrate
    from consistency.checks import check_run
    data = orch._data
    scen = make_triad(orch.params(), horizon=30)[1]      # AI shift, no policy

    base = SFCCore(base_year=2019).run(scen, data)        # i_rate default 0
    assert all(per.reported["gov_interest"] == 0.0 for per in base.periods)

    p_i = calibrate(data, geo="DE", base_year=2019, i_rate=0.03)
    withi = SFCCore(base_year=2019, calib_kwargs={"i_rate": 0.03}).run(
        make_triad(p_i, horizon=30)[1], data)
    reports = check_run(withi, strict=False)
    assert all(r.passed for r in reports)                 # still gate-clean
    assert max(r.max_residual for r in reports) < 1.0
    # interest accrues on the debt (sign follows the debt: a surplus-running
    # government is a net creditor and earns it), and it bends the fiscal path.
    assert any(abs(per.reported["gov_interest"]) > 0 for per in withi.periods)
    assert (withi.periods[-1].reported["gov_debt_gdp"]
            != base.periods[-1].reported["gov_debt_gdp"])      # fiscal path moves
