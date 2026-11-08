"""Which countries' results the project reports (Phase 7 step F).

Three members are formally excluded from published results. All three still run
and balance; their numbers are not meaningful under this model, for reasons in the
data rather than in the model's settings, so no parameter is tuned to rescue
them. Every published table, frontier and dashboard view filters on usable().
"""
from __future__ import annotations

from typing import Dict, List, Optional

EXCLUDED: Dict[str, str] = {
    "EL": ("Greek households consumed more than their disposable income in every year "
           "2012-2019 (gross saving rate -1.6% to -7.0%, Eurostat nasa_10_ki). The model's "
           "households cannot run down their wealth year after year, so matching 2019 "
           "consumption needs an owners' propensity to consume above 1 (1.27) and the debt "
           "path explodes. Fixing it would need persistent dissaving or under-recorded income, "
           "which the data cannot pin down."),
    "IE": ("Multinationals' accounting dominates Ireland's national accounts: investment was "
           "53% of GDP in 2019 and real GDP rose 25% in 2015 (intellectual-property "
           "onshoring and aircraft leasing; Eurostat nama_10_gdp). The CSO's modified "
           "measures (GNI*, modified investment) that strip these out are not in the "
           "harmonised Eurostat tables this model is calibrated on."),
    "LU": ("Luxembourg's cross-border income is dominated by pass-through companies: equity "
           "income paid and received exceeds 100% of GDP (Eurostat nasa_10_nf_tr), so the "
           "model replaces it with the other members' medians and its 2019 current account "
           "starts at +30% of GDP against an actual -0.5% (AMECO UBCA). Consumption and "
           "national income follow from that error (2011-19 backtest: real consumption off "
           "by 20% on average)."),
}


def usable(geo: Optional[str]) -> bool:
    return (geo or "").upper() not in EXCLUDED


def exclusion_reason(geo: Optional[str]) -> Optional[str]:
    return EXCLUDED.get((geo or "").upper())


def usable_geos(geos: List[str]) -> List[str]:
    return [g for g in geos if usable(g)]
