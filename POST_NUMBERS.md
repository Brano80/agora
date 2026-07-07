# POST_NUMBERS — engine audit of LINKEDIN_POSTS_READY.md

Regenerated from the gated engine (DE/FR/SK, horizon 30). **43/45 checks PASS.**

Not auto-audited here: Post 7 (100+ Monte-Carlo draws, run `uncertainty.py`) and Post 9 backtest MAE (networked panel; constant in build_manifesto.py). Posts 10/12 carry no pre-audit engine numbers.

## FLAGGED (fix before posting)

- **P5 pooling DE+FR+SK** — engine `46.6` vs post `61`
- **P5 pooling DE+FR** — engine `49.8` vs post `58`

## All checks

- [PASS] P1 DE Gini none: engine `0.34` / post `0.34`
- [PASS] P1 DE pov none: engine `20.7` / post `21`
- [PASS] P1 DE Gini cash: engine `0.24` / post `0.24`
- [PASS] P1 DE pov cash: engine `6.4` / post `6`
- [PASS] P1 DE Gini ubc: engine `0.12` / post `0.12`
- [PASS] P1 DE pov ubc: engine `0.0` / post `0`
- [PASS] P1/P8 DE UBC/cash GDP: engine `1.278` / post `1.28`
- [PASS] P2 DE tau shape: engine `peak 0.50` / post `peak~0.5`
- [PASS] P3 DE labour-share race: engine `(8.5, 22.9)` / post `(9, 23)`
- [PASS] P4 DE ramp==scurve pov: engine `{'ramp': 20.7, 'scurve': 20.7}` / post `equal`
- [PASS] P6/11 DE ICT, finance & business: engine `(45.0, 2.0)` / post `(45, 2)`
- [PASS] P8 DE fixed: engine `1.28` / post `1.28`
- [PASS] P8 DE endogenous: engine `0.81` / post `0.81`
- [PASS] P8 DE endogenous+reinvest: engine `0.97` / post `0.97`
- [PASS] P1 FR Gini none: engine `0.34` / post `0.34`
- [PASS] P1 FR pov none: engine `20.4` / post `20`
- [PASS] P1 FR Gini cash: engine `0.23` / post `0.24`
- [PASS] P1 FR pov cash: engine `6.1` / post `6`
- [PASS] P1 FR Gini ubc: engine `0.12` / post `0.12`
- [PASS] P1 FR pov ubc: engine `0.0` / post `0`
- [PASS] P1/P8 FR UBC/cash GDP: engine `1.274` / post `1.27`
- [PASS] P2 FR tau shape: engine `peak 0.50` / post `peak~0.5`
- [PASS] P3 FR labour-share race: engine `(8.7, 23.4)` / post `(9, 23)`
- [PASS] P4 FR ramp==scurve pov: engine `{'ramp': 20.4, 'scurve': 20.4}` / post `equal`
- [PASS] P6/11 FR ICT, finance & business: engine `(50.0, 2.0)` / post `(50, 2)`
- [PASS] P8 FR fixed: engine `1.27` / post `1.27`
- [PASS] P8 FR endogenous: engine `0.71` / post `0.71`
- [PASS] P8 FR endogenous+reinvest: engine `0.88` / post `0.88`
- [PASS] P1 SK Gini none: engine `0.26` / post `0.26`
- [PASS] P1 SK pov none: engine `13.6` / post `14`
- [PASS] P1 SK Gini cash: engine `0.18` / post `0.18`
- [PASS] P1 SK pov cash: engine `2.5` / post `3`
- [PASS] P1 SK Gini ubc: engine `0.12` / post `0.12`
- [PASS] P1 SK pov ubc: engine `0.0` / post `0`
- [PASS] P1/P8 SK UBC/cash GDP: engine `1.041` / post `1.04`
- [PASS] P2 SK tau shape: engine `rising True` / post `still rising`
- [PASS] P3 SK labour-share race: engine `(7.2, 19.3)` / post `(7, 19)`
- [PASS] P4 SK ramp==scurve pov: engine `{'ramp': 13.6, 'scurve': 13.6}` / post `equal`
- [PASS] P6/11 SK ICT, finance & business: engine `(31.0, 2.0)` / post `(31, 2)`
- [PASS] P8 SK fixed: engine `1.04` / post `1.04`
- [PASS] P8 SK endogenous: engine `0.79` / post `0.79`
- [PASS] P8 SK endogenous+reinvest: engine `0.84` / post `0.84`
- [FLAG] P5 pooling DE+FR+SK: engine `46.6` / post `61`
- [FLAG] P5 pooling DE+FR: engine `49.8` / post `58`
- [PASS] P1 frontier all-UBC: engine `['ubc']` / post `['ubc']`
