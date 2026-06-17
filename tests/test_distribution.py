"""Distribution module: anchoring, reconciliation gate, and the decoupling
mechanism at the personal (decile) level — for DE and FR, offline."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from orchestrator import AgoraOrchestrator
from consistency.checks import check_distribution
from modules.distribution import decile_shares, grouped_gini


@pytest.fixture(scope="module", params=["DE", "FR"])
def runs(request):
    o = AgoraOrchestrator(geo=request.param, year=2019, allow_live=False, strict=True)
    o.load_data()
    return {r.scenario: r for r in o.run_triad(horizon=30)}, request.param


def test_decile_shares_sum_to_one():
    for g in (0.10, 0.297, 0.5, 0.7):
        s = decile_shares(g)
        assert abs(sum(s) - 1.0) < 1e-9
        assert all(s[i] <= s[i + 1] + 1e-12 for i in range(9))  # ascending


def test_distribution_present_and_reconciles(runs):
    data, geo = runs
    for name, run in data.items():
        assert run.dist is not None, f"{geo}/{name}: no distribution result"
        reps = check_distribution(run.dist)
        worst = max(r.max_residual for r in reps)
        assert all(r.passed for r in reps), f"{geo}/{name} reconcile {worst:.3e}"
        assert worst < 1.0                       # sums to well under one euro


def test_baseline_gini_anchored_to_observed(runs):
    data, geo = runs
    base0 = data["Baseline"].result.periods[0].reported          # SFC
    dist0 = data["Baseline"].dist.periods[0].reported            # distribution
    target = {"DE": 0.297, "FR": 0.292}[geo]
    # year-0 personal Gini reproduces the observed disposable-income Gini
    assert abs(dist0["gini_personal"] - target) < 0.01
    # and the baseline gini holds across the horizon (no AI shift, no policy)
    last = data["Baseline"].dist.periods[-1].reported
    assert abs(last["gini_personal"] - target) < 0.02


def test_personal_decoupling_and_settlement(runs):
    data, geo = runs
    base = data["Baseline"].dist.periods[-1].reported
    nopol = data["AI shift, no policy"].dist.periods[-1].reported
    settle = data["AI shift + Abundance Settlement"].dist.periods[-1].reported

    # no policy: inequality AND poverty rise vs baseline
    assert nopol["gini_personal"] > base["gini_personal"]
    assert nopol["poverty_rate"] > base["poverty_rate"]
    assert nopol["top10_share"] > base["top10_share"]

    # settlement contains both relative to the no-policy path
    assert settle["gini_personal"] < nopol["gini_personal"]
    assert settle["poverty_rate"] < nopol["poverty_rate"]


def test_winners_losers_direction(runs):
    """Per-decile: the settlement lifts the bottom decile's share vs no-policy,
    and trims the top decile's share."""
    data, _ = runs
    nopol = data["AI shift, no policy"].dist.periods[-1].reported
    settle = data["AI shift + Abundance Settlement"].dist.periods[-1].reported
    assert settle["decile_share_1"] > nopol["decile_share_1"]    # poorest gain
    assert settle["decile_share_10"] < nopol["decile_share_10"]  # richest trim


