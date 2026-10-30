# AGORA — a sandbox for the economics of abundance

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20726928.svg)](https://doi.org/10.5281/zenodo.20726928)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-green.svg)](https://creativecommons.org/licenses/by/4.0/)
![tests](https://img.shields.io/badge/tests-241%20passing-brightgreen)
![status](https://img.shields.io/badge/status-research%20preview-orange)

**AGORA** is an open, **stock-flow-consistent** model of the European economy built
to answer one question rigorously: *as AI raises productivity, who gets the gains —
and which policies actually share them?* It compares policies (cash UBI vs
**Universal Basic Capital**) inside one accounting-complete world, calibrated to
live data and validated against history.

> **Sandbox, not oracle.** AGORA produces *scenario comparisons under explicit,
> swappable assumptions* — not forecasts. Every parameter is inspectable and
> sourced; every scenario must pass a consistency gate (no money created or lost
> in the accounts) before any result is reported.

> ⚠️ **Known issues: headline results under revision (2026-10-28).** A review found
> that several headline numbers below come from runs that pass the accounting gate but
> are not economically plausible. Until the fixes in [`docs/PHASE7.md`](docs/PHASE7.md)
> land, treat the headline results, frontier charts, study PDF and dashboard as
> **provisional**:
> 1. **No supply side.** Output is purely demand-led, with no capacity limit or price
>    level, so redistribution raises GDP mechanically. The growth claims below ("the UBC
>    economy ends larger", "predistribution needn't cost growth") follow from this
>    closure; they are not findings.
>    *Fixed in the engine on 2026-10-29 (Phase 7 step C,
>    [`docs/AUDIT-2026-10-stepC.md`](docs/AUDIT-2026-10-stepC.md)): real output is now
>    capped by capacity, with prices. Over 30 years cash UBI is roughly neutral for real
>    output and UBC depends on whether the fund reinvests; the numbers above are not yet
>    regenerated.*
> 2. **Unconstrained investment financing.** Investment follows an assumed path, and
>    capital owners finance it with unlimited interest-free borrowing from the state.
>    Their money balance goes negative in over half the policy runs, cash UBI and UBC
>    alike, and in about a third of UBC runs they end insolvent, owing more than they own.
>    *Fixed in the engine on 2026-10-29 (Phase 7 step B,
>    [`docs/AUDIT-2026-10-stepB.md`](docs/AUDIT-2026-10-stepB.md)); the published
>    numbers above still come from the old engine until they are regenerated.*
> 3. **No foreign ownership of capital.** All capital, AI capital included, is modelled
>    as domestically owned, so the model cannot yet say how much of a largely
>    foreign-owned AI rent European policies can reach.
>    *Fixed in the engine on 2026-10-30 (Phase 7 step D,
>    [`docs/AUDIT-2026-10-stepD.md`](docs/AUDIT-2026-10-stepD.md)): foreign owners hold
>    their observed share of capital and 70% of the AI rent is paid abroad. Taxes on
>    domestic capital and dilution reach none of that foreign part; a source levy
>    reaches little, because providers pass it on. The numbers above are not yet
>    regenerated.*
>
> An audit of the 3,057 scenario runs behind the published numbers finds that every one
> balances its books, but only 13% also pass the new plausibility checks:
> [`docs/AUDIT-2026-10.md`](docs/AUDIT-2026-10.md).
>
> What stands: the accounting framework, the live EU data pipeline and the consistency
> gate. Whether "ownership beats cash" survives the fixes is open. Corrections will ship
> as a new versioned release.

📄 **Read the study:** *Owning the Machine — A Governance of Abundance for Europe* (12 pp) → [`AGORA_Manifesto.pdf`](AGORA_Manifesto.pdf) · permanent copy: https://doi.org/10.5281/zenodo.20726928 · SSRN: (forthcoming)
📋 **One-page policy brief:** [`AGORA_Policy_Brief_UBC.pdf`](AGORA_Policy_Brief_UBC.pdf) — practical paths to implement UBC and where the capital comes from.
🔗 **Live dashboard:** https://brano80.github.io/agora/

---

## The headline result *(provisional, see Known issues above)*
![Only ownership touches wealth](social_1_wealth.png)

Under an AI labour-share shock (Germany, 30-year scenario):
- **Cash UBI** lowers income inequality but leaves the **top-10% wealth share ~56%** — it redistributes the income capital throws off, never the capital.
- **Universal Basic Capital** (a citizens' fund paying a per-capita dividend) collapses it to **~20%** — it distributes the asset itself.
- With fund **reinvestment**, the UBC economy ends *larger* than the cash economy — predistribution needn't cost growth. *(Artifact of the demand-led closure; under revision.)*
- A **pooled EU dividend** roughly **halves** between-country inequality.
- Across a multi-objective frontier, **UBC policies dominate** both cash UBI and inaction. *(Holds only with investment held fixed; with investment responding, cash re-enters the frontier: finding F23.)*

![UBC owns the policy frontier — equality and growth together (Germany, France, Slovakia)](AGORA_frontier_DE_FR_SK.png)

*At equal cost, Universal Basic Capital is non-dominated across all five objectives (growth, equality, poverty, fiscal sustainability, stability); cash UBI and “do nothing” are dominated everywhere. Per-country charts: [DE](AGORA_frontier_DE.png).*

## How it's built
- **Stock-flow-consistent core** + pluggable modules (distribution · input-output · AI-shock · citizens' fund · multi-region) through a common schema.
- **Live data:** Eurostat national accounts, AMECO wage shares, BIS household debt, OECD wealth distribution, Eurostat **FIGARO** input-output — integrated via DBnomics; 26 EU members calibrated.
- **Validated:** back-tested to 2010–2019 history (~2.3% mean GDP error; government-debt path within the 10% bound); a consistency gate enforced on every run (residuals ~1e-10 of GDP); **241 automated tests**.
- Pure standard-library Python engine.

## Drive it in plain language (MCP + agent crew)

AGORA runs as an **MCP server**, so any AI assistant — Claude Desktop, Claude Code,
VS Code — can drive the model directly, and a small **agent crew** turns a
plain-language request into a gated, reported run. Ask in words:

> *"Compare cash UBI vs UBC under an AI shock in Slovakia"*
> *"What's the policy trade-off frontier for Germany?"*
> *"Run an AI shock with UBC at 40% in France"*

The crew plans the request, resolves the assumptions for your approval, runs it
through the consistency gate, and reports the result — a single scenario, a
comparison, or the Pareto frontier — always with the numbers and **never a
"winner"** (the values judgement stays with you). It runs offline with no LLM:

```bash
python agent_crew.py "What's the policy frontier for Germany under an AI shock?"
```
```
AGORA crew -- policy frontier on DE (30y). 4 non-dominated policies out of 13;
no single 'best' -- each trades one objective for another.
  - UBC t=20%: GDP 9,382,116, Gini 0.250, poverty 0.090, debt/GDP 143.
  - UBC t=30%: GDP 10,496,531, Gini 0.193, poverty 0.016, debt/GDP 136.
  - UBC t=40%: GDP 12,414,605, Gini 0.119, poverty 0.000, debt/GDP 125.
  - UBC t=50%: GDP 14,699,402, Gini 0.056, poverty 0.000, debt/GDP 118.
  Sandbox, not a forecast; every candidate passed the consistency gate.
```

**Why it's trustworthy as a tool** — the guardrails live in the tool layer, not
the wrapper: every result passes the stock-flow consistency gate before it
leaves (a failing scenario returns the failing checks and *no numbers*, with no
switch to disable it); every payload carries its assumptions and data provenance;
the comparison tools have no "winner" field; and AGORA bundles **no model of its
own** — optional narration borrows the client's model via MCP sampling.

10 read-only MCP tools (`agora_run_scenario`, `agora_compare`,
`agora_policy_frontier`, `agora_preview_scenario`, `agora_narrate`, `agora_crew`,
…). Connect it:
```bash
pip install "mcp[cli]"
# then add mcp_server.py to claude_desktop_config.json (see docs/MCP.md)
```
Full tool list + setup: [`docs/MCP.md`](docs/MCP.md) · crew design: [`docs/PHASE5.md`](docs/PHASE5.md).

## Quickstart
```bash
python -m pytest tests/ -q              # run the test suite (241)
python -m streamlit run dashboard/app.py # explore scenarios
python scripts/run_triad.py --geo DE     # baseline / AI-shift / settlement
```

## Repository map
- `schema/` canonical SNA accounts · `modules/` model adapters · `consistency/` the gate
- `data/` live connectors + cached snapshots · `orchestrator.py` · `scenarios.py`
- `docs/` architecture, manifesto, findings · `tests/`

## Citation
```bibtex
@misc{agora2026,
  title  = {Owning the Machine: A Governance of Abundance for Europe},
  author = {Branislav Ambroz},
  year   = {2026},
  note   = {AGORA — an open, consistency-gated model of AI's distributional impact},
  doi    = {10.5281/zenodo.20726928},
  url    = {https://doi.org/10.5281/zenodo.20726928}
}
```

## License
Code & documents: **CC BY 4.0** (attribution). See `LICENSE`.

---
*AGORA is a research preview. It is a tool for comparing policies transparently — not investment, legal, or policy advice.*
