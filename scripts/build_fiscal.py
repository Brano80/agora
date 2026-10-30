#!/usr/bin/env python3
"""Pull the fiscal calibration for every snapshot country (Phase 7 E).

One DBnomics call (Eurostat gov_10dd_edpt1: GD, B9, D41PAY, % of GDP):
    python scripts/build_fiscal.py            # dry run: fetch and print
    python scripts/build_fiscal.py --write    # write data/cache/fiscal_positions.json
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.connectors.fiscal import CACHE, fetch_all, summarise   # noqa: E402
from schema.accounts import AGGREGATE_GEOS                        # noqa: E402
from scout.checks import snapshot_geos                            # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="write the cache (default: dry run)")
    ap.add_argument("--year", type=int, default=2019)
    a = ap.parse_args()
    rec = fetch_all(base_year=a.year)
    out, missing = {}, []
    for geo in [g for g in snapshot_geos() if g.upper() not in AGGREGATE_GEOS]:
        r = rec.get(geo.upper())
        s = summarise(r["series"], a.year) if r else None
        if not s:
            missing.append(geo)
            print(f"{geo}: MISSING -> default stays in use")
            continue
        r["source"] = f"Eurostat gov_10dd_edpt1 GD/B9/D41PAY (DBnomics), rate {s['window']}"
        out[geo] = r
        print(f"{geo}: debt {s['debt']:.2f}  primary balance {s['primary_balance']:+.3f}  "
              f"implicit rate {s['implicit_rate']:.4f}")
    print(f"\n{len(out)} countries pulled, {len(missing)} missing: {', '.join(missing) or '-'}")
    if a.write:
        doc = {"generated": time.strftime("%Y-%m-%d"), "base_year": a.year,
               "series": "Eurostat gov_10dd_edpt1 (S13; GD, B9, D41PAY; % of GDP); annual",
               "countries": out}
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        print(f"wrote {CACHE}")
    else:
        print("dry run - nothing written (use --write)")


if __name__ == "__main__":
    main()
