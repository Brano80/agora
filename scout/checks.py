"""Deterministic checks — the factual backbone of the scout.

Reproducible findings WITHOUT any LLM. The Qwen layer only prioritises and
narrates; it never invents facts.

  * freshness_findings  — live DBnomics vs snapshot: revisions, newer obs, fails.
  * coverage_findings   — snapshot-only series, missing-country snapshots,
                          inactive schema layers (roadmap).
  * catalog_findings    — sources in docs/DATA-SOURCES.md with no connector yet.
  * dataset_discovery_findings — (live, opt-in) DBnomics datasets matching our
                          themes that we don't use.
"""
from __future__ import annotations

import glob
import json
import os
import re
import urllib.request
from typing import List, Optional

from schema.accounts import SERIES, series_for_geo, SECTORS, INSTRUMENTS
from data.connectors.dbnomics import DBnomicsConnector
from scout.proposals import Finding

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE = os.path.join(_REPO, "data", "cache")
_DATASOURCES = os.path.join(_REPO, "docs", "DATA-SOURCES.md")
_API = "https://api.db.nomics.world/v22"

TARGET_GEOS = ["DE", "FR", "IT", "ES", "NL", "BE", "EA20"]
IMPLEMENTED_SOURCES = ("dbnomics", "bis", "wid", "epoch",
                       "income & wealth distribution")  # connectors we already have
DISCOVERY_KEYWORDS = ["wage", "labour", "labor", "capital", "wealth", "debt",
                      "productivity", "income", "compensation", "gini"]


def snapshot_geos() -> List[str]:
    return sorted({os.path.basename(p).split("_baseline_")[0].upper()
                   for p in glob.glob(os.path.join(_CACHE, "*_baseline_*.json"))})


# --------------------------------------------------------------------------- #
def freshness_findings(geo: str, year: int,
                       connector: Optional[DBnomicsConnector] = None,
                       rev_tol: float = 0.005) -> List[Finding]:
    """Compare live DBnomics to our snapshot. Returns [] when offline."""
    conn = connector or DBnomicsConnector(allow_live=True)
    if not conn.allow_live:
        return []
    out: List[Finding] = []
    for code, s in series_for_geo(geo).items():
        if not s.live:
            continue
        snap = conn.fetch_one(geo, year, code, allow_live=False)
        snap_v = snap["value"] if snap else None
        live = conn.fetch_one(geo, year, code, allow_live=True)
        if not live or live.get("source") != "live":
            out.append(Finding(
                "LIVE_FAIL", "medium", f"Live pull failed for '{code}'",
                f"The live DBnomics query for '{code}' ({s.hint()}) returned no "
                f"data; the model falls back to the snapshot. Dimensions may "
                f"need adjusting.",
                proposal=f"Confirm the dimension codes for '{code}' in "
                         f"schema.accounts.SERIES via scripts/verify_live.py.",
                geo=geo, series=code,
                evidence={"hint": s.hint(), "snapshot_value": snap_v}))
            continue
        live_v = live["value"]
        obs_year = live.get("obs_year")
        if snap_v not in (None, 0):
            diff = abs(live_v - snap_v) / abs(snap_v)
            if obs_year == year and diff > rev_tol:
                out.append(Finding(
                    "DATA_REVISION", "high",
                    f"'{code}' for {year} has been revised",
                    f"DBnomics now reports {live_v:,.1f} for {geo} {year}; the "
                    f"snapshot holds {snap_v:,.1f} ({diff*100:.2f}% diff).",
                    proposal=f"Update the {geo} {year} snapshot value for "
                             f"'{code}' to {live_v:,.1f}, then re-validate.",
                    geo=geo, series=code,
                    evidence={"live": live_v, "snapshot": snap_v,
                              "pct_diff": round(diff*100, 3), "obs_year": obs_year}))
        if obs_year is not None and obs_year > year:
            out.append(Finding(
                "NEWER_DATA", "low",
                f"Newer data available for '{code}' ({obs_year})",
                f"DBnomics has {geo} '{code}' through {obs_year}; baseline is "
                f"calibrated to {year}.",
                proposal=f"Consider adding a {obs_year} baseline for {geo}.",
                geo=geo, series=code,
                evidence={"latest_obs_year": obs_year, "baseline_year": year}))
    return out


