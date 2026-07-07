# Phase 5 — the run-time agent crew (increment 1)

`agent_crew.py` turns a plain-language request into a gated, reported run by
threading the run-time pipeline from `docs/AGENTIC-BUILD-PLAN.md`:

```
Scenario(plan) -> approve(elicitation) -> Runner -> Critic(gate) -> Report
```

Every stage calls the same guarded tool layer (`mcp_api`) the MCP server
exposes, so nothing bypasses the consistency gate (the **Critic** is
non-negotiable) and the sandbox/provenance guardrails travel with every result.

## Design
- **Deterministic by default, offline, testable.** A rule-based planner
  (`plan()`) and a template reporter (`template_report()`) — no LLM needed to run
  the loop. Both are **pluggable**: pass `planner=` / `reporter=` to swap in an
  LLM (the client's model via MCP sampling, or the local Qwen the scout uses).
  No bundled model.
- **Human gate (elicitation).** For single scenarios the crew previews the
  resolved assumptions (via `agora_preview_scenario`) and calls `approver(preview)
  -> bool` BEFORE compute; a veto stops the run with nothing computed. Default is
  auto-approve, but the hook is where "the values judgement stays with the user"
  lives.
- **No 'winner'.** Comparison reports list the trade-offs across arms and
  explicitly decline to crown one.
- **Traceable transcript.** `CrewResult` records the plan, the assumptions shown
  for approval, the gate outcome, the ordered stage log, and the full payload.

## The planner (rule-based NL -> levers)
Recognises a country (name or 2-letter code; default DE), an AI shock
("AI shock/shift/automation"), a policy form (UBC / cash UBI), a tax rate
("40%", "tau 0.4"), fund reinvestment ("reinvest 50%"), and comparison intent
("compare", " vs ", "ubc vs cash", "triad"). Unknown phrasing degrades to the
no-shock baseline for the detected country.

## Use
```
python agent_crew.py "Run an AI shock with UBC at 40% in Germany"
python agent_crew.py "Compare cash UBI vs UBC under an AI shock in Slovakia"
```
Programmatic:
```python
from agent_crew import run_crew
res = run_crew("triad for France", approver=my_human_gate)   # -> CrewResult
print(res.report)
```

## Scope / next increments
- Increment 1 (this): Scenario + approve + Runner + Critic + Report, deterministic.
- Next: LLM planner/reporter via MCP sampling; wire the **scout** and the
  **Phase-4 optimiser** in as crew tools (the plan already treats them as
  callable stages); optional LangGraph/n8n DAG for the deterministic wiring.
