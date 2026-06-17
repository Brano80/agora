"""AI-shock driver: lever-path construction, adoption shapes, and a custom
scenario through the full gate."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from orchestrator import AgoraOrchestrator
from scenarios import make_triad, build_custom, LS_AI_END
from modules.ai_shock import AIShock, Policy, to_scenario, _labour_share_path


@pytest.fixture(scope="module")
def params():
    o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False)
    o.load_data()
    return o.params(), o


def test_baseline_holds_labour_share(params):
    p, _ = params
    s = to_scenario(p, AIShock("Baseline", labour_share_end=None,
                               capex_growth=0.015), Policy("baseline"))
    assert abs(s.labour_share.at(0, 30) - s.labour_share.at(29, 30)) < 1e-9
    assert abs(s.labour_share.at(0, 30) - p.ls0) < 1e-9


def test_ai_shift_ramps_labour_share_down(params):
    p, _ = params
    s = to_scenario(p, AIShock("AI shift", labour_share_end=LS_AI_END,
                               capex_growth=0.06), Policy("no policy"))
    assert abs(s.labour_share.at(0, 30) - p.ls0) < 1e-9          # starts at baseline
    assert abs(s.labour_share.at(29, 30) - LS_AI_END) < 1e-9     # ends at target
    assert s.labour_share.at(29, 30) < s.labour_share.at(0, 30)  # falls
    # capex grows
    assert s.ai_capex.at(10, 30) > s.ai_capex.at(0, 30)


def test_scurve_endpoints_exact(params):
    p, _ = params
    lp = _labour_share_path(p, AIShock("AI shift", labour_share_end=0.30,
                                       adoption="scurve"))
    assert abs(lp.at(0, 30) - p.ls0) < 1e-9
    assert abs(lp.at(29, 30) - 0.30) < 1e-9
    # monotone decreasing
    vals = [lp.at(t, 30) for t in range(30)]
    assert all(vals[i] >= vals[i + 1] - 1e-9 for i in range(29))


def test_custom_scenario_runs_and_gates(params):
    p, o = params
    cs = build_custom(p, labour_share_end=0.45, capex_growth=0.04,
                      capital_tax=0.25, ubi=True, name="Custom")
    run = o.run_scenario(cs)
    assert run.consistent
    assert run.dist is not None
    last = run.dist.periods[-1].reported
    # a partial settlement lands between baseline and full no-policy on inequality
    assert 0.25 < last["gini_personal"] < 0.55


def test_triad_built_via_driver(params):
    p, _ = params
    names = [s.name for s in make_triad(p)]
    assert names == ["Baseline", "AI shift, no policy",
                     "AI shift + Abundance Settlement"]


# --- Acemoglu-Restrepo task block: labour share EMERGES from automation (#55) - #
def test_task_block_labour_share_emerges(params):
    """With automation/reinstatement rates set, the wage share starts at the
    baseline, falls monotonically as tasks are displaced, and converges to the
    steady-state floor ls0·(1 - a/(a+r)) — no assumed end-point."""
    from modules.ai_shock import AIShock, _labour_share_path
    p, _ = params
    a, r = 0.06, 0.02
    lp = _labour_share_path(p, AIShock(automation_rate=a, reinstatement_rate=r))
    path = [lp.at(t, 60) for t in range(60)]
    assert abs(path[0] - p.ls0) < 1e-9                 # starts at baseline
    assert all(b <= a_ + 1e-9 for a_, b in zip(path, path[1:]))  # monotone down
    floor = p.ls0 * (1.0 - a / (a + r))
    assert abs(path[-1] - floor) < 0.02                # converges to the A-R floor


def test_task_block_faster_automation_falls_further(params):
    from modules.ai_shock import AIShock, _labour_share_path
    p, _ = params
    slow = _labour_share_path(p, AIShock(automation_rate=0.04, reinstatement_rate=0.03))
    fast = _labour_share_path(p, AIShock(automation_rate=0.10, reinstatement_rate=0.02))
    assert fast.at(29, 30) < slow.at(29, 30)           # more automation -> lower share