# --------------------------------------------------------------------------- #
def coverage_findings(year: int = 2019) -> List[Finding]:
    out: List[Finding] = []
    for code, s in SERIES.items():
        if not s.live:
            out.append(Finding(
                "SNAPSHOT_ONLY", "medium", f"Series '{code}' is snapshot-only",
                f"'{code}' ({s.provider}/{s.dataset}) is not wired live; its "
                f"value comes from the snapshot.",
                proposal=f"Verify {s.provider} dimensions for '{code}' via "
                         f"scripts/verify_live.py, then set live=True.",
                series=code, evidence={"hint": s.hint()}))

    have = set(snapshot_geos())
    for g in TARGET_GEOS:
        if g not in have:
            out.append(Finding(
                "COVERAGE_GAP", "low", f"No calibrated snapshot for {g}",
                f"{g} has no bundled {year} snapshot, so it can't calibrate "
                f"offline. (Architecture already supports it via geo.)",
                proposal=f"Run `python scripts/build_snapshot.py --geo {g} "
                         f"--write` (live DBnomics pull, validated) to add the "
                         f"{g} {year} snapshot; review flagged defaults.",
                geo=g))

    inactive_sectors = [s.code for s in SECTORS.values() if not s.active]
    inactive_instr = [i.code for i in INSTRUMENTS.values() if not i.active]
    if inactive_sectors or inactive_instr:
        out.append(Finding(
            "ROADMAP", "info",
            "Declared-but-inactive schema layers awaiting modules",
            "Reserved in the canonical schema; activate as later modules plug in.",
            proposal="Prioritise the next module (distribution / AI-shock).",
            evidence={"inactive_sectors": inactive_sectors,
                      "inactive_instruments": inactive_instr}))
    return out


# --------------------------------------------------------------------------- #
def catalog_findings() -> List[Finding]:
    """Cross-reference docs/DATA-SOURCES.md against connectors we have."""
    if not os.path.exists(_DATASOURCES):
        return []
    skip = ("access notes", "how this changes", "convenience")
    sections: dict = {}
    cur = None
    with open(_DATASOURCES, encoding="utf-8") as fh:
        for line in fh:
            h = re.match(r"^##\s+(.*)", line)
            if h:
                cur = h.group(1).strip()
                continue
            if cur is None or any(k in cur.lower() for k in skip):
                continue
            m = re.match(r"^\s*-\s*\*\*(.+?)\*\*", line)
            if not m:
                continue
            name = m.group(1).strip()
            if name.endswith(":") or any(s in name.lower()
                                         for s in IMPLEMENTED_SOURCES):
                continue
            sections.setdefault(cur, [])
            if name not in sections[cur]:
                sections[cur].append(name)
    out: List[Finding] = []
    for title, names in sections.items():
        if not names:
            continue
        out.append(Finding(
            "TOOL", "low",
            f"Catalog sources without a connector: {title}",
            f"In docs/DATA-SOURCES.md but not yet connected: {'; '.join(names)}.",
            proposal="Build a connector for the highest-value source here; it "
                     "maps into the canonical schema like the DBnomics connector.",
            evidence={"section": title, "sources": names}))
    return out


# --------------------------------------------------------------------------- #
def dataset_discovery_findings(connector: DBnomicsConnector,
                               providers=("Eurostat",),
                               keywords: Optional[List[str]] = None,
                               cap: int = 8) -> List[Finding]:
    """(Opt-in, live) Scan provider dataset lists for themed datasets we don't
    use. Experimental: parsing is defensive and returns [] on any issue."""
    if not connector.allow_live:
        return []
    keywords = [k.lower() for k in (keywords or DISCOVERY_KEYWORDS)]
    have = {s.dataset.lower() for s in SERIES.values()}
    out: List[Finding] = []
    for prov in providers:
        try:
            url = f"{_API}/datasets/{prov}?limit=1000"
            req = urllib.request.Request(url, headers={"User-Agent": "agora/0.2"})
            with urllib.request.urlopen(req, timeout=connector.timeout) as r:
                data = json.loads(r.read().decode())
            docs = (data.get("datasets", {}) or {}).get("docs")
            if not isinstance(docs, list):
                continue
            hits = []
            for d in docs:
                code = str(d.get("code", "")).lower()
                name = str(d.get("name", ""))
                if code in have:
                    continue
                blob = (code + " " + name).lower()
                if any(k in blob for k in keywords):
                    hits.append({"code": d.get("code"), "name": name})
                if len(hits) >= cap:
                    break
            for h in hits:
                out.append(Finding(
                    "NEW_DATASET", "info",
                    f"{prov} dataset matches our themes: {h['code']}",
                    f"'{h['name']}' ({prov}/{h['code']}) matches AGORA themes "
                    f"and is not used yet.",
                    proposal=f"Evaluate adding series from {prov}/{h['code']} "
                             f"to schema.accounts.SERIES.",
                    evidence=h))
        except Exception:
            continue
    return out


# --------------------------------------------------------------------------- #
def run_all_checks(geos: List[str], year: int, allow_live: bool = True,
                   discover: bool = False) -> List[Finding]:
    conn = DBnomicsConnector(allow_live=allow_live)
    findings = coverage_findings(year) + catalog_findings()
    for g in geos:
        findings.extend(freshness_findings(g, year, connector=conn))
    if discover:
        findings.extend(dataset_discovery_findings(conn))
    return findings
