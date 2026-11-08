"""Interest rates and the financial sector (Phase 7 Banks step, 2026-11-01).

Read from the DBnomics mirror in five calls (scripts/build_rates.py):
    AMECO ISN               nominal short-term interest rate (%), all EU members
    AMECO ILN               nominal long-term government bond yield (%)
    ECB MIR  A20/2240/O     bank rate on outstanding loans to non-financial firms
    ECB MIR  L21/2250/N     bank rate on households' overnight deposits
    Eurostat nasa_10_f_bs   households' deposits (F2), debt securities (F3),
                            insurance and pension claims (F6), % of GDP
The cache keeps the annual series; the calibration is derived at load time:
    policy0        short-term rate in the base year (the starting policy rate)
    gov_spread     new government borrowing rate minus the policy rate:
                   euro area (and DK, BG, HR): the euro-area term premium
                   (mean ILN - ISN over WINDOW) + the country's 2019 long-term
                   spread over the euro area; floaters (CZ, HU, PL, RO, SE):
                   their own mean ILN - ISN over WINDOW
    loan_spread    mean MIR firm-loan rate - mean ISN over WINDOW
    deposit_rate0  MIR households' overnight deposit rate, base year
    deposit_share  F2 / (F2 + F3 + F6), base year
Missing pieces fall back to the euro-area value (flagged).

Behaviour constants (sourced in docs/PHASE7.md, Banks step):
    NEUTRAL_RATE      2.0% nominal (ECB Economic Bulletin 1/2025: nominal r* 1.75-2.25%)
    TAYLOR_INFLATION  1.5, TAYLOR_GAP 0.5 (Taylor 1993)
    RATE_SMOOTHING    0.6 a year (estimated ECB smoothing ~0.85-0.9 a quarter)
    RATE_FLOOR        -0.5% (the ECB deposit-rate low, 2019-2022, and the
                      Riksbank's); 0 for CZ, HU, PL, RO, whose central banks never
                      set negative rates
    DEPOSIT_BETA      0.25 (ECB WP 3255: long-run household sight-deposit beta 0.247)
    RISK_PREMIUM      0.03 per unit of debt/GDP = 3 bp per pp (Pamies, Carnot &
                      Patarau 2021, EC Discussion Paper 141)
    DEBT_MATURITY     7 years (average residual maturity of euro-area government
                      debt, 6.6-8 years; ECB Occasional Paper 132)
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
CACHE = os.path.join(_ROOT, "data", "cache", "rates.json")
WINDOW = (2015, 2019)

NEUTRAL_RATE = 0.02
TAYLOR_INFLATION = 1.5
TAYLOR_GAP = 0.5
RATE_SMOOTHING = 0.6
RATE_FLOOR = -0.005
FLOOR_BY_GEO = {"CZ": 0.0, "HU": 0.0, "PL": 0.0, "RO": 0.0}
DEPOSIT_BETA = 0.25
RISK_PREMIUM = 0.03
DEBT_MATURITY = 7.0

EURO_AREA = "EA20"
# euro members in 2026 plus Denmark (ERM II peg): they face the ECB rate
ECB_FOLLOWERS = {"AT", "BE", "BG", "CY", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR",
                 "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PT", "SI", "SK"}
FLOATERS = {"CZ", "HU", "PL", "RO", "SE"}       # own central bank, own rule
# conduit economies whose foreign debt-type position exceeds what households
# hold: the public stand-in keeps it (deposits would start at or below zero)
STAND_IN = {"IE", "CY"}

AMECO_ISO = {"AUT": "AT", "BEL": "BE", "BGR": "BG", "CYP": "CY", "CZE": "CZ", "DEU": "DE",
             "DNK": "DK", "EST": "EE", "GRC": "EL", "ESP": "ES", "FIN": "FI", "FRA": "FR",
             "HRV": "HR", "HUN": "HU", "IRL": "IE", "ITA": "IT", "LTU": "LT", "LUX": "LU",
             "LVA": "LV", "MLT": "MT", "NLD": "NL", "POL": "PL", "PRT": "PT", "ROM": "RO",
             "SWE": "SE", "SVN": "SI", "SVK": "SK", "EA20": "EA20"}
MIR_GEO = {"GR": "EL", "U2": "EA20"}
NATIONAL_CURRENCY = {"BG": "BGN", "CZ": "CZK", "DK": "DKK", "HR": "HRK", "HU": "HUF",
                     "PL": "PLN", "RO": "RON", "SE": "SEK"}

_DB = "https://api.db.nomics.world/v22/series/"


def _url(path: str, dims: Optional[dict] = None) -> str:
    q = ("?dimensions=" + urllib.parse.quote(json.dumps(dims, separators=(",", ":")))
         + "&") if dims else "?"
    return _DB + path + q + "observations=1&limit=1000&format=json"


API = {
    "isn": _url("AMECO/ISN"),
    "iln": _url("AMECO/ILN"),
    "mir_loans": _url("ECB/MIR", {"FREQ": ["M"], "BS_REP_SECTOR": ["B"], "BS_ITEM": ["A20"],
                                  "MATURITY_NOT_IRATE": ["A"], "DATA_TYPE_MIR": ["R"],
                                  "AMOUNT_CAT": ["A"], "BS_COUNT_SECTOR": ["2240"],
                                  "IR_BUS_COV": ["O"]}),
    "mir_deposits": _url("ECB/MIR", {"FREQ": ["M"], "BS_ITEM": ["L21"],
                                     "MATURITY_NOT_IRATE": ["A"], "BS_COUNT_SECTOR": ["2250"],
                                     "IR_BUS_COV": ["N"], "DATA_TYPE_MIR": ["R"]}),
    "hh_assets": _url("Eurostat/nasa_10_f_bs", {"unit": ["PC_GDP"], "co_nco": ["CO"],
                                                "sector": ["S14_S15"], "finpos": ["ASS"],
                                                "na_item": ["F2", "F3", "F6"]}),
}


def _annual(doc: dict, base_year: int, min_months: int = 6) -> Dict[str, float]:
    """Annual values up to base_year; monthly series are averaged per year."""
    by: Dict[str, List[float]] = {}
    for per, val in zip(doc.get("period", []), doc.get("value", [])):
        try:
            y, v = int(str(per)[:4]), float(val)
        except (TypeError, ValueError):
            continue
        if v == v and y <= base_year:
            by.setdefault(str(y), []).append(v)
    monthly = any(len(v) > 1 for v in by.values())
    return {y: sum(v) / len(v) for y, v in by.items()
            if not monthly or len(v) >= min_months}


def from_dbnomics(docs: Dict[str, List[dict]], base_year: int = 2019) -> Dict[str, dict]:
    """{geo: {"series": {name: {year: value}}}} from the five DBnomics answers."""
    rec: Dict[str, dict] = {}

    def put(geo, name, ser):
        if ser:
            rec.setdefault(geo, {"series": {}})["series"][name] = ser

    for key, name in (("isn", "ISN"), ("iln", "ILN")):
        for d in docs.get(key, []):
            geo = AMECO_ISO.get(str(d.get("series_code", "")).split(".")[0])
            if geo and name not in rec.get(geo, {}).get("series", {}):
                put(geo, name, _annual(d, base_year))
    for key, name in (("mir_loans", "MIR_LOANS"), ("mir_deposits", "MIR_DEPOSITS")):
        for d in docs.get(key, []):
            parts = str(d.get("series_code", "")).split(".")
            if len(parts) < 10:
                continue
            geo = MIR_GEO.get(parts[1], parts[1])
            cur = parts[8]
            if cur not in ("EUR", NATIONAL_CURRENCY.get(geo, "EUR")):
                continue
            ser = _annual(d, base_year)
            # national currency wins where both exist (the base-year currency)
            if cur == NATIONAL_CURRENCY.get(geo) or name not in rec.get(geo, {}).get("series", {}):
                put(geo, name, ser)
    for d in docs.get("hh_assets", []):
        dm = d.get("dimensions", {})
        geo = dm.get("geo", "").upper()
        geo = "EA20" if geo == "EA20" else geo
        put(geo, "HH_" + dm.get("na_item", ""), _annual(d, base_year))
    return rec


def _mean(ser: Dict[str, float], window=WINDOW) -> Optional[float]:
    xs = [ser[str(y)] for y in range(window[0], window[1] + 1) if str(y) in ser]
    return statistics.mean(xs) if len(xs) >= 3 else None


def summarise(rec: Dict[str, dict], geo: str, base_year: int = 2019) -> Optional[Dict[str, object]]:
    """The rate calibration of one country (fractions), or None if the cache
    lacks its short-term rate."""
    g = geo.upper()
    s = rec.get(g, {}).get("series", {})
    ea = rec.get(EURO_AREA, {}).get("series", {})
    by = str(base_year)
    win = (base_year - (WINDOW[1] - WINDOW[0]), base_year)   # the five years to the base year
    isn, iln = s.get("ISN", {}), s.get("ILN", {})
    ea_isn, ea_iln = ea.get("ISN", {}), ea.get("ILN", {})
    if by not in isn or by not in ea_isn or _mean(ea_iln, win) is None:
        return None
    flags = []
    ea_term = _mean(ea_iln, win) - _mean(ea_isn, win)
    regime = "ecb" if g in ECB_FOLLOWERS else ("own" if g in FLOATERS else "own")
    if g == EURO_AREA:
        gov_spread = ea_term
    elif regime == "ecb":
        if by in iln and by in ea_iln:
            gov_spread = ea_term + (iln[by] - ea_iln[by])
        else:
            gov_spread = ea_term
            flags.append("gov_spread=euro area")
    else:
        own = _mean({y: iln[y] - isn[y] for y in iln if y in isn}, win)
        if own is None:
            gov_spread = ea_term
            flags.append("gov_spread=euro area")
        else:
            gov_spread = own
    ea_loans = ea.get("MIR_LOANS", {})
    loans = s.get("MIR_LOANS", {})
    yrs = [str(y) for y in range(win[0], win[1] + 1)]
    ls = [loans[y] - isn[y] for y in yrs if y in loans and y in isn]
    if len(ls) >= 3:
        loan_spread = statistics.mean(ls)
    else:
        loan_spread = statistics.mean(ea_loans[y] - ea_isn[y] for y in yrs
                                      if y in ea_loans and y in ea_isn)
        flags.append("loan_spread=euro area")
    dep = s.get("MIR_DEPOSITS", {})
    if by in dep:
        deposit_rate0 = dep[by]
    else:
        deposit_rate0 = ea.get("MIR_DEPOSITS", {}).get(by, 0.03)
        flags.append("deposit_rate=euro area")
    f2, f3, f6 = (s.get("HH_" + k, {}).get(by) for k in ("F2", "F3", "F6"))
    if None not in (f2, f3, f6) and (f2 + f3 + f6) > 0:
        deposit_share = f2 / (f2 + f3 + f6)
    else:
        e2, e3, e6 = (ea.get("HH_" + k, {}).get(by) for k in ("F2", "F3", "F6"))
        deposit_share = e2 / (e2 + e3 + e6) if None not in (e2, e3, e6) else 0.48
        flags.append("deposit_share=euro area")
    return {"regime": regime, "policy0": isn[by] / 100.0,
            "rate_floor": FLOOR_BY_GEO.get(g, RATE_FLOOR),
            "gov_spread": gov_spread / 100.0, "loan_spread": loan_spread / 100.0,
            "deposit_rate0": deposit_rate0 / 100.0, "deposit_share": deposit_share,
            "ea_term": ea_term / 100.0, "ea_policy0": ea_isn[by] / 100.0,
            "stand_in": g in STAND_IN, "flag": ",".join(flags) or "data"}


# Euro-area values (cache built 2026-11-01), used when the cache is missing
DEFAULT = {"regime": "ecb", "policy0": -0.0036, "rate_floor": RATE_FLOOR, "gov_spread": 0.0115, "loan_spread": 0.0255,
           "deposit_rate0": 0.0003, "deposit_share": 0.48, "ea_term": 0.0115,
           "ea_policy0": -0.0036, "stand_in": False,
           "flag": "default: euro area (run scripts/build_rates.py --write)"}


@lru_cache(maxsize=8)
def _load(path: str, mtime: float) -> Dict[str, dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("countries", {})
    except Exception:
        return {}


def rates_for(geo: Optional[str], cache_path: str = CACHE, base_year: int = 2019) -> Dict[str, object]:
    """The rate calibration for a country (fractions), with flag and source."""
    try:
        rec = _load(cache_path, os.path.getmtime(cache_path))
    except OSError:
        rec = {}
    g = (geo or "").upper()
    s = summarise(rec, g, base_year) if g else None
    if s is None:
        out = dict(DEFAULT)
        out["regime"] = "own" if g in FLOATERS else "ecb"
        out["stand_in"] = g in STAND_IN
        return out
    s["source"] = ("AMECO ISN/ILN, ECB MIR (firm loans, household overnight deposits), "
                   "Eurostat nasa_10_f_bs (DBnomics)")
    return s


def _get_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "AGORA/rates"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_all(base_year: int = 2019, timeout: float = 90.0) -> Dict[str, dict]:
    """Five DBnomics calls -> the cache records (see from_dbnomics)."""
    docs = {k: _get_json(u, timeout).get("series", {}).get("docs", []) for k, u in API.items()}
    return from_dbnomics(docs, base_year)
