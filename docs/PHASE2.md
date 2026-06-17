# AGORA — Phase 2 (in progress)

Phase 2 adds the **distribution module** (real winners/losers) + the AI-shock
driver + a side-by-side comparison view. This document covers the first
increment: the distribution module, shipped and gated.

## Distribution module — the personal income layer
`modules/distribution.py`. Loose coupling exactly as the docs prescribe: the
SFC core sets the macro aggregates, the distribution module distributes them.

It reads the SFC core's per-period **net wages / net profits / disposable
income** (via the run `context`) and turns them into a 10-decile personal
distribution. Mechanism (reduced-form, transparent, anchored):

```
G_t = G0 + β·(capital_share_t − capital_share_0) − γ·ubi_intensity_t
```
- **G0** = the country's observed disposable-income Gini → year-0 reproduces
  reality by construction.
- **β** (default 0.6): how strongly a rising household capital share concentrates
  income at the top — the decoupling channel.
- **γ** (default 0.5): how strongly a per-capita UBI compresses the distribution.
- Given `G_t`, income is modelled as lognormal; decile shares, the
  at-risk-of-poverty rate (< 60% of median), the Palma and S80/S20 ratios follow.

β and γ are **inspectable, swappable assumptions** (sidebar sliders), to be
grounded empirically later (a job for the scout). The module reports
`gini_personal`, `poverty_rate`, `palma_ratio`, `s80s20_ratio`, decile incomes
and shares, the household capital share and UBI intensity.

## Reconciliation gate (extends the consistency check)
`consistency.check_distribution`: every period, **Σ decile incomes == macro
household disposable income**, and **decile shares sum to 1**. This is the
"reconcile through the schema" law applied to a downstream decomposition — the
distribution module cannot invent or lose money relative to the macro core. The
orchestrator runs it automatically and it gates every run.

## Orchestration (loose coupling, in sequence)
`orchestrator.py` now runs the active modules in order, passing each a `context`
of the results produced so far: `SFC core → distribution`. The generic TFM/BSM
gate runs on the SFC result; the reconciliation check runs on the distribution
result. `ScenarioRun` stays backward-compatible (`.result` = the macro result,
`.dist` = the distribution result).

## Result (illustrative, DE, final year — not a forecast)
| Scenario | Personal Gini | Poverty | Palma | Top 10% | Bottom 40% |
|---|---|---|---|---|---|
| Baseline | 0.297 | 17% | 1.07 | 23% | 21% |
| AI, no policy | 0.47 | 28% | 2.7 | 34% | 13% |
| AI + Abundance Settlement | 0.33 | 20% | 1.2 | 25% | 20% |

The decoupling is now visible at the household level: without policy, the top
decile's share jumps and the bottom 40%'s collapses; the settlement contains
both. The baseline poverty rate (~17%) emerges close to Germany's actual
at-risk-of-poverty figure without being fitted. France behaves the same way.

## Run it
```bash
python -m pytest tests/ -q            # full suite incl. distribution + reconcile
python -m streamlit run dashboard/app.py
```
The dashboard now has a **"Distribution — who wins & loses"** section: personal
Gini / poverty / Palma trajectories, a final-year decile-share chart, and a
per-decile **Settlement vs No-policy** winners/losers bar.

## Honest limitations (this increment)
- The distribution is **reduced-form** (a lognormal whose Gini moves with the
  capital share and UBI), not a household microsimulation. A PolicyEngine/
  EUROMOD adapter can replace it behind the same interface — schema, gate, and
  dashboard unchanged.
- `gini_personal` is the modelled Gini anchored at the observed value; β, γ are
  assumptions, not yet empirically estimated.
- Still a closed economy (rest-of-world is Phase 3).

## Next in Phase 2
- **AI-shock driver** — an explicit module turning AI/automation parameters
  (productivity, automation exposure, compute) into the scenario shocks, grounded
  in Epoch / AI Index / ILO figures.
- **Scenario builder + side-by-side comparison view** in the dashboard.

---

## Phase 2 complete — AI-shock driver + scenario builder + comparison view

**AI-shock driver** (`modules/ai_shock.py`). The principled layer that turns
interpretable AI/automation parameters into the SFC core's scenario levers, so
the shock is named and sourced rather than hand-coded:
  * `AIShock(labour_share_end, capex_growth, adoption)` — the AI shock enters
    via the labour-share trajectory (automation displaces labour; `ramp` or
    `scurve` adoption) and the AI-capex injection growth (the buildout boom).
  * `Policy(capital_tax, ubi)` — the response levers.
  * `to_scenario(p, ai, policy)` composes them into a `Scenario`.
Anchors are documented (ILO/Karabarbounis-Neiman for labour-share decline;
Stanford AI Index / Epoch for AI investment & compute) and flagged as swappable
assumptions, not forecasts. `scenarios.make_triad` now builds the triad through
the driver (single source of truth), and `scenarios.build_custom(...)` builds a
bespoke scenario.

**Scenario builder + comparison view** (dashboard). A "build your own scenario"
panel (labour-share target or hold, adoption path, capex growth, capital tax,
UBI) adds a live **Custom** scenario alongside the triad. A scenario multiselect
drives a **side-by-side comparison**: overlaid macro + distribution charts, a
final-year decile-share chart, a metrics table, and a **Δ-vs-Baseline** table.

**Verification:** 32 tests pass (added AI-shock driver tests: labour-share path
construction, exact S-curve endpoints, a custom scenario through the full gate).
Dashboard renders for DE and FR with the comparison view and custom scenario.

## Phase 2 status: COMPLETE
- ✅ Distribution module (deciles, poverty, Palma) + reconciliation gate
- ✅ AI-shock driver (named, sourced shock parameters → scenario levers)
- ✅ Scenario builder + side-by-side comparison view

## Next (Phase 3, per the roadmap)
FIGARO input-output module; more connectors (BIS debt stocks, WID wealth, Epoch
compute) via the scout backlog; the rest-of-world sector (open economy); and
consistency reconciliation across tightly-coupled modules.
