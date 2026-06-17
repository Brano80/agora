"""AGORA dashboard (Layer 1) — Streamlit control surface.

    streamlit run dashboard/app.py

Open-economy macro core + personal distribution + production structure (input-
output) + AI-shock driver, with a build-your-own scenario, a side-by-side
comparison view, and the consistency-gate verdict (incl. fx, decile, and
sectoral reconciliation). A sandbox for comparing policies, NOT a forecast.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from data.connectors.dbnomics import DBnomicsConnector
from calibration import calibrate
from modules.sfc_core import SFCCore
from modules.distribution import DistributionModule
from modules.input_output import InputOutputModule
from consistency.checks import check_run, check_distribution, check_input_output
from scenarios import make_triad, build_custom, make_ubc_experiment
from policy_search import search_policies
from region import MultiRegion
from uncertainty import monte_carlo
from schema.accounts import series_for_geo

st.set_page_config(page_title="AGORA — EU economy sandbox", layout="wide")


@st.cache_data(show_spinner=False)
def load_data(geo, year, allow_live):
    conn = DBnomicsConnector(allow_live=allow_live)
    rows = conn.fetch(geo, year)
    data = {c: r["value"] for c, r in rows.items()}
    sources = {c: r["source"] for c, r in rows.items()}
    data["_sources"] = sources
    return data, rows, sources


def frame(runs, which):
    idx = {"sfc": 1, "dist": 2, "io": 3}[which]
    rows = []
    for tup in runs:
        name, res = tup[0], tup[idx]
        if res is None:
            continue
        for per in res.periods:
            for k, v in per.reported.items():
                rows.append({"scenario": name, "year": per.year,
                             "metric": k, "value": v})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
st.sidebar.title("AGORA")
st.sidebar.caption("Modular sandbox for the EU economy under the AI transition. "
                   "Compare policies — not a forecast.")

geo = st.sidebar.selectbox("Country / geo", ["DE", "FR"], 0,
                           help="DE and FR ship calibrated, sourced snapshots.")
year = st.sidebar.number_input("Baseline year", 2000, 2024, 2019, 1)
allow_live = st.sidebar.checkbox("Try live DBnomics", value=False)
horizon = st.sidebar.slider("Horizon (years)", 10, 50, 30)

st.sidebar.markdown("### Module manager")
for label, on in [("SFC monetary core (open economy)", True),
                  ("Distribution (deciles)", True),
                  ("Input-output (sectors)", True), ("AI-shock driver", True)]:
    st.sidebar.checkbox(label, value=on, disabled=True, help="Active.")
st.sidebar.checkbox("Agent-based (EconAgent)", value=False, disabled=True,
                    help="Plugs in at a later phase via the same interface.")

st.sidebar.markdown("### Build your own scenario")
hold_ls = st.sidebar.checkbox("Hold labour share (no AI shift)", value=False)
ls_end = st.sidebar.slider("AI labour-share target (%)", 10, 62, 30,
                           disabled=hold_ls) / 100.0
adoption = st.sidebar.selectbox("AI adoption path", ["ramp", "scurve"], 0)
capex_growth = st.sidebar.slider("AI capex growth (%/yr)", 0, 15, 6) / 100.0
capital_tax = st.sidebar.slider("Capital tax (%)", 0, 80, 40) / 100.0
ubi = st.sidebar.checkbox("UBI on (recycle capital tax)", value=True)
ubc = st.sidebar.checkbox("UBC instead (citizens' fund owns capital)", value=False,
    help="Universal Basic Capital: the levy builds a citizens' capital endowment "
         "that pays a per-capita dividend. Takes precedence over UBI if both are on.")
ubc_reinvest = st.sidebar.slider("UBC fund reinvest rate", 0.0, 1.0, 0.0, 0.1,
    help="Fraction of the fund's profit share reinvested into capex (vs paid out). "
         ">0 sustains investment as private owners are diluted (resolves crux C1).")

st.sidebar.markdown("### Calibration / elasticities")
f_workers = st.sidebar.slider("Worker population share", 0.5, 0.95, 0.80, 0.01)
a1_w = st.sidebar.slider("Workers' MPC", 0.5, 1.0, 0.95, 0.01)
wealth_share_owners = st.sidebar.slider("Owners' share of money wealth",
                                        0.3, 0.95, 0.70, 0.05)
beta = st.sidebar.slider("Capital share → inequality (β)", 0.0, 1.5, 0.6, 0.05)
gamma = st.sidebar.slider("UBI → compression (γ)", 0.0, 1.5, 0.5, 0.05)
i_rate = st.sidebar.slider("Interest on gov debt (%/yr)", 0.0, 6.0, 0.0, 0.5,
    help="Debt service on government money/bills. >0 compounds the deficit — "
         "hardens the fiscal-sustainability picture as the wage-tax base erodes.") / 100.0
inv_elasticity = st.sidebar.slider(
    "Investment → owners' retained return (ε, crux C1)", 0.0, 2.0, 0.0, 0.1,
    help="0 = autonomous capex. >0 = taxing/diluting owners' capital income deters investment; UBC's falling retained share (1-φ) bites harder over time "
         "than a flat capital tax (1-τ).")

# --------------------------------------------------------------------------- #
# Run
# --------------------------------------------------------------------------- #
try:
    data, rows, sources = load_data(geo, int(year), allow_live)
except Exception as exc:  # pragma: no cover
    st.error(f"Could not load data for {geo} {year}: {exc}")
    st.stop()
if "gdp" not in data:
    st.error(f"No calibration data for {geo} {year}.")
    st.stop()

calib_kwargs = dict(f_workers=f_workers, a1_w=a1_w,
                    wealth_share_owners=wealth_share_owners, i_rate=i_rate)
p = calibrate(data, geo=geo, base_year=int(year), sources=sources, **calib_kwargs)
core = SFCCore(base_year=int(year), calib_kwargs=calib_kwargs, inv_elasticity=inv_elasticity)
dist_mod = DistributionModule(beta=beta, gamma=gamma, base_year=int(year))
io_mod = InputOutputModule(base_year=int(year))

scenarios = make_triad(p, horizon=horizon)
scenarios.append(build_custom(
    p, labour_share_end=(None if hold_ls else ls_end), capex_growth=capex_growth,
    capital_tax=capital_tax, ubi=ubi, ubc=ubc, ubc_reinvest=ubc_reinvest,
    adoption=adoption, horizon=horizon, name="Custom (yours)"))

runs, all_reports = [], []
for scen in scenarios:
    sfc_res = core.run(scen, data)
    dist_res = dist_mod.run(scen, data, {"sfc_core": sfc_res})
    io_res = io_mod.run(scen, data, {"sfc_core": sfc_res})
    runs.append((scen.name, sfc_res, dist_res, io_res))
    all_reports += (check_run(sfc_res, strict=False)
                    + check_distribution(dist_res) + check_input_output(io_res))

worst = max((r.max_residual for r in all_reports), default=0.0)
all_pass = all(r.passed for r in all_reports)

# --------------------------------------------------------------------------- #
# Header + gate
# --------------------------------------------------------------------------- #
st.title("AGORA — EU economy scenario sandbox")
live_n = sum(1 for v in sources.values() if v == "live")
st.caption(f"{geo} {year} · data: {live_n}/{len(sources)} live, "
           f"{len(sources)-live_n} snapshot · horizon {horizon}y · "
           f"modules: SFC core (open) + distribution + input-output + AI-shock")

c1, c2, c3 = st.columns(3)
(c1.success if all_pass else c1.error)(
    "Consistency gate: PASSED" if all_pass else "Consistency gate: FAILED")
c2.metric("Worst residual (MEUR)", f"{worst:.2e}",
          help="Largest discrepancy across all periods/scenarios and the fx, "
               "decile, and sectoral reconciliation checks. Near-zero = books close.")
c3.metric("Net exports (baseline)", f"{p.targets['net_exports']:,.0f} MEUR",
          help="Inside the books — rest-of-world sector active; accumulates as "
               "net foreign assets.")

# --------------------------------------------------------------------------- #
# Scenario picker
# --------------------------------------------------------------------------- #
all_names = [r[0] for r in runs]
chosen = st.multiselect("Scenarios to compare", all_names, default=all_names)
if not chosen:
    st.warning("Select at least one scenario.")
    st.stop()
sel = [r for r in runs if r[0] in chosen]
macro = frame(sel, "sfc")
dist = frame(sel, "dist")


def chart(df, metric, title, col):
    sub = df[df.metric == metric].pivot(index="year", columns="scenario", values="value")
    with col:
        st.markdown(f"**{title}**")
        st.line_chart(sub, height=230)


st.subheader("Macro (open economy)")
cc = st.columns(2)
chart(macro, "gdp", "GDP (MEUR)", cc[0])
chart(macro, "consumption", "Household consumption (MEUR)", cc[1])
chart(macro, "net_exports", "Net exports (MEUR)", cc[0])
chart(macro, "nfa_gdp", "Net foreign assets (% of GDP)", cc[1])
chart(macro, "gov_debt_gdp", "Government debt (% of GDP)", cc[0])
chart(macro, "labour_share", "Labour share (%)", cc[1])

st.subheader("Distribution — who wins & loses")
st.caption("Personal income distribution anchored at the observed Gini, shifting "
           "with the household capital share (β) and UBI intensity (γ). Decile "
           "incomes reconcile to the macro household disposable income.")
dc = st.columns(3)
chart(dist, "gini_personal", "Personal Gini", dc[0])
chart(dist, "poverty_rate", "At-risk-of-poverty rate", dc[1])
chart(dist, "palma_ratio", "Palma (top 10% / bottom 40%)", dc[2])

last_year = sel[0][2].periods[-1].year
share_tbl = {n: [d.periods[-1].reported[f"decile_share_{k}"] * 100
                 for k in range(1, 11)] for n, _s, d, _io in sel}
st.markdown(f"**Final-year ({last_year}) income share by decile** "
            "(D1 = poorest 10% … D10 = richest)")
st.bar_chart(pd.DataFrame(share_tbl, index=[f"D{k}" for k in range(1, 11)]),
             height=240)

# --------------------------------------------------------------------------- #
# Production structure (input-output)
# --------------------------------------------------------------------------- #
io_meta = next((r[3].meta for r in sel if r[3] and r[3].meta), None)
if io_meta:
    sectors = io_meta["sectors"]
    n = len(sectors)
    st.subheader("Production structure (input-output)")
    st.caption("The macro output is decomposed across sectors (Leontief). An "
               "'AI hits sector X' shock concentrates the labour-share fall in "
               "high automation-exposure sectors. Sectoral value added reconciles "
               "to GDP.")
    # final-year sectoral labour share, by scenario
    ls_tbl = {n_: [r.periods[-1].reported[f"lshare_{s+1}"]
                   for s in range(n)]
              for n_, _s, _d, r in sel if r and r.periods}
    st.markdown(f"**Final-year ({last_year}) sectoral labour share** "
                "(AI-exposed sectors shed labour share fastest)")
    st.bar_chart(pd.DataFrame(ls_tbl, index=sectors), height=260)
    # output multipliers (structural; same across scenarios)
    mult = io_meta.get("multipliers", {})
    expo = io_meta.get("automation_exposure", {})
    st.markdown("**Sector output multipliers & AI exposure**")
    st.dataframe(pd.DataFrame({
        "Output multiplier": {k: round(v, 2) for k, v in mult.items()},
        "AI exposure (0-1)": {k: round(v, 2) for k, v in expo.items()},
    }), width="stretch")

# --------------------------------------------------------------------------- #
# Side-by-side comparison
# --------------------------------------------------------------------------- #
st.subheader("Side-by-side — final year")


def finals(tup):
    m, d = tup[1].periods[-1].reported, tup[2].periods[-1].reported
    return {
        "GDP (MEUR)": m["gdp"], "Consumption (MEUR)": m["consumption"],
        "Net exports/GDP %": 100 * m["net_exports"] / m["gdp"],
        "NFA/GDP %": m["nfa_gdp"], "Debt/GDP %": m["gov_debt_gdp"],
        "Personal Gini": d["gini_personal"], "Poverty %": d["poverty_rate"] * 100.0,
        "Palma": d["palma_ratio"],
    }


vals = {r[0]: finals(r) for r in sel}
metrics = list(next(iter(vals.values())).keys())
comp = pd.DataFrame({n: [vals[n][m] for m in metrics] for n in chosen}, index=metrics)
st.dataframe(comp.map(lambda v: f"{v:,.2f}"), width="stretch")
if "Baseline" in chosen and len(chosen) > 1:
    st.markdown("**Δ vs Baseline** (positive = higher than baseline)")
    delta = comp.drop(columns=["Baseline"]).sub(comp["Baseline"], axis=0)
    st.dataframe(delta.map(lambda v: f"{v:+,.2f}"), width="stretch")

# --------------------------------------------------------------------------- #
# Validation + assumptions
# --------------------------------------------------------------------------- #
with st.expander("Baseline validation — does it reproduce the national targets?"):
    base_run = next(r for r in runs if r[0] == "Baseline")
    m0, d0, t = base_run[1].periods[0].reported, base_run[2].periods[0].reported, p.targets
    seed = 100.0 * (p.M_w0 + p.M_k0) / t["gdp"]
    checks = [("GDP (C+I+G+X-M)", t["gdp_expenditure"], m0["gdp"]),
              ("Exports", t["exports"], m0["exports"]),
              ("Imports", t["imports"], m0["imports"]),
              ("Net exports", t["net_exports"], m0["net_exports"]),
              ("Household consumption", t["hh_consumption"], m0["consumption"]),
              ("Investment (GFCF)", t["gfcf"], m0["investment"]),
              ("Government expenditure", t["gov_consumption"], m0["gov_expenditure"]),
              ("Labour share (%)", t["labour_share"], m0["labour_share"]),
              ("Gov debt seed / full GDP (%)", t["gov_debt_gdp"], seed),
              ("Personal Gini (x100)", t["gini_disp_income"], d0["gini_personal"] * 100.0)]
    vrows = [{"Metric": nm, "Target": f"{tg:,.1f}", "Model": f"{mo:,.1f}",
              "Rel err": f"{abs(mo-tg)/(abs(tg) or 1)*100:.3f}%",
              "OK": "✅" if abs(mo-tg)/(abs(tg) or 1) <= 0.02 else "❌"}
             for nm, tg, mo in checks]
    st.dataframe(pd.DataFrame(vrows), hide_index=True, width="stretch")

with st.expander("Assumptions & data sources (inspectable + swappable)"):
    bound = series_for_geo(geo)
    prov = [{"Canonical series": c, "Value": f"{v:,.2f}",
             "DBnomics code": bound[c].hint() if c in bound else "",
             "Source": sources.get(c, ""), "URL": bound[c].source_url if c in bound else ""}
            for c, v in data.items() if c != "_sources"]
    st.markdown("**Data provenance**")
    st.dataframe(pd.DataFrame(prov), hide_index=True, width="stretch")
    st.caption(f"Scenario/structural assumptions (all swappable): β={beta} "
               f"(capital share → inequality), γ={gamma} (UBI → compression); "
               "labour-share path & capex growth per scenario; input-output is an "
               "illustrative coarse structure pending a live FIGARO pull.")

# --------------------------------------------------------------------------- #
# THE PINNED EXPERIMENT — Universal Basic Capital vs cash UBI (flow vs stock)
# --------------------------------------------------------------------------- #
st.subheader("Universal Basic Capital vs cash UBI — the flow-vs-stock test")
st.caption("Both arms face the same AI shock and apply the SAME intensity lever "
           f"(capital levy {int(capital_tax*100)}%) on capital income — equal-cost. "
           "Cash UBI hands the levy out as an equal per-capita transfer every year "
           "(pure FLOW). UBC converts the same value, in kind, into a citizens' "
           "capital endowment (the sovereign fund) whose profit share is paid out "
           "per capita (STOCK). The endowment compounds. Every period below is "
           "consistency-gated.")

_exp = make_ubc_experiment(p, horizon=horizon)
_cash = next(sc for sc in _exp if sc.name == "AI + Cash UBI")
_ubc = next(sc for sc in _exp if sc.name == "AI + Universal Basic Capital")
_cash_r, _ubc_r = core.run(_cash, data), core.run(_ubc, data)
_cd = dist_mod.run(_cash, data, {"sfc_core": _cash_r})
_ud = dist_mod.run(_ubc, data, {"sfc_core": _ubc_r})
_yrs = [per.year for per in _ubc_r.periods]

ec = st.columns(2)
ec[0].markdown("**Citizens' fund ownership share φ = fund capital / total capital**")
ec[0].line_chart(pd.DataFrame(
    {"UBC": [per.reported["swf_share"] for per in _ubc_r.periods]}, index=_yrs),
    height=230)
ec[1].markdown("**Annual benefit to citizens (MEUR): cash transfer vs fund dividend**")
ec[1].line_chart(pd.DataFrame({
    "Cash UBI transfer": [per.reported["transfer_pool"] for per in _cash_r.periods],
    "UBC dividend": [per.reported["swf_dividend"] for per in _ubc_r.periods]},
    index=_yrs), height=230)
ec2 = st.columns(2)
ec2[0].markdown("**Inequality (macro Gini): cash UBI vs UBC**")
ec2[0].line_chart(pd.DataFrame({
    "Cash UBI": [per.reported["gini"] for per in _cash_r.periods],
    "UBC": [per.reported["gini"] for per in _ubc_r.periods]}, index=_yrs), height=230)
ec2[1].markdown("**Top-10% WEALTH share — only UBC compresses it (cash UBI is a flow)**")
ec2[1].line_chart(pd.DataFrame({
    "Cash UBI": [pp.reported["top10_wealth_share"] for pp in _cd.periods],
    "UBC": [pp.reported["top10_wealth_share"] for pp in _ud.periods]},
    index=_yrs), height=230)
ec2[1].caption("Cash UBI redistributes income but never wealth; UBC moves the "
               "capital itself into citizens' hands.")

_cross = next((per.year for i, per in enumerate(_ubc_r.periods)
               if per.reported["swf_dividend"] > _cash_r.periods[i].reported["transfer_pool"]),
              None)
_g_cash0 = _cash_r.periods[0].reported["gini"]; _g_ubc_end = _ubc_r.periods[-1].reported["gini"]
_g_cash_end = _cash_r.periods[-1].reported["gini"]
st.info(
    f"**Read-out.** Cash UBI compresses inequality immediately (Gini {_g_cash0:.2f} "
    f"in year 1) and helps most in the first decade. UBC starts slow — it is "
    f"building the endowment — but its dividend overtakes the cash transfer in "
    + (f"**{_cross}**" if _cross else "—") +
    f", and by {_yrs[-1]} citizens own {_ubc_r.periods[-1].reported['swf_share']*100:.0f}% "
    f"of the capital stock, with the macro Gini at {_g_ubc_end:.2f} vs cash UBI's "
    f"{_g_cash_end:.2f}. The trade-off is real: redistribution (flow) is faster, "
    "predistribution (stock) compounds. This is a sandbox comparison, not a forecast, "
    "and it assumes the dilution leaves investment unchanged — an open question.")

# --------------------------------------------------------------------------- #
# PHASE 4 — multi-objective policy search & the trade-off (Pareto) frontier
# --------------------------------------------------------------------------- #
st.subheader("Policy search — the trade-off frontier (no single 'best')")
st.caption("Given the AI shock, every policy (no-policy / cash UBI / UBC across "
           "a capital-levy grid) is run through the full gated chain and scored "
           "on five objectives: growth, equality, stability, fiscal, resilience. "
           "The frontier is the set no other policy beats on every axis at once — "
           "the values judgement (which axis matters most) stays with you.")


class _GatedRun:
    def __init__(self, result, dist, reports):
        self.result, self.dist = result, dist
        self.consistent = all(r.passed for r in reports)
        self.max_residual = max((r.max_residual for r in reports), default=0.0)


def _gated_run(scen):
    _sfc = core.run(scen, data)
    _d = dist_mod.run(scen, data, {"sfc_core": _sfc})
    _io = io_mod.run(scen, data, {"sfc_core": _sfc})
    return _GatedRun(_sfc, _d, check_run(_sfc, strict=False)
                     + check_distribution(_d) + check_input_output(_io))


_pts = search_policies(_gated_run, p, horizon=horizon)
_pdf = pd.DataFrame([{
    "policy": pt.name, "form": pt.form,
    "GDP end (MEUR)": pt.metrics["gdp_end"],
    "Equality (1−Gini)": 1.0 - pt.metrics["gini"],
    "Growth volatility": pt.metrics["growth_vol"],
    "Debt/GDP %": pt.metrics["debt_gdp"],
    "Poverty": pt.metrics["poverty"],
    "Fund ownership φ": pt.metrics["swf_share"],
    "status": "on frontier" if pt.on_frontier else "dominated",
} for pt in _pts])

pc = st.columns(2)
with pc[0]:
    st.markdown("**Equality vs growth** (top-right is better; frontier highlighted)")
    st.scatter_chart(_pdf, x="GDP end (MEUR)", y="Equality (1−Gini)",
                     color="status", height=300)
with pc[1]:
    st.markdown("**Equality vs stability** (the core trade-off: UBC is more equal, "
                "cash UBI is smoother)")
    _pdf2 = _pdf.assign(**{"Stability (−vol)": -_pdf["Growth volatility"]})
    st.scatter_chart(_pdf2, x="Stability (−vol)", y="Equality (1−Gini)",
                     color="status", height=300)

st.markdown("**Pareto-optimal policies** (each is 'best' for *some* set of priorities)")
_front = _pdf[_pdf.status == "on frontier"].drop(columns=["status", "form"])
st.dataframe(_front.style.format({
    "GDP end (MEUR)": "{:,.0f}", "Equality (1−Gini)": "{:.3f}",
    "Growth volatility": "{:.3f}", "Debt/GDP %": "{:.1f}",
    "Poverty": "{:.3f}", "Fund ownership φ": "{:.2f}"}),
    hide_index=True, width="stretch")
st.caption(f"{len(_pts)} policies evaluated, all consistency-gated "
           f"(worst residual {max(pt.max_residual for pt in _pts):.1e} MEUR); "
           f"{int((_pdf.status=='on frontier').sum())} on the frontier. "
           "'No policy' is dominated. The frontier spans BOTH cash UBI (wins on "
           "stability) and UBC (wins on growth/equality/resilience) — there is no "
           "single best, only a trade-off you choose along.")

# --------------------------------------------------------------------------- #
# MULTI-REGION — the national vs global AI dividend (Q2)
# --------------------------------------------------------------------------- #
st.subheader("National vs global AI dividend — does it widen the gap between countries? (Q2)")
st.caption("Each country is a separately-gated open economy. A NATIONAL dividend "
           "pays each country's levy to its own citizens; a GLOBAL one pools the "
           "levies and pays an equal per-capita dividend across the combined "
           "population. The chart is the population-weighted Gini BETWEEN countries "
           "of per-capita disposable income — lower = countries are closer.")
from scout.checks import snapshot_geos as _snap_geos
from schema.accounts import AGGREGATE_GEOS as _AGG
# aggregates (EA20/EU27) are valid single-country runs but never bloc members
_avail = [g for g in _snap_geos() if g.upper() not in _AGG]
_bloc = st.multiselect("Countries in the bloc (auto-detected from your snapshots)",
                       _avail, default=_avail, key="q2_bloc")
if len(_bloc) < 2:
    st.info("Select at least two countries to compare the between-country gap.")
else:
    try:
        _mr = MultiRegion(geos=tuple(_bloc), year=int(year), allow_live=allow_live,
                          inv_elasticity=inv_elasticity)
        _form = "ubc" if ubc else "cash_ubi"
        _cmp = _mr.dividend_comparison(form=_form, tau=capital_tax,
                                       horizon=horizon, reinvest=ubc_reinvest)
        _yrs = list(range(int(year), int(year) + horizon))
        rc = st.columns([3, 2])
        with rc[0]:
            st.markdown(f"**Between-country gap — national vs global** — "
                        f"bloc {', '.join(_bloc)} · {_form} · τ={int(capital_tax*100)}%")
            st.line_chart(pd.DataFrame(
                {"National dividend": _cmp.gini_national,
                 "Global (pooled) dividend": _cmp.gini_global}, index=_yrs), height=260)
        with rc[1]:
            _s = _cmp.summary()
            st.metric("Between-country gap, end (national)",
                      f"{_s['gini_national_end']:.4f}")
            st.metric("…under global pooling", f"{_s['gini_global_end']:.4f}",
                      delta=f"-{_s['gap_narrowing_pct']:.0f}% gap",
                      delta_color="inverse")
        st.markdown("**End-horizon per-capita dividend & pooling transfer** "
                    "(transfer + = country receives under global pooling)")
        _tbl = pd.DataFrame({
            "National dividend p.c.": _cmp.div_pc_national,
            "Pooling transfer p.c.": _cmp.pooling_transfer_pc,
        }).sort_values("National dividend p.c.")
        st.dataframe(_tbl.style.format("{:+.4f}"), width="stretch")
        if _cmp.excluded:
            st.warning("Excluded as non-viable (entrepôt/financial-centre economies "
                       "whose trade ≫ GDP break the standalone closure): "
                       + ", ".join(_cmp.excluded) + ". Model them only inside the "
                       "tight-trade regional fixed point.")
        st.caption(f"Pooled per-capita dividend = {_cmp.div_pc_global:.4f}. A national "
                   "dividend hands the biggest cheque to the richest country; pooling "
                   "transfers to the poorest. Adding lower-income members widens the "
                   "national gap further (docs/MULTI-REGION.md).")
    except Exception as _exc:  # pragma: no cover
        st.info(f"Multi-region comparison unavailable: {_exc}")

# --------------------------------------------------------------------------- #
# UNCERTAINTY — Monte-Carlo bands (point estimates are over-precise)
# --------------------------------------------------------------------------- #
st.subheader("Uncertainty bands — ranges, not false-precise point numbers")
st.caption("Sweeps the uncertain assumptions (shock depth/speed, the β/γ "
           "elasticities, the C1 investment response, the MPC) and reports p5 / "
           "median / p95 of the outcomes. If two policies' bands don't overlap, "
           "the ranking between them is robust — not an artifact of one guess.")
if st.checkbox("Run Monte-Carlo (≈120 gated draws per policy; a few seconds)",
               value=False, key="run_mc"):
    import pandas as _pd
    _rows = []
    for _form, _lbl in (("none", "No policy"), ("cash_ubi", "Cash UBI"),
                        ("ubc", "UBC")):
        _b, _used, _sk = monte_carlo(geo, form=_form, tau=capital_tax,
                                     year=int(year), horizon=horizon, n=120, seed=1)
        _rows.append({
            "Policy": _lbl,
            "Gini (p5–p50–p95)": f"{_b['gini'].p5:.2f} – {_b['gini'].p50:.2f} – {_b['gini'].p95:.2f}",
            "Poverty %": f"{_b['poverty'].p5*100:.0f} – {_b['poverty'].p50*100:.0f} – {_b['poverty'].p95*100:.0f}",
            "Citizen wealth €/pp": f"{_b['citizen_wealth_pc'].p5:,.0f} – {_b['citizen_wealth_pc'].p50:,.0f} – {_b['citizen_wealth_pc'].p95:,.0f}",
            "draws": _used,
        })
    st.dataframe(_pd.DataFrame(_rows), hide_index=True, width="stretch")
    st.caption("Non-overlapping bands between UBC and cash UBI on Gini/poverty mean "
               "the verdict holds across the whole range of assumptions.")

st.caption("AGORA is a sandbox for comparing policies in an internally consistent "
           "accounting world — not a forecast. Every assumption is inspectable "
           "and swappable.")
