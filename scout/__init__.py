"""AGORA scout - a research/watchdog agent for the living project.

Runs on a schedule on YOUR machine (it needs your network + your local Qwen),
scans for data revisions, coverage gaps, and roadmap opportunities, and writes
**proposals** for human review. It never edits the schema, snapshots, or model.

The loop: scout drafts -> you review/approve -> implement -> consistency gate +
tests. Nothing is auto-applied.
"""
from scout.proposals import Finding, write_report
from scout.checks import coverage_findings, freshness_findings, run_all_checks
from scout.llm import QwenClient
from scout.scout import run_scout

__all__ = [
    "Finding", "write_report", "coverage_findings", "freshness_findings",
    "run_all_checks", "QwenClient", "run_scout",
]
