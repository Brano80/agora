"""Existing private debt (Phase 7 step F) - the loans on banks' books.

Eurostat nasa_10_f_bs, consolidated, % of GDP, liabilities, loans (F4), read
from the DBnomics mirror in one call:
    S11       non-financial corporations
    S14_S15   households and non-profit institutions serving them
The engine puts both on the financial sector's books in the base year: the
domestically owned firms' share (1 - the foreign stake) is owed by the owners,
household loans by workers and owners in proportion to their base-year
disposable income. Each stays a constant share of GDP (old loans are repaid
and new ones taken at the same pace) and pays the loan rate; deposits gross
up by the same amounts, so households' NET financial wealth is unchanged.
Before this, deposits were the government's bonds plus the foreign
debt-type position alone: SK 0% of GDP in 2019 against 52% in the data.
A missing country gets the euro-area values (flag "default").
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from functools import lru_cache
from typing import Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(_ROOT, "data", "cache", "private_loans.json")
# euro area (EA20) 2019, % of GDP (cache built 2026-11-08)
DEFAULT = {"nfc": 0.683, "hh": 0.569, "flag": "default",
           "source": "DEFAULT: euro area (Eurostat nasa_10_f_bs F4). Run "
                     "scripts/build_loans.py --write for country values."}
API = ("https://api.db.nomics.world/v22/series/Eurostat/nasa_10_f_bs?dimensions="
       + urllib.parse.quote(json.dumps({"unit": ["PC_GDP"], "co_nco": ["CO"],
                                        "sector": ["S11", "S14_S15"], "finpos": ["LIAB"],
                                        "na_item": ["F4"]}, separators=(",", ":")))
       + "&observations=1&limit=1000&format=json")


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
        geo = dm.get("geo", "").upper()
        if len(geo) == 2 or geo == "EA20":
            rec.setdefault(geo, {"series": {}})["series"][dm["sector"]] = ser
    return rec


@lru_cache(maxsize=4)
def _load(path: str, mtime: float) -> Dict[str, dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("countries", {})
    except Exception:
        return {}


def private_loans_for(geo: Optional[str], cache_path: str = CACHE,
                      base_year: int = 2019) -> Dict[str, object]:
    """{nfc, hh}: loans owed by firms and by households, fractions of GDP."""
    try:
        rec = _load(cache_path, os.path.getmtime(cache_path)).get((geo or "").upper())
    except OSError:
        rec = None
    s = (rec or {}).get("series", {})
    by = str(base_year)
    if by not in s.get("S11", {}) or by not in s.get("S14_S15", {}):
        return dict(DEFAULT)
    return {"nfc": s["S11"][by] / 100.0, "hh": s["S14_S15"][by] / 100.0, "flag": "live",
            "source": "Eurostat nasa_10_f_bs F4 liabilities, S11 and S14_S15 (DBnomics)"}


def fetch_all(base_year: int = 2019, timeout: float = 60.0) -> Dict[str, dict]:
    req = urllib.request.Request(API, headers={"User-Agent": "agora/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        docs = json.loads(resp.read().decode()).get("series", {}).get("docs", [])
    return from_dbnomics(docs, base_year)
