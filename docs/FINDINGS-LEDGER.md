# Findings ledger (Phase 7 step F3, 2026-11-08)

Every finding the project published (F1-F23 and Q2 in `docs/MANIFESTO.md`, the five
findings in `docs/FINDINGS.md`, the README headline) re-run on the step-F engine: the
behavioural closure with banks, each country's own capital stock, existing loans,
lagged consumption and Ageing Report trend growth (`docs/VALIDATION-2026-11.md`).
Numbers: `docs/findings-ledger-2026-11.json` (`python scripts/findings_ledger.py`) and
`docs/robustness-2026-11.json` (`python scripts/robustness.py`). Germany, 2049, AI
shift, 40% levy or claim, fund paying out 3% of its value a year, real 2019 euros,
unless stated. Step G rewrites the public documents from this ledger.

**Status:** *survives* (holds as stated), *changed* (direction holds, the numbers or the
scope do not), *retracted* (does not hold), *unaffected* (not an engine result).

## Manifesto findings

| # | Claim as published | Step-F engine | Status |
|---|---|---|---|
| F1 | No policy: personal Gini ~0.30 to ~0.47, poverty ~17% to ~28%; a capital-funded UBI contains both | Gini 0.297 to 0.333, poverty 17.2% to 20.0%; cash UBI 0.242 and 7.7% | changed: same direction, a fifth to a quarter of the size |
| F2 | The wage-tax base erodes; deficits and debt rise | Debt 60% to 140% of GDP (24-country median 55% to 127%; 7 of 24 above 150%) | survives |
| F3 | DE's surplus builds a net creditor position of ~117% of GDP over 30 years | Baseline NIIP 67% to 160% of GDP | survives, unvalidated: the current account is the backtest's weakest variable and there is no exchange-rate feedback |
| F4 | The AI shock lands unevenly across sectors | Labour share: ICT, finance & business 0.45 to 0.02 (the floor); construction 0.63 to 0.47 | survives |
| F5 | UBC's dividend overtakes cash around year 11; citizens own ~100% of capital; Gini ~0.04 against ~0.33; poverty eliminated | The dividend never overtakes cash by 2049 (€5,300 against €7,700 per person); citizens own 84%; Gini 0.202 against 0.242; poverty 4.5% against 7.7% | changed: the crossover is retracted; the equality and ownership edge survives, much smaller |
| F6 / F6b | Diluting owners deters investment; fund reinvestment cures it | Investment responds to profits by default. UBC's real GDP is 1.00x cash with no reinvestment; 1.03x at 30-60% and 0.97x at 100% (DE); 0.89-0.97x in FR | changed: dilution costs little in DE, and reinvestment is no cure (in FR it lowers output) |
| F7 | A national dividend widens the between-country gap; pooling narrows it ~34% (DE+FR) | DE+FR+PL (the published pair plus Poland): pooling narrows it 31% (cash) and 29% (UBC) by 2049; Poland gains €3,800 per person a year under cash, Germany pays €3,100 | survives, revised numbers |
| F8 | Only ownership touches wealth: top-10% wealth share ~60% under cash, ~21% under UBC; robust across the Monte Carlo | 59.6% against 16.9%; separated in 100% of 500 joint draws (DE, FR, SK) | survives |
| F9 | Backtest: GDP within ~1-1.6%, debt fixed; the model is historically validated | 2011-19 backtest: median GDP error 3.9% (DE 1.2%), debt 8.4 pp; the engine beats both naive benchmarks in 37% of cases | retracted: "validated" does not stand. See `docs/VALIDATION-2026-11.md` |
| F10 | Cash leaves poverty at ~11.8%; only UBC abolishes it | Cash 7.7%, UBC 4.5% | changed: both cut poverty, UBC more; neither abolishes it |
| F11 (+ amendment) | Pooling narrows gaps under both forms, more under UBC (DE+FR+PL ~50% cash, ~58% UBC) | 31% cash, 29% UBC | changed: UBC no longer narrows more |
| F12 | Beta is unidentified, but UBC beats cash on Gini and poverty across the whole beta prior | Separated on Gini and poverty in DE, FR and SK (100% of draws; FR poverty 98%) | survives |
| F13 | The redistribution wedge is ~0.37 (OECD IDD) | Data result, unchanged | unaffected |
| F14 | Endogenous investment chokes UBC unless the fund reinvests; with reinvestment UBC matches or beats cash; equality untouched | See F6. UBC's Gini rises to 0.278 at full reinvestment, above cash's 0.242 | changed: reinvestment is a dial between dividend and capital, not a cure; the equality edge needs the payout |
| F15 | Market-Gini panel: beta 0.128 | Data result, unchanged | unaffected |
| F16 | Ownership is the durable UBC win; the income-Gini edge depends on the payout | Top-10% wealth 15-17% in every regime; income Gini edge gone at full reinvestment | survives |
| F17 | Wealth concentrates without policy (top 10%: 55.5% to 60.7%) | 55.5% to 59.7% | survives |
| F18 | The verdict survives the full joint prior; the investment response drives ~50% of the variance | Separation survives (19 priors, 500 draws). The UBC Gini's variance: beta 91%, AI labour-share fall 5%; profit response under 1% | changed: beta, not investment, drives the inequality result |
| F19 | AI exposure is cognitive (OECD 2024 taxonomy) | Input data, unchanged | unaffected |
| F20 | A responsive government holds debt at 80-82% under every policy; fiscal sustainability is policy-invariant | No-policy debt 127% of GDP (24-country median); in DE the proposals move it by -15 to +29 pp | retracted (already in `docs/PHASE7.md`, step E) |
| F21 | Under Norway's 3% rule the DE dividend is ~€25,000 and the fund compounds to full ownership | €5,300 per person; the fund owns 84% of domestic capital; citizens' fund wealth €178,000 per person (Monte Carlo median) | changed: the rule stands, the dividend is a fifth of the published one |
| F22 | An AI-specific levy is a seed (~€33-40 per person a year), not the engine | Sizing study outside the engine (`scripts/study_ai_levy_base.py`) | unaffected |
| F23 | "UBC dominates cash" holds only with fixed investment | With investment responding by default, cash UBI at every rate, no policy and all six proposals are on the DE frontier; UBC at 40-60% is off it | survives, and strengthened: there is no dominant form |
| Q2 | A pooled EU dividend halves the between-country Gini under either form (51% cash, 52% UBC) | 24 countries, 2049: 32% cash, 21% UBC | changed: pooling narrows the gap by a third (cash) or a fifth (UBC) |

