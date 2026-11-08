#!/usr/bin/env python3
"""Reproducible builder for AGORA_Manifesto.pdf ("Who Owns the Machine?", v1.2)
and the two README charts (AGORA_tradeoff_DE.png, AGORA_fiscal_EU.png).

Every engine-derived number and every figure is regenerated from the gated
engine at build time; the prose contains no hand-typed results. Two inputs are
read from files the engine wrote earlier, because they take too long to rerun
here: the 2011-2019 backtest and multipliers (docs/validation-2026-11.json,
`python scripts/validate.py`) and the Monte Carlo (docs/robustness-2026-11.json,
`python scripts/robustness.py`). v1.2 rewrites the thesis around what survived
the Phase 7 re-validation (docs/FINDINGS-LEDGER.md).

Usage:  python scripts/build_manifesto.py [out.pdf]     (offline, a few minutes)
Deps :  pip install reportlab matplotlib
"""
from __future__ import annotations

import io
import json
import os
import statistics
import subprocess
import sys
from typing import Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TITLE = "Who Owns the Machine?"
SUBTITLE = "AI, the labour share and Europe's policy choices"
DATE_LINE = "November 2026 (v1.2, corrected)"
AUTHOR = "Branislav Ambroz"
VALIDATION_JSON = os.path.join(ROOT, "docs", "validation-2026-11.json")
ROBUSTNESS_JSON = os.path.join(ROOT, "docs", "robustness-2026-11.json")

# categorical slots (dataviz reference palette, light mode; validated all-pairs
# for three series; aqua is below 3:1 on white, so every line is direct-labelled)
C_CASH, C_NOPOL, C_UBC = "#2a78d6", "#eb6834", "#1baf7a"
C_REF, C_GRID = "#8a8984", "#e4e3df"
INK, INK2 = "#0b0b0b", "#52514e"
ARM = {"none": ("No policy", C_NOPOL), "cash": ("Cash UBI", C_CASH),
       "ubc": ("Universal Basic Capital", C_UBC)}
WEDGE_GEOS = ["DE", "FR", "IT", "ES", "NL", "SE"]
LADDER = (0.0, 0.3, 0.6, 1.0)


def _test_count() -> int:
    try:
        out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only",
                              "-q", "-p", "no:cacheprovider", "tests/"],
                             capture_output=True, text=True, timeout=180, cwd=ROOT).stdout
        for line in reversed(out.strip().splitlines()):
            for tok in line.replace("/", " ").split():
                if tok.isdigit():
                    return int(tok)
    except Exception:
        pass
    return 0


def _load(path: str) -> dict:
    if not os.path.exists(path):
        sys.exit(f"ABORT: {os.path.relpath(path, ROOT)} is missing; run the script that writes it")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# Numbers
# --------------------------------------------------------------------------- #
def compute() -> Dict[str, object]:
    """Run the gated engine and collect every number the prose and charts use."""
    from orchestrator import AgoraOrchestrator
    from region import MultiRegion
    from backtest import redistribution_wedge
    from proposals import run_library
    from scout.checks import snapshot_geos
    from schema.accounts import AGGREGATE_GEOS
    from schema.coverage import EXCLUDED, usable

    S: Dict[str, object] = {}
    gated: List[bool] = []
    geos = [g for g in snapshot_geos() if g.upper() not in AGGREGATE_GEOS and usable(g)]
    S["geos"], S["excluded"] = geos, sorted(EXCLUDED)

    # ---- Germany: the pinned experiment (AI shift; 40% levy as cash or claim) ----
    o = AgoraOrchestrator(geo="DE", year=2019, allow_live=False, strict=True)
    o.load_data()
    pop = o.params().population
    runs = {r.scenario: r for r in o.run_ubc_experiment(horizon=30)}
    triad = {r.scenario: r for r in o.run_triad(horizon=30)}
    gated += [r.consistent for r in list(runs.values()) + list(triad.values())]
    arms = {"none": runs["AI shift, no policy"], "cash": runs["AI + Cash UBI"],
            "ubc": runs["AI + Universal Basic Capital"]}
    S["years"] = arms["none"].result.years()

    def real_pc(r, key):          # MEUR at current prices -> EUR per person, 2019 prices
        return [s.reported.get(key, 0.0) / s.reported.get("price_level", 1.0) * 1e6 / pop
                for s in r.result.periods]

    A = {}
    for tag, r in arms.items():
        per, dist = r.result.periods, r.dist.periods
        c = real_pc(r, "consumption")
        A[tag] = {"c_pc": c, "c_avg": statistics.mean(c[1:]),
                  "pay_pc": real_pc(r, "transfer_pool"),
                  "w10": [d.reported["top10_wealth_share"] for d in dist],
                  "gini": [d.reported["gini_personal"] for d in dist],
                  "pov": [d.reported["poverty_rate"] for d in dist],
                  "gdp_idx": per[-1].reported["gdp_real"] / per[0].reported["gdp_real"],
                  "gni_idx": per[-1].reported["gni_real"] / per[0].reported["gni_real"],
                  "cap_idx": per[-1].reported["capital"] / per[0].reported["capital"],
                  "debt_end": per[-1].reported["gov_debt_gdp"],
                  "own_10y": per[10].reported.get("swf_share", 0.0),
                  "own_end": per[-1].reported.get("swf_share", 0.0),
                  "wealth_pc_end": per[-1].reported.get("citizen_wealth_pc", 0.0) * 1e6,
                  "reach": per[-1].reported.get("ai_rent_reached_share", 0.0)}
    S["A"] = A
    S["crossover"] = next((S["years"][t] for t in range(2, len(S["years"]))
                           if A["ubc"]["pay_pc"][t] > A["cash"]["pay_pc"][t]), None)

    npl = arms["none"].result.periods
    S["ls"] = [100.0 * s.reported["labour_share"] / (100.0 if s.reported["labour_share"] > 1 else 1.0)
               for s in npl]
    S["gdp_path"] = [100.0 * s.reported["gdp_real"] / npl[0].reported["gdp_real"] for s in npl]
    S["gni_path"] = [100.0 * s.reported["gni_real"] / npl[0].reported["gni_real"] for s in npl]
    e = npl[-1].reported
    S["rent_end"], S["abroad_end"] = e["ai_rent"] / e["gdp"], e["ai_rent_abroad"] / e["gdp"]
    bp = triad["Baseline"].result.periods
    S["base_gdp_idx"] = bp[-1].reported["gdp_real"] / bp[0].reported["gdp_real"]

    io_res = arms["none"].io
    S["io_real"] = io_res is not None and io_res.meta.get("matrix_source") == "real"
    if io_res is not None and io_res.periods:
        n = io_res.meta["n_sectors"]
        S["sectors"] = io_res.meta["sectors"]
        S["ls_sec_0"] = [io_res.periods[0].reported[f"lshare_{s+1}"] * 100 for s in range(n)]
        S["ls_sec_H"] = [io_res.periods[-1].reported[f"lshare_{s+1}"] * 100 for s in range(n)]

    # ---- the fund's reinvestment dial ----
    L = {}
    for rv in LADDER:
        rr = {r.scenario: r for r in o.run_ubc_experiment(horizon=30, inv_elasticity=0.75,
                                                          reinvest=rv)}
        u, c = rr["AI + Universal Basic Capital"], rr["AI + Cash UBI"]
        gated += [u.consistent, c.consistent]
        gi = lambda r: r.result.periods[-1].reported["gdp_real"] / r.result.periods[0].reported["gdp_real"]
        L[rv] = {"gdp_ratio": gi(u) / gi(c),
                 "gini_ubc": u.dist.periods[-1].reported["gini_personal"],
                 "gini_cash": c.dist.periods[-1].reported["gini_personal"],
                 "div_end": real_pc(u, "transfer_pool")[-1]}
    S["ladder"] = L

    # ---- real proposals against no policy (DE) ----
    S["props"] = [{"key": r.key, "name": r.name, "ok": r.consistent, **(r.metrics or {})}
                  for r in run_library(o)]
    gated += [r["ok"] for r in S["props"]]

    # ---- the fiscal base, no policy, every usable member ----
    F = {}
    for g in geos:
        og = o if g == "DE" else AgoraOrchestrator(geo=g, year=2019, allow_live=False)
        if g != "DE":
            og.load_data()
        r = triad["AI shift, no policy"] if g == "DE" else \
            {x.scenario: x for x in og.run_triad(horizon=30)}["AI shift, no policy"]
        gated.append(r.consistent)
        p0, p1 = r.result.periods[0], r.result.periods[-1]

        def rev(pp):
            t, y = pp.tfm, pp.reported["gdp"]
            k = sum(t.get(n, {}).get("government", 0.0) for n in ("tax_capital", "tax_capital_base"))
            return t["tax_income"]["government"] / y, k / y
        lt0, kt0 = rev(p0)
        lt1, kt1 = rev(p1)
        F[g] = {"debt0": p0.reported["gov_debt_gdp"], "debt1": p1.reported["gov_debt_gdp"],
                "lt0": lt0, "lt1": lt1, "kt0": kt0, "kt1": kt1,
                "tl0": p0.reported["tax_rate_labour"], "tl1": p1.reported["tax_rate_labour"]}
    S["F"] = F
    med = lambda k: statistics.median(v[k] for v in F.values())
    S["debt0_med"], S["debt1_med"] = med("debt0"), med("debt1")
    S["n150"] = sum(v["debt1"] > 150 for v in F.values())
    S["n_rise"] = sum(v["debt1"] > v["debt0"] for v in F.values())
    S["lt0_med"], S["lt1_med"] = med("lt0"), med("lt1")

    # ---- pooling across the usable members ----
    mr = MultiRegion(geos=tuple(geos), allow_live=False)
    q2 = {}
    for form in ("cash_ubi", "ubc"):
        c = mr.dividend_comparison(form=form, tau=0.40, horizon=30)
        gated.append(c.consistent)
        q2[form] = {"nat": list(c.gini_national), "glob": list(c.gini_global), "n": len(c.geos),
                    "tr": {k: v * 1e6 for k, v in c.pooling_transfer_pc.items()}}
        q2[form]["cut_end"] = 100.0 * (1 - q2[form]["glob"][-1] / q2[form]["nat"][-1])
        q2[form]["cut_10y"] = 100.0 * (1 - q2[form]["glob"][10] / q2[form]["nat"][10])
    S["q2"] = q2

    per, mean = redistribution_wedge(WEDGE_GEOS, allow_live=False)
    S["wedge_per"], S["wedge_mean"] = per, mean
    S["val"], S["rob"] = _load(VALIDATION_JSON), _load(ROBUSTNESS_JSON)
    S["tests"] = _test_count()
    S["all_gated"] = all(gated)
    return S


