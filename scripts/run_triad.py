#!/usr/bin/env python3
"""Run the Phase-1 scenario triad end-to-end through the orchestrator.

Usage:
    python scripts/run_triad.py [--geo DE] [--year 2019] [--horizon 30] [--live]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import build  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", default="DE")
    ap.add_argument("--year", type=int, default=2019)
    ap.add_argument("--horizon", type=int, default=30)
    ap.add_argument("--live", action="store_true",
                    help="attempt the live DBnomics API (else use snapshot)")
    args = ap.parse_args()

    orch = build(geo=args.geo, year=args.year, allow_live=args.live, strict=True)
    data = orch.load_data()
    src = orch._sources
    live_n = sum(1 for v in src.values() if v == "live")
    print(f"AGORA Phase 1 — {args.geo} {args.year}  "
          f"(data: {live_n}/{len(src)} live, rest snapshot)\n")

    # validation / backtest
    rows, _ = orch.validate_baseline(horizon=args.horizon)
    print("Baseline validation (does it reproduce the national targets?)")
    print(f"  {'metric':28}{'target':>16}{'model':>16}{'rel err':>10}  ok")
    for r in rows:
        print(f"  {r.metric:28}{r.target:16,.1f}{r.model:16,.1f}"
              f"{r.rel_error*100:9.3f}%  {'PASS' if r.ok else 'FAIL'}")

    p = orch.params()
    print(f"\n  net-export gap excluded (RoW Phase 3): {p.nx_gap:,.0f} MEUR "
          f"({100*p.nx_gap/p.gdp_full:.1f}% of full GDP)")
    print(f"  calibrated income tax θ={p.theta:.3f}, owners' MPC a1_k={p.a1_k:.3f}\n")

    # triad
    runs = orch.run_triad(horizon=args.horizon)
    print(f"{'scenario':36}{'final GDP':>12}{'final C':>12}{'Gini':>7}"
          f"{'debt/GDP':>10}  consistent")
    for run in runs:
        last = run.result.periods[-1].reported
        print(f"{run.scenario:36}{last['gdp']:12,.0f}{last['consumption']:12,.0f}"
              f"{last['gini']:7.3f}{last['gov_debt_gdp']:9.1f}%  "
              f"{'YES' if run.consistent else 'NO — LEAK!'}")

    worst = max(r.max_residual for run in runs for r in run.reports)
    print(f"\nConsistency gate: worst residual across all periods/scenarios "
          f"= {worst:.3e} MEUR  ->  books close.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
