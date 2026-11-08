#!/usr/bin/env python3
"""Pull the capital-stock calibration for every snapshot country (Phase 7 F).

Four DBnomics calls (AMECO OKND, PIGT, UKCT, UVGD; total economy):
    python scripts/build_capital.py            # dry run: fetch and print
    python scripts/build_capital.py --write    # write data/cache/capital_stock.json
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.connectors.capital import CACHE, fetch_all, from_dbnomics, summarise   # noqa: E402
from schema.accounts import AGGREGATE_GEOS                                        # noqa: E402
from scout.checks import snapshot_geos                                            # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="write the cache (default: dry run)")
    ap.add_argument("--year", type=int, default=2019)
    ap.add_argument("--from-files", nargs=4, metavar=("OKND", "PIGT", "UKCT", "UVGD"),
                    help="parse saved DBnomics answers instead of fetching")
    a = ap.parse_args()
    if a.from_files:
        docs = {}
        for var, path in zip(("OKND", "PIGT", "UKCT", "UVGD"), a.from_files):
            with open(path, encoding="utf-8") as fh:
                docs[var] = json.load(fh).get("series", {}).get("docs", [])
        rec = from_dbnomics(docs, a.year)
    else:
        rec = fetch_all(base_year=a.year)
    geos = [g for g in snapshot_geos() if g.upper() not in AGGREGATE_GEOS] + ["EA20"]
    out, missing = {}, []
    for geo in geos:
        r = rec.get(geo.upper())
        s = summarise(r["series"], a.year) if r else None
        if not s:
            missing.append(geo)
            print(f"{geo}: MISSING -> euro-area default stays in use")
            continue
        r["source"] = f"AMECO OKND/PIGT/UKCT/UVGD (DBnomics), depreciation {s['window']}"
        out[geo.upper()] = r
        print(f"{geo}: K/Y {s['k_y']:.2f}  depreciation {s['delta']:.4f}  "
              f"CFC/GDP {s['cfc_gdp']:.3f}  real stock growth {s['real_stock_growth']:+.4f}")
    print(f"\n{len(out)} pulled, {len(missing)} missing: {', '.join(missing) or '-'}")
    if a.write:
        doc = {"generated": time.strftime("%Y-%m-%d"), "base_year": a.year,
               "series": "AMECO OKND (net capital stock, 2020 prices), PIGT (GFCF deflator, "
                         "2020 = 100), UKCT (consumption of fixed capital), UVGD (GDP), total "
                         "economy, national currency; annual",
               "retrieved": time.strftime("%Y-%m-%d") + " from the DBnomics endpoints in "
                            "data/connectors/capital.py (fetched through a web proxy; rebuild "
                            "with scripts/build_capital.py --write)",
               "countries": out}
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        print(f"wrote {CACHE}")
    else:
        print("dry run - nothing written (use --write)")


if __name__ == "__main__":
    main()
