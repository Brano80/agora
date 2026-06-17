"""DBnomics connector - one connector, dozens of providers.

Queries the live DBnomics REST API (v22) BY DIMENSIONS, which is order-
independent and far more robust than guessing a dotted series code: DBnomics
returns the series matching the dimension filter regardless of code layout.
On any failure (offline, firewalled, missing series, unconfirmed dimensions) it
falls back per-series to a bundled, sourced snapshot, stamping each row with
`source = 'live' | 'snapshot'` so provenance is never ambiguous.

Mapping is driven entirely by schema.accounts.SERIES, so adding a series is a
schema edit, not a connector edit. Country-agnostic: pass any geo code.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

from schema.accounts import SERIES, series_for_geo, Series
from data.connectors.base import Connector

_API = "https://api.db.nomics.world/v22/series"
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")


class DBnomicsConnector(Connector):
    name = "dbnomics"

    def __init__(self, timeout: float = 20.0, allow_live: bool = True):
        self.timeout = timeout
        self.allow_live = allow_live

    def provides(self) -> List[str]:
        return list(SERIES.keys())

    # ------------------------------------------------------------------ #
    def fetch(self, geo: str, year: int) -> Dict[str, dict]:
        bound = series_for_geo(geo)
        snapshot = self._load_snapshot(geo, year)
        out: Dict[str, dict] = {}
        for code, s in bound.items():
            row = None
            if self.allow_live and s.live:
                row = self._fetch_live(s, year)
            if row is None:
                row = self._from_snapshot(snapshot, code, s)
            if row is not None:
                out[code] = row
        return out

    def fetch_one(self, geo: str, year: int, code: str,
                  allow_live: Optional[bool] = None,
                  force_live: bool = False) -> Optional[dict]:
        """Fetch a single canonical series (used by the live verifier and the
        snapshot builder). `force_live` attempts a live pull even for series
        flagged snapshot-only (live=False) - the builder uses it to TRY the
        AMECO/BIS/WID dimensions and report whether they resolve."""
        s = series_for_geo(geo)[code]
        live = self.allow_live if allow_live is None else allow_live
        if live and (s.live or force_live):
            row = self._fetch_live(s, year)
            if row is not None:
                return row
        return self._from_snapshot(self._load_snapshot(geo, year), code, s)

    def fetch_range(self, geo: str, code: str, years: List[int],
                    allow_live: Optional[bool] = None) -> Dict[int, float]:
        """All requested years of ONE canonical series in ONE live request
        (DBnomics returns the full series; fetch() would re-pull every series
        for every year - the panel loader uses this instead). Offline/failed:
        falls back to the bundled snapshot (its base year only)."""
        s = series_for_geo(geo)[code]
        live = self.allow_live if allow_live is None else allow_live
        out: Dict[int, float] = {}
        if live and s.live:
            try:
                url = self._build_url(s)
                req = urllib.request.Request(url, headers={"User-Agent": "agora/0.2"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    payload = json.loads(resp.read().decode())
                docs = payload.get("series", {}).get("docs", [])
                if docs:
                    doc = docs[0]
                    periods = doc.get("period", []) or doc.get("original_period", [])
                    for per, val in zip(periods, doc.get("value", [])):
                        fv = self._num(val)
                        if fv is None:
                            continue
                        try:
                            y = int(str(per)[:4])
                        except ValueError:
                            continue
                        if y in years:
                            out[y] = fv * getattr(s, "scale", 1.0)
                    if out:
                        return out
            except Exception:
                pass
        for y in years:                                   # snapshot fallback
            row = self._from_snapshot(self._load_snapshot(geo, y), code, s)
            if row is not None:
                out[y] = row["value"]
        return out

    # ------------------------------------------------------------------ #
    def _build_url(self, s: Series) -> str:
        dims = {k: [v] for k, v in s.dimensions.items()}
        q = urllib.parse.urlencode({
            "dimensions": json.dumps(dims, separators=(",", ":")),
            "observations": "1",
        })
        return f"{_API}/{s.provider}/{s.dataset}?{q}"

    def _fetch_live(self, s: Series, year: int) -> Optional[dict]:
        """Try the live API; return None on any problem (caller falls back)."""
        try:
            url = self._build_url(s)
            req = urllib.request.Request(url, headers={"User-Agent": "agora/0.2"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode())
            docs = payload.get("series", {}).get("docs", [])
            if not docs:
                return None
            doc = docs[0]
            periods = doc.get("period", []) or doc.get("original_period", [])
            values = doc.get("value", [])
            value = self._pick_value(periods, values, year)
            if value is None:
                return None
            value *= getattr(s, "scale", 1.0)
            return {
                "value": value, "unit": s.unit, "provider": s.provider,
                "provider_code": doc.get("series_code", s.hint()),
                "source_url": s.source_url, "source": "live",
                "obs_year": self._matched_year(periods, values, year),
            }
        except Exception:
            return None

    @staticmethod
    def _num(v):
        """Missing observations arrive as None OR the string 'NA'."""
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _pick_value(periods, values, year):
        for p, v in zip(periods, values):
            if str(p).startswith(str(year)):
                fv = DBnomicsConnector._num(v)
                if fv is not None:
                    return fv
        for v in reversed(values):           # fall back to most recent non-null
            fv = DBnomicsConnector._num(v)
            if fv is not None:
                return fv
        return None

    @staticmethod
    def _matched_year(periods, values, year):
        for p, v in zip(periods, values):
            if (str(p).startswith(str(year))
                    and DBnomicsConnector._num(v) is not None):
                return int(str(p)[:4])
        for p, v in zip(reversed(periods), reversed(values)):
            if DBnomicsConnector._num(v) is not None:
                return int(str(p)[:4])
        return None

    # ------------------------------------------------------------------ #
    def _load_snapshot(self, geo: str, year: int) -> Optional[dict]:
        path = os.path.join(_CACHE_DIR, f"{geo.lower()}_baseline_{year}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _from_snapshot(self, snapshot, code, s: Series) -> Optional[dict]:
        if not snapshot:
            return None
        entry = snapshot.get("series", {}).get(code)
        if entry is None:
            return None
        return {
            "value": float(entry["value"]),
            "unit": entry.get("unit", s.unit),
            "provider": entry.get("provider", s.provider),
            "provider_code": entry.get("provider_code", s.hint()),
            "source_url": entry.get("source_url", s.source_url),
            "source": "snapshot",
        }


def load_calibration(geo: str = "DE", year: int = 2019, allow_live: bool = True,
                     store=None) -> Tuple[Dict[str, float], Dict[str, str]]:
    """Fetch calibration series -> ({code: value}, {code: source}). Lands rows
    in the store with provenance if one is provided."""
    conn = DBnomicsConnector(allow_live=allow_live)
    rows = conn.fetch(geo, year)
    if store is not None and getattr(store, "available", False):
        store.upsert_series([
            {"geo": geo, "series_code": c, "year": year, "value": r["value"],
             "unit": r["unit"], "provider": r["provider"],
             "provider_code": r["provider_code"], "source_url": r["source_url"],
             "source": r["source"]}
            for c, r in rows.items()
        ])
    return ({c: r["value"] for c, r in rows.items()},
            {c: r["source"] for c, r in rows.items()})