# --- dynamic wealth distribution (#56): the dimension UBC actually targets ---- #
def test_wealth_distribution_only_ubc_compresses_it():
    """Cash UBI is a flow: it compresses income but leaves WEALTH concentration
    untouched. UBC socialises capital, so the top-10% wealth share collapses.
    This is the model dimension that makes 'owning beats receiving' explicit."""
    from orchestrator import AgoraOrchestrator
    o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True)
    o.load_data()
    runs = {r.scenario: r for r in o.run_ubc_experiment(horizon=30)}
    for tag in ("AI shift, no policy", "AI + Cash UBI", "AI + Universal Basic Capital"):
        d = runs[tag].dist.periods
        for k in ("top10_wealth_share", "bottom50_wealth_share", "wealth_gini"):
            assert k in d[-1].reported
    w0 = runs["AI + Cash UBI"].dist.periods[0].reported["top10_wealth_share"]
    cash_end = runs["AI + Cash UBI"].dist.periods[-1].reported["top10_wealth_share"]
    nopol_end = runs["AI shift, no policy"].dist.periods[-1].reported["top10_wealth_share"]
    ubc_end = runs["AI + Universal Basic Capital"].dist.periods[-1].reported["top10_wealth_share"]
    # With the endogenous wealth channel (omega>0), the capital-share rise
    # concentrates wealth EQUALLY across no-policy and cash (flows don't touch
    # ownership), so cash TRACKS no-policy - it does not socialise capital.
    assert abs(cash_end - nopol_end) < 0.01    # cash UBI tracks no-policy on WEALTH
    assert cash_end >= w0 - 0.01               # cash does NOT reduce concentration (rises with capital share)
    assert ubc_end < nopol_end - 0.2           # only UBC collapses the top-wealth share
    assert ubc_end < w0 - 0.2                  # UBC ends far below baseline
    assert (runs["AI + Universal Basic Capital"].dist.periods[-1].reported["wealth_gini"]
            < runs["AI + Cash UBI"].dist.periods[-1].reported["wealth_gini"])


def test_omega_endogenous_wealth_concentration():
    """omega=0 freezes no-policy wealth (legacy); omega>0 makes it concentrate as
    the capital share rises - even with no policy - which is what makes the flat
    baseline defensible and strengthens the UBC comparison."""
    from orchestrator import AgoraOrchestrator
    from modules.sfc_core import SFCCore
    from modules.distribution import DistributionModule
    from modules.input_output import InputOutputModule

    def nopol_wealth(omega):
        mods = [SFCCore(base_year=2019),
                DistributionModule(base_year=2019, omega=omega),
                InputOutputModule(base_year=2019)]
        o = AgoraOrchestrator(geo="DE", year=2019, modules=mods,
                              allow_live=False, strict=True)
        o.load_data()
        runs = {r.scenario: r for r in o.run_ubc_experiment(horizon=30)}
        d = runs["AI shift, no policy"].dist.periods
        return d[0].reported["top10_wealth_share"], d[-1].reported["top10_wealth_share"]

    w0_off, wend_off = nopol_wealth(0.0)
    assert abs(wend_off - w0_off) < 1e-9               # omega=0 -> frozen (backward-compatible)
    w0_on, wend_on = nopol_wealth(0.15)
    assert wend_on > w0_on + 0.02                      # omega>0 -> concentrates
    assert 0.10 <= wend_on <= 0.99                     # stays in bounds


# --- optional true MARKET-Gini anchor (OECD IDD), default OFF --------------- #
def test_market_anchor_reproduces_baseline_and_reports_true_level():
    """With the IDD market anchor on, the baseline still reproduces the observed
    DISPOSABLE Gini (the welfare state enters as the baseline wedge), but the
    reported gini_market is now the true PRE-tax level — and the reconciliation
    gate still holds. Default-off behaviour is covered by the other tests."""
    from orchestrator import AgoraOrchestrator
    from modules.sfc_core import SFCCore
    from modules.distribution import DistributionModule
    from modules.input_output import InputOutputModule
    from consistency.checks import check_distribution
    from data.connectors.oecd_idd import OECDIDDConnector

    M0 = OECDIDDConnector().fetch("DE")["gini_market_oecd"]["value"]
    mods = [SFCCore(base_year=2019),
            DistributionModule(base_year=2019, gini_market_anchor=M0),
            InputOutputModule(base_year=2019)]
    o = AgoraOrchestrator(geo="DE", year=2019, modules=mods,
                          allow_live=False, strict=True)
    o.load_data()
    runs = {r.scenario: r for r in o.run_triad(horizon=30)}
    b0 = runs["Baseline"].dist.periods[0].reported
    assert abs(b0["gini_personal"] - 0.297) < 0.01      # disposable reproduced
    assert abs(b0["gini_market"] - M0) < 1e-6           # true market level
    meta = runs["Baseline"].dist.meta
    assert meta["gini_market_anchor"] == M0
    assert 0.30 < meta["baseline_redistribution_wedge"] < 0.50
    worst = max(r.max_residual for run_ in runs.values()
                for r in check_distribution(run_.dist))
    assert worst < 1e-6                                  # gate still reconciles
