---
title: Building the EU Macro Model with an AI-Agent Crew — Architecture & Build Plan
created: 2026-06-03
note: Ambitious but decomposable. The agents make it tractable for a solo operator; human judgment + hard accounting identities are the guardrails.
---

# Building the EU macro model with an AI-agent crew

The idea: don't hand-build a macro model, and don't trust one agent to "do economics." Instead, run a **crew of specialised agents** along two pipelines — one that *builds and validates* the model, one that *runs your scenarios* — all calling the existing tools (Eurostat, EUROMOD, sfctools…) wrapped as MCP services. You stay the economist-in-command; the agents do the labour. (See the diagram.)

## The model it produces (modular, stock-flow consistent)
A hybrid so each question hits the right engine:
- **Stock-flow-consistent (SFC) macro core** — the heart. Sectors: households (workers + AI-capital owners), firms, banks, central bank, government, sovereign fund, rest-of-world. Every flow has a source and a sink; balance sheets close. This is where money, debt, deflation, and the sovereign-fund dividend live. Built on **sfctools**.
- **Microsimulation layer (EUROMOD)** — real household distribution: who wins/loses, poverty, Gini, fiscal cost of a UBI/tax.
- **Input–output layer (FIGARO)** — production structure and sector linkages, so "AI hits sector X" propagates realistically.

## Build-time agents (construct the model)
1. **Data** — pulls and harmonises Eurostat / ECB / FIGARO / AMECO into a local DuckDB warehouse; tracks provenance.
2. **Architect** — turns economic structure into the SFC transaction-flow and balance-sheet matrices (the Godley–Lavoie tables); defines sectors and identities.
3. **Calibrate** — sets initial stocks and behavioural parameters (MPCs, shares, propensities) so the **baseline reproduces history**. This is the hard, judgement-heavy step.
4. **Codegen** — implements the model in sfctools; enforces stock-flow consistency in code.
5. **Critic** — the most important agent. Checks accounting (no money leaks — exactly the death-spiral bug we hit in v0), backtests the baseline against real data, applies sanity laws (sectoral balances sum to zero, Walras' law), and **loops failures back to Calibrate/Codegen** to self-heal.

## Run-time agents (test the scenarios)
6. **Scenario** — turns plain language ("AI lifts productivity 6%/yr, labour share → 30%, add UBI + capital tax + sovereign fund") into parameter sets and shocks.
7. **Runner** — executes parameter sweeps and Monte-Carlo runs.
8. **Analysis** — computes outcomes (GDP, Gini, debt, sectoral balances) and runs **sensitivity analysis** — which assumptions actually drive the result.
9. **Report** — charts, narrative, dashboards; loops back to Scenario for the next experiment.

## The substrate (fits your stack)
- **Orchestration:** a workflow graph (LangGraph, or **n8n** which you already use) for the deterministic DAG; Claude agents as the reasoning nodes.
- **Tools as MCP:** wrap each tool (Eurostat API, EUROMOD, sfctools, PySD, DuckDB) as an MCP server the agents call — the same MCP-first pattern from your SAIN work.
- **Shared memory:** a structured store for the model spec, parameter provenance, the assumptions log, and validation history — so every number is traceable.
- **Human gates (you):** you approve the model spec, sign off the calibration targets, define/greenlight scenarios, and interpret results. Agents draft; you decide.

## The honest risks (read these)
- **Garbage calibration → confident nonsense.** The danger isn't that agents can't write code; it's that they produce a plausible model that's quietly wrong. The **Critic agent + hard accounting identities + your judgment** are the only things standing between you and confidently-wrong charts. Budget most effort here.
- **Calibration is genuinely hard** and partly an art; expect this to be where the time goes, not codegen.
- **It's still a sandbox, not an oracle** (from the scope doc) — agents make building faster, not the economics more predictive.
- **Agent sprawl:** start with few agents doing real work, not a flowchart of 9 from day one.

## Phased build (thin vertical slice first)
- **Sprint 1 — Spine:** one country (Germany), SFC core in sfctools, Data agent + Eurostat calibration of ~10–15 series, Critic checking the books, one scenario (baseline vs AI-no-policy vs Abundance Settlement). Prove the loop end-to-end. *(Today's `econ_sim_v0` is the pre-cursor — replace its toy parameters with calibrated ones.)*
- **Sprint 2 — Rigour:** bolt on EUROMOD via the microsim agent for real distribution numbers; add the sovereign fund + Universal Basic Compute as explicit sectors.
- **Sprint 3 — Breadth:** FIGARO input–output, multi-country, sensitivity/Monte-Carlo, a scenario dashboard.
- **Sprint 4 — Crew:** formalise the full agent pipeline in n8n/LangGraph with MCP-wrapped tools and the memory layer, so you can describe a scenario in words and get a validated run back.

## Recommended next step
Build **Sprint 1** — I wire the Data agent (Eurostat API) into a calibrated single-country SFC core and stand up the Critic's accounting checks, turning today's toy into a trustworthy baseline. Everything else hangs off that spine.
