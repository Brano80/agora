#!/usr/bin/env python3
"""
AGORA study — How big is an AI-specific levy base, and could it fund the dividend?

Sizing exercise (not a GE run): compares funding the citizens' dividend from an
AI-SPECIFIC LEVY (digital-services tax + a data-centre / AI-compute levy) against
funding it from OWNERSHIP (equity dilution of the existing capital stock, the route
the AGORA counterfactual already quantifies).

All inputs are documented constants with sources. Outputs a report + a chart.

KEY INPUTS (sourced)
- Global AI/data-centre capex 2026: ~$600-725bn (Big-5 hyperscaler guidance, Q1-2026
  earnings); ~75% is AI-specific. Midpoint used: $650bn.  [Tax Foundation / MUFG / Futurum]
- EU share of that capex: ~10% — the AI value chain is US-dominated.  [assumption, flagged]
- Existing EU national DSTs (2023): FR 680 + IT 434 + ES 345 + AT 103 = EUR 1.56bn,
  each < 0.07% of general revenue.  [Tax Foundation 2024]
- EU-wide DST at a higher rate (CEPS 2025): order EUR ~12bn/yr.  [CEPS]
- Ownership dividend (AGORA counterfactual, 5% POMV on a citizens' fund built since 1995):
  order EUR ~1,000-1,500 / person / yr.  [AGORA study_ownership_counterfactual]
"""

EU_POP        = 449e6      # EU-27 population
USD_EUR       = 0.92       # 2026 average

# --- AI levy base, today (EUR/yr, EU-wide) ---
AI_CAPEX_GLOBAL_USD = 650e9          # 2026, midpoint of $602-725bn
EU_CAPEX_SHARE      = 0.10           # EU share of global AI/data-centre build-out
AI_CAPEX_EU = AI_CAPEX_GLOBAL_USD * EU_CAPEX_SHARE * USD_EUR   # ~EUR 60bn

DST_EU_WIDE = 12e9                   # CEPS-style EU-wide DST, EUR/yr

LEVY_RATES  = [0.05, 0.10]           # levy on the AI capex/compute build-out

# --- Ownership benchmark (the alternative) ---
OWN_DIV_LOW, OWN_DIV_HIGH = 1000.0, 1500.0   # EUR/person/yr

# --- Growth for the projection ---
# Digital-revenue (DST) base grows ~ with the digital economy.
G_DST   = 0.08
# AI-capex/compute base grows fast now (~60%/yr) but damps toward a sustainable rate.
G_CAPEX_START, G_CAPEX_END, DAMP_YEARS = 0.35, 0.12, 12

YEARS = list(range(2026, 2061))

def capex_growth(t):
    if t >= DAMP_YEARS: return G_CAPEX_END
    return G_CAPEX_START + (G_CAPEX_END - G_CAPEX_START) * (t / DAMP_YEARS)

def per_capita(rate):
    """Combined AI-levy base EUR/person/yr, projected, at a given capex-levy rate.
       DST is applied at its own headline rate already (revenue figure), so we add it flat
       and grow it at G_DST; the capex/compute levy is rate*base."""
    out = []
    dst = DST_EU_WIDE
    capex = AI_CAPEX_EU
    for i, yr in enumerate(YEARS):
        total = dst + rate * capex
        out.append(total / EU_POP)
        dst   *= (1 + G_DST)
        capex *= (1 + capex_growth(i))
    return out

series = {r: per_capita(r) for r in LEVY_RATES}

def crossover(rate, target):
    for yr, v in zip(YEARS, series[rate]):
        if v >= target: return yr
    return None

# ---- report ----
L = []
L.append("# AGORA study — Can an AI-specific levy fund the dividend?\n")
L.append("_Sizing exercise. Compares an AI-specific levy (digital-services tax + a "
         "data-centre/AI-compute levy) against funding the same dividend from ownership "
         "(equity dilution of the existing capital stock). Inputs are documented constants; "
         "this is a back-of-model scale check, not a GE run._\n")

base5  = (DST_EU_WIDE + 0.05*AI_CAPEX_EU)/EU_POP
base10 = (DST_EU_WIDE + 0.10*AI_CAPEX_EU)/EU_POP
L.append("## The AI levy base today (EU-27)\n")
L.append(f"- EU-wide DST (CEPS-style): EUR {DST_EU_WIDE/1e9:.0f}bn/yr  =  EUR {DST_EU_WIDE/EU_POP:.0f}/person/yr")
L.append(f"- EU AI/data-centre capex base: EUR {AI_CAPEX_EU/1e9:.0f}bn/yr "
         f"(= 10% of ${AI_CAPEX_GLOBAL_USD/1e9:.0f}bn global x {USD_EUR})")