# --------------------------------------------------------------------------- #
# Charts (all from the stats dict)
# --------------------------------------------------------------------------- #
def _png(fig, path=None, dpi=170) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    if path:
        fig.savefig(path, format="png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


def _years_axis(ax, yrs):
    ax.set_xticks([y for y in range(2020, yrs[-1] + 1, 10)] + [yrs[-1]])


def _style(ax, title=None):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(C_REF)
    ax.grid(axis="y", color=C_GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=7.5, colors=INK2)
    if title:
        ax.set_title(title, fontsize=8.5, color=INK, loc="left", pad=6)


def _label_end(ax, x, y, text, dy=0.0):
    ax.annotate(text, (x, y), xytext=(4, dy), textcoords="offset points",
                fontsize=7, color=INK2, va="center")


def _arms(ax, S, key, scale=1.0, tags=("none", "cash", "ubc"), labels=True, offsets=None):
    yrs = S["years"]
    for tag in tags:
        name, col = ARM[tag]
        ys = [v * scale for v in S["A"][tag][key]]
        ax.plot(yrs, ys, color=col, lw=1.8, label=name)
        if labels:
            _label_end(ax, yrs[-1], ys[-1], name.replace("Universal Basic Capital", "UBC"),
                       (offsets or {}).get(tag, 0.0))
    ax.set_xlim(yrs[0], yrs[-1] + 7)
    _years_axis(ax, yrs)


def fig_shock(S):
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 2.6))
    yrs = S["years"]
    a.plot(yrs, S["ls"], color=C_NOPOL, lw=1.8)
    _style(a, "Labour share of income (%)")
    b.plot(yrs, S["gdp_path"], color=C_NOPOL, lw=1.8)
    b.plot(yrs, S["gni_path"], color=C_NOPOL, lw=1.8, ls="--")
    _label_end(b, yrs[-1], S["gdp_path"][-1], "real GDP")
    _label_end(b, yrs[-1], S["gni_path"][-1], "real national income")
    b.axhline(100, color=C_REF, lw=0.8, ls=":")
    b.set_xlim(yrs[0], yrs[-1] + 11)
    _years_axis(a, yrs)
    _years_axis(b, yrs)
    _style(b, "Germany, no policy (2019 = 100)")
    fig.tight_layout(w_pad=2.5)
    return _png(fig)


def fig_sectors(S):
    fig, ax = plt.subplots(figsize=(7.0, 2.7))
    idx = range(len(S["sectors"]))
    w = 0.36
    ax.bar([i - w / 2 - 0.01 for i in idx], S["ls_sec_0"], w, color=C_REF, label="2019")
    ax.bar([i + w / 2 + 0.01 for i in idx], S["ls_sec_H"], w, color=C_NOPOL,
           label=f"{S['years'][-1]}, AI shift, no policy")
    ax.set_xticks(list(idx))
    ax.set_xticklabels([s.replace(" & ", "\n& ").replace(", ", ",\n") for s in S["sectors"]],
                       fontsize=7)
    ax.legend(fontsize=7.5, frameon=False, loc="upper left")
    _style(ax, "Labour share by sector, Germany (%)")
    return _png(fig)


