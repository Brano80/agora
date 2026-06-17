"""Epoch connector - global AI-compute metrics (geo-agnostic).

Unlike the macro connectors, Epoch's data is global frontier-technology trends
(training compute growth, doubling time), not per-country macro series. It
GROUNDS the AI-shock driver's assumptions (how fast the AI capex/capability
shock could plausibly be) rather than feeding the SFC calibration.

Snapshot-based now (the Epoch database is a downloadable CSV/DB, not reachable
from this sandbox); the live-download path is documented for a future pull. Same
Connector contract: declares what it provides, fetch() returns rows with
provenance and a `source` tag.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from data.connectors.base import Connector

_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "cache")


class EpochConnector(Connector):
    name = "epoch"

    def __init__(self, allow_live: bool = True):
        # live download (epoch.ai data export) would go here; snapshot fallback below
        self.allow_live = allow_live

    def provides(self) -> List[str]:
        snap = self._snapshot()
        return list(snap.get("series", {}).keys()) if snap else [
            "frontier_training_compute_growth_x", "compute_doubling_months"]

    def _snapshot(self) -> Optional[dict]:
        path = os.path.join(_CACHE, "epoch_compute.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    def fetch(self, geo: Optional[str] = None, year: Optional[int] = None) -> Dict[str, dict]:
        """Global metrics; geo/year are accepted for interface symmetry, ignored."""
        snap = self._snapshot()
        if not snap:
            return {}
        out = {}
        for code, e in snap.get("series", {}).items():
            out[code] = {
                "value": float(e["value"]), "unit": e.get("unit", ""),
                "provider": e.get("provider", "Epoch AI"),
                "provider_code": e.get("provider_code", code),
                "source_url": e.get("source_url", ""), "source": "snapshot",
                "note": e.get("note", ""),
            }
        return out
