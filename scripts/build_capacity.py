#!/usr/bin/env python3
"""Pull EC-survey capacity utilisation for every snapshot country (Phase 7 C).

Reads Eurostat ei_bsin_q_r2 (BS-ICU-PC, SA) for all members in one DBnomics
call; a country it misses falls back to the Bundesbank mirror, then the
Eurostat API. Run on a machine that can reach them (your
own, not the sandbox):
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

from data.connectors.capacity import CACHE, fetch_all, fetch_live   # noqa: E402
from schema.accounts import AGGREGATE_GEOS                         # noqa: E402
from scout.checks import snapshot_geos                             # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="write the cache (default: dry run)")
    ap.add_argument("--year", type=int, default=2019)
    a = ap.parse_args()
    out, missing = {}, []
    try:
        bulk = fetch_all(base_year=a.year)
    except Exception as e:                           # fall back country by country
        bulk = {}
        print(f"bulk Eurostat pull failed ({type(e).__name__}: {e}); trying per country")
    for geo in [g for g in snapshot_geos() if g.upper() not in AGGREGATE_GEOS]:
        try:
            rec = bulk.get(geo.upper()) or fetch_live(geo, base_year=a.year)
        except Exception as e:                       # network / provider error
            rec, err = None, f"{type(e).__name__}: {e}"
        else:
            err = "no observation for the base year"
        if rec:
            out[geo] = rec
            print(f"{geo}: 2019 {rec['base']:.3f}  normal {rec['normal']:.3f} "
                  f"({rec['normal_window']})  min {rec['min']:.3f}  max {rec['max']:.3f}  "
                  f"({rec['n_obs']} yrs, {rec['route']})")
        else:
            missing.append(geo)
            print(f"{geo}: MISSING ({err}) -> default stays in use")
    print(f"\n{len(out)} countries pulled, {len(missing)} missing: {', '.join(missing) or '-'}")
    if a.write:
        doc = {"generated": time.strftime("%Y-%m-%d"), "base_year": a.year,
               "series": "EC BCS manufacturing capacity utilisation (Eurostat ei_bsin_q_r2 "
                         "BS-ICU-PC SA; fallback BUBA/BBXS1), annual means, fractions",
               "countries": out}
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        print(f"wrote {CACHE}")
    else:
        print("dry run - nothing written (use --write)")


if __name__ == "__main__":
    main()
