#!/usr/bin/env python3
"""Patch the agora-dashboard artifact's sectoral I-O data with the REAL
Eurostat matrix (after build_io.py --write). Run on YOUR machine — it reads the
local io_{geo}.json + recomputes the sectoral panel from the gated engine, so it
needs no network and no mount.

  python scripts/patch_dashboard.py --dry-run     # show what would change
  python scripts/patch_dashboard.py               # patch in place (.bak saved)
  python scripts/patch_dashboard.py --html PATH   # custom artifact path

Default artifact path: %USERPROFILE%\\Documents\\Claude\\Artifacts\\agora-dashboard\\index.html
It recomputes io ONLY for geos that already have an io block AND a real io_*.json
(matrix_source 'real'); others (illustrative) are left untouched. The DATA blob
is extracted with a JSON decoder (robust to nested braces) and re-serialised.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import AgoraOrchestrator        # noqa: E402
from modules.input_output import load_io           # noqa: E402

_MARKER = "const DATA = "


def _default_html() -> str:
    return os.path.join(os.path.expanduser("~"), "Documents", "Claude",
                        "Artifacts", "agora-dashboard", "index.html")


def _round_map(sectors, vals, nd=3):
    return {s: round(v, nd) for s, v in zip(sectors, vals)}


def compute_io_by_scenario(geo: str) -> dict:
    """{scenario_name: io_dict} from the gated engine on the local real matrix.
    io_dict matches the artifact schema: sectors, multipliers, exposure,
    lshare_start, lshare_end (+ va/output if the existing block carries them)."""
    o = AgoraOrchestrator(geo=geo, year=2019, allow_live=False, strict=True)
    o.load_data()
    out = {}
    for run in o.run_triad(horizon=30):
        io_res = run.io
        if io_res is None or not io_res.periods:
            continue
        sectors = io_res.meta["sectors"]
        n = len(sectors)
        mult = io_res.meta["multipliers"]
        expo = io_res.meta["automation_exposure"]
        p0, pL = io_res.periods[0].reported, io_res.periods[-1].reported
        out[run.scenario] = {
            "sectors": sectors,
            "multipliers": {s: round(mult[s], 3) for s in sectors},
            "exposure": {s: round(expo[s], 3) for s in sectors},
            "lshare_start": [round(p0[f"lshare_{i+1}"], 4) for i in range(n)],
            "lshare_end": [round(pL[f"lshare_{i+1}"], 4) for i in range(n)],
            "va": [round(pL[f"va_{i+1}"], 1) for i in range(n)],
            "output": [round(pL[f"output_{i+1}"], 1) for i in range(n)],
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=_default_html())
    ap.add_argument("--geos", nargs="+", default=["DE", "FR"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.html):
        print(f"artifact not found: {args.html}\nPass --html with the correct path.")
        return 1
    html = open(args.html, encoding="utf-8").read()
    if _MARKER not in html:
        print("could not find `const DATA = ` in the artifact.")
        return 1
    i = html.index(_MARKER) + len(_MARKER)
    data, end = json.JSONDecoder().raw_decode(html, i)

    geos = data.get("geos", {})
    changed = []
    for geo in args.geos:
        gkey = geo.upper()
        if gkey not in geos or "triad" not in geos[gkey]:
            print(f"{gkey}: no triad in DATA — skipped"); continue
        io_local = load_io(gkey)
        if not (io_local and io_local.get("A")):
            print(f"{gkey}: no REAL io_{gkey.lower()}.json (matrix_source real) — skipped")
            continue
        new_io = compute_io_by_scenario(gkey)
        triad = geos[gkey]["triad"]
        for scn, scn_obj in triad.items():
            if not isinstance(scn_obj, dict) or "io" not in scn_obj:
                continue
            if scn not in new_io:
                continue
            # keep only the keys the existing io block uses (schema-preserving),
            # but always refresh the core fields
            existing_keys = set(scn_obj["io"].keys())
            merged = {k: v for k, v in new_io[scn].items()
                      if k in existing_keys or k in
                      ("sectors", "multipliers", "exposure",
                       "lshare_start", "lshare_end")}
            scn_obj["io"] = merged
        changed.append(gkey)
        m = new_io.get("AI shift, no policy", {})
        print(f"{gkey}: io refreshed (real matrix). AI-shift multipliers="
              f"{m.get('multipliers')}")
        print(f"      lshare_start={m.get('lshare_start')}")
        print(f"      lshare_end  ={m.get('lshare_end')}")

    if not changed:
        print("nothing changed.")
        return 0
    if args.dry_run:
        print("\n--dry-run: no file written. Re-run without --dry-run to apply.")
        return 0

    new_json = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    new_html = html[:i] + new_json + html[end:]
    bak = args.html + ".bak"
    if not os.path.exists(bak):
        open(bak, "w", encoding="utf-8").write(html)
    open(args.html, "w", encoding="utf-8").write(new_html)
    print(f"\npatched {args.html} (backup: {bak}) — geos updated: {changed}")
    print("Reload the artifact to see the real sectoral matrix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
