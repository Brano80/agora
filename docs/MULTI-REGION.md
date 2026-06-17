# Multi-region core — the national-vs-global AI dividend (MANIFESTO Q2)

**The question (Q2, raised by Brano).** "For a truly working UBI from AI it needs
to be *universal* — the whole world — otherwise the benefits are again
distributed to the richest countries, widening the gap even further." Does the
sandbox bear that out? If the AI dividend is paid only *nationally*, the richer,
more capital-intensive economy throws off a bigger per-capita dividend, so an
"AI UBI/UBC" entrenches the gap *between* countries. A *global* (pooled) dividend
spreads the combined levy equally per head, transferring from richer to poorer.

## Design (loose coupling, per CLAUDE.md)

Each country is its own calibrated, **individually consistency-gated** open
economy (`AgoraOrchestrator` for DE and FR). The region layer (`region.py`) runs
them under the *same* AI shock + policy and reconciles only at the
dividend-distribution step:

- **National** — each country's levy `τ·FP` funds a dividend for *its own*
  citizens only.
- **Global** — the countries' levies are pooled and paid out equally per capita
  across the *combined* population.

Everything else is held identical, so the change isolates the national-vs-global
effect. Between-country inequality is the population-weighted Gini *across*
regions of per-capita household disposable income. (This increment does **not**
yet force tight bilateral trade feedback — rest-of-world stays each country's
single counterparty; tight DE↔FR trade coupling is the next increment.)

## Result (DE + FR, 2019, τ=40%, 30-year horizon; both gate-clean)

**Cash UBI — the clean illustration of Q2:**

| Year | National between-country Gini | Global (pooled) | 
|---:|---:|---:|
| 2019 | 0.0192 | 0.0149 |
| 2039 | 0.0335 | 0.0227 |
| 2048 | **0.0478** | **0.0314** |

Under the AI shock a purely **national** cash dividend lets the between-country
gap *grow* (0.019 → 0.048) — the richer economy (DE) generates the bigger
dividend. **Pooling it globally narrows the gap ~34%** (to 0.031) and transfers
per-capita income from DE (−) to FR (+). That is Q2, confirmed: a national AI
dividend entrenches the cross-country gap; a pooled one shrinks it.

**UBC — a twist worth noting:** full socialisation drives each country's
per-capita dividend toward its whole capital-income share, and the two converge
on their own, so the *national* between-country gap actually shrinks over the
horizon (0.027 → 0.0095); pooling still trims a further ~33%. Predistribution is
partially self-equalising across countries; redistribution (cash) is not.

## Honest caveat (and the next increment)

DE and FR are **both rich** European economies, so the between-country gap here
is small (Gini ~0.01–0.05) relative to *within*-country inequality. The
*mechanism* is demonstrated, but its *magnitude* understates the real Q2 force —
which is about rich vs poor countries globally. Adding a lower-income region
(EA20 is calibratable; a non-European low-income economy would be the real test)
would amplify the national-vs-global divergence sharply. That, plus **tight
bilateral trade feedback** (one country's exports = another's imports, fed back
into demand), is the next multi-region increment. Until then, read the direction
as robust and the magnitude as a lower bound.

## How to run it

```python
from region import MultiRegion
mr = MultiRegion(geos=("DE", "FR"), year=2019, allow_live=False)
cmp = mr.dividend_comparison(form="cash_ubi", tau=0.40, horizon=30)  # or form="ubc"
cmp.summary()   # gini_national_end, gini_global_end, gap_narrowing_pct, ...
```

Module: `region.py`. Tests: `tests/test_region.py` (each country gated; pooling
is redistributive and conserves the total; pooling narrows the gap; national cash
dividend widens it). Dashboard: the "National vs global AI dividend" section.

---

## Increment 2 — a low-income region, and tight bilateral trade (2026-06-07)

### A poorer region is where Q2 gets its magnitude

DE+FR alone are both rich, so the gap was small. Adding **Poland** (a sourced
2019 snapshot, ~€14k GDP/capita vs DE ~€43k, FR ~€36k — `data/cache/pl_baseline_2019.json`)
makes the point land. `MultiRegion` is N-country from the start, so it is just a
longer `geos` tuple; Poland calibrates and gates clean (residual ~3.6e-6).

