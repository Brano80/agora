# What the model says: a plain-English brief (v1.2, 2026-11-08)

*Scenario comparisons in a consistency-checked accounting model of 24 EU economies,
calibrated to 2019 data. Not forecasts: they show the economic logic of each policy under
one stated AI shock. Euros are per person at 2019 prices. The direction of each result is
more reliable than its size.*

*This brief replaces the June 2026 version, whose five findings did not survive the
Phase 7 rebuild of the model. What changed, finding by finding:
[`FINDINGS-LEDGER.md`](FINDINGS-LEDGER.md).*

**The shock assumed here:** AI pushes the labour share of income down from ~66% to 30%
by 2048, in a straight line, with an investment boom in AI capital. 70% of the profit
earned by AI capital is paid to foreign providers, roughly the US share of Europe's cloud
market. A milder or slower shock gives the same pattern, smaller.

## Three findings

1. **The welfare state's tax base erodes.** European states fund themselves mostly by
   taxing wages. With no policy, German wage-tax revenue falls from 13.8% to 7.1% of GDP
   by 2048, and taxes on profits rise only from 5.9% to 8.9%. Public debt rises in all
   24 member states, from a median of 55% to 127% of GDP; 7 end above 150%. This holds
   whatever you think of basic income.

2. **Cash and ownership trade consumption now for wealth later.** A 40% levy on profits
   can be paid out as cash to everyone, or taken as shares in a citizens' fund that pays
   out 3% of its value a year (Universal Basic Capital, UBC).
   - Cash raises consumption per person by 13% over no policy; UBC by 1%.
   - UBC cuts the top-10% share of wealth from 56% to 17%; with cash it ends at 60%, as
     with no policy.
   - UBC ends with the lower income inequality (Gini 0.20 against 0.24) and less poverty
     (4.5% against 7.7%).
   - The fund's dividend stays below the cash payment every year to 2048 (€5,324 against
     €7,739).
   - Both cost about 8% of GDP against no policy, because both tax the profits that fund
     investment.

   Neither is better on everything. Across 500 combinations of the model's uncertain
   assumptions, UBC is more equal every time and cash gives more consumption every time.

3. **Europe does not own most of the machine.** By 2048 the AI rent is 36% of German
   GDP, and 70% of it leaves the country. GDP grows 10% while national income falls 13%,
   and consumption per person ends 23% below 2019. Taxes and claims on domestic
   companies cannot reach the part that leaves: a 40% claim in shares reaches a quarter
   of the AI rent; a 3% levy on AI fees paid abroad reaches 0.3% of the foreign part,
   because providers pass it on in prices.

**Between countries:** pooling the levy across the EU and paying an equal European
dividend narrows the gap between member states by 32% under cash and 21% under UBC by
2048. It means large transfers: under cash, Malta pays €15,822 per person a year,
Denmark €11,108 and the Netherlands €10,150, while Bulgaria receives €7,483 and Romania
€6,083.

## Germany after ten years (2029)

| 2029 | No policy | Cash UBI | UBC |
|---|---:|---:|---:|
| Poverty rate | 18.2% | 10.0% | 13.8% |
| Inequality (Gini) | 0.309 | 0.249 | 0.269 |
| Paid to each person a year | €0 | €6,675 | €1,836 |
| Consumption per person a year | €20,314 | €23,897 | €20,430 |
| Top-10% share of wealth | 57% | 57% | 27% |
| Share of capital owned by citizens | 0% | 0% | 61% |
| Fund wealth per person | €0 | €0 | €76,619 |

2019: poverty 17.2%, Gini 0.297, consumption €22,446, top-10% wealth share 56%.

Cash helps sooner. Ownership builds a stake (€76,619 per person after ten years) that
pays little at first. Whether that is worth less consumption now is a values question;
the model only shows the size of the trade.

## Honest limits

- **Not a forecaster.** Started in 2010 with what actually happened to government
  spending and world demand, the model tracks 2011–2019 no better than simple benchmarks
  ([`VALIDATION-2026-11.md`](VALIDATION-2026-11.md)). Its short-run fiscal responses are
  in line with central-bank models in the first year.
- **The AI shock is an assumption,** and its size drives most of the results.
- **The size of the inequality gap is uncertain.** It depends mostly on one parameter
  that recent data cannot pin down; the ranking holds across its range.
- **Outside the model:** the politics of a capital levy, fund governance and capture,
  capital flight, and whether the AI shock comes at all.
- **Coverage:** Greece, Ireland and Luxembourg are left out (calibration and
  multinational accounting distort them).

Everything here is regenerated from the model: the study by
`scripts/build_manifesto.py`, the ledger numbers by `scripts/findings_ledger.py`.
