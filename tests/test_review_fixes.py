"""Regression tests for the 2026-06-11 code-review fixes."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calibration import calibrate
from consistency.checks import check_period
from modules.interface import PeriodState, Scenario, LeverPath
from data.connectors.dbnomics import DBnomicsConnector


def _data(geo="DE", year=2019):
    rows = DBnomicsConnector(allow_live=False).fetch(geo, year)
    return {k: v["value"] for k, v in rows.items()}


# --- fix 4: calibration refuses pathological structures -------------------- #
def test_calibrate_raises_on_entrepot_structure():
    d = _data()
    # LU-like pathology: a massive external surplus + high wage share makes
    # the residually-solved owners' MPC insane (trade SCALE alone cancels in
    # the closure; the surplus and factor split are what break it).
    d["exports"] = d["gdp"] * 1.5
    d["imports"] = d["gdp"] * 1.0
    d["labour_share"] = 80.0
    try:
        calibrate(d, geo="XX")
    except ValueError as e:
        assert "a1_k" in str(e)
    else:
        raise AssertionError("expected ValueError for entrepot structure")


def test_calibrate_normal_countries_unaffected():
    for geo in ("DE", "FR", "PL"):
        p = calibrate(_data(geo), geo=geo)
        assert 0.0 <= p.a1_k <= 1.0, (geo, p.a1_k)
        assert "a1_k_warning" not in p.notes


# --- fix 11: gate catches a non-financial row that does not net out -------- #
def test_gate_catches_unbalanced_nonfinancial_row():
    st = PeriodState(year=2019, tfm={
        "wages": {"hh_workers": 100.0, "firms": -90.0},   # 10 leaks
    }, bsm={}, reported={"gdp": 100.0})
    rep = check_period(st, stock_flow_map={})
    fails = [c.name for c in rep.failures()]
    assert "row_balance_all_flows" in fails


# --- fix 2: gov_override drives G absolutely in the core ------------------- #
def test_gov_override_drives_absolute_g():
    from modules.sfc_core import SFCCore
    d = _data()
    p = calibrate(d, geo="DE")
    gov = [p.g_ratio * p.Y0 * 1.0] * 5                   # flat absolute path
    scen = Scenario(name="t", horizon=5, geo="DE",
                    labour_share=LeverPath(p.ls0),
                    ai_capex=LeverPath(p.a_ratio0),
                    gov_ratio=LeverPath(9.99),           # would explode if used
                    gov_override=LeverPath(gov),
                    tax_income=LeverPath(p.theta))
    res = SFCCore().run(scen, d)
    for t, per in enumerate(res.periods):
        assert abs(per.reported["gov_expenditure"] - gov[t]) < 1e-6


# --- fix 1: injected trade matrix is the one used in reported intra-exports - #
def test_solve_trade_reports_injected_matrix_exports():
    from region import MultiRegion
    mr = MultiRegion(geos=("DE", "FR", "PL"), allow_live=False)
    geos = mr.geos
    # lopsided matrix: all of everyone's intra-bloc imports come from DE
    lopsided = {i: {j: (1.0 if j == "DE" else 0.0)
                    for j in geos if j != i} for i in geos}
    sol = mr.solve_trade(form="none", horizon=10, intra_share=0.5,
                         trade_shares=lopsided)
    assert sol.converged
    # under the injected matrix FR/PL receive no intra-bloc demand; before the
    # fix the report used gravity weights and showed them positive.
    assert sol.intra_exports["FR"][-1] == 0.0
    assert sol.intra_exports["PL"][-1] == 0.0
    assert sol.intra_exports["DE"][-1] > 0.0


# --- inventories (P52+P53) close the identity, owner-financed, gate-clean --- #
def test_inventories_close_identity_and_books():
    from modules.sfc_core import SFCCore
    from scenarios import make_triad
    from consistency.checks import check_run
    d = _data()
    d["gcf"] = d["gfcf"] + 8099.0            # DE's published P5G - P51G gap
    p = calibrate(d, geo="DE")
    assert abs(p.inv0 - 8099.0) < 1e-6
    assert abs(p.nx_gap) < 1.0               # identity closes to ~0
    res = SFCCore().run(make_triad(p, horizon=5)[0], d)
    assert max(r.max_residual for r in check_run(res, strict=False)) < 1e-3
    assert abs(res.periods[0].reported["inventories"] - 8099.0) < 1e-6
    assert abs(res.periods[0].reported["gdp"] - p.Y0) < 1e-3 * p.Y0


# --- #5: the pooled global dividend goes THROUGH the books (gated) ---------- #
def test_pooled_dividend_is_gated_through_the_books():
    from region import MultiRegion
    mr = MultiRegion(geos=("DE", "PL"), allow_live=False)
    cmp_ = mr.dividend_comparison(form="cash_ubi", tau=0.40, horizon=10)
    assert cmp_.consistent                       # BOTH arms pass the gate now
    assert cmp_.max_residual < 1.0
    # pooling still narrows the rich-poor between-country gap
    assert cmp_.gini_global[-1] < cmp_.gini_national[-1]
    # net transfers sum to ~zero across the bloc (per capita x pop)
    tot = sum(cmp_.pooling_transfer_pc[g] * cmp_.populations[g]
              for g in cmp_.geos)
    scale = sum(cmp_.populations.values())
    assert abs(tot) / scale < 1e-6


# --- intl_transfer lever: books close with a RoW-financed household receipt - #
def test_intl_transfer_books_close():
    from modules.sfc_core import SFCCore
    from scenarios import make_triad
    from consistency.checks import check_run
    d = _data()
    p = calibrate(d, geo="DE")
    scen = make_triad(p, horizon=5)[0]
    scen.intl_transfer = LeverPath(10000.0)      # 10 BEUR/yr from abroad
    res = SFCCore().run(scen, d)
    assert max(r.max_residual for r in check_run(res, strict=False)) < 1e-3
    r0 = res.periods[0].reported
    assert abs(r0["current_account"] - (r0["net_exports"] + 10000.0)) < 1e-6
