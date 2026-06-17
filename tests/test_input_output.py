"""Input-output module (Phase 3): sectoral value added reconciles to GDP, the
Leontief identity holds, and the AI shock concentrates the labour-share fall in
high-automation-exposure sectors. DE + FR, offline."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from orchestrator import AgoraOrchestrator
from consistency.checks import check_input_output
from modules.input_output import load_io


@pytest.fixture(scope="module", params=["DE", "FR"])
def runs(request):
    o = AgoraOrchestrator(geo=request.param, year=2019, allow_live=False, strict=True)
    o.load_data()
    return {r.scenario: r for r in o.run_triad(horizon=30)}, request.param


def test_io_present_and_reconciles_to_gdp(runs):
    data, geo = runs
    for name, run in data.items():
        assert run.io is not None and run.io.periods, f"{geo}/{name}: no I-O result"
        reps = check_input_output(run.io)
        worst = max(r.max_residual for r in reps)
        assert all(r.passed for r in reps), f"{geo}/{name}: I-O reconcile {worst:.3e}"


def test_leontief_identity(runs):
    """x_s == Σ_j A[s][j] x_j + f_s. Uses the REAL A matrix when present
    (Eurostat naio via the figaro connector), else the legacy supply-shares
    construction A[i][j] = (1-va[j])*supply[i]."""
    data, geo = runs
    io = load_io(geo)
    n = len(io["sectors"])
    A = io.get("A") or [[(1 - io["va_coeff"][j]) * io["supply_shares"][i]
                         for j in range(n)] for i in range(n)]
    rep = data["Baseline"].io.periods[0].reported
    Y = rep["gdp_ref"]
    x = [rep[f"output_{s+1}"] for s in range(n)]
    f = [io["final_demand_shares"][s] * Y for s in range(n)]
    for s in range(n):
        lhs = x[s]
        rhs = sum(A[s][j] * x[j] for j in range(n)) + f[s]
        assert abs(lhs - rhs) < 1e-3 * max(1.0, abs(Y)), f"{geo}: Leontief row {s}"


def test_ai_shock_concentrates_in_exposed_sectors(runs):
    data, geo = runs
    base = data["Baseline"].io.periods[-1].reported
    nopol = data["AI shift, no policy"].io.periods[-1].reported
    # sector indices: 2 = Construction (low exposure 0.2), 4 = ICT/fin/bus (high 0.9)
    drop_construction = base["lshare_3"] - nopol["lshare_3"]
    drop_ict = base["lshare_5"] - nopol["lshare_5"]
    assert drop_ict > drop_construction, \
        f"{geo}: AI shock should hit ICT harder than construction"
    # the exposed-sector VA share is reported and in (0, 1)
    assert 0.0 < nopol["ai_exposed_va_share"] < 1.0
