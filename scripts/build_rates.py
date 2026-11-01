#!/usr/bin/env python3
"""Pull the interest-rate calibration for every snapshot country (Phase 7 Banks).

Five DBnomics calls (AMECO ISN/ILN, ECB MIR firm loans and household overnight
deposits, Eurostat nasa_10_f_bs household assets):
    python scripts/build_rates.py            # dry run: fetch and print
    python scripts/build_rates.py --write    # write data/cache/rates.json
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.connectors.rates import CACHE, EURO_AREA, fetch_all, summarise   # noqa: E402
from schema.accounts import AGGREGATE_GEOS                                 # noqa: E402
from scout.checks import snapshot_geos                                     # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="write the cache (default: dry run)")
    ap.add_argument("--year", type=int, default=2019)
    a = ap.parse_args()
    rec = fetch_all(base_year=a.year)
    members = [g.upper() for g in snapshot_geos() if g.upper() not in AGGREGATE_GEOS]
    out, missing = {}, []
    for geo in members + [EURO_AREA]:
        s = summarise(rec, geo, a.year)
        if not s:
            missing.append(geo)
            print(f"{geo}: MISSING -> euro-area default stays in use")
            continue
        out[geo] = rec[geo]
        print(f"{geo}: {s['regime']:>3}  policy {s['policy0']:+.4f}  gov spread {s['gov_spread']:.4f}  "
              f"loan spread {s['loan_spread']:.4f}  deposits {s['deposit_rate0']:.4f} "
              f"(share {s['deposit_share']:.2f})  [{s['flag']}]")
    print(f"\n{len(out)} pulled, {len(missing)} missing: {', '.join(missing) or '-'}")
    if a.write:
        doc = {"generated": time.strftime("%Y-%m-%d"), "base_year": a.year,
               "series": "AMECO ISN, ILN (%); ECB MIR firm-loan (A20/2240, outstanding) and "
                         "household overnight-deposit (L21/2250) rates, annual means of monthly "
                         "data (%); Eurostat nasa_10_f_bs households F2/F3/F6 (% of GDP)",
               "countries": out}
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        print(f"wrote {CACHE}")
    else:
        print("dry run - nothing written (use --write)")


if __name__ == "__main__":
    main()