def fig_fiscal(S, path=None):
    F = S["F"]
    order = sorted(F, key=lambda g: F[g]["debt1"])
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    for i, g in enumerate(order):
        ax.plot([F[g]["debt0"], F[g]["debt1"]], [i, i], color=C_GRID, lw=2.2, zorder=1)
    ax.scatter([F[g]["debt0"] for g in order], range(len(order)), s=26, color=C_REF,
               zorder=2, label="2019")
    ax.scatter([F[g]["debt1"] for g in order], range(len(order)), s=30, color=C_NOPOL,
               zorder=3, label=f"{S['years'][-1]}, AI shift, no policy")
    ax.axvline(60, color=C_REF, lw=0.8, ls=":")
    ax.annotate("60% reference value", (60, len(order) - 0.6), xytext=(3, 0),
                textcoords="offset points", fontsize=7, color=INK2)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=7.5)
    ax.legend(fontsize=7.5, frameon=False, loc="lower right")
    _style(ax, "Public debt, % of GDP: with no policy it rises in "
               f"{S['n_rise']} of {len(order)} member states")
    ax.grid(axis="x", color=C_GRID, lw=0.6)
    ax.grid(axis="y", visible=False)
    return _png(fig, path)


def fig_tradeoff(S, path=None):
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 2.9))
    _arms(a, S, "c_pc", offsets={"none": -7, "ubc": 7})
    lo = min(min(S["A"][t]["c_pc"]) for t in ARM)
    a.set_ylim(lo * 0.95, None)
    _style(a, "Consumption per person (EUR a year, 2019 prices)")
    _arms(b, S, "w10", 100.0, offsets={"none": 5, "cash": -5})
    b.set_ylim(0, 70)
    _style(b, "Top-10% share of net wealth (%)")
    fig.tight_layout(w_pad=2.5)
    return _png(fig, path)


def fig_payments(S):
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 2.8))
    _arms(a, S, "pay_pc", tags=("cash", "ubc"))
    _style(a, "Paid to each person (EUR a year, 2019 prices)")
    _arms(b, S, "gini", offsets={"none": 0, "cash": 3, "ubc": -3})
    _style(b, "Personal income Gini")
    fig.tight_layout(w_pad=2.5)
    return _png(fig)


def fig_pooling(S):
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.7), sharey=True)
    yrs = S["years"]
    for ax, form, col, name in ((axes[0], "cash_ubi", C_CASH, "Cash UBI"),
                                (axes[1], "ubc", C_UBC, "UBC")):
        q = S["q2"][form]
        n = min(len(yrs), len(q["nat"]))
        ax.plot(yrs[:n], q["nat"][:n], color=C_REF, lw=1.8, ls="--")
        ax.plot(yrs[:n], q["glob"][:n], color=col, lw=1.8)
        _label_end(ax, yrs[n - 1], q["nat"][n - 1], "national")
        _label_end(ax, yrs[n - 1], q["glob"][n - 1], "pooled")
        ax.set_xlim(yrs[0], yrs[-1] + 8)
        _years_axis(ax, yrs)
        _style(ax, f"{name}: between-country Gini ({q['n']} members)")
    fig.tight_layout(w_pad=2.0)
    return _png(fig)


