"""Self-populating baseline snapshots from live DBnomics (Phase 5 — toward EU27).

Adding an EU country should be 'run the builder, review, write' — not hand-typing
a JSON. `build_snapshot` pulls every calibration series live (via the existing
DBnomics connector, BY DIMENSIONS), stamps full provenance, reconciles imports to
the expenditure identity where needed, flags anything that must be sourced by
hand, and — crucially — VALIDATES the result through calibration before it is
trusted (the 'validate before trusting' principle: a freshly pulled country must
reproduce its own national-accounts targets and pass the consistency gate).

The sandbox here is firewalled from DBnomics, so live pulls run on the user's
machine (like the scout). Offline, the builder round-trips the bundled snapshots,
which is what the tests exercise.

Series coverage: the 9 Eurostat national-accounts/Gini/population series pull live
today. labour_share (AMECO), hh_debt_gdp (BIS) and top10_wealth_share (WID) are
attempted live (force_live) and, if their provider dimensions don't resolve, fall
back to a clearly-FLAGGED regional default for review.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from schema.accounts import series_for_geo
from data.connectors.dbnomics import DBnomicsConnector

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

# Flagged regional defaults for series whose provider dimensions may not resolve
# live for a new country. Used ONLY when both live and snapshot fail; always
# stamped source='default_review' so the reviewer knows to source them properly.
REGIONAL_DEFAULTS: Dict[str, float] = {
    "labour_share": 57.0,        # EU-ish adjusted wage share (% of GDP)
    "hh_debt_gdp": 50.0,         # placeholder household-debt ratio
    "top10_wealth_share": 0.55,  # placeholder top-10% wealth share
}
# series the macro calibration cannot run without
REQUIRED = ("gdp", "hh_consumption", "gov_consumption", "gfcf",
            "gini_disp_income", "population", "gov_debt_gdp", "labour_share")


@dataclass
class BuildReport:
    geo: str
    year: int
    live: List[str] = field(default_factory=list)
    snapshot: List[str] = field(default_factory=list)
    defaulted: List[str] = field(default_factory=list)
    reconciled: List[str] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    year_mismatch: List[str] = field(default_factory=list)  # live value from another year
    identity_residual: float = 0.0          # |GDP - (C+I+G+X-M)| in MEUR
    buildable: bool = True
    calibration_ok: Optional[bool] = None
    validation_failures: List[str] = field(default_factory=list)
    worst_gate_residual: Optional[float] = None

    def as_text(self) -> str:
        L = [f"{self.geo} {self.year}: live={len(self.live)} "
             f"snapshot={len(self.snapshot)} defaulted={len(self.defaulted)}"]
        if self.reconciled:
            L.append(f"  reconciled: {', '.join(self.reconciled)}")
        if self.defaulted:
            L.append(f"  ⚠ defaulted (source by hand): {', '.join(self.defaulted)}")
        if self.missing_required:
            L.append(f"  ✗ MISSING REQUIRED: {', '.join(self.missing_required)}")
        if self.year_mismatch:
            L.append(f"  ⚠ off-year live values (obs_year != {self.year}): "
                     f"{', '.join(self.year_mismatch)}")
        L.append(f"  identity |GDP-(C+I+G+X-M)| = {self.identity_residual:,.0f} MEUR")
        if self.calibration_ok is not None:
            tag = "PASS" if self.calibration_ok else "FAIL"
            L.append(f"  calibration validation: {tag}"
                     + (f" (gate worst {self.worst_gate_residual:.1e})"
                        if self.worst_gate_residual is not None else ""))
            if self.validation_failures:
                L.append(f"    failed targets: {', '.join(self.validation_failures)}")
        return "\n".join(L)


def _note(code: str, source: str) -> str:
    today = _dt.date.today().isoformat()
    if source == "live":
        return f"Live DBnomics pull ({today})."
    if source == "reconciled":
        return ("Imports reconciled to the expenditure identity: "
                "M = X - (GDP - C - I - G).")
    if source == "default_review":
        return (f"⚠ REGIONAL DEFAULT pending real sourcing — provider dimensions "
                f"did not resolve live for this geo on {today}. Verify before trusting.")
    return "From bundled snapshot."


def build_snapshot(geo: str, year: int = 2019,
                   connector: Optional[DBnomicsConnector] = None,
                   reconcile_imports: bool = False,
                   validate: bool = True) -> Tuple[dict, BuildReport]:
    """Build a sourced baseline-snapshot dict for `geo`/`year`. Returns
    (snapshot_dict, report). Does NOT write to disk (caller decides)."""
    conn = connector or DBnomicsConnector(allow_live=True)
    bound = series_for_geo(geo)
    rep = BuildReport(geo=geo.upper(), year=year)
    series: Dict[str, dict] = {}
    vals: Dict[str, float] = {}

    for code, s in bound.items():
        # respect the connector's allow_live (so --offline truly goes offline);
        # force_live only ATTEMPTS the snapshot-only providers when live is on.
        row = conn.fetch_one(geo, year, code, force_live=True)
        if row is not None:
            src = row["source"]
            (rep.live if src == "live" else rep.snapshot).append(code)
            entry = {
                "value": float(row["value"]), "unit": row.get("unit", s.unit),
                "provider": row.get("provider", s.provider),
                "provider_code": row.get("provider_code", s.hint()),
                "source_url": row.get("source_url", s.source_url),
                "note": _note(code, src), "source": src,
            }
            # provenance: a live pull may substitute the most recent year when
            # the requested one is missing - record it and FLAG the mismatch.
            oy = row.get("obs_year")
            if oy is not None:
                entry["obs_year"] = int(oy)
                if src == "live" and int(oy) != year:
                    rep.year_mismatch.append(code)
                    entry["note"] += (f" ⚠ value observed in {int(oy)}, not "
                                      f"{year} (requested year missing live).")
        elif code in REGIONAL_DEFAULTS:
            rep.defaulted.append(code)
            entry = {
                "value": float(REGIONAL_DEFAULTS[code]), "unit": s.unit,
                "provider": s.provider, "provider_code": s.hint(),
                "source_url": s.source_url, "note": _note(code, "default_review"),
                "source": "default_review",
            }
        else:
            continue                      # unresolved, no default → omit
        series[code] = entry
        vals[code] = entry["value"]

    # imports: POLICY (2026-06-11) - prefer the DIRECT pull; the statistical
    # discrepancy vs published GDP is tracked as nx_gap by calibration.
    # Reconcile to the identity only when imports is missing, or on request.
    have_components = all(k in vals for k in ("gdp", "hh_consumption", "gfcf",
                                              "gov_consumption", "exports"))
    if have_components and (reconcile_imports or "imports" not in vals):
        M = (vals["exports"]
             - (vals["gdp"] - vals["hh_consumption"] - vals["gfcf"]
                - vals["gov_consumption"]))
        s = bound["imports"]
        series["imports"] = {
            "value": float(M), "unit": s.unit, "provider": s.provider,
            "provider_code": s.hint(), "source_url": s.source_url,
            "note": _note("imports", "reconciled"), "source": "reconciled"}
        vals["imports"] = M
        rep.reconciled.append("imports")

    rep.missing_required = [c for c in REQUIRED if c not in vals]
    rep.buildable = not rep.missing_required
    if all(k in vals for k in ("gdp", "hh_consumption", "gfcf",
                               "gov_consumption", "exports", "imports")):
        inv = (vals["gcf"] - vals["gfcf"]) if "gcf" in vals else 0.0
        rep.identity_residual = abs(
            vals["gdp"] - (vals["hh_consumption"] + vals["gfcf"] + inv
                           + vals["gov_consumption"] + vals["exports"]
                           - vals["imports"]))

    snapshot = {
        "_meta": {
            "geo": geo.upper(), "year": year,
            "description": (f"Auto-built {geo.upper()} {year} baseline snapshot "
                            "(snapshot_builder, live DBnomics pull). Every value "
                            "carries provenance; review flagged defaults before "
                            "trusting."),
            "currency_unit": "MEUR (current prices)",
            "note": (f"Generated {_dt.date.today().isoformat()}. "
                     "Imports reconciled to the expenditure identity unless pulled "
                     "live. 'default_review' series need manual sourcing."),
        },
        "series": series,
    }

    if validate and rep.buildable:
        rep.calibration_ok, rep.validation_failures, rep.worst_gate_residual = \
            validate_snapshot(vals, geo, year)
    return snapshot, rep


def validate_snapshot(data: Dict[str, float], geo: str, year: int
                      ) -> Tuple[bool, List[str], float]:
    """Validate before trusting: does the pulled data calibrate, reproduce its
    own national-accounts targets at year 0, and pass the consistency gate?"""
    from calibration import calibrate
    from modules.sfc_core import SFCCore
    from scenarios import make_triad
    from consistency.checks import check_run
    try:
        p = calibrate(data, geo=geo, base_year=year)
        baseline = make_triad(p, horizon=5)[0]
        res = SFCCore(base_year=year).run(baseline, data)
        reports = check_run(res, strict=False)
        worst = max(r.max_residual for r in reports)
        m0, t = res.periods[0].reported, p.targets

        def off(metric, target, model, tol=0.005):
            denom = abs(target) or 1.0
            return abs(model - target) / denom > tol

        fails = []
        checks = [("GDP", t["gdp_expenditure"], m0["gdp"]),
                  ("hh_consumption", t["hh_consumption"], m0["consumption"]),
                  ("gfcf", t["gfcf"], m0["investment"]),
                  ("gov", t["gov_consumption"], m0["gov_expenditure"]),
                  ("labour_share", t["labour_share"], m0["labour_share"])]
        for nm, tg, mo in checks:
            if off(nm, tg, mo):
                fails.append(nm)
        return (not fails and worst < 1.0), fails, worst
    except Exception as exc:               # pragma: no cover
        return False, [f"exception: {exc}"], float("nan")


def write_snapshot_file(snapshot: dict, geo: str, year: int,
                        cache_dir: Optional[str] = None) -> str:
    path = os.path.join(cache_dir or _CACHE_DIR,
                        f"{geo.lower()}_baseline_{year}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2)
    return path
