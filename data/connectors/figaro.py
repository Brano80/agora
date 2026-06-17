"""FIGARO / Eurostat input-output connector — the REAL production structure.

Replaces the illustrative 6-sector matrix with sourced Eurostat input-output
data, aggregated NACE-section -> AGORA's coarse sectors. Self-discovering by
design (the sandbox that wrote this is firewalled, so dataset/dimension codes
could not be verified): `probe()` reads the dataset structure from DBnomics
and the fetcher auto-detects the row/column industry dimensions; candidate
dataset codes are tried in order. Run `scripts/build_io.py --probe` first on a
networked machine; everything prints diagnostics rather than guessing silently.

Output: the io_{geo}.json shape modules/input_output.py loads, PLUS the real
technical-coefficient matrix "A" (the module uses it directly when present,
keeping the legacy supply-shares construction as fallback). Sectoral labour
shares come from nama_10_a64 (D1 compensation / B1G value added, 64 industries
-> 6 sectors). `automation_exposure` stays a documented ASSUMPTION.
"""
from __future__ import annotations

import datetime as _dt
import json
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

_API = "https://api.db.nomics.world/v22"

SECTORS = ["Agriculture", "Industry", "Construction", "Distribution & transport",
           "ICT, finance & business", "Public & other services"]
_LETTER = {"A": 0, "B": 1, "C": 1, "D": 1, "E": 1, "F": 2,
           "G": 3, "H": 3, "I": 3, "J": 4, "K": 4, "L": 4, "M": 4, "N": 4,
           "O": 5, "P": 5, "Q": 5, "R": 5, "S": 5, "T": 5, "U": 5}
# assumption, unchanged from the illustrative file (documented, swappable)
EXPOSURE = [0.3, 0.7, 0.2, 0.5, 0.9, 0.4]

# tried in order (probe-confirmed 2026-06-12: the naio_10_fcp_* FIGARO codes
# 404 on DBnomics; cp1750 = industry x industry but only 16 geos, no DE/FR;
# cp1700 = CPA product x product, 32 geos — the workhorse).
DATASET_CANDIDATES = ("naio_10_cp1750", "naio_10_cp1700")
STK_FLOW_CANDIDATES = ("DOM", "TOTAL")   # domestic matrix first: imports leak
# final-demand column codes (any that resolve are summed)
_FD_CODES = {"P3_S14", "P3_S13", "P3_S15", "P31_S14", "P31_S15", "P32_S13",
             "P3_S14_S15", "P51G", "P5M", "P52", "P53", "P6", "P61", "P62", "P7"}
_OUTPUT_ROWS = {"P1", "TOTAL"}
# accounting-row codes that share letter prefixes with NACE sections (B1G vs
# NACE B, D1 vs D35, P2 vs P85...) — ALWAYS checked before the letter map.
_SPECIAL = {"B1G", "B1GQ", "B2A3G", "D1", "D11", "D12", "D21", "D29", "D31",
            "D39", "D21X31", "P1", "P2", "P3", "P5", "P51G", "P5M", "P52",
            "P53", "P6", "P61", "P62", "P7", "IMP", "TOTAL", "OP_RES",
            "OP_NRES", "CIF_FOB", "TS_BP"} | _FD_CODES


_NACE_RE = None


def sector_of(code: str) -> Optional[int]:
    """Map a NACE/CPA industry code ('C10-C12', 'C10T12', 'J62_J63', 'L68A',
    'CPA_F', 'B', 'D35') to a coarse sector index; None for anything else.
    STRICT pattern: section letter + optional TWO-digit division blocks —
    accounting codes (B1G, B2A3N, B3G, D1, P1, P51G...) have single digits or
    mixed tails and can never match (probe-confirmed collision set, 2026-06-12)."""
    global _NACE_RE
    if _NACE_RE is None:
        import re
        _NACE_RE = re.compile(
            r"^([A-U])([0-9]{2}[A-Z]?([-_T][A-Z]?[0-9]{2}[A-Z]?)*)?$")
    c = code.upper()
    if c.startswith("CPA_"):
        c = c[4:]
    if c in _SPECIAL:
        return None
    m = _NACE_RE.match(c)
    return _LETTER.get(m.group(1)) if m else None


