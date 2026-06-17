"""Scout orchestrator: checks -> optional Qwen brief + per-proposal patches ->
proposal report. Runs on YOUR machine on a schedule; applies nothing.

Patch drafting is grounded three ways: the real repo file list (allowable
paths), FILE EXCERPTS of the most-relevant files (so the model edits the symbol
that actually exists, not a guessed location), and a deterministic
path-verification backstop. Hallucinated or mis-located edits are therefore
either prevented or clearly flagged for the reviewer.
"""
from __future__ import annotations

import datetime as _dt
import glob
import hashlib
import json
import os
from typing import List, Optional, Tuple

from scout.checks import run_all_checks
from scout.llm import (QwenClient, draft_brief, draft_patch, unverified_paths,
                       _PATH_RE)
from scout.proposals import Finding, write_report, _sev_rank

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROPOSALS = os.path.join(_REPO, "proposals")
_SRC_DIRS = ("schema", "data", "modules", "consistency", "scout", "tests",
             "scripts", "dashboard", "docs")
_ROOT_FILES = ("calibration.py", "orchestrator.py", "scenarios.py",
               "conftest.py", "requirements.txt", "README.md", "CLAUDE.md")
_PATCHABLE = ("DATA_REVISION", "COVERAGE_GAP", "SNAPSHOT_ONLY", "TOOL",
              "NEW_DATASET")

# Per finding-kind, the files whose CONTENTS most help draft a correct patch.
# (Selection is intersected with the real repo file list, so a missing file is
# silently skipped; this is a relevance hint, never a source of truth.)
_KIND_FILES = {
    "SNAPSHOT_ONLY": ("schema/accounts.py", "data/connectors/dbnomics.py",
                      "scripts/verify_live.py"),
    "DATA_REVISION": ("data/connectors/dbnomics.py", "schema/accounts.py"),
    "NEWER_DATA":    ("schema/accounts.py", "data/connectors/dbnomics.py"),
    "LIVE_FAIL":     ("schema/accounts.py", "data/connectors/dbnomics.py",
                      "scripts/verify_live.py"),
    "NEW_DATASET":   ("schema/accounts.py", "data/connectors/dbnomics.py"),
    "COVERAGE_GAP":  ("data/cache/de_baseline_2019.json",
                      "data/connectors/dbnomics.py", "schema/accounts.py"),
    "TOOL":          ("data/connectors/__init__.py", "data/connectors/base.py",
                      "data/connectors/epoch.py"),
    "ROADMAP":       ("schema/accounts.py", "docs/ROADMAP.md"),
}


def repo_files() -> List[str]:
    """The real source/data/doc files, as repo-relative paths. Used to ground
    the patch-drafting prompt so the model cannot invent file paths."""
    out: List[str] = []
    for d in _SRC_DIRS:
        base = os.path.join(_REPO, d)
        if not os.path.isdir(base):
            continue
        for r, _dirs, fs in os.walk(base):
            if "__pycache__" in r:
                continue
            for fn in fs:
                if fn.endswith((".py", ".json", ".md")):
                    rel = os.path.relpath(os.path.join(r, fn), _REPO)
                    out.append(rel.replace(os.sep, "/"))
    for f in _ROOT_FILES:
        if os.path.exists(os.path.join(_REPO, f)):
            out.append(f)
    return sorted(set(out))


def relevant_files(finding: Finding, files: List[str]) -> List[str]:
    """Pick the repo files whose CONTENTS will help draft a correct patch for
    this finding: the geo snapshot (when geo-specific), a kind-based shortlist,
    and any real path the finding's own text/evidence already references. Only
    ever returns real repo files (a subset of `files`), order = relevance."""
    known = set(files)
    ordered: List[str] = []

    def add(rel: str) -> None:
        if rel in known and rel not in ordered:
            ordered.append(rel)

    geo = getattr(finding, "geo", None)
    if geo:
        pref = "data/cache/%s_baseline_" % geo.lower()
        for rel in files:
            if rel.startswith(pref):
                add(rel)
    for rel in _KIND_FILES.get(getattr(finding, "kind", ""), ()):
        add(rel)
    blob = " ".join(str(x) for x in (
        getattr(finding, "detail", ""), getattr(finding, "proposal", ""),
        json.dumps(getattr(finding, "evidence", {}), default=str)))
    for m in _PATH_RE.finditer(blob):
        add(m.group(0).lstrip("./"))
    return ordered


