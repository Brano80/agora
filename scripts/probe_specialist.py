#!/usr/bin/env python3
"""Resolve the live DBnomics codes for the two snapshot-DEFAULT specialist
series — BIS household debt (hh_debt_gdp) and WID top-10% wealth share
(top10_wealth_share) — so they can be wired live (they currently fall back to
the 50.0 / 0.55 defaults for every country but DE/FR/PL).

Run on a machine WITH network access:

  python scripts/probe_specialist.py                  # discover datasets + test current dims
  python scripts/probe_specialist.py --dims BIS/WS_TC # dump one dataset's dimensions

Then paste the output to Claude, who will set the confirmed dataset + dimensions
and flip live=True for each series in schema/accounts.py (the connector keeps the
snapshot as fallback, so a wrong dim degrades gracefully).
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.connectors.dbnomics import DBnomicsConnector   # noqa: E402
from schema.accounts import series_for_geo                # noqa: E402

_API = "https://api.db.nomics.world/v22"


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "agora/0.3"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def discover(queries):
    seen = {}
    for q in queries:
        try:
            payload = _get(f"{_API}/search?"
                           + urllib.parse.urlencode({"q": q, "limit": 20}))
        except Exception as e:
            print(f"  search '{q}' failed: {type(e).__name__}: {e}")
            continue
        docs = (payload.get("results", {}).get("docs")
                or payload.get("datasets", {}).get("docs")
                or payload.get("docs", []))
        for d in docs:
            prov = d.get("provider_code") or d.get("provider")
            code = d.get("code") or d.get("dataset_code")
            if prov and code and (prov, code) not in seen:
                seen[(prov, code)] = {
                    "provider": prov, "dataset": code,
                    "name": d.get("name", ""),
                    "nb": d.get("nb_series") or d.get("nb_matching_series")}
    return list(seen.values())


def list_provider(provider, limit=40):
    """List a provider's datasets directly (when search finds nothing). Returns
    [{provider, dataset, name, nb}]."""
    try:
        payload = _get(f"{_API}/datasets/{urllib.parse.quote(provider)}?limit={limit}")
    except Exception as e:
        print(f"  provider listing for {provider} failed: {type(e).__name__}: {e}")
        return []
    node = payload.get("datasets", {})
    docs = node.get("docs") if isinstance(node, dict) else None
    out = []
    if isinstance(docs, list):
        for d in docs:
            out.append({"provider": provider, "dataset": d.get("code"),
                        "name": d.get("name", ""), "nb": d.get("nb_series")})
    elif isinstance(node, dict):
        for code, d in node.items():
            if isinstance(d, dict):
                out.append({"provider": provider, "dataset": code,
                            "name": d.get("name", ""), "nb": d.get("nb_series")})
    return out


def dump_dims(spec):
    provider, dataset = spec.split("/", 1)
    payload = _get(f"{_API}/series/{urllib.parse.quote(provider)}/"
                   f"{urllib.parse.quote(dataset)}?observations=0&limit=1")
    dd = payload.get("dataset", {}).get("dimensions_values_labels", {})
    if not dd:
        docs = payload.get("series", {}).get("docs", [{}])
        dd = docs[0].get("dimensions", {}) if docs else {}
    print(f"{spec} dimensions:\n")
    for axis, labels in dd.items():
        items = list(labels.items()) if isinstance(labels, dict) else labels
        print(f"  {axis}:")
        if isinstance(items, list):
            for pair in items[:40]:
                if isinstance(pair, (list, tuple)) and len(pair) == 2:
                    print(f"    {pair[0]} = {pair[1]}")


def inspect_series(provider, dataset, filt, year=2019, max_docs=120):
    """Query a PARTIAL dimension filter and print each returned series' full
    dimensions + its value for `year`. This reveals the exact code combination
    for the series we want (e.g. the BIS row whose value ~= % of GDP)."""
    q = urllib.parse.urlencode({
        "dimensions": json.dumps({k: (v if isinstance(v, list) else [v])
                                  for k, v in filt.items()}, separators=(",", ":")),
        "observations": "1", "limit": str(max_docs)})
    try:
        payload = _get(f"{_API}/series/{urllib.parse.quote(provider)}/"
                       f"{urllib.parse.quote(dataset)}?{q}")
    except Exception as e:
        print(f"  inspect_series failed: {type(e).__name__}: {e}")
        return
    docs = payload.get("series", {}).get("docs", [])
    print(f"  {len(docs)} series for {provider}/{dataset} filter={filt}:")
    for d in docs:
        dims = d.get("dimensions", {})
        periods = d.get("period", []) or d.get("original_period", [])
        vals = d.get("value", [])
        latest = None
        for pp, vv in zip(periods, vals):
            try:
                fv = float(vv)
            except (TypeError, ValueError):
                continue
            latest = (pp, fv)                     # keep the last non-null
        sig = ",".join(f"{k}={dims[k]}" for k in sorted(dims))
        shown = f"{latest[1]} @{latest[0]}" if latest else "(no data)"
        print(f"    {shown}   <-  {sig}")


def test_force_live(geo="DE", year=2019):
    conn = DBnomicsConnector(allow_live=True)
    bound = series_for_geo(geo)
    for code in ("hh_debt_gdp", "top10_wealth_share"):
        s = bound[code]
        print(f"\n{code}: current schema -> {s.hint()}  (live={s.live})")
        row = conn.fetch_one(geo, year, code, allow_live=True, force_live=True)
        if row and row.get("source") == "live":
            print(f"  FORCE-LIVE OK: value={row['value']} "
                  f"obs_year={row.get('obs_year')} matched={row.get('provider_code')}")
            print("  (verify this is the RIGHT series — %GDP household debt / "
                  "top-10% net wealth — not a different unit/sector.)")
        else:
            print("  force-live did NOT resolve with current dims -> the dataset "
                  "or dimensions need fixing (use --dims on the discovered dataset).")


def _top_for(hits, prefer_provider):
    """Pick the most relevant hit, preferring a provider and inequality keywords."""
    def score(h):
        blob = f"{h['provider']} {h['dataset']} {h.get('name','')}".lower()
        return (h["provider"].upper() == prefer_provider) * 10 + sum(
            k in blob for k in ("credit", "debt", "household", "wealth",
                                "top", "decile", "gdp"))
    return max(hits, key=score) if hits else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dims", default=None, metavar="PROVIDER/DATASET",
                    help="dump one dataset's dimensions")
    args = ap.parse_args()
    if args.dims:
        dump_dims(args.dims)
        return 0

    print("=" * 70)
    print("BIS — household debt (hh_debt_gdp). Discovering datasets...")
    bis = discover(["BIS credit to households to GDP", "total credit households",
                    "BIS debt service ratio households", "credit to GDP households"])
    for h in bis[:10]:
        print(f"  {h['provider']}/{h['dataset']}  (series={h['nb']})  {h['name']}")
    print("\n-- ACTUAL BIS/WS_TC series for DE households annual (find the % "
          "of GDP row, ~54) --")
    inspect_series("BIS", "WS_TC",
                   {"BORROWERS_CTY": "DE", "TC_BORROWERS": "H", "FREQ": "Q"})

    print("\n" + "=" * 70)
    print("WID — top-10% wealth share (top10_wealth_share). Discovering datasets...")
    # WID is not a DBnomics provider for this; the real source is the OECD
    # Wealth Distribution Database (DSD_WEALTH). Show its dimensions + sample.
    WEALTH_DS = "OECD/DSD_WEALTH@DF_WEALTH"
    print(f"-- dimensions of {WEALTH_DS} (OECD Wealth Distribution Database) --")
    try:
        dump_dims(WEALTH_DS)
    except Exception as e:
        print(f"  dims failed: {e}")
    print(f"\n-- ACTUAL {WEALTH_DS} series for DE (find the TOP-10% net wealth "
          "share, ~0.6) --")
    inspect_series("OECD", "DSD_WEALTH@DF_WEALTH",
                   {"REF_AREA": "DEU", "MEASURE": "SH_TOP10"})

    print("\n" + "=" * 70)
    print("Force-live test of the CURRENT schema dims (DE)...")
    test_force_live()
    print("\nPASTE THIS WHOLE OUTPUT to Claude — it has the datasets, their real "
          "dimension codes, and whether the current dims resolve. Claude will set "
          "the confirmed dataset/dims + live=True in schema/accounts.py; then run "
          "`python scripts/verify_live.py --geo DE` and "
          "`python scripts/build_snapshot.py --geo <all> --write`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
