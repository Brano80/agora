# Phase 4 — Multi-objective policy search & the trade-off frontier

**The principle (CLAUDE.md, non-negotiable):** there is *no single best* policy.
AGORA reports the multi-objective trade-off and leaves the values judgement to
the user. Phase 4 operationalises that: it sweeps the policy space against a
fixed AI shock, runs every candidate through the **full module chain + the
consistency gate**, scores five objectives, and returns the **Pareto frontier** —
the set of policies that no other policy beats on every axis at once.

## What it does

- **Decision space** (`policy_search.search_policies`): policy *form* ∈
  {no policy, cash UBI, Universal Basic Capital} × capital-levy intensity
  `τ ∈ {0.1 … 0.6}` (the shock is held fixed, so the question is "given the AI
  transition, which policy *mix* is on the frontier?").
- **Five objectives**, each expressed so higher = better for clean dominance:
  growth (end GDP), equality (−Gini), stability (−volatility of YoY GDP growth),
  fiscal (−debt/GDP), resilience (−poverty rate).
- **Every candidate is gated.** A policy point only enters the ranking if its run
  passes the consistency gate — the frontier can never be built on leaky books.
- **Pareto dominance** (`_dominates` / `pareto_front`): A dominates B iff A ≥ B on
  every objective and strictly > on at least one. The frontier is the
  non-dominated set.
- Exposed as `AgoraOrchestrator.run_policy_search(taus=None, horizon=30)`; the
  dashboard renders the frontier (equality-vs-growth and equality-vs-stability
  scatters + a Pareto table).

## Result (DE, 2019, 30-year horizon)

13 policies evaluated, **all consistency-gated** (worst residual ~1e-4 MEUR),
**8 on the frontier**. Highlights:

| Policy | GDP end | Gini | Growth vol | Debt/GDP | Poverty | On frontier |
|---|---:|---:|---:|---:|---:|:--:|
| No policy | 13.1M | 0.466 | 0.010 | 99.6 | 0.281 | — (dominated) |
| Cash UBI τ=30% | 18.9M | 0.362 | **0.002** | 89.7 | 0.221 | ★ |
| Cash UBI τ=50% | 26.3M | 0.287 | 0.010 | 81.7 | 0.163 | ★ |
| Cash UBI τ=60% | 32.5M | 0.245 | 0.013 | 77.1 | 0.123 | ★ |
| UBC τ=20% | 22.2M | 0.211 | 0.015 | 76.1 | 0.089 | ★ |
| UBC τ=40% | 83.9M | **0.050** | 0.046 | **41.3** | **0.000** | ★ |
| UBC τ=60% | 108.0M | 0.050 | 0.037 | 46.3 | 0.000 | ★ |

**What the frontier says.** Doing nothing is **dominated** — some policy beats it
on every axis. The frontier then splits along a real trade-off: **UBC** points win
on growth, equality, fiscal, and resilience (near-zero Gini, zero poverty, the
smallest debt), but at the cost of a **bumpier** growth path; **cash UBI** points
earn their place by being the *smoothest* (growth volatility down to ~0.002). So
the model does not crown a winner — it hands you the menu: if you weight stability
highest, a cash UBI is on your frontier; if you weight equality / resilience /
growth, UBC is. The choice is yours, and it is explicit.

(The UBC GDP levels are large because the dividend keeps demand high as it
compounds; magnitudes are nominal over 30 years — the *ranking* is what the
frontier uses. Growth volatility is higher for UBC because the dividend
accelerates with `φ`; that bumpiness is exactly why cash UBI survives on the
frontier.)

## Honest caveats

- **Policy-only search.** The AI shock and the structural elasticities (β, γ, the
  C1 investment elasticity ε) are held fixed. The frontier is conditional on
  them — change an assumption in the sidebar and the frontier moves. That is the
  point: it is a sandbox for *exploring* trade-offs, not an optimiser that claims
  a globally best policy.
- **The objectives are choices too.** "Resilience = −poverty" and "stability =
  −growth volatility" are defensible but not unique operationalisations; they are
  inspectable and swappable in `policy_search.OBJECTIVES`.
- **Coarse grid.** Seven τ values × three forms. Finer grids or extra levers
  (UBC reinvestment, targeted sectoral taxes) are easy follow-ups and would just
  add points to the same frontier machinery.

## How to run it

```python
from orchestrator import AgoraOrchestrator
o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True)
o.load_data()
points = o.run_policy_search(horizon=30)          # every point gated
frontier = [p for p in points if p.on_frontier]
```

Module: `policy_search.py`. Tests: `tests/test_policy_search.py` (gate, dominance
logic, "no single best" spans both forms, dominated points covered). Dashboard:
the "Policy search — the trade-off frontier" section.

---

## 2026-06-12 re-run — the frontier under the hardened model

An honest correction to the original headline: after the fiscal fix (F9),
the poverty floor (F10) and the inventories identity closure, the DE frontier
no longer spans both policy forms. Re-running the same 13-point grid:

**4 of 13 points are non-dominated, and all four are UBC intensities
(tau = 20/30/40/50%).** Cash UBI is now dominated at every tau: once the books
are realistic, UBC matches or beats it on equality, resilience (its dividend
clears the poverty line; cash never does), growth and fiscal, leaving cash no
axis to win. "No single best" survives WITHIN the UBC family — the tau choice
still trades immediate dividend against fund growth — but the FORM question now
has a model answer rather than a frontier spread. (Earlier "frontier spans both
forms" tables reflect the pre-F9/F10 books; superseded.) The coarse-grid caveat
stands: extra levers (reinvest rate, sectoral taxes) may re-open the form
trade-off; that is the planned finer search.
