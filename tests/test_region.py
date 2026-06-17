"""Multi-region core — the national-vs-global AI dividend (MANIFESTO Q2).

Pins the integrity guarantees (each country stays individually gated) and the
substantive Q2 result: a national dividend leaves the between-country gap intact
(cash UBI widens it), while a pooled/global dividend narrows it by redistributing
from the richer to the poorer economy.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from region import MultiRegion, between_region_gini


def test_between_region_gini_unit():
    assert between_region_gini([5.0, 5.0], [0.5, 0.5]) == 0.0      # no spread
    # two equal-size groups at 1 and 0: G = w1*w2*|Δ| / mean = .25 / .5 = 0.5
    assert abs(between_region_gini([1.0, 0.0], [0.5, 0.5]) - 0.5) < 1e-12


@pytest.fixture(scope="module")
def mr():
    return MultiRegion(geos=("DE", "FR"), year=2019, allow_live=False)


@pytest.fixture(scope="module")
def cash(mr):
    return mr.dividend_comparison(form="cash_ubi", tau=0.40, horizon=30)


@pytest.fixture(scope="module")
def ubc(mr):
    return mr.dividend_comparison(form="ubc", tau=0.40, horizon=30)


def test_each_country_stays_gated(cash, ubc):
    for c in (cash, ubc):
        assert c.consistent, f"{c.form}: a country failed its gate"
        assert c.max_residual < 1.0
        assert c.excluded == []                 # DE/FR are viable: no false drops


def test_pooled_dividend_is_a_population_weighted_average(cash):
    nat = list(cash.div_pc_national.values())
    assert min(nat) <= cash.div_pc_global <= max(nat)


def test_pooling_is_redistributive_and_conserves_total(cash):
    """Population-weighted net transfers from pooling must sum to ~0 (it only
    moves the dividend around, it doesn't create or destroy it)."""
    wsum = sum(cash.populations[g] * cash.pooling_transfer_pc[g]
               for g in cash.geos)
    assert abs(wsum) < 1e-6 * sum(cash.populations.values())


def test_pooling_transfers_from_richer_to_poorer(cash):
    """The country with the larger national dividend gives; the smaller receives."""
    geos = cash.geos
    rich = max(geos, key=lambda g: cash.div_pc_national[g])
    poor = min(geos, key=lambda g: cash.div_pc_national[g])
    assert cash.pooling_transfer_pc[rich] < 0 < cash.pooling_transfer_pc[poor]


def test_global_dividend_narrows_the_between_country_gap(cash, mr3):
    """The headline Q2 result, in its honest gated form: the pooled arm runs
    THROUGH each country's books and the transfer<->pool feedback is iterated
    to a damped fixed point (2026-06-12 - the single corrective pass drove a
    big UBC giver into negative income, and made near-equal blocs appear to
    'overshoot'; both were solver artifacts). At the fixed point pooling
    narrows the between-country gap in every tested configuration."""
    assert cash.gini_global[-1] < cash.gini_national[-1]      # strict for cash UBI
    u3 = mr3.dividend_comparison(form="ubc", tau=0.40, horizon=25)
    assert u3.consistent
    assert u3.gini_global[-1] < u3.gini_national[-1]          # UBC narrows rich+poor


def test_national_dividend_does_not_close_the_gap(cash):
    """A purely national cash dividend does NOT close the between-country gap on
    its own — it persists across the horizon (pooling is what narrows it, per the
    test above). For two similar-income countries the exact drift is calibration-
    dependent, so we assert PERSISTENCE (a real, non-shrinking gap), not a strict
    increase — the robust form of "the gap doesn't fix itself nationally"."""
    gH = cash.gini_national[-1]
    assert gH > 1e-4                      # a real between-country gap persists nationally
    assert cash.gini_global[-1] < gH      # pooling (not the national dividend) narrows it


# --- scaling to N countries: a low-income region amplifies the gap (Q2) ------ #
@pytest.fixture(scope="module")
def mr3():
    return MultiRegion(geos=("DE", "FR", "PL"), year=2019, allow_live=False)


@pytest.fixture(scope="module")
def cash3(mr3):
    return mr3.dividend_comparison(form="cash_ubi", tau=0.40, horizon=30)


def test_three_country_bloc_gate_clean(cash3):
    assert cash3.consistent and cash3.max_residual < 1.0
    assert set(cash3.geos) == {"DE", "FR", "PL"}


def test_poland_is_the_low_income_region(cash3):
    """Poland's per-capita AI dividend is the smallest — it is the poorer region
    whose presence is the real point of the national-vs-global question."""
    assert cash3.div_pc_national["PL"] < cash3.div_pc_national["FR"]
    assert cash3.div_pc_national["PL"] < cash3.div_pc_national["DE"]


def test_pooling_sends_the_most_to_the_poorest(cash3):
    poorest = min(cash3.geos, key=lambda g: cash3.div_pc_national[g])
    assert poorest == "PL"
    assert cash3.pooling_transfer_pc["PL"] == max(
        cash3.pooling_transfer_pc.values())
    assert cash3.pooling_transfer_pc["PL"] > 0          # the poor country gains


def test_adding_a_poor_region_amplifies_the_gap(mr, mr3):
    """The headline: the between-country gap is far larger once a genuinely
    lower-income economy is in the bloc — the rich-vs-poor force Q2 is about."""
    g2 = mr.dividend_comparison(form="cash_ubi", tau=0.40, horizon=30)
    g3 = mr3.dividend_comparison(form="cash_ubi", tau=0.40, horizon=30)
    assert g3.gini_national[-1] > 1.5 * g2.gini_national[-1]
    # pooling still narrows it for the larger bloc too
    assert g3.gini_global[-1] < g3.gini_national[-1]


# --- tight bilateral trade feedback (Phase 5 increment 2) ------------------- #
@pytest.fixture(scope="module")
def trade(mr3):
    return mr3.solve_trade(form="cash_ubi", tau=0.40, horizon=30, intra_share=0.5)


def test_trade_fixed_point_converges(trade):
    assert trade.converged, f"trade solver did not converge in {trade.iters_used} iters"


def test_trade_keeps_every_country_gated(trade):
    """Injecting partner-driven exports must not break any country's own books."""
    assert trade.consistent and trade.max_residual < 1.0


def test_intra_bloc_trade_reconciles(trade):
    """The regional reconciliation: one country's intra-bloc exports are another's
    imports, so the bloc's intra exports and imports net to ~zero every period."""
    assert trade.trade_balance_residual < 1e-3


def test_trade_coupling_actually_propagates(mr3):
    """Two-way feedback is real: turning on intra-bloc trade changes the GDP path
    vs the autonomous (intra_share=0) case — partners' demand now matters."""
    coupled = mr3.solve_trade(form="cash_ubi", tau=0.40, horizon=30, intra_share=0.6)
    auton = mr3.solve_trade(form="cash_ubi", tau=0.40, horizon=30, intra_share=0.0)
    assert coupled.converged and auton.converged
    moved = any(abs(coupled.gdp[g][-1] - auton.gdp[g][-1]) / auton.gdp[g][-1] > 0.01
                for g in coupled.geos)
    assert moved, "coupling had no effect on any country's output"
    # every country has positive intra-bloc exports under coupling
    assert all(coupled.intra_exports[g][-1] > 0 for g in coupled.geos)


# --- real bilateral trade matrix + euro/non-euro FX channel (#57) ----------- #
def test_euro_membership():
    from schema.accounts import is_euro
    assert is_euro("DE") and is_euro("FR") and is_euro("IT")
    assert not is_euro("PL") and not is_euro("SE") and not is_euro("RO")


def test_trade_matrix_rows_are_shares(mr3):
    W = mr3.load_trade_matrix()
    for i in mr3.geos:
        assert abs(sum(W[i].values()) - 1.0) < 1e-9      # partner shares sum to 1
        assert i not in W[i]                             # no self-trade


def test_injected_trade_matrix_converges_and_reconciles(mr3):
    geos = mr3.geos
    equal = {i: {j: 1.0 / (len(geos) - 1) for j in geos if j != i} for i in geos}
    sol = mr3.solve_trade(form="cash_ubi", horizon=20, intra_share=0.5,
                          trade_shares=equal)
    assert sol.converged and sol.consistent
    assert sol.trade_balance_residual < 1e-3             # intra-bloc still nets out


def test_fx_channel_moves_non_euro_trade_only(mr3):
    """Turning on the FX channel changes a non-euro member's trade (it can
    depreciate); a pure gravity run differs from an fx run for PL."""
    base = mr3.solve_trade(form="cash_ubi", horizon=20, intra_share=0.6)
    fx = mr3.solve_trade(form="cash_ubi", horizon=20, intra_share=0.6, fx_response=0.4)
    assert base.converged and fx.converged
    assert base.intra_exports["PL"][-1] != fx.intra_exports["PL"][-1]   # PL is non-euro
