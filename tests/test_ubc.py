"""The pinned experiment — Universal Basic Capital vs cash UBI.

These tests pin BOTH the integrity guarantees (the consistency gate still holds
exactly once the sovereign fund is active) AND the qualitative flow-vs-stock
result the experiment exists to demonstrate (MANIFESTO Q1). They are the
regression guard for the central thesis test, so they assert the SHAPE of the
result, not fragile exact numbers.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from orchestrator import AgoraOrchestrator
from schema.accounts import SECTORS, FLOWS


@pytest.fixture(scope="module")
def runs():
    o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True)
    o.load_data()
    return {r.scenario: r for r in o.run_ubc_experiment(horizon=30)}


def test_schema_layers_active():
    assert SECTORS["sovereign_fund"].active
    assert FLOWS["dividend_swf"].active


def test_all_arms_pass_the_gate(runs):
    """Activating the fund must not open an accounting leak — every arm, every
    period, including the distribution + input-output reconciliations."""
    for name, r in runs.items():
        assert r.consistent, f"{name} failed the consistency gate"
        assert r.max_residual < 1.0, f"{name} residual {r.max_residual:.3e}"


def test_fund_holds_no_money_pure_passthrough(runs):
    """The sovereign fund's profit share equals the dividend it pays, so it
    accumulates capital, never money — money stays a closed gov/household loop."""
    ubc = runs["AI + Universal Basic Capital"]
    for per in ubc.result.periods:
        assert "sovereign_fund" not in per.bsm["money"]
        # capital is split between owners and the fund and still sums to K
        cap = per.bsm["capital"]
        assert abs((cap.get("hh_owners", 0.0) + cap.get("sovereign_fund", 0.0))
                   - per.reported["capital"]) < 1e-6


def test_ubc_builds_endowment_cash_does_not(runs):
    ubc = runs["AI + Universal Basic Capital"].result
    cash = runs["AI + Cash UBI"].result
    stake = [p.reported["swf_stake"] for p in ubc.periods]
    assert stake[-1] > 0
    assert all(b >= a - 1e-6 for a, b in zip(stake, stake[1:]))   # non-decreasing
    assert all(p.reported["swf_stake"] == 0 for p in cash.periods)
    # citizens come to own (almost) the whole capital stock
    share = [p.reported["swf_share"] for p in ubc.periods]
    assert share[0] < 0.10 and share[-1] > 0.5   # citizens come to own a majority
    assert max(share) <= 1.0 + 1e-9


def test_cash_is_pure_flow_ubc_is_the_stock(runs):
    cash = runs["AI + Cash UBI"].result
    ubc = runs["AI + Universal Basic Capital"].result
    # cash arm: a cash UBI pool, never a dividend; UBC arm: the reverse
    assert all(p.reported["ubi"] > 0 for p in cash.periods[1:])
    assert all(p.reported["swf_dividend"] == 0 for p in cash.periods)
    assert all(p.reported["ubi"] == 0 for p in ubc.periods)
    assert ubc.periods[-1].reported["swf_dividend"] > 0


def test_flow_vs_stock_crossover(runs):
    """The defining result: cash UBI helps MORE early (immediate redistribution),
    UBC's compounding dividend overtakes it later — within the horizon."""
    cash = runs["AI + Cash UBI"].result
    ubc = runs["AI + Universal Basic Capital"].result
    H = len(cash.periods)
    # early: the cash transfer exceeds the (still-tiny) UBC dividend
    assert cash.periods[0].reported["transfer_pool"] > ubc.periods[0].reported["swf_dividend"]
    # a crossover year exists strictly inside the horizon
    cross = next((t for t in range(H)
                  if ubc.periods[t].reported["swf_dividend"]
                  > cash.periods[t].reported["transfer_pool"]), None)
    assert cross is not None and 0 < cross < H


def test_ubc_wins_late_on_inequality_and_poverty(runs):
    """By the horizon the endowment dominates: UBC ends more equal and with less
    poverty than cash UBI — while cash UBI is more equal at the start."""
    cash, ubc = runs["AI + Cash UBI"], runs["AI + Universal Basic Capital"]
    g_cash0 = cash.result.periods[0].reported["gini"]
    g_ubc0 = ubc.result.periods[0].reported["gini"]
    assert g_cash0 < g_ubc0                                  # cash wins year 0
    g_cashH = cash.result.periods[-1].reported["gini"]
    g_ubcH = ubc.result.periods[-1].reported["gini"]
    assert g_ubcH < g_cashH                                  # UBC wins by horizon
    p_cashH = cash.dist.periods[-1].reported["poverty_rate"]
    p_ubcH = ubc.dist.periods[-1].reported["poverty_rate"]
    assert p_ubcH <= p_cashH


