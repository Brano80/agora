"""The capital stock (Phase 7 step F) - each country's own capital-output ratio
and depreciation rate, replacing the uniform K/Y = 3 and 6% a year.

Four AMECO variables, read from the DBnomics mirror (one call each), total
economy, national currency:
    OKND   net capital stock at constant (2020) prices
    PIGT   price deflator of gross fixed capital formation (2020 = 100)
    UKCT   consumption of fixed capital at current prices
    UVGD   gross domestic product at current prices
AMECO builds the stock by the perpetual-inventory method from national-accounts
investment (DG ECFIN, the stock used in the Commission's potential-output
estimates). The cache keeps the annual series to the base year; the
calibration is derived at load time:
    k_y    = OKND * PIGT / 100 / UVGD in the base year (net stock at
             replacement cost over GDP)
    delta  = mean over WINDOW of UKCT(t) / (OKND(t-1) * PIGT(t) / 100)
             (depreciation over the stock it wears down, at this year's prices)
so delta * k_y reproduces the national accounts' depreciation share of GDP,
and investment / stock - delta reproduces AMECO's growth of the real stock
(DE 2019: 1.13% against 1.07%).
A missing country gets the euro-area values (flag "default").
"""
from __future__ import annotations

import json
import os
import statistics
import urllib.request
from functools import lru_cache
from typing import Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(_ROOT, "data", "cache", "capital_stock.json")
WINDOW_YEARS = 5                      # depreciation: mean of the five years to the base year
# Euro area (EA20) 2019 values from the cache built 2026-11-08; used for a
# country missing from it.
DEFAULT = {"k_y": 2.96, "delta": 0.0595, "flag": "default",
           "source": "DEFAULT: euro area (AMECO OKND, PIGT, UKCT, UVGD). Run "
                     "scripts/build_capital.py --write for country values."}

AMECO_ISO = {"AUT": "AT", "BEL": "BE", "BGR": "BG", "CYP": "CY", "CZE": "CZ", "DEU": "DE",
             "DNK": "DK", "EST": "EE", "GRC": "EL", "ESP": "ES", "FIN": "FI", "FRA": "FR",
             "HRV": "HR", "HUN": "HU", "IRL": "IE", "ITA": "IT", "LTU": "LT", "LUX": "LU",
             "LVA": "LV", "MLT": "MT", "NLD": "NL", "POL": "PL", "PRT": "PT", "ROM": "RO",
             "SWE": "SE", "SVN": "SI", "SVK": "SK", "EA20": "EA20"}
# AMECO unit codes (second to fifth field of the series code): national
# currency for the stocks and flows, national currency 2020 = 100 for PIGT
UNIT = {"OKND": "1.0.0.0", "UKCT": "1.0.0.0", "UVGD": "1.0.0.0", "PIGT": "3.1.0.0"}
_DB = "https://api.db.nomics.world/v22/series/AMECO/"
API = {k: _DB + k + "?observations=1&limit=1000&format=json" for k in UNIT}


def from_dbnomics(docs: Dict[str, List[dict]], base_year: int = 2019) -> Dict[str, dict]:
    """{geo: {"series": {OKND|PIGT|UKCT|UVGD: {year: value}}}} from the four answers."""
    rec: Dict[str, dict] = {}
    for var, ds in docs.items():
        for d in ds:
            parts = str(d.get("series_code", "")).split(".")
            geo = AMECO_ISO.get(parts[0])
            if not geo or ".".join(parts[1:5]) != UNIT[var]:
                continue
            ser = {}
            for per, val in zip(d.get("period", []), d.get("value", [])):
                try:
                    y, v = int(str(per)[:4]), float(val)
                except (TypeError, ValueError):
                    continue
                if v == v and y <= base_year:
                    ser[str(y)] = v
            rec.setdefault(geo, {"series": {}})["series"][var] = ser
    return rec


def summarise(series: Dict[str, Dict[str, float]], base_year: int = 2019,
              window_years: int = WINDOW_YEARS) -> Optional[Dict[str, object]]:
    k, p, c, y = (series.get(v, {}) for v in ("OKND", "PIGT", "UKCT", "UVGD"))
    by = str(base_year)
    if not (by in k and by in p and y.get(by)):
        return None
    k_y = k[by] * p[by] / 100.0 / y[by]
    yrs = [t for t in range(base_year - window_years + 1, base_year + 1)
           if str(t) in c and str(t - 1) in k and str(t) in p]
    if len(yrs) < 3:
        return None
    deltas = [c[str(t)] / (k[str(t - 1)] * p[str(t)] / 100.0) for t in yrs]
    real_growth = (k[by] / k[str(base_year - 1)] - 1.0) if str(base_year - 1) in k else None
    return {"k_y": round(k_y, 4), "delta": round(statistics.mean(deltas), 5),
            "cfc_gdp": round(c[by] / y[by], 4) if by in c else None,
            "real_stock_growth": round(real_growth, 5) if real_growth is not None else None,
            "window": f"{yrs[0]}-{yrs[-1]}"}


@lru_cache(maxsize=8)
def _load(path: str, mtime: float) -> Dict[str, dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("countries", {})
    except Exception:
        return {}


def capital_position_for(geo: Optional[str], cache_path: str = CACHE,
                         base_year: int = 2019) -> Dict[str, object]:
    """{k_y, delta, cfc_gdp, real_stock_growth}, plus flag and source."""
    try:
        mtime = os.path.getmtime(cache_path)
    except OSError:
        return dict(DEFAULT)
    rec = _load(cache_path, mtime).get((geo or "").upper())
    s = summarise(rec["series"], base_year) if rec and rec.get("series") else None
    if not s:
        return dict(DEFAULT)
    return {**s, "flag": "live",
            "source": rec.get("source", "AMECO OKND, PIGT, UKCT, UVGD (DBnomics)")}


def _get_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "agora/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def fetch_all(base_year: int = 2019, timeout: float = 90.0) -> Dict[str, dict]:
    docs = {k: _get_json(u, timeout).get("series", {}).get("docs", []) for k, u in API.items()}
    return from_dbnomics(docs, base_year)
