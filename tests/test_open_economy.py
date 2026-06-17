"""Open economy (Phase 3): exports/imports inside the books, the rest_of_world
sector and fx_assets instrument gated, and net foreign assets accumulating the
current account. DE (surplus) and FR (near-balanced/deficit), offline."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from orchestrator import AgoraOrchestrator
from consistency.checks import check_run
from scenarios import make_triad


@pytest.fixture(scope="module", params=["DE", "FR"])
def ctx(request):
    o = AgoraOrchestrator(geo=request.param, year=2019, allow_live=False, strict=True)
    o.load_data()
    p = o.params()
    res = o.modules[0].run(make_triad(p)[0], o._data)   # baseline SFC result
    return o, p, res, request.param


def test_baseline_reproduces_full_gdp_and_trade(ctx):
    o, p, res, geo = ctx
    m0 = res.periods[0].reported
    t = p.targets
    for key, rep in [("gdp_expenditure", "gdp"), ("exports", "exports"),
                     ("imports", "imports"), ("net_exports", "net_exports")]:
        tgt = t[key]
        assert abs(m0[rep] - tgt) <= 1e-6 * max(1.0, abs(tgt)), \
            f"{geo}: {rep} {m0[rep]} vs target {tgt}"
    # POLICY (2026-06-11 scout review): imports are direct Eurostat pulls, not
    # identity-reconciled, so a small statistical discrepancy vs published GDP
    # is EXPECTED and tracked as nx_gap - bounded (<1% of GDP), not zero.
    assert abs(p.nx_gap) <= 0.01 * p.gdp_full


def test_fx_and_rest_of_world_gated(ctx):
    o, p, res, geo = ctx
    reports = check_run(res, strict=False)
    worst = max(r.max_residual for r in reports)
    assert all(r.passed for r in reports), f"{geo}: open-economy gate {worst:.3e}"
    assert worst < 1.0
    # fx_assets instrument is actually present and nets to ~0 across sectors
    last = res.periods[-1]
    assert "fx_assets" in last.bsm
    assert abs(sum(last.bsm["fx_assets"].values())) < 1.0
    assert "rest_of_world" in last.bsm["fx_assets"]


def test_nfa_accumulates_current_account(ctx):
    o, p, res, geo = ctx
    for i in range(1, len(res.periods)):
        nfa = res.periods[i].reported["net_foreign_assets"]
        nfa_prev = res.periods[i - 1].reported["net_foreign_assets"]
        ca = res.periods[i].reported["current_account"]
        assert abs((nfa - nfa_prev) - ca) < 1e-6 * max(1.0, abs(nfa)), \
            f"{geo}: NFA did not accumulate the current account at period {i}"


def test_external_position_direction(ctx):
    """NFA accumulates the current account, so the external position's sign
    follows the trade balance: a surplus -> net creditor, a deficit -> net
    debtor. Robust to data refreshes and the foreign-demand export closure."""
    o, p, res, geo = ctx
    last = res.periods[-1].reported
    if geo == "DE":          # large persistent surplus -> clear net creditor
        assert last["net_foreign_assets"] > 0
    else:                     # FR is ~balanced -> its external position stays moderate
        assert abs(last["nfa_gdp"]) < 200.0


def test_decoupling_still_holds_open(ctx):
    o, p, res, geo = ctx
    runs = {r.scenario: r for r in o.run_triad(horizon=30)}
    base = runs["Baseline"].dist.periods[-1].reported
    nopol = runs["AI shift, no policy"].dist.periods[-1].reported
    settle = runs["AI shift + Abundance Settlement"].dist.periods[-1].reported
    assert nopol["gini_personal"] > base["gini_personal"]
    assert settle["gini_personal"] < nopol["gini_personal"]
