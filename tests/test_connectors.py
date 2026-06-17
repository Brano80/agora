"""Specialist connectors (Phase 3 increment 3): BIS household debt + WID top-10%
wealth via the multi-provider DBnomics path (snapshot-sourced), and the bespoke
global Epoch AI-compute connector. Offline."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from data.connectors.dbnomics import DBnomicsConnector
from data.connectors.epoch import EpochConnector


@pytest.mark.parametrize("geo", ["DE", "FR"])
def test_bis_wid_series_present(geo):
    conn = DBnomicsConnector(allow_live=False)
    rows = conn.fetch(geo, 2019)
    assert "hh_debt_gdp" in rows and rows["hh_debt_gdp"]["provider"] == "BIS"
    assert "top10_wealth_share" in rows and rows["top10_wealth_share"]["provider"] in ("WID", "OECD")
    # sourced, plausible ranges
    assert 30 < rows["hh_debt_gdp"]["value"] < 120
    assert 0.4 < rows["top10_wealth_share"]["value"] < 0.8
    assert rows["top10_wealth_share"]["source"] == "snapshot"


def test_epoch_connector_global_compute():
    e = EpochConnector()
    provides = e.provides()
    assert "frontier_training_compute_growth_x" in provides
    rows = e.fetch()                      # geo-agnostic
    g = rows["frontier_training_compute_growth_x"]
    assert g["provider"] == "Epoch AI"
    assert g["value"] > 1.0               # compute grows several-fold per year
    assert g["source_url"]                # provenance present


def test_catalog_backlog_shrank():
    """BIS / WID / Epoch are now connected, so the scout no longer lists them."""
    from scout.checks import catalog_findings
    blob = " ".join(str(f.evidence.get("sources", [])) for f in catalog_findings())
    assert "BIS Data Portal" not in blob
    assert "WID.world" not in blob
    assert "Epoch AI Database" not in blob
    # but still-unconnected sources remain flagged
    assert "EU KLEMS" in blob or "Penn World Table" in blob


# --- OECD IDD inequality connector (market vs disposable Gini) -------------- #
def test_oecd_idd_connector_provides_and_fetches():
    from data.connectors.oecd_idd import OECDIDDConnector
    c = OECDIDDConnector()
    provides = c.provides()
    assert "gini_market_oecd" in provides and "gini_disp_oecd" in provides
    rows = c.fetch("DE", 2019)
    g = rows["gini_market_oecd"]
    assert g["provider"] == "OECD"
    assert g["source"] == "snapshot"
    assert g["source_url"]                       # provenance present
    assert 0.0 < rows["gini_disp_oecd"]["value"] < 1.0


def test_oecd_idd_market_exceeds_disposable():
    """Taxes & transfers reduce inequality: market Gini > disposable Gini for
    every covered country (the robust, used invariant)."""
    from data.connectors.oecd_idd import OECDIDDConnector
    c = OECDIDDConnector()
    for geo in c.geos():
        rows = c.fetch(geo)
        assert rows["gini_market_oecd"]["value"] > rows["gini_disp_oecd"]["value"]
        assert c.validate(geo) == []             # all invariants hold


def test_oecd_idd_unknown_geo_is_empty():
    from data.connectors.oecd_idd import OECDIDDConnector
    assert OECDIDDConnector().fetch("ZZ") == {}


def test_oecd_idd_dropped_from_catalog_backlog():
    """OECD IDD is now connected -> the scout stops listing it; other OECD
    sources (Productivity / ICIO / .AI) must STAY flagged."""
    from scout.checks import catalog_findings
    blob = " ".join(str(f.evidence.get("sources", [])) for f in catalog_findings())
    assert "Income & Wealth Distribution" not in blob
    assert "OECD ICIO" in blob or "OECD Productivity" in blob


# --- OECD IDD LIVE market-Gini (GINIB) fetch path (offline-safe) ------------ #
def test_oecd_idd_live_query_config_present():
    """The live path's resolvable codes live in the snapshot _meta (so they can
    be fixed after --probe-idd without editing connector code)."""
    import json, os
    from data.connectors import oecd_idd as _m
    d = json.load(open(os.path.join(os.path.dirname(_m.__file__),
                                    "..", "cache", "oecd_idd.json"),
                       encoding="utf-8"))
    lq = d["_meta"]["live_query"]
    assert lq["candidates"] and all("dataset" in c for c in lq["candidates"])
    assert lq["geo_iso3"]["DE"] == "DEU" and lq["geo_iso3"]["FR"] == "FRA"


def test_oecd_idd_iso3_and_candidate_url():
    from data.connectors.oecd_idd import OECDIDDConnector
    c = OECDIDDConnector()
    assert c._iso3("DE") == "DEU" and c._iso3("PL") == "POL"
    cand = c._live_cfg()["candidates"][0]
    url = c._candidate_url(cand, "DE")
    assert url.startswith("https://api.db.nomics.world/v22/series/OECD/")
    assert "DEU" in url and "dimensions=" in url and "observations=1" in url


def test_oecd_idd_market_range_offline_is_single_vintage():
    """Offline, the market-Gini range yields at most the one snapshot vintage —
    not enough for a panel, which is the honest result until the live pull."""
    from data.connectors.oecd_idd import OECDIDDConnector
    rng = OECDIDDConnector().fetch_market_gini_range(
        "DE", list(range(2010, 2025)), allow_live=False)
    assert len(rng) <= 1
    for y, v in rng.items():
        assert 0.3 < v < 0.7                    # plausible market Gini


def test_oecd_idd_probe_is_graceful():
    """probe() must not crash and returns one structured entry per candidate,
    each carrying an ok flag (False when firewalled, True if DBnomics is
    reachable) — network-independent."""
    from data.connectors.oecd_idd import OECDIDDConnector
    cfg = OECDIDDConnector()._live_cfg()
    out = OECDIDDConnector(timeout=3).probe("DE")
    assert len(out) == len(cfg["candidates"])
    assert all("dataset" in e and "ok" in e for e in out)


def test_bis_and_wealth_wired_live():
    """BIS hh_debt_gdp (WS_TC, quarterly, UNIT_TYPE 770) and top10_wealth_share
    (OECD Wealth DB SH_TOP10, percent->0-1 via scale) are both wired live —
    probe-confirmed 2026-06-14."""
    from schema.accounts import SERIES
    b = SERIES["hh_debt_gdp"]
    assert b.live is True and b.geo_dim == "BORROWERS_CTY" and b.dataset == "WS_TC"
    assert b.dimensions["FREQ"] == "Q" and b.dimensions["UNIT_TYPE"] == "770"
    w = SERIES["top10_wealth_share"]
    assert w.live is True and w.provider == "OECD" and w.geo_dim == "REF_AREA"
    assert w.dimensions["MEASURE"] == "SH_TOP10" and abs(w.scale - 0.01) < 1e-12
    # OECD geo binds to ISO3
    assert w.for_geo("DE").dimensions["REF_AREA"] == "DEU"