L.append(f"  - levy at 5%: EUR {0.05*AI_CAPEX_EU/1e9:.1f}bn  =  EUR {0.05*AI_CAPEX_EU/EU_POP:.0f}/person")
L.append(f"  - levy at 10%: EUR {0.10*AI_CAPEX_EU/1e9:.1f}bn  =  EUR {0.10*AI_CAPEX_EU/EU_POP:.0f}/person")
L.append(f"- **Combined AI-specific levy: EUR {base5:.0f}/person/yr (5%) to EUR {base10:.0f}/person/yr (10%).**\n")

L.append("## The ownership benchmark\n")
L.append(f"- A 5% POMV dividend on a citizens' fund built since 1995: EUR "
         f"{OWN_DIV_LOW:.0f}-{OWN_DIV_HIGH:.0f}/person/yr (AGORA counterfactual).")
ratio = OWN_DIV_LOW / base10
L.append(f"- So the AI levy today funds roughly **1/{ratio:.0f}th** of the ownership dividend "
         f"(EUR {base10:.0f} vs EUR {OWN_DIV_LOW:.0f}+). The AI base must grow ~{ratio:.0f}x to match it.\n")

L.append("## When would the AI levy catch up?\n")
for r in LEVY_RATES:
    cy = crossover(r, OWN_DIV_LOW)
    yr = str(cy) if cy else "after 2060"
    L.append(f"- at {int(r*100)}% capex levy, the AI levy matches the low end of the "
             f"ownership dividend (EUR {OWN_DIV_LOW:.0f}/person) around **{yr}** "
             f"-- about {(cy-2026) if cy else '35+'} years out")
L.append("")
L.append(f"(2026 -> 2050 path, 10% levy: EUR {series[0.10][0]:.0f} -> EUR {series[0.10][-1]:.0f}/person/yr.)\n")

L.append("## Reading\n")
L.append("1. **Tiny today.** Every AI-specific base is small in the EU (tens of EUR/person/yr) "
         "because the AI value chain is largely US-owned and lightly taxed here. A flow tax "
         "mostly misses value that has already left the jurisdiction.")
L.append("2. **Slow to catch up.** Even on aggressive compounding the levy does not match an "
         "ownership-funded dividend until the early-to-mid 2050s (2052 at 10%, 2057 at 5%) -- about a generation out.")
L.append("3. **Therefore: levy = seed, ownership = engine.** Predistribution through equity "
         "reaches households now and captures the value a flow tax leaks. The AI levy is a "
         "useful, fast-growing *supplement* that seeds the fund — not the primary mechanism.")

open("study_ai_levy_base.md","w").write("\n".join(L))

# ---- chart ----
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(9,5.2))
ax.axhspan(OWN_DIV_LOW, OWN_DIV_HIGH, color="#cde3d3", alpha=.7, zorder=0)
ax.text(2026.4, (OWN_DIV_LOW+OWN_DIV_HIGH)/2, "ownership dividend\n(equity route, today)",
        va="center", fontsize=9, color="#1d4d2b")
for r, c in zip(LEVY_RATES, ["#9aa7b0","#c0392b"]):
    ax.plot(YEARS, series[r], color=c, lw=2.4, label=f"AI levy, {int(r*100)}% capex rate")
    cy = crossover(r, OWN_DIV_LOW)
    if cy: ax.scatter([cy],[OWN_DIV_LOW], color=c, zorder=5)
ax.annotate(f"~EUR {base10:.0f}/person today", (2026, base10),
            xytext=(2028, 130), fontsize=9,
            arrowprops=dict(arrowstyle="->", color="#555"))
ax.set_ylabel("EUR / person / year"); ax.set_xlabel("")
ax.set_title("An AI-specific levy vs an ownership dividend (EU-27)", fontsize=13, weight="bold")
ax.set_ylim(0, OWN_DIV_HIGH*1.15); ax.legend(loc="upper left", frameon=False)
ax.grid(axis="y", alpha=.25); ax.spines[["top","right"]].set_visible(False)
fig.tight_layout(); fig.savefig("social_ai_levy.png", dpi=140)
print("OK")
print("today 5%/10% EUR/person:", round(base5), round(base10))
print("crossover 5%:", crossover(0.05, OWN_DIV_LOW), " 10%:", crossover(0.10, OWN_DIV_LOW))
print("2050 10% EUR/person:", round(series[0.10][-1]))
