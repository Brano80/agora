"""External positions (Phase 7 step D) - who owns what across the border.

Three Eurostat tables, read from the DBnomics mirror (one call each):
  nasa_10_nf_tr  A.CP_MEUR.{RECV,PAID}.{D42,D43}.S2.{GEO}
      distributed income of corporations (D42, dividends) plus reinvested
      earnings on FDI (D43), seen from the rest of the world (S2):
      RECV = paid by residents to FOREIGN owners of domestic firms (inward),
      PAID = received by residents from their equity ABROAD (outward).
  nama_10_gdp    A.CP_MEUR.B1GQ.{GEO}                     nominal GDP
  tipsii10       A.NSA.FA.S1.S1.N_LE.WRL_REST.PC_GDP.{GEO}
      net international investment position, % of GDP (MIP scoreboard).

The cache keeps the annual series to the base year; the calibration is derived
at load time:
    inward_gdp  = mean over WINDOW of inward equity income / GDP
    outward_gdp = mean over WINDOW of outward equity income / GDP
    niip_gdp    = net international investment position / GDP, base year
The engine turns inward_gdp into the foreign-owned share of domestic capital
(inward / gross profits) and outward_gdp into owners' equity abroad (income /
R_WORLD).

CONDUITS. In NL, IE, LU, MT and CY most equity income only passes through
special-purpose entities (inward and outward both above 15% of GDP; LU and MT
above 100%). Those flows are not ownership of domestic capital, so a conduit
gets the median of the other members (flag "conduit"; step F reviews them).
A country missing from the cache gets the same medians (flag "default").
"""
from __future__ import annotations

import json
import os
import statistics
import urllib.parse
import urllib.request
from functools import lru_cache
from typing import Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(_ROOT, "data", "cache", "external_positions.json")
WINDOW = (2015, 2019)                 # five years to the base year
CONDUIT_INWARD_GDP = 0.15             # inward equity income above 15% of GDP = SPE conduit
# Nominal return on a diversified world equity portfolio: Norway's GPFG,
# annualised 6.64% in its currency basket 1998-2025 (net real 4.34% plus
# 2.13% inflation; NBIM Annual Report 2025, Table 5).
R_WORLD = 0.066
# Medians of the 22 non-conduit members, 2015-2019 (computed from the cache
# built 2026-10-29); used for conduits and missing countries.
DEFAULT = {"inward_gdp": 0.036, "outward_gdp": 0.017, "niip_gdp": 0.0,
           "flag": "default",
           "source": "DEFAULT: median of the non-conduit EU members (Eurostat "
                     "nasa_10_nf_tr D42+D43, 2015-2019); NIIP 0. Run "
                     "scripts/build_external.py --write for country values."}

_DBN = "https://api.db.nomics.world/v22/series/Eurostat/"


def _q(dataset: str, dims: dict) -> str:
    return (_DBN + dataset + "?dimensions="
            + urllib.parse.quote(json.dumps(dims, separators=(",", ":")))
            + "&observations=1&limit=1000")


API_D4 = _q("nasa_10_nf_tr", {"na_item": ["D42", "D43"], "sector": ["S2"],
                               "direct": ["RECV", "PAID"], "unit": ["CP_MEUR"]})
API_GDP = _q("nama_10_gdp", {"na_item": ["B1GQ"], "unit": ["CP_MEUR"]})
API_NIIP = _q("tipsii10", {"partner": ["WRL_REST"], "unit": ["PC_GDP"]})


def _annual(doc: dict, base_year: int) -> Dict[str, float]:
    out = {}
    for per, val in zip(doc.get("period", []), doc.get("value", [])):
        try:
            y, v = int(str(per)[:4]), float(val)
        except (TypeError, ValueError):
            continue
        if v == v and y <= base_year:
            out[str(y)] = v
    return out


def from_dbnomics(d4_docs: List[dict], gdp_docs: List[dict], niip_docs: List[dict],
                  base_year: int = 2019) -> Dict[str, dict]:
    """{geo: {"series": {...}}} - raw annual series up to the base year."""
    rec: Dict[str, dict] = {}

    def slot(g):
        return rec.setdefault(g.upper(), {"series": {"inward": {}, "outward": {},
                                                     "gdp": {}, "niip_pc_gdp": {}}})
    for d in d4_docs:
        dm = d.get("dimensions", {})
        key = "inward" if dm.get("direct") == "RECV" else "outward"
        ser = slot(dm["geo"])["series"][key]
        for y, v in _annual(d, base_year).items():
            ser[y] = ser.get(y, 0.0) + v              # D42 + D43
    for d in gdp_docs:
        slot(d["dimensions"]["geo"])["series"]["gdp"] = _annual(d, base_year)
    for d in niip_docs:
        dm = d.get("dimensions", {})
        if dm.get("unit", "PC_GDP") == "PC_GDP":
            slot(dm["geo"])["series"]["niip_pc_gdp"] = _annual(d, base_year)
    return rec


def summarise(series: Dict[str, Dict[str, float]], base_year: int = 2019,
              window=WINDOW) -> Optional[Dict[str, object]]:
    """Window means of inward / outward equity income over GDP, and the
    base-year NIIP. None when the base year or the window is missing."""
    inw, outw, gdp = series.get("inward", {}), series.get("outward", {}), series.get("gdp", {})
    yrs = [str(y) for y in range(window[0], window[1] + 1)
           if str(y) in inw and str(y) in outw and gdp.get(str(y))]
    niip = series.get("niip_pc_gdp", {}).get(str(base_year))
    if len(yrs) < 3 or niip is None:
        return None
    return {"inward_gdp": round(statistics.mean(inw[y] / gdp[y] for y in yrs), 5),
            "outward_gdp": round(statistics.mean(outw[y] / gdp[y] for y in yrs), 5),
            "niip_gdp": round(niip / 100.0, 4), "n_years": len(yrs),
            "window": f"{yrs[0]}-{yrs[-1]}"}


@lru_cache(maxsize=8)
def _load(path: str, mtime: float) -> Dict[str, dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("countries", {})
    except Exception:
        return {}


def external_position_for(geo: Optional[str], cache_path: str = CACHE,
                          base_year: int = 2019) -> Dict[str, object]:
    """{inward_gdp, outward_gdp, niip_gdp} as fractions of GDP, plus flag
    ('live' | 'conduit' | 'default') and source."""
    try:
        mtime = os.path.getmtime(cache_path)
    except OSError:
        return dict(DEFAULT)
    allrec = _load(cache_path, mtime)
    rec = allrec.get((geo or "").upper())
    summ = summarise(rec["series"], base_year) if rec and rec.get("series") else None
    if not summ:
        return dict(DEFAULT)
    out = {**summ, "flag": "live",
           "source": rec.get("source", "Eurostat nasa_10_nf_tr / nama_10_gdp / tipsii10")}
    if summ["inward_gdp"] > CONDUIT_INWARD_GDP:
        out.update(inward_gdp=DEFAULT["inward_gdp"], outward_gdp=DEFAULT["outward_gdp"],
                   flag="conduit",
                   observed_inward_gdp=summ["inward_gdp"],
                   observed_outward_gdp=summ["outward_gdp"])
    return out


def _get_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "agora/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def fetch_all(base_year: int = 2019, timeout: float = 60.0) -> Dict[str, dict]:
    docs = [_get_json(u, timeout).get("series", {}).get("docs", [])
            for u in (API_D4, API_GDP, API_NIIP)]
    return from_dbnomics(*docs, base_year=base_year)
