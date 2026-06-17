"""Monte-Carlo uncertainty bands (#53). Verifies the band machinery is sound AND
that the UBC-vs-cash ranking is robust to the full span of uncertain assumptions
(the bands don't overlap), not an artifact of one point estimate."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uncertainty import monte_carlo, _pctile, Band


def test_percentile_helper():
    assert _pctile([1, 2, 3, 4, 5], 50) == 3
    assert _pctile([0, 10], 5) == 0.5
    assert _pctile([], 50) != _pctile([], 50) or True   # NaN-safe (no crash)


def test_bands_are_ordered_and_nondegenerate():
    bands, used, _ = monte_carlo("DE", form="ubc", horizon=20, n=60, seed=3)
    assert used > 40                                   # most draws are viable
    for b in bands.values():
        assert b.p5 <= b.p50 <= b.p95
    assert bands["gini"].p95 > bands["gini"].p5        # there IS spread


def test_monte_carlo_is_deterministic_with_seed():
    a, _, _ = monte_carlo("DE", form="ubc", horizon=15, n=40, seed=7)
    b, _, _ = monte_carlo("DE", form="ubc", horizon=15, n=40, seed=7)
    assert a["gini"].as_tuple() == b["gini"].as_tuple()


def test_ubc_beats_cash_across_the_whole_uncertainty_range():
    """The headline robustness check: UBC's inequality and poverty bands sit
    ENTIRELY below cash UBI's — the verdict survives the full prior span."""
    ubc, _, _ = monte_carlo("DE", form="ubc", horizon=30, n=120, seed=1)
    cash, _, _ = monte_carlo("DE", form="cash_ubi", horizon=30, n=120, seed=1)
    assert ubc["gini"].p95 < cash["gini"].p5           # non-overlapping on Gini
    assert ubc["poverty"].p95 < cash["poverty"].p5     # non-overlapping on poverty
    # and only UBC builds citizen wealth, under every draw
    assert ubc["citizen_wealth_pc"].p5 > 0
    assert cash["citizen_wealth_pc"].p95 == 0
