"""Capacity utilisation (Phase 7 step C) - the supply side's calibration data.

Source: European Commission Business and Consumer Surveys (BCS), manufacturing,
current level of capacity utilisation (% of full capacity), as published by
Eurostat in ei_bsin_q_r2 (indicator BS-ICU-PC, seasonally adjusted, quarterly)
for all 27 members. scripts/build_capacity.py reads it in ONE call from the
DBnomics mirror; a country missing there falls back, in order, to
  - the Bundesbank mirror on DBnomics (annual; euro-area members only):
        BUBA/BBXS1/A.{GEO}.N.EUBUCS.MANU.MAN013.TT.PCT.I00
  - the same Eurostat series per country on DBnomics, SA then NSA,
  - the Eurostat API (JSON-stat).
Quarterly values are averaged to calendar years. (The Bundesbank annual
values equal the Eurostat annual means for the 21 members both cover.)

The cache keeps the annual series up to the base year, and the calibration is
derived from it at load time (nothing after 2019 leaks in):
    normal = mean of the NORMAL_YEARS years to the base year -> zero output gap
    base   = the base-year value                             -> the 2019 gap
    max    = the historical maximum                          -> the output ceiling
    min    = the lowest year in the same window (2009)          -> plausibility range
"Normal" uses a recent window, not the full history: in the central and
eastern members the 1990s transition years sit 10-15 pp below anything seen
since, so a full-history mean would make 2019 look like a 20% boom.

scripts/build_capacity.py writes data/cache/capacity_utilisation.json on a
machine that can reach DBnomics. A country missing from the cache gets a
FLAGGED default: Germany's long-run mean (83.7%) and maximum (89.7%) of the
same series, 1985-2025 (read from DBnomics on 2026-10-29), with 2019 treated
as a normal year.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from functools import lru_cache
from typing import Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(_ROOT, "data", "cache", "capacity_utilisation.json")
SERIES = "BUBA/BBXS1/A.{g}.N.EUBUCS.MANU.MAN013.TT.PCT.I00"
_API = "https://api.db.nomics.world/v22/series/" + SERIES + "?observations=1"
_GEO = {"EL": "GR"}                  # DBnomics/BUBA codes Greece as GR
EUROSTAT_SERIES = "Eurostat/ei_bsin_q_r2/Q.BS-ICU-PC.{adj}.{g}"
_API_ESTAT_DBN = "https://api.db.nomics.world/v22/series/" + EUROSTAT_SERIES + "?observations=1"
_API_ESTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
              "ei_bsin_q_r2?format=JSON&lang=EN&indic=BS-ICU-PC&s_adj={adj}&geo={g}")
_API_ESTAT_BULK = ("https://api.db.nomics.world/v22/series/Eurostat/ei_bsin_q_r2?dimensions="
                   + urllib.parse.quote('{"indic":["BS-ICU-PC"],"s_adj":["SA"]}')
                   + "&observations=1&limit=100")
MIN_HEADROOM = 0.02                  # ceiling at least 2 pp above the base year
NORMAL_YEARS = 15                    # "normal" = mean of 2005-2019 for a 2019 base
MIN_QUARTERS = 2                     # a quarterly year needs >= 2 observations
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


def capacity_utilisation_for(geo: Optional[str], cache_path: str = CACHE,
                             base_year: int = 2019) -> Dict[str, object]:
    """{normal, base, max, min} as fractions, plus flag ('live'|'default') and source."""
    try:
        mtime = os.path.getmtime(cache_path)
    except OSError:
        return dict(DEFAULT)
    rec = _load(cache_path, mtime).get((geo or "").upper())
    if not rec:
        return dict(DEFAULT)
    if rec.get("series"):                       # derive at load time from the series
        yrs = sorted(rec["series"])
        summ = summarise(yrs, [rec["series"][y] for y in yrs], base_year, scale=1.0)
        if summ:
            rec = {**rec, **summ}
    base = float(rec["base"])
    return {"normal": float(rec["normal"]), "base": base,
            "max": max(float(rec["max"]), base + MIN_HEADROOM),
            "min": float(rec["min"]) if rec.get("min") is not None else None,
            "flag": "live", "source": rec.get("source", SERIES)}


def annualise(periods: List[str], values: List[object]) -> Dict[int, float]:
    """Calendar-year means of a quarterly (or annual) series; NaN/None dropped."""
    acc: Dict[int, List[float]] = {}
    quarterly = any("Q" in str(p).upper() for p in periods)
    for per, val in zip(periods, values):
        try:
            y, v = int(str(per)[:4]), float(val)
        except (TypeError, ValueError):
            continue
        if v == v:
            acc.setdefault(y, []).append(v)
    need = MIN_QUARTERS if quarterly else 1
    return {y: sum(v) / len(v) for y, v in acc.items() if len(v) >= need}


def summarise(periods: List[str], values: List[object], base_year: int = 2019,
              scale: float = 100.0, normal_years: int = NORMAL_YEARS
              ) -> Optional[Dict[str, object]]:
    """Reduce a series (percent by default; scale=1 for fractions) to
    {normal, base, max, min} as fractions, using only years up to and
    including the base year. Also returns the annual series it used."""
    annual = {y: v / scale for y, v in annualise(periods, values).items() if y <= base_year}
    if base_year not in annual:
        return None
    yrs = sorted(annual)
    window = [annual[y] for y in yrs if y > base_year - normal_years]
    vals = [annual[y] for y in yrs]
    return {"normal": round(sum(window) / len(window), 4),
            "base": round(annual[base_year], 4), "max": round(max(vals), 4),
            "min": round(min(window), 4), "n_obs": len(vals),
            "normal_window": f"{max(yrs[0], base_year - normal_years + 1)}-{base_year}",
            "first_year": yrs[0], "last_year": base_year,
            "series": {str(y): round(annual[y], 4) for y in yrs}}


def parse_jsonstat(payload: dict):
    """(periods, values) from a Eurostat JSON-stat 2.0 response filtered to a
    single series (every non-time dimension has one category)."""
    ids = payload.get("id") or list(payload.get("dimension", {}).keys())
    sizes = payload.get("size") or [1] * len(ids)
    if "time" not in ids:
        return [], []
    k = ids.index("time")
    stride = 1
    for n in sizes[k + 1:]:
        stride *= int(n)
    tindex = payload["dimension"]["time"]["category"]["index"]
    if isinstance(tindex, list):
        tindex = {p: i for i, p in enumerate(tindex)}
    raw = payload.get("value", {})
    get = (lambda j: raw.get(str(j))) if isinstance(raw, dict) else (
        lambda j: raw[j] if j < len(raw) else None)
    periods = sorted(tindex, key=tindex.get)
    return periods, [get(tindex[p] * stride) for p in periods]


def _get_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "agora/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _dbnomics(url: str, timeout: float):
    docs = _get_json(url, timeout).get("series", {}).get("docs", [])
    return (docs[0].get("period", []), docs[0].get("value", [])) if docs else ([], [])


def from_dbnomics_docs(docs: List[dict], base_year: int = 2019,
                       label: str = "Eurostat ei_bsin_q_r2 BS-ICU-PC SA (DBnomics)",
                       route: str = "Eurostat/DBnomics SA") -> Dict[str, dict]:
    """{geo: summary} for every DBnomics series doc that has a base-year value."""
    out = {}
    for doc in docs:
        geo = (doc.get("dimensions") or {}).get("geo")
        if not geo:
            continue
        rec = summarise(doc.get("period", []), doc.get("value", []), base_year)
        if rec:
            rec["route"] = route
            rec["source"] = (f"EC BCS manufacturing capacity utilisation, {label}, "
                             f"quarterly averaged to years, {rec['first_year']}-{base_year} "
                             f"({rec['n_obs']} yrs)")
            out[geo.upper()] = rec
    return out


def fetch_all(base_year: int = 2019, timeout: float = 60.0) -> Dict[str, dict]:
    """Every country's series from Eurostat ei_bsin_q_r2 on DBnomics, one call."""
    return from_dbnomics_docs(_get_json(_API_ESTAT_BULK, timeout)
                              .get("series", {}).get("docs", []), base_year)


