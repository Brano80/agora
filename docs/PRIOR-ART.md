---
title: Does this already exist? — Prior art on AI-agent economy simulation
created: 2026-06-03
note: Due diligence before building. Short answer: the pieces exist, the exact combo exists at research stage, but no accessible AI-paradigm scenario sandbox exists.
---

# Does this kind of software already exist?

**Short answer:** Yes — in pieces, and the *specific* combination (LLM agents + macro simulation, and AI/UBI scenario models) already exists **at research stage** run by heavy institutions. What does **not** exist is an accessible, calibrated, interactive *scenario sandbox for the AI/post-labor paradigm* that a non-institutional user can drive in plain language. That's the gap — and it's an accessibility/integration gap, not a "no one has thought of this" gap.

## What exists, by layer

### 1. Modeling engines (use these, don't rebuild)
- **Minsky** (Steve Keen) — free, open-source system-dynamics + **monetary** modelling with "Godley Tables" (stock-flow consistent, money-aware) and a GUI. A ready engine for the SFC core *without coding*. Strong match for your monetary questions.
- **PolicyEngine / EUROMOD** — distribution/tax-benefit (already in the plan).
- **sfctools / QuantEcon / Insight Maker / System Dynamics tools** — building blocks.

### 2. AI-agent economic simulation (this is an ACTIVE research frontier — not novel)
- **Salesforce "AI Economist"** — RL agents that earn, trade, and pay taxes in a sim; the system also *learns optimal tax policy*. Open-sourced (the "Foundation" framework). Abstract gridworld, not calibrated to a real economy; now fairly dormant.
- **EconAgent** (arXiv 2310.10436) — LLM-empowered agents with human-like behaviour for **macroeconomic** simulation. Open, research-grade.
- **EconGrowthAgent** — LLM agents simulating economic growth from decomposed growth theory.
- **Stanford Digital Economy Lab — "Economic Simulations with AI"** — actively fusing LLMs + agent-based methods + real economic measurement. This is precisely your idea, run by a top lab.
- **Bank of Japan** working paper — LLMs as economic agents in simulations.
> Note the distinction: most of this is **agents AS the economic actors inside the model**. Your diagram is mostly **agents that BUILD and operate the model** — which is "applied agentic engineering," less of a research novelty and more a tooling choice. Both are valid; only the first is a hot research area.

### 3. AI-economy / UBI / TAI scenario models (your exact subject — already being done)
- **Stanford/Benzell, "Simulating the Global Effect of Transformative AI" (2024)** — a model built to run **TAI technology + policy scenarios** and link them to economic/political outcomes. The closest academic match to your intent.
- **Ito (2026), "Feasibility of UBI in the Age of AI"** — a new model to *quantitatively* assess UBI feasibility under AI. Literally your question, done formally.
- **IMF (2026), "Global Economic and Financial Implications of AI"** — official scenario analysis (productivity, jobs, inequality, fiscal).
- **ORNL — "digital twin of the US labor market"** — a real labour-market digital twin for the automation transition.
- **PIIE (2026)** — AI futures / transformative-scenario planning.

### 4. Interactive public sandboxes (the UX target — mostly absent for this)
- **PolicyEngine** — interactive, but distribution-only, not macro/AI-paradigm.
- **en-ROADS** (climate) — the UX exemplar to copy, but it's climate, not economy.
- No turnkey "AI-economy macro sandbox" for a general user surfaced.

## The honest gap analysis
- **As research: not novel.** Stanford's Digital Economy Lab, the IMF, the BoJ, and ORNL are already deep in exactly this. You will not out-research them — don't try to.
- **As a personal thinking tool / learning project / portfolio piece: very worthwhile** — and you should **fork their open code** (AI Economist "Foundation", EconAgent, Minsky, and Benzell's/Ito's models as references) rather than build from scratch. That saves months and borrows their credibility.
- **As a product/business: hard and crowded.** A genuine but narrow gap exists on **accessibility + integration** — an en-ROADS-style, plain-language, AI-paradigm scenario sandbox for a non-expert audience. But — same pattern as every idea this session — the bottleneck isn't building it; it's **trust and distribution**. A solo-built economic model has a credibility problem the institutions don't: why would anyone believe your numbers over the IMF's?

## Recommended approach (revised by this finding)
1. **Don't build the engine.** Start by *running* existing tools: **Minsky** for the monetary/SFC core, **EconAgent / AI Economist** if you want agent-based, with **Benzell's TAI model** and **Ito's UBI model** as references/calibration targets.
2. **Your agentic crew becomes "glue + accessibility,"** not a from-scratch model — orchestrating these engines, wiring the DBnomics data layer, and turning plain-language scenarios into runs. That's the defensible, in-scope part.
3. **Reframe the goal honestly:** this is your *thinking tool and learning vehicle* (and a strong portfolio artifact showing you can orchestrate AI agents over real economic models) — not a bid to produce authoritative forecasts that compete with Stanford and the IMF.

## Next step
Worth me pulling and evaluating the most relevant open repo (AI Economist "Foundation", EconAgent, or Minsky) to judge whether **forking one** beats building Sprint 1 from scratch — likely it does for the agent-based core, while Minsky likely wins for the monetary core.