def _read_excerpt(rel: str, max_chars: int,
                  focus: Optional[str] = None) -> Optional[str]:
    """Read a repo-relative file. If it exceeds the budget, return a window
    focused on `focus` (e.g. the series code) when present, else the head."""
    try:
        with open(os.path.join(_REPO, rel), encoding="utf-8") as fh:
            text = fh.read()
    except Exception:
        return None
    if len(text) <= max_chars:
        return text
    if focus and focus in text:
        idx = text.index(focus)
        win = max(400, max_chars - 600)
        start = max(0, idx - win // 3)
        return (text[start:start + win] +
                "\n# ... (excerpt focused on '%s'; rest of file omitted) ..." % focus)
    return text[:max_chars] + "\n# ... (truncated) ..."


def build_excerpts(finding: Finding, files: List[str], max_files: int = 3,
                   per_file: int = 6000,
                   total_budget: int = 14000) -> Tuple[str, List[str]]:
    """Return (excerpt_block, used_files): labelled current contents of the most
    relevant real files, focused on the finding's series and budget-bounded so a
    local model's context window is never blown."""
    focus = getattr(finding, "series", None) or None
    blocks: List[str] = []
    used: List[str] = []
    budget = total_budget
    for rel in relevant_files(finding, files)[:max_files]:
        if budget <= 0:
            break
        ex = _read_excerpt(rel, min(per_file, budget), focus=focus)
        if not ex:
            continue
        blocks.append("===== %s =====\n%s" % (rel, ex))
        used.append(rel)
        budget -= len(ex)
    return "\n\n".join(blocks), used


# --------------------------------------------------------------------------- #
# Novelty filter — only surface a report when the finding SET actually changes.
# --------------------------------------------------------------------------- #
# Fields that define a finding's IDENTITY. LLM-variable fields (brief, patch),
# status and the run timestamp are deliberately excluded so re-runs over
# identical facts hash identically; any real change flips the hash.
_IDENTITY_FIELDS = ("kind", "severity", "title", "detail", "geo", "series",
                    "evidence")


def _finding_key(d: dict) -> str:
    return json.dumps({k: d.get(k) for k in _IDENTITY_FIELDS},
                      sort_keys=True, default=str, ensure_ascii=False)


def findings_fingerprint(findings: list) -> str:
    """Order-independent signature of the finding set (accepts Finding objects
    or plain dicts). Two runs with the same underlying findings -> same hash."""
    keys = sorted(_finding_key(f.as_dict() if hasattr(f, "as_dict") else f)
                  for f in findings)
    h = hashlib.sha256()
    for k in keys:
        h.update(k.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def _latest_report_json(out_dir: str) -> Optional[str]:
    """Most recent written report's JSON path (timestamp stems sort lexically)."""
    paths = sorted(glob.glob(os.path.join(out_dir, "*_scout.json")))
    return paths[-1] if paths else None


def _prior_fingerprint(out_dir: str) -> Optional[str]:
    p = _latest_report_json(out_dir)
    if not p:
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            return findings_fingerprint(json.load(fh).get("findings", []))
    except Exception:
        return None


def _write_heartbeat(out_dir: str, fingerprint: str, changed: bool,
                     report: Optional[str], n: int) -> None:
    """Record that the scout RAN, even on a no-change day (so 'it ran and found
    nothing new' is auditable, distinct from 'it never ran'). Not a report:
    deliberately named so the *_scout.json glob never picks it up."""
    os.makedirs(out_dir, exist_ok=True)
    rec = {
        "ran_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "changed": changed, "fingerprint": fingerprint, "n_findings": n,
        "report": os.path.basename(report) if report else None,
    }
    with open(os.path.join(out_dir, ".last_run.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)


def run_scout(geos: Optional[List[str]] = None, year: int = 2019,
              use_llm: str = "auto", allow_live: bool = True,
              out_dir: Optional[str] = None, discover: bool = False,
              max_patches: int = 6, force: bool = False) -> dict:
    """use_llm: 'auto' | 'on' | 'off'. Returns a summary dict."""
    geos = geos or ["DE", "FR"]
    out_dir = out_dir or _PROPOSALS
    findings: List[Finding] = run_all_checks(geos, year, allow_live=allow_live,
                                             discover=discover)

    # Novelty filter: if the finding SET is identical to the most recent report,
    # surface nothing (skip the LLM and the write) unless force=True. Stops the
    # daily repeat when the scout has nothing new to say.
    fingerprint = findings_fingerprint(findings)
    prior = _prior_fingerprint(out_dir)
    if prior is not None and prior == fingerprint and not force:
        prior_report = _latest_report_json(out_dir)
        _write_heartbeat(out_dir, fingerprint, changed=False,
                         report=prior_report, n=len(findings))
        return {
            "report": None, "changed": False, "fingerprint": fingerprint,
            "prior_report": prior_report, "n_findings": len(findings),
            "llm_used": False, "patches": 0, "flagged_paths": 0,
            "excerpted": 0, "by_kind": _counts(findings), "findings": findings,
        }

    brief, llm_used, patches, flagged, excerpted = None, False, 0, 0, 0
    if use_llm in ("auto", "on"):
        client = QwenClient()
        if use_llm == "on" or client.available():
            brief = draft_brief(
                client, json.dumps([f.as_dict() for f in findings], default=str))
            llm_used = brief is not None
            if llm_used and max_patches > 0:
                files = repo_files()
                actionable = sorted(
                    [f for f in findings if f.kind in _PATCHABLE],
                    key=lambda f: -_sev_rank(f.severity))[:max_patches]
                for f in actionable:
                    excerpts, _used = build_excerpts(f, files)
                    p = draft_patch(client, json.dumps(f.as_dict(), default=str),
                                    files, excerpts)
                    if not p:
                        continue
                    if excerpts:
                        excerpted += 1
                    bad = unverified_paths(p, files)
                    if bad:
                        flagged += 1
                        p += ("\n\n> ⚠ Draft references path(s) not found in "
                              "the repo: " + ", ".join(bad) +
                              " - verify before applying (likely hallucinated).")
                    f.patch = p
                    patches += 1

    path = write_report(findings, out_dir, geos=geos, brief=brief,
                        llm_used=llm_used)
    _write_heartbeat(out_dir, fingerprint, changed=True, report=path,
                     n=len(findings))
    return {
        "report": path, "changed": True, "fingerprint": fingerprint,
        "n_findings": len(findings), "llm_used": llm_used,
        "patches": patches, "flagged_paths": flagged, "excerpted": excerpted,
        "by_kind": _counts(findings), "findings": findings,
    }


def _counts(findings: List[Finding]) -> dict:
    c: dict = {}
    for f in findings:
        c[f.kind] = c.get(f.kind, 0) + 1
    return c
