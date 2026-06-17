#!/usr/bin/env python3
"""All-EU Q2 - national vs GLOBAL (pooled) AI dividend across every snapshot
country, with the pooled arm GATED (transfers through each country's books).
Offline-capable (snapshots); excludes aggregates; drops IE by default
(MNC-inflated GDP distorts the giver ranking - pass --drop none to keep it).

    python scripts/q2_all_eu.py
    python scripts/q2_all_eu.py --form ubc --tau 0.4 --horizon 30 --drop none
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from region import MultiRegion                                 # noqa: E402
from scout.checks import snapshot_geos                         # noqa: E402
from schema.accounts import AGGREGATE_GEOS                     # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--form", nargs="+", default=["cash_ubi", "ubc"])
    ap.add_argument("--tau", type=float, default=0.40)
    ap.add_argument("--horizon", type=int, default=30)
    ap.add_argument("--drop", nargs="*", default=["IE"])
    ap.add_argument("--year", type=int, default=2019)
    args = ap.parse_args()
    drop = {d.upper() for d in args.drop if d.lower() != "none"}
    geos = [g for g in snapshot_geos()
            if g.upper() not in AGGREGATE_GEOS and g.upper() not in drop]
    print(f"Bloc: {len(geos)} countries ({', '.join(geos)})")
    mr = MultiRegion(geos=tuple(geos), year=args.year, allow_live=False)
    for form in args.form:
        c = mr.dividend_comparison(form=form, tau=args.tau, horizon=args.horizon)
        n, g = c.gini_national[-1], c.gini_global[-1]
        print(f"\n=== {form} (tau={args.tau:.0%}, {args.horizon}y) ===")
        print(f"  viable: {len(c.geos)}  excluded: {c.excluded or '-'}  "
              f"gated: {'YES' if c.consistent else 'NO'} (worst {c.max_residual:.1e})")
        print(f"  between-country Gini: national {n:.4f} -> global {g:.4f} "
              f"({100 * (1 - g / n):+.0f}% narrowing)")
        tr = sorted(c.pooling_transfer_pc.items(), key=lambda kv: kv[1])
        give = ", ".join(f"{k} {1e6 * v:,.0f}" for k, v in tr[:3])
        recv = ", ".join(f"{k} {1e6 * v:,.0f}" for k, v in tr[-3:][::-1])
        print(f"  top givers (EUR/capita): {give}")
        print(f"  top receivers          : {recv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
