# AGORA — Phase 3 (in progress)

Phase 3 = open economy (rest-of-world) · FIGARO input-output · more connectors.
This document covers **increment 1: the open economy**, shipped and gated.

## Open economy — rest-of-world + net foreign assets
The closed Phase-1/2 economy excluded net exports (the "net-export gap"). They
are now **inside the books**: the reserved `rest_of_world` sector and `fx_assets`
instrument are active, and the consistency gate validates them like everything
else.

Closure:
```
Y = C + A + G + X - M          # exports inject, imports leak
X = export_ratio * Y_prev      # world demand proxied by lagged output
M = m_imp * Y                  # imports scale with output
current account NX = X - M  ->  accumulates as net foreign assets (fx)
```
- **fx_assets** (net foreign assets) are held by households, split by money
  wealth; **rest_of_world** is the counterpart (its liability = domestic NFA).
- The consumption wealth term now uses **money + fx**, so a surplus country's
  owners can shift into foreign assets without distorting consumption.
- Setting `exports = imports = 0` recovers the closed Phase-1/2 economy — this
  generalises rather than replaces it.

The gate gained nothing special-cased: the generic checks now cover a second
financial instrument (`fx_assets` ↔ `fx_chg`) and a fifth sector
(`rest_of_world`) automatically. Worst residual across all runs: ~6e-5 MEUR.

## Calibration
Baseline GDP is now the **full** expenditure identity `Y0 = C+I+G+X-M`, so the
model reproduces **published GDP** (not just domestic demand). Imports in the
snapshots are reconciled to close the identity exactly; exports are sourced
(Eurostat P6). New canonical series: `exports` (P6), `imports` (P7) — live-
pullable via the connector, snapshot fallback for DE & FR.

## Result (illustrative, final year — not a forecast)
| | GDP | Net exports / GDP | Net foreign assets / GDP |
|---|---|---|---|
| **DE** baseline | grows | ~+5% (persistent surplus) | climbs to ~+117% |
| **FR** baseline | grows | ~−0.4% (near-balanced) | drifts to ~−8% |

