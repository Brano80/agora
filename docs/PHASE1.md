# AGORA — Phase 1 (Skeleton) — built

A working **modular skeleton with one plug fitted**: the plug-in contract proven
end-to-end, gated by the consistency checker, calibrated to Germany 2019, and
driven through the Baseline / AI-no-policy / Abundance-Settlement triad.

## The five layers, realised
| Layer | Where | What |
|---|---|---|
| 1 Dashboard | `dashboard/app.py` | Streamlit: scenario triad, gate verdict, validation, inspectable+swappable assumptions, module manager. |
| 2 Orchestrator + gate | `orchestrator.py`, `consistency/checks.py` | Route → run → reconcile → **consistency gate**. Calibration loading + baseline backtest. |
| 3 Modules | `modules/interface.py`, `modules/sfc_core.py` | The `Module` contract + the self-contained two-class monetary SFC core. |
| 4 Canonical schema | `schema/accounts.py` | Sectors, instruments, flows, canonical series (with DBnomics codes), DuckDB DDL. The linchpin. |
| 5 Data | `data/connectors/dbnomics.py`, `data/store.py`, `data/cache/de_baseline_2019.json` | DBnomics connector (live → sourced snapshot fallback) + DuckDB store. |

## How to run
```bash
pip install -r requirements.txt
python scripts/run_triad.py          # CLI: validation + triad + gate residual
streamlit run dashboard/app.py       # interactive dashboard
pytest tests/                        # 8 tests incl. leak-detection + decoupling
```
`--live` on the script (or the sidebar checkbox) attempts the real DBnomics API;
otherwise the bundled, sourced German-2019 snapshot is used. Every value carries
its DBnomics series code as provenance.

## What the gate enforces (the crown jewel)
Every period of every run is checked for: column budgets sum to zero, financial
rows balance (incl. the hidden equation / Walras' law), **stock-flow
articulation** (Δstock == driving flow — the exact leak that killed v0), balance-
sheet closure, and sectoral balances summing to zero. Strict mode **blocks** a
run on any failure. Worst residual on the German baseline: ~2e-4 MEUR on a
multi-trillion economy (machine precision).

## Calibration (validate before trusting)
Closed-form fit to German 2019. Year-0 reproduces GDP (closed = C+I+G),
consumption, investment, government, labour share, and Gini at 0.000% error; the
debt stock is seeded to the Maastricht ratio (59.6%). Income tax θ is calibrated
to the Gini target; owners' MPC is solved so baseline demand reproduces GDP.

## The result (illustrative, not a forecast)
- **Baseline** — Gini holds ~0.30; debt drifts with a small deficit.
- **AI, no policy** — labour share 0.61→0.30, capex +6%/yr: Gini explodes to ~0.58
  and the wage-tax base erodes → rising deficits/debt. The Great Decoupling.
- **AI + Abundance Settlement** — same shock + 40% capital tax recycled as UBI:
  Gini contained ~0.33 and consumption sustained highest.

## Honest limitations (Phase 1 by design)
- **Closed economy** — net exports (~5.9% of German GDP) are excluded and
  reported; `rest_of_world` activates in Phase 3.
- **Two-class distribution** — Gini is between-group only; real micro-distribution
  is the Phase 2 EUROMOD/PolicyEngine module.
- **One financial instrument** (government money). Banks/loans, bills, equity, the
  sovereign fund and Universal Basic Compute are declared in the schema but
  inactive — they snap in via the same interface.
- **Sandbox, not oracle.** It compares policies in an internally consistent world;
  it does not forecast.

## Country-agnostic
Schema, connector, and calibration all take a `geo` code. Germany → France →
euro-area is a snapshot/`geo` swap, not a rewrite. Multi-country is Phase 3/4.

## Next (Phase 2)
Distribution module (EUROMOD/PolicyEngine) + an explicit AI-shock driver
(Epoch/AI Index/ILO parameters) + a richer scenario builder and side-by-side
comparison view, all behind the existing interface and gate.

---

## Update — live data + multi-country (Phase 1.5)

**Live DBnomics pull.** The connector now queries the v22 API **by dimensions**
(`{freq, unit, na_item, sector, geo, ...}`) rather than a guessed dotted series
code — order-independent and robust. Each series pulls live when reachable and
**falls back per-series to the sourced snapshot** otherwise; every row is
stamped `live` or `snapshot`. The 7 Eurostat series (GDP, consumption,
government, investment, debt, Gini, population) are wired live; labour share
(AMECO adjusted wage share) is snapshot-sourced until its AMECO dimensions are
confirmed (flip `live=True` in `schema/accounts.py` once verified).

Confirm on a networked machine:
```bash
python scripts/verify_live.py --geo DE      # per-series live vs snapshot
python scripts/run_triad.py  --geo DE --live
```
`verify_live` prints the exact DBnomics query URL for each series so you can
eyeball it in a browser.

**Second country: France.** `data/cache/fr_baseline_2019.json` adds a sourced
FR-2019 snapshot. France calibrates and stays consistent out of the box
(baseline Gini 0.292; debt starts at its real 97.4% ratio). Switch country in
the dashboard picker or via `--geo FR`. Adding Italy/Spain/euro-area is now just
another snapshot file (or confirmed live) — the schema, connector, calibration,
gate and dashboard are unchanged.
