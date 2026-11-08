#!/usr/bin/env python3
"""Pull the 1995-2019 history panel the backtest uses (Phase 7 F).

Seven DBnomics calls (data/connectors/history.py):
    python scripts/build_history.py            # dry run: fetch and print
    python scripts/build_history.py --write    # write data/cache/history_panel.json
    python scripts/build_history.py --from-dir DIR --write   # saved answers DIR/<key>.json
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.connectors.history import API, CACHE, GEOS, fetch_all, from_dbnomics   # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="write the cache (default: dry run)")
    ap.add_argument("--from-dir", help="parse saved DBnomics answers (<key>.json per API key)")
    a = ap.parse_args()
    if a.from_dir:
        docs = {}
        for k in API:
            with open(os.path.join(a.from_dir, k + ".json"), encoding="utf-8") as fh:
                docs[k] = json.load(fh).get("series", {}).get("docs", [])
        rec = from_dbnomics(docs)
    else:
        rec = fetch_all()
    for g in GEOS:
        s = rec.get(g, {}).get("series", {})
        gaps = [k for k in ("gdp", "gdp_real", "hh_consumption_real", "gfcf_real", "gov_gfcf",
                            "hh_saving_rate", "labour_share", "ca_gdp", "gini_disp_income")
                if "2010" not in s.get(k, {})]
        print(f"{g}: {len(s)} series, 2010 gaps: {', '.join(gaps) or '-'}")
    if a.write:
        doc = {"generated": time.strftime("%Y-%m-%d"), "years": "1995-2019",
               "series": "Eurostat nama_10_gdp (CP_MEUR; CLV20_MEUR else CLV15_MEUR as *_real), "
                         "gov_10a_main (S13 P51G MIO_EUR; D9PAY, D9REC PC_GDP), nasa_10_ki (SRG_S14_S15), ilc_di12 (GINI_HND); "
                         "AMECO ALCD2 (adjusted wage share), UBCA (current account, % of GDP)",
               "retrieved": time.strftime("%Y-%m-%d") + " from the DBnomics endpoints in "
                            "data/connectors/history.py (fetched through a web proxy)",
               "countries": rec}
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, separators=(",", ":"))
        print(f"wrote {CACHE} ({os.path.getsize(CACHE) // 1024} KB)")
    else:
        print("dry run - nothing written (use --write)")


if __name__ == "__main__":
    main()
