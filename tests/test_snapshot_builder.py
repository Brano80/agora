"""Snapshot builder — self-populating baseline snapshots from live DBnomics.

All tests run OFFLINE (network-independent): the builder round-trips the bundled
snapshots, which exercises the assembly, import-reconciliation, default-flagging,
validation, and write paths without any live pull. The live path runs on the
user's machine.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from data.connectors.dbnomics import DBnomicsConnector
from data.snapshot_builder import (build_snapshot, write_snapshot_file,
                                    validate_snapshot, REQUIRED)


@pytest.fixture(scope="module")
def offline():
    return DBnomicsConnector(allow_live=False)


@pytest.mark.parametrize("geo", ["DE", "FR", "PL"])
def test_offline_round_trip_builds_and_validates(offline, geo):
    """Rebuilding an existing country from its snapshot must be buildable, close
    the expenditure identity, and PASS calibration validation (the trust gate)."""
    snap, rep = build_snapshot(geo, 2019, connector=offline)
    assert rep.buildable and not rep.missing_required
    assert all(c in snap["series"] for c in REQUIRED)
    # POLICY (2026-06-11): imports are direct pulls; the statistical
    # discrepancy is allowed but bounded (<1% of GDP), tracked as nx_gap.
    assert rep.identity_residual <= 0.01 * snap["series"]["gdp"]["value"]
    assert rep.calibration_ok is True
    assert rep.worst_gate_residual < 1.0


def test_provenance_is_stamped_on_every_series(offline):
    snap, _ = build_snapshot("DE", 2019, connector=offline)
    for code, entry in snap["series"].items():
        for field in ("value", "unit", "provider", "provider_code",
                      "source_url", "note", "source"):
            assert field in entry, f"{code} missing {field}"
        assert entry["source"] in ("live", "snapshot", "reconciled",
                                   "default_review")


def test_imports_are_reconciled_to_the_identity(offline):
    snap, rep = build_snapshot("PL", 2019, connector=offline,
                               reconcile_imports=True)
    assert "imports" in rep.reconciled
    s = snap["series"]
    M = s["imports"]["value"]
    expect = (s["exports"]["value"]
              - (s["gdp"]["value"] - s["hh_consumption"]["value"]
                 - s["gfcf"]["value"] - s["gov_consumption"]["value"]))
    assert abs(M - expect) < 1e-6
    assert s["imports"]["source"] == "reconciled"


def test_unavailable_country_reports_missing_not_crashes(offline):
    """A geo with no snapshot AND no live coverage (synthetic 'ZZ', robust on any
    machine) is flagged un-buildable and its optional series defaulted —
    gracefully, not via an exception."""
    snap, rep = build_snapshot("ZZ", 2019, connector=offline)
    assert rep.buildable is False
    assert rep.missing_required                          # required Eurostat series
    assert set(rep.defaulted) <= {"labour_share", "hh_debt_gdp",
                                  "top10_wealth_share"}
    assert rep.calibration_ok is None                    # not validated when unbuildable


def test_defaults_are_flagged_for_review(offline):
    snap, rep = build_snapshot("ZZ", 2019, connector=offline)
    for code in rep.defaulted:
        assert snap["series"][code]["source"] == "default_review"
        assert "verify" in snap["series"][code]["note"].lower()


def test_write_round_trips_and_recalibrates(offline):
    """A written snapshot must reload via the connector and re-validate — proving
    the file the builder emits is itself trustworthy and self-consistent."""
    snap, _ = build_snapshot("DE", 2019, connector=offline)
    with tempfile.TemporaryDirectory() as d:
        path = write_snapshot_file(snap, "ZZ", 2019, cache_dir=d)
        assert os.path.exists(path)
        reloaded = json.load(open(path, encoding="utf-8"))
        vals = {c: e["value"] for c, e in reloaded["series"].items()}
        ok, fails, worst = validate_snapshot(vals, "DE", 2019)
        assert ok, f"written snapshot failed re-validation: {fails}"
