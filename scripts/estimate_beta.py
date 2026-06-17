#!/usr/bin/env python3
"""Estimate beta (capital share -> inequality elasticity) from the live panel.

Run on a machine WITH network access.

  python scripts/estimate_beta.py --years 2010 2024
  python scripts/estimate_beta.py --geo DE FR PL IT ES NL --years 2005 2024

Beta is the elasticity of MARKET (pre-tax-pre-transfer) inequality to the
capital share. The disposable-Gini panel (EU-SILC) is a LOWER anchor only
(redistribution absorbs the shift, F12); the OECD IDD market Gini is the
variable beta is actually defined on. To resolve the OECD/IDD live codes
(DBnomics restructured OECD, so the dataset code must be discovered):

  python scripts/estimate_beta.py --probe-idd                 # find the dataset
  python scripts/estimate_beta.py --probe-dims OECD/<DATASET>  # list its dims

then edit data/cache/oecd_idd.json -> _meta.live_query and re-run --years.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest import (estimate_beta_panel, redistribution_wedge,  # noqa: E402
                      estimate_beta_market_cross_section,          # noqa: E402
                      estimate_beta_market_panel)                  # noqa: E402
from scout.checks import snapshot_geos                         # noqa: E402
from schema.accounts import AGGREGATE_GEOS                     # noqa: E402
from data.connectors.oecd_idd import OECDIDDConnector          # noqa: E402


def _probe_idd(geos) -> int:
    """Try the guessed OECD/IDD candidates, then DISCOVER the real income-
    distribution dataset via the DBnomics search API."""
    idd = OECDIDDConnector(allow_live=True)
    print("Probing OECD/IDD candidate datasets on DBnomics...\n")
    for entry in idd.probe(geos[0] if geos else "DE"):
        print(f"dataset: {entry['dataset']}  (geo_dim={entry.get('geo_dim')})")
        print(f"  current guessed dims: {entry.get('current_dims')}")
        if entry.get("ok"):
            print(f"  REAL dimension axes: {entry.get('dimension_axes')}")
            for axis, labels in (entry.get("dimensions_values_labels") or {}).items():
                vals = list(labels.items())[:12] if isinstance(labels, dict) else labels
                print(f"    {axis}: {vals}")
        else:
            print(f"  unavailable: {entry.get('error')}")
        print()
    print("Discovering income-distribution datasets on DBnomics (search API)...\n")
    hits = idd.discover_datasets()
    if hits:
        for h in hits[:20]:
            print(f"  {h['provider']}/{h['dataset']}  "
                  f"(series={h.get('nb_series')})  {h.get('name', '')}")
        print("\nPick the OECD income-distribution dataset above, then list its "
              "dimensions:\n"
              "  python scripts/estimate_beta.py --probe-dims PROVIDER/DATASET")
    else:
        print("  no search hits (offline or API shape changed).")
    print("\nThen edit data/cache/oecd_idd.json -> _meta.live_query.candidates so "
          "the before-tax Gini MEASURE + geo_dim match the chosen dataset, and "
          "re-run with --years.")
    return 0


def _probe_dims(spec: str) -> int:
    """Print the real dimensions of one PROVIDER/DATASET (from discovery), so the
    exact before-tax MEASURE + geo dimension codes can be read off."""
    import json as _json
    import urllib.parse as _up
    import urllib.request as _ur
    if "/" not in spec:
        print("usage: --probe-dims PROVIDER/DATASET")
        return 2
    provider, dataset = spec.split("/", 1)
    url = ("https://api.db.nomics.world/v22/series/"
           + _up.quote(provider) + "/" + _up.quote(dataset)
           + "?observations=0&limit=1")
    try:
        req = _ur.Request(url, headers={"User-Agent": "agora/0.2"})
        with _ur.urlopen(req, timeout=20) as r:
            payload = _json.loads(r.read().decode())
    except Exception as e:
        print(f"could not fetch {spec}: {type(e).__name__}: {e}")
        return 1
    dd = payload.get("dataset", {}).get("dimensions_values_labels", {})
    if not dd:
        docs = payload.get("series", {}).get("docs", [{}])
        dd = docs[0].get("dimensions", {}) if docs else {}
    print(f"{spec} dimensions:\n")
    for axis, labels in dd.items():
        items = list(labels.items()) if isinstance(labels, dict) else labels
        print(f"  {axis}:")
        if isinstance(items, list):
            for pair in items[:30]:
                if isinstance(pair, (list, tuple)) and len(pair) == 2:
                    print(f"    {pair[0]} = {pair[1]}")
                else:
                    print(f"    {pair}")
    print("\nSet _meta.live_query: geo_dim = the country axis (REF_AREA/LOCATION); "
          "dims = fix the geo placeholder + pick the MARKET (before tax & "
          "transfer) Gini MEASURE code above.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", nargs="+", default=None,
                    help="default: every snapshot country (aggregates excluded)")
    ap.add_argument("--years", nargs=2, type=int, default=[2010, 2024],
                    metavar=("FROM", "TO"))
    ap.add_argument("--probe-idd", action="store_true",
                    help="discover OECD income-distribution datasets and exit")
    ap.add_argument("--probe-dims", default=None, metavar="PROVIDER/DATASET",
                    help="list one dataset's dimensions (run after --probe-idd)")
    args = ap.parse_args()
    if args.probe_dims:
        return _probe_dims(args.probe_dims)
    geos = args.geo or [g for g in snapshot_geos()
                        if g.upper() not in AGGREGATE_GEOS]
    if args.probe_idd:
        return _probe_idd(geos)
    years = list(range(args.years[0], args.years[1] + 1))
    print(f"Panel: {len(geos)} countries x {years[0]}-{years[-1]} "
          f"(2 live requests per country)...")
    import backtest as _bt
    _orig = _bt.load_panel

    def _verbose(g, *a, **kw):
        print(f"  {g}...", flush=True)
        return _orig(g, *a, **kw)

    _bt.load_panel = _verbose
    b, r2, n, nc = estimate_beta_panel(geos, years, allow_live=True)
    _bt.load_panel = _orig
    print(f"\nbeta (FE, within-country, DISPOSABLE Gini) = {b:.3f}   "
          f"R^2 = {r2:.3f}   obs = {n}   countries = {nc}")
    print("Interpretation: LOWER anchor only (observed Gini is post-redistribution).")

    # MARKET-Gini diagnostics (OECD IDD) -- the variable beta is defined on.
    per, mean = redistribution_wedge(geos, allow_live=True)
    if per:
        print("\nRedistribution wedge (1 - disposable/market Gini, OECD IDD):")
        for g in sorted(per):
            print(f"  {g}: {per[g]:.3f}")
        print(f"  mean = {mean:.3f}  <- share of MARKET inequality removed by "
              "taxes & transfers; why the disposable-Gini beta is biased to ~0.")
        bm, am, r2m, nm = estimate_beta_market_cross_section(geos, allow_live=True)
        print(f"\nmarket-Gini cross-section (DIAGNOSTIC): beta={bm:.3f} "
              f"R^2={r2m:.3f} n={nm}  <- between-country, structurally confounded "
              "(often wrong sign); NOT a valid identification.")
        print("CORRECT route: within-country FE on the IDD market Gini (GINIB). "
              "Estimating it now...")
        bmp, r2mp, nmp, ncmp = estimate_beta_market_panel(geos, years,
                                                          allow_live=True)
        if ncmp > 0:
            print(f"\nMARKET-Gini FE panel (the F12 closer): beta={bmp:.3f} "
                  f"R^2={r2mp:.3f} obs={nmp} countries={ncmp}")
            print("This is the elasticity the model's beta IS. If credible, set "
                  "DistributionModule(beta=...) + tighten the prior; log in STATE.")
        else:
            print("\nMARKET-Gini FE panel: no multi-year market Gini resolved "
                  "(0 countries). The OECD/IDD live codes are unconfirmed - run "
                  "`--probe-idd`, then `--probe-dims`, edit _meta.live_query, retry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
