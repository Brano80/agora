"""Connector contract — the data-side mirror of the module interface.

A connector declares which canonical schema series it can provide and fetches
them for a given geo/year, returning rows ready for the store. Same loose-
coupling discipline as modules: connectors speak only schema names.
"""
from __future__ import annotations

from typing import Dict, List


class Connector:
    name: str = "connector"

    def provides(self) -> List[str]:
        """Canonical schema series codes this connector can supply."""
        raise NotImplementedError

    def fetch(self, geo: str, year: int) -> Dict[str, dict]:
        """Return {series_code: {value, unit, provider, provider_code,
        source_url, source}} mapped into schema names."""
        raise NotImplementedError