def test_fr_ubc_also_gate_clean():
    """Country-agnostic: the fund mechanism closes for France too."""
    o = AgoraOrchestrator(geo="FR", year=2019, allow_live=False, strict=True)
    o.load_data()
    runs = {r.scenario: r for r in o.run_ubc_experiment(horizon=30)}
    assert all(r.consistent for r in runs.values())


# --- C1: investment endogenised against owners' retained return ------------- #
@pytest.fixture(scope="module")
def runs_eps1():
    o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True,
                          inv_elasticity=1.0)
    o.load_data()
    return {r.scenario: r for r in o.run_ubc_experiment(horizon=30)}


def test_eps_zero_is_autonomous(runs):
    """Default elasticity (0) must reproduce autonomous capex: every AI arm
    shares the identical investment path — the Phase-1..3 contract is untouched."""
    nop = runs["AI shift, no policy"].result
    cash = runs["AI + Cash UBI"].result
    ubc = runs["AI + Universal Basic Capital"].result
    for a, b, c in zip(nop.periods, cash.periods, ubc.periods):
        assert abs(a.reported["investment"] - b.reported["investment"]) < 1e-6
        assert abs(a.reported["investment"] - c.reported["investment"]) < 1e-6
        assert abs(c.reported["inv_response"] - 1.0) < 1e-12   # signal off


def test_investment_feedback_stays_gate_clean(runs_eps1):
    """Endogenous investment must not break consistency at any elasticity."""
    for name, r in runs_eps1.items():
        assert r.consistent, f"{name} failed the gate with inv feedback"
        assert r.max_residual < 1.0


def test_disincentive_bites_ubc_hardest(runs_eps1):
    """With a real disincentive, UBC's retained-return signal (1-φ) falls to ~0
    as ownership socialises, so its capex collapses below the flat cash-UBI path
    (signal 1-τ) — the enclosure-vs-diffusion tension, made quantitative (C1)."""
    cash = runs_eps1["AI + Cash UBI"].result
    ubc = runs_eps1["AI + Universal Basic Capital"].result
    sig = [p.reported["inv_response"] for p in ubc.periods]
    assert sig[0] > 0.9 and sig[-1] < 0.2                  # signal decays toward 0
    assert all(b <= a + 1e-9 for a, b in zip(sig, sig[1:]))  # monotone non-increasing
    # cash signal is flat at (1-τ)
    csig = [p.reported["inv_response"] for p in cash.periods]
    assert max(csig) - min(csig) < 1e-9
    # by the horizon UBC under-invests vs cash and ends with a smaller capital stock
    assert ubc.periods[-1].reported["investment"] < cash.periods[-1].reported["investment"]
    assert ubc.periods[-1].reported["capital"] < cash.periods[-1].reported["capital"]


def test_equality_verdict_survives_the_disincentive(runs_eps1):
    """The distributional result is robust: even when diluting owners chokes
    investment, UBC still ends far more equal than cash UBI."""
    cash = runs_eps1["AI + Cash UBI"].result
    ubc = runs_eps1["AI + Universal Basic Capital"].result
    assert ubc.periods[-1].reported["gini"] < cash.periods[-1].reported["gini"]


# --- fund reinvestment: resolving the C1 collapse (F6 follow-up) ------------- #
@pytest.fixture(scope="module")
def reinvest_runs():
    """UBC at eps=1 (disincentive ON) with vs without fund reinvestment, + cash."""
    from scenarios import build_custom, LS_AI_END, CAPEX_AI_GROWTH
    o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True,
                          inv_elasticity=1.0)
    o.load_data()
    p = o.params()

    def mk(name, **kw):
        return build_custom(p, labour_share_end=LS_AI_END,
                            capex_growth=CAPEX_AI_GROWTH, capital_tax=0.40,
                            horizon=30, name=name, **kw)
    return {
        "ubc0": o.run_scenario(mk("UBC r=0", ubc=True, ubc_reinvest=0.0)),
        "ubc5": o.run_scenario(mk("UBC r=0.5", ubc=True, ubc_reinvest=0.5)),
        "cash": o.run_scenario(mk("cash", ubi=True)),
    }


def test_reinvest_default_zero_unchanged(runs):
    """The pinned experiment uses reinvest=0; the fund must reinvest nothing
    there, so F5 (and all prior results) are byte-for-byte unaffected."""
    ubc = runs["AI + Universal Basic Capital"].result
    assert all(p.reported["swf_reinvest"] == 0.0 for p in ubc.periods)
    assert all(p.reported["reinvest_rate"] == 0.0 for p in ubc.periods)


def test_reinvest_stays_gate_clean(reinvest_runs):
    for tag, r in reinvest_runs.items():
        assert r.consistent, f"{tag} failed the gate"
        assert r.max_residual < 1.0


