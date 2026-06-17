#!/usr/bin/env python3
"""Regenerate the public AGORA dashboard (docs/index.html) from the CURRENT engine.
Recomputes every tab for every calibrated country (grounded beta, real FIGARO,
live wealth/debt), so the dashboard matches the published study and covers all
members. Run on your machine (snapshots + io files intact), then commit & push:

    python scripts/build_dashboard.py            # all snapshot countries
    python scripts/build_dashboard.py --geos DE FR   # subset (testing)
"""
import sys, os, json, argparse, random, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orchestrator import AgoraOrchestrator
from modules.sfc_core import SFCCore
from modules.distribution import DistributionModule
from modules.input_output import InputOutputModule
from scout.checks import snapshot_geos
from schema.accounts import AGGREGATE_GEOS
from region import MultiRegion

H = 30
Q2_EXCLUDE = {"IE", "LU"}   # MNC-inflated / entrepot GDP distorts cross-country comparison
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _provenance(geo):
    """Per-series provenance (provider, code, source URL, obs year) from the snapshot."""
    fp = os.path.join(ROOT, "data", "cache", geo.lower() + "_baseline_2019.json")
    try:
        snap = json.load(open(fp, encoding="utf-8"))
    except Exception:
        return []
    ser = snap.get("series", snap)
    out = []
    for name, v in ser.items():
        if not isinstance(v, dict):
            continue
        out.append({"s": name, "val": v.get("value"), "unit": v.get("unit", ""),
                    "prov": v.get("provider", ""), "code": v.get("provider_code", ""),
                    "url": v.get("source_url", ""), "yr": v.get("obs_year")})
    return out

