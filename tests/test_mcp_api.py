"""AGORA-over-MCP tool layer (mcp_api) — the spike's regression guard.

Pins the two non-negotiable guardrails at the MCP boundary:
  1. the consistency gate gates every payload (failing runs return an error
     payload with NO series), and
  2. the sandbox-not-oracle disclaimer + assumptions + data provenance travel
     with every result.
Offline by design (allow_live=False -> validated snapshots). The mcp_server.py
shim is import-tested only when the optional `mcp` package is present.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import mcp_api
from mcp_api import ToolError, _public


# --------------------------------------------------------------------------- #
# run_scenario
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def baseline_payload():
    return mcp_api.run_scenario(geo="DE", horizon=10, allow_live=False)


def test_run_scenario_baseline_gated(baseline_payload):
    p = baseline_payload
    assert "error" not in p
    assert p["gate"]["passed"] is True
    assert p["gate"]["max_residual"] < 1e-2      # MEUR residual, gate-clean
    assert p["geo"] == "DE" and p["base_year"] == 2019


def test_payload_carries_guardrails(baseline_payload):
    p = baseline_payload
    assert "sandbox" in p["disclaimer"].lower()
    assert "not" in p["disclaimer"].lower()      # "not an oracle / NOT forecasts"
    levers = p["assumptions"]["levers"]
    assert "labour_share" in levers and "tax_capital" in levers
    assert set(levers["labour_share"]) == {"start", "end", "path"}
    # provenance: every macro series maps to a source bucket
    src = p["data_sources"]
    codes = [c for k, v in src.items() if k != "note" for c in v]
    assert "gdp" in codes


def test_run_scenario_series_selection(baseline_payload):
    p = baseline_payload
    assert set(p["series"]) == set(mcp_api.DEFAULT_SERIES)
    assert len(p["series"]["gdp"]) == 10
    assert len(p["years"]) == 10
    assert p["summary"]["gdp_end"] == p["series"]["gdp"][-1]


def test_run_scenario_unknown_series_hint():
    p = mcp_api.run_scenario(geo="DE", horizon=5, series=["gdp", "nope"],
                             allow_live=False)
    assert "nope" in p["series_not_found"]["requested"]
    assert "gini_personal" in p["series_not_found"]["available"]
    assert "gdp" in p["series"]


def test_run_scenario_ubc_vs_baseline_wealth():
    ubc = mcp_api.run_scenario(geo="DE", horizon=30, labour_share_end=0.30,
                               capex_growth=0.06, capital_tax=0.40, ubc=True,
                               allow_live=False)
    assert ubc["gate"]["passed"]
    base = mcp_api.run_scenario(geo="DE", horizon=30, allow_live=False)
    # the durable UBC verdict: top-10% wealth share collapses vs baseline
    assert (ubc["summary"]["top10_wealth_share_end"]
            < base["summary"]["top10_wealth_share_end"])


# --------------------------------------------------------------------------- #
# guardrail: gate refusal + input validation
# --------------------------------------------------------------------------- #
def test_gate_refusal_withholds_series():
    """A failing gate must produce an error payload with NO series."""
    @_public
    def failing_tool():
        class _Check:
            name, passed, max_residual, detail = "row_balance", False, 42.0, ""
        class _Rep:
            year = 2019
            @property
            def passed(self):
                return False
            @property
            def max_residual(self):
                return 42.0
            def failures(self):
                return [_Check()]
        class _Run:
            scenario, reports, consistent, max_residual = \
                "leaky", [_Rep()], False, 42.0
        return mcp_api._require_gate(_Run())

    p = failing_tool()
    assert "error" in p and "withheld" in p["error"]
    assert p["gate"]["passed"] is False
    assert p["gate"]["failures"][0]["check"] == "row_balance"
    assert "series" not in p
    assert "disclaimer" in p


def test_unknown_geo_actionable():
    p = mcp_api.run_scenario(geo="XX", allow_live=False)
    assert "error" in p and "Unknown geo 'XX'" in p["error"]
    assert "DE" in p["error"]                    # lists what IS available


def test_ubi_and_ubc_mutually_exclusive():
    p = mcp_api.run_scenario(geo="DE", ubi=True, ubc=True, capital_tax=0.4,
                             allow_live=False)
    assert "error" in p and "cannot set both" in p["error"]


def test_bad_capital_tax_rejected():
    p = mcp_api.run_scenario(geo="DE", capital_tax=1.5, allow_live=False)
    assert "error" in p and "capital_tax" in p["error"]


def test_bad_horizon_rejected():
    p = mcp_api.run_scenario(geo="DE", horizon=1, allow_live=False)
    assert "error" in p and "horizon" in p["error"]


# --------------------------------------------------------------------------- #
# compare
# --------------------------------------------------------------------------- #
def test_compare_ubc_preset():
    p = mcp_api.compare(geo="DE", preset="ubc", horizon=15,
                        series=["gini_personal", "top10_wealth_share"],
                        allow_live=False)
    assert "error" not in p
    assert [r["scenario"] for r in p["runs"]] == [
        "Baseline", "AI shift, no policy", "AI + Cash UBI",
        "AI + Universal Basic Capital"]
    assert all(r["gate"]["passed"] for r in p["runs"])
    by = {r["scenario"]: r for r in p["runs"]}
    # flow-vs-stock: UBC ends with lower top-10% wealth than cash UBI
    assert (by["AI + Universal Basic Capital"]["summary"]
            ["top10_wealth_share_end"]
            < by["AI + Cash UBI"]["summary"]["top10_wealth_share_end"])


def test_compare_custom_scenarios():
    p = mcp_api.compare(geo="FR", horizon=8, series=["gdp"], scenarios=[
        {"name": "hold"},
        {"name": "shock", "labour_share_end": 0.30, "capex_growth": 0.06}],
        allow_live=False)
    assert "error" not in p
    assert [r["scenario"] for r in p["runs"]] == ["hold", "shock"]
    assert all(r["gate"]["passed"] for r in p["runs"])
    assert len(p["runs"][0]["series"]["gdp"]) == 8


def test_compare_unknown_lever_actionable():
    p = mcp_api.compare(geo="DE", scenarios=[{"name": "x", "warp_speed": 9}],
                        allow_live=False)
    assert "error" in p and "warp_speed" in p["error"]
    assert "labour_share_end" in p["error"]      # tells the caller what exists


def test_compare_nothing_to_compare():
    p = mcp_api.compare(geo="DE", allow_live=False)
    assert "error" in p and "preset" in p["error"]


# --------------------------------------------------------------------------- #
# catalogue tools
# --------------------------------------------------------------------------- #
def test_list_modules_shape():
    p = mcp_api.list_modules()
    names = [m["name"] for m in p["modules"]]
    assert names == ["sfc_core", "distribution", "input_output"]
    sfc = p["modules"][0]
    assert "gdp" in sfc["inputs"] and "gdp" in sfc["outputs"]


def test_get_series_catalogue_and_detail():
    cat = mcp_api.get_series()
    codes = {s["code"] for s in cat["series"]}
    assert {"gdp", "labour_share", "top10_wealth_share"} <= codes
    det = mcp_api.get_series("labour_share")
    assert det["provider"].upper() == "AMECO"
    assert det["source_url"].startswith("http")
    bad = mcp_api.get_series("nope")
    assert "error" in bad and "gdp" in bad["error"]


def test_list_geos_shape():
    p = mcp_api.list_geos()
    by = {g["geo"]: g for g in p["geos"]}
    assert "DE" in by and "FR" in by
    assert by["EA20"]["aggregate"] is True
    assert by["DE"]["aggregate"] is False
    assert by["DE"]["io_matrix"] is True


def test_validate_baseline_de():
    p = mcp_api.validate_baseline(geo="DE", allow_live=False)
    assert "error" not in p
    assert p["gate"]["passed"] and p["all_ok"]
    metrics = [r["metric"] for r in p["rows"]]
    assert any("GDP" in m for m in metrics)


# --------------------------------------------------------------------------- #
# the shim (only when the optional mcp package is installed)
# --------------------------------------------------------------------------- #
def test_mcp_server_shim_registers_tools():
    pytest.importorskip("mcp")
    import mcp_server
    import asyncio
    tools = asyncio.get_event_loop().run_until_complete(
        mcp_server.mcp.list_tools())
    names = {t.name for t in tools}
    assert {"agora_run_scenario", "agora_compare", "agora_list_modules",
            "agora_get_series", "agora_list_geos",
            "agora_validate_baseline"} <= names
