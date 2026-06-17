"""Historical backtest + parameter grounding (#54). Offline tests exercise the
OLS, the cross-section β fit, the Epoch-grounded anchors, and the harness
mechanics; the real multi-year validation runs live on the user's machine."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest import (_ols, load_panel, backtest, estimate_beta_cross_section,
                      ground_ai_shock)


def test_ols_recovers_known_line():
    xs = [0, 1, 2, 3, 4]
    ys = [1 + 2 * x for x in xs]            # y = 1 + 2x
    b, a, r2 = _ols(xs, ys)
    assert abs(b - 2.0) < 1e-9 and abs(a - 1.0) < 1e-9 and abs(r2 - 1.0) < 1e-9


def test_cross_section_beta_runs_offline():
    b, a, r2, n = estimate_beta_cross_section(["DE", "FR", "PL", "RO", "BG"], 2019)
    assert n == 5
    assert b == b and a == a                # finite (not NaN) with >=2 points


def test_ground_ai_shock_is_sane_and_sourced():
    g = ground_ai_shock()
    assert 0.0 < g["capex_growth"] <= 0.10           # damped from raw compute growth
    assert 0.30 <= g["labour_share_end"] <= 0.60
    assert "rationale" in g and g["raw_compute_growth_per_yr"] > 0


def test_backtest_needs_a_multiyear_panel():
    panel = load_panel("DE", [2019], allow_live=False)   # offline -> one year
    r = backtest("DE", panel)
    assert r.n_years == 1 and "need" in r.note            # degenerate, flagged


def test_backtest_runs_on_a_panel_and_scores_outcomes():
    """Synthetic 2-year panel exercises the compare path: the harness drives the
    model with the actual labour-share/investment paths and scores GDP error."""
    from data.connectors.dbnomics import DBnomicsConnector
    d0 = {k: v["value"] for k, v in DBnomicsConnector(allow_live=False).fetch("DE", 2019).items()}
    d1 = dict(d0); d1["gdp"] = d0["gdp"] * 1.02          # +2% next year
    d1["hh_consumption"] = d0["hh_consumption"] * 1.02
    panel = {2019: d0, 2020: d1}
    r = backtest("DE", panel)
    assert r.n_years == 2
    assert "gdp" in r.mae_pct and r.mae_pct["gdp"] >= 0.0


def test_beta_panel_fixed_effects_recovers_slope():
    """Two synthetic countries share slope 0.7 but have different LEVELS
    (fixed effects); the within-country estimator must recover the slope the
    pooled cross-section would miss."""
    from backtest import estimate_beta_panel
    years = list(range(2010, 2020))
    panels = {}
    for g, (x0, c) in {"AA": (0.30, 0.20), "BB": (0.40, 0.45)}.items():
        panels[g] = {y: {"labour_share": 100.0 * (1.0 - (x0 + 0.004 * i)),
                         "gini_disp_income": 100.0 * (c + 0.7 * (x0 + 0.004 * i))}
                     for i, y in enumerate(years)}
    b, r2, n, nc = estimate_beta_panel(["AA", "BB"], years, panels=panels)
    assert abs(b - 0.7) < 1e-9 and r2 > 0.999 and n == 20 and nc == 2


# --- beta identification via the MARKET Gini (OECD IDD) — closes F12 -------- #
def test_redistribution_wedge_quantifies_the_welfare_state():
    """The wedge = 1 - disposable/market Gini is the share of market inequality
    removed by taxes & transfers — large and positive, and the reason a
    disposable-Gini beta is biased toward zero."""
    from backtest import redistribution_wedge
    per, mean = redistribution_wedge(["DE", "FR"])
    assert set(per) == {"DE", "FR"}
    assert all(0.2 < w < 0.6 for w in per.values())     # ~30-45% for DE/FR
    assert 0.2 < mean < 0.6


def test_market_cross_section_runs_and_is_diagnostic_only():
    """The market cross-section removes the redistribution confound but the tiny
    between-country sample is structurally heterogeneous — it runs, but is not a
    valid identification (documented; we don't assert a sign)."""
    from backtest import estimate_beta_market_cross_section
    b, a, r2, n = estimate_beta_market_cross_section(
        ["DE", "FR", "IT", "ES", "NL", "PL"])
    assert n == 6
    assert b == b and a == a                             # finite


def test_market_panel_fe_recovers_slope():
    """Within-country FE on the MARKET Gini recovers a shared slope despite
    different national levels — the correct identification once a market-Gini
    time series exists (live IDD pull). Proven here on an injected panel."""
    from backtest import estimate_beta_market_panel
    years = list(range(2010, 2020))
    panels = {}
    for g, (x0, c) in {"AA": (0.30, 0.35), "BB": (0.42, 0.55)}.items():
        panels[g] = {y: {"capital_share": x0 + 0.004 * i,
                         "gini_market": c + 0.8 * (x0 + 0.004 * i)}
                     for i, y in enumerate(years)}
    b, r2, n, nc = estimate_beta_market_panel(["AA", "BB"], years, panels=panels)
    assert abs(b - 0.8) < 1e-9 and r2 > 0.999 and n == 20 and nc == 2


def test_market_panel_without_data_is_honest():
    """No offline market-Gini time series exists (IDD snapshot = one vintage);
    a call that can't source a multi-year market panel skips honestly rather
    than guessing. Network-independent (allow_live=False)."""
    from backtest import estimate_beta_market_panel
    b, r2, n, nc = estimate_beta_market_panel(["DE", "FR"], [2015, 2016, 2017],
                                              allow_live=False)
    assert nc == 0 and n == 0
