#!/usr/bin/env python3
"""Pull EC-survey capacity utilisation for every snapshot country (Phase 7 C).

Run on a machine that can reach DBnomics (your own, not the sandbox):
    python scripts/build_capacity.py            # dry run: fetch and print
    python scripts/build_capacity.py --write    # write data/cache/capacity_utilisation.json
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.connectors.capacity import CACHE, fetch_live      # noqa: E402
from schema.accounts import AGGREGATE_GEOS                    # noqa: E402
from scout.checks import snapshot_geos                        # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="write the cache (default: dry run)")
    ap.add_argument("--year", type=int, default=2019)
    a = ap.parse_args()
    out, missing = {}, []
    for geo in [g for g in snapshot_geos() if g.upper() not in AGGREGATE_GEOS]:
        try:
            rec = fetch_live(geo, base_year=a.year)
        except Exception as e:                       # network / provider error
            rec, err = None, f"{type(e).__name__}: {e}"
        else:
            err = "no observation for the base year"
        if rec:
            out[geo] = rec
            print(f"{geo}: 2019 {rec['base']:.3f}  normal {rec['normal']:.3f}  "
                  f"max {rec['max']:.3f}  ({rec['n_obs']} obs)")
        else:
            missing.append(geo)
            print(f"{geo}: MISSING ({err}) -> default stays in use")
    print(f"\n{len(out)} countries pulled, {len(missing)} missing: {', '.join(missing) or '-'}")
    if a.write:
        doc = {"generated": time.strftime("%Y-%m-%d"), "base_year": a.year,
               "series": "EC BCS manufacturing capacity utilisation (BUBA/BBXS1 on DBnomics)",
               "countries": out}
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        print(f"wrote {CACHE}")
    else:
        print("dry run - nothing written (use --write)")


if __name__ == "__main__":
    main()
