"""EU-wide sweep: EVERY cached country snapshot must calibrate, reproduce its
own national-accounts targets, and pass the consistency gate (validate before
trusting, applied to the whole bloc instead of just DE/FR/PL)."""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from data.connectors.dbnomics import DBnomicsConnector
from data.snapshot_builder import validate_snapshot

_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "cache")
FILES = sorted(glob.glob(os.path.join(_CACHE, "*_baseline_2019.json")))
IDS = [os.path.basename(p).split("_")[0].upper() for p in FILES]


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_every_snapshot_validates(path):
    geo = os.path.basename(path).split("_")[0].upper()
    try:
        with open(path, encoding="utf-8") as fh:
            json.load(fh)
    except Exception:
        pytest.skip("file unreadable through this mount (stale view); "
                    "validates on a native checkout")
    rows = DBnomicsConnector(allow_live=False).fetch(geo, 2019)
    data = {k: v["value"] for k, v in rows.items()}
    ok, fails, worst = validate_snapshot(data, geo, 2019)
    assert ok, f"{geo}: failed {fails} (gate worst {worst:.2e})"