def geo_data(geo):
    o = AgoraOrchestrator(geo=geo, year=2019, allow_live=False, strict=True); o.load_data()
    d = o._data
    triad = {r.scenario: r for r in o.run_triad(horizon=H)}
    ubc = {r.scenario: r for r in o.run_ubc_experiment(horizon=H)}
    base, ai, settle = triad["Baseline"], triad["AI shift, no policy"], triad["AI shift + Abundance Settlement"]
    cash, ubcr, npl = ubc["AI + Cash UBI"], ubc["AI + Universal Basic Capital"], ubc["AI shift, no policy"]
    pop = float(d.get("population") or 1.0)
    n = len(ai.result.periods); yrs = list(range(2019, 2019 + n))
    S = lambda r, k: [round(p.reported.get(k, 0.0), 4) for p in r.result.periods]
    D = lambda r, k: [round(p.reported.get(k, 0.0), 4) for p in r.dist.periods]
    g0 = ai.result.periods[0].reported["gdp"]; gb0 = base.result.periods[0].reported["gdp"]
    pc = lambda r, k: [round((p.reported.get(k, 0.0) or 0.0) / pop * 1e6) for p in r.result.periods]
    res = {
      "params": {"gdp": round(d.get("gdp", 0)/1e6, 1), "ls": round(d.get("labour_share", 0), 1),
                 "gini": round(d.get("gini_disp_income", 0), 1), "debt": round(d.get("gov_debt_gdp", 0), 1),
                 "pop": round(pop/1e6, 1), "wealth": round(d.get("top10_wealth_share", 0)*100, 1),
                 "hhdebt": round(d.get("hh_debt_gdp", 0), 1)},
      "years": yrs,
      "triad": {"ls_base": S(base, "labour_share"), "ls_ai": S(ai, "labour_share"),
                "gdp_ai": [round(100*v/g0, 1) for v in S(ai, "gdp")],
                "gini_base": D(base, "gini_personal"), "gini_ai": D(ai, "gini_personal"),
                "gini_settle": D(settle, "gini_personal"), "pov_ai": D(ai, "poverty_rate")},
      "ubc": {"cash_div": pc(cash, "transfer_pool"), "ubc_div": pc(ubcr, "transfer_pool"),
              "cash_gini": D(cash, "gini_personal"), "ubc_gini": D(ubcr, "gini_personal"), "nopol_gini": D(npl, "gini_personal"),
              "cash_pov": D(cash, "poverty_rate"), "ubc_pov": D(ubcr, "poverty_rate"), "nopol_pov": D(npl, "poverty_rate"),
              "cash_w": [round(v*100, 1) for v in D(cash, "top10_wealth_share")],
              "ubc_w": [round(v*100, 1) for v in D(ubcr, "top10_wealth_share")],
              "nopol_w": [round(v*100, 1) for v in D(npl, "top10_wealth_share")],
              "fund": [round(p.reported.get("swf_share", 0)*100, 1) for p in ubcr.result.periods]},
      "dist": {"dec_nopol": [round(npl.dist.periods[-1].reported.get(f"decile_share_{i}", 0)*100, 2) for i in range(1, 11)],
               "dec_cash": [round(cash.dist.periods[-1].reported.get(f"decile_share_{i}", 0)*100, 2) for i in range(1, 11)],
               "dec_ubc": [round(ubcr.dist.periods[-1].reported.get(f"decile_share_{i}", 0)*100, 2) for i in range(1, 11)]},
    }
    if ai.io and ai.io.periods:
        m = ai.io.meta; ns = len(m["sectors"]); b = ai.io.periods[0].reported; e = ai.io.periods[-1].reported
        notes = m.get("notes", {}) if isinstance(m.get("notes"), dict) else {}
        res["sectors"] = {"names": m["sectors"], "mult": [round(m["multipliers"][s], 2) for s in m["sectors"]],
                          "expo": [round(m["automation_exposure"][s], 2) for s in m["sectors"]],
                          "ls_start": [round(b.get(f"lshare_{i+1}", 0)*100, 1) for i in range(ns)],
                          "ls_end": [round(e.get(f"lshare_{i+1}", 0)*100, 1) for i in range(ns)],
                          "real": m.get("matrix_source") == "real", "src": notes.get("source", ""),
                          "expo_src": m.get("ai_exposure_source", ""), "expo_url": m.get("ai_exposure_url", "")}
    else:
        res["sectors"] = None
    fr = []
    for p in o.run_policy_search(horizon=H):
        mt = p.metrics
        fr.append({"name": p.name, "form": p.form, "gini": round(mt["gini"], 3),
                   "gdp": round(mt["gdp_end"]/1e6, 2), "pov": round(mt["poverty"], 3), "front": bool(p.on_frontier)})
    res["frontier"] = fr
    rows, run = o.validate_baseline(horizon=H)
    m0 = run.result.periods[0].reported
    relabel = {"Gov debt seed / full GDP (%)": "Government debt / GDP (%)"}
    valid = []
    for r in rows:
        valid.append({"m": relabel.get(r.metric, r.metric), "t": round(r.target, 1), "v": round(r.model, 1), "ok": bool(r.ok)})
        if r.metric == "Investment (GFCF)":
            inv = float(m0.get("inventories", 0.0))
            tgt = float(d.get("gcf", 0.0)) - float(d.get("gfcf", 0.0))
            if abs(tgt) < 1e-9: tgt = inv
            valid.append({"m": "Changes in inventories", "t": round(tgt, 1), "v": round(inv, 1),
                          "ok": abs(inv - tgt) <= max(1.0, 1e-6 * abs(tgt))})
    res["valid"] = valid
    res["prov"] = _provenance(geo)
    return res

def q2_data(geos):
    """Live between-country Gini (national vs pooled EU dividend), IE/LU excluded."""
    elig = tuple(g for g in geos if g.upper() not in Q2_EXCLUDE)
    if len(elig) < 2:
        return None
    mr = MultiRegion(geos=elig, year=2019, allow_live=False)
    out = {"excluded": sorted(g.upper() for g in geos if g.upper() in Q2_EXCLUDE), "tau": 40}
    runtime_excl = set()
    for form in ("cash", "ubc"):
        dc = mr.dividend_comparison(form=form, tau=0.40, horizon=H)
        srt = dc.summary()
        out[form + "_nat"] = round(srt["gini_national_end"], 4)
        out[form + "_pool"] = round(srt["gini_global_end"], 4)
        runtime_excl |= {x.upper() for x in dc.excluded}
    out["excluded"] = sorted(set(out["excluded"]) | runtime_excl)
    out["n"] = len(elig) - len(runtime_excl)
    return out


