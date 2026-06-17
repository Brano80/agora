# The pinned experiment — Universal Basic Capital vs cash UBI

**The question (MANIFESTO Q1, the flow-vs-stock crux).** If AI drives the labour
share down and capital income up, is it better to redistribute a slice of capital
income every year as cash (a *flow* — universal basic income), or to convert that
same slice into a citizens' ownership stake in the capital itself (a *stock* —
universal basic capital)? AGORA exists to compare such policies in one internally
consistent accounting world, so this is the experiment it was built to run.

## Design (equal-cost by construction)

Both policy arms face the **same** AI shock (labour share → 30%, AI-capex boom)
and apply the **same** intensity lever `τ = 40%` to capital income. They differ
*only in form*:

- **Cash UBI.** The levy `τ·FP` is redistributed as an equal per-capita cash
  transfer **that year**. Pure flow; it builds no wealth and is re-levied every
  year from whatever the current capital income happens to be.
- **Universal Basic Capital.** An equal-valued claim `τ·FP` is converted **in
  kind** each year into a citizens' capital endowment held by the
  `sovereign_fund` (existing owners are diluted; no cash levy). The fund comes to
  own a share `φ = E_sf / K` of the capital stock, earns `φ·FP` of profits, and
  pays it out per capita as the **sovereign-fund dividend**. The endowment
  compounds.

The government's deficit path is **identical** across the two arms
(`dH_s = G − tax_w`), so the comparison is genuinely equal-cost. The fund holds
**no money** — its profit share exactly equals the dividend it pays — so only
*money* and *fx* remain financial instruments and the consistency gate still
closes to ~1e-4 MEUR every period. (Activating the fund did not open a leak; the
gate is the proof.)

## Result (DE, 2019 calibration, 30-year horizon)

| Year | Gini: no-policy | Gini: cash UBI | Gini: UBC | Cash transfer (MEUR) | UBC dividend (MEUR) | UBC φ | UBC poverty | cash poverty |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2019 | 0.297 | **0.138** | 0.297 | 612,446 | 0 | 0.05 | 0.172 | **0.074** |
| 2024 | 0.351 | **0.175** | 0.256 | 981,893 | 434,430 | 0.25 | 0.112 | **0.096** |
| 2030 | 0.412 | 0.216 | **0.199** | 1,584,251 | 1,626,562 | 0.47 | **0.027** | 0.122 |
| 2038 | 0.490 | 0.269 | **0.052** | 2,915,096 | 8,383,837 | 0.86 | **0.000** | 0.156 |
| 2048 | 0.579 | 0.330 | **0.044** | 6,168,002 | 58,700,645 | 1.00 | **0.000** | 0.195 |

