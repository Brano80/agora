"""Government finances (Phase 7 step E) - the realistic fiscal block.

Eurostat gov_10dd_edpt1 (general government, % of GDP), read from the DBnomics
mirror in one call:
    GD      consolidated gross debt
    B9      net lending (+) / net borrowing (-)
    D41PAY  interest payable
The cache keeps the annual series to the base year; the calibration is derived
at load time:
    implicit_rate   = mean over WINDOW of interest(t) / debt(t-1)
    primary_balance = (B9 + D41PAY) in the base year, as a share of GDP
    debt            = gross debt in the base year, as a share of GDP
A missing country gets the EU-27 medians (flag "default").
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
CACHE = os.path.join(_ROOT, "data", "cache", "fiscal_positions.json")
WINDOW = (2015, 2019)
# EU-27 medians of the members, 2015-2019 rate / 2019 balance (cache built 2026-10-30)
DEFAULT = {"implicit_rate": 0.0247, "primary_balance": 0.017, "flag": "default",
           "source": "DEFAULT: EU-27 medians (Eurostat gov_10dd_edpt1). Run "
                     "scripts/build_fiscal.py --write for country values."}
API = ("https://api.db.nomics.world/v22/series/Eurostat/gov_10dd_edpt1?dimensions="
       + urllib.parse.quote(json.dumps({"na_item": ["GD", "B9", "D41PAY"], "sector": ["S13"],
                                        "unit": ["PC_GDP"]}, separators=(",", ":")))
       + "&observations=1&limit=1000")


def from_dbnomics(docs: List[dict], base_year: int = 2019) -> Dict[str, dict]:
    rec: Dict[str, dict] = {}
    for d in docs:
        dm = d.get("dimensions", {})
        ser = {}
        for per, val in zip(d.get("period", []), d.get("value", [])):
            try:
                y, v = int(str(per)[:4]), float(val)
            except (TypeError, ValueError):
                continue
            if v == v and y <= base_year:
                ser[str(y)] = v
        rec.setdefault(dm["geo"].upper(), {"series": {}})["series"][dm["na_item"]] = ser
    return rec


def summarise(series: Dict[str, Dict[str, float]], base_year: int = 2019,
              window=WINDOW) -> Optional[Dict[str, object]]:
    gd, b9, d41 = series.get("GD", {}), series.get("B9", {}), series.get("D41PAY", {})
    rates = [d41[str(y)] / gd[str(y - 1)] for y in range(window[0], window[1] + 1)
             if str(y) in d41 and gd.get(str(y - 1))]
    by = str(base_year)
    if len(rates) < 3 or by not in b9 or by not in d41 or by not in gd:
        return None
    return {"implicit_rate": round(statistics.mean(rates), 5),
            "primary_balance": round((b9[by] + d41[by]) / 100.0, 5),
            "debt": round(gd[by] / 100.0, 4), "window": f"{window[0]}-{window[1]}"}


@lru_cache(maxsize=8)
def _load(path: str, mtime: float) -> Dict[str, dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("countries", {})
    except Exception:
        return {}


def fiscal_position_for(geo: Optional[str], cache_path: str = CACHE,
                        base_year: int = 2019) -> Dict[str, object]:
    """{implicit_rate, primary_balance, debt} as fractions, plus flag and source."""
    try:
        mtime = os.path.getmtime(cache_path)
    except OSError:
        return dict(DEFAULT)
    rec = _load(cache_path, mtime).get((geo or "").upper())
    s = summarise(rec["series"], base_year) if rec and rec.get("series") else None
    if not s:
        return dict(DEFAULT)
    return {**s, "flag": "live",
            "source": rec.get("source", "Eurostat gov_10dd_edpt1 (GD, B9, D41PAY)")}


def fetch_all(base_year: int = 2019, timeout: float = 60.0) -> Dict[str, dict]:
    req = urllib.request.Request(API, headers={"User-Agent": "agora/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        docs = json.loads(resp.read().decode()).get("series", {}).get("docs", [])
    return from_dbnomics(docs, base_year)
