#!/usr/bin/env python3
"""Pull the external-position calibration for every snapshot country (Phase 7 D).

Three bulk DBnomics calls (Eurostat nasa_10_nf_tr D42+D43 vs the rest of the
world, nama_10_gdp, tipsii10). Run on a machine that can reach DBnomics:
    python scripts/build_external.py            # dry run: fetch and print
    python scripts/build_external.py --write    # write data/cache/external_positions.json
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.connectors.external import (CACHE, CONDUIT_INWARD_GDP, fetch_all,  # noqa: E402
                                      summarise)
from schema.accounts import AGGREGATE_GEOS                                    # noqa: E402
from scout.checks import snapshot_geos                                        # noqa: E402


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
        r["source"] = ("Eurostat nasa_10_nf_tr D42+D43 S2 RECV/PAID, nama_10_gdp B1GQ, "
                       f"tipsii10 NIIP (DBnomics), {s['window']}")
        out[geo] = r
        tag = "  CONDUIT" if s["inward_gdp"] > CONDUIT_INWARD_GDP else ""
        print(f"{geo}: inward {s['inward_gdp']:.3f}  outward {s['outward_gdp']:.3f} of GDP  "
              f"NIIP {s['niip_gdp']:+.2f}{tag}")
    print(f"\n{len(out)} countries pulled, {len(missing)} missing: {', '.join(missing) or '-'}")
    if a.write:
        doc = {"generated": time.strftime("%Y-%m-%d"), "base_year": a.year,
               "series": ("Eurostat nasa_10_nf_tr (D42+D43, S2, RECV=inward/PAID=outward, "
                          "CP_MEUR), nama_10_gdp (B1GQ, CP_MEUR), tipsii10 (NIIP, % of GDP); "
                          "annual"),
               "countries": out}
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        print(f"wrote {CACHE}")
    else:
        print("dry run - nothing written (use --write)")


if __name__ == "__main__":
    main()
