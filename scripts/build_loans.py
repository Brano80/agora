#!/usr/bin/env python3
"""Pull firms' and households' loan liabilities (Phase 7 F).

One DBnomics call (Eurostat nasa_10_f_bs, F4, S11 and S14_S15, % of GDP):
    python scripts/build_loans.py            # dry run
    python scripts/build_loans.py --write    # write data/cache/private_loans.json
    python scripts/build_loans.py --from-file saved.json --write
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.connectors.loans import CACHE, fetch_all, from_dbnomics   # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--year", type=int, default=2019)
    ap.add_argument("--from-file")
    a = ap.parse_args()
    if a.from_file:
        with open(a.from_file, encoding="utf-8") as fh:
            rec = from_dbnomics(json.load(fh).get("series", {}).get("docs", []), a.year)
    else:
        rec = fetch_all(a.year)
    for g in sorted(rec):
        s = rec[g]["series"]
        print(f"{g}: firms {s.get('S11', {}).get(str(a.year), '-')}  households "
              f"{s.get('S14_S15', {}).get(str(a.year), '-')} (% of GDP)")
    if a.write:
        doc = {"generated": time.strftime("%Y-%m-%d"), "base_year": a.year,
               "series": "Eurostat nasa_10_f_bs (PC_GDP, CO, LIAB, F4; S11, S14_S15); annual",
               "retrieved": time.strftime("%Y-%m-%d") + " from the DBnomics endpoint in "
                            "data/connectors/loans.py (fetched through a web proxy)",
               "countries": rec}
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        print(f"wrote {CACHE}")


if __name__ == "__main__":
    main()
