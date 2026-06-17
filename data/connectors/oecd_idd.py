"""OECD IDD connector — per-country income-inequality anchors.

The OECD Income & Wealth Distribution Database (IDD) gives, for each country, the
Gini of MARKET income (before taxes and transfers) and of DISPOSABLE income
(after taxes and transfers), plus relative income poverty. The market measure is
the point: AGORA's distribution module reports a `gini_market`, but until now the
only observable inequality anchor was Eurostat's POST-tax Gini, which cannot pin
down the market capital-share elasticity beta (STATE.md F12). IDD supplies the
missing PRE-redistribution anchor from an independent source.

Same loose-coupling contract as the Epoch connector: snapshot-backed now (the
IDD bulk file isn't reachable from this sandbox; the live DBnomics path is
documented in the snapshot `_meta.live_path`), geo-aware, every row tagged with
provenance and a `source`. It declares auxiliary series for
validation/identification — it does NOT feed the core SFC calibration, so adding
it cannot disturb the consistency gate or the country snapshots.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

from data.connectors.base import Connector

_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "cache")
_SNAPSHOT = os.path.join(_CACHE, "oecd_idd.json")


class OECDIDDConnector(Connector):
    name = "oecd_idd"

    def __init__(self, allow_live: bool = True, timeout: float = 20.0):
        self.allow_live = allow_live
        self.timeout = timeout

    def _snapshot(self) -> Optional[dict]:
        if not os.path.exists(_SNAPSHOT):
            return None
        with open(_SNAPSHOT, encoding="utf-8") as fh:
            return json.load(fh)

    def geos(self) -> List[str]:
        snap = self._snapshot()
        return sorted(snap.get("data", {}).keys()) if snap else []

    def provides(self) -> List[str]:
        snap = self._snapshot()
        return list(snap.get("series_defs", {}).keys()) if snap else [
            "gini_market_oecd", "gini_disp_oecd", "poverty_rate_oecd"]

    def fetch(self, geo: str, year: Optional[int] = None) -> Dict[str, dict]:
        """Return the IDD inequality rows for `geo` (year accepted for interface
        symmetry; the snapshot carries the series' own `as_of` vintage)."""
        snap = self._snapshot()
        if not snap:
            return {}
        rows = snap.get("data", {}).get(geo.upper())
        if not rows:
            return {}
        defs = snap.get("series_defs", {})
        out: Dict[str, dict] = {}
        for code, meta in defs.items():
            if code not in rows:
                continue
            out[code] = {
                "value": float(rows[code]),
                "unit": meta.get("unit", ""),
                "provider": meta.get("provider", "OECD"),
                "provider_code": meta.get("provider_code", code),
                "source_url": meta.get("source_url", ""),
                "source": "snapshot",
                "as_of": rows.get("as_of"),
                "note": meta.get("note", ""),
            }
        return out

    # ------------------------------------------------------------------ #
    # LIVE market-Gini (GINIB) time series via DBnomics (provider OECD).
    # Codes are firewall-best-guess and live in the snapshot _meta.live_query so
    # they can be corrected (after `probe`) WITHOUT editing this file. Each
    # candidate dataset/dim set is tried in order; first that returns a series
    # wins. Offline (or all candidates failing) -> the single snapshot vintage.
    # ------------------------------------------------------------------ #
    def _live_cfg(self) -> dict:
        snap = self._snapshot() or {}
        return snap.get("_meta", {}).get("live_query", {})

    def _iso3(self, geo: str) -> str:
        return self._live_cfg().get("geo_iso3", {}).get(geo.upper(), geo.upper())

    @staticmethod
    def _num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def _url_for(self, dataset: str, dims: dict, geo: str) -> str:
        cfg = self._live_cfg()
        provider = cfg.get("provider", "OECD")
        geo3 = self._iso3(geo)
        qdims = {k: [str(v).replace("{geo3}", geo3).replace("{geo}", geo.upper())]
                 for k, v in dims.items()}
        q = urllib.parse.urlencode({
            "dimensions": json.dumps(qdims, separators=(",", ":")),
            "observations": "1",
        })
        return ("https://api.db.nomics.world/v22/series/"
                f"{provider}/{dataset}?{q}")

    def _candidate_url(self, cand: dict, geo: str) -> str:   # back-compat
        return self._url_for(cand["dataset"], cand.get("dims", {}), geo)

    def _best_doc_range(self, payload: dict, years: List[int]) -> Dict[int, float]:
        """From all returned docs, pick the one with the most in-range non-null
        observations (robust to multiple docs differing in unspecified dims or
        scale). A 0-100 Gini is normalised to 0-1."""
        best: Dict[int, float] = {}
        for doc in payload.get("series", {}).get("docs", []):
            periods = doc.get("period", []) or doc.get("original_period", [])
            got: Dict[int, float] = {}
            for per, val in zip(periods, doc.get("value", [])):
                fv = self._num(val)
                if fv is None:
                    continue
                try:
                    y = int(str(per)[:4])
                except ValueError:
                    continue
                if y in years:
                    got[y] = fv / 100.0 if fv > 1.5 else fv
            if len(got) > len(best):
                best = got
        return best

    def fetch_market_gini_range(self, geo: str, years: List[int],
                                allow_live: Optional[bool] = None
                                ) -> Dict[int, float]:
        """Return {year: market Gini (0-1)} for `geo` over `years`. For each
        live_query candidate it tries the full dimension filter, then (if that
        returns nothing) the candidate's `relax_dims` minimal filter, choosing
        the doc with the most observations. Falls back to the single snapshot
        vintage (so OFFLINE this yields at most one point - honest, not a guess).
        Values on a 0-100 scale are normalised to 0-1."""
        live = self.allow_live if allow_live is None else allow_live
        cfg = self._live_cfg()
        out: Dict[int, float] = {}
        if live and cfg.get("candidates"):
            for cand in cfg["candidates"]:
                for dims in (cand.get("dims"), cand.get("relax_dims")):
                    if not dims:
                        continue
                    try:
                        url = self._url_for(cand["dataset"], dims, geo)
                        req = urllib.request.Request(
                            url, headers={"User-Agent": "agora/0.2"})
                        with urllib.request.urlopen(req, timeout=self.timeout) as r:
                            payload = json.loads(r.read().decode())
                        got = self._best_doc_range(payload, years)
                        if got:
                            return got
                    except Exception:
                        continue
        # snapshot fallback: the connector's one sourced vintage
        rows = self.fetch(geo)
        gm = rows.get("gini_market_oecd")
        as_of = gm.get("as_of") if gm else None
        if gm and as_of in years:
            out[int(as_of)] = float(gm["value"])
        return out

    def probe(self, geo: str = "DE") -> List[dict]:
        """Best-effort: ask DBnomics for each candidate dataset's structure so a
        human can read the REAL dimension codes (esp. the before-tax MEASURE) and
        correct _meta.live_query. Returns a list of {dataset, ok, dimensions|error}.
        Offline every entry is an error - that is the expected firewalled result."""
        cfg = self._live_cfg()
        out: List[dict] = []
        for cand in cfg.get("candidates", []):
            ds = cand.get("dataset")
            entry = {"dataset": ds, "geo_dim": cand.get("geo_dim"),
                     "current_dims": cand.get("dims")}
            try:
                url = ("https://api.db.nomics.world/v22/series/"
                       f"{cfg.get('provider', 'OECD')}/{ds}?observations=0&limit=1")
                req = urllib.request.Request(
                    url, headers={"User-Agent": "agora/0.2"})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    payload = json.loads(r.read().decode())
                dims = (payload.get("series", {}).get("docs", [{}])[0]
                        .get("dimensions", {}))
                dd = payload.get("dataset", {}).get("dimensions_values_labels", {})
                entry["ok"] = True
                entry["dimension_axes"] = list(dd.keys()) or list(dims.keys())
                entry["dimensions_values_labels"] = dd
            except Exception as e:
                entry["ok"] = False
                entry["error"] = f"{type(e).__name__}: {e}"
            out.append(entry)
        return out

    def discover_datasets(self, queries: Optional[List[str]] = None,
                          limit: int = 25) -> List[dict]:
        """Ask the DBnomics SEARCH API which datasets match income-distribution
        keywords, so the REAL provider+dataset code can be found when the guessed
        candidates 404 (DBnomics restructured OECD to the SDMX 'Data Explorer',
        changing every code). Returns ranked {provider, dataset, name, nb_series}
        hits. Best-effort; offline returns []."""
        queries = queries or [
            "OECD income distribution database gini",
            "gini market income before taxes transfers",
            "income inequality gini disposable",
            "IDD income distribution",
        ]
        seen: Dict[str, dict] = {}
        for q in queries:
            try:
                url = ("https://api.db.nomics.world/v22/search?"
                       + urllib.parse.urlencode({"q": q, "limit": limit}))
                req = urllib.request.Request(
                    url, headers={"User-Agent": "agora/0.2"})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    payload = json.loads(r.read().decode())
                docs = (payload.get("results", {}).get("docs")
                        or payload.get("datasets", {}).get("docs")
                        or payload.get("docs", []))
                for d in docs:
                    prov = d.get("provider_code") or d.get("provider")
                    code = d.get("code") or d.get("dataset_code")
                    if not (prov and code):
                        continue
                    name = (d.get("name") or d.get("dataset_name") or "")
                    nb = (d.get("nb_series") or d.get("nb_matching_series")
                          or d.get("nb_total_series"))
                    key = f"{prov}/{code}"
                    blob = f"{prov} {code} {name}".lower()
                    score = sum(k in blob for k in
                                ("income", "inequality", "gini", "distribution",
                                 "idd", "wealth"))
                    if key not in seen or score > seen[key]["_score"]:
                        seen[key] = {"provider": prov, "dataset": code,
                                     "name": name, "nb_series": nb,
                                     "via_query": q, "_score": score}
            except Exception:
                continue
        ranked = sorted(seen.values(), key=lambda h: -h["_score"])
        for h in ranked:
            h.pop("_score", None)
        return ranked

    # ------------------------------------------------------------------ #
    def validate(self, geo: str) -> List[str]:
        """Validate-before-trust: return a list of problems (empty == OK).
        Enforces the economic invariants the data must obey regardless of the
        exact vintage, so a corrupt or mis-pulled snapshot is caught."""
        rows = self.fetch(geo)
        problems: List[str] = []
        if not rows:
            return [f"no IDD data for {geo}"]
        gm = rows.get("gini_market_oecd", {}).get("value")
        gd = rows.get("gini_disp_oecd", {}).get("value")
        pov = rows.get("poverty_rate_oecd", {}).get("value")
        for name, v in (("gini_market_oecd", gm), ("gini_disp_oecd", gd),
                        ("poverty_rate_oecd", pov)):
            if v is None:
                problems.append(f"{geo}: missing {name}")
            elif not (0.0 < v < 1.0):
                problems.append(f"{geo}: {name}={v} out of (0,1)")
        if gm is not None and gd is not None and not (gm > gd):
            problems.append(
                f"{geo}: market Gini {gm} must exceed disposable Gini {gd} "
                "(taxes & transfers reduce inequality)")
        if pov is not None and not (0.0 <= pov < 0.4):
            problems.append(f"{geo}: poverty_rate_oecd={pov} implausible")
        return problems