# --------------------------------------------------------------------------- #
# Document
# --------------------------------------------------------------------------- #
def build_pdf(S: Dict[str, object], out_path: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                    Spacer, Image, Table, TableStyle, PageBreak, KeepTogether)
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    fdir = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
    pdfmetrics.registerFont(TTFont("DVS", os.path.join(fdir, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DVSB", os.path.join(fdir, "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DVSI", os.path.join(fdir, "DejaVuSans-Oblique.ttf")))

    ink, mut, acc = colors.HexColor("#1a2332"), colors.HexColor("#5a6472"), colors.HexColor("#0f6b54")
    ss = {
        "body": ParagraphStyle("body", fontName="DVS", fontSize=9.5, leading=13.5,
                               textColor=ink, spaceAfter=6),
        "h1": ParagraphStyle("h1", fontName="DVSB", fontSize=15, leading=19, textColor=ink,
                             spaceBefore=4, spaceAfter=8, keepWithNext=1),
        "part": ParagraphStyle("part", fontName="DVSB", fontSize=10, leading=12,
                               textColor=acc, spaceBefore=2, spaceAfter=2, keepWithNext=1),
        "h2": ParagraphStyle("h2", fontName="DVSB", fontSize=11, leading=14, textColor=ink,
                             spaceBefore=8, spaceAfter=5, keepWithNext=1),
        "bullet": ParagraphStyle("bullet", fontName="DVS", fontSize=9.5, leading=13.5,
                                 textColor=ink, leftIndent=10, bulletIndent=2, spaceAfter=5),
        "cap": ParagraphStyle("cap", fontName="DVSB", fontSize=8.5, leading=11, textColor=ink,
                              spaceBefore=3, spaceAfter=1),
        "src": ParagraphStyle("src", fontName="DVSI", fontSize=7.5, leading=9.5,
                              textColor=mut, spaceAfter=8),
        "cell": ParagraphStyle("cell", fontName="DVS", fontSize=8, leading=10, textColor=ink),
        "cellb": ParagraphStyle("cellb", fontName="DVSB", fontSize=8, leading=10, textColor=ink),
        "box": ParagraphStyle("box", fontName="DVS", fontSize=9, leading=12.5, textColor=ink,
                              backColor=colors.HexColor("#f2f6f5"), borderColor=acc,
                              borderWidth=0.8, borderPadding=7, spaceBefore=6, spaceAfter=8),
    }

    def footer(canv, doc):
        canv.saveState()
        canv.setFont("DVS", 7)
        canv.setFillColor(mut)
        if doc.page > 1:
            canv.drawString(18 * mm, 285 * mm, f"AGORA · {TITLE} {SUBTITLE}")
            canv.drawRightString(192 * mm, 285 * mm, DATE_LINE)
            canv.drawRightString(192 * mm, 12 * mm, "Sandbox, not oracle")
        canv.drawString(18 * mm, 12 * mm, str(doc.page))
        canv.restoreState()

    doc = BaseDocTemplate(out_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                          topMargin=16 * mm, bottomMargin=17 * mm,
                          title=f"{TITLE} {SUBTITLE}", author=AUTHOR)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=footer)])

    def P(t, style="body"):
        return Paragraph(t, ss[style])

    def B(t):
        return Paragraph(f"• {t}", ss["bullet"])

    def figure(buf, cap, src, w=168, hmax=95):
        from reportlab.lib.utils import ImageReader
        iw, ih = ImageReader(buf).getSize()
        buf.seek(0)
        width = w * mm
        height = width * ih / iw                  # keep the chart's aspect ratio
        if height > hmax * mm:
            height, width = hmax * mm, hmax * mm * iw / ih
        img = Image(buf, width=width, height=height)
        return KeepTogether([img, P(cap, "cap"), P(src, "src")])

    def table(rows, widths, head=True):
        t = Table([[P(c, "cellb" if (head and i == 0) else "cell") for c in r]
                   for i, r in enumerate(rows)], colWidths=[w * mm for w in widths])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8d0da")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f6")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
        return t

    # ---- computed strings ----
    A, F, L, q2, yrs = S["A"], S["F"], S["ladder"], S["q2"], S["years"]
    END, END2 = str(yrs[-1]), str(yrs[-1])[2:]
    de = F["DE"]
    pc = lambda x: f"{100 * x:.0f}"
    pc1 = lambda x: f"{100 * x:.1f}"
    eur = lambda x: f"€{x:,.0f}"
    c_gain = {t: 100 * (A[t]["c_avg"] / A["none"]["c_avg"] - 1) for t in ("cash", "ubc")}
    gdp_cost = 100 * (1 - A["cash"]["gdp_idx"] / A["none"]["gdp_idx"])
    c_drop = 100 * (1 - A["none"]["c_pc"][-1] / A["none"]["c_pc"][0])
    props = {r["key"]: r for r in S["props"]}
    val, rob = S["val"], S["rob"]
    vs = val["summary"]["final"]
    mult = val["summary"]["multipliers"]["final"]
    paired = {g: rob["geos"][g]["paired_ubc_better"] for g in rob["geos"]}
    sens = rob["geos"]["DE"]["sensitivity_ubc"]
    top = lambda m: sens[m]["drivers"][0]
    tr_cash = q2["cash_ubi"]["tr"]
    givers = sorted(tr_cash, key=lambda g: tr_cash[g])[:3]
    takers = sorted(tr_cash, key=lambda g: -tr_cash[g])[:3]
    reach_ubc = A["ubc"]["reach"]
    reach_src = props["source_levy"].get("ai_rent_foreign_reached", 0.0)
    reach_pledge = props["pledge"].get("ai_rent_foreign_reached", 0.0)
    abroad_share = S["abroad_end"] / S["rent_end"]
    ls0, ls1 = S["ls"][0], S["ls"][-1]
    ex = ", ".join(S["excluded"])
    ngeo = len(S["geos"])
    cross = (f"overtakes the cash transfer in {S['crossover']}" if S["crossover"]
             else f"stays below the cash transfer every year to {END}")
    dshare = lambda g, m: f"{100 * paired[g][m]:.0f}%"

    E = []
    # ================= title =================
    E += [Spacer(1, 28 * mm),
          Paragraph("A G O R A", ParagraphStyle("t0", fontName="DVSB", fontSize=13,
                    textColor=acc, alignment=1, spaceAfter=2)),
          Paragraph("A sandbox for the economics of abundance",
                    ParagraphStyle("t1", fontName="DVSI", fontSize=9, textColor=mut,
                                   alignment=1, spaceAfter=16)),
          Paragraph(TITLE, ParagraphStyle("t2", fontName="DVSB", fontSize=27, leading=31,
                                          textColor=ink, alignment=1, spaceAfter=4)),
          Paragraph(SUBTITLE, ParagraphStyle("t3", fontName="DVS", fontSize=14, textColor=mut,
                                             alignment=1, spaceAfter=14)),
          Paragraph("What happens to Europe's households and public finances if AI moves income "
                    "from work to capital, and what cash transfers and citizen ownership can and "
                    f"cannot do about it. Tested in a stock-flow-consistent model of {ngeo} EU "
                    "economies.",
                    ParagraphStyle("t4", fontName="DVS", fontSize=10, leading=14.5,
                                   textColor=ink, alignment=1, spaceAfter=18)),
          P("<b>A sandbox, not an oracle. Please read this first.</b> Every number here is a "
            "comparison between policies inside one accounting-complete model, under stated "
            "assumptions. None is a forecast. The central scenario assumes AI pushes the labour "
            f"share from {ls0:.0f}% to {ls1:.0f}% of income by {END}; a milder shift gives "
            "smaller effects. The model reproduces the 2019 national accounts, and its "
            "first-year fiscal multipliers sit inside the published ranges. Over 2011–2019, "
            "though, it tracks history no better than simple benchmarks (Part V). Read the "
            "direction of each result and the trade-offs, not the decimals. Every figure is "
            "regenerated from the engine by <font name='DVSB'>scripts/build_manifesto.py</font>.",
            "box"),
          P("<b>This is version 1.2.</b> It replaces v1.1 (“Owning the Machine”), whose "
            "headline claims did not survive a re-validation of the model: the citizens' "
            "dividend overtaking cash, ownership dominating every alternative, and the model "
            "being validated against history. Part V lists every change.", "box"),
          Spacer(1, 8 * mm),
          Paragraph(f"Prepared with the AGORA engine · {ngeo} EU economies · {DATE_LINE}"
                    f"<br/>By {AUTHOR}",
                    ParagraphStyle("t5", fontName="DVS", fontSize=9, textColor=mut,
                                   alignment=1)),
          PageBreak()]

    # ================= executive summary =================
    E += [P("Executive summary", "h1"),
          P("If AI raises output while shrinking the share of it paid as wages, three things "
            "follow for Europe. AGORA, an open, accounting-complete model of the economies of "
            f"{ngeo} member states, traces each of them under one stated scenario: the labour "
            f"share falls from {ls0:.0f}% to {ls1:.0f}% by {END}, with an investment boom in AI "
            f"capital. Germany is the worked example; the other {ngeo - 1} members are run the "
            "same way."),
          P("1. The welfare state's tax base erodes", "h2"),
          P("European welfare states are funded mostly by taxes on wages. With no policy "
            f"response, German wage-tax revenue falls from {pc1(de['lt0'])}% to "
            f"{pc1(de['lt1'])}% of GDP by {END}. Taxes on profits rise ({pc1(de['kt0'])}% to "
            f"{pc1(de['kt1'])}%), but not by enough. Across the {ngeo} members the median "
            f"public debt rises from {S['debt0_med']:.0f}% to {S['debt1_med']:.0f}% of GDP, and "
            f"{S['n150']} pass 150%. This needs no view on basic income: the state taxes the "
            "income AI shrinks."),
          P("2. Cash and ownership trade consumption now for wealth later", "h2"),
          P("A 40% levy on profits can be paid out as a cash basic income, or taken as shares "
            "in a citizens' fund that pays a dividend (Universal Basic Capital, UBC). Cash "
            f"raises average consumption per person by {c_gain['cash']:.0f}% over no policy; "
            f"UBC by {c_gain['ubc']:.0f}%. UBC cuts the top-10% share of wealth from "
            f"{pc(A['ubc']['w10'][0])}% to {pc(A['ubc']['w10'][-1])}%, while cash leaves it at "
            f"{pc(A['cash']['w10'][-1])}%, and it ends with the lower income Gini "
            f"({A['ubc']['gini'][-1]:.2f} against {A['cash']['gini'][-1]:.2f}). The fund's "
            f"dividend {cross} ({eur(A['ubc']['pay_pc'][-1])} against "
            f"{eur(A['cash']['pay_pc'][-1])} per person in {END}). Both cost output: GDP ends "
            f"about {gdp_cost:.0f}% below the no-policy path, because both tax the profits that "
            "fund investment. Neither form dominates. Choosing between them means choosing "
            "between consumption now and ownership later. Across 500 joint draws of the "
            "model's uncertain assumptions, UBC is more equal in every draw, and cash gives "
            "more consumption in every draw."),
          P("3. Europe does not own most of the machine", "h2"),
          P(f"By {END} the rent earned by AI capital reaches {pc(S['rent_end'])}% of German GDP, "
            f"and {pc(abroad_share)}% of it is paid abroad as licence and cloud fees (US "
            "providers hold about 70% of Europe's cloud market). Real GDP rises "
            f"{100 * (A['none']['gdp_idx'] - 1):.0f}% while real national income falls "
            f"{100 * (1 - A['none']['gni_idx']):.0f}%, and consumption per person ends "
            f"{c_drop:.0f}% below 2019. No domestic instrument reaches the part "
            "that leaves: a 40% claim on domestic profits reaches at most "
            f"{pc(reach_ubc)}% of the AI rent, and a 3% levy on fees paid abroad reaches "
            f"{pc1(reach_src)}% of the foreign part, because providers pass it on."),
          P("What follows", "h2"),
          P("The choice Europe faces is less “cash or capital” than how its welfare state is "
            "funded once wages shrink, and who owns the AI it uses. A dividend pooled across "
            f"the Union narrows the gap between member states by {q2['cash_ubi']['cut_end']:.0f}% "
            f"(cash) or {q2['ubc']['cut_end']:.0f}% (UBC) by {END}, but needs transfers of up to "
            f"{eur(-tr_cash[givers[0]])} per person a year from the richest members."),
          PageBreak()]

    # ================= PART I =================
    E += [P("PART I", "part"), P("The shock: income moves from work to capital", "h1"),
          P("AGORA represents the AI transition as an assumption, not a forecast. From 2019 "
            f"to {END} the labour share falls in a straight line from {ls0:.0f}% to "
            f"{ls1:.0f}%, and investment in AI capital booms. The profit attributed to AI "
            "capital (the AI rent) is split between domestic owners and foreign providers; "
            "by default 70% is earned abroad, the US providers' share of the European cloud "
            "market (Synergy Research, 2025). The size of this shock is the model's largest "
            f"driver: across the Monte Carlo, the labour-share fall explains "
            f"{100 * top('consumption_pc_avg')['share']:.0f}% of the variation in German "
            "consumption and "
            f"{100 * top('gni_end')['share']:.0f}% of the variation in national income."),
          figure(fig_shock(S),
                 "Figure 1. Output keeps growing; national income does not. With no policy, "
                 "real GDP rises while real national income, which nets out the AI rent paid "
                 "abroad, falls below its 2019 level.",
                 "Source: AGORA engine, AI shift with no policy, Germany, calibrated to 2019 "
                 "Eurostat and AMECO data. Scenario, not a forecast. Without the AI shift, real "
                 f"GDP grows {100 * (S['base_gdp_idx'] - 1):.0f}% by {END} at the 2024 Ageing "
                 "Report trend."),
          P("The shock is not uniform. Using Germany's Eurostat input-output table (FIGARO), "
            "AGORA spreads the fall across sectors by their exposure to AI, which is cognitive "
            "rather than robotic (OECD 2024 sectoral taxonomy). Labour's share in ICT, "
            f"finance and business services falls from {S['ls_sec_0'][S['sectors'].index('ICT, finance & business')]:.0f}% "
            f"to {S['ls_sec_H'][S['sectors'].index('ICT, finance & business')]:.0f}%; "
            f"construction moves from {S['ls_sec_0'][S['sectors'].index('Construction')]:.0f}% "
            f"to {S['ls_sec_H'][S['sectors'].index('Construction')]:.0f}%."),
          figure(fig_sectors(S),
                 "Figure 2. A concentrated shock: office work loses most of its labour share.",
                 "Source: AGORA input-output module on "
                 f"{'real Eurostat FIGARO tables' if S['io_real'] else 'an illustrative structure'}, "
                 "Germany. Sector value added reconciles to GDP. Labour shares are floored at "
                 "2%."),
          PageBreak()]

    # ================= PART II =================
    E += [P("PART II", "part"), P("Finding 1: the welfare state's tax base erodes", "h1"),
          P("Europe's public finances rest on labour. In 2019 the model's taxes on wages "
            f"(income tax and social contributions) raise {pc1(de['lt0'])}% of German GDP, "
            f"and taxes on profits {pc1(de['kt0'])}%. As the labour share halves, wage-tax "
            f"revenue falls to {pc1(de['lt1'])}% of GDP by {END}. Profit taxes rise to "
            f"{pc1(de['kt1'])}%, because profits grow, but much of the new profit is the AI "
            "rent paid abroad, which the German budget never taxes. The government in the "
            "model responds as European governments have historically done: it raises tax "
            "rates as debt climbs (the wage-tax rate goes from "
            f"{pc1(de['tl0'])}% to {pc1(de['tl1'])}%). Debt rises anyway."),
          P(f"The pattern holds across the Union. Median wage-tax revenue falls from "
            f"{pc1(S['lt0_med'])}% to {pc1(S['lt1_med'])}% of GDP; public debt rises in "
            f"{S['n_rise']} of {ngeo} members, from a median of {S['debt0_med']:.0f}% to "
            f"{S['debt1_med']:.0f}% of GDP, and {S['n150']} end above 150% (Figure 3)."),
          figure(fig_fiscal(S),
                 "Figure 3. With no policy, public debt rises across the Union.",
                 f"Source: AGORA engine, AI shift with no policy, {ngeo} members ({ex} "
                 "excluded: Part V). The government follows a fiscal rule that raises tax "
                 "rates as debt rises, and borrows at market rates with a risk premium."),
          P("Of the three findings, this one depends least on contested assumptions. It "
            "follows from where European taxes fall, and it holds whatever one thinks of "
            "basic income or citizens' funds. The levels depend on interest rates and "
            "inflation, which the model holds near the ECB's 2% target; the direction does "
            "not. Any answer to the AI transition in Europe is also an answer to how the "
            "welfare state is funded."),
          PageBreak()]

    # ================= PART III =================
    ladder_rows = [["Share of the fund's retained profit reinvested at home",
                    "UBC economy (cash economy = 1.00)", f"UBC Gini, {END}",
                    f"Dividend per person, {END}"]]
    for rv in LADDER:
        ladder_rows.append([f"{100 * rv:.0f}%", f"{L[rv]['gdp_ratio']:.2f}",
                            f"{L[rv]['gini_ubc']:.3f} (cash {L[rv]['gini_cash']:.3f})",
                            eur(L[rv]["div_end"])])
    mc_rows = [["Share of 500 draws in which UBC beats cash UBI"] + list(paired)]
    for m, lab in (("gini", f"Lower income Gini, {END}"), ("poverty", f"Lower poverty rate, {END}"),
                   ("citizen_wealth_pc", "More citizen-owned wealth"),
                   ("consumption_pc_avg", f"Higher consumption per person, 2020–{END2}"),
                   ("gni_end", f"Higher real national income, {END}")):
        mc_rows.append([lab] + [dshare(g, m) for g in paired])
    E += [P("PART III", "part"),
          P("Finding 2: cash or ownership, consume now or own later", "h1"),
          P("The two forms are compared at the same intensity. Each year 40% of profits is "
            "either taxed and paid to every resident as an equal cash income, or converted "
            "into new shares owned by a citizens' fund. The fund follows Norway's rule for its "
            "sovereign wealth fund: it pays out 3% of its value a year as an equal dividend "
            "and keeps the rest invested. Shares are priced at market value, and the fund "
            "takes on its share of company debt."),
          figure(fig_tradeoff(S),
                 "Figure 4. Cash raises consumption; only ownership changes who owns.",
                 "Source: AGORA engine, Germany, AI shift, 40% levy paid as cash or 40% claim "
                 "in shares (fund pays 3% of its value a year). Consumption in 2019 prices."),
          P("Figure 4 is the trade-off in one picture. Cash lifts average consumption per "
            f"person by {c_gain['cash']:.0f}% over 2020–{END2}; UBC by "
            f"{c_gain['ubc']:.0f}%. Wealth runs the other way: with cash, the top-10% share "
            f"drifts up from {pc(A['cash']['w10'][0])}% to {pc(A['cash']['w10'][-1])}%, as it "
            f"does with no policy; under UBC it falls to {pc(A['ubc']['w10'][-1])}%, because "
            f"citizens come to own {pc(A['ubc']['own_end'])}% of domestic capital "
            f"({pc(A['ubc']['own_10y'])}% after ten years), worth "
            f"{eur(A['ubc']['wealth_pc_end'])} per person by {END}."),
          figure(fig_payments(S),
                 "Figure 5. The dividend never catches the cash transfer; the income Gini "
                 "still ends lower under UBC.",
                 "Source: as Figure 4. Payments in 2019 prices."),
          P("UBC is in effect a collective savings scheme: most of what the levy raises is "
            "kept as capital rather than paid out. Comparing it with cash compares saving "
            f"with spending. After ten years the cash transfer is {eur(A['cash']['pay_pc'][10])} "
            f"per person and the dividend {eur(A['ubc']['pay_pc'][10])}; by {END} "
            f"{eur(A['cash']['pay_pc'][-1])} against {eur(A['ubc']['pay_pc'][-1])}. Cash "
            "cuts poverty faster (after ten years: "
            f"{pc1(A['cash']['pov'][10])}% against {pc1(A['ubc']['pov'][10])}%, with "
            f"{pc1(A['none']['pov'][10])}% under no policy). UBC ends lower "
            f"({pc1(A['ubc']['pov'][-1])}% against {pc1(A['cash']['pov'][-1])}% in {END}): "
            "under UBC the capital income itself is spread more evenly, while cash adds a "
            "flat payment to an unchanged market distribution."),
          P("Neither form protects growth", "h2"),
          P(f"Both forms cost about {gdp_cost:.0f}% of {END} GDP against no policy: real GDP "
            f"ends {A['none']['gdp_idx']:.2f}× its 2019 level with no policy, "
            f"{A['cash']['gdp_idx']:.2f}× with cash and {A['ubc']['gdp_idx']:.2f}× with UBC. "
            "Investment follows profits, and both take 40% of them. Letting the fund reinvest "
            "more of its profit at home does not change this much (Table 1). It moves money "
            "from the dividend into capital, the economy ends at most a few per cent larger, "
            "and at full reinvestment it is smaller while the Gini rises above cash's."),
          KeepTogether([P(f"Table 1. The fund's reinvestment dial (Germany, {END})", "cap"),
                        table(ladder_rows, [52, 40, 42, 34]),
                        P("Source: AGORA engine, Germany, AI shift, 40% claim in shares.", "src")]),
          P("How robust is this?", "h2"),
          P("The ranking survives the model's uncertainty. Drawing all 19 uncertain "
            "assumptions together 500 times for Germany, France and Slovakia (Table 2), UBC "
            "is more equal, has less poverty and leaves citizens more wealth in practically "
            "every draw, and cash gives more consumption in every draw. On national income "
            "the result depends on the country."),
          KeepTogether([P("Table 2. UBC against cash UBI across 500 joint draws", "cap"),
                        table(mc_rows, [76] + [30] * len(paired)),
                        P("Source: docs/ROBUSTNESS-2026-11.md (scripts/robustness.py), seed 0. "
                          "The same draw gives both forms the same assumptions.", "src")]),
          P("The size of the inequality gap is far less certain than its direction. "
            f"{100 * top('gini')['share']:.0f}% of the variation in UBC's Gini comes from one "
            "parameter, β, which links the capital share to market inequality. It cannot be "
            "estimated from recent data, because European taxes and transfers already erase "
            f"about {pc(S['wedge_mean'])}% of market inequality, hiding the signal. The ranking "
            "holds across β's whole plausible range; the gap between the two forms does not."),
          P("If a society chooses ownership", "h2"),
          B("<b>Write the payout rule into law.</b> The split between dividend and "
            "reinvestment decides who gains when (Table 1). It should be set by rule, not "
            "discretion."),
          B("<b>Keep stakes equal and non-tradable,</b> so ownership cannot re-concentrate "
            "through a secondary market, the failure of past voucher privatisations."),
          B("<b>Expect a slow start.</b> At a 3% payout the dividend stays small for a "
            "generation. Pairing a fund with a cash floor is a design option the model does "
            "not yet test."),
          PageBreak()]

    # ================= PART IV =================
    prop_rows = [["Policy", f"Real national income, {END} (2019 = 1)",
                  f"Consumption per person, 2020–{END2}", f"Gini, {END}", f"Public debt, {END} (% GDP)",
                  "Share of foreign AI rent reached"]]
    for k in ("none", "stock_levy", "pledge", "debt_fund", "child_accounts", "source_levy",
              "broad_ubi", "cash_ubi_40", "ubc_40"):
        r = props.get(k)
        if not r or not r["ok"]:
            continue
        prop_rows.append([r["name"], f"{r['gni_vs_2019']:.2f}", eur(r["consumption_pc_avg"]),
                          f"{r['gini_end']:.3f}", f"{r['debt_gdp_end']:.0f}",
                          f"{100 * r.get('ai_rent_foreign_reached', 0.0):.1f}%"])
    E += [P("PART IV", "part"), P("Finding 3: Europe does not own most of the machine", "h1"),
          P(f"The AI rent is large and mostly leaves. By {END} it reaches "
            f"{pc(S['rent_end'])}% of German GDP, and {pc(S['abroad_end'])}% of GDP is paid to "
            "foreign providers. That is why, in Figure 1, real GDP rises "
            f"{100 * (A['none']['gdp_idx'] - 1):.0f}% while real national income falls "
            f"{100 * (1 - A['none']['gni_idx']):.0f}%. The fees leave the national income that "
            f"households and the state live on: consumption per person ends {c_drop:.0f}% below 2019 "
            "with no policy, and below 2019 under cash and UBC too (Figure 4). Taxes on "
            "domestic profits and claims on "
            "domestic shares reach only the domestic part. The 40% claim in shares reaches "
            f"{pc(reach_ubc)}% of the AI rent; the 40% cash levy {pc(A['cash']['reach'])}%."),
          P("Table 3 runs six real 2026 proposals against the two 40% benchmarks. None reaches "
            "much of the foreign rent. A 3% levy on fees paid abroad reaches "
            f"{pc1(reach_src)}% of it, because providers raise prices by about the levy; "
            "voluntary pledges by AI companies, in their best case, reach "
            f"{pc(reach_pledge)}%. The real proposals are also small: none moves national "
            "income by more than a few per cent."),
          KeepTogether([P("Table 3. Real proposals against no policy (Germany, AI shift)", "cap"),
                        table(prop_rows, [50, 25, 26, 17, 24, 26]),
                        P("Source: AGORA proposals library (proposals.py), every run "
                          "consistency-gated. Each proposal runs at its announced size; the two "
                          "benchmarks are far larger than any of them.", "src")]),
          P("The model can say that the foreign part is out of reach of domestic taxes and "
            "claims. Whether Europe can build its own AI providers or take stakes in foreign "
            "ones is a question of industrial policy, outside the model. But it is where most "
            "of the money is."),
          P("Between member states: pooling", "h2"),
          P("A purely national dividend lets richer members pay bigger dividends, so the gap "
            "between countries persists. Pooling the levy across the Union and paying an equal "
            "European dividend narrows the between-country Gini by "
            f"{q2['cash_ubi']['cut_end']:.0f}% under cash and {q2['ubc']['cut_end']:.0f}% under "
            f"UBC by {END} (Figure 6). After ten years cash pooling has narrowed it "
            f"{q2['cash_ubi']['cut_10y']:.0f}%, while UBC pooling has "
            f"{'narrowed' if q2['ubc']['cut_10y'] >= 0 else 'widened'} it "
            f"{abs(q2['ubc']['cut_10y']):.0f}%. The transfers are large: under cash pooling "
            + ", ".join(f"{g} pays {eur(-tr_cash[g])}" for g in givers)
            + f" per person a year by {END}, and "
            + ", ".join(f"{g} receives {eur(tr_cash[g])}" for g in takers)
            + ". The arithmetic works; the politics would be hard."),
          figure(fig_pooling(S),
                 "Figure 6. Pooling narrows the gap between member states under both forms.",
                 f"Source: AGORA multi-region module, {q2['cash_ubi']['n']} members, 40% levy, "
                 "transfers routed through each country's accounts and iterated to a fixed "
                 "point.")]

    # ================= PART V =================
    vrows = [["Variable", "Engine error", "Random walk", "Static multiplier",
              "Engine beats both"]]
    lab = {"gdp_real": ("Real GDP", "%"), "consumption_real": ("Real consumption", "%"),
           "investment_real": ("Real private investment", "%"),
           "inflation": ("Inflation", " pp/yr"), "debt_gdp": ("Public debt / GDP", " pp"),
           "ca_gdp": ("Current account / GDP", " pp"),
           "private_balance": ("Private-sector balance / GDP", " pp")}
    for k, (name, u) in lab.items():
        r = vs["rows"][k]
        vrows.append([name, f"{r['model']:.1f}{u}", f"{r['rw']:.1f}{u}", f"{r['static']:.1f}{u}",
                      f"{r['beats_both']} of {r['n']}"])
    E += [Spacer(1, 6 * mm), P("PART V", "part"), P("What the model can and cannot tell you", "h1"),
          P("History test", "h2"),
          P("The model was started in 2010 from 2010 data only, fed the government spending, "
            "exports, wage share and interest rates that actually happened, and left to "
            "produce everything else to 2019. It was scored against two naive benchmarks: a "
            "random walk, and a static multiplier given the same inputs. The bar, set before "
            "the run, was to beat both for most countries and variables. "
            f"<b>It does not: the engine beats both in {vs['beats_both']} of {vs['cells']} "
            f"cases ({100 * vs['beats_both'] / vs['cells']:.0f}%).</b> Inflation is its best "
            "variable and the current account its worst."),
          KeepTogether([P(f"Table 4. Median error, 2011–2019, {vs['n_countries']} members", "cap"),
                        table(vrows, [52, 28, 28, 30, 30]),
                        P("Source: docs/VALIDATION-2026-11.md (scripts/validate.py). Errors are "
                          "changes since 2010.", "src")]),
          P("Its short-run responses are closer to the evidence. A stimulus of 1% of GDP "
            f"raises GDP by {mult['spending']['year1']:.2f} per euro of public spending in "
            f"the first year, {mult['labour_tax']['year1']:.2f} for a cut in taxes on wages "
            f"and {mult['capital_tax']['year1']:.2f} for a cut in taxes on profits, all inside "
            "the ranges of European central-bank models. In the second year the responses "
            f"are above them (spending {mult['spending']['year2']:.2f}), because the model has "
            "no central-bank reaction; read its short-run effects as upper bounds."),
          P("Limits", "h2"),
          B("<b>The AI shock is assumed,</b> and its size drives most results (Part I)."),
          B("<b>No exchange rates and no monetary reaction.</b> Surplus countries keep "
            "accumulating foreign assets; the current account is the weakest variable in the "
            "history test."),
          B("<b>Inflation is anchored near 2%.</b> Over 2011–19 actual inflation was lower, so "
            "the model under-predicted debt in most countries."),
          B("<b>The 70% foreign share of the AI rent</b> is proxied by the US share of "
            "Europe's cloud market (Monte-Carlo range 50–90%)."),
          B(f"<b>{ex} are excluded:</b> Greek households spent more than their income in "
            "2019 under the model's calibration, and multinational accounting distorts Irish "
            "and Luxembourg GDP."),
          B("<b>Outside the model:</b> the politics of a capital levy, fund governance and "
            "capture, capital flight, and whether the AI shock comes at all."),
          P("What changed from v1.1", "h2"),
          P("Between October and November 2026 the model gained capacity limits and prices, "
            "credit constraints for owners, foreign ownership of capital and of the AI rent, "
            "market prices for shares, a banking sector, existing loans, each country's own "
            "capital stock and trend growth, and gradual consumption. Each step made the "
            "effects smaller and turned clear wins into trade-offs. v1.1 claims that do not "
            "survive:"),
          B("“The citizens' dividend overtakes cash around year 11.” Retracted: it "
            f"{cross}."),
          B("“UBC dominates both cash and inaction; doing nothing is off the frontier.” "
            "Retracted: no policy and cash UBI at every rate are on the trade-off frontier."),
          B("“With reinvestment the UBC economy ends larger than the cash economy.” "
            f"Retracted: at most {max(L[r]['gdp_ratio'] for r in LADDER):.2f}× (Table 1)."),
          B("“Back-tested to ~2.3% mean GDP error; the model is validated.” Retracted: see "
            "Table 4."),
          B("“Pooling roughly halves the European gap.” Changed: "
            f"{q2['cash_ubi']['cut_end']:.0f}% (cash) and {q2['ubc']['cut_end']:.0f}% (UBC)."),
          B("“UBC eliminates poverty.” Changed: it falls to "
            f"{pc1(A['ubc']['pov'][-1])}%, against {pc1(A['cash']['pov'][-1])}% under cash."),
          P("What survives: only ownership moves the concentration of wealth, and UBC is more "
            "equal than cash in every draw. Every published finding and its status is listed "
            "in <font name='DVSB'>docs/FINDINGS-LEDGER.md</font>."),
          P("The bottom line", "h2"),
          P("If AI moves income from work to capital on anything like this scale, Europe's "
            "welfare states lose their tax base, and much of the new income leaves the "
            "continent. Cash and citizen ownership answer different questions: cash protects "
            "consumption now, ownership changes who holds wealth later, and both cost some "
            "growth. The model cannot choose between them; that is a choice of values. It can "
            "show what each choice costs, in an open model anyone can rerun and change."),
          PageBreak()]

    # ================= APPENDIX =================
    srcs = [["Layer / quantity", "Source"],
            ["GDP, consumption, investment, trade; history 1995–2019",
             "Eurostat national accounts (nama_10_gdp, gov_10a_main, nasa_10_ki)"],
            ["Labour share; capital stock and depreciation", "AMECO (ALCD2; OKND, PIGT, UKCT, UVGD)"],
            ["Public debt, deficit, interest", "Eurostat gov_10dd_edpt1"],
            ["Interest rates, loan and deposit rates", "AMECO (ISN, ILN); ECB MFI interest rates"],
            ["Existing loans of firms and households", "Eurostat financial accounts (nasa_10_f_bs, F4)"],
            ["Foreign ownership of capital; foreign positions",
             "Eurostat nasa_10_nf_tr (D42+D43 with the rest of the world); tipsii10"],
            ["Capacity utilisation", "European Commission business surveys (ei_bsin_q_r2)"],
            ["Trend growth to 2070", "2024 Ageing Report, European Commission Institutional Paper 257"],
            ["Propensities to consume", "Onaran &amp; Obst (2016); Jappelli &amp; Pistaferri (2014); "
             "Fagereng, Holm &amp; Natvik (2021)"],
            ["Income and wealth distribution", "Eurostat ilc_di12; OECD IDD and Wealth Distribution Database"],
            ["Sectoral structure; AI exposure", "Eurostat FIGARO (naio_10_cp1700); OECD (2024) "
             "sectoral taxonomy of AI intensity"],
            ["Foreign share of the AI rent", "Synergy Research (2025), European cloud market shares"]]
    E += [P("APPENDIX", "part"), P("Method, data and reproducibility", "h1"),
          P("<b>The engine.</b> AGORA is a stock-flow-consistent model: every euro is someone's "
            "asset and someone else's liability, and every scenario must pass a consistency "
            "gate (sector balances sum to zero, stocks match accumulated flows) before any "
            "result is reported. It combines a macro core with capacity limits, prices, a "
            "banking sector and a government with a fiscal rule; a household income and "
            "wealth distribution; a sectoral input-output layer; foreign ownership of capital "
            "and of the AI rent; a citizens'-fund mechanism; and a multi-country layer for the "
            "Union. Each run is also checked against plausibility laws (no insolvent "
            "households, investment below 40% of GDP, Gini above 0.15)."),
          P(f"<b>Calibration.</b> Each of the {ngeo} members is calibrated to its 2019 "
            "national accounts, its own capital stock, debt, interest rates, foreign "
            "position and existing loans, and grows at its 2024 Ageing Report trend without "
            "the AI shift. Every parameter is sourced or labelled as an assumption with a "
            "Monte-Carlo range."),
          P("Data sources (through DBnomics unless noted)", "h2"),
          table(srcs, [70, 98]), Spacer(1, 5),
          P(f"<b>Reproducibility.</b> The full test suite ({S['tests']} tests) passes, and "
            "every number in this document is recomputed from the gated engine by "
            "<font name='DVSB'>scripts/build_manifesto.py</font>, which refuses to build if "
            "any scenario fails the gate. The history test and the Monte Carlo are read from "
            "files written by <font name='DVSB'>scripts/validate.py</font> and "
            "<font name='DVSB'>scripts/robustness.py</font>."),
          Spacer(1, 6),
          P("AGORA: a sandbox for the economics of abundance. Scenario comparisons under "
            "explicit assumptions; not investment, legal or policy advice.", "src")]

    doc.build(E)


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "AGORA_Manifesto.pdf")
    print("computing stats from the gated engine (offline, a few minutes)...")
    S = compute()
    A = S["A"]
    print(f"  gated: {S['all_gated']} | tests: {S['tests']} | crossover {S['crossover']} | "
          f"own {100 * A['ubc']['own_end']:.0f}% | debt median {S['debt0_med']:.0f}->"
          f"{S['debt1_med']:.0f} | Q2 {S['q2']['cash_ubi']['cut_end']:.0f}%/"
          f"{S['q2']['ubc']['cut_end']:.0f}%")
    if not S["all_gated"]:
        sys.exit("ABORT: a scenario failed the consistency gate; not publishing from it")
    fig_tradeoff(S, os.path.join(ROOT, "AGORA_tradeoff_DE.png"))
    fig_fiscal(S, os.path.join(ROOT, "AGORA_fiscal_EU.png"))
    build_pdf(S, out)
    print(f"wrote {out}, AGORA_tradeoff_DE.png, AGORA_fiscal_EU.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
