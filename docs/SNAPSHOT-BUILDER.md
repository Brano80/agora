# Self-populating snapshots — the live multi-country pull (toward EU27)

Adding an EU country used to mean hand-authoring a `data/cache/<geo>_baseline_<year>.json`.
The snapshot builder turns that into **run · review · write**: it pulls every
calibration series live from DBnomics, stamps full provenance, reconciles imports,
flags anything that needs manual sourcing, and **validates the result through
calibration before it is trusted**.

## Run it (on a machine with network access)

```bash
python scripts/build_snapshot.py --geo PL                # dry-run report, review first
python scripts/build_snapshot.py --geo RO BG --write     # add two members
python scripts/build_snapshot.py --geo DE --offline      # round-trip a bundled snapshot
```

DRY-RUN by default (human-gated, like the scout): you see the provenance report
first, then pass `--write` to persist. Multiple `--geo` codes build a batch.

## What it does, per country

1. **Live pull, by dimension.** Reuses the existing `DBnomicsConnector` to fetch
   each canonical series in `schema.accounts.SERIES`, bound to the geo. The nine
   Eurostat national-accounts / Gini / population series resolve live today.
2. **Best-effort on the rest.** `labour_share` (AMECO), `hh_debt_gdp` (BIS) and
   `top10_wealth_share` (WID) are *attempted* live (`force_live`); the AMECO geo
   map now covers all EU27, so the wage share can resolve for any member. If a
   provider's dimensions don't resolve, the series falls back to a clearly
   **flagged regional default** (`source: "default_review"`) so you know exactly
   what to source by hand.
3. **Import reconciliation.** Imports are reconciled to the expenditure identity
   `M = X − (GDP − C − I − G)` so the books close (or kept live with `--no-reconcile`,
   letting the statistical discrepancy stand — the calibration absorbs it as `nx_gap`).
4. **Provenance on every value** — provider, DBnomics provider code, source URL, a
   dated note, and a `source` tag (`live` / `snapshot` / `reconciled` / `default_review`).
5. **Validate before trusting.** The pulled data is calibrated and run one period
   through the SFC core + consistency gate; it must reproduce its own GDP / C / I /
   G / labour-share targets *and* pass the gate. A country that fails validation is
   **not written** by default.

## Why this is the EU27 on-ramp

The whole stack is already N-country (`region.py`: calibration, the per-country
gate, the gravity trade matrix, dividend pooling, the between-country Gini all
scale without code changes). The only manual step left was the data. With the
builder, the remaining EU members become a batch job + a review of the flagged
series, after which the national-vs-global dividend question (Q2) can be answered
for the actual Union.

## Honest limits

- The sandbox used to develop this is firewalled from DBnomics, so the **live**
  path runs on the user's machine; offline it round-trips the bundled snapshots
  (what the tests exercise).
- `labour_share`/BIS/WID live resolution depends on each provider's DBnomics
  dimension layout. The builder *reports* whether they resolved; where they don't,
  the flagged default is a placeholder, not a sourced figure — review it (and
  `verify_live.py`) before trusting a new country.

Module: `data/snapshot_builder.py`. CLI: `scripts/build_snapshot.py`. Tests:
`tests/test_snapshot_builder.py` (offline round-trip + validation, reconciliation,
missing/default flagging, write round-trip).
