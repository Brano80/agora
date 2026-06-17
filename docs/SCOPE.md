---
title: Simulating the Economy to Test AI-Paradigm Scenarios — Feasibility & Best Path
created: 2026-06-03
note: A scenario sandbox is achievable solo. A predictive model of Europe is not. Read the framing first.
---

# Can we simulate the economy and test these scenarios? Yes — within limits. Here's the best way.

## Proof it's possible
`econ_sim_v0.py` already runs (see `econ_sim_v0.png`). It's a minimal, **illustrative** demand-multiplier model with two income classes and policy toggles. With invented parameters it reproduces your exact thesis:

| Scenario | Output (GDP) | Household consumption | Inequality (Gini) | Worker / Owner income |
|---|---|---|---|---|
| Baseline (no AI shift) | 193 | 147 | 0.20 | 1.45 / 3.86 |
| **AI shift, NO policy** | 321 | 198 | **0.50** | **1.20** / 11.23 |
| **AI shift + Abundance Settlement** | **426** | **303** | 0.28 | 2.79 / 10.15 |

The "no policy" path shows the decoupling precisely: **GDP rises (investment boom) while workers' incomes fall below baseline and inequality explodes.** Redistribution (capital tax → UBI) sustains demand, so output is *highest* and inequality contained. *(Caveat: illustrative only — this shows a mechanism, not a forecast, and the "redistribution raises GDP" result depends on the demand-led closure + spending assumptions.)*

## Three honest reframes (read before going further)
1. **It's a scenario sandbox, not an oracle.** No model predicts the macroeconomy reliably — central banks' billion-dollar models miss. The value is *comparing policies and stress-testing logic* in an internally consistent world, not forecasting 2035. Treat outputs as "if these assumptions hold, this is the direction," never as truth.
2. **Your GPU is irrelevant here; this isn't an ML problem.** These models are CPU/RAM-bound, and even then tiny. Your 128 GB RAM is overkill-plenty. The binding constraints are *modeling method, data wrangling, and interpretation* — not compute.
3. **"Feed as much data as possible" has steep diminishing returns.** A simplified model with a few dozen well-chosen, calibrated parameters beats a data dump. The skill is choosing the right structure, not maximizing data volume. Feed *enough to calibrate*, not everything.

## Don't build from scratch — stand on existing tools

**For distribution scenarios (UBI / capital tax / LVT on real households):**
- **EUROMOD** — the EU gold standard. Static tax-benefit microsimulation across all EU countries on harmonised microdata; free software from the JRC (microdata via an EU-SILC access request). Best for rigorous poverty/Gini/budget/winners-losers by country.
- **PolicyEngine** — free, open-source, lovely UX + Python API; strongest for US/UK, EU coverage growing. Great for fast UBI/tax-reform what-ifs.
- **OpenFisca** — "rules-as-code" engine powering several national models.

**For the structural / monetary paradigm (what microsim can't do):**
- **sfctools** (PyPI) — lightweight Python framework for **agent-based + stock-flow-consistent** macro models. The right tool to grow `econ_sim` into something monetarily coherent (tracks money, debt, sectoral balances).
- **macrosimulation.org** — ready-to-run SFC + ABM teaching models (great to learn from / fork).
- **PySD** — run system-dynamics (Vensim/XMILE) models in Python (good for aggregate "Limits to Growth"-style scenario storytelling).
- **Eurace** — a real agent-based simulator of the European economy. Research-grade and heavy; reference, not a starting point.

**Data (Europe), all free unless noted:**
- **Eurostat dissemination API** (national accounts, labour share, income, prices) — the workhorse.
- **FIGARO** EU inter-country input-output tables (economy structure / sector linkages).
- **ECB Statistical Data Warehouse**, **AMECO**, **OECD** (macro/financial series).
- **EU-SILC** household income microdata — needed for microsim; access-controlled (research request).

## Recommended path (Europe-first, tiered)
**Track A — Distribution, rigorous, mostly off-the-shelf.** Use EUROMOD (or PolicyEngine where EU is covered) to test "UBI funded by a capital/robot tax or LVT" on real EU households → hard numbers on poverty, Gini, fiscal cost, who wins/loses, per country. This *is* the redistribution pillar of the Abundance Settlement, already built.

**Track B — Paradigm sandbox, custom, what we started today.** Grow `econ_sim_v0` into a calibrated **stock-flow-consistent** model (via `sfctools`) with sectors: workers, AI-capital owners, firms, banks/central bank, government, sovereign fund — plus levers for AI productivity, falling labour share, price deflation, UBI, **Universal Basic Compute**, capital/robot tax, LVT, and sovereign-fund dividends. Calibrate to Eurostat aggregates for the EU (or start with Germany), ~10–30 variables. This answers the monetary/structural questions microsim can't.

**Track C — Optional later.** An agent-based version (sfctools/Mesa) for *emergent* inequality dynamics as labour share → 0. Most flexible, hardest to calibrate; your RAM helps.

**Sequence:** Track B is the heart (it directly tests your scenarios end-to-end and we've already begun it); bolt on Track A for credible distribution figures; add C only if useful.

## What's genuinely in *your* scope
- A working, calibrated, EU-aggregate **scenario sandbox** comparing baseline vs AI-no-policy vs Abundance-Settlement (and variants) — yes, very doable, weeks not years, mostly my coding + your direction.
- Rigorous **distribution analysis** via EUROMOD/PolicyEngine — yes.
- A **predictive model of the European economy** — no. That's a research-consortium effort (Eurace took years); anyone claiming a solo build of that is selling something.

## Next step (pick one)
1. **Calibrate the sandbox with real data** — I wire the Eurostat API into `econ_sim` (EU or Germany: GDP, labour share, income distribution, prices) so the baseline matches reality before we run scenarios. *(Recommended — turns the toy into something trustworthy.)*
2. **Stand up EUROMOD/PolicyEngine** — get rigorous UBI/tax distribution numbers for a chosen country.
3. **Deepen the model first** — add money/debt, a sovereign fund, and Universal Basic Compute as explicit sectors (move to `sfctools`) before calibrating.
