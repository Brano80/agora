"""History panel (Phase 7 step F) - the realised 1995-2019 paths the backtest
starts from and is scored against.

Seven DBnomics calls, cut at 2019 (before COVID):
    Eurostat nama_10_gdp   B1GQ, P31_S14_S15, P3_S13, P51G, P5G, P6, P7 at
                           current prices (CP_MEUR) and chain-linked volumes
                           (CLV20_MEUR, else CLV15_MEUR)
    Eurostat gov_10a_main  P51G, S13: government investment (MIO_EUR); D9PAY and
                           D9REC: capital transfers paid and received (% of GDP;
                           bank rescues are booked here)
    Eurostat nasa_10_ki    SRG_S14_S15: gross household saving rate (%)
    Eurostat ilc_di12      GINI_HND: Gini of equivalised disposable income
    AMECO ALCD2            adjusted wage share (% of GDP at factor cost; the
                           labour share the snapshots use)
    AMECO UBCA             current-account balance (% of GDP)
Government debt, interest rates, capacity utilisation and external positions
come from their own caches (fiscal, rates, capacity, external), which already
hold the annual series back to the 1990s.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from functools import lru_cache
from typing import Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(_ROOT, "data", "cache", "history_panel.json")
LAST_YEAR = 2019
FIRST_YEAR = 1995
GEOS = ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU",
        "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK", "EA20"]
AMECO_ISO = {"AUT": "AT", "BEL": "BE", "BGR": "BG", "CYP": "CY", "CZE": "CZ", "DEU": "DE",
             "DNK": "DK", "EST": "EE", "GRC": "EL", "ESP": "ES", "FIN": "FI", "FRA": "FR",
             "HRV": "HR", "HUN": "HU", "IRL": "IE", "ITA": "IT", "LTU": "LT", "LUX": "LU",
             "LVA": "LV", "MLT": "MT", "NLD": "NL", "POL": "PL", "PRT": "PT", "ROM": "RO",
             "SWE": "SE", "SVN": "SI", "SVK": "SK", "EA20": "EA20"}
NAMA = {"B1GQ": "gdp", "P31_S14_S15": "hh_consumption", "P3_S13": "gov_consumption",
        "P51G": "gfcf", "P5G": "gcf", "P6": "exports", "P7": "imports"}
_DB = "https://api.db.nomics.world/v22/series/"


def _url(path: str, dims: Optional[dict] = None) -> str:
    q = ("?dimensions=" + urllib.parse.quote(json.dumps(dims, separators=(",", ":")))
         + "&") if dims else "?"
    return _DB + path + q + "observations=1&limit=1000&format=json"


API = {
    "nama": _url("Eurostat/nama_10_gdp", {"freq": ["A"], "unit": ["CP_MEUR", "CLV15_MEUR", "CLV20_MEUR"],
                                          "na_item": list(NAMA), "geo": GEOS}),
    "govinv": _url("Eurostat/gov_10a_main", {"freq": ["A"], "unit": ["MIO_EUR"], "sector": ["S13"],
                                             "na_item": ["P51G"], "geo": GEOS}),
    "captrans": _url("Eurostat/gov_10a_main", {"freq": ["A"], "unit": ["PC_GDP"], "sector": ["S13"],
                                               "na_item": ["D9PAY", "D9REC"], "geo": GEOS}),
    "saving": _url("Eurostat/nasa_10_ki", {"freq": ["A"], "na_item": ["SRG_S14_S15"], "geo": GEOS}),
    "gini": _url("Eurostat/ilc_di12", {"freq": ["A"], "geo": GEOS}),
    "ALCD2": _url("AMECO/ALCD2"),
    "UBCA": _url("AMECO/UBCA"),
}


def _annual(doc: dict) -> Dict[str, float]:
    out = {}
    for per, val in zip(doc.get("period", []), doc.get("value", [])):
        try:
            y, v = int(str(per)[:4]), float(val)
        except (TypeError, ValueError):
            continue
        if v == v and FIRST_YEAR <= y <= LAST_YEAR:
            out[str(y)] = v
    return out


def from_dbnomics(docs: Dict[str, List[dict]]) -> Dict[str, dict]:
    """{geo: {"series": {name: {year: value}}}} from the seven answers."""
    rec: Dict[str, dict] = {}

    def put(geo, name, ser):
        if geo and ser:
            rec.setdefault(geo, {"series": {}})["series"][name] = ser

    clv: Dict[tuple, Dict[str, Dict[str, float]]] = {}
    for d in docs.get("nama", []):
        dm = d.get("dimensions", {})
        geo, item, unit = dm.get("geo", "").upper(), dm.get("na_item"), dm.get("unit")
        if item not in NAMA:
            continue
        if unit == "CP_MEUR":
            put(geo, NAMA[item], _annual(d))
        else:
            clv.setdefault((geo, item), {})[unit] = _annual(d)
    for (geo, item), by_unit in clv.items():     # the newest reference year available
        ser = by_unit.get("CLV20_MEUR") or by_unit.get("CLV15_MEUR")
        put(geo, NAMA[item] + "_real", ser)
    for d in docs.get("govinv", []):
        put(d["dimensions"]["geo"].upper(), "gov_gfcf", _annual(d))
    for d in docs.get("captrans", []):
        dm = d["dimensions"]
        put(dm["geo"].upper(), "gov_" + dm["na_item"].lower() + "_gdp", _annual(d))
    for d in docs.get("saving", []):
        put(d["dimensions"]["geo"].upper(), "hh_saving_rate", _annual(d))
    for d in docs.get("gini", []):
        dm = d.get("dimensions", {})
        if dm.get("age", "TOTAL") == "TOTAL" and dm.get("statinfo") == "GINI_HND":
            put(dm["geo"].upper(), "gini_disp_income", _annual(d))
    for key, name, unit in (("ALCD2", "labour_share", "1.0.0.0"),
                            ("UBCA", "ca_gdp", "1.0.310.0")):
        for d in docs.get(key, []):
            parts = str(d.get("series_code", "")).split(".")
            if ".".join(parts[1:5]) == unit:
                put(AMECO_ISO.get(parts[0]), name, _annual(d))
    return rec


@lru_cache(maxsize=4)
def _load(path: str, mtime: float) -> Dict[str, dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("countries", {})
    except Exception:
        return {}


def history_for(geo: Optional[str], cache_path: str = CACHE) -> Dict[str, Dict[int, float]]:
    """{series: {year: value}} for one country; {} when the cache lacks it."""
    try:
        rec = _load(cache_path, os.path.getmtime(cache_path)).get((geo or "").upper())
    except OSError:
        return {}
    if not rec:
        return {}
    return {k: {int(y): v for y, v in s.items()} for k, s in rec.get("series", {}).items()}


def _get_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "agora/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def fetch_all(timeout: float = 120.0) -> Dict[str, dict]:
    return from_dbnomics({k: _get_json(u, timeout).get("series", {}).get("docs", [])
                          for k, u in API.items()})
