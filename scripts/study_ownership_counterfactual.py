#!/usr/bin/env python3
"""STANDALONE STUDY — the citizens'-fund counterfactual, all EU states.

"If every EU state had started a citizens' capital fund in the mid-1990s, how much
of the national capital stock would its citizens own today, and what dividend would
it pay?"

Method (partial-equilibrium OWNERSHIP accumulation, driven by each country's REAL
history; NOT the full gated GE engine — the levy transfers ownership of capital that
already exists, it doesn't change how much capital there is, to first order):
  1. Pull actual GDP, GFCF (investment), labour share, population per year (live).
  2. Build the capital stock by perpetual inventory: K_t = K_{t-1}(1-delta) + GFCF_t,
     seeded K_0 = ky * GDP_0 (the seed washes out over ~30 years).
  3. Run the fund: each year it is issued tau * capital-income in new shares
     (in-kind dilution) AND reinvests its own return net of a POMV draw (GPFG 3%);
     the fund compounds. phi = E_sf / K.
  4. Report per country: fund ownership %, citizens' capital per person, dividend
     per person (POMV draw), for a couple of levy intensities.

Run on a NETWORKED machine (live DBnomics):
    python scripts/study_ownership_counterfactual.py
    python scripts/study_ownership_counterfactual.py --start 1995 --end 2024 --taus 0.05 0.10
Writes study_ownership_counterfactual.md. Standalone; changes nothing in the engine.
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest import load_panel
from scout.checks import snapshot_geos
from schema.accounts import AGGREGATE_GEOS

DELTA     = 0.05    # depreciation (perpetual-inventory)
KY        = 3.0     # capital/GDP seed ratio (AGORA default)
PAYOUT    = 0.03    # POMV draw (Norway GPFG fiscal rule)
R_REINVEST= 0.04    # fund's NET REAL reinvestment/compounding rate (Norway GPFG ~4%
                    # real). Caps the compounding so the stake can't outgrow the
                    # economy at the raw domestic profit rate (~13%) and saturate.
EXCLUDE   = {"IE", "LU"}   # MNC-inflated / entrepot GDP distorts the capital stock


def build_capital(panel):
    """Perpetual-inventory capital stock from actual GFCF; seed K0 = KY*GDP0."""
    yrs = sorted(panel)
    K = {}
    K0 = KY * panel[yrs[0]]["gdp"]
    K[yrs[0]] = K0
    for prev, y in zip(yrs, yrs[1:]):
        gfcf = panel[y].get("gfcf", panel[prev].get("gfcf", 0.0))
        K[y] = K[prev] * (1 - DELTA) + gfcf
    return K


def run_fund(panel, K, tau, r_reinvest=R_REINVEST):
    """Citizens'-fund OWNERSHIP share over the real path, compounded at a realistic
    (Norway-like) real return so it can't saturate. Each year the fund's share grows
    by (a) reinvesting at r_reinvest and (b) new shares from the dilution levy
    (tau * capital-income, as a fraction of the capital stock). Depreciation hits the
    fund's shares and the capital stock equally, so the SHARE is depreciation-neutral.
    Returns (phi, capital_per_person, dividend_per_person, window)."""
    yrs = sorted(panel)
    phi = 0.0
    used = []
    for y in yrs:
        ls = panel[y].get("labour_share")
        gdp = panel[y].get("gdp")
        if ls is None or not gdp or K[y] <= 0:
            continue
        cap_share = max(0.0, 1.0 - ls / 100.0)
        ky = K[y] / gdp
        dilution = (tau * cap_share / ky) if ky > 0 else 0.0   # new ownership from the levy
        phi = min(1.0, phi * (1.0 + r_reinvest) + dilution)
        used.append(y)
    if not used:
        return 0.0, 0.0, 0.0, (None, None)
    last = used[-1]
    pop = panel[last].get("population") or 1.0
    cap_pc = phi * K[last] / pop * 1e6          # EUR of capital owned per person
    return phi, cap_pc, PAYOUT * cap_pc, (used[0], used[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geos", nargs="+", default=None)
    ap.add_argument("--start", type=int, default=1995)
    ap.add_argument("--end", type=int, default=2024)
    ap.add_argument("--taus", nargs="+", type=float, default=[0.05, 0.10])
    a = ap.parse_args()
    geos = a.geos or [g for g in snapshot_geos()
             if g.upper() not in AGGREGATE_GEOS and g.upper() not in EXCLUDE]
    yrs = list(range(a.start, a.end + 1))

    rows = []
    for g in geos:
        print("... pulling", g)
        panel = load_panel(g, yrs, allow_live=True,
                           required=("gdp", "gfcf", "labour_share"))
        got = sorted(panel)
        if len(got) < 5:
            print("   %s: only %d yrs (needs live DBnomics)" % (g, len(got)))
            rows.append((g, None)); continue
        K = build_capital(panel)
        res = {tau: run_fund(panel, K, tau) for tau in a.taus}
        rows.append((g, (got[0], got[-1], res)))

    out = ["# AGORA — the citizens'-fund counterfactual (all EU, %d-%d)\n" % (a.start, a.end),
           "_If each EU state had started a citizens' capital fund in the mid-1990s, "
           "how much would its citizens own today? Partial-equilibrium ownership "
           "accumulation driven by each country's REAL GDP/investment/capital-share "
           "history; POMV draw = %.0f%% (Norway GPFG rule). Not the full gated GE "
           "engine — see header. Compounding capped at the Norway ~%.0f%% real return; "
           "IE & LU excluded (distorted GDP)._\n" % (PAYOUT * 100, R_REINVEST * 100)]
    head = "| Country | window | " + " | ".join(
        "fund owns @%.0f%% | EUR/person @%.0f%% | div/yr @%.0f%%" % (t*100, t*100, t*100)
        for t in a.taus) + " |"
    out.append(head)
    out.append("|" + "---|" * (2 + 3 * len(a.taus)))
    for g, data in rows:
        if data is None:
            out.append("| %s | (no live data) |%s" % (g, " |" * (3 * len(a.taus))))
            continue
        y0, y1, res = data
        cells = []
        for t in a.taus:
            phi, cap_pc, div_pc, _ = res[t]
            cells += ["%.0f%%" % (phi*100), "EUR %s" % f"{cap_pc:,.0f}", "EUR %s" % f"{div_pc:,.0f}"]
        out.append("| %s | %d-%d | %s |" % (g, y0, y1, " | ".join(cells)))
    report = "\n".join(out)
    open("study_ownership_counterfactual.md", "w", encoding="utf-8").write(report)
    print("\n" + report + "\n\nwrote study_ownership_counterfactual.md")


if __name__ == "__main__":
    main()