## README headline

| Claim | Step-F engine | Status |
|---|---|---|
| Cash UBI leaves the top-10% wealth share ~56%; UBC collapses it to ~20% | 59.6% against 16.9% | survives |
| With reinvestment the UBC economy ends larger than the cash economy | DE 0.97-1.03x; FR 0.89-0.97x | retracted |
| A pooled EU dividend roughly halves between-country inequality | A third (cash), a fifth (UBC) | changed |
| UBC dominates cash UBI and inaction across the frontier | No policy and every cash rate are on the DE frontier | retracted |
| Validated: ~2.3% mean GDP error 2010-2019, debt within 10% | Median 3.9% GDP error, 8.4 pp debt; does not beat naive benchmarks | retracted |

## `docs/FINDINGS.md` (the plain-English brief)

| Claim | Step-F engine | Status |
|---|---|---|
| 1. No policy: poverty +11 points in ten years; DE Gini 0.30 to 0.51 | +0.8 points in ten years, +2.4 by 2049 (median); DE Gini 0.309 after ten years, 0.333 by 2049 | retracted (magnitude) |
| 2. Ten years of UBC: DE poverty 12.8%, below 2019's 17.2%; citizens own 50% of capital | 13.8%; Gini 0.269 below 0.297; citizens own 61% | survives |
| 3. Cash and UBC give similar income at ten years (~€25,000 each); UBC's dividend reaches ~6x cash by 30 years | After ten years: cash €6,700, UBC €1,800 per person; UBC stays below cash to 2049 | retracted |
| 4. Pooling cuts the gap by a third in ten years | After ten years: -25% (cash); UBC pooling widens it 5% before narrowing 21% by 2049. Romania gains €6,100 a year by 2049 under cash (published ~€11,000) | changed |
| 5. No single best policy, but inaction is never on the frontier | No policy is on the DE frontier | changed: "no single best" stands; "inaction never" is retracted |

## What survives, in one paragraph

Owning beats receiving on wealth and inequality: in every country, regime and draw,
UBC leaves citizens owning most domestic capital and a lower Gini and poverty rate than
cash. That is the robust core (F8, F12, F16, F17). Everything that rested on UBC's
dividend outgrowing the cash transfer, or on UBC costing no growth, does not survive.
The dividend stays below the transfer to 2049, cash delivers more consumption in every
draw (`docs/ROBUSTNESS-2026-11.md`), and reinvestment trades dividend for capital
without lifting output. Choosing between them is a values call between consumption now
and ownership. Doing nothing is no longer dominated: it wins on national income because
both policies tax the profits that drive investment.
