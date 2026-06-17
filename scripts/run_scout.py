#!/usr/bin/env python3
"""Run the AGORA scout — writes proposals for your review (applies nothing).

    python scripts/run_scout.py --geo DE FR          # live + local Qwen if up
    python scripts/run_scout.py --no-llm             # deterministic only
    python scripts/run_scout.py --offline            # no network (snapshot)
    python scripts/run_scout.py --discover           # + live DBnomics dataset scan

Configure the local model via env: AGORA_LLM_BASE_URL, AGORA_LLM_MODEL.
Schedule it daily (Windows Task Scheduler / cron) — see docs/SCOUT.md.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scout.scout import run_scout  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", nargs="+", default=["DE", "FR"])
    ap.add_argument("--year", type=int, default=2019)
    ap.add_argument("--no-llm", action="store_true", help="skip the Qwen brief/patches")
    ap.add_argument("--offline", action="store_true", help="no live DBnomics")
    ap.add_argument("--discover", action="store_true",
                    help="also scan DBnomics dataset lists (live, slower)")
    ap.add_argument("--max-patches", type=int, default=6)
    ap.add_argument("--force", action="store_true",
                    help="write a report even if findings are unchanged")
    ap.add_argument("--out", default=None, help="proposals output dir")
    args = ap.parse_args()

    res = run_scout(
        geos=args.geo, year=args.year,
        use_llm="off" if args.no_llm else "auto",
        allow_live=not args.offline, out_dir=args.out,
        discover=args.discover, max_patches=args.max_patches, force=args.force)

    print(f"AGORA scout — {', '.join(args.geo)} {args.year}")
    print(f"  findings: {res['n_findings']}  "
          f"({', '.join(f'{k}:{v}' for k, v in res['by_kind'].items())})")
    if not res.get("changed", True):
        print("  no change vs the most recent report — nothing surfaced.")
        print(f"  prior report: {res.get('prior_report')}")
        print("  (run with --force to write a report anyway.)")
        return 0
    print(f"  Qwen brief: {'yes' if res['llm_used'] else 'no'}  "
          f"| draft patches: {res['patches']} ({res['flagged_paths']} path-flagged)")
    print(f"  report: {res['report']}")
    print("\n  All items are PENDING_REVIEW — nothing was applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
