"""DuckDB local store. Lands calibration series + run results behind the schema.

Kept deliberately thin: it owns table creation (from schema.accounts.DDL) and
read/write helpers. DuckDB is optional at runtime — if it is not installed the
rest of AGORA still works in-memory; the store just becomes a no-op persister.
"""
from __future__ import annotations

import datetime as _dt
from typing import Dict, List, Optional

from schema.accounts import DDL

try:
    import duckdb  # type: ignore
    _HAS_DUCKDB = True
except Exception:  # pragma: no cover - environment dependent
    _HAS_DUCKDB = False


class Store:
    """Wrapper over a DuckDB connection. `path=None` -> in-memory."""

    def __init__(self, path: Optional[str] = None):
        if not _HAS_DUCKDB:
            self.con = None
            return
        self.con = duckdb.connect(path or ":memory:")
        for stmt in DDL:
            self.con.execute(stmt)

    @property
    def available(self) -> bool:
        return self.con is not None

    # --- series ---------------------------------------------------------- #
    def upsert_series(self, rows: List[dict]) -> None:
        if not self.available:
            return
        now = _dt.datetime.now(_dt.timezone.utc)
        for r in rows:
            self.con.execute(
                "INSERT OR REPLACE INTO series_data VALUES (?,?,?,?,?,?,?,?,?,?)",
                [
                    r["geo"], r["series_code"], r["year"], r["value"], r["unit"],
                    r["provider"], r["provider_code"], r["source_url"],
                    r.get("retrieved_at", now), r.get("source", "snapshot"),
                ],
            )

    def load_series(self, geo: str, year: Optional[int] = None) -> Dict[str, float]:
        if not self.available:
            return {}
        if year is None:
            rows = self.con.execute(
                "SELECT series_code, value FROM series_data WHERE geo = ?", [geo]
            ).fetchall()
        else:
            rows = self.con.execute(
                "SELECT series_code, value FROM series_data WHERE geo = ? AND year = ?",
                [geo, year],
            ).fetchall()
        return {code: val for code, val in rows}

    # --- results --------------------------------------------------------- #
    def save_result(self, run_id: str, result) -> None:
        if not self.available:
            return
        for p in result.periods:
            for item, val in p.reported.items():
                self.con.execute(
                    "INSERT INTO run_results VALUES (?,?,?,?,?,?)",
                    [run_id, result.scenario, result.geo, p.year, item, float(val)],
                )
            for flow, cols in p.tfm.items():
                for sector, val in cols.items():
                    self.con.execute(
                        "INSERT INTO tfm VALUES (?,?,?,?,?,?)",
                        [run_id, result.scenario, p.year, flow, sector, float(val)],
                    )
            for inst, cols in p.bsm.items():
                for sector, val in cols.items():
                    self.con.execute(
                        "INSERT INTO bsm VALUES (?,?,?,?,?,?)",
                        [run_id, result.scenario, p.year, inst, sector, float(val)],
                    )

    def save_consistency(self, run_id: str, scenario: str, reports: List) -> None:
        if not self.available:
            return
        for rep in reports:
            for chk in rep.checks:
                self.con.execute(
                    "INSERT INTO consistency_log VALUES (?,?,?,?,?,?)",
                    [run_id, scenario, rep.year, chk.name, chk.passed,
                     float(chk.max_residual)],
                )
