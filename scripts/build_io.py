#!/usr/bin/env python3
"""Build io_{geo}.json from REAL Eurostat input-output data (FIGARO/naio).

Run on a machine WITH network access. Self-discovering: tries the candidate
datasets in order and auto-detects the table's row/column dimensions. ALWAYS
run --probe first on a new setup — it prints the dataset structure so a wrong
guess is a visible diagnosis, not a silent bad matrix.

    python scripts/build_io.py --probe                      # inspect candidates
    python scripts/build_io.py --geo DE FR                  # dry-run + validate
    python scripts/build_io.py --geo DE FR --write          # persist

Validate-before-trust: a built structure must be PRODUCTIVE (A column sums
< 1), have sane coefficients, run through the I-O module against the SFC
baseline, and reconcile Σ sectoral VA == GDP via the existing gate check.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.connectors.figaro import (build_io_structure, probe, inspect,
                                    DATASET_CANDIDATES, SECTORS)  # noqa: E402
from scout.checks import snapshot_geos                          # noqa: E402
from schema.accounts import AGGREGATE_GEOS                      # noqa: E402

_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "cache")


def validate_io(io: dict, geo: str, year: int):
    """Productive matrix + sane coefficients + module run reconciles to GDP."""
    n = len(io["sectors"])
    fails = []
    A = io.get("A") or []
    for j in range(n):
        cs = sum(A[i][j] for i in range(n)) if A else 0.0
        if cs >= 0.95:
            fails.append(f"A colsum[{j}]={cs:.2f} (not productive)")
    for k in ("va_coeff", "labour_share_sector"):
        if not all(0.0 < v < 1.0 for v in io[k]):
            fails.append(f"{k} outside (0,1)")
    if abs(sum(io["final_demand_shares"]) - 1.0) > 1e-6:
        fails.append("final_demand_shares do not sum to 1")
    if fails:
        return False, fails, None
    # run the chain against this structure and gate the reconciliation
    from orchestrator import AgoraOrchestrator
    from consistency.checks import check_input_output
    import modules.input_output as iom
    orig = iom.load_io
    iom.load_io = lambda g: io if g.upper() == geo.upper() else orig(g)
    try:
        o = AgoraOrchestrator(geo=geo, year=year, allow_live=False, strict=True)
        o.load_data()
        run = o.run_triad(horizon=5)[0]
        reps = check_input_output(run.io)
        worst = max(r.max_residual for r in reps)
        if not all(r.passed for r in reps):
            fails.append(f"VA reconciliation failed (worst {worst:.3g})")
        mult = run.io.meta["multipliers"]
        if not all(1.0 <= m <= 5.0 for m in mult.values()):
            fails.append(f"implausible multipliers: {mult}")
        return (not fails), fails, {"worst_resid": worst, "multipliers": mult}
    finally:
        iom.load_io = orig


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", nargs="+", default=[])
    ap.add_argument("--year", type=int, default=2019)
    ap.add_argument("--dataset", default=None,
                    help=f"override; default tries {DATASET_CANDIDATES}")
    ap.add_argument("--stk-flow", default=None)
    ap.add_argument("--probe", action="store_true",
                    help="print each candidate dataset's structure and exit")
    ap.add_argument("--inspect", default=None, metavar="GEO",
                    help="deep per-row diagnostic for GEO (why 'only N cells'); exits")
    ap.add_argument("--all", action="store_true",
                    help="build for every snapshot country (aggregates excluded)")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if args.all:
        args.geo = [g for g in snapshot_geos()
                    if g.upper() not in AGGREGATE_GEOS]

    if args.probe:
        for ds in ([args.dataset] if args.dataset else DATASET_CANDIDATES):
            print(f"\n=== Eurostat/{ds} ===")
            try:
                for dim, vals in probe(ds).items():
                    print(f"  {dim}: {len(vals)} values, e.g. {vals[:8]}")
            except Exception as exc:
                print(f"  probe failed: {exc}")
        return 0

    if args.inspect:
        for ds in ([args.dataset] if args.dataset else DATASET_CANDIDATES):
            print(f"\n=== inspect Eurostat/{ds} for {args.inspect} ===")
            try:
                inspect(args.inspect, ds, stk_flow=args.stk_flow)
            except Exception as exc:
                print(f"  inspect failed: {exc}")
        return 0

    if not args.geo:
        print("--geo required (or --probe)"); return 1
    rc = 0
    for geo in args.geo:
        print("\n" + "=" * 64)
        try:
            io, rep = build_io_structure(geo, args.year, dataset=args.dataset,
                                         stk_flow=args.stk_flow)
        except Exception as exc:
            print(f"{geo}: BUILD FAILED — {exc}")
            rc = 1
            continue
        print(f"{geo} {args.year}: {rep['dataset']}/{rep['stk_flow']} "
              f"(io year {rep.get('io_year', args.year)}, {rep['n_cells']} cells, "
              f"axes {rep.get('axes')}); labour shares: {rep['labour_share_source']}")
        if rep["tried"]:
            print(f"  fell through: {rep['tried']}")
        ok, fails, info = validate_io(io, geo, args.year)
        if info:
            print(f"  validation: {'PASS' if ok else 'FAIL'} "
                  f"(VA reconcile worst {info['worst_resid']:.1e})")
            print("  multipliers: " + ", ".join(
                f"{s.split(',')[0].split(' &')[0]} {m:.2f}"
                for s, m in info["multipliers"].items()))
        if not ok:
            print(f"  ✗ NOT written: {fails}")
            rc = 1
            continue
        if args.write:
            path = os.path.join(_CACHE, f"io_{geo.lower()}.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(io, fh, indent=1)
            print(f"  → wrote {path}")
        else:
            print("  → dry-run (pass --write to persist)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
