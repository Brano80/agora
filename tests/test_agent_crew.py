"""Phase 5 -- the run-time agent crew over the gated tool layer.

Pins: the planner maps language to the right levers; the crew always runs
through the consistency gate; the human-approval gate can veto BEFORE compute;
comparisons never declare a 'winner'; the transcript is traceable.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_crew as crew


# ---- planner (deterministic NL -> levers) --------------------------------- #
def test_plan_single_ubc_with_shock_and_tau():
    p = crew.plan("Run an AI shock with UBC at 40% in Germany")
    assert p.geo == "DE" and p.mode == "single"
    assert p.levers.get("ubc") is True
    assert abs(p.levers.get("capital_tax") - 0.40) < 1e-9
    assert p.levers.get("labour_share_end") == 0.30      # AI shock recognised


def test_plan_compare_pinned_experiment():
    p = crew.plan("compare cash UBI vs UBC under an AI shock in Slovakia")
    assert p.geo == "SK" and p.mode == "compare" and p.preset == "ubc"


def test_plan_triad_and_country_code():
    p = crew.plan("show me the triad for FR")
    assert p.geo == "FR" and p.mode == "compare" and p.preset == "triad"


def test_plan_defaults_to_baseline_de():
    p = crew.plan("what happens normally")
    assert p.geo == "DE" and p.mode == "single" and not p.levers


# ---- the crew loop -------------------------------------------------------- #
def test_crew_runs_through_the_gate():
    r = crew.run_crew("AI shock with UBC at 40% in Germany", horizon=10)
    assert r.gate_passed is True
    assert "critic: gate PASSED" in r.stages
    assert "Gate passed" in r.report and r.plan["geo"] == "DE"
    # traceable transcript: every stage recorded, in order
    assert r.stages[0].startswith("scenario:")
    assert any(s.startswith("runner:") for s in r.stages)


def test_human_approval_gate_can_veto_before_compute():
    seen = {}

    def deny(preview):
        seen["assumptions"] = preview.get("assumptions")
        return False

    r = crew.run_crew("AI shock with UBC at 40% in Germany",
                      approver=deny, horizon=10)
    assert r.approved is False
    assert r.payload.get("declined") is True          # nothing computed
    assert "gate" not in r.payload and "series" not in r.payload
    assert seen["assumptions"] is not None            # human saw the levers first
    assert "DECLINED" in r.stages[-1]


def test_compare_report_declares_no_winner():
    r = crew.run_crew("compare cash UBI vs UBC in Slovakia", horizon=10)
    assert r.gate_passed is True
    assert "No single 'winner'" in r.report
    assert r.report.count(" - ") >= 3                 # each arm listed


def test_reporter_hook_is_pluggable():
    r = crew.run_crew("UBC at 40% in Germany", horizon=8,
                      reporter=lambda payload: "CUSTOM:" + payload["geo"])
    assert r.report == "CUSTOM:DE"


def test_refusal_payload_reads_as_refused():
    txt = crew.template_report({"geo": "XX", "error": "Unknown geo 'XX'."})
    assert "REFUSED" in txt and "XX" in txt


def test_plan_frontier_intent():
    assert crew.plan("optimise policy in France").mode == "frontier"
    assert crew.plan("which policy is best for SK").mode == "frontier"
    assert crew.plan("show me the trade-off frontier for Germany").mode == "frontier"


def test_crew_frontier_mode_returns_a_menu():
    r = crew.run_crew("what is the policy frontier for Germany", horizon=10)
    assert r.plan["mode"] == "frontier" and r.gate_passed is True
    assert "non-dominated" in r.report and "no single 'best'" in r.report
    assert r.payload.get("n_frontier", 0) >= 2
    assert r.payload.get("n_gated_out") == 0
