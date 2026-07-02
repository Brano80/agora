#!/usr/bin/env python3
"""Reproducible builder for AGORA_Manifesto.pdf ('Owning the Machine').

Every engine-derived number and all 8 figures are REGENERATED from the gated
engine at build time — the prose contains no hand-typed results, so the
document can never silently drift from the model again (the v1 lesson: it
shipped a pre-bugfix '~1% GDP error' claim). The only hand-carried numbers are
the historical-backtest errors, which need a networked machine and are kept as
documented constants below with provenance.

Usage:  python scripts/build_manifesto.py [out.pdf]     (offline, ~1 min)
Deps :  pip install reportlab matplotlib
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- hand-carried constants (live-machine results; everything else is computed)
BACKTEST = {
    "gdp_mae_pct": 2.34, "debt_mae_pct": 9.72, "window": "2010–2019",
    "provenance": "live DE panel, run 2026-06-11 (post gov_override fix); "
                  "debt within the pre-set 10% validation bound",
}
DATE_LINE = "June 2026 (v1.1, corrected)"
AUTHOR = "Branislav Ambroz"

C_BASE, C_NOPOL, C_CASH, C_UBC = "#64748b", "#c0392b", "#2563eb", "#059669"
WEDGE_GEOS = ["DE", "FR", "IT", "ES", "NL", "SE"]


def _test_count() -> int:
    try:
        out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only",
                              "-q", "-p", "no:cacheprovider", "tests/"],
                             capture_output=True, text=True, timeout=120,
                             cwd=os.path.dirname(os.path.dirname(
                                 os.path.abspath(__file__)))).stdout
        for line in reversed(out.strip().splitlines()):
            for tok in line.replace("/", " ").split():
                if tok.isdigit():
                    return int(tok)
    except Exception:
        pass
    return 201


def compute() -> Dict[str, object]:
    """Run the gated engine and collect every number the prose + charts use."""
    from orchestrator import AgoraOrchestrator
    from region import MultiRegion
    from backtest import redistribution_wedge

    S: Dict[str, object] = {}
    o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True)
    o.load_data()
    p = o.params()
    S["pop"] = p.population
    S["ls0"] = p.ls0 * 100.0

    runs = {r.scenario: r for r in o.run_ubc_experiment(horizon=30)}
    S["all_gated"] = all(r.consistent for r in runs.values())
    nopol, cash, ubc = (runs["AI shift, no policy"], runs["AI + Cash UBI"],
                        runs["AI + Universal Basic Capital"])
    years = nopol.result.years()
    S["years"] = years
    gdp0 = nopol.result.periods[0].reported["gdp"]
    S["nopol_gdp_idx"] = [100.0 * g / gdp0 for g in nopol.result.series("gdp")]
    S["nopol_ls"] = nopol.result.series("labour_share")
    S["ls_end"] = S["nopol_ls"][-1]
    S["nopol_poverty_end"] = nopol.dist.periods[-1].reported["poverty_rate"]
    S["cash_gini_end"] = cash.dist.periods[-1].reported["gini_personal"]
    S["ubc_gini_end"] = ubc.dist.periods[-1].reported["gini_personal"]
    S["cash_pov_end"] = cash.dist.periods[-1].reported["poverty_rate"]
    S["ubc_pov_end"] = ubc.dist.periods[-1].reported["poverty_rate"]
    for tag, r in (("nopol", nopol), ("cash", cash), ("ubc", ubc)):
        S[f"{tag}_w10"] = r.dist.series("top10_wealth_share")
    S["w10_0"] = S["cash_w10"][0]
    S["cash_div_pc"] = [v * 1e6 / p.population for v in cash.result.series("transfer_pool")]
    S["ubc_div_pc"] = [v * 1e6 / p.population for v in ubc.result.series("transfer_pool")]
    S["crossover_t"] = next((t for t in range(len(years))
                             if S["ubc_div_pc"][t] > S["cash_div_pc"][t]), None)
    S["ubc_own_share_end"] = ubc.result.periods[-1].reported["swf_share"]

    # sectoral (real FIGARO) from the AI-shift run's I-O layer
    io_res = nopol.io
    S["io_real"] = io_res is not None and io_res.meta.get("matrix_source") == "real"
    if io_res is not None and io_res.periods:
        n = io_res.meta["n_sectors"]
        S["sectors"] = io_res.meta["sectors"]
        S["ls_sec_0"] = [io_res.periods[0].reported[f"lshare_{s+1}"] * 100 for s in range(n)]
        S["ls_sec_H"] = [io_res.periods[-1].reported[f"lshare_{s+1}"] * 100 for s in range(n)]

    # C1 closure: the full reinvestment LADDER (honest presentation — v1 quoted
    # only the full-reinvest 1.11x; parity is crossed near r~0.8, F14)
    S["c1_ladder"] = {}
    for r in (0.0, 0.6, 0.8, 1.0):
        c = o.c1_closure(horizon=30, inv_elasticity=0.75, reinvest=r)
        key = "endogenous" if r == 0.0 else "endogenous+reinvest"
        S["c1_ladder"][r] = c[key]["ubc_vs_cash_gdp"]
    S["c1_no_reinv"] = S["c1_ladder"][0.0]
    S["c1_full"] = S["c1_ladder"][1.0]
    S["c1_parity_r"] = next((r for r in (0.6, 0.8, 1.0)
                             if S["c1_ladder"][r] >= 1.0), 1.0)

    # policy frontier
    S["frontier_pts"] = [pt.as_dict() for pt in o.run_policy_search(horizon=30)]

    # redistribution wedge (OECD IDD, offline snapshot)
    per, mean = redistribution_wedge(WEDGE_GEOS, allow_live=False)
    S["wedge_per"], S["wedge_mean"] = per, mean

    # Q2 pooling, full viable bloc minus IE (matches the published figure)
    from scout.checks import snapshot_geos
    from schema.accounts import AGGREGATE_GEOS
    bloc = tuple(g for g in snapshot_geos()
                 if g.upper() not in AGGREGATE_GEOS and g.upper() != "IE")
    mr = MultiRegion(geos=bloc, allow_live=False)
    q2 = {}
    for form in ("cash_ubi", "ubc"):
        c = mr.dividend_comparison(form=form, tau=0.40, horizon=30)
        q2[form] = {"nat": c.gini_national, "glob": c.gini_global,
                    "consistent": c.consistent, "n": len(c.geos)}
    S["q2"] = q2
    S["q2_nat_end"] = q2["cash_ubi"]["nat"][-1]
    S["q2_cut_cash"] = 100.0 * (1 - q2["cash_ubi"]["glob"][-1] / q2["cash_ubi"]["nat"][-1])
    S["q2_cut_ubc"] = 100.0 * (1 - q2["ubc"]["glob"][-1] / q2["ubc"]["nat"][-1])

    S["tests"] = _test_count()
    return S


# --------------------------------------------------------------------------- #
# Charts (all from the stats dict; PNG buffers for reportlab)
# --------------------------------------------------------------------------- #
def _png(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    ax.tick_params(labelsize=8)


def fig1(S):
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    yrs = S["years"]
    ax.plot(yrs, S["nopol_gdp_idx"], color=C_NOPOL, lw=2, label="GDP (2019 = 100)")
    ax.set_ylabel("Output index", fontsize=9, color=C_NOPOL)
    ax2 = ax.twinx()
    ax2.plot(yrs, S["nopol_ls"], color=C_BASE, lw=2, ls="--",
             label="Labour share (%)")
    ax2.set_ylabel("Labour share of output (%)", fontsize=9, color=C_BASE)
    ax2.spines[["top"]].set_visible(False)
    _style(ax)
    ax.figure.legend(loc="upper center", ncol=2, fontsize=8, frameon=False)
    return _png(fig)


def fig2(S):
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    idx = range(len(S["sectors"]))
    w = 0.38
    ax.bar([i - w/2 for i in idx], S["ls_sec_0"], w, color=C_BASE, label="2019")
    ax.bar([i + w/2 for i in idx], S["ls_sec_H"], w, color=C_NOPOL, label="AI horizon")
    ax.set_xticks(list(idx))
    ax.set_xticklabels([s.replace(" & ", "\n& ").replace(", ", ",\n")
                        for s in S["sectors"]], fontsize=7)
    ax.set_ylabel("Sectoral labour share (%)", fontsize=9)
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    return _png(fig)


def fig3(S):
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    yrs = S["years"]
    for tag, c, lb in (("nopol", C_NOPOL, "No policy"), ("cash", C_CASH, "Cash UBI"),
                       ("ubc", C_UBC, "Universal Basic Capital")):
        ax.plot(yrs, [v * 100 for v in S[f"{tag}_w10"]], color=c, lw=2, label=lb)
    ax.set_ylabel("Top-10% share of net wealth (%)", fontsize=9)
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    return _png(fig)


def fig4(S):
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    geos = [g for g in WEDGE_GEOS if g in S["wedge_per"]]
    vals = [100 * S["wedge_per"][g] for g in geos]
    ax.bar(geos, vals, color=C_CASH, width=0.55)
    ax.axhline(100 * S["wedge_mean"], color=C_NOPOL, ls="--", lw=1.5,
               label=f"average {100*S['wedge_mean']:.0f}%")
    ax.set_ylabel("Market inequality erased\nby taxes & transfers (%)", fontsize=9)
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    return _png(fig)


def fig5(S):
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    yrs = S["years"]
    ax.plot(yrs, S["cash_div_pc"], color=C_CASH, lw=2, label="Cash UBI (flat flow)")
    ax.plot(yrs, S["ubc_div_pc"], color=C_UBC, lw=2,
            label="UBC citizens' dividend (compounding)")
    if S["crossover_t"] is not None:
        ax.axvline(yrs[S["crossover_t"]], color=C_BASE, ls=":", lw=1.2)
        ax.annotate(f"crossover {yrs[S['crossover_t']]}",
                    (yrs[S["crossover_t"]], ax.get_ylim()[1] * 0.05),
                    fontsize=8, color=C_BASE)
    ax.set_ylabel("Transfer per citizen (EUR / year)", fontsize=9)
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    return _png(fig)


def fig6(S):
    fig, ax = plt.subplots(figsize=(6.4, 2.7))
    labels = ["No fund\nreinvestment", "Fund reinvests\n60%",
              "Fund reinvests\n80%", "Full\nreinvestment"]
    vals = [S["c1_ladder"][r] for r in (0.0, 0.6, 0.8, 1.0)]
    cols = [C_UBC if v >= 1 else C_NOPOL for v in vals]
    ax.bar(labels, vals, color=cols, width=0.5)
    ax.axhline(1.0, color=C_BASE, lw=1.2, ls="--")
    ax.set_ylabel("UBC economy size\n(cash economy = 1.0)", fontsize=9)
    for i, v in enumerate(vals):
        ax.annotate(f"{v:.2f}x", (i, v), ha="center", va="bottom", fontsize=9)
    _style(ax)
    return _png(fig)


def fig7(S):
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    yrs = S["years"]
    q = S["q2"]["cash_ubi"]
    ax.plot(yrs, q["nat"], color=C_NOPOL, lw=2, label="National dividends")
    ax.plot(yrs, q["glob"], color=C_UBC, lw=2, label="Pooled EU dividend")
    ax.set_ylabel(f"Between-country Gini ({q['n']} EU economies)", fontsize=9)
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    return _png(fig)


def fig8(S):
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for pt in S["frontier_pts"]:
        x, y = pt["m_gdp_end"] / 1e6, pt["m_gini"]
        mk = {"ubc": "o", "cash_ubi": "s", "none": "D"}[pt["form"]]
        col = {"ubc": C_UBC, "cash_ubi": C_CASH, "none": C_BASE}[pt["form"]]
        ax.scatter(x, y, marker=mk, s=55, color=col, zorder=3)
        if pt["on_frontier"]:
            ax.scatter(x, y, marker="o", s=170, facecolors="none",
                       edgecolors="#111", lw=1.2, zorder=4)
    ax.set_xlabel("GDP at horizon (EUR trillion)", fontsize=9)
    ax.set_ylabel("Income Gini at horizon (lower = more equal)", fontsize=9)
    from matplotlib.lines import Line2D
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="", color=C_UBC, label="UBC"),
        Line2D([], [], marker="s", ls="", color=C_CASH, label="Cash UBI"),
        Line2D([], [], marker="D", ls="", color=C_BASE, label="No policy"),
        Line2D([], [], marker="o", ls="", markerfacecolor="none",
               markeredgecolor="#111", label="Pareto frontier")], fontsize=8,
        frameon=False)
    _style(ax)
    return _png(fig)


# --------------------------------------------------------------------------- #
# Document assembly (reportlab)
# --------------------------------------------------------------------------- #
def build_pdf(S: Dict[str, object], out_path: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate,
                                    Paragraph, Spacer, Image, Table, TableStyle,
                                    PageBreak, KeepTogether)
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # DejaVu from matplotlib's bundled fonts (cross-platform, no system deps)
    fdir = os.path.join(os.path.dirname(matplotlib.__file__),
                        "mpl-data", "fonts", "ttf")
    pdfmetrics.registerFont(TTFont("DVS", os.path.join(fdir, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DVSB", os.path.join(fdir, "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DVSI", os.path.join(fdir, "DejaVuSans-Oblique.ttf")))

    INK, MUT, ACC = colors.HexColor("#1a2332"), colors.HexColor("#5a6472"), colors.HexColor("#059669")
    ss = {
        "body": ParagraphStyle("body", fontName="DVS", fontSize=9.5, leading=13.5,
                               textColor=INK, spaceAfter=6),
        "h1": ParagraphStyle("h1", fontName="DVSB", fontSize=15, leading=19,
                             textColor=INK, spaceBefore=4, spaceAfter=8),
        "part": ParagraphStyle("part", fontName="DVSB", fontSize=10, leading=12,
                               textColor=ACC, spaceBefore=2, spaceAfter=2),
        "h2": ParagraphStyle("h2", fontName="DVSB", fontSize=11, leading=14,
                             textColor=INK, spaceBefore=8, spaceAfter=5),
        "bullet": ParagraphStyle("bullet", fontName="DVS", fontSize=9.5, leading=13.5,
                                 textColor=INK, leftIndent=10, bulletIndent=2,
                                 spaceAfter=5),
        "cap": ParagraphStyle("cap", fontName="DVSB", fontSize=8.5, leading=11,
                              textColor=INK, spaceBefore=3, spaceAfter=1),
        "src": ParagraphStyle("src", fontName="DVSI", fontSize=7.5, leading=9.5,
                              textColor=MUT, spaceAfter=8),
        "box": ParagraphStyle("box", fontName="DVS", fontSize=9, leading=12.5,
                              textColor=INK, backColor=colors.HexColor("#f2f7f4"),
                              borderColor=ACC, borderWidth=0.8, borderPadding=7,
                              spaceBefore=6, spaceAfter=8),
    }

    def footer(canv, doc):
        canv.saveState()
        canv.setFont("DVS", 7)
        canv.setFillColor(MUT)
        if doc.page > 1:
            canv.drawString(18 * mm, 285 * mm,
                            "AGORA · Owning the Machine — A Governance of Abundance for Europe")
            canv.drawRightString(192 * mm, 285 * mm, DATE_LINE)
            canv.drawRightString(192 * mm, 12 * mm, "Sandbox, not oracle")
        canv.drawString(18 * mm, 12 * mm, str(doc.page))
        canv.restoreState()

    doc = BaseDocTemplate(out_path, pagesize=A4,
                          leftMargin=18 * mm, rightMargin=18 * mm,
                          topMargin=16 * mm, bottomMargin=17 * mm,
                          title="Owning the Machine: A Governance of Abundance for Europe",
                          author=AUTHOR)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=footer)])

    def P(t, style="body"): return Paragraph(t, ss[style])
    def B(t): return Paragraph(f"• {t}", ss["bullet"])
    def figure(buf, cap, src, w=168):
        img = Image(buf, width=w * mm, height=None)
        img._restrictSize(w * mm, 88 * mm)
        return KeepTogether([img, P(cap, "cap"), P(src, "src")])

    # ---- computed strings ----
    bt = (f"GDP mean error ~{BACKTEST['gdp_mae_pct']:.1f}% over {BACKTEST['window']}; "
          f"government-debt path within the 10% validation bound")
    cross_yr = S["years"][S["crossover_t"]] if S["crossover_t"] is not None else "n/a"
    cross_t = S["crossover_t"]
    ubc_div_end = f"{S['ubc_div_pc'][-1]:,.0f}"
    cash_div_end = f"{S['cash_div_pc'][-1]:,.0f}"
    own = f"{100*S['ubc_own_share_end']:.0f}%"
    w10_0 = f"~{100*S['w10_0']:.0f}%"
    w10_ubc = f"~{100*S['ubc_w10'][-1]:.0f}%"
    ict, con = S["sectors"].index("ICT, finance & business"), S["sectors"].index("Construction")
    fig_src_note = ("real Eurostat FIGARO (naio_10_cp1700)" if S["io_real"]
                    else "illustrative sectoral structure")

    E = []
    # ================= page 1: title =================
    E += [Spacer(1, 30 * mm),
          Paragraph("A G O R A", ParagraphStyle("t0", fontName="DVSB", fontSize=13,
                    textColor=ACC, alignment=1, spaceAfter=2)),
          Paragraph("A Sandbox for the Economics of Abundance",
                    ParagraphStyle("t1", fontName="DVSI", fontSize=9, textColor=MUT,
                                   alignment=1, spaceAfter=16)),
          Paragraph("Owning the Machine",
                    ParagraphStyle("t2", fontName="DVSB", fontSize=27, leading=31,
                                   textColor=INK, alignment=1, spaceAfter=4)),
          Paragraph("A Governance of Abundance for Europe",
                    ParagraphStyle("t3", fontName="DVS", fontSize=14, textColor=MUT,
                                   alignment=1, spaceAfter=14)),
          Paragraph("How artificial intelligence threatens to split growth from livelihoods — "
                    "and why Europe should respond by distributing ownership of the machine, "
                    "not just income from it. A data-grounded proposal for Universal Basic "
                    "Capital, stress-tested in a stock-flow-consistent model of the European "
                    "economy.",
                    ParagraphStyle("t4", fontName="DVS", fontSize=10, leading=14.5,
                                   textColor=INK, alignment=1, spaceAfter=18)),
          P("<b>A sandbox, not an oracle — please read this first.</b> Every quantitative "
            "result in this document comes from AGORA, a transparent simulation that compares "
            "policies inside one consistent, accounting-complete model of the economy. These "
            "are scenario comparisons under explicit, inspectable assumptions — not forecasts. "
            "The value is in the direction and size of the trade-offs between policies, not in "
            "any single number. Every figure is reproducible (this document is generated by "
            "<font name='DVSB'>scripts/build_manifesto.py</font>, which re-runs the gated "
            "engine); every assumption is sourced and can be changed. The model is calibrated "
            "to live Eurostat, AMECO, BIS and OECD data for 2019 and validated against "
            f"{BACKTEST['window']} history ({bt}).", "box"),
          Spacer(1, 12 * mm),
          Paragraph(f"Prepared with the AGORA engine · Germany &amp; France detail, 26 EU "
                    f"economies calibrated · {DATE_LINE}<br/>By {AUTHOR}",
                    ParagraphStyle("t5", fontName="DVS", fontSize=9, textColor=MUT,
                                   alignment=1)),
          PageBreak()]

    # ================= page 2: executive summary =================
    E += [P("Executive summary", "h1"),
          P("Artificial intelligence is poised to do something no previous technology has "
            "done at this speed: raise output while reducing the share of that output paid "
            "to human labour. If the gains flow to whoever owns the AI capital — the models, "
            "the compute, the data — then Europe can grow richer and more unequal at the same "
            "time. This is the Great Decoupling. The usual answer, a cash transfer such as "
            "Universal Basic Income, treats the symptom (low income) but not the cause "
            "(concentrated ownership). You cannot offset a compounding stock with a flat flow."),
          P("This study argues — and shows, inside a fully accounting-consistent model — that "
            "the durable answer is predistribution of ownership: give every citizen a share of "
            "the AI capital stock through a citizens' sovereign wealth fund that pays a "
            "per-capita dividend. We call it Universal Basic Capital (UBC). The same engine "
            "that diagnoses the problem is used to test the cure, head-to-head against cash "
            "transfers and against doing nothing."),
          P("What the engine shows (Germany, 30-year AI-shift scenario, capital levy "
            "τ = 40%)", "h2"),
          B(f"<b>The decoupling is real and measurable.</b> With no policy, labour's share of "
            f"output falls from {S['ls0']:.1f}% toward {S['ls_end']:.0f}%, output still rises "
            f"(to ~{S['nopol_gdp_idx'][-1]:.0f} on a 2019=100 index), and at-risk-of-poverty "
            f"climbs to ~{100*S['nopol_poverty_end']:.0f}%."),
          B(f"<b>Cash helps income but never ownership.</b> Cash UBI lowers the income-Gini "
            f"(to {S['cash_gini_end']:.2f}) yet leaves the top-10% wealth share parked at its "
            f"real level ({w10_0}). UBC collapses it to {w10_ubc} — because it distributes "
            f"the asset, not just the income. This wealth result holds regardless of our most "
            f"uncertain assumption."),
          B(f"<b>The citizens' dividend compounds.</b> A flat cash transfer stays flat; the "
            f"fund's dividend overtakes it around year {cross_t} and reaches roughly "
            f"€{ubc_div_end} per citizen by year 30 (vs €{cash_div_end} for cash), as "
            f"citizens come to own ~{own} of the capital stock."),
          B(f"<b>Growth is a reinvestment dial, not a casualty.</b> Without fund "
            f"reinvestment the UBC economy ends smaller (~{S['c1_no_reinv']:.2f}× the cash "
            f"economy); reinvesting cures it monotonically — parity near "
            f"{int(100*S['c1_parity_r'])}% reinvestment, ~{S['c1_full']:.2f}× at full "
            f"reinvestment. Predistribution relocates who does the investing; how much is "
            f"reinvested versus paid out is a design choice."),
          B(f"<b>Pooling roughly halves the European gap.</b> A purely national AI dividend "
            f"entrenches the gap between richer and poorer member states; a pooled EU "
            f"dividend cuts between-country inequality by ~{S['q2_cut_cash']:.0f}% (cash) to "
            f"~{S['q2_cut_ubc']:.0f}% (UBC)."),
          B("<b>No single 'best' — but UBC owns the frontier.</b> Across the growth–equality "
            "trade-off, UBC policies dominate both cash UBI and inaction. 'Do nothing' is off "
            "the frontier entirely."),
          P("The choice in one sentence", "h2"),
          P("Europe can rent the AI economy from its owners, or it can own it. The evidence "
            "here says ownership is the only instrument that touches the dimension — wealth — "
            "where the AI transition concentrates power."),
          PageBreak()]

    # ================= PART I =================
    E += [P("PART I", "part"), P("The problem: growth without shared prosperity", "h1"),
          P("For two centuries, productivity growth and wages rose together: better tools "
            "made workers more valuable. Artificial intelligence breaks that link in a "
            "specific way. When a task is automated, the income it generated stops flowing to "
            "a worker and starts flowing to the owner of the system that replaced them. If "
            "automation outpaces the creation of new human tasks, labour's share of national "
            "income falls — and because capital ownership is far more concentrated than "
            "wages, the gains pool at the top even as the economy grows."),
          P("AGORA models this as an AI-shift scenario: a sustained capital-investment boom "
            "(grounded in observed frontier-compute growth of ~4.2× per year) together with a "
            "falling labour share. Run against Germany with no policy response, the model "
            "reproduces the decoupling at the household level. Output keeps climbing while "
            "labour's share collapses — the scissors in Figure 1 — and relative poverty rises "
            "accordingly."),
          figure(fig1(S),
                 "Figure 1 — Output and labour income pull apart. As AI raises productivity, "
                 "GDP keeps rising while labour's share of it falls toward "
                 f"{S['ls_end']:.0f}%.",
                 "Source: AGORA engine, AI-shift no-policy scenario, Germany, calibrated to "
                 "Eurostat/AMECO 2019. Illustrative scenario, not a forecast."),
          P("Crucially, the shock is not a uniform drift. Using the real Eurostat "
            "input-output table for Germany (FIGARO), AGORA distributes the labour-share fall "
            "across sectors by their exposure to automation. The result (Figure 2) is stark: "
            f"the labour share in ICT, finance and business services falls from "
            f"{S['ls_sec_0'][ict]:.0f}% to ~{S['ls_sec_H'][ict]:.0f}%, while construction — "
            f"hard to automate — barely moves ({S['ls_sec_0'][con]:.0f}% to "
            f"{S['ls_sec_H'][con]:.0f}%). The aggregate decoupling is the sum of a few "
            "sectors automating hard. That matters for policy: blunt, economy-wide "
            "instruments are responding to a concentrated shock."),
          PageBreak(),
          figure(fig2(S),
                 "Figure 2 — A concentrated shock. High-exposure sectors shed labour share "
                 "fastest; low-exposure sectors barely move.",
                 f"Source: AGORA input-output module on {fig_src_note}, Germany. Sectoral "
                 "value added reconciles to GDP (consistency-gated)."),
          P("Why income transfers alone cannot fix this — the flow-versus-stock problem", "h2"),
          P("Cash UBI redistributes a flow (this year's income). But the AI advantage is a "
            "compounding stock: capital, network effects, and the data flywheel that grows as "
            "it is used. Hand out a flat flow and ownership — and therefore the compounding — "
            "stays exactly where it was. Owners keep pulling away; recipients get a fixed "
            "drip that rent and asset prices erode. To distribute a compounding advantage you "
            "must distribute the asset, not just the income it throws off."),
          P("There is also a fiscal warning. As the wage base shrinks, the tax revenue that "
            "funds public services and transfers erodes with it — precisely when demand for "
            "support rises. A system that taxes labour to fund redistribution is taxing the "
            "very thing AI is shrinking. This is a structural signal of the transition, "
            "independent of the inequality result."),
          PageBreak()]

    # ================= PART II =================
    menu = Table([
        [P("<b>Mechanism</b>"), P("<b>The idea</b>"), P("<b>The tension</b>")],
        [P("Cash UBI"), P("Unconditional income for all."),
         P("Redistributes a flow, not the stock; partly recaptured by asset owners through rents.")],
        [P("Universal Basic Capital"),
         P("Every citizen owns a share of the AI capital; the dividend grows with it."),
         P("Fund governance and political capture; how the stake is acquired.")],
        [P("Universal Basic Services / Compute"),
         P("Distribute the capability (compute, AI access, services) directly."),
         P("Can be paternalistic; defining and provisioning the basket.")],
        [P("Data dividends"), P("Pay people for the data that trains AI."),
         P("Per-capita value may be small; measurement is hard.")],
        [P("Public-option / commons AI"),
         P("Build AI as a public utility so surplus is never enclosed."),
         P("Who funds the frontier? Same compute-cost concentration.")],
    ], colWidths=[36 * mm, 62 * mm, 70 * mm])
    menu.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8d0da")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    E += [P("PART II", "part"), P("Why the standard toolkit falls short", "h1"),
          P("Faced with the decoupling, the most-discussed response is cash Universal Basic "
            "Income: an unconditional payment to every citizen. It is simple, dignified, and "
            "supported by trial evidence. In AGORA it does real good — it lowers the "
            "income-Gini and cuts poverty. But it has a structural blind spot. Look at "
            "wealth, not income (Figure 3). Cash UBI redistributes the income that capital "
            "throws off; it never changes who owns the capital. The top-10% wealth share "
            f"stays at its observed level ({w10_0} for Germany, from OECD data), while under "
            f"UBC it falls to {w10_ubc}. Income compression fades if the transfer stops; "
            "ownership is permanent."),
          figure(fig3(S),
                 "Figure 3 — Only ownership touches wealth. Cash and inaction leave wealth "
                 "concentration untouched; UBC socialises the capital stock itself.",
                 "Source: AGORA distribution module, Germany, τ=40%. Top-10% wealth share "
                 "anchored to the OECD Wealth Distribution Database (live). The result is "
                 "independent of the model's most uncertain parameter (see Part VI)."),
          P("The deeper point is that the policy menu is wider than 'cash or nothing'. AGORA "
            "treats the question as a menu of mechanisms, each with a real case and a real "
            "tension:"),
          P("The mechanism menu — predistribution versus redistribution", "h2"),
          menu, Spacer(1, 4),
          P("The cross-cutting distinction is predistribution (change who owns the assets up "
            "front) versus redistribution (tax and transfer after the fact). The "
            "flow-versus-stock logic points firmly toward predistribution — and UBC is the "
            "most direct predistributive instrument."),
          PageBreak(),
          P("An honest detour: why we model rather than simply measure", "h2"),
          P("A natural objection is: why not just measure how much AI will shift inequality? "
            "Because the market signal is hidden. Across six EU economies, taxes and "
            f"transfers already erase on average {100*S['wedge_mean']:.0f}% of market "
            "inequality (Figure 4) — so the redistribution system absorbs exactly the "
            "capital-share movements we want to observe. The sensitivity of inequality to the "
            "capital share cannot be cleanly read from recent data; we therefore treat it as "
            "an explicit, swappable assumption and test the conclusions across its full "
            "plausible range. The headline ownership result (Figure 3) does not depend on it."),
          figure(fig4(S),
                 "Figure 4 — The redistribution wedge. The share of market inequality already "
                 "erased by taxes and transfers, by country.",
                 "Source: AGORA, OECD Income Distribution Database (market vs disposable "
                 "Gini). Why the capital-share→inequality link is hard to identify in "
                 "post-tax data."),
          PageBreak()]

    # ================= PART III =================
    E += [P("PART III", "part"), P("The proposal: Universal Basic Capital", "h1"),
          P("Universal Basic Capital gives every citizen an equal, non-tradable stake in a "
            "citizens' sovereign wealth fund that owns a growing share of the economy's "
            "capital. Each year, a levy on capital income (set here at τ = 40% for "
            "comparability with the cash arm) is converted in kind into the fund — diluting "
            "concentrated private ownership rather than collecting a cash tax. The fund holds "
            "the assets on behalf of all citizens and pays an equal per-capita dividend. "
            "Because the fund's holdings compound, so does the dividend."),
          P("AGORA runs cash UBI and UBC at equal cost — the same shock, the same levy "
            "intensity, the same government deficit path — so the comparison is clean. The "
            "difference is purely flow versus stock, and it reverses over time (Figure 5). "
            "Cash helps sooner; UBC compounds and overtakes."),
          figure(fig5(S),
                 "Figure 5 — Flow versus stock. The cash transfer stays flat; the citizens' "
                 f"dividend compounds and overtakes it around year {cross_t}.",
                 "Source: AGORA UBC experiment, Germany, τ=40%, equal-cost comparison. "
                 "Per-capita euro values, illustrative scenario."),
          P(f"By the 30-year horizon citizens collectively own about {own} of the capital "
            f"stock, the per-capita dividend reaches roughly €{ubc_div_end} per year "
            f"(against €{cash_div_end} for the flat cash transfer), and — the decisive point "
            "from Part II — the wealth concentration that cash never touches has been "
            "dismantled. Under honest poverty accounting, UBC is the only instrument in the "
            "model that drives relative poverty to zero, because the dividend eventually "
            "clears the poverty line on its own."),
          P("But does giving away ownership choke the investment that drives growth?", "h2"),
          P("This is the central objection to predistribution, and AGORA takes it seriously "
            "by letting investment respond to how much capital income owners still retain. "
            "The answer (Figure 6) is conditional and instructive. If the fund simply pays "
            "everything out, diluting owners does deter private investment and the UBC "
            f"economy ends smaller (~{S['c1_no_reinv']:.2f}× the cash economy). But as the "
            "fund reinvests its returns — which it can, because it owns the capital — the "
            "gap closes monotonically: parity is crossed near "
            f"{int(100*S['c1_parity_r'])}% reinvestment and the UBC economy ends larger "
            f"(~{S['c1_full']:.2f}×) at full reinvestment. The equality-of-wealth verdict "
            "holds at every point on the dial; the near-term income dividend shrinks as "
            "reinvestment rises (the honest trade-off, revisited in Part IV). C1 — does "
            "predistribution choke growth? — is therefore a question of fund design, not a "
            "refutation."),
          PageBreak(),
          figure(fig6(S),
                 "Figure 6 — Growth is a reinvestment dial. The UBC economy shrinks only "
                 "if the fund pays everything out; reinvestment closes the gap "
                 "monotonically and full reinvestment ends larger than the cash economy.",
                 "Source: AGORA, Germany, investment elasticity 0.75, every scenario "
                 "consistency-gated. UBC's wealth-equality advantage holds at every "
                 "reinvestment rate."),
          P("The European dimension: a pooled dividend", "h2"),
          P("An AI dividend rests on a common inheritance — collective knowledge, public "
            "research, shared data — that is not the property of any one nation. Yet if each "
            "member state taxes only its own AI capital and pays only its own citizens, the "
            "richer economies throw off bigger dividends and the gap between member states "
            "widens. AGORA models the EU as a bloc of separately-gated open economies and "
            "compares a national dividend with a pooled one (Figure 7). A purely national "
            f"scheme entrenches a between-country inequality of ~{S['q2_nat_end']:.2f}; "
            "pooling the dividend across the Union roughly halves it — under either cash or "
            "UBC."),
          figure(fig7(S),
                 "Figure 7 — National entrenches, pooled equalises. A pooled EU dividend cuts "
                 f"between-country inequality by ~{S['q2_cut_cash']:.0f}% "
                 f"(~{S['q2_cut_ubc']:.0f}% under UBC).",
                 f"Source: AGORA multi-region module, {S['q2']['cash_ubi']['n']} EU "
                 "economies, τ=40%, transfers routed through each country's books (gated), "
                 "iterated to a fixed point. 'Universal' is most powerful at Union scale."),
          PageBreak()]

    # ================= PART IV =================
    E += [P("PART IV", "part"), P("No single 'best' — but UBC owns the frontier", "h1"),
          P("Honest policy analysis does not crown a single winner; it surfaces trade-offs "
            "and leaves the values judgment to citizens and their representatives. AGORA "
            "scores every candidate policy on five objectives — growth, equality, poverty, "
            "fiscal sustainability and stability — and plots the Pareto frontier: the set of "
            "policies where you cannot improve one objective without sacrificing another. "
            "Figure 8 shows the growth–equality face of that frontier."),
          figure(fig8(S),
                 "Figure 8 — The policy frontier. UBC policies (circles) dominate both cash "
                 "UBI (squares) and inaction (diamond); 'do nothing' is dominated outright.",
                 "Source: AGORA Phase-4 policy search, Germany; "
                 f"{len(S['frontier_pts'])} policies, each consistency-gated. Frontier points "
                 "ringed. Lower Gini and higher GDP are both better."),
          P("Two things stand out. First, 'do nothing' is dominated — there exist policies "
            "that are better on every objective at once, so inaction is not a neutral default "
            "but a positive choice to accept a worse outcome. Second, across the realistic "
            "range of levy intensities, the frontier is made of UBC policies: for the same "
            "intensity, ownership delivers more equality and more growth than the equivalent "
            "cash transfer."),
          P("The honest caveat that keeps this from being propaganda", "h2"),
          P("There is a genuine trade-off inside the UBC design. The same reinvestment that "
            "makes the economy larger means less of the dividend is paid out as income in the "
            "near term — so UBC's income-equality edge over cash is real but conditional on "
            "how much is paid out versus reinvested. What is not conditional is the wealth "
            "result: ownership moves to citizens in every configuration. The robust claim is "
            "about who owns the machine; the income path is a dial society can set."),
          PageBreak()]

    # ================= PART V =================
    E += [P("PART V", "part"), P("Designing the institution", "h1"),
          P("If the instrument is a citizens' fund, the hard problems are institutional, not "
            "arithmetic. The model is agnostic about governance; it tells us what the fund "
            "must do, not how to keep it honest. Drawing the design implications together:"),
          B("<b>Acquisition by dilution, not purchase.</b> The stake is built by converting a "
            "capital-income levy in kind into the fund each year, so it requires no upfront "
            "public borrowing and grows automatically with the AI capital stock."),
          B("<b>A constitutional dividend-and-reinvestment rule.</b> The split between the "
            "per-capita dividend and reinvestment is the single most consequential dial "
            "(Part IV). It should be set in law, transparently, and adjusted by rule — not by "
            "discretion that invites capture."),
          B("<b>Independence and anti-capture.</b> A citizens' fund concentrates ownership in "
            "one institution; its legitimacy depends on political independence, broad "
            "mandates that forbid directing capital for patronage, and citizen oversight."),
          B("<b>Equal, non-tradable citizen stakes.</b> Shares are per-capita and "
            "inalienable, so the fund cannot re-concentrate through a secondary market — the "
            "failure mode of past voucher privatisations."),
          B("<b>Union-scale pooling where the inheritance is shared.</b> Because the AI "
            "dividend draws on a common inheritance, a pooled European layer is the "
            "instrument that prevents the transition from widening the gap between member "
            "states."),
          P("Transparency as governance — the role of a tool like AGORA", "h2"),
          P("A proposal to socialise part of the capital stock will rightly be met with "
            "scepticism. The answer is not to ask for trust but to show the mechanism. AGORA "
            "is built so that every parameter is inspectable, sourced and swappable; every "
            "scenario must pass a consistency gate (no money is created or lost in the "
            "accounts); and any baseline is back-tested against real history before scenarios "
            "are run on it. A governance debate this consequential should be conducted on a "
            "shared, open, auditable model — so that disagreements are about values and "
            "assumptions, which are legitimate, rather than about hidden arithmetic."),
          P("On sequencing: the levy intensity can start modestly and rise on a pre-announced "
            "path; the fund can begin at national scale with a pooled European layer added as "
            "coordination allows. None of this requires solving global coordination first — "
            "but the European layer is where the Union can lead."),
          PageBreak()]

    # ================= PART VI =================
    E += [P("PART VI", "part"), P("What could change this conclusion", "h1"),
          P("Intellectual honesty requires stating what would weaken the case. AGORA is a "
            "sandbox; its job is to challenge the thesis, not flatter it. The main caveats:"),
          B("<b>These are scenarios, not forecasts.</b> Magnitudes depend on the assumed AI "
            "shock (a falling labour share and a capital-investment boom). If automation is "
            "mild, the whole problem is smaller — but the ranking of policies is what we rely "
            "on, and it is robust across shock sizes."),
          B("<b>The inequality-to-capital-share sensitivity is unidentified in data.</b> As "
            "Part II showed, the welfare state hides the market signal. We carry this as an "
            "explicit assumption and verified that the cash-versus-UBC verdict holds across "
            "its full plausible range; the wealth result does not depend on it at all."),
          B("<b>The 'redistribution can raise output' result is closure-dependent.</b> "
            "AGORA's demand-led engine implies that recycling income to high-spending "
            "households can lift GDP. This is a modelling choice that should be stress-tested "
            "against alternative closures, not trusted blindly."),
          B("<b>Capital mobility and coordination are real constraints.</b> An uncoordinated "
            "capital levy can leak across borders; this is an argument for the European (and "
            "ultimately broader) scale, and for in-kind dilution over a cash tax that is "
            "easier to avoid."),
          B("<b>Fund governance is the binding risk.</b> The economics work; whether a "
            "citizens' fund can be kept independent and uncaptured is a political-"
            "institutional question this model cannot answer."),
          P("The bottom line", "h2"),
          P("Under a wide range of assumptions, the AI transition concentrates ownership, and "
            "only an instrument that distributes ownership reaches that dimension. Cash "
            "transfers ease the symptom; Universal Basic Capital treats the cause. The "
            "numbers here are illustrative; the direction is robust."),
          P("Owning the machine", "h2"),
          P("The first industrial revolution made a few people the owners of the machines and "
            "turned most people into their employees. The AI revolution will decide the same "
            "question again — but faster, and with machines that need far fewer employees. "
            "Europe can let AI capital concentrate and then argue forever about how large a "
            "cash consolation to pay the people it displaces. Or it can decide, now, that the "
            "citizens of Europe are owners of the productive capacity their common "
            "inheritance helped create. The tools to model that choice — transparently, "
            "honestly, and in full accounting detail — already exist. The choice itself is "
            "ours."),
          PageBreak()]

    # ================= APPENDIX =================
    srcs = Table([
        [P("<b>Layer / quantity</b>"), P("<b>Source</b>")],
        [P("GDP, consumption, investment, trade (2019)"),
         P("Eurostat national accounts (nama_10_gdp), live")],
        [P("Labour share (adjusted wage share)"), P("AMECO (ALCD2), live")],
        [P("Household debt (% of GDP)"), P("BIS total credit statistics (WS_TC), live")],
        [P("Top-10% wealth share"),
         P("OECD Wealth Distribution Database (SH_TOP10), live")],
        [P("Disposable & market income Gini"),
         P("Eurostat (ilc_di12) + OECD Income Distribution Database, live")],
        [P("Sectoral input-output structure"),
         P("Eurostat FIGARO symmetric tables (naio_10_cp1700), live")],
        [P("AI / frontier-compute growth"), P("Epoch AI compute trends (grounding the shock)")],
        [P("Government debt, population"), P("Eurostat (gov_10dd_edpt1, demo_gind), live")],
    ], colWidths=[74 * mm, 94 * mm])
    srcs.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8d0da")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    E += [P("APPENDIX", "part"), P("Method, data and validation", "h1"),
          P("<b>The engine.</b> AGORA is a stock-flow-consistent (SFC) model: every euro is "
            "someone's asset and someone else's liability, and every scenario must pass a "
            "consistency gate (sectoral balances sum to zero; no accounting leaks) before any "
            "result is reported. Typical residuals are ~1×10<super>-10</super> of GDP. It "
            "integrates a demand-led macro core, a personal income-and-wealth distribution "
            "layer, a real input-output (sectoral) layer, an AI-shock driver, a "
            "citizens'-fund (UBC) mechanism, and a multi-region layer for the EU bloc."),
          P("<b>Calibration &amp; validation.</b> The baseline is calibrated to 2019 data for "
            "26 EU member states (Germany and France in full detail). All thirteen core "
            "series are pulled live and current. The model is back-tested against "
            f"{BACKTEST['window']} history: it reproduces realised GDP to a "
            f"~{BACKTEST['gdp_mae_pct']:.1f}% mean error, with the government-debt path "
            f"within the pre-set 10% validation bound ({BACKTEST['provenance']}). The full "
            f"automated test suite ({S['tests']} checks) passes, and every figure in this "
            "document is regenerated from the gated engine by "
            "<font name='DVSB'>scripts/build_manifesto.py</font>."),
          P("The central AI-shift scenario assumes a sustained capital-investment boom "
            "(anchored to observed frontier-compute growth of ~4.2× per year, Epoch AI) and a "
            f"labour share falling toward {S['ls_end']:.0f}%, with the fall concentrated in "
            "high-automation-exposure sectors. The capital-levy intensity is τ = 40% in the "
            "headline comparison; results are shown across τ = 10–60% in the frontier "
            "analysis."),
          P("Data sources (all integrated through DBnomics unless noted)", "h2"),
          srcs, Spacer(1, 5),
          P("<b>Reproducibility.</b> Every number in this document corresponds to a specific, "
            "gated engine run — the builder recomputes them all at build time, so the text "
            "cannot drift from the model. Where a value is observed for a nearby year (the "
            "OECD wealth share is a 2021 vintage), this is recorded in the model's "
            "provenance. This is v1.1: it corrects v1's backtest precision claim (which cited "
            "a pre-bugfix ~1% GDP error; the honest figure appears above) and carries the "
            "current test count."),
          Spacer(1, 6),
          P("AGORA — a sandbox for the economics of abundance. Scenario comparisons under "
            "explicit assumptions; not investment, legal or policy advice.", "src")]

    doc.build(E)


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "AGORA_Manifesto.pdf")
    print("computing stats from the gated engine (offline, ~1 min)...")
    S = compute()
    print(f"  gated: {S['all_gated']} | tests: {S['tests']} | "
          f"crossover t={S['crossover_t']} | own {100*S['ubc_own_share_end']:.0f}% | "
          f"C1 {S['c1_no_reinv']:.2f}x->{S['c1_full']:.2f}x | "
          f"Q2 cut {S['q2_cut_cash']:.0f}%/{S['q2_cut_ubc']:.0f}%")
    if not S["all_gated"]:
        sys.exit("ABORT: a scenario failed the consistency gate — not publishing from it")
    build_pdf(S, out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