def fetch_live(geo: str, base_year: int = 2019, timeout: float = 20.0
               ) -> Optional[Dict[str, object]]:
    """One country, for when fetch_all misses it: BUBA (annual), then Eurostat
    ei_bsin_q_r2 via DBnomics, then the Eurostat API. Returns the summary of the first route with a base-year value;
    raises the last error if every route failed."""
    g = geo.upper()
    routes = [(lambda: _dbnomics(_API.format(g=_GEO.get(g, g)), timeout),
               f"DBnomics {SERIES.format(g=_GEO.get(g, g))} (annual)", "BUBA")]
    for adj in ("SA", "NSA"):
        routes.append((lambda adj=adj: _dbnomics(_API_ESTAT_DBN.format(adj=adj, g=g), timeout),
                       f"DBnomics {EUROSTAT_SERIES.format(adj=adj, g=g)} (quarterly, annual mean)",
                       f"Eurostat/DBnomics {adj}"))
        routes.append((lambda adj=adj: parse_jsonstat(_get_json(_API_ESTAT.format(adj=adj, g=g),
                                                                timeout)),
                       f"Eurostat API ei_bsin_q_r2 BS-ICU-PC {adj} {g} (quarterly, annual mean)",
                       f"Eurostat API {adj}"))
    last_err = None
    for fetch, label, route in routes:
        try:
            periods, values = fetch()
        except Exception as e:                  # 404 / network: try the next route
            last_err = e
            continue
        out = summarise(periods, values, base_year)
        if out:
            out["route"] = route
            out["source"] = (f"EC BCS manufacturing capacity utilisation, {label}, "
                             f"{out['first_year']}-{base_year} ({out['n_obs']} yrs)")
            return out
    if last_err is not None:
        raise last_err
    return None