| Bloc | National between-country Gini (end) | Global (pooled) | 
|---|---:|---:|
| DE + FR | 0.048 | 0.031 |
| DE + FR + **PL** | **0.138** | 0.092 |

Adding the poorer country **nearly triples** the between-country gap. Per-capita
AI dividends end at DE 0.074, FR 0.060, **PL 0.027** — Poland's is a third of
Germany's, purely because it has less capital income to socialise. Global pooling
narrows the 3-country gap ~33% and sends the **largest** transfer to Poland
(+0.033 per capita, funded mainly by DE). This is the real shape of Q2: a national
AI dividend hands the biggest cheque to the richest country; only a pooled dividend
moves resources to where they are scarcest. The effect will grow further as
genuinely poor regions and the full EU are added.

### Tight bilateral trade feedback

Increment 1 left each country's exports autonomous. Increment 2 ties them
together (`MultiRegion.solve_trade`): a **gravity trade matrix** allocates each
country's intra-bloc imports across partners in proportion to partner GDP, so one
country's exports = the sum of its partners' imports directed to it (plus an
autonomous external-RoW component). A **damped regional fixed point** iterates the
whole bloc's output to convergence — a boom in one country pulls in imports,
lifting partners' exports and output, which feeds back. Two-way, not loose.

Guarantees (all verified in `tests/test_region.py`):
- **Convergence** — the damped iteration settles (≈33–55 iterations for DE+FR+PL).
- **Per-country gate intact** — injecting partner-driven exports never breaks any
  country's own stock-flow consistency (worst residual ~6e-5 MEUR).
- **Regional reconciliation** — intra-bloc exports and imports net to zero every
  period to ~1e-9 (one country's export *is* another's import).
- **Real propagation** — turning intra-bloc trade on visibly moves each country's
  GDP path vs the autonomous case.

### Toward the whole EU

The architecture is deliberately N-country: add a sourced `xx_baseline_2019.json`
and extend the `geos` tuple — calibration, the per-country gate, the gravity trade
matrix, the dividend pooling, and the between-country Gini all scale without code
changes. The roadmap is to add the remaining EU members (a low-income region next,
then fill in toward EU27), at which point the national-vs-global dividend question
is answered for the actual Union, not a two-country stand-in.

---

## EU-wide result (2026-06-07) — 26 countries live

All EU27 baselines were pulled live (`build_snapshot`). **26 are viable; Luxembourg
is excluded.** LU is an entrepôt/financial centre where exports and imports each
exceed GDP, so the standalone open-economy closure (exports proxied by own lagged
output) compounds without bound and the calibration produces a pathological
consumption parameter — the run diverges (gate ~1e+233). The `MultiRegion`
viability guard now detects this (non-finite / residual > 1) and skips such a
country, recording it in `DividendComparison.excluded`, so a single distorted
member can't poison the whole bloc. (LU can still be studied inside the
tight-trade regional fixed point, where exports are bounded by partners' demand.)

Across the 26-country bloc (cash UBI, τ=40%, 30-year horizon, gate-clean at ~7e-5):

| Bloc | National between-country Gini | Global (pooled) |
|---|---:|---:|
| EU-26 (LU excluded) | 0.223 | 0.151 (−33%) |
| EU-25 (also excl. IE) | 0.212 | 0.142 (−33%) |

The pattern is unchanged but now at full scale: a **national** AI dividend leaves a
large between-country gap (the richest economies generate the biggest per-capita
dividends); **global pooling narrows it by a third**, transferring per-capita
income from the richest members to the poorest (top receivers: Romania, Croatia,
Hungary, Poland; top payers: Denmark, Germany, Sweden).

**Caveat — Ireland.** IE passes the gate but its GDP is heavily inflated by
multinational profit-shifting / IP relocation, so it shows up as the single
biggest "giver" (−0.085 p.c.) — an artefact, not real prosperity. The EU-25 row
(excluding IE) is the more trustworthy headline; the dashboard's bloc multiselect
lets you drop IE (and would use GNI* if we wire it). LU and IE are the two members
where headline GDP is least representative of the real economy.

**Safety.** `build_snapshot.py --write` now refuses to persist a country that fails
calibration validation (use `--force` only for diagnosis) — so a divergent snapshot
can't land silently the way LU did.