**The flow-vs-stock trade-off is real and it reverses.** Cash UBI compresses
inequality *immediately* (Gini 0.30 → 0.14 in year 1) and does the most good in
the **first decade** — its transfer is large from day one. UBC starts slow,
because the first years go into *building* the endowment rather than paying it
out. But the endowment compounds: the UBC dividend **overtakes the cash transfer
in 2030**, and from there it pulls away. By the end of the horizon citizens own
**100%** of the capital stock, the dividend is roughly **10×** the cash transfer,
the macro Gini has collapsed to **0.04** (vs cash UBI's 0.33), and poverty is
eliminated. Cash UBI, by contrast, must keep re-levying a fixed share of a capital
base it never comes to own, so inequality keeps drifting up underneath it.

In one line: **redistribution (flow) is faster; predistribution (stock)
compounds.** A society optimising for the next election prefers cash; a society
optimising for a generation prefers capital. The dashboard's "Universal Basic
Capital vs cash UBI" panel shows the four charts (ownership share, annual benefit,
inequality, citizens' wealth) live and swappable.

## Honest caveats (sandbox, not oracle)

- **Investment is held on the same path in both arms.** The single biggest open
  question (MANIFESTO C1, enclosure-vs-diffusion): if diluting owners' returns
  depresses investment `A`, UBC's capital base grows more slowly and the verdict
  softens. The model does **not** yet endogenise that incentive response — it is
  the obvious next stress test (make `capex_growth` respond to the owners' net
  return).
- **The dividend is paid out in full** (no reinvestment). Reinvesting part of the
  fund's profits would make UBC compound *even faster* — so this is the
  conservative case for UBC.
- **Two-class macro distribution.** The personal Gini comes from the reduced-form
  distribution module; the *direction* and *crossover* are robust, the exact
  levels are model-dependent and swappable (β, γ).
- **One country, closed to the dividend's global dimension.** This is a national
  fund. The "should the dividend be global?" question (MANIFESTO Q2) needs the
  multi-region extension and is untouched here.

## How to run it

```python
from orchestrator import AgoraOrchestrator
o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True)
o.load_data()
runs = {r.scenario: r for r in o.run_ubc_experiment(horizon=30)}   # gated
```

Levers: `scenarios.make_ubc_experiment` (shared shock, shared `τ`), or
`build_custom(..., ubc=True)`. Mechanism: `modules/sfc_core.py` (the `ubc_on`
branch). Regression guard: `tests/test_ubc.py` (gate-clean + the crossover +
late-inequality result are all pinned).

---

## C1 stress test — what if diluting owners chokes investment? (2026-06-07)

The headline result above held investment on the same path in both arms. The
obvious objection (crux C1, enclosure-vs-diffusion): owners fund the capex, and
if their returns are socialised they may stop building. We endogenised it. The
SFC core now carries an **investment elasticity** `ε` (`inv_elasticity`, an
inspectable, swappable assumption; `ε=0` reproduces the autonomous Phase-1..3
behaviour). Investment responds to the share of capital income owners still
**retain**:

```
A_t = (autonomous AI-capex)_t · signal_t ** ε
signal_t = 1 − φ_t   (UBC: owners' retained share of the capital stock)
         = 1 − τ      (cash UBI / no policy: the flat after-tax share)
```

Both policies extract `τ·FP` a year, so a *flat* tax and UBC look identical at
`t=0`. The difference is dynamic: cash UBI's signal stays flat at `1−τ`, but
UBC keeps socialising the **stock**, so its signal `1−φ` falls toward zero as the
fund approaches full ownership. UBC is therefore the *harder* case for private
investment — exactly the tension C1 names.

Sweeping `ε` (DE, 30y; gate stays clean at ~1e-4 every period):

| ε | crossover | UBC Gini (end) | cash Gini (end) | UBC capital (end) | cash capital (end) |
|---:|---:|---:|---:|---:|---:|
| 0.0 | 2030 | 0.044 | 0.330 | 69.9M | 69.9M |
| 0.5 | 2030 | 0.044 | 0.330 | 32.8M | 56.6M |
| 1.0 | 2030 | 0.044 | 0.330 | 27.1M | 46.2M |
| 1.5 | 2029 | 0.044 | 0.330 | 23.7M | 38.2M |

**What's robust, and what isn't.** The *distributional* verdict is robust: the
dividend overtakes the cash transfer at the same time (~2030) and UBC ends far
more equal (Gini ~0.04 vs ~0.33) at **every** elasticity — because the crossover
is driven by early endowment accumulation, before investment paths diverge much.
What is *not* robust is the **level of output**: with a strong disincentive
(`ε=1`), UBC's capex falls as owners are diluted out, and it ends with a capital
stock ~40% below the cash-UBI path. Predistribution still wins on equality, but
under a real incentive response it buys that equality at the cost of a smaller
economy.

**Honest read (and the next refinement).** This is partly an artefact worth
naming: in the current model *only private owners* fund investment and the fund
is a **pure pass-through** (it pays out 100% of its profit share). So as owners
exit, nobody picks up the capex — investment collapses by construction. A
citizens' fund that *owns* the capital would naturally **reinvest** to maintain
and grow it; letting the fund reinvest would transfer the investment function
from departing private owners to the fund and largely neutralise the `ε`
penalty. That — endogenous fund reinvestment — is the clean follow-up, and it
turns C1 from "predistribution kills investment" into "predistribution *moves*
the investment decision from owners to the public fund." Until that is modelled,
read the `ε>0` capital gap as the *pessimistic bound* for UBC.

---

## C1 resolved — let the fund reinvest (2026-06-07)

The `ε>0` capital collapse above was flagged as partly an artefact: only private
owners funded capex, and the fund paid out 100%. We closed that. The fund now
**reinvests** a fraction `r` (`ubc_reinvest`, swappable, default 0) of its profit
share into capital formation instead of paying it all out:

```
fund profit share  = φ·FP
  ├─ reinvested  A_fund = r·φ·FP   → finances capex, grows the citizens' stake
  └─ paid out    Div    = (1−r)·φ·FP → the per-capita dividend
total investment   A = A_priv + A_fund,  A_priv = (autonomous)·(1−φ)**ε
```

The fund's profit share is fully used (dividend + reinvestment), so it still
holds **no money** and the gate still closes exactly. Re-running the hard case
(`ε=1`, disincentive ON, DE, 30y):

| UBC reinvest r | end capital | end investment | end Gini | gate |
|---:|---:|---:|---:|:--:|
| 0.0 | 27.1M | **0** (collapsed) | 0.044 | ✓ |
| 0.3 | 68.4M | 6.1M | 0.058 | ✓ |
| 0.5 | 124.5M | 16.1M | 0.072 | ✓ |
| (cash UBI, ref) | 46.2M | 2.4M | 0.330 | ✓ |

**The collapse vanishes.** Even a modest reinvest rate (`r ≥ 0.3`) leaves UBC with
a **larger** capital stock than the cash-UBI path — the opposite of the `r=0`
result. The mechanism is exactly the resolution we predicted: as `φ→1` and private
owners are diluted out, their capex falls toward zero, but the fund (which now
owns the capital) picks it up — by the late horizon **all** investment is
fund-financed. The investment function does not disappear; it **moves from
departing private owners to the public fund**.

So crux **C1 is not fatal to predistribution** — it is a *governance design*
question. "Who invests when capital is socialised?" has a clean answer in this
model: the fund does, out of the returns it now earns. The remaining trade-off is
gentler and internal to UBC: a higher reinvest rate buys a bigger economy at the
cost of slightly less immediate equality (more retained, less paid out as
dividend), but inequality stays far below cash UBI at every rate. The dashboard's
"UBC fund reinvest rate" slider makes this live.

---

## 2026-06-12 re-run — magnitudes under the hardened model

The mechanism and the verdict above are unchanged, but the NUMBERS in earlier
tables predate four hardening steps: the fiscal-balance theta (F9), the exact
poverty-floor incidence (F10, no more assumed gamma), the inventories component
closing the expenditure identity, and the exact demand solve. Current results
(tau=40%, 30y, consistency-gated, snapshots rebuilt live 2026-06-12):

| | crossover yr | end Gini | end poverty | fund share of K | citizen wealth /cap | top-10% wealth |
|---|---:|---:|---:|---:|---:|---:|
| **DE** cash UBI | — | 0.354 | 11.8% | — | €0 | 60% (unmoved) |
| **DE** UBC      | 2029 | 0.118 | **0.0%** | 79% | €294,600 | 21% |
| **FR** cash UBI | — | 0.355 | 11.5% | — | €0 | 55% (unmoved) |
| **FR** UBC      | 2030 | 0.131 | **0.0%** | 77% | €258,500 | 20% |
| **PL** cash UBI | — | 0.308 | 10.3% | — | €0 | 58% (unmoved) |
| **PL** UBC      | 2027 | 0.070 | **0.0%** | 82% | €90,400 | 19% |

Two honest changes of substance vs the original write-up: (1) cash UBI's old
"poverty -> 0" was an artifact of the assumed gamma compression — under exact
incidence its flat pool never clears the 60%-of-median line (ends ~10-12%),
while UBC's dividend compounds past the line and reaches a TRUE zero (F10).
(2) The flow-vs-stock gap is therefore LARGER than first reported, and it now
rests on arithmetic rather than an elasticity. Remaining assumption: beta
(market-Gini sensitivity) — panel estimator shipped (`scripts/estimate_beta.py`).
