"""Country trend growth (Phase 7 step F) - the economy's long-run path.

The 30-year projections follow the European Commission's and the Economic
Policy Committee's 2024 Ageing Report, the EU's official long-run projection
(European Commission, "2024 Ageing Report. Underlying assumptions and
projection methodologies", Institutional Paper 257, November 2023, Table
I.3.1: potential GDP growth, period averages). Exports (the rest of the
world's demand for the country's output) grow at it, and the engine sets
capacity so the no-shock economy grows at it (modules/sfc_core.py).
Model years map to the report's periods (2020-2030 -> 2022-30 and so on;
beyond 2070 the last period holds). The report starts in 2022; 2020-21 use
the 2022-30 average.

A base year before 2019 (the historical backtest) cannot use a projection
published in 2023: it gets its own pre-sample averages instead, real GDP and
growth over the ten years to the base year (Eurostat nama_10_gdp), constant
over the horizon.

MC: the report's lower and higher TFP scenarios (Tables I.3.7, I.3.8, growth
2022-2070) bound a uniform shift of the growth path; draw in [-1, 1].
"""
from __future__ import annotations

from typing import Dict, List, Optional

PERIODS = ((2020, 2030), (2031, 2040), (2041, 2050), (2051, 2060), (2061, 2070))
# Table I.3.1: potential GDP growth (%), 2022-30, 2031-40, 2041-50, 2051-60, 2061-70
POTENTIAL_GROWTH = {
    "BE": (1.4, 1.3, 1.5, 1.3, 1.2), "BG": (2.0, 1.5, 1.3, 1.2, 1.2), "CZ": (1.4, 1.4, 1.6, 1.5, 1.5),
    "DK": (1.2, 1.3, 1.7, 1.4, 1.1), "DE": (0.8, 1.1, 1.4, 1.1, 1.2), "EE": (1.5, 1.8, 1.8, 1.4, 1.5),
    "IE": (5.2, 1.9, 1.3, 1.3, 1.1), "EL": (1.0, 0.7, 1.2, 1.2, 1.2), "ES": (1.2, 1.1, 1.4, 1.3, 1.1),
    "FR": (0.8, 0.9, 1.4, 1.3, 1.1), "HR": (2.3, 1.5, 1.5, 1.2, 0.9), "IT": (0.8, 0.8, 1.4, 1.4, 1.2),
    "CY": (2.3, 1.7, 1.7, 1.2, 1.2), "LV": (1.6, 1.4, 0.8, 0.5, 1.1), "LT": (2.3, 1.4, 0.9, 0.3, 0.6),
    "LU": (2.2, 1.8, 2.0, 1.5, 1.3), "HU": (2.4, 1.8, 1.7, 1.5, 1.3), "MT": (4.2, 3.1, 1.8, 0.9, 0.8),
    "NL": (1.3, 1.1, 1.7, 1.4, 1.1), "AT": (1.4, 1.4, 1.4, 1.1, 1.1), "PL": (2.6, 2.0, 1.0, 0.9, 1.0),
    "PT": (1.4, 0.7, 1.3, 1.5, 1.2), "RO": (2.6, 1.9, 1.3, 1.4, 1.2), "SI": (2.6, 1.9, 1.1, 1.2, 1.2),
    "SK": (1.7, 1.6, 1.4, 1.2, 1.3), "FI": (1.1, 1.3, 1.3, 1.0, 0.9), "SE": (1.6, 1.8, 1.8, 1.6, 1.4),
    "EA20": (1.2, 1.1, 1.4, 1.2, 1.1), "EU27": (1.3, 1.2, 1.4, 1.3, 1.1),
}
# Tables I.3.7 / I.3.8: potential growth 2022-2070 in the higher / lower TFP
# scenario minus the baseline (pp); the MC shifts the whole path within them
SCENARIO_SHIFT = {
    "BE": (0.1, -0.2), "BG": (0.1, -0.2), "CZ": (0.1, -0.2), "DK": (0.2, -0.2), "DE": (0.2, -0.2),
    "EE": (0.1, -0.2), "IE": (0.1, -0.2), "EL": (0.0, -0.3), "ES": (0.1, -0.2), "FR": (0.1, -0.2),
    "HR": (0.0, -0.2), "IT": (0.1, -0.2), "CY": (0.1, -0.2), "LV": (0.1, -0.2), "LT": (0.1, -0.2),
    "LU": (0.1, -0.3), "HU": (0.1, -0.2), "MT": (0.1, -0.2), "NL": (0.1, -0.2), "AT": (0.1, -0.2),
    "PL": (0.1, -0.2), "PT": (0.1, -0.2), "RO": (0.0, -0.2), "SI": (0.1, -0.2), "SK": (0.1, -0.2),
    "FI": (0.1, -0.2), "SE": (0.2, -0.2), "EA20": (0.1, -0.2), "EU27": (0.1, -0.2),
}
SOURCE = ("European Commission (2023), 2024 Ageing Report. Underlying assumptions and "
          "projection methodologies, Institutional Paper 257, Tables I.3.1, I.3.7, I.3.8")
PRE_SAMPLE_YEARS = 10


def _period(year: int) -> int:
    for i, (a, b) in enumerate(PERIODS):
        if year <= b:
            return i
    return len(PERIODS) - 1


def ageing_report_path(geo: str, base_year: int, H: int, draw: float = 0.0) -> Optional[Dict[str, object]]:
    g = (geo or "").upper()
    if g not in POTENTIAL_GROWTH:
        g = "EU27"
    hi, lo = SCENARIO_SHIFT[g]
    shift = (hi if draw > 0 else -lo) * draw / 100.0          # draw in [-1, 1]
    growth = [POTENTIAL_GROWTH[g][_period(base_year + t)] / 100.0 + shift for t in range(H)]
    return {"growth": growth, "flag": "ageing_report", "source": SOURCE, "geo_row": g}


def pre_sample_path(geo: str, base_year: int, H: int) -> Optional[Dict[str, object]]:
    """Real GDP growth over the ten years to the base year."""
    from data.connectors.history import history_for
    h = history_for(geo).get("gdp_real", {})
    a = base_year - PRE_SAMPLE_YEARS
    if a not in h or base_year not in h:
        return None
    gy = (h[base_year] / h[a]) ** (1.0 / PRE_SAMPLE_YEARS) - 1.0
    return {"growth": [gy] * H, "flag": "pre_sample",
            "source": f"Eurostat nama_10_gdp, real GDP growth {a}-{base_year}"}


def trend_path(geo: Optional[str], base_year: int = 2019, H: int = 30,
               draw: float = 0.0) -> Dict[str, object]:
    """{growth: [g_Y(t)], flag, source}; t = 0 is the base year (its entry is
    unused: growth starts in year 1)."""
    if base_year >= 2019:
        return ageing_report_path(geo or "", base_year, H, draw)
    out = pre_sample_path(geo or "", base_year, H)
    return out if out is not None else ageing_report_path(geo or "", base_year, H, draw)


def mean_growth(path: Dict[str, object]) -> float:
    gs = path["growth"][1:] or path["growth"]
    return sum(gs) / len(gs)
