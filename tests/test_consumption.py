"""Phase 7 step E5 (2026-10-31): both classes' propensities to consume are
solved from 2019 consumption and the published wage/profit consumption gap
(Onaran & Obst 2016; Kaczmarski 2024 for PL), with owners consuming out of
income net of depreciation on the capital they own."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from consistency.checks import check_run
from data.connectors.consumption import (DIFFERENTIAL, EU15_MEDIAN, EU15_RANGE,
                                         consumption_differential_for)
from modules.sfc_core import MAX_WORKERS_MPC, SFCCore
from orchestrator import AgoraOrchestrator
from schema.accounts import AGGREGATE_GEOS
from scout.checks import snapshot_geos
from scenarios import make_triad
from uncertainty import LEGACY_PRIORS, PRIORS, core_kwargs

MEMBERS = [g for g in snapshot_geos() if g.upper() not in AGGREGATE_GEOS]


def _orch(geo, **kw):
    o = AgoraOrchestrator(geo=geo, allow_live=False, strict=True, **kw)
    o.load_data()
    return o


def _no_policy(o):
    return o.run_scenario(make_triad(o.params())[1]).result


def test_published_estimates_and_their_ranges():
    assert consumption_differential_for("DE")["value"] == -0.397
    assert consumption_differential_for("PL")["value"] == -0.255
    assert "Kaczmarski" in consumption_differential_for("PL")["source"]
    sk = consumption_differential_for("SK")
    assert sk["flag"] == "eu15_median" and sk["value"] == EU15_MEDIAN == -0.323
    assert consumption_differential_for("SK", -1.0)["value"] == EU15_RANGE[0] == -0.564
    assert consumption_differential_for("SK", 1.0)["value"] == EU15_RANGE[1] == -0.151
    assert consumption_differential_for("DE", 1.0)["value"] == pytest.approx(-0.297)
    assert len(DIFFERENTIAL) == 15 and all(v < 0 for v, _ in DIFFERENTIAL.values())


@pytest.mark.parametrize("geo", MEMBERS)
def test_year0_reproduces_and_the_gap_is_the_published_one(geo):
    o = _orch(geo)
    res = _no_policy(o)
    m, y0 = res.meta, res.periods[0].reported
    tgt = o.params().targets
    assert y0["consumption"] == pytest.approx(tgt["hh_consumption"], rel=1e-9)
    assert y0["gdp"] == pytest.approx(tgt["gdp_expenditure"], rel=1e-9)
    a1_w, a1_k = m["workers_mpc"], m["owners_mpc"]
    assert 0.5 < a1_w <= MAX_WORKERS_MPC and 0.2 < a1_k < 1.0, (geo, a1_w, a1_k)
    pr = m["params"]
    gap = a1_k * (1 - m["foreign_stake0"]) * (1 - pr["theta_k"]) - a1_w * (1 - pr["theta_w"])
    assert gap == pytest.approx(m["consumption_differential"], abs=1e-9)
    if "workers_capped" in m["consumption_differential_flag"]:
        assert a1_w == MAX_WORKERS_MPC                    # EL, RO, SK: 2019 dissaving
    else:
        assert gap == pytest.approx(consumption_differential_for(geo)["value"], abs=1e-9)
    assert not any(c.name == "owners_mpc_in_unit_interval"
                   for r in check_run(res, plausibility="audit") for c in r.advisories())


def test_only_the_dissaving_economies_are_capped():
    capped = sorted(g for g in MEMBERS
                    if "workers_capped" in _no_policy(_orch(g)).meta["consumption_differential_flag"])
    assert capped == ["EL", "RO", "SK"]


def test_de_gap_halves_the_old_one_and_workers_save_like_households():
    m = _no_policy(_orch("DE")).meta
    assert m["workers_mpc"] == pytest.approx(0.869, abs=0.002)
    assert m["owners_mpc"] == pytest.approx(0.389, abs=0.002)
    # step E3 had 0.95 / 0.04: a gap of -0.73 against the estimated -0.40
    # DE households save 17.9% gross, ~11% net of depreciation (Eurostat nasa_10_ki, 2019)
    assert 0.10 < 1 - m["workers_mpc"] < 0.18


def test_override_and_monte_carlo_draw():
    o = _orch("DE")
    scen = make_triad(o.params())[1]
    base = SFCCore().run(scen, o._data).meta
    flat = SFCCore(consumption_differential=-0.15).run(scen, o._data).meta
    assert flat["consumption_differential_flag"] == "override"
    assert flat["owners_mpc"] > base["owners_mpc"] and flat["workers_mpc"] < base["workers_mpc"]
    lo = SFCCore(consumption_draw=-1.0).run(scen, o._data).meta
    assert lo["consumption_differential"] == pytest.approx(-0.497)
    assert "consumption_draw" in PRIORS and "a1_w" not in PRIORS and "a1_w" in LEGACY_PRIORS
    assert core_kwargs({"consumption_draw": 0.3})["consumption_draw"] == 0.3


def test_legacy_closure_keeps_the_residual():
    o = _orch("DE", investment_closure="legacy")
    m = _no_policy(o).meta
    assert m["workers_mpc"] == 0.95 and m["owners_mpc"] == o.params().a1_k
    assert m["consumption_differential"] is None
