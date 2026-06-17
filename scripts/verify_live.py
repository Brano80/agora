#!/usr/bin/env python3
"""Verify live DBnomics pulls, per series, for a geo/year.

Run on a machine WITH network access to https://api.db.nomics.world. Reports,
for each canonical series, whether the live pull succeeded, the live value, the
observation year actually matched, and the % difference vs the bundled snapshot.
Use it to confirm the live wiring and to spot any series whose DBnomics
dimensions need adjusting (they fall back to snapshot until fixed).

    python scripts/verify_live.py --geo DE --year 2019
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.connectors.dbnomics import DBnomicsConnector  # noqa: E402
from schema.accounts import series_for_geo               # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", default="DE")
    ap.add_argument("--year", type=int, default=2019)
    ap.add_argument("--timeout", type=float, default=20.0)
    args = ap.parse_args()

    conn = DBnomicsConnector(timeout=args.timeout, allow_live=True)
    bound = series_for_geo(args.geo)

    print(f"AGORA live DBnomics check - {args.geo} {args.year}\n")
    print(f"{'series':18}{'live?':7}{'live value':>16}{'obs yr':>8}"
          f"{'snapshot':>16}{'diff':>9}  source")
    live_ok = 0
    for code, s in bound.items():
        live = conn.fetch_one(args.geo, args.year, code, allow_live=True) if s.live else None
        snap = conn.fetch_one(args.geo, args.year, code, allow_live=False)
        snap_v = snap["value"] if snap else float("nan")
        if live and live.get("source") == "live":
            live_ok += 1
            lv = live["value"]; oy = live.get("obs_year", "")
            diff = (lv - snap_v) / snap_v * 100 if snap_v else float("nan")
            print(f"{code:18}{'YES':7}{lv:16,.1f}{str(oy):>8}{snap_v:16,.1f}"
                  f"{diff:8.2f}%  live")
        else:
            why = "snapshot-only" if not s.live else "fell back"
            print(f"{code:18}{'no':7}{'-':>16}{'-':>8}{snap_v:16,.1f}"
                  f"{'-':>9}  {why}")
    n = len(bound)
    print(f"\n{live_ok}/{n} series pulled live; {n-live_ok} from snapshot.")
    print(f"DBnomics dimension query example:\n  {conn._build_url(bound['gdp'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
