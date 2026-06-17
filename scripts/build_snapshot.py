#!/usr/bin/env python3
"""Self-populate baseline snapshots from live DBnomics — toward EU27.

Run on a machine WITH network access to https://api.db.nomics.world. For each
geo it pulls every calibration series live, reconciles imports, validates the
result through calibration (must reproduce the national-accounts targets + pass
the consistency gate), and prints a provenance report. DRY-RUN by default;
pass --write to persist data/cache/<geo>_baseline_<year>.json.

    python scripts/build_snapshot.py --geo PL                 # dry-run, review
    python scripts/build_snapshot.py --geo RO BG --write      # add two members
    python scripts/build_snapshot.py --geo DE --offline       # round-trip test

Human-gated by design (like the scout): review the report, then --write.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.connectors.dbnomics import DBnomicsConnector          # noqa: E402
from data.snapshot_builder import build_snapshot, write_snapshot_file  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Build baseline snapshots from live DBnomics.")
    ap.add_argument("--geo", nargs="+", required=True,
                    help="One or more Eurostat geo codes, e.g. PL RO BG EA20.")
    ap.add_argument("--year", type=int, default=2019)
    ap.add_argument("--write", action="store_true",
                    help="Write the snapshot file(s). Default: dry-run report only.")
    ap.add_argument("--offline", action="store_true",
                    help="No network (round-trip the bundled snapshots; for testing).")
    ap.add_argument("--reconcile", action="store_true",
                    help="Force imports = X - (GDP-C-I-G) so the identity closes "
                         "exactly. Default keeps the DIRECT imports pull and lets "
                         "the statistical discrepancy stand (tracked as nx_gap).")
    ap.add_argument("--force", action="store_true",
                    help="Write even if calibration validation FAILS (dangerous; for "
                         "diagnosis only). Default refuses to persist a divergent country.")
    ap.add_argument("--timeout", type=float, default=20.0)
    args = ap.parse_args()

    conn = DBnomicsConnector(timeout=args.timeout, allow_live=not args.offline)
    rc = 0
    for geo in args.geo:
        snap, rep = build_snapshot(
            geo, args.year, connector=conn,
            reconcile_imports=args.reconcile, validate=True)
        print("\n" + "=" * 64)
        print(rep.as_text())
        if not rep.buildable:
            print("  → NOT written: required series missing (needs live access "
                  "or manual sourcing).")
            rc = 1
            continue
        if rep.calibration_ok is False and not args.force:
            print("  → NOT written: FAILED calibration validation. Likely an "
                  "entrepôt / financial-centre economy whose trade >> GDP "
                  "destabilises the standalone open-economy closure (exports grow "
                  "with own output → unbounded). Model it only inside the "
                  "tight-trade regional fixed point, or exclude it. (--force to "
                  "override.)")
            rc = 1
            continue
        if args.write:
            path = write_snapshot_file(snap, geo, args.year)
            print(f"  → wrote {path}")
        else:
            print("  → dry-run (pass --write to persist). Review provenance first.")
    print("\n" + "=" * 64)
    print("Review flagged ('default_review') series and re-run verify_live before "
          "trusting any new country.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
