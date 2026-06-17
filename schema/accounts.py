"""Canonical accounts schema - the shared SNA vocabulary (ESA/SNA based).

This is AGORA's linchpin. It declares:
  * SECTORS      - institutional sectors (households split into workers /
                   capital-owners, firms, banks, central bank, government,
                   sovereign fund, rest-of-world).
  * INSTRUMENTS  - financial instruments (assets are someone's liability) plus
                   the one real (non-financial) stock we track: fixed capital.
  * FLOWS        - transaction types (rows of the transaction-flow matrix).
  * SERIES       - canonical macro series that modules consume and that data
                   connectors map their provider series into, addressed by
                   DBnomics provider/dataset + a DIMENSION dict (order-
                   independent, robust for live pulls), with provenance.

Phase 1 activates a subset (workers, owners, firms, government; money; the
demand-side flows). Everything else is declared but inactive so later phases
snap in without touching the schema.

The schema is country-agnostic. `series_for_geo(geo)` binds the geo dimension
so Germany -> France -> EA20 is a config swap, not a rewrite.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Highest phase whose sectors/instruments/flows are ACTIVE. Declared-but-
# inactive entries (banks, bills, ...) snap in by raising this, not by edits.
ACTIVE_PHASE = 1


# --------------------------------------------------------------------------- #
# Sectors
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Sector:
    code: str
    label: str
    active_phase: int
    note: str = ""

    @property
    def active(self) -> bool:
        return self.active_phase <= ACTIVE_PHASE


SECTORS: Dict[str, Sector] = {
    s.code: s
    for s in [
        Sector("hh_workers", "Households - workers", 1,
                "Earn wages (+ any UBI), high propensity to consume."),
        Sector("hh_owners", "Households - capital owners", 1,
                "Receive distributed firm profits, lower propensity to consume."),
        Sector("firms", "Non-financial firms", 1,
                "Produce output; pass-through in Phase 1 (zero net financial worth)."),
        Sector("government", "General government", 1,
                "Taxes, spends, issues government money to cover deficits."),
        Sector("banks", "Banks", 2,
                "Loans = deposits. Inactive until investment is bank-financed."),
        Sector("central_bank", "Central bank", 2,
                "Reserves, base money. Inactive in Phase 1."),
        Sector("sovereign_fund", "Sovereign wealth fund", 1,
                "Holds a citizens' capital stake; pays a per-capita dividend (UBC)."),
        Sector("rest_of_world", "Rest of world", 1,
                "External sector (open economy, Phase 3): one per-country counterparty."),
    ]
}


# --------------------------------------------------------------------------- #
# Instruments (financial; sign convention: asset +, liability -)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Instrument:
    code: str
    label: str
    active_phase: int
    real: bool = False
    note: str = ""

    @property
    def active(self) -> bool:
        return self.active_phase <= ACTIVE_PHASE


INSTRUMENTS: Dict[str, Instrument] = {
    i.code: i
    for i in [
        Instrument("money", "Government money / deposits", 1,
                   note="The single financial asset in Phase 1; gov liability."),
        Instrument("capital", "Fixed capital stock", 1, real=True,
                   note="Real (non-financial) stock; accumulates investment."),
        Instrument("bills", "Government bills", 2, note="Inactive in Phase 1."),
        Instrument("loans", "Bank loans", 2, note="Inactive in Phase 1."),
        Instrument("deposits", "Bank deposits", 2, note="Inactive in Phase 1."),
        Instrument("equity", "Firm equity", 2, note="Inactive in Phase 1."),
        Instrument("reserves", "Central-bank reserves", 2, note="Inactive."),
        Instrument("fx_assets", "Net foreign assets", 1, note="Domestic net foreign assets vs RoW (open economy)."),
    ]
}


# --------------------------------------------------------------------------- #
# Flows (transaction-flow-matrix rows). Each must sum to zero across sectors.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Flow:
    code: str
    label: str
    active_phase: int
    note: str = ""

    @property
    def active(self) -> bool:
        return self.active_phase <= ACTIVE_PHASE


FLOWS: Dict[str, Flow] = {
    f.code: f
    for f in [
        Flow("consumption", "Household consumption", 1, ""),
        Flow("investment", "Fixed investment (AI capex)", 1, ""),
        Flow("gov_expenditure", "Government expenditure", 1, ""),
        Flow("wages", "Wage bill", 1, ""),
        Flow("profits", "Distributed profits", 1, ""),
        Flow("tax_income", "Income tax", 1, ""),
        Flow("tax_capital", "Capital / profit tax", 1, ""),
        Flow("transfer_ubi", "UBI transfer", 1, ""),
        Flow("money_chg", "Change in money holdings", 1, "Balancing financial flow."),
        Flow("exports", "Exports to rest of world", 1, "Foreign demand for domestic output."),
        Flow("imports", "Imports from rest of world", 1, "Domestic demand met from abroad."),
        Flow("fx_chg", "Change in net foreign assets", 1, "External balancing flow."),
        Flow("interest", "Interest payments", 1, "Interest on government debt to money/bill holders."),
        Flow("dividend_swf", "Sovereign-fund dividend", 1, "Citizens' per-capita dividend from the sovereign fund's capital stake (UBC)."),
        Flow("transfer_intl", "International transfer", 1, "Cross-border secondary income to households (the pooled global dividend); RoW counterpart."),
    ]
}


# --------------------------------------------------------------------------- #
# Canonical macro series. Addressed by DBnomics provider/dataset + DIMENSIONS.
# Querying by dimensions (not a dotted series code) is order-independent and
# robust: DBnomics returns the matching series regardless of code layout.
# --------------------------------------------------------------------------- #
# Map a geo to the code each provider expects (Eurostat = 2-letter, AMECO = ISO3)
# Eurostat 2-letter geo -> AMECO geo dimension value. AMECO on DBnomics codes
# the country dimension as LOWERCASE ISO3 (proven working query: {"geo":["grc"]}).
# Euro-area members (share the euro; no own exchange rate). The rest of the EU
# keep national currencies -> an exchange-rate channel applies to them.
EURO_MEMBERS = {"AT", "BE", "CY", "EE", "FI", "FR", "DE", "EL", "GR", "IE", "IT",
                "LV", "LT", "LU", "MT", "NL", "PT", "SK", "SI", "ES", "HR", "EA20"}

# Statistical AGGREGATES (valid standalone geos, NEVER bloc members - mixing an
# aggregate with its member states in MultiRegion double-counts the population).
AGGREGATE_GEOS = {"EA20", "EU27_2020"}


def is_euro(geo: str) -> bool:
    """True if `geo` is in the euro area (no independent exchange rate)."""
    return geo.upper() in EURO_MEMBERS


_AMECO_GEO = {
    "AT": "aut", "BE": "bel", "BG": "bgr", "HR": "hrv", "CY": "cyp",
    "CZ": "cze", "DK": "dnk", "EE": "est", "FI": "fin", "FR": "fra",
    "DE": "deu", "EL": "grc", "GR": "grc", "HU": "hun", "IE": "irl",
    "IT": "ita", "LV": "lva", "LT": "ltu", "LU": "lux", "MT": "mlt",
    "NL": "nld", "PL": "pol", "PT": "prt", "RO": "rom", "SK": "svk",  # AMECO uses legacy ROM for Romania
    "SI": "svn", "ES": "esp", "SE": "swe",
    "EA20": "ea20", "EU27_2020": "eu27",
}

# ISO2 -> ISO3 for OECD / SDMX REF_AREA dims (OECD uses ROU for Romania).
_ISO3 = {
    "AT": "AUT", "BE": "BEL", "BG": "BGR", "HR": "HRV", "CY": "CYP",
    "CZ": "CZE", "DK": "DNK", "EE": "EST", "FI": "FIN", "FR": "FRA",
    "DE": "DEU", "EL": "GRC", "GR": "GRC", "HU": "HUN", "IE": "IRL",
    "IT": "ITA", "LV": "LVA", "LT": "LTU", "LU": "LUX", "MT": "MLT",
    "NL": "NLD", "PL": "POL", "PT": "PRT", "RO": "ROU", "SK": "SVK",
    "SI": "SVN", "ES": "ESP", "SE": "SWE",
}


@dataclass
class Series:
    code: str                       # canonical schema name
    label: str
    unit: str
    provider: str                   # DBnomics provider, e.g. "Eurostat"
    dataset: str                    # DBnomics dataset code
    dimensions: Dict[str, str]      # dim_code -> value ("{geo}" placeholder ok)
    source_url: str
    note: str = ""
    live: bool = True               # attempt a live pull (False = snapshot-only)
    geo_dim: str = "geo"            # which dimension carries the country code
    scale: float = 1.0             # multiply live values (e.g. percent->0-1)

    def for_geo(self, geo: str) -> "Series":
        """Bind the geo placeholder to a country code (provider-specific)."""
        dims = dict(self.dimensions)
        if self.geo_dim in dims and dims[self.geo_dim] == "{geo}":
            if self.provider.upper() == "AMECO":
                dims[self.geo_dim] = _AMECO_GEO.get(geo, geo)
            elif self.provider.upper() == "OECD":
                dims[self.geo_dim] = _ISO3.get(geo.upper(), geo)
            else:
                dims[self.geo_dim] = geo
        return Series(self.code, self.label, self.unit, self.provider,
                      self.dataset, dims, self.source_url, self.note,
                      self.live, self.geo_dim, self.scale)

    def hint(self) -> str:
        body = ",".join(f"{k}={v}" for k, v in self.dimensions.items())
        return f"{self.provider}/{self.dataset}[{body}]"


SERIES: Dict[str, Series] = {
    s.code: s
    for s in [
        Series(
            "gdp", "GDP at current prices", "MEUR", "Eurostat", "nama_10_gdp",
            {"freq": "A", "unit": "CP_MEUR", "na_item": "B1GQ", "geo": "{geo}"},
            "https://ec.europa.eu/eurostat/databrowser/product/view/nama_10_gdp",
            "Expenditure-side GDP (B1GQ), current prices."),
        Series(
            "hh_consumption", "Household final consumption", "MEUR",
            "Eurostat", "nama_10_gdp",
            {"freq": "A", "unit": "CP_MEUR", "na_item": "P31_S14_S15", "geo": "{geo}"},
            "https://ec.europa.eu/eurostat/databrowser/product/view/nama_10_gdp",
            "Household + NPISH final consumption (P31_S14_S15)."),
        Series(
            "gov_consumption", "Government final consumption", "MEUR",
            "Eurostat", "nama_10_gdp",
            {"freq": "A", "unit": "CP_MEUR", "na_item": "P3_S13", "geo": "{geo}"},
            "https://ec.europa.eu/eurostat/databrowser/product/view/nama_10_gdp",
            "General government final consumption (P3_S13)."),
        Series(
            "gfcf", "Gross fixed capital formation", "MEUR",
            "Eurostat", "nama_10_gdp",
            {"freq": "A", "unit": "CP_MEUR", "na_item": "P51G", "geo": "{geo}"},
            "https://ec.europa.eu/eurostat/databrowser/product/view/nama_10_gdp",
            "Investment proxy for the AI-capex injection (P51G)."),
        Series(
            "gcf", "Gross capital formation (P5G, incl. inventories)", "MEUR",
            "Eurostat", "nama_10_gdp",
            {"freq": "A", "unit": "CP_MEUR", "na_item": "P5G", "geo": "{geo}"},
            "https://ec.europa.eu/eurostat/databrowser/product/view/nama_10_gdp",
            "Total gross capital formation. inventories = gcf - gfcf (P52+P53); "
            "closes the expenditure identity (the systematic positive nx_gap "
            "found 2026-06-11 was this omitted component, not a discrepancy)."),
        Series(
            "exports", "Exports of goods and services", "MEUR", "Eurostat", "nama_10_gdp",
            {"freq": "A", "unit": "CP_MEUR", "na_item": "P6", "geo": "{geo}"},
            "https://ec.europa.eu/eurostat/databrowser/product/view/nama_10_gdp",
            "Exports (P6) - foreign demand for domestic output."),
        Series(
            "imports", "Imports of goods and services", "MEUR", "Eurostat", "nama_10_gdp",
            {"freq": "A", "unit": "CP_MEUR", "na_item": "P7", "geo": "{geo}"},
            "https://ec.europa.eu/eurostat/databrowser/product/view/nama_10_gdp",
            "Imports (P7) - domestic demand met from abroad."),
        Series(
            "hh_debt_gdp", "Household debt (% of GDP)", "PC_GDP", "BIS", "WS_TC",
            {"FREQ": "Q", "BORROWERS_CTY": "{geo}", "TC_BORROWERS": "H",
             "TC_LENDERS": "A", "VALUATION": "M", "UNIT_TYPE": "770",
             "TC_ADJUST": "A"},
            "https://www.bis.org/statistics/totcredit.htm",
            "BIS total credit to households & NPISHs, % of GDP (WS_TC; "
            "UNIT_TYPE 770 = % of GDP, geo dim BORROWERS_CTY; probe-confirmed "
            "2026-06-14). Live with snapshot fallback.",
            live=True, geo_dim="BORROWERS_CTY"),
        Series(
            "top10_wealth_share", "Top 10% share of net wealth", "SHARE",
            "OECD", "DSD_WEALTH@DF_WEALTH",
            {"FREQ": "A", "MEASURE": "SH_TOP10", "REF_AREA": "{geo}",
             "STATISTICAL_OPERATION": "_Z", "THRESHOLD": "_Z",
             "UNIT_MEASURE": "PT_B90_S14"},
            "https://www.oecd.org/social/wealth-distribution-database.htm",
            "OECD Wealth Distribution Database, share of top 10% of net wealth "
            "(SH_TOP10; probe-confirmed 2026-06-14). Percent -> 0-1 via scale; "
            "annual, most-recent vintage (~2021). Feeds Universal Basic Capital.",
            live=True, geo_dim="REF_AREA", scale=0.01),
        Series(
            "gov_debt_gdp", "General government gross debt (% of GDP)", "PC_GDP",
            "Eurostat", "gov_10dd_edpt1",
            {"freq": "A", "unit": "PC_GDP", "sector": "S13", "na_item": "GD",
             "geo": "{geo}"},
            "https://ec.europa.eu/eurostat/databrowser/product/view/gov_10dd_edpt1",
            "Maastricht general government gross debt (S13)."),
        Series(
            "gini_disp_income", "Gini of equivalised disposable income", "IDX",
            "Eurostat", "ilc_di12",
            {"freq": "A", "geo": "{geo}"},
            "https://ec.europa.eu/eurostat/databrowser/product/view/ilc_di12",
            "EU-SILC Gini coefficient of equivalised disposable income."),
        Series(
            "population", "Population (average)", "PERSONS",
            "Eurostat", "demo_gind",
            {"freq": "A", "indic_de": "AVG", "geo": "{geo}"},
            "https://ec.europa.eu/eurostat/databrowser/product/view/demo_gind",
            "Average population (per-capita and UBI calcs)."),
        # AMECO adjusted wage share (% of GDP at factor cost). LIVE: the geo
        # dimension is lowercase ISO3 on DBnomics (bound via _AMECO_GEO), e.g.
        # {"geo":["deu"]} for Germany. Falls back to snapshot if a pull fails.
        Series(
            "labour_share", "Adjusted wage share (% of GDP)", "PC_GDP",
            "AMECO", "ALCD2",
            {"geo": "{geo}"},
            "https://economy-finance.ec.europa.eu/economic-research-and-databases/economic-databases/ameco-database_en",
            "Adjusted wage share, total economy (AMECO ALCD2).",
            live=True),
    ]
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def active_sectors() -> List[Sector]:
    return [s for s in SECTORS.values() if s.active]


def active_instruments() -> List[Instrument]:
    return [i for i in INSTRUMENTS.values() if i.active]


def active_flows() -> List[Flow]:
    return [f for f in FLOWS.values() if f.active]


def series_for_geo(geo: str) -> Dict[str, Series]:
    return {code: s.for_geo(geo) for code, s in SERIES.items()}


# --------------------------------------------------------------------------- #
# DuckDB DDL - the local store layout.
# --------------------------------------------------------------------------- #
DDL: List[str] = [
    """
    CREATE TABLE IF NOT EXISTS series_data (
        geo          VARCHAR,
        series_code  VARCHAR,
        year         INTEGER,
        value        DOUBLE,
        unit         VARCHAR,
        provider     VARCHAR,
        provider_code VARCHAR,
        source_url   VARCHAR,
        retrieved_at TIMESTAMP,
        source       VARCHAR,
        PRIMARY KEY (geo, series_code, year)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS run_results (
        run_id VARCHAR, scenario VARCHAR, geo VARCHAR, year INTEGER,
        item VARCHAR, value DOUBLE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tfm (
        run_id VARCHAR, scenario VARCHAR, year INTEGER,
        flow VARCHAR, sector VARCHAR, value DOUBLE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bsm (
        run_id VARCHAR, scenario VARCHAR, year INTEGER,
        instrument VARCHAR, sector VARCHAR, value DOUBLE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS consistency_log (
        run_id VARCHAR, scenario VARCHAR, year INTEGER,
        check_name VARCHAR, passed BOOLEAN, max_residual DOUBLE
    )
    """,
]