def _get(url: str, timeout: float = 60.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "agora/0.3"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


_PROBE_CACHE: Dict[str, Dict[str, List[str]]] = {}


def probe(dataset: str) -> Dict[str, List[str]]:
    """Read the dataset structure: {dimension_code: [sample values...]}.
    Memoised (the fetcher calls it per attempt). Run FIRST on a new setup."""
    if dataset in _PROBE_CACHE:
        return _PROBE_CACHE[dataset]
    payload = _get(f"{_API}/datasets/Eurostat/{dataset}")
    docs = payload.get("datasets", {})
    doc = (docs.get("docs") or [None])[0] if isinstance(docs.get("docs"), list) \
        else docs.get(f"Eurostat/{dataset}") or next(iter(docs.values()), None)
    if not doc:
        raise ValueError(f"dataset '{dataset}' not found on DBnomics")
    dims = doc.get("dimensions_values_labels") or doc.get("dimensions_labels") or {}
    order = doc.get("dimensions_codes_order") or list(dims.keys())
    out = {}
    for d in order:
        vals = dims.get(d)
        codes = list(vals.keys()) if isinstance(vals, dict) else \
            [v[0] for v in vals] if isinstance(vals, list) else []
        out[d] = codes
    _PROBE_CACHE[dataset] = out
    return out


def _page_series(dataset: str, dim_filter: Dict[str, List[str]],
                 timeout: float = 60.0) -> List[dict]:
    """Pull every series matching the filter, paging past the 1000-doc limit."""
    docs, offset = [], 0
    while True:
        q = urllib.parse.urlencode({
            "dimensions": json.dumps(dim_filter, separators=(",", ":")),
            "observations": "1", "limit": "1000", "offset": str(offset)})
        payload = _get(f"{_API}/series/Eurostat/{dataset}?{q}", timeout)
        batch = payload.get("series", {}).get("docs", [])
        docs += batch
        total = payload.get("series", {}).get("num_found", len(docs))
        offset += len(batch)
        if not batch or offset >= total:
            return docs


def _num(v) -> Optional[float]:
    """DBnomics serialises missing observations as None OR the string 'NA'."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _value_for_year(doc: dict, year: int) -> Optional[float]:
    periods = doc.get("period", []) or doc.get("original_period", [])
    for p, v in zip(periods, doc.get("value", [])):
        if str(p).startswith(str(year)):
            return _num(v)
    return None


def _years_in_docs(docs: List[dict]) -> set:
    yrs = set()
    for doc in docs:
        periods = doc.get("period", []) or doc.get("original_period", [])
        for p, v in zip(periods, doc.get("value", [])):
            if _num(v) is not None:
                try:
                    yrs.add(int(str(p)[:4]))
                except ValueError:
                    pass
    return yrs


def _pick_io_year(requested: int, available: set) -> int:
    """Symmetric IO tables (naio_10_cp1700) are BENCHMARK years (2010/2015/2020),
    so a requested off-benchmark year (e.g. 2019) is sparse. Prefer the requested
    year if present, else the nearest available year not later than requested+2,
    else the latest available."""
    if not available or requested in available:
        return requested
    not_far = [y for y in available if y <= requested + 2]
    return max(not_far) if not_far else max(available)


# dimensions that are NEVER the industry/product axis — guards against the
# freq='A' (annual) value colliding with NACE section A (agriculture), which made
# axis detection pick 'freq' as the row dimension (probe-confirmed 2026-06-14).
_META_DIMS = {"freq", "unit", "stk_flow", "geo", "time", "time_period",
              "currency", "obs_status", "decimals"}


def _detect_axes(dims: Dict[str, List[str]]) -> Tuple[Optional[str], Optional[str]]:
    """(row_dim, col_dim) for an IO table. Eurostat names them *_use (columns)
    and *_ava (rows: products/industries available/supplied) — detect by name
    first; fall back to 'a non-meta dim whose values map to NACE sectors'."""
    col_d = next((k for k in dims if "use" in k.lower()), None)
    row_d = next((k for k in dims if "ava" in k.lower() and k != col_d), None)
    if row_d is None:
        row_d = next((k for k in dims
                      if k != col_d and k.lower() not in _META_DIMS
                      and any(sector_of(v) is not None for v in dims[k])), None)
    return row_d, col_d


def fetch_io_cells(geo: str, year: int, dataset: str, stk_flow: str,
                   timeout: float = 60.0) -> Tuple[Dict[Tuple[str, str], float],
                                                   Tuple[str, str], int, int]:
    """Pull the table cells for geo, ONE ROW PER REQUEST. A whole-table filter
    makes DBnomics scan ~15k series in one query and TIME OUT (probe-confirmed);
    per-row requests return <=130 series each and stream fast. Only rows the
    aggregation uses are pulled: NACE industries + P1 + B1G. The symmetric table
    is benchmark-year only, so the YEAR is auto-selected to the nearest available
    (probed from the first populated row). Returns ({(row,col): value},
    (row_dim, col_dim), n_rows_pulled, used_year)."""
    dims = probe(dataset)
    if geo not in dims.get("geo", []):
        raise ValueError(f"{dataset}: geo {geo} not available "
                         f"(has {len(dims.get('geo', []))} geos)")
    row_d, col_d = _detect_axes(dims)
    if not (row_d and col_d):
        raise ValueError(f"cannot detect row/col dims among {list(dims)}")
    wanted = [v for v in dims[row_d]
              if sector_of(v) is not None
              or v.upper() in _OUTPUT_ROWS or v.upper() in ("B1G", "B1GQ")]

    def _row_filter(rv: str) -> Dict[str, List[str]]:
        f: Dict[str, List[str]] = {"geo": [geo], "unit": ["MIO_EUR"], row_d: [rv]}
        if stk_flow and "stk_flow" in dims:
            f["stk_flow"] = [stk_flow]
        return f

    # auto-select the year from whichever years populated rows carry. Probe a
    # BIG industry first (agriculture sub-products are often suppressed for a
    # given geo, which left the year stuck); accumulate until we have a few years.
    available: set = set()
    probe_rows = [r for r in ("CPA_C", "CPA_G", "CPA_J", "C", "G")
                  if r in dims.get(row_d, [])]
    probe_rows += [r for r in wanted if r not in probe_rows][:6]
    for rv in probe_rows:
        available |= _years_in_docs(_page_series(dataset, _row_filter(rv), timeout))
        if len(available) >= 3:
            break
    used_year = _pick_io_year(year, available)

    cells: Dict[Tuple[str, str], float] = {}
    for i, rv in enumerate(wanted):
        for doc in _page_series(dataset, _row_filter(rv), timeout):
            d = doc.get("dimensions", {})
            v = _value_for_year(doc, used_year)
            if v is not None:
                cells[(d.get(row_d, "?"), d.get(col_d, "?"))] = v
        if (i + 1) % 15 == 0:
            print(f"    ...{i + 1}/{len(wanted)} rows", flush=True)
    return cells, (row_d, col_d), len(wanted), used_year


def aggregate_io(cells: Dict[Tuple[str, str], float]) -> dict:
    """NACE-64 cell map -> coarse 6-sector Z, f, x, va. Pure function (tested
    offline). Output row P1 is used for x when present, else x = colsum + va
    cannot be known -> x = colsum(Z)+f-row heuristics are avoided: require P1
    or compute x = colsum(Z) + va from B1G row; LAST resort rowsum+fd."""
    n = len(SECTORS)
    Z = [[0.0] * n for _ in range(n)]
    f = [0.0] * n
    x = [0.0] * n
    va = [0.0] * n
    have_x = have_va = False
    for (r, c), v in cells.items():
        ru, cu = r.upper(), c.upper()
        rs = None if ru in _SPECIAL or ru in _OUTPUT_ROWS else sector_of(r)
        cs = None if cu in _SPECIAL else sector_of(c)
        if rs is not None and cs is not None:
            Z[rs][cs] += v
        elif rs is not None and cu in _FD_CODES:
            f[rs] += v
        elif ru in _OUTPUT_ROWS and cs is not None:
            x[cs] += v
            have_x = True
        elif ru in ("B1G", "B1GQ") and cs is not None:
            va[cs] += v
            have_va = True
    if not have_x:
        if have_va:
            x = [sum(Z[i][j] for i in range(n)) + va[j] for j in range(n)]
        else:
            x = [sum(Z[j][i] for i in range(n)) + f[j] for j in range(n)]
    if not have_va:
        va = [x[j] - sum(Z[i][j] for i in range(n)) for j in range(n)]
    return {"Z": Z, "f": f, "x": x, "va": va}


def fetch_sector_labour_shares(geo: str, year: int,
                               timeout: float = 60.0) -> Optional[List[float]]:
    """Sectoral labour shares from nama_10_a64: D1 / B1G per coarse sector."""
    try:
        docs = _page_series("nama_10_a64",
                            {"geo": [geo], "unit": ["CP_MEUR"],
                             "na_item": ["B1G", "D1"]}, timeout)
    except Exception:
        return None
    if not docs:
        return None
    coe = [0.0] * len(SECTORS)
    vag = [0.0] * len(SECTORS)
    for doc in docs:
        dims = doc.get("dimensions", {})
        ind = dims.get("nace_r2", "")
        s = sector_of(ind)
        if s is None or "-" not in ind and len(ind) == 1 and ind.upper() == "TOTAL":
            continue
        v = _value_for_year(doc, year)
        if v is None:
            continue
        if dims.get("na_item") == "D1":
            coe[s] += v
        elif dims.get("na_item") == "B1G":
            vag[s] += v
    if not any(vag):
        return None
    return [min(0.95, max(0.05, coe[s] / vag[s] if vag[s] else 0.55))
            for s in range(len(SECTORS))]


def inspect(geo: str, dataset: str, stk_flow: Optional[str] = None,
            timeout: float = 60.0) -> None:
    """Deep diagnostic for one (geo, dataset): for several representative rows it
    prints how many series come back, how many distinct COLUMNS, which YEARS
    carry data, and a sample series' full dimensions. This is what tells us why a
    fetch returns 'only N cells' — too few columns, wrong stk_flow/unit, or a
    year with no symmetric table. Run on a networked machine."""
    dims = probe(dataset)
    print(f"dataset {dataset}: dims = {list(dims)}")
    if geo not in dims.get("geo", []):
        print(f"  geo {geo} NOT in this dataset ({len(dims.get('geo', []))} geos)")
        return
    row_d, col_d = _detect_axes(dims)
    print(f"  detected row_d={row_d}  col_d={col_d}")
    wanted = [v for v in dims.get(row_d, [])
              if sector_of(v) is not None
              or v.upper() in _OUTPUT_ROWS or v.upper() in ("B1G", "B1GQ")]
    print(f"  {len(wanted)} 'wanted' rows; sample: {wanted[:6]}")
    # pick representative rows: a big industry if present, plus the first few
    probes = []
    for cand in ("CPA_C", "CPA_G", "C", "G"):
        if cand in dims.get(row_d, []):
            probes.append(cand)
    probes += [r for r in wanted[:3] if r not in probes]
    sfs = [stk_flow] if stk_flow else list(STK_FLOW_CANDIDATES) + [None]
    for sf in sfs:
        print()
        print(f"  --- stk_flow={sf} ---")
        for rv in probes[:4]:
            filt: Dict[str, List[str]] = {"geo": [geo], "unit": ["MIO_EUR"],
                                          row_d: [rv]}
            if sf and "stk_flow" in dims:
                filt["stk_flow"] = [sf]
            try:
                docs = _page_series(dataset, filt, timeout)
            except Exception as exc:
                print(f"    {rv}: query failed: {exc}")
                continue
            cols = sorted({d.get("dimensions", {}).get(col_d) for d in docs})
            yrs = sorted(_years_in_docs(docs))
            print(f"    {rv}: {len(docs)} docs, {len(cols)} distinct {col_d}, "
                  f"years {yrs[-8:]}")
            if docs:
                print(f"       sample dims: {docs[0].get('dimensions')}")
                # how many cols have a value in the latest year
                if yrs:
                    ly = yrs[-1]
                    nz = sum(1 for d in docs if _value_for_year(d, ly) is not None)
                    print(f"       {nz}/{len(docs)} docs have a {ly} value")


def build_io_structure(geo: str, year: int = 2019,
                       dataset: Optional[str] = None,
                       stk_flow: Optional[str] = None,
                       timeout: float = 60.0) -> Tuple[dict, dict]:
    """Build the io_{geo}.json dict from live Eurostat data. Returns
    (io_dict, report). Tries DATASET_CANDIDATES x STK_FLOW_CANDIDATES until one
    yields a usable table; report records what happened."""
    report = {"geo": geo.upper(), "year": year, "tried": [],
              "dataset": None, "stk_flow": None, "n_cells": 0,
              "labour_share_source": "illustrative-fallback"}
    cells, axes = None, None
    for ds in ([dataset] if dataset else DATASET_CANDIDATES):
        for sf in ([stk_flow] if stk_flow is not None else STK_FLOW_CANDIDATES):
            try:
                cells, axes, nd, used_year = fetch_io_cells(
                    geo, year, ds, sf, timeout)
                if len(cells) >= 100:                  # a real table, not crumbs
                    report.update(dataset=ds, stk_flow=sf, n_cells=len(cells),
                                  axes=list(axes), n_docs=nd, io_year=used_year)
                    break
                report["tried"].append(
                    f"{ds}/{sf}: only {len(cells)} cells (year {used_year})")
                cells = None
            except Exception as exc:
                report["tried"].append(f"{ds}/{sf}: {exc}")
                cells = None
        if cells:
            break
    if not cells:
        raise RuntimeError("no FIGARO/naio dataset resolved; run --probe and "
                           f"inspect: {report['tried']}")
    agg = aggregate_io(cells)
    n = len(SECTORS)
    Z, f, x, va = agg["Z"], agg["f"], agg["x"], agg["va"]
    A = [[(Z[i][j] / x[j] if x[j] else 0.0) for j in range(n)] for i in range(n)]
    # value-added coefficient = primary-input RESIDUAL = 1 - intermediate column
    # sum. This is the I-O accounting identity that makes the module's sectoral
    # VA sum to GDP EXACTLY (the reconciliation gate). The independent B1G/output
    # ratio does NOT satisfy it on real data (the domestic table omits imports +
    # net taxes), which is what failed validation. The real B1G/output ratio is
    # kept in meta as `va_coeff_observed` for transparency.
    colsum_A = [sum(A[i][j] for i in range(n)) for j in range(n)]
    va_coeff = [min(0.999, max(0.001, 1.0 - colsum_A[j])) for j in range(n)]
    va_coeff_observed = [round(va[j] / x[j], 4) if x[j] else None
                         for j in range(n)]
    tot_f = sum(f) or 1.0
    tot_z = sum(sum(r) for r in Z) or 1.0
    io_year = report.get("io_year", year)
    ls = fetch_sector_labour_shares(geo, io_year, timeout)
    if ls:
        report["labour_share_source"] = "nama_10_a64 (D1/B1G)"
    io = {
        "sectors": SECTORS,
        "A": A,
        "va_coeff": va_coeff,
        "supply_shares": [sum(Z[i]) / tot_z for i in range(n)],   # legacy fallback
        "final_demand_shares": [v / tot_f for v in f],
        "labour_share_sector": ls or [0.45, 0.55, 0.62, 0.6, 0.5, 0.7],
        "automation_exposure": EXPOSURE,
        "_meta": {
            "note": ("REAL Eurostat input-output structure, NACE-64 aggregated to "
                     "6 sectors; A used directly by the module. automation_exposure "
                     "remains a documented assumption."),
            "source": f"Eurostat/{report['dataset']} (stk_flow={report['stk_flow']}), "
                      f"{report['n_cells']} cells, pulled {_dt.date.today().isoformat()}",
            "labour_shares": report["labour_share_source"],
            "va_coeff_definition": "1 - intermediate column sum (primary-input "
                                   "residual; reconciles VA to GDP). Domestic "
                                   "table -> includes import+tax content.",
            "va_coeff_observed_B1G": va_coeff_observed,
            "geo": geo.upper(), "year": year,
            "io_year": report.get("io_year", year),
        },
    }
    return io, report
