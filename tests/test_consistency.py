"""The gate must (a) pass clean books and (b) CATCH a deliberate leak.

The leak tests reproduce the class of bug that killed the v0 prototype and
prove the checker would have blocked it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.interface import PeriodState
from consistency.checks import check_period

SFM = {"money": "money_chg"}


def test_clean_books_pass():
    """A genuinely balanced period (every column and row sums to zero).

    workers: wages 100, tax 10, consume 90  -> dM_w = 0
    owners:  profits 20, consume 15         -> dM_k = 5
    firms:   revenue 90+15+15 = 120 = wages 100 + profits 20
    gov:     spends 15, taxes 10 (deficit 5) -> issues money 5
    """
    M_w0, M_k0 = 50.0, 70.0
    tfm = {
        "wages": {"hh_workers": 100.0, "firms": -100.0},
        "profits": {"hh_owners": 20.0, "firms": -20.0},
        "consumption": {"firms": 105.0, "hh_workers": -90.0, "hh_owners": -15.0},
        "gov_expenditure": {"firms": 15.0, "government": -15.0},
        "tax_income": {"government": 10.0, "hh_workers": -10.0},
        "money_chg": {"hh_workers": 0.0, "hh_owners": -5.0, "government": 5.0},
    }
    prev = PeriodState(2019, bsm={"money": {"hh_workers": M_w0, "hh_owners": M_k0,
                                            "government": -(M_w0 + M_k0)}})
    cur = PeriodState(
        2020, tfm=tfm,
        bsm={"money": {"hh_workers": M_w0, "hh_owners": M_k0 + 5.0,
                       "government": -(M_w0 + M_k0 + 5.0)}},
        reported={"gdp": 135.0},
    )
    rep = check_period(cur, prev, stock_flow_map=SFM)
    assert rep.passed, [(c.name, c.detail) for c in rep.failures()]


def test_stock_flow_leak_is_caught():
    """Owners' money rises by 10 but no flow accounts for it -> a leak."""
    M_w0, M_k0 = 50.0, 70.0
    tfm = {
        "wages": {"hh_workers": 100.0, "firms": -100.0},
        "consumption": {"firms": 100.0, "hh_workers": -100.0},
        "money_chg": {"hh_workers": 0.0, "hh_owners": 0.0, "government": 0.0},
    }
    prev = PeriodState(2019, bsm={"money": {"hh_workers": M_w0, "hh_owners": M_k0,
                                            "government": -(M_w0 + M_k0)}})
    cur = PeriodState(
        2020, tfm=tfm,
        bsm={"money": {"hh_workers": M_w0, "hh_owners": M_k0 + 10.0,
                       "government": -(M_w0 + M_k0)}},
        reported={"gdp": 100.0},
    )
    rep = check_period(cur, prev, stock_flow_map=SFM)
    assert not rep.passed
    failed = {c.name for c in rep.failures()}
    assert "stock_flow_articulation" in failed
    assert "balance_sheet_closure" in failed


def test_column_budget_leak_is_caught():
    """A sector spends money that doesn't come from anywhere."""
    tfm = {
        "wages": {"hh_workers": 100.0, "firms": -100.0},
        "consumption": {"firms": 120.0, "hh_workers": -120.0},
        "money_chg": {"hh_workers": 0.0, "firms": 0.0},
    }
    cur = PeriodState(2020, tfm=tfm,
                      bsm={"money": {"hh_workers": 0.0, "government": 0.0}},
                      reported={"gdp": 100.0})
    rep = check_period(cur, None, stock_flow_map=SFM)
    assert not rep.passed
    assert "column_budget" in {c.name for c in rep.failures()}


# --- law 6: economic plausibility (sanity, not just accounting) ------------- #
def _balanced_state(reported):
    """A trivially balanced one-sector period (empty books) carrying `reported`,
    so only the plausibility law can fail."""
    from modules.interface import PeriodState
    return PeriodState(year=2030, tfm={}, bsm={}, reported=reported)


def test_plausibility_passes_sane_numbers():
    st = _balanced_state({"gdp": 3.5e6, "consumption": 2e6, "investment": 7e5,
                          "capital": 1e7, "hh_disposable": 3e6, "gini": 0.30,
                          "swf_share": 0.4, "owners_capital_share": 0.6})
    rep = check_period(st, stock_flow_map=SFM)
    assert rep.passed
    assert next(c for c in rep.checks if c.name == "economic_plausibility").passed


def test_plausibility_catches_nonfinite_and_explosions():
    for bad in ({"gdp": float("inf")},
                {"gdp": float("nan")},
                {"gdp": 3.2e233},                    # the Luxembourg blow-up
                {"gdp": 3.5e6, "consumption": -1e5}, # negative level
                {"gdp": 3.5e6, "swf_share": 1.4},    # share out of [0,1]
                {"gdp": 3.5e6, "gini": -0.2}):
        rep = check_period(_balanced_state(bad), stock_flow_map=SFM)
        plaus = next(c for c in rep.checks if c.name == "economic_plausibility")
        assert not plaus.passed, f"should have flagged {bad}"
        assert not rep.passed


def test_plausibility_catches_explosive_growth():
    prev = _balanced_state({"gdp": 3.5e6})
    cur = _balanced_state({"gdp": 3.5e6 * 500})       # 500x in one period
    rep = check_period(cur, prev_state=prev, stock_flow_map=SFM)
    assert not rep.passed
