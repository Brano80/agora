---
title: Free Data Sources for the EU Macro Model — Catalog
created: 2026-06-03
note: All free for research use. A few microdata sets need an application (flagged). Licences vary — check before any commercial use.
---

# Free data sources — what else is useful here

Beyond Eurostat / ECB / FIGARO / AMECO / OECD already noted. Organised by which model layer it feeds. **Start with DBnomics** — it wraps most macro sources behind one API.

## 0. The meta-source (start here)
- **DBnomics** — one free API/Python client that unifies **Eurostat, ECB, IMF, OECD, World Bank, BIS, AMECO, WID** and ~90 providers. The Data agent should target this first: one connector, dozens of sources, consistent format. Removes most of the data-plumbing pain.

## 1. Macro aggregates, money & debt (SFC core + balance sheets)
- **BIS Data Portal** — total credit, debt-service ratios, property prices, effective exchange rates. **Critical for the SFC balance sheets** (household/firm/government debt stocks) — the part Eurostat covers weakly.
- **IMF Data** (IFS, WEO, GFS) — national accounts, fiscal, balance of payments, monetary; good cross-checks and rest-of-world sector.
- **World Bank Open Data / Data360** — broad development + macro indicators, clean API.
- **FRED** (St. Louis Fed) — huge series library incl. international; easiest single API for quick pulls.
- **Eurostat external-sector tables (used, Phase 7 D; `data/connectors/external.py`, rebuild with `scripts/build_external.py`)** — `nasa_10_nf_tr` D42 + D43 vs the rest of the world (S2): equity income paid to foreign owners (RECV) and received from abroad (PAID), which calibrate the foreign-owned share of capital and owners' equity abroad; `nama_10_gdp` B1GQ; `tipsii10` net international investment position (% of GDP). All via DBnomics bulk calls.
- **Eurostat `gov_10dd_edpt1`** (used, Phase 7 E; `data/connectors/fiscal.py`, rebuild with `scripts/build_fiscal.py`) — general government (S13) gross debt GD, net lending B9 and interest paid D41PAY, % of GDP: each country's 2015–19 implicit interest rate and 2019 debt ratio (the fiscal rule's target). Via a DBnomics bulk call.
- **Consumption response to the wage/profit split** (used, Phase 7 E5; `data/connectors/consumption.py`) — published estimates, not a data series: Onaran & Obst (2016), *Cambridge Journal of Economics* 40(6), Table 7 col. A (EU15, 1961–2013); Kaczmarski (2024), *The Polish Journal of Economics* (PL, 2001–2022); EU15 median for the rest. Cross-checked against Eurostat `nasa_10_ki` SRG_S14_S15 (gross household saving rate) and the experimental ICW `icw_sr_10` (propensity to consume by income quintile).
- **Eurostat `ei_bsin_q_r2`** (used, Phase 7 C; `data/connectors/capacity.py`) — EC business-survey capacity utilisation, BS-ICU-PC, SA, all 27 members.
- **Conference Board Total Economy Database** — GDP, hours, labour productivity, TFP, capital services (long annual series).

## 2. Productivity, capital & labour by industry (automation-by-sector + labour share)
- **EU KLEMS & INTANProd** — industry-level capital, labour, energy, materials, productivity **and intangibles**. The best source for "AI hits sector X" and for the falling-labour-share story by industry. (EU Commission / LUISS.)
- **Penn World Table v11** (Groningen GGDC) — 185 countries: real output, capital stocks, **labour share**, TFP. The cross-country gold standard for calibration.
- **OECD Productivity** — complementary productivity/labour-share series.

## 3. Inequality & wealth distribution (core to the scenarios)
- **WID.world (World Inequality Database)** — open API; income **and wealth** distribution, top shares, and the **capital vs labour share** split. Directly feeds the "decoupling" and sovereign-fund-dividend scenarios.
- **OECD Income & Wealth Distribution Database (IDD)** — Gini, poverty, wealth concentration, free.
- **Eurostat SILC indicators** — the *aggregated* income/poverty/inequality indicators are free (the household *microdata* is the access-controlled part).
- **LIS — Luxembourg Income Study** — harmonised income/wealth microdata; "LIS Key Figures" are free, raw microdata needs an account.

## 4. Input–output / production structure
- **OECD ICIO / TiVA** — inter-country input-output, global value chains (free).
- **WIOD** — world input-output tables with socio-economic accounts (labour by skill, capital) — good for automation exposure by sector.
- **EXIOBASE** — environmentally-extended multi-regional I-O (sectors + energy + materials + labour) — free, great if energy/resources matter.
- *(FIGARO already in the plan for the EU-specific I-O.)*

## 5. AI, automation & compute (the scenario drivers — new vs the macro stack)
- **Stanford AI Index 2026** — free PDF + downloadable data: AI investment, adoption, compute, jobs/skills, performance. The single richest free AI dataset.
- **Epoch AI Database** — free; 3,200+ ML models with **training compute, cost, and scaling trends** — the empirical backbone for "compute as a resource/tax base" and AI-capability projections.
- **OECD.AI Policy Observatory** — live data on AI in employment, skills, research, investment by country.
- **ILO Observatory on AI and Work** + **ILOSTAT** — labour-side exposure to AI/automation, plus global employment, wages, **labour share** series.
- **IFR robot density** (International Federation of Robotics) — robots per 10k workers by country/sector; headline stats are free (appear in AI Index/OECD), full reports paid.

## 6. Energy (the physical bottleneck + the energy-backed-money idea)
- **Our World in Data — Energy** — free, clean CSVs: energy use, electricity mix, prices, intensity.
- **Ember** — global electricity generation/price data, free API.
- **ENTSO-E Transparency Platform** — EU electricity generation, load, prices (free, registration).
- **Eurostat Energy** — EU energy balances, prices.

## 7. Convenience / discovery
- **Our World in Data** — pre-cleaned CSVs across economy/energy/tech; fastest for a quick calibrated series.
- **Google Dataset Search**, **Zenodo**, **Kaggle** — for one-off or research datasets.

## Access notes (honest)
- **Free + open API:** DBnomics, WID, World Bank, IMF, FRED, BIS, OWID, Ember, Epoch, OECD.AI.
- **Free download (file/PDF):** EU KLEMS, Penn World Table, Conference Board TED, Stanford AI Index, WIOD, EXIOBASE, OECD IDD/ICIO.
- **Application required (microdata):** EU-SILC (Eurostat research request — needed for EUROMOD), LIS microdata, ENTSO-E (free registration).
- Most are free for research/non-commercial; verify licences before any commercial product use.

## How this changes the build
- Point the **Data agent at DBnomics first** (covers ~80% of macro needs via one API), then add the specialist sources (WID for distribution, EU KLEMS/PWT for sector productivity & labour share, BIS for debt stocks, Stanford AI Index/Epoch/OECD.AI/ILO for the AI-shock parameters).
- This means the **AI-scenario knobs can be empirically grounded**, not guessed: labour-share trajectory (PWT/EU KLEMS/WID), automation exposure by sector (WIOD/ILO/IFR), and compute/capability trends (Epoch/AI Index).

## Auto-building snapshots (live pull)

New country baselines are self-populated from live DBnomics via `python scripts/build_snapshot.py --geo <CODE> --write` (see `docs/SNAPSHOT-BUILDER.md`). It stamps provenance on every value, reconciles imports to the expenditure identity, flags any provider whose dimensions don't resolve (`default_review`), and validates the country through calibration before writing. Dry-run by default.
