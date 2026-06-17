"""Findings + the proposal-report writer. The scout's only output.

A Finding is a single observation, optionally carrying a concrete proposed
change and (when the local model is up) an LLM-drafted implementation patch.
Reports are markdown (for you) + JSON (for tooling / the review task). Status is
always PENDING_REVIEW; the scout applies nothing.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

KINDS = ("DATA_REVISION", "NEWER_DATA", "LIVE_FAIL", "SNAPSHOT_ONLY",
         "COVERAGE_GAP", "NEW_DATASET", "TOOL", "ROADMAP")
SEVERITIES = ("info", "low", "medium", "high")


@dataclass
class Finding:
    kind: str
    severity: str
    title: str
    detail: str
    proposal: str = ""                       # concrete suggested change (for review)
    geo: Optional[str] = None
    series: Optional[str] = None
    evidence: Dict[str, object] = field(default_factory=dict)
    patch: str = ""                          # LLM-drafted implementation sketch
    status: str = "PENDING_REVIEW"

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


def _sev_rank(s: str) -> int:
    return SEVERITIES.index(s) if s in SEVERITIES else 0


def write_report(findings: List[Finding], out_dir: str,
                 geos: Optional[List[str]] = None,
                 brief: Optional[str] = None,
                 llm_used: bool = False) -> str:
    """Write a timestamped markdown + JSON proposal report. Returns the md path."""
    os.makedirs(out_dir, exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = os.path.join(out_dir, f"{ts}_scout")
    findings = sorted(findings, key=lambda f: -_sev_rank(f.severity))

    with open(stem + ".json", "w", encoding="utf-8") as fh:
        json.dump({
            "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "geos": geos or [], "llm_used": llm_used,
            "n_findings": len(findings),
            "findings": [f.as_dict() for f in findings],
        }, fh, indent=2)

    lines: List[str] = [
        f"# AGORA scout report — {ts}",
        "",
        f"_Geos: {', '.join(geos or [])} · {len(findings)} findings · "
        f"LLM: {'yes' if llm_used else 'no (deterministic only)'}_",
        "",
        "> **PROPOSALS — review required. Nothing here has been applied.** "
        "Approve an item and I will implement it; every change must then pass "
        "the consistency gate + tests.",
        "",
    ]
    if brief:
        lines += ["## Scout brief (LLM-drafted, for review)", "", brief.strip(), ""]
    counts: Dict[str, int] = {}
    for f in findings:
        counts[f.kind] = counts.get(f.kind, 0) + 1
    lines += ["## Summary", ""]
    lines += [f"- **{k}**: {n}" for k, n in sorted(counts.items(),
                                                   key=lambda kv: -kv[1])]
    lines += ["", "## Findings", ""]
    for i, f in enumerate(findings, 1):
        loc = " · ".join(x for x in [f.geo, f.series] if x)
        lines.append(f"### {i}. [{f.kind}/{f.severity}] {f.title}"
                     + (f"  ({loc})" if loc else ""))
        lines += ["", f.detail]
        if f.proposal:
            lines += ["", f"**Proposed change:** {f.proposal}"]
        if f.patch:
            lines += ["", "**Draft patch (LLM, review before applying):**", "",
                      f.patch.strip()]
        if f.evidence:
            lines += ["", f"`evidence: {json.dumps(f.evidence, default=str)}`"]
        lines.append("")
    md = "\n".join(lines)
    with open(stem + ".md", "w", encoding="utf-8") as fh:
        fh.write(md)
    return stem + ".md"
