#!/usr/bin/env python3
"""Backtest the model against a multi-year panel + ground its parameters.

Run on a machine WITH live DBnomics access. Validates the model's DYNAMICS
against history (the project's 'validate before trusting' rule) and grounds the
AI-shock anchors in Epoch data.

    python scripts/backtest.py --geo DE --years 2010 2011 ... 2019
    python scripts/backtest.py --geo DE FR --years 2012 2013 2014 2015 2016 2017 2018 2019
    python scripts/backtest.py --ground-shock           # Epoch-grounded anchors
    python scripts/backtest.py --beta --geo DE FR PL RO BG ES IT NL  # fit β (cross-section)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest import (load_panel, backtest, estimate_beta_cross_section,  # noqa: E402
                      ground_ai_shock)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", nargs="+", default=["DE"])
    ap.add_argument("--years", nargs="+", type=int,
                    default=list(range(2010, 2020)))
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--ground-shock", action="store_true")
    ap.add_argument("--beta", action="store_true")
    args = ap.parse_args()
    live = not args.offline

    if args.ground_shock:
        print("AI-shock anchors (Epoch-grounded):")
        for k, v in ground_ai_shock().items():
            print(f"  {k}: {v}")
        return 0
    if args.beta:
        b, a, r2, n = estimate_beta_cross_section(args.geo, args.years[-1], live)
        print(f"β (capital-share -> inequality) cross-section fit over {n} geos: "
              f"slope={b:.3f} intercept={a:.3f} R^2={r2:.2f}")
        if r2 < 0.1:
            print("  (low R^2: cross-section of DISPOSABLE-income Gini doesn't "
                  "identify β — redistribution confounds it. Use a multi-year "
                  "MARKET-income panel for a real estimate.)")
        return 0

    rc = 0
    for geo in args.geo:
        panel = load_panel(geo, args.years, allow_live=live)
        r = backtest(geo, panel)
        print(f"\n=== {geo}: backtest over {sorted(panel)} ({r.n_years} yrs) ===")
        if r.n_years < 2:
            print(f"  {r.note}")
            rc = 1
            continue
        for series, e in r.mae_pct.items():
            print(f"  {series:14}: mean abs error {e*100:5.2f}%")
        print(f"  verdict: {'PASS' if r.passed() else 'REVIEW'} "
              f"(outcome series within 10%)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