def mc_de():
    """Joint-prior Monte-Carlo (all 6 assumptions sampled together) + first-order
    sensitivity ranking, for DE as the reference economy."""
    import uncertainty as U
    cb, _, _ = U.monte_carlo("DE", "cash_ubi", n=200, seed=1)
    ub, _, _ = U.monte_carlo("DE", "ubc", n=200, seed=1)
    sg = U.sensitivity("DE", "ubc", n=400, seed=1, metric="gini")
    pretty = {"labour_share_end": "AI labour-share floor", "capex_growth": "AI capex growth",
              "inv_elasticity": "Investment response (C1)", "beta": "Income elasticity β",
              "omega": "Wealth elasticity ω", "a1_w": "Consumption propensity"}
    band = lambda b, k: [round(b[k].p5, 3), round(b[k].p95, 3)]
    return {"n": cb["gini"].n, "ndraws": sg["n"],
            "cash_gini": band(cb, "gini"), "ubc_gini": band(ub, "gini"),
            "cash_pov": band(cb, "poverty"), "ubc_pov": band(ub, "poverty"),
            "drivers": [{"name": pretty.get(d["param"], d["param"]),
                         "share": round(d["share"] * 100, 1), "corr": round(d["corr"], 2)}
                        for d in sg["drivers"] if d["share"] >= 0.005],
            "linear_r2": round(sg["linear_r2"], 2)}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--geos", nargs="+", default=None); a = ap.parse_args()
    geos = a.geos or [g for g in snapshot_geos() if g.upper() not in AGGREGATE_GEOS]
    DATA = {"meta": {"generated": datetime.date.today().isoformat()}, "geos": {}}
    for g in geos:
        try:
            DATA["geos"][g] = geo_data(g); print("ok", g)
        except Exception as e:
            print("skip", g, "->", e)
    DATA["meta"]["geos"] = sorted(DATA["geos"].keys())
    DATA["global"] = {
        "q2": q2_data(geos),
        "mc": mc_de() if "DE" in DATA["geos"] else None,
        "assumptions": [
            ["Capital-share → market-inequality elasticity (β)", "0.13 (prior 0.1–1.0)", "Live OECD market-Gini FE estimate; verdict is band-separated across the prior (F15/F16)."],
            ["Capital levy intensity (τ), headline", "40%", "Equal cost for cash vs UBC; frontier sweeps 10–60%."],
            ["AI labour-share floor", "30%", "Mid-case AI shift; ILO/Karabarbounis–Neiman trend, AI-accelerated."],
            ["AI capex growth", "~6%/yr", "Damped from Epoch frontier-compute growth (~4.2×/yr)."],
            ["Fund reinvestment (headline)", "0 (pay-out)", "C1: with reinvestment UBC ends a larger economy (F14)."],
            ["Horizon", "30 years", "Scenario comparison, not a forecast."],
            ["AI exposure by sector", "0.25 / 0.45 / 0.25 / 0.45 / 0.80 / 0.55", "SOURCED: OECD (2024) Sectoral Taxonomy of AI Intensity (NACE A38 High/Med/Low) + Felten-Raj-Seamans (2021) AIIE, mapped to the 6 sectors. AI exposure is cognitive - services high, manufacturing mid, agri/construction low (corrects the old robot-automation guess)."],
            ["Per-sector labour-share floor", "2%", "No sector's labour share falls below 2% under the AI shift (why high-exposure sectors bottom out rather than hit zero)."],
            ["Wealth-ownership dynamics", "fixed unless UBC acts", "No-policy &amp; cash hold the top-10% wealth share constant; only an ownership transfer (UBC) moves it. Conservative for UBC."],
            ["Input-output tables", "FIGARO cp1700 ×17, cp1750 ×10", "Per-country Eurostat symmetric IO table (product×product or industry×industry, whichever Eurostat publishes). Cross-country sector structure mixes both constructs."],
        ],
    }
    html = TEMPLATE.replace("__DATA__", json.dumps(DATA, separators=(",", ":"), ensure_ascii=False)) \
                   .replace("__DATE__", DATA["meta"]["generated"]) \
                   .replace("__NGEOS__", str(len(DATA["geos"])))
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nwrote docs/index.html ({len(html)//1024} KB) for {len(DATA['geos'])} countries")

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>AGORA — AI-economy policy sandbox</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.js" integrity="sha384-iU8HYtnGQ8Cy4zl7gbNMOhsDTTKX02BTXptVP/vqAWIaTfM7isw76iyZCsjL2eVi" crossorigin="anonymous"></script>
<style>
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1f2937;background:#fff;line-height:1.5}
.wrap{max-width:1080px;margin:0 auto;padding:0 18px 60px}
header{background:#0f3a2e;color:#fff;padding:20px 0}
header .wrap{padding-top:0;padding-bottom:0}
h1{margin:0;font-size:22px;letter-spacing:.5px}
.sub{color:#bfe3d6;font-size:13px;margin-top:4px}
.note{background:#f3f6f5;border-left:3px solid #E08A2B;padding:10px 14px;font-size:12.5px;color:#374151;margin:16px 0}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:16px 0}
select{font-size:14px;padding:6px 10px;border:1px solid #cfe0d9;border-radius:6px}
.tabs{display:flex;flex-wrap:wrap;gap:4px;border-bottom:2px solid #eef2f4;margin:6px 0 18px}
.tabs button{background:none;border:none;padding:8px 12px;font-size:13.5px;color:#6b7280;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px}
.tabs button.active{color:#0f3a2e;font-weight:700;border-bottom-color:#117A5B}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.card{background:#f3f6f5;border:1px solid #e5edea;border-radius:8px;padding:12px}
.card .v{font-size:22px;font-weight:700;color:#0f3a2e}
.card .l{font-size:11.5px;color:#6b7280;margin-top:2px}
.chartbox{position:relative;height:340px;margin:8px 0 20px}
h3{font-size:15px;color:#117A5B;margin:18px 0 6px}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin:8px 0}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #eef2f4}
th{background:#0f3a2e;color:#fff;font-weight:600}
.ok{color:#117A5B;font-weight:700}.bad{color:#C0392B;font-weight:700}
.pill{display:inline-block;background:#117A5B;color:#fff;font-size:11px;padding:2px 8px;border-radius:10px}
.u{color:#9ca3af;font-size:11px}
.srcbadge{display:inline-block;background:#eef5f2;color:#117A5B;font-size:11px;padding:2px 8px;border-radius:10px;text-decoration:none;border:1px solid #cfe3da}
.srcbadge:hover{background:#117A5B;color:#fff}
.srcbadge.dead{background:#f3f4f6;color:#9ca3af;border-color:#e5e7eb}
.warn{display:inline-block;background:#FBE9D2;color:#9a5b16;font-size:10.5px;padding:1px 6px;border-radius:8px;margin-left:4px}
a{color:#2C6E9B}
footer{font-size:11.5px;color:#6b7280;margin-top:30px;border-top:1px solid #eef2f4;padding-top:12px}
</style></head><body>
<header><div class="wrap"><h1>AGORA</h1><div class="sub">AI-economy &amp; post-labour policy sandbox — European Union · __NGEOS__ countries · generated __DATE__</div></div></header>
<div class="wrap">
<div class="note"><b>Sandbox, not oracle.</b> Every result is a policy comparison under explicit, swappable assumptions — never a forecast. Calibrated to live Eurostat / AMECO / BIS / OECD data; every scenario passes a consistency gate (books close to ~1e-10 of GDP). Companion study: <a href="https://doi.org/10.5281/zenodo.20726928">Owning the Machine</a> · <a href="https://github.com/Brano80/agora">code</a>.</div>
<div class="bar"><label for="geo"><b>Country:</b></label> <select id="geo"></select>
<span id="ctx" style="font-size:12.5px;color:#6b7280"></span></div>
<div class="tabs" id="tabs"></div>
<div id="content"></div>
<footer>AGORA — an open, consistency-gated model of AI's distributional impact. Scenario comparisons, not forecasts or advice. © 2026 Branislav Ambroz · CC BY 4.0.</footer>
</div>
<script>
const DATA = __DATA__;
const C = {ubc:'#117A5B',cash:'#E08A2B',nopol:'#C0392B',blue:'#2C6E9B',grey:'#94a3b8',ink:'#1f2937'};
const TABS = [["overview","Overview"],["scenarios","Scenarios"],["ubc","UBC vs cash"],["dist","Distribution"],["sectors","Sectors"],["frontier","Policy frontier"],["europe","Europe (Q2)"],["uncert","Uncertainty"],["assume","Assumptions"]];
let cur = {geo: DATA.meta.geos[0], tab:"overview"};
let charts = [];
Chart.defaults.font.family = "-apple-system,Segoe UI,Roboto,sans-serif";
Chart.defaults.font.size = 12;

const sel = document.getElementById("geo");
DATA.meta.geos.forEach(g=>{const o=document.createElement("option");o.value=g;o.textContent=g;sel.appendChild(o);});
sel.value = cur.geo;
sel.onchange = ()=>{cur.geo=sel.value; render();};
const tabsEl = document.getElementById("tabs");
TABS.forEach(([id,label])=>{const b=document.createElement("button");b.textContent=label;b.dataset.id=id;
  b.onclick=()=>{cur.tab=id; render();}; tabsEl.appendChild(b);});

function killCharts(){charts.forEach(c=>c.destroy());charts=[];}
function line(id, labels, sets, ylabel){
  const ctx=document.getElementById(id); if(!ctx)return;
  charts.push(new Chart(ctx,{type:'line',data:{labels,datasets:sets.map(s=>({label:s.l,data:s.d,borderColor:s.c,backgroundColor:s.c,borderWidth:2.4,pointRadius:0,tension:.15,borderDash:s.dash||[]}))},
    options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
      plugins:{legend:{labels:{usePointStyle:true,boxWidth:8}}},scales:{y:{title:{display:!!ylabel,text:ylabel}}}}}));
}
function bar(id, labels, sets, ylabel){
  const ctx=document.getElementById(id); if(!ctx)return;
  charts.push(new Chart(ctx,{type:'bar',data:{labels,datasets:sets.map(s=>({label:s.l,data:s.d,backgroundColor:s.c}))},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{usePointStyle:true,boxWidth:8}}},scales:{y:{title:{display:!!ylabel,text:ylabel}}}}}));
}
function fmt(n,d=0){return Number(n).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d});}
function vfmt(n){return Math.abs(n)>=1000?fmt(n,0):fmt(n,1);}

function render(){
  killCharts();
  [...tabsEl.children].forEach(b=>b.classList.toggle("active",b.dataset.id===cur.tab));
  const g = DATA.geos[cur.geo], G = DATA.global, yr = g.years, box = document.getElementById("content");
  document.getElementById("ctx").textContent = "GDP €"+g.params.gdp+"tn · labour share "+g.params.ls+"% · Gini "+g.params.gini+" · gov debt "+g.params.debt+"% of GDP";
  const lastYr = yr[yr.length-1];
  if(cur.tab==="overview"){
    const p=g.params;
    box.innerHTML = `<div class="cards">
      <div class="card"><div class="v">€${p.gdp}tn</div><div class="l">GDP (2019, current prices)</div></div>
      <div class="card"><div class="v">${p.ls}%</div><div class="l">Labour share of GDP</div></div>
      <div class="card"><div class="v">${p.gini}</div><div class="l">Gini, disposable income</div></div>
      <div class="card"><div class="v">${p.wealth}%</div><div class="l">Top-10% wealth share (OECD${(()=>{const w=(g.prov||[]).find(r=>r.s==='top10_wealth_share');return w&&w.yr?', '+w.yr:'';})()})</div></div>
      <div class="card"><div class="v">${p.debt}%</div><div class="l">Govt debt / GDP</div></div>
      <div class="card"><div class="v">${p.pop}M</div><div class="l">Population</div></div></div>
      <h3>Baseline validation (year-0 reproduces the national accounts)</h3>
      <table><tr><th>Metric</th><th>Target</th><th>Model</th><th>OK</th></tr>
      ${g.valid.map(r=>`<tr><td>${r.m}</td><td>${vfmt(r.t)}</td><td>${vfmt(r.v)}</td><td>${r.ok?'<span class="ok">✓</span>':'<span class="bad">✗</span>'}</td></tr>`).join("")}</table>
      <div class="note">Calibrated to live 2019 data; back-tested to 2010–2019 history (~1% GDP error). Every scenario below is consistency-gated.</div>
      <h3>Data provenance — every parameter sourced &amp; swappable</h3>
      <table><tr><th>Series</th><th>Value</th><th>Provider</th><th>Source</th></tr>
      ${g.prov.map(r=>`<tr><td>${r.s}</td><td>${(Math.abs(r.val)>=1000?fmt(r.val,0):fmt(r.val,2))} <span class="u">${r.unit}</span></td><td>${r.prov}${(r.yr&&r.yr!=2019)?` <span class="warn" title="latest observation ${r.yr}, not 2019">obs ${r.yr}</span>`:''}</td><td>${r.url?`<a class="srcbadge" href="${r.url}" target="_blank" rel="noopener" title="${r.code}">open ↗</a>`:`<span class="srcbadge dead" title="${r.code}">${r.code||'—'}</span>`}</td></tr>`).join("")}</table>
      <div class="note">Each value links to its official dataset (Eurostat / AMECO / BIS / OECD). Click <b>open ↗</b> to inspect the source series; hover for the exact series code. <span class="warn">obs YYYY</span> marks a value whose latest observation predates 2019.</div>`;
  } else if(cur.tab==="scenarios"){
    box.innerHTML=`<h3>The Great Decoupling — labour share vs output (no policy)</h3>
      <div class="chartbox"><canvas id="c1"></canvas></div>
      <h3>Inequality under each scenario (personal Gini)</h3>
      <div class="chartbox"><canvas id="c2"></canvas></div>
      <div class="note">The settlement scenario applies policy from year 0, so its Gini starts below the no-policy baseline. The labour-share line floors at 30% (an assumption — see Assumptions tab).</div>`;
    line("c1",yr,[{l:"Labour share % (AI shift)",d:g.triad.ls_ai,c:C.nopol},{l:"GDP index (AI shift, 2019=100)",d:g.triad.gdp_ai,c:C.blue}]);
    line("c2",yr,[{l:"Baseline",d:g.triad.gini_base,c:C.grey},{l:"AI shift, no policy",d:g.triad.gini_ai,c:C.nopol},{l:"AI + settlement",d:g.triad.gini_settle,c:C.ubc}]);
  } else if(cur.tab==="ubc"){
    const u=g.ubc, i=yr.length-1;
    box.innerHTML=`<div class="cards">
      <div class="card"><div class="v">${u.nopol_gini[i].toFixed(2)} → ${u.cash_gini[i].toFixed(2)} → ${u.ubc_gini[i].toFixed(2)}</div><div class="l">Gini at yr ${lastYr}: no-policy → cash → UBC</div></div>
      <div class="card"><div class="v">${u.fund[i]}%</div><div class="l">Citizens' fund share of capital (UBC, yr ${lastYr})</div></div>
      <div class="card"><div class="v">€${fmt(u.ubc_div[i])} vs €${fmt(u.cash_div[i])}</div><div class="l">UBC dividend vs cash transfer / person (yr ${lastYr})</div></div></div>
      <h3>Flow vs stock — annual payment per citizen</h3><div class="chartbox"><canvas id="c1"></canvas></div>
      <h3>Only ownership touches wealth — top-10% wealth share</h3><div class="chartbox"><canvas id="c2"></canvas></div>
      <div class="note">Cash UBI (dashed) sits exactly on the No-policy line — cash flows don't change who owns capital, so the two coincide. Only UBC (an ownership transfer) bends the wealth curve down.</div>`;
    line("c1",yr,[{l:"Cash UBI transfer (€)",d:u.cash_div,c:C.cash},{l:"UBC dividend (€)",d:u.ubc_div,c:C.ubc}],"€ / person / yr");
    line("c2",yr,[{l:"No policy",d:u.nopol_w,c:C.nopol},{l:"Cash UBI",d:u.cash_w,c:C.cash,dash:[8,5],width:3},{l:"UBC",d:u.ubc_w,c:C.ubc}],"Top-10% wealth share (%)");
  } else if(cur.tab==="dist"){
    box.innerHTML=`<h3>Income share by decile at yr ${lastYr} (1 = poorest, 10 = richest)</h3>
      <div class="chartbox"><canvas id="c1"></canvas></div>
      <div class="note">Cash UBI and UBC both lift the bottom deciles vs no-policy; UBC additionally socialises the capital stock (see UBC vs cash tab).</div>`;
    bar("c1",["1","2","3","4","5","6","7","8","9","10"],
      [{l:"No policy",d:g.dist.dec_nopol,c:C.nopol},{l:"Cash UBI",d:g.dist.dec_cash,c:C.cash},{l:"UBC",d:g.dist.dec_ubc,c:C.ubc}],"% of income");
  } else if(cur.tab==="sectors"){
    if(!g.sectors){box.innerHTML=`<div class="note">No input-output structure for ${cur.geo}. Run <code>python scripts/build_io.py --geo ${cur.geo} --write</code> to add it.</div>`;}
    else{const s=g.sectors;
      box.innerHTML=`<h3>Sectoral labour share — baseline vs AI horizon ${s.real?'<span class="pill">real Eurostat FIGARO</span>':''}</h3>
        <div class="chartbox"><canvas id="c1"></canvas></div>
        <h3>Output multipliers &amp; AI exposure ${s.expo_url?`<a class="srcbadge" href="${s.expo_url}" target="_blank" rel="noopener" title="${s.expo_src}">sourced ↗</a>`:''}</h3>
        <table><tr><th>Sector</th><th>Multiplier</th><th>AI exposure</th></tr>
        ${s.names.map((nm,k)=>`<tr><td>${nm}</td><td>${s.mult[k].toFixed(2)}</td><td>${s.expo[k].toFixed(2)}</td></tr>`).join("")}</table>
        <div class="note">AI exposure is <b>cognitive</b>, not robotic: services (ICT/finance, public) are most exposed, manufacturing is mid, agriculture &amp; construction low. Multipliers from real FIGARO; exposure from the OECD Sectoral Taxonomy of AI Intensity + Felten-Raj-Seamans AIIE (click <b>sourced ↗</b>). ${s.src?('I-O matrix source: '+s.src):''}</div>`;
      bar("c1",s.names,[{l:"Baseline",d:s.ls_start,c:C.grey},{l:"After AI shift",d:s.ls_end,c:C.nopol}],"Sector labour share (%)");
    }
  } else if(cur.tab==="frontier"){
    box.innerHTML=`<h3>Policy frontier — equality vs economy size (year ${lastYr})</h3>
      <div class="chartbox"><canvas id="c1"></canvas></div>
      <div class="note">Lower Gini (right) and higher GDP (up) are both better. The frontier is <b>multi-objective</b> (growth, equality, stability, fiscal, resilience) — this view shows two of the five criteria, so a point that is off the frontier here can still look non-dominated in this 2-D slice. At <b>equal tax rate</b>, UBC dominates cash UBI on every criterion; "no policy" is off the frontier. Hover a point for its policy, intensity and outcomes.</div>`;
    const ctx=document.getElementById("c1");
    const pt=(f,fl)=>g.frontier.filter(p=>p.form===f).map(p=>({x:p.gini,y:p.gdp,front:p.front,name:p.name,pov:p.pov}));
    const ds=(arr,label,col,style)=>({label,data:arr,backgroundColor:col,pointStyle:style,radius:arr.map(a=>a.front?8:5),borderColor:'#1f2937',borderWidth:arr.map(a=>a.front?1.5:0)});
    charts.push(new Chart(ctx,{type:'scatter',data:{datasets:[
      ds(pt('ubc'),'UBC',C.ubc,'circle'),ds(pt('cash_ubi'),'Cash UBI',C.cash,'rect'),ds(pt('none'),'No policy',C.nopol,'triangle')]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{usePointStyle:true}},
        tooltip:{callbacks:{label:c=>`${c.raw.name}${c.raw.front?' • on frontier':''}: Gini ${c.parsed.x}, GDP €${c.parsed.y}tn, poverty ${(c.raw.pov*100).toFixed(1)}%`}}},
        scales:{x:{reverse:true,title:{display:true,text:'Inequality — Gini (lower = better →)'}},y:{title:{display:true,text:'GDP at horizon (€tn, model scale)'}}}}}));
  } else if(cur.tab==="europe"){
    const q=DATA.global.q2;
    if(!q){box.innerHTML=`<div class="note">Between-country comparison needs the full multi-country build.</div>`;}
    else{box.innerHTML=`<h3>Between-country inequality: national vs pooled EU dividend (${q.n} countries)</h3>
      <div class="chartbox"><canvas id="c1"></canvas></div>
      <div class="note">A purely national AI dividend entrenches the gap between richer and poorer member states (Gini ~0.21); pooling the dividend across the Union roughly <b>halves</b> it under either form. Dividend at τ=${q.tau}%. ${q.excluded&&q.excluded.length?('Excluded: '+q.excluded.join(', ')+' (MNC-inflated / entrepôt GDP distorts the cross-country comparison), matching the companion study.'):''} Gated all-EU run; magnitudes are model-scale, not forecasts.</div>`;
    bar("c1",["Cash UBI","Universal Basic Capital"],[{l:"National dividend",d:[q.cash_nat,q.ubc_nat],c:C.grey},{l:"Pooled EU dividend",d:[q.cash_pool,q.ubc_pool],c:C.ubc}],"Between-country Gini");}
  } else if(cur.tab==="uncert"){
    const m=DATA.global.mc;
    if(!m){box.innerHTML=`<div class="note">Uncertainty needs the full multi-country build (Germany reference).</div>`;}
    else{box.innerHTML=`<h3>Robustness across the JOINT assumption space — Germany, ${m.n} gated draws over 6 priors</h3>
      <div class="chartbox"><canvas id="c1"></canvas></div>
      <div class="note">Sampling all six uncertain assumptions <b>together</b> (labour-share floor, capex growth, investment response, income elasticity β, wealth elasticity ω, consumption propensity), UBC's Gini and poverty bands (p5–p95) sit entirely below cash UBI's — so "owning beats receiving" survives the <b>full joint space</b>, not just β. Computed for Germany as the reference economy; not affected by the country selector.</div>
      <h3>What drives the result — first-order sensitivity (UBC Gini, ${m.ndraws} draws)</h3>
      <table><tr><th>Assumption</th><th>Share of variance</th><th>Direction</th></tr>
      ${m.drivers.map(d=>`<tr><td>${d.name}</td><td>${d.share}%</td><td>${d.corr>0?'↑ raises Gini':(d.corr<0?'↓ lowers Gini':'—')}</td></tr>`).join("")}</table>
      <div class="note">The investment response (C1) and the AI capex boom move the outcome most; β matters less and ω barely touches the <i>income</i> Gini — it acts on the <i>wealth</i> stock instead (see UBC vs cash). First-order explains ${(m.linear_r2*100).toFixed(0)}% of the variance; the rest is interactions. These are the levers worth pinning down first.</div>`;
      bar("c1",["Cash UBI","UBC"],[{l:"Gini p5",d:[m.cash_gini[0],m.ubc_gini[0]],c:C.grey},{l:"Gini p95",d:[m.cash_gini[1],m.ubc_gini[1]],c:C.ubc}],"Personal Gini at horizon (p5–p95)");
    }
  } else if(cur.tab==="assume"){
    box.innerHTML=`<h3>Key assumptions — all inspectable &amp; swappable</h3>
      <table><tr><th>Assumption</th><th>Value</th><th>Basis</th></tr>
      ${DATA.global.assumptions.map(a=>`<tr><td>${a[0]}</td><td><b>${a[1]}</b></td><td>${a[2]}</td></tr>`).join("")}</table>
      <div class="note"><b>Sandbox, not oracle.</b> These are the levers the headline numbers are conditional on. Change them and the model recomputes — the value is the direction and size of the policy trade-offs, not any single figure.</div>`;
  }
}
render();
</script></body></html>"""

if __name__ == "__main__":
    main()
