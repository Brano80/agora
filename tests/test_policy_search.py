"""Phase 4 — policy search & the Pareto frontier.

Pins the integrity guarantees (every candidate is gated; the frontier is built
only from consistent points; dominance logic is correct) AND the project's
"no single best" principle (the frontier is multi-membered and spans more than
one policy FORM, so the values judgement genuinely stays with the user).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from orchestrator import AgoraOrchestrator
from policy_search import _dominates, pareto_front, PolicyPoint, OBJECTIVES


@pytest.fixture(scope="module")
def points():
    o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True)
    o.load_data()
    return o.run_policy_search(horizon=30)


def test_every_candidate_is_gated(points):
    assert points
    for p in points:
        assert p.consistent, f"{p.name} failed the gate"
        assert p.max_residual < 1.0


def test_frontier_is_a_proper_nonempty_subset(points):
    front = [p for p in points if p.on_frontier]
    assert front, "frontier must not be empty"
    assert len(front) < len(points), "if everything is optimal, nothing is"


def test_frontier_is_internally_non_dominated(points):
    front = [p for p in points if p.on_frontier]
    for a in front:
        for b in front:
            if a is not b:
                assert not _dominates(a.objectives, b.objectives)


def test_every_dominated_point_is_covered_by_the_frontier(points):
    front = [p for p in points if p.on_frontier]
    for p in points:
        if not p.on_frontier:
            assert any(_dominates(f.objectives, p.objectives) for f in front), \
                f"{p.name} is off-frontier but nothing dominates it"


def test_no_single_best_multiple_optima(points):
    """The crux principle: the frontier offers several non-dominated options (no
    single policy wins on every objective) and excludes 'do nothing'. With the
    fiscal block corrected (F9), UBC dominates cash UBI on the trade-offs, so the
    frontier is several UBC INTENSITIES — the remaining choice is how aggressive
    the levy is (low τ = least debt/most poverty; high τ = most growth/volatility)."""
    front = [p for p in points if p.on_frontier]
    assert len(front) >= 2                          # no single best
    assert all(p.form != "none" for p in front)     # doing nothing is dominated
    assert any(p.form == "ubc" for p in front)


def test_doing_nothing_is_dominated(points):
    nop = next(p for p in points if p.form == "none")
    assert not nop.on_frontier


def test_dominance_logic_unit():
    keys = [k for k, _ in OBJECTIVES]
    good = {k: 1.0 for k in keys}
    bad = {k: 0.0 for k in keys}
    tie = {k: 1.0 for k in keys}
    assert _dominates(good, bad)
    assert not _dominates(bad, good)
    assert not _dominates(good, tie)            # equal on all -> no strict dominance
    better_one = dict(good); better_one[keys[0]] = 2.0
    assert _dominates(better_one, good)         # >= on all, strictly > on one
    trade = dict(good); trade[keys[0]] = 2.0; trade[keys[1]] = 0.0
    assert not _dominates(trade, good)          # genuine trade-off -> neither way
    assert not _dominates(good, trade)


def test_pareto_front_ignores_inconsistent_points():
    keys = [k for k, _ in OBJECTIVES]
    win = PolicyPoint("ubc", 0.4, "win", True, 0.0,
                      objectives={k: 9.0 for k in keys})
    ghost = PolicyPoint("ubc", 0.9, "ghost", False, 5.0,
                        objectives={k: 99.0 for k in keys})   # better but FAILED gate
    front = pareto_front([win, ghost])
    assert win in front and ghost not in front                # gate gates the search


def test_phase6_fiscal_block_makes_debt_a_realistic_objective():
    """Phase 6: running the policy search with the proper fiscal block (broad base
    + fiscal-reaction) makes the 'fiscal' objective REALISTIC — debt is controlled,
    not a stub runaway — and reveals that a responsive government can make ANY of
    the policies fiscally sustainable. Fiscal sustainability thus stops being the
    binding trade-off; the real choices are equality/growth/poverty (UBC wins)."""
    from orchestrator import AgoraOrchestrator

    def run(fiscal_on):
        kw = dict(capital_tax_share=0.2, fiscal_reaction=0.01) if fiscal_on else {}
        o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True, **kw)
        o.load_data()
        pts = o.run_policy_search(horizon=30)
        assert all(p.consistent for p in pts)                       # gate holds both ways
        return [p.metrics["debt_gdp"] for p in pts], pts

    d_off, _ = run(False)
    d_on, pts_on = run(True)
    assert max(d_on) < min(d_off)                                   # block controls debt vs runaway
    assert (max(d_on) - min(d_on)) < (max(d_off) - min(d_off))      # fiscal axis compresses
    assert any(p.on_frontier and p.form == "ubc" for p in pts_on)   # UBC still on the frontier