Germany's persistent current-account surplus accumulates a large net-creditor
position over 30 years (the savings-glut dynamic — the flip side of someone
else's debt); France drifts to a net debtor. The household decoupling result
(personal Gini ~0.30 → ~0.47 no-policy, contained ~0.32 under the settlement) is
**unchanged** by opening the economy — as it should be.

## Tests
44 passing (10 new open-economy tests, DE + FR): baseline reproduces full GDP +
exports/imports/net exports; `fx_assets` and `rest_of_world` are gated; net
foreign assets accumulate the current account each period (NFA_t − NFA_{t-1} ==
CA_t); external-position direction (DE creditor, FR debtor); decoupling still
holds open.

## Honest limitations (this increment)
- **Per-country RoW**: one external counterparty per economy (DE's RoW includes
  France). Multi-region (DE↔FR modelled, RoW = non-Europe) is the deferred fork —
  the prerequisite for the national-vs-global dividend question (Manifesto Q2).
- **No cross-border factor income / transfers** yet: current account = trade
  balance only. (Primary income & transfers are a later refinement.)
- **Exports proxied** by a stable share of lagged output (world grows with you);
  a true rest-of-world GDP driver needs multi-region.
- **No valuation effects** on the NFA stock (flows only).

## Next in Phase 3
- **FIGARO input-output module** — production structure / sector linkages so an
  "AI hits sector X" shock propagates realistically.
- **More connectors** from the scout backlog (BIS debt, WID wealth, Epoch compute).
- Then the **pinned experiment**: Universal Basic Capital vs cash UBI (activate
  `sovereign_fund`).

---

## Increment 2 — input-output (production structure) ✅

`modules/input_output.py` — the firm-side analogue of the distribution module:
the SFC core sets aggregate output; this decomposes it across ~6 NACE-aggregate
sectors via a **Leontief** structure, so an "AI hits sector X" shock propagates.

- Gross output `x = (I − A)^-1 f` (pure-stdlib linear algebra), value added by
  sector `VA_s = va_coeff_s · x_s`, output multipliers (Leontief column sums).
- **AI sectoral exposure:** the macro labour-share fall is distributed across
  sectors weighted by automation exposure (VA-weighted to track the aggregate).
  Result: ICT/finance/business and Industry shed labour share fastest;
  Construction/Agriculture least — the sectoral face of the decoupling.
- **Reconciliation gate** (`check_input_output`): Σ sectoral value added == GDP,
  and the parts sum to the reported total, every period.
- `A` is built from the snapshot as `A[i,j] = (1−va_coeff[j])·supply_shares[i]`
  (a valid productive matrix). The coarse structure is **illustrative**, anchored
  to stylised EU value-added facts, and **swappable for a live FIGARO / Eurostat
  naio pull** behind the same interface (scout backlog).

Illustrative result (DE, AI-no-policy, final year): macro labour share 0.605 →
0.30 lands very unevenly — ICT/finance/business ~0.51 → ~0.05, Industry ~0.57 →
~0.20, Construction ~0.64 → ~0.53. Tests: 50 passing (6 new I-O tests, DE + FR:
VA reconciles to GDP, the Leontief identity holds, the AI shock concentrates in
exposed sectors). Dashboard gained a sectoral panel (labour share by sector +
output multipliers + AI exposure).

### Honest limitations (this increment)
- The I-O coefficients are an **illustrative coarse 6-sector structure**, not the
  real FIGARO matrix (pending the live pull). Same supplier-share simplification
  for all columns.
- **Loose coupling**: the I-O layer decomposes the macro result; it does not feed
  back into the macro core (no sector-specific price/quantity feedback yet).
- Shared structure across DE & FR for now (per-country FIGARO is the refinement).

---

## Increment 3 — specialist connectors ✅

The scout's connector backlog, partly cleared:
- **BIS** household debt (`hh_debt_gdp`) and **WID** top-10% net-wealth share
  (`top10_wealth_share`) added as canonical series via the multi-provider
  DBnomics path — snapshot-sourced for DE & FR, live-pending (like AMECO; flip
  `live=True` once the BIS/WID dimensions are confirmed via verify_live). The
  wealth-concentration series is direct prep for the **Universal Basic Capital**
  experiment (it measures how concentrated capital ownership is — the thing UBC
  redistributes); household debt is prep for balance-sheet work.
- **Epoch AI** — a bespoke geo-agnostic connector (`EpochConnector`) for global
  frontier-compute trends (training-compute growth ~4.2x/yr, doubling ~6 months).
  It **grounds** the AI-shock driver's assumptions rather than feeding the macro
  calibration, and proves the connector abstraction generalises beyond DBnomics.
  Honest anchor: AGORA's macro capex-growth lever (~6%/yr) is a *conservative
  investment proxy*, not raw compute growth.

The scout now treats BIS / WID / Epoch as connected (its catalog backlog shows
only the still-unconnected sources: EU KLEMS, Penn World Table, OECD, energy…).

### Remaining Phase 3 connector
- **Live FIGARO / Eurostat naio** for the *real* input-output matrix (replacing
  the illustrative coarse structure). Deferred: the symmetric I-O tables are
  large and the pull is data-heavy; the I-O module already runs on the swappable
  snapshot, so this is a drop-in upgrade when the connector lands.

## Phase 3 status
- Increment 1 — open economy (rest-of-world + fx) ✅
- Increment 2 — input-output (Leontief sector decomposition) ✅
- Increment 3 — BIS / WID / Epoch connectors ✅ (live FIGARO matrix pending)

Next: the pinned **Universal Basic Capital vs cash UBI** experiment (activate
`sovereign_fund`) — the foundation (open economy + sectors + wealth data) is now
in place.
