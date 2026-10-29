"""Capacity utilisation (Phase 7 step C) - the supply side's calibration data.

Source: European Commission Business and Consumer Surveys, manufacturing,
current level of capacity utilisation (% of full capacity), annual, via the
Bundesbank mirror on DBnomics:
    BUBA/BBXS1/A.{GEO}.N.EUBUCS.MANU.MAN013.TT.PCT.I00

Three numbers per country calibrate the supply side (all through the base year,
so nothing after 2019 leaks into the calibration):
    normal = long-run mean          -> "normal" utilisation (zero output gap)
    base   = the base-year value    -> where the economy started (2019 gap)
    max    = the historical maximum -> the ceiling on output

scripts/build_capacity.py writes data/cache/capacity_utilisation.json on a
machine that can reach DBnomics. A country missing from the cache gets a
FLAGGED default: Germany's long-run mean (83.7%) and maximum (89.7%) of the
same series, 1985-2025 (read from DBnomics on 2026-10-29), with 2019 treated
as a normal year.
"""
from __future__ import annotations

import json
import os
import urllib.request
from functools import lru_cache
from typing import Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(_ROOT, "data", "cache", "capacity_utilisation.json")
SERIES = "BUBA/BBXS1/A.{g}.N.EUBUCS.MANU.MAN013.TT.PCT.I00"
_API = "https://api.db.nomics.world/v22/series/" + SERIES + "?observations=1"
_GEO = {"EL": "GR"}                  # DBnomics/BUBA codes Greece as GR
MIN_HEADROOM = 0.02                  # ceiling at least 2 pp above the base year
DEFAULT = {
    "normal": 0.837, "base": 0.837, "max": 0.897, "flag": "default",
    "source": ("DEFAULT (country not yet pulled): Germany's long-run mean 83.7% and "
               "max 89.7% of EC BCS manufacturing capacity utilisation, 1985-2025, "
               "DBnomics " + SERIES.format(g="DE") + "; 2019 treated as normal. "
               "Run scripts/build_capacity.py --write for country values."),
}


@lru_cache(maxsize=8)
def _load(path: str, mtime: float) -> Dict[str, dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("countries", {})
    except Exception:
        return {}


def capacity_utilisation_for(geo: Optional[str], cache_path: str = CACHE) -> Dict[str, object]:
    """{normal, base, max} as fractions, plus flag ('live'|'default') and source."""
    try:
        mtime = os.path.getmtime(cache_path)
    except OSError:
        return dict(DEFAULT)
    rec = _load(cache_path, mtime).get((geo or "").upper())
    if not rec:
        return dict(DEFAULT)
    base = float(rec["base"])
    return {"normal": float(rec["normal"]), "base": base,
            "max": max(float(rec["max"]), base + MIN_HEADROOM),
            "flag": "live", "source": rec.get("source", SERIES)}


def summarise(periods: List[str], values: List[object], base_year: int = 2019
              ) -> Optional[Dict[str, object]]:
    """Reduce an annual series to {normal, base, max} (fractions), using only
    observations up to and including the base year."""
    obs = []
    for per, val in zip(periods, values):
        try:
            y, v = int(str(per)[:4]), float(val)
        except (TypeError, ValueError):
            continue
        if y <= base_year and v == v:          # drop NaN
            obs.append((y, v))
    if not obs or base_year not in {y for y, _ in obs}:
        return None
    vals = [v for _, v in obs]
    base = next(v for y, v in obs if y == base_year)
    return {"normal": round(sum(vals) / len(vals) / 100.0, 4),
            "base": round(base / 100.0, 4), "max": round(max(vals) / 100.0, 4),
            "n_obs": len(vals), "first_year": min(y for y, _ in obs),
            "last_year": base_year}


def fetch_live(geo: str, base_year: int = 2019, timeout: float = 20.0
               ) -> Optional[Dict[str, object]]:
    g = _GEO.get(geo.upper(), geo.upper())
    req = urllib.request.Request(_API.format(g=g), headers={"User-Agent": "agora/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode())
    docs = payload.get("series", {}).get("docs", [])
    if not docs:
        return None
    doc = docs[0]
    out = summarise(doc.get("period", []), doc.get("value", []), base_year)
    if out:
        out["source"] = (f"EC BCS manufacturing capacity utilisation, DBnomics "
                         f"{SERIES.format(g=g)}, {out['first_year']}-{base_year} "
                         f"({out['n_obs']} obs)")
    return out