def test_reinvest_fund_holds_no_money(reinvest_runs):
    """Profit share = dividend + reinvested capex, so the fund still nets to zero
    in money — the books close exactly with the extra channel."""
    for per in reinvest_runs["ubc5"].result.periods:
        assert "sovereign_fund" not in per.bsm["money"]


def test_reinvest_averts_the_capital_collapse(reinvest_runs):
    """The C1 fix: with the disincentive ON, reinvestment keeps capex alive where
    r=0 collapses — UBC ends LARGER than both its no-reinvest self and cash UBI."""
    k0 = reinvest_runs["ubc0"].result.periods[-1].reported["capital"]
    k5 = reinvest_runs["ubc5"].result.periods[-1].reported["capital"]
    kc = reinvest_runs["cash"].result.periods[-1].reported["capital"]
    assert k5 > 2.0 * k0                # reinvestment substantially averts the collapse
    assert k5 > 0.5 * kc                # lands comparable to cash, not collapsed
    # private capex collapses but total investment stays alive (fund backstops)
    end = reinvest_runs["ubc5"].result.periods[-1].reported
    assert reinvest_runs["ubc0"].result.periods[-1].reported["investment"] < 1.0
    assert end["investment"] > 1.0


def test_investment_migrates_from_owners_to_fund(reinvest_runs):
    """As ownership socialises, the fund's capex rises while private capex falls —
    the investment function MOVES to the public fund rather than disappearing."""
    per = reinvest_runs["ubc5"].result.periods
    fund_capex = [p.reported["swf_reinvest"] for p in per]
    priv_capex = [p.reported["investment_private"] for p in per]
    assert fund_capex[-1] > fund_capex[0]            # fund takes over
    assert priv_capex[-1] < priv_capex[len(priv_capex)//3]   # owners retreat
    assert reinvest_runs["ubc5"].result.periods[-1].reported["gini"] < \
        reinvest_runs["cash"].result.periods[-1].reported["gini"]   # still more equal


# --- C1 CLOSURE: the pinned experiment with investment ENDOGENISED ---------- #
# F5's caveat was "investment held fixed across arms". c1_closure() runs the
# actual cash-vs-UBC arms under three investment regimes and shows the verdict
# survives once the fund reinvests (the integrated close of crux C1).
def test_c1_closure_choke_then_cure():
    from orchestrator import AgoraOrchestrator
    o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True)
    o.load_data()
    c = o.c1_closure(horizon=30, inv_elasticity=0.75, reinvest=1.0)

    # every arm in every regime stays gate-consistent
    assert all(c[r]["all_consistent"] for r in c)

    fixed = c["fixed"]["ubc_vs_cash_gdp"]
    endog = c["endogenous"]["ubc_vs_cash_gdp"]
    cured = c["endogenous+reinvest"]["ubc_vs_cash_gdp"]

    # 1) endogenous investment CHOKES UBC: diluting owners deters capex, so the
    #    UBC economy shrinks vs cash relative to the fixed-investment headline.
    assert endog < fixed
    assert endog < 1.0                       # UBC ends smaller than cash (F6)

    # 2) fund reinvestment CURES it: output recovers and UBC matches/exceeds cash.
    assert cured > endog                      # monotone recovery
    assert cured >= 1.0                       # full closure at high reinvest

    # 3) the ROBUST (beta-independent) equality verdict holds in ALL regimes:
    #    UBC collapses WEALTH concentration vs cash (ownership is socialised),
    #    while cash never touches it. This is the durable "owning beats
    #    receiving" core (F8/F16), true at the data-grounded beta and in every
    #    investment regime.
    for r in c:
        assert c[r]["ubc_wealth_top10_end"] < c[r]["cash_wealth_top10_end"] - 0.2

    # 4) the INCOME-Gini advantage is conditional (F16): it holds when the fund
    #    PAYS OUT the dividend (fixed regime), but full reinvestment plows the
    #    dividend into capital+growth instead, easing income compression even as
    #    wealth still collapses — a real dividend-vs-ownership trade-off.
    assert c["fixed"]["ubc_gini_end"] < c["fixed"]["cash_gini_end"]


def test_c1_reinvest_recovery_is_monotone():
    """Higher fund reinvestment -> larger UBC economy (the cure is dose-dependent)."""
    from orchestrator import AgoraOrchestrator
    o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True)
    o.load_data()

    def ubc_vs_cash(reinvest):
        by = {r.scenario: r for r in o.run_ubc_experiment(
            horizon=30, inv_elasticity=0.75, reinvest=reinvest)}
        return (by["AI + Universal Basic Capital"].result.periods[-1].reported["gdp"]
                / by["AI + Cash UBI"].result.periods[-1].reported["gdp"])

    lo, hi = ubc_vs_cash(0.0), ubc_vs_cash(0.8)
    assert hi > lo
