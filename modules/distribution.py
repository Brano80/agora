"""Distribution module (Phase 2) - the personal income distribution layer.

Loose coupling, exactly as the docs prescribe: the macro core sets the
aggregates, this module distributes them. It reads the SFC core's per-period
net labour / net capital / disposable pools (via the run `context`) and turns
them into a 10-decile personal distribution.

Mechanism (reduced-form, transparent, anchored):
  * The personal Gini is anchored at the country's OBSERVED disposable-income
    Gini at the baseline (so year-0 reproduces reality by construction).
  * It then moves with two forces the macro model already produces:
       G_t = G0 + beta * (capital_share_t - capital_share_0)   # decoupling
                 - gamma * ubi_intensity_t                      # redistribution
    Higher capital share concentrates income at the top; a per-capita UBI
    compresses it. `beta` and `gamma` are inspectable, swappable elasticities
    (assumptions to be grounded empirically later, e.g. via the scout).
  * Given G_t, income is modelled as lognormal; decile shares, an at-risk-of-
    poverty rate (< 60% of median), the Palma and S80/S20 ratios follow.

Decile incomes always sum to the macro household disposable income, so the
consistency gate's reconciliation check holds by construction (and guards bugs).

A PolicyEngine/EUROMOD microsimulation adapter can later replace this behind the
same Module interface without touching the schema, gate, or dashboard.
"""
from __future__ import annotations

from math import exp, log, sqrt
from statistics import NormalDist
from typing import Dict, List, Optional

from modules.interface import Module, Scenario, RunResult, PeriodState
from modules.sfc_core import SFCCore

_N = NormalDist()
N_DECILES = 10


def _sigma_from_gini(g: float) -> float:
    """Lognormal shape parameter sigma implied by a Gini coefficient."""
    g = min(max(g, 1e-4), 0.95)
    return sqrt(2.0) * _N.inv_cdf((1.0 + g) / 2.0)


def decile_shares(gini: float) -> List[float]:
    """Income share of each of 10 equal-population deciles (ascending) for a
    lognormal distribution with the given Gini. Shares sum to 1."""
    sigma = _sigma_from_gini(gini)
    shares, prev = [], 0.0
    for d in range(1, N_DECILES + 1):
        if d == N_DECILES:
            cum = 1.0
        else:
            # Lorenz curve of lognormal: L(p) = Phi(Phi^-1(p) - sigma)
            cum = _N.cdf(_N.inv_cdf(d / N_DECILES) - sigma)
        shares.append(cum - prev)
        prev = cum
    return shares


def grouped_gini(shares: List[float]) -> float:
    n = len(shares)
    return (2.0 * sum((i + 1) * s for i, s in enumerate(shares)) - (n + 1)) / n


def poverty_rate(gini: float) -> float:
    """At-risk-of-poverty headcount: share below 60% of the median, lognormal."""
    sigma = _sigma_from_gini(gini)
    return _N.cdf(log(0.6) / sigma) if sigma > 0 else 0.0


# --- EXPLICIT TRANSFER INCIDENCE (2026-06-11 review fix) ------------------- #
# Total income = flat universal per-capita transfer + lognormal MARKET income.
# Adding a constant to every income preserves ranking, so deciles coincide with
# the market deciles, and three things follow EXACTLY (no assumed elasticity):
#   shares:  s_d(total) = 0.1*t + (1-t)*s_d(market),   t = transfer / total
#   gini:    G(total)   = G(market) * (1 - t)          (mean-shift property)
#   poverty: the transfer is a FLOOR - the AROP rate is the lognormal mass
#            below (0.6*median_total - transfer), ZERO once the transfer alone
#            clears the 60%-of-median line. This replaces the old reduced-form
#            gamma compression, which had no floor and overstated how fast
#            poverty falls at low transfer levels while missing the hard zero.
def shifted_decile_shares(g_mkt: float, t_share: float) -> List[float]:
    """Decile shares of (flat transfer + lognormal market income)."""
    base = decile_shares(g_mkt)
    return [0.1 * t_share + (1.0 - t_share) * s for s in base]


def shifted_gini(g_mkt: float, t_share: float) -> float:
    """Exact Gini of (flat transfer + lognormal market income)."""
    return g_mkt * (1.0 - min(max(t_share, 0.0), 1.0))


def shifted_poverty(g_mkt: float, t_share: float) -> float:
    """AROP (<60% of median) under a flat transfer t_share of total income."""
    t = min(max(t_share, 0.0), 0.999)
    if t <= 0.0:
        return poverty_rate(g_mkt)
    sigma = _sigma_from_gini(g_mkt)
    if sigma <= 0:
        return 0.0
    m_bar = 1.0 - t                          # market mean (total income = 1)
    mu = log(m_bar) - 0.5 * sigma * sigma    # lognormal location for that mean
    med_x = exp(mu)                          # market median
    cut = 0.6 * (t + med_x) - t              # market income below which poor
    if cut <= 0.0:
        return 0.0                           # transfer alone clears the line
    return _N.cdf((log(cut) - mu) / sigma)


