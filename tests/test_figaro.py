"""FIGARO connector — offline tests: code classification, the aggregation
math, the real-A module path, and the build validator (all network-free)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.connectors.figaro import sector_of, aggregate_io, SECTORS


def test_sector_classification():
    assert sector_of("A01") == 0 and sector_of("CPA_A02") == 0
    assert sector_of("C10-C12") == 1 and sector_of("D35") == 1 and sector_of("B") == 1
    assert sector_of("F") == 2
    assert sector_of("G45") == 3 and sector_of("H49") == 3
    assert sector_of("J62_J63") == 4 and sector_of("K64") == 4 and sector_of("M69_M70") == 4
    assert sector_of("O84") == 5 and sector_of("Q86") == 5 and sector_of("U") == 5
    # accounting codes must NEVER classify as industries (B1G vs NACE B etc.)
    for bad in ("B1G", "B1GQ", "D1", "D21X31", "P1", "P2", "P51G", "P6",
                "TOTAL", "IMP", "OP_RES", "P3_S14"):
        assert sector_of(bad) is None, bad


def test_aggregation_books_balance():
    """Synthetic 3-industry table: agriculture A01, manufacturing C10, IT J62.
    x = Z rowsums... checks Z/f/x/va aggregation closes x = colsum(Z) + va."""
    cells = {
        ("A01", "A01"): 10, ("A01", "C10"): 20, ("A01", "J62"): 5,
        ("C10", "A01"): 8,  ("C10", "C10"): 50, ("C10", "J62"): 12,
        ("J62", "A01"): 2,  ("J62", "C10"): 15, ("J62", "J62"): 30,
        ("A01", "P3_S14"): 65, ("C10", "P51G"): 120, ("J62", "P6"): 41,
        ("P1", "A01"): 100, ("P1", "C10"): 205, ("P1", "J62"): 88,
        ("B1G", "A01"): 80, ("B1G", "C10"): 120, ("B1G", "J62"): 41,
        ("D1", "A01"): 30,                       # must be ignored (special row)
    }
    agg = aggregate_io(cells)
    Z, f, x, va = agg["Z"], agg["f"], agg["x"], agg["va"]
    assert x[0] == 100 and x[1] == 205 and x[4] == 88        # P1 output row
    assert va[0] == 80 and va[1] == 120 and va[4] == 41      # B1G row
    assert f[0] == 65 and f[1] == 120 and f[4] == 41
    assert Z[1][1] == 50 and Z[0][1] == 20 and Z[4][4] == 30
    assert sum(Z[i][2] for i in range(6)) == 0               # no construction


def test_module_uses_real_A_and_reconciles():
    """A handcrafted io dict WITH a real A must run through the module, use the
    matrix directly, and still reconcile Σ sectoral VA == GDP (the gate)."""
    from orchestrator import AgoraOrchestrator
    from consistency.checks import check_input_output
    import modules.input_output as iom
    n = len(SECTORS)
    A = [[0.05 if i != j else 0.15 for j in range(n)] for i in range(n)]
    io = {"sectors": SECTORS, "A": A,
          "va_coeff": [1.0 - sum(A[i][j] for i in range(n)) for j in range(n)],
          "final_demand_shares": [1.0 / n] * n,
          "labour_share_sector": [0.45, 0.55, 0.62, 0.6, 0.5, 0.7],
          "automation_exposure": [0.3, 0.7, 0.2, 0.5, 0.9, 0.4]}
    orig = iom.load_io
    iom.load_io = lambda g: io
    try:
        o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True)
        o.load_data()
        run = o.run_triad(horizon=5)[0]
    finally:
        iom.load_io = orig
    assert run.io.meta["matrix_source"] == "real"
    reps = check_input_output(run.io)
    assert all(r.passed for r in reps)
    assert all(1.0 <= m <= 5.0 for m in run.io.meta["multipliers"].values())


def test_build_validator_rejects_nonproductive():
    from scripts.build_io import validate_io
    n = len(SECTORS)
    bad = {"sectors": SECTORS,
           "A": [[0.2] * n for _ in range(n)],                # colsums 1.2
           "va_coeff": [0.4] * n, "final_demand_shares": [1.0 / n] * n,
           "labour_share_sector": [0.5] * n,
           "automation_exposure": [0.5] * n}
    ok, fails, _ = validate_io(bad, "DE", 2019)
    assert not ok and any("productive" in f for f in fails)


def test_pick_io_year_prefers_available_benchmark():
    """Symmetric IO tables are benchmark years; an off-benchmark request must
    fall back to the nearest available year (offline-pure logic)."""
    from data.connectors.figaro import _pick_io_year
    # requested present -> kept
    assert _pick_io_year(2015, {2010, 2015, 2020}) == 2015
    # 2019 absent -> nearest not-later-than 2021 -> 2020
    assert _pick_io_year(2019, {2010, 2015, 2020}) == 2020
    # nothing within +2 -> latest available
    assert _pick_io_year(2019, {2010, 2015}) == 2015
    # no availability info -> keep requested (let the caller fail loudly)
    assert _pick_io_year(2019, set()) == 2019


def test_years_in_docs_parses_periods():
    from data.connectors.figaro import _years_in_docs
    docs = [{"period": ["2018", "2019", "2020"], "value": [1.0, None, 3.0]}]
    assert _years_in_docs(docs) == {2018, 2020}        # None dropped


def test_detect_axes_ignores_freq_a_collision():
    """The row/col detector must pick the product axes (*_ava / *_use), NOT the
    'freq' dim whose value 'A' (annual) collides with NACE section A. This was
    the cp1700 '1 wanted row [A], 80 cells' bug (2026-06-14)."""
    from data.connectors.figaro import _detect_axes
    # cp1700-style dims (order matters: freq first, as DBnomics returns it)
    cp1700 = {
        "freq": ["A"], "unit": ["MIO_EUR", "MIO_NAC"],
        "stk_flow": ["DOM", "IMP", "TOTAL"],
        "prd_use": ["CPA_A01", "CPA_C", "CPA_G"],
        "prd_ava": ["CPA_A01", "CPA_C", "CPA_G", "B1G"],
        "geo": ["DE", "FR"],
    }
    row_d, col_d = _detect_axes(cp1700)
    assert (row_d, col_d) == ("prd_ava", "prd_use")
    # cp1750-style (industry x industry)
    cp1750 = {"freq": ["A"], "unit": ["MIO_EUR"], "ind_ava": ["C", "G"],
              "ind_use": ["C", "G"], "stk_flow": ["DOM"], "geo": ["BE"]}
    assert _detect_axes(cp1750) == ("ind_ava", "ind_use")
