# AGORA v1.2: correction note (2026-11-08)

Release notes for v1.2 of *Who Owns the Machine? AI, the labour share and Europe's policy
choices* (formerly *Owning the Machine: A Governance of Abundance for Europe*, v1.0 June
2026, v1.1 July 2026). Use it as the GitHub release text; the Zenodo description
(`scripts/launch_zenodo.py`) carries a short version.

## Why a correction

A review on 2026-10-28 found that the published headline results came from scenario runs
that balanced their books but were not economically plausible:
- output had no capacity limit and no price level;
- capital owners financed investment by unlimited interest-free borrowing from the state;
- all capital, AI capital included, was domestically owned;
- shares moved to the citizens' fund at book value.

An audit of the 3,057 runs behind the published numbers found that only 13% passed basic
plausibility checks (`docs/AUDIT-2026-10.md`).

Phase 7 rebuilt the engine step by step and re-ran every published claim
(`docs/PHASE7.md`). The rebuild added:
- capacity limits and prices;
- credit constraints;
- foreign ownership of capital and of the AI rent;
- shares at market value and a fiscal rule;
- six real policy proposals;
- a banking sector with market interest rates;
- existing loans;
- each country's own capital stock and trend growth;
- gradual consumption.

It then ran a blind 2011–2019 backtest, a multiplier test and a 500-draw Monte Carlo.

## What changed

| Claim in v1.0 / v1.1 | v1.2 | Status |
|---|---|---|
| The citizens' dividend overtakes the cash transfer around year 11 | It stays below the cash transfer every year to 2048 (€5,324 against €7,739 per person, Germany) | retracted |
| UBC dominates both cash UBI and inaction; doing nothing is off the frontier | No policy and cash UBI at every rate are on the trade-off frontier; neither form dominates | retracted |
| With fund reinvestment the UBC economy ends larger than the cash economy | At most 1.04× the cash economy, 0.97× at full reinvestment (Germany); smaller in France | retracted |
| Back-tested to ~2.3% mean GDP error; validated against history | From 2010 data the engine beats a random walk and a static multiplier in only 37% of country-variable cases (median GDP error 3.9%) | retracted |
| UBC eliminates poverty | Poverty falls to 4.5% under UBC, 7.7% under cash | changed |
| A pooled EU dividend roughly halves between-country inequality | Pooling narrows it by 32% (cash) and 21% (UBC) | changed |
| With no policy, inequality rises from ~0.30 to ~0.47 and poverty from ~17% to ~28% | Gini 0.30 to 0.33, poverty 17% to 20% (Germany, 2048) | changed |
| Under the 3% rule the dividend reaches ~€25,000 and citizens come to own all capital | €5,324; citizens own 84% of domestic capital | changed |

Every finding (F1–F23, Q2, the README and the plain-English brief), with its v1.2
number and status: `docs/FINDINGS-LEDGER.md`.

## What survives

- **Only ownership moves the concentration of wealth.** The top-10% wealth share is 17%
  under UBC against 60% under cash (Germany, 2048). UBC has the lower inequality in
  every one of 500 joint Monte-Carlo draws, and the lower poverty rate in 98–100% of them
  (Germany, France, Slovakia).
- **The wage-tax base erodes** as the labour share falls. Public debt rises in all 24
  usable member states, from a median of 55% to 127% of GDP by 2048.
- **The AI shock lands on office work,** not factories.
- **No policy form dominates;** the trade-offs are real.

## What is new in v1.2

The thesis is rewritten around three results:
1. The welfare state's tax base erodes.
2. Cash and ownership trade consumption now for wealth later.
3. Europe does not own most of the machine: 70% of the AI rent is paid abroad by default,
   beyond the reach of domestic taxes and claims.

The study states plainly that the model is not validated as a forecaster.

## Other changes

- **Excluded countries.** Greece, Ireland and Luxembourg are left out of published results
  (`schema/coverage.py`). Greece's calibration implies households spending more than
  their income; multinational accounting distorts Irish and Luxembourg GDP.
- **Year labels.** The 30-period horizon ends in 2048. Earlier documents labelled it 2049.
- **Withdrawn:**
  - the one-page policy brief `AGORA_Policy_Brief_UBC.pdf`. It argued from v1.1 results and
    had no reproducible builder;
  - the README frontier charts.

## Reproduce

```bash
python -m pytest tests/ -q              # 422 tests
python scripts/validate.py              # backtest + multipliers -> docs/VALIDATION-2026-11.md
python scripts/robustness.py            # Monte Carlo -> docs/ROBUSTNESS-2026-11.md
python scripts/findings_ledger.py       # numbers behind the ledger
python scripts/build_manifesto.py       # the study PDF and the README charts
python scripts/build_dashboard.py       # docs/index.html
```

## Publishing steps (for the author)

1. **Zenodo.** Publish v1.2 under the same concept DOI (10.5281/zenodo.20726928):
   `ZENODO_TOKEN=... ZENODO_NEW_VERSION=21127193 python scripts/launch_zenodo.py
   AGORA_Manifesto.pdf`. Earlier versions stay frozen as the public correction record.
2. **GitHub.** Cut release `v1.2` with this file as the notes and attach
   `AGORA_Manifesto.pdf`.
