"""Scout tests — deterministic checks, graceful offline LLM, report writing.

All run offline (no network, no Qwen) and are network-independent so they pass
on a machine WITH live access too.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scout.checks import coverage_findings, snapshot_geos, freshness_findings
from scout.llm import QwenClient
from scout.scout import run_scout
from data.connectors.dbnomics import DBnomicsConnector


def test_snapshot_geos_detected():
    geos = snapshot_geos()
    assert "DE" in geos and "FR" in geos


def test_coverage_flags_snapshot_only_and_gaps():
    fs = coverage_findings(2019)
    # all series are now wired live -> the backlog is cleared (no snapshot-only)
    assert not any(f.kind == "SNAPSHOT_ONLY" for f in fs)
    # EA20 built 2026-06-11 -> its gap finding must be GONE (coverage works
    # both ways: flags missing geos, stops flagging built ones).
    assert not any(f.kind == "COVERAGE_GAP" and f.geo == "EA20" for f in fs)
    assert any(f.kind == "ROADMAP" for f in fs)


def test_freshness_skipped_when_offline():
    # offline connector cannot assess freshness -> returns nothing (graceful),
    # and produces no misleading LIVE_FAIL noise. Network-independent.
    conn = DBnomicsConnector(allow_live=False)
    assert freshness_findings("DE", 2019, connector=conn) == []


def test_qwen_client_offline_is_graceful():
    client = QwenClient(base_url="http://127.0.0.1:1/v1", timeout=2)
    assert client.available() is False
    assert client.chat([{"role": "user", "content": "hi"}]) is None


def test_run_scout_offline_writes_report():
    with tempfile.TemporaryDirectory() as d:
        res = run_scout(geos=["DE"], year=2019, use_llm="off",
                        allow_live=False, out_dir=d)
        assert res["n_findings"] > 0          # coverage findings still present
        assert res["llm_used"] is False
        assert os.path.exists(res["report"])
        assert os.path.exists(res["report"].replace(".md", ".json"))
        with open(res["report"], encoding="utf-8") as fh:
            assert "PROPOSALS — review required" in fh.read()


def test_catalog_findings_from_datasources_doc():
    from scout.checks import catalog_findings
    fs = catalog_findings()
    assert fs and all(f.kind == "TOOL" for f in fs)
    blob = " ".join(str(f.evidence.get("sources", [])) for f in fs)
    # known catalog sources should surface as connector candidates
    assert any(name in blob for name in ("BIS", "WID", "Penn World Table",
                                         "Epoch", "EU KLEMS"))
    # already-implemented source must NOT be proposed
    assert "DBnomics" not in blob


def test_repo_files_lists_real_files():
    from scout.scout import repo_files
    files = repo_files()
    assert "schema/accounts.py" in files
    assert "modules/distribution.py" in files
    assert "data/cache/de_baseline_2019.json" in files
    assert not any("__pycache__" in f for f in files)


def test_unverified_paths_flags_hallucinated_only():
    from scout.scout import repo_files
    from scout.llm import unverified_paths
    files = repo_files()
    # the exact hallucination the review caught
    bad = unverified_paths("Edit `datasets/ameco.py` and set live=True.", files)
    assert "datasets/ameco.py" in bad
    # a real path must NOT be flagged
    assert unverified_paths("Edit `schema/accounts.py` to flip live.", files) == []
    # a real data file must NOT be flagged
    assert unverified_paths("Update data/cache/de_baseline_2019.json", files) == []


# --- patch-hardening: feed the model the actual file CONTENTS --------------- #
def _snapshot_only_finding():
    """Synthetic SNAPSHOT_ONLY finding for a real series. (Every series is now
    wired live, so we construct one to exercise the patch-relevance/excerpt logic
    that targets schema/accounts.py.)"""
    from scout.proposals import Finding
    return Finding("SNAPSHOT_ONLY", "medium",
                   "Series 'top10_wealth_share' is snapshot-only",
                   "synthetic fixture", series="top10_wealth_share")


def test_relevant_files_series_finding_points_at_schema():
    """The hh_debt_gdp fix lives in schema/accounts.py (the live= flag), NOT
    in the connector. Relevance selection must surface accounts.py, and every
    file it returns must be a real repo file."""
    from scout.scout import repo_files, relevant_files
    files = repo_files()
    rel = relevant_files(_snapshot_only_finding(), files)
    assert "schema/accounts.py" in rel
    assert all(r in files for r in rel)                 # never invents a path


def test_relevant_files_geo_finding_includes_snapshot():
    from scout.scout import repo_files, relevant_files
    from scout.proposals import Finding
    files = repo_files()
    f = Finding("DATA_REVISION", "high", "x", "y", geo="DE", series="gdp")
    rel = relevant_files(f, files)
    assert any(r.startswith("data/cache/de_baseline_") for r in rel)
    assert all(r in files for r in rel)


def test_build_excerpts_surfaces_real_edit_site():
    """The excerpt for the snapshot-only series must contain the actual
    `live=False` line from accounts.py — the decisive evidence the model lacked."""
    from scout.scout import repo_files, build_excerpts
    files = repo_files()
    block, used = build_excerpts(_snapshot_only_finding(), files)
    assert used and all(u in files for u in used)       # only real files
    assert "schema/accounts.py" in used
    assert "top10_wealth_share" in block                  # the real edit site
    assert "===== schema/accounts.py =====" in block     # labelled per file


def test_build_excerpts_is_budget_bounded():
    from scout.scout import repo_files, build_excerpts
    files = repo_files()
    block, used = build_excerpts(_snapshot_only_finding(), files,
                                 max_files=3, total_budget=14000)
    assert len(used) <= 3
    assert len(block) <= 14000 + 3 * 200                 # budget + label overhead


def test_draft_patch_offline_graceful_with_excerpts():
    """draft_patch must accept the new file_excerpts arg and still degrade to
    None when the local model is unreachable."""
    from scout.llm import draft_patch, QwenClient
    client = QwenClient(base_url="http://127.0.0.1:1/v1", timeout=2)
    assert draft_patch(client, "{}", ["schema/accounts.py"],
                       "===== schema/accounts.py =====\nlive=False") is None


# --- novelty filter: only surface a report when the finding SET changes ----- #
def test_fingerprint_ignores_llm_and_status_fields():
    from scout.scout import findings_fingerprint
    from scout.proposals import Finding
    a = Finding("TOOL", "low", "t", "d", evidence={"x": 1})
    b = Finding("TOOL", "low", "t", "d", evidence={"x": 1},
                patch="some LLM patch", status="APPLIED")
    assert findings_fingerprint([a]) == findings_fingerprint([b])  # LLM-blind
    c = Finding("TOOL", "low", "t", "d", evidence={"x": 2})        # real change
    assert findings_fingerprint([a]) != findings_fingerprint([c])


def test_fingerprint_is_order_independent():
    from scout.scout import findings_fingerprint
    from scout.proposals import Finding
    a = Finding("SNAPSHOT_ONLY", "medium", "a", "d", series="x")
    b = Finding("TOOL", "low", "b", "d")
    assert findings_fingerprint([a, b]) == findings_fingerprint([b, a])


def test_scout_skips_report_when_unchanged():
    import glob as _glob
    with tempfile.TemporaryDirectory() as d:
        r1 = run_scout(geos=["DE"], year=2019, use_llm="off",
                       allow_live=False, out_dir=d)
        assert r1["changed"] is True and r1["report"]
        r2 = run_scout(geos=["DE"], year=2019, use_llm="off",
                       allow_live=False, out_dir=d)
        assert r2["changed"] is False          # identical findings -> no surface
        assert r2["report"] is None
        assert r2["fingerprint"] == r1["fingerprint"]
        # exactly ONE report written despite two runs
        assert len(_glob.glob(os.path.join(d, "*_scout.json"))) == 1
        # but the run is still auditable via the heartbeat
        assert os.path.exists(os.path.join(d, ".last_run.json"))


def test_scout_force_writes_even_when_unchanged():
    with tempfile.TemporaryDirectory() as d:
        run_scout(geos=["DE"], year=2019, use_llm="off",
                  allow_live=False, out_dir=d)
        rf = run_scout(geos=["DE"], year=2019, use_llm="off",
                       allow_live=False, out_dir=d, force=True)
        assert rf["changed"] is True
        assert rf["report"] and os.path.exists(rf["report"])


def test_scout_heartbeat_excluded_from_report_glob():
    """.last_run.json must never be mistaken for a report."""
    import glob as _glob
    with tempfile.TemporaryDirectory() as d:
        run_scout(geos=["DE"], year=2019, use_llm="off",
                  allow_live=False, out_dir=d)
        reports = _glob.glob(os.path.join(d, "*_scout.json"))
        assert all(".last_run" not in os.path.basename(p) for p in reports)