class DistributionModule(Module):
    name = "distribution"

    def __init__(self, beta: float = 0.13, gamma: float = 0.5,
                 base_year: int = 2019, sfc: Optional[SFCCore] = None,
                 gini_market_anchor: Optional[float] = None,
                 omega: float = 0.15):
        # beta default 0.13 = the live OECD/IDD market-Gini within-country FE
        # estimate (2026-06-14, F15) - the conceptually-correct (pre-tax)
        # anchor. It is WEAK (R^2~0.02: the capital share barely moves market
        # inequality over 2010-24, far from the modelled labour-share-halving
        # shock), so the Monte-Carlo prior stays WIDE (0.1, 1.0); the UBC-vs-cash
        # verdict is band-separated across it (F12). Swappable as always.
        self.beta = beta          # capital-share -> inequality elasticity
        self.gamma = gamma        # UBI-intensity -> compression elasticity
        self.base_year = base_year
        self._sfc = sfc
        # OPTIONAL true MARKET-Gini anchor (e.g. the OECD IDD gini_market_oecd).
        # Default None = legacy behaviour: the reported gini_market is anchored
        # at the observed DISPOSABLE Gini (it understates true pre-tax inequality
        # by the redistribution wedge). When set, gini_market is anchored at the
        # real pre-tax level and the existing welfare state enters as a baseline
        # flat-transfer wedge (t0 = 1 - G0/anchor) so the baseline still
        # reproduces the observed disposable Gini exactly. Headline-affecting, so
        # OFF by default until explicitly enabled and re-reviewed.
        self.gini_market_anchor = gini_market_anchor
        # omega = capital-share -> WEALTH-concentration elasticity. beta drifts
        # MARKET INCOME inequality with the capital share; omega mirrors it on the
        # STOCK: as the capital share rises, wealth concentrates (differential
        # saving / r>g) even with NO policy. omega=0 reproduces the legacy
        # behaviour (no-policy wealth share frozen).
        #   GROUNDING: the cross-section (top-10 wealth share vs capital share, 27
        #   EU members) is UNINFORMATIVE - slope -0.26, R^2 0.06, wrong sign for
        #   the within-country mechanism (national wealth institutions confound it,
        #   exactly as for beta, F9/F15). So omega is NOT set from the cross-
        #   section; the default 0.15 is a CONSERVATIVE r>g / differential-saving
        #   value (DE no-policy top-10 share +~5pp over the 30y shock - modest vs
        #   observed historical wealth-concentration trends). Swappable; the
        #   Monte-Carlo prior spans 0.0-0.40 so the verdict is robust across it.
        self.omega = omega

    def declares_inputs(self) -> List[str]:
        return ["hh_disposable", "net_wages", "net_profits", "ubi",
                "transfer_pool", "gini_disp_income"]

    def declares_outputs(self) -> List[str]:
        outs = ["gini_personal", "poverty_rate", "palma_ratio", "s80s20_ratio",
                "top10_share", "bottom40_share", "bottom10_share",
                "capital_share_hh", "ubi_intensity", "hh_disposable",
                "top10_wealth_share", "bottom50_wealth_share", "wealth_gini"]
        outs += [f"decile_income_{d}" for d in range(1, N_DECILES + 1)]
        outs += [f"decile_share_{d}" for d in range(1, N_DECILES + 1)]
        return outs

    @staticmethod
    def _capital_share(rep: Dict[str, float]) -> float:
        nl, nk = rep.get("net_wages", 0.0), rep.get("net_profits", 0.0)
        denom = nl + nk
        return nk / denom if denom else 0.0

    def run(self, scenario: Scenario, data: Dict[str, float],
            context: Optional[dict] = None) -> RunResult:
        # Loose coupling: take the upstream SFC result; if called standalone,
        # run the SFC core ourselves so the module is self-sufficient.
        sfc_res = (context or {}).get("sfc_core")
        if sfc_res is None:
            sfc_res = (self._sfc or SFCCore(base_year=self.base_year)).run(
                scenario, data)

        G0 = float(data.get("gini_disp_income", 30.0)) / 100.0
        kappa0 = self._capital_share(sfc_res.periods[0].reported)
        # When a true market anchor is supplied, M0 anchors market inequality and
        # the baseline redistribution wedge t0 makes disposable reproduce G0.
        M0 = self.gini_market_anchor
        t0 = max(0.0, 1.0 - G0 / M0) if (M0 and M0 > 0) else 0.0
        # dynamic WEALTH distribution: the citizens' fund socialises capital
        # (phi), moving it from concentrated private hands to an equally-held
        # endowment, so the top-10% WEALTH share falls from the observed
        # baseline toward the equal floor (10%).
        w10_0 = float(data.get("top10_wealth_share", 0.60))

        periods: List[PeriodState] = []
        for per in sfc_res.periods:
            rep = per.reported
            yd = rep.get("hh_disposable", 0.0)
            kappa = self._capital_share(rep)
            # universal per-capita transfer = cash UBI pool OR the UBC
            # sovereign-fund dividend; both compress the distribution.
            transfer = rep.get("transfer_pool", rep.get("ubi", 0.0))
            ubi_int = (transfer / yd) if yd else 0.0

            # MARKET inequality drifts with the capital share (beta); the
            # transfer's effect is now EXPLICIT incidence, not an elasticity.
            # Anchor at the true pre-tax level when given (M0), else at the
            # observed-disposable level (legacy). The baseline welfare wedge t0
            # is folded into the transfer share so disposable still hits G0.
            anchor0 = M0 if (M0 and M0 > 0) else G0
            G_mkt = anchor0 + self.beta * (kappa - kappa0)
            G_mkt = min(max(G_mkt, 0.05), 0.95)
            t_share = min(max(t0 + ubi_int, 0.0), 0.95)
            G = shifted_gini(G_mkt, t_share)

            shares = shifted_decile_shares(G_mkt, t_share)
            reported: Dict[str, float] = {
                "gini_personal": G,  # modeled Gini (anchored exactly at the observed baseline)
                "poverty_rate": shifted_poverty(G_mkt, t_share),
                "gini_market": G_mkt,
                "palma_ratio": shares[9] / sum(shares[0:4]) if sum(shares[0:4]) else 0.0,
                "s80s20_ratio": (shares[8] + shares[9]) / (shares[0] + shares[1])
                if (shares[0] + shares[1]) else 0.0,
                "top10_share": shares[9],
                "bottom40_share": sum(shares[0:4]),
                "bottom10_share": shares[0],
                "capital_share_hh": kappa,
                "ubi_intensity": ubi_int,
                "hh_disposable": yd,
            }
            # WEALTH (stock) distribution — the dimension UBC actually targets.
            phi = rep.get("swf_share", 0.0)
            # (1) ENDOGENOUS concentration: wealth concentrates as the capital
            #     share rises (omega) - happens even with no policy. (2) SOCIAL-
            #     ISATION: the citizens' fund moves capital into equal hands (phi).
            w10_market = w10_0 + self.omega * (kappa - kappa0)
            w10_market = min(max(w10_market, 0.10), 0.99)
            w10 = w10_market - (w10_market - 0.10) * phi   # socialised capital is equal-held
            w10 = min(max(w10, 0.10), 0.99)
            # 2-group (top 10% vs bottom 90%) wealth Gini from the top share
            top_pc, rest_pc = w10 / 0.10, (1.0 - w10) / 0.90
            wealth_gini = 0.10 * 0.90 * abs(top_pc - rest_pc)   # mean = 1 by construction
            reported["top10_wealth_share"] = w10
            reported["bottom50_wealth_share"] = max(0.0, (1.0 - w10) * (0.50 / 0.90))
            reported["wealth_gini"] = wealth_gini
            for d in range(N_DECILES):
                reported[f"decile_income_{d + 1}"] = shares[d] * yd
                reported[f"decile_share_{d + 1}"] = shares[d]

            periods.append(PeriodState(year=per.year, tfm={}, bsm={},
                                       reported=reported))

        return RunResult(
            module=self.name, scenario=scenario.name, geo=scenario.geo,
            periods=periods,
            meta={
                "beta": self.beta, "gamma": self.gamma, "G0": G0,
                "kappa0": kappa0, "n_deciles": N_DECILES,
                "gini_market_anchor": M0, "baseline_redistribution_wedge": t0,
                "notes": {
                    "model": "Lognormal MARKET income (Gini anchored at the "
                             "observed baseline, drifting with the household "
                             "capital share via beta) + EXPLICIT flat-transfer "
                             "incidence: shares, Gini and the poverty FLOOR "
                             "follow exactly from transfer/total income.",
                    "gini": "gini_personal = G_market * (1 - transfer share), "
                            "exact for a mean shift. beta remains the one "
                            "swappable assumption; gamma is DEPRECATED/unused "
                            "(replaced by exact incidence).",
                    "reconcile": "Decile incomes sum to hh_disposable by "
                                 "construction; the gate verifies it each period.",
                },
            },
        )
