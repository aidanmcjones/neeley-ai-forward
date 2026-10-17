"""DECIDE move templates: cash-flow generators, probability structures, parameters, Part 1 feeds.

Spec: docs/quant_model.md Section 5 (equation 5.1, templates 5.3, five numbers 5.4, kill signals 5.6) and the
weight table 11.2. Dollar figures are USD millions. Time is monthly, tau = 1..horizon, with tau = 1..24 the decision
window; later months are the terminal value (TV) of the position held at month 24, valued under the same rules.

A template turns a parameter dict into a CashPlan: a list of Lines (one monthly cash stream each), the technical
probability events (phase readouts), and notes. decide.evaluate_move() discounts and scenario-weights the plan.

Line semantics (equation 5.1):
  kind "in"   incremental after-tax operating cash flow, weighted by P_alive(tau) and, when scaled, by the scenario
              revenue multiplier (0.8 / 1.0 / 1.2).  Negative amounts are allowed (e.g. net price given up).
  kind "out"  committed or phase-gated spend, weighted by P_reach(tau); never scenario-scaled.
  avoidable   contractually avoidable payments (milestones, CVRs); excluded from cash at risk.

Every constant below lives in the `decide_weights` block, each with a source comment and URL where the source is
one. DECIDE does not import the FIND worker's weights.py.
"""

from dataclasses import dataclass, field
from types import SimpleNamespace

# --------------------------------------------------------------------------------------------------------------
# decide_weights: every DECIDE constant, with source. REGISTRY maps name -> Benchmark for citation building.
# --------------------------------------------------------------------------------------------------------------

BIO = "https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf"
DAMODARAN = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html"
DAMODARAN_MARGIN = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/margin.html"   # gross margin, SG&A
BIO_P15 = BIO + "#page=15"     # Figure 9 (non-NME transition rates) is on PDF page 15 (review D7)
MOORE_JAMA = "https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2702287"   # Moore et al. 2018
CIDARA = "https://www.sec.gov/Archives/edgar/data/1610618/000119312525309970/d59361dsc14d9.htm"
FURIEX = "https://www.sec.gov/Archives/edgar/data/0001484478/000119312514225775/d727381ddefm14a.htm"


@dataclass
class Benchmark:
    name: str
    value: object
    unit: str
    source: str            # paper / report and the number as the source states it
    url: str = ""
    kind: str = "benchmark"   # benchmark | inference
    note: str = ""


REGISTRY = {}


def _b(name, value, unit, source, url="", kind="benchmark", note=""):
    REGISTRY[name] = Benchmark(name, value, unit, source, url, kind, note)
    return value


# Discounting and scenario weights (spec 5.1)
WACC = _b("wacc", 0.0785, "fraction per year", "Damodaran Drugs (Pharmaceutical), 228 firms, WACC 7.85%, Jan 2026", DAMODARAN)
P_SCENARIO = {
    "bear": _b("p_bear", 0.50, "probability", "Trinity 2023 US launches: 50% underperformed first-year forecasts",
               "https://www.trinitylifesciences.com/"),
    "base": _b("p_base", 0.11, "probability", "Trinity 2023 US launches: remaining 11% on forecast",
               "https://www.trinitylifesciences.com/"),
    "bull": _b("p_bull", 0.39, "probability", "Trinity 2023 US launches: 39% overperformed",
               "https://www.trinitylifesciences.com/"),
}
MULT_SCENARIO = {  # ZS success (>=120% of prelaunch forecast, year 3) and failure (<=80%) definitions
    "bear": _b("mult_bear", 0.8, "x revenue", "ZS: failure = year-3 sales <= 80% of prelaunch forecast", ""),
    "base": 1.0,
    "bull": _b("mult_bull", 1.2, "x revenue", "ZS: success = year-3 sales >= 120% of prelaunch forecast", ""),
}
SCENARIOS = ("bear", "base", "bull")
WINDOW = 24            # decision window, months (the case: "24-month CEO move")
PAYBACK_SEARCH = 120   # spec 5.4: payback searched to 120 months
POST_LAUNCH_MONTHS = 120  # spec 5.1: TV to LOE or 10 years after launch

# Clinical probabilities (BIO/Informa/QLS 2021)
NON_NME = {"ph1": _b("p_nonnme_ph1", 0.575, "probability", "BIO 2021 Figure 9 non-NME Phase I->II 57.5%", BIO_P15),
           "ph2": _b("p_nonnme_ph2", 0.375, "probability", "BIO 2021 Figure 9 non-NME Phase II->III 37.5%", BIO_P15),
           "ph3": _b("p_nonnme_ph3", 0.675, "probability", "BIO 2021 Figure 9 non-NME Phase III->NDA/BLA 67.5%", BIO_P15),
           "nda": _b("p_nonnme_nda", 0.915, "probability", "BIO 2021 Figure 9 non-NME NDA/BLA->approval 91.5%", BIO_P15)}
# BIO 2021 Figure 1, Phase I->II / II->III / III->NDA / NDA->approval, by therapeutic area
BIO_TA = {
    "hematology": (0.696, 0.481, 0.768, 0.931), "metabolic": (0.618, 0.450, 0.636, 0.875),
    "infectious disease": (0.578, 0.384, 0.640, 0.929), "ophthalmology": (0.716, 0.355, 0.512, 0.911),
    "autoimmune": (0.552, 0.314, 0.653, 0.941), "allergy": (0.564, 0.283, 0.647, 1.000),
    "gastroenterology": (0.467, 0.342, 0.571, 0.909), "respiratory": (0.559, 0.219, 0.645, 0.956),
    "psychiatry": (0.527, 0.268, 0.563, 0.912), "endocrine": (0.433, 0.266, 0.662, 0.863),
    "neurology": (0.477, 0.268, 0.531, 0.867), "oncology": (0.488, 0.246, 0.477, 0.920),
    "cardiovascular": (0.500, 0.210, 0.552, 0.825), "urology": (0.409, 0.150, 0.692, 0.846),
    "non-nme": (0.575, 0.375, 0.675, 0.915),
}
REGISTRY["bio_ta_rates"] = Benchmark("bio_ta_rates", BIO_TA, "probabilities", "BIO 2021 Figure 1 and Figure 9 transition rates by TA", BIO)

# Costs
TRIAL_COST_PLACEBO = _b("trial_cost_placebo", 28.8, "USD M per pivotal trial", "Moore et al. JAMA Intern Med 2018: placebo-controlled mean $28.8M",
                        "https://www.ajmc.com/view/more-than-100fold-cost-differences-found-for-pivotal-trials")
TRIAL_COST_ACTIVE = _b("trial_cost_active", 48.9, "USD M per pivotal trial", "Moore et al. 2018: active-comparator mean $48.9M",
                       "https://www.ajmc.com/view/more-than-100fold-cost-differences-found-for-pivotal-trials")
TRIAL_COST_MEDIAN = _b("trial_cost_median", 19.0, "USD M per pivotal trial", "Moore et al. 2018: median $19M (IQR 12.2-33.1)",
                       "https://www.raps.org/resource/phase-3-trial-costs-estimated-at-19m-study-finds.html")
TRIAL_COST_CARDIO = _b("trial_cost_cardio", 157.0, "USD M per pivotal trial", "Moore et al. 2018: cardiovascular pivotal trials mean $157M (driven by one $346.8M trial)",
                       MOORE_JAMA)   # the outsourcing-pharma article returned HTTP 410 (review D7)
REP_COST = _b("rep_cost", 176.5, "USD K per rep-year", "Rework 2025: developed-market loaded rep cost $134,000-219,000 (midpoint; vendor estimate)",
              "https://resources.rework.com/libraries/pharmaceutical-growth/pharma-field-sales-economics")
REP_RAMP_MONTHS = _b("rep_ramp_months", 18, "months", "Rework 2025: 12-24 month ramp to full productivity (midpoint)",
                     "https://resources.rework.com/libraries/pharmaceutical-growth/pharma-field-sales-economics")
DTC_TV_LOW = _b("dtc_tv_low", 260.0, "USD M per year", "iSpot via Fierce Pharma 2024: Wegovy >$260M TV spend",
                "https://www.fiercepharma.com/marketing/abbvies-skyrizi-takes-full-year-tv-ad-spending-crown-yet-again-jjs-tremfya-hot-pursuit")
DTC_TV_HIGH = _b("dtc_tv_high", 440.0, "USD M per year", "iSpot via Fierce Pharma 2025: Skyrizi nearly $440M",
                 "https://www.fiercepharma.com/marketing/abbvie-maintains-top-tv-ad-spend-spot-skyrizi-sees-rinvoq-fall-behind-jjs-tremfya-novos")
PROMO_SHARE = _b("promo_share", 0.108, "fraction of US sales", "CBO 2008: promotion = 10.8% of US sales",
                 "https://www.thepharmaletter.com/biotech-news/usa-s-budget-office-reviews-promotional-spending-for-prescription-drugs")
EPS_PROMO = _b("eps_promo", 0.06, "elasticity", "Datta and Dave NBER w19592: physician-level detailing elasticity ~0.06 (range 0.05-0.30 is our inference)",
               "https://www.nber.org/papers/w19592")
PLANT_CAPEX_LOW = _b("plant_capex_low", 1000.0, "USD M", "DCAT 2025: plants $1B-$6.5B", "https://www.dcatvci.org/features/big-pharma-us-manufacturing-investment/")
PLANT_CAPEX_HIGH = _b("plant_capex_high", 6500.0, "USD M", "DCAT 2025 / Lilly: $6.5B Texas API facility", "https://www.dcatvci.org/features/big-pharma-us-manufacturing-investment/")
PLANT_BUILD_MONTHS = _b("plant_build_months", 48, "months", "DCAT 2025: 3-5 years (midpoint)", "https://www.dcatvci.org/features/big-pharma-us-manufacturing-investment/")
PLANT_DEPR_YEARS = _b("plant_depr_years", 15, "years", "Spec 5.3 M7 (KQ3 inference): depreciation about pledge/15 per year", "", kind="inference")

# M&A and licensing (spec 5.3 M1, M2)
PREMIUM_MEDIAN = _b("premium_median", 0.63, "fraction", "Evercore precedents, Merck/Cidara SC 14D9: median premium 63% (mean 53%, range 17-102%)", CIDARA)
EV_PEAK_LOW = _b("ev_peak_low", 0.5, "x peak sales", "Credit Suisse, Furiex DEFM14A 2014: EV/peak sales range 0.5x-1.0x", FURIEX)
EV_PEAK_HIGH = _b("ev_peak_high", 1.0, "x peak sales", "Credit Suisse, Furiex DEFM14A 2014: EV/peak sales range 0.5x-1.0x", FURIEX)
UPFRONT_SHARE = _b("upfront_share", 0.06, "fraction of total deal value", "Goodwin 2025 early-stage median 3.7%; Gowling about 5%; JPM/DealForma about 7% (6% is the all-stage midpoint, our inference)",
                   "https://www.goodwinlaw.com/en/insights/publications/2026/03/insights-lifesciences-2025-yir-life-sciences-licensing-collaboration-deals")
DEV_MILESTONE_SHARE = _b("dev_milestone_share", 0.33, "fraction of total deal value", "Goodwin 2025 early stage: development milestones 33%",
                         "https://www.goodwinlaw.com/en/insights/publications/2026/03/insights-lifesciences-2025-yir-life-sciences-licensing-collaboration-deals")
SALES_MILESTONE_SHARE = _b("sales_milestone_share", 0.64, "fraction of total deal value", "Goodwin 2025 early stage: sales milestones 64%",
                           "https://www.goodwinlaw.com/en/insights/publications/2026/03/insights-lifesciences-2025-yir-life-sciences-licensing-collaboration-deals")
ROYALTY_EARLY = _b("royalty_early", 0.065, "fraction of net sales", "Goodwin 2025 early stage tiers 4.5%-8% (midpoint)",
                   "https://www.goodwinlaw.com/en/insights/publications/2026/03/insights-lifesciences-2025-yir-life-sciences-licensing-collaboration-deals")
ROYALTY_LATE = _b("royalty_late", 0.113, "fraction of net sales", "Goodwin 2025 Phase 1+ tiers 9.3%-13% (midpoint); LES 2014 flat 10.2% late Phase II-III, 12.5% NDA-launch",
                  "https://www.goodwinlaw.com/en/insights/publications/2026/03/insights-lifesciences-2025-yir-life-sciences-licensing-collaboration-deals")

# Margins and uptake
CM_EXISTING = _b("cm_existing", 0.85, "fraction", "Spec 5.3 M3: 80-90% incremental contribution for an existing brand (inference from Damodaran 71.73% gross margin, 21.91% SG&A/sales)", DAMODARAN_MARGIN, kind="inference")
CM_ACQUIRED = _b("cm_acquired", 0.7173, "fraction", "Damodaran Jan 2026 pharma gross margin 71.73%", DAMODARAN_MARGIN)
CM_PRICE = 1.0     # price changes drop through (pharma_impact_math: dOI = dRev_net x 1.0)
CM_VOLUME = _b("cm_volume", 0.70, "fraction", "pharma_impact_math / spec 4.3 e: volume-led change CM 0.70", "", kind="inference")
UPTAKE_MONTHS = _b("uptake_months", 39.9, "months to peak", "IQVIA 2021, 813 launches: 13.3 quarters to peak volume",
                   "https://www.iqvia.com/blogs/2021/10/using-historical-analogues-to-forecast-new-product-launches")
UPTAKE_MONTHS_ONC = _b("uptake_months_onc", 60, "months to peak", "Spec 5.3 M1: 5 years for oncology (21 drugs, median)", "")
LABEL_RAMP_MONTHS = _b("label_ramp_months", 60, "months to peak", "Spec 5.3 M3: 25-40% of peak 24 months after launch (strategic_move); a linear 60-month ramp gives 40% at 24 months and sits inside the spec's 3.5-5 year share ramp (review A23)", "", kind="inference")
LABEL_RAMP_MONTHS_ALT = _b("label_ramp_months_alt", 42, "months to peak", "Alternative ramp: the spec 5.5 synthetic reference case (42 months = 57% of peak at 24 months, above the 25-40% benchmark; review A23)", "", kind="inference")
LABEL_SHARE_24M = (0.25, 0.40)   # share of peak 24 months after launch the benchmark states (strategic_move L213)
COVERAGE_LAG = _b("coverage_lag_months", 9, "months", "Tufts/ICER: 6-12 months to majority commercial coverage (midpoint)",
                  "https://www.beckerspayer.com/research-analysis/new-drugs-can-see-coverage-delays-of-up-to-1-year-report/")

# LOE and policy curves: brand revenue retention R(y) by year since entry (spec 4.3 e; pharma_impact_math KQ4)
LOE_RETENTION = {
    "biologic": (_b("loe_bio_y1", 0.65, "retention", "Humira US -35% year 1; biologic R(1) 0.65 (pharma_impact_math KQ4)", ""), 0.35, 0.20),
    "small_molecule": (_b("loe_sm_y1", 0.30, "retention", "IQVIA traditional ~90% erosion; small molecule R(1..3) 0.30/0.15/0.10 (pharma_impact_math KQ4)", ""), 0.15, 0.10),
}
REGISTRY["loe_retention"] = Benchmark("loe_retention", LOE_RETENTION, "retention by year 1/2/3",
                                      "Spec 4.3 e: biologic 0.65/0.35/0.20, small molecule 0.30/0.15/0.10; Humira US -35%/-38%/-57% (AbbVie 10-K)", "")
MFN_SHARE = _b("mfn_share", 0.0065, "fraction of US net revenue", "Pfizer Medicaid MFN exposure <1% of US net revenue; range 0.3-1.0%, base midpoint (spec 4.3 c, inference)", "", kind="inference")
TARIFF_RATE = _b("tariff_rate", 0.15, "fraction of imported cost", "Spec 4.3 d: 15% cap for EU/Japan/Korea/Switzerland; 0.20 onshoring plan; 1.00 otherwise",
                 "https://www.crowell.com/en/insights/client-alerts/trump-administration-imposes-section-232-tariffs-on-patented-pharmaceutical-imports-tiered-rate-structure-takes-effect-beginning-july-31-2026")
TARIFF_START_MONTH = _b("tariff_start_month", 27, "months from 2026-10-17", "Proclamation 11020: MFN signers exempt until 2029-01-20 (spec 4.3 d)", "")
SELF_PAY_SHARE = _b("self_pay_share", 0.35, "fraction of new scripts", "Walmart/LillyDirect release 2025: ~35% of new Zepbound prescriptions via LillyDirect self-pay in Q2 2025",
                    "https://corporate.walmart.com/news/2025/10/29/lillydirect-and-walmart-pharmacy-launch-first-retail-pick-up-option-with-direct-to-consumer-pricing-for-zepbound")
SKYRIZI_OFFSET = _b("successor_offset", 0.49, "growth", "AbbVie 10-Q Q3 2024: Skyrizi +49% (Rinvoq +55%) 9M 2024 successor offset",
                    "https://www.sec.gov/Archives/edgar/data/1551152/000155115224000040/abbv-20240930.htm")

# MCDA and rule constants
MCDA_WEIGHTS = {k: _b("mcda_w_" + k, 0.25, "weight", "ISPOR MCDA Task Force 2016 checklist; equal weights by the 1/N argument (spec D3)", "")
                for k in ("strategic_fit", "capability", "execution_risk", "stakeholder_evidence")}
COMMERCIAL_MULT_CAP = 1.2   # execution risk divisor: 1 means certain bull (spec 5.4)
# Strategic-fit denominator excludes these old-engine kinds (spec D5: favorable level outlier, pi = 0)
FAVORABLE_LEVEL_KINDS = ("gross_margin_peer_outlier",)

decide_weights = SimpleNamespace(
    WACC=WACC, P_SCENARIO=P_SCENARIO, MULT_SCENARIO=MULT_SCENARIO, WINDOW=WINDOW, PAYBACK_SEARCH=PAYBACK_SEARCH,
    POST_LAUNCH_MONTHS=POST_LAUNCH_MONTHS, NON_NME=NON_NME, BIO_TA=BIO_TA,
    TRIAL_COST_PLACEBO=TRIAL_COST_PLACEBO, TRIAL_COST_ACTIVE=TRIAL_COST_ACTIVE, TRIAL_COST_MEDIAN=TRIAL_COST_MEDIAN,
    TRIAL_COST_CARDIO=TRIAL_COST_CARDIO, REP_COST=REP_COST, REP_RAMP_MONTHS=REP_RAMP_MONTHS, PROMO_SHARE=PROMO_SHARE,
    EPS_PROMO=EPS_PROMO, PLANT_CAPEX_HIGH=PLANT_CAPEX_HIGH, PLANT_BUILD_MONTHS=PLANT_BUILD_MONTHS,
    PREMIUM_MEDIAN=PREMIUM_MEDIAN, EV_PEAK_LOW=EV_PEAK_LOW, EV_PEAK_HIGH=EV_PEAK_HIGH, UPFRONT_SHARE=UPFRONT_SHARE,
    CM_EXISTING=CM_EXISTING, CM_ACQUIRED=CM_ACQUIRED, CM_VOLUME=CM_VOLUME, CM_PRICE=CM_PRICE,
    UPTAKE_MONTHS=UPTAKE_MONTHS, LOE_RETENTION=LOE_RETENTION, MFN_SHARE=MFN_SHARE, TARIFF_RATE=TARIFF_RATE,
    MCDA_WEIGHTS=MCDA_WEIGHTS, COMMERCIAL_MULT_CAP=COMMERCIAL_MULT_CAP,
)


def r_monthly(wacc=WACC):
    return (1.0 + wacc) ** (1.0 / 12.0) - 1.0


# --------------------------------------------------------------------------------------------------------------
# Plan structures
# --------------------------------------------------------------------------------------------------------------

@dataclass
class Line:
    name: str
    kind: str                 # "in" | "out"
    amount: list              # monthly magnitude, length = horizon, index 0 = month 1
    prob: list                # P_alive (in) or P_reach (out), length = horizon
    scaled: bool = False      # multiplied by the scenario revenue multiplier
    avoidable: bool = False   # contractually avoidable (excluded from cash at risk)
    note: str = ""


@dataclass
class CashPlan:
    lines: list
    horizon: int
    events: list = field(default_factory=list)       # (month, probability, label) technical readouts
    first_readout: int | None = None                  # month of the first technical readout, None if no trial
    notes: list = field(default_factory=list)
    abandon_value: float = 0.0                        # salvage less exit costs (spec 5.6 stop rule)

    def p_alive_end(self):
        p = 1.0
        for _, q, _ in self.events:
            p *= q
        return p


def alive_curve(events, horizon):
    """P_alive(tau) = product of the transition probabilities of readouts at or before tau."""
    out, p = [], 1.0
    for m in range(1, horizon + 1):
        for em, q, _ in events:
            if em == m:
                p *= q
        out.append(p)
    return out


def _zeros(h):
    return [0.0] * h


def _ones(h):
    return [1.0] * h


def _ramp(k, ramp_m):
    return 0.0 if k <= 0 else min(1.0, k / float(ramp_m))


def retention(months_since_loe, curve):
    """R for the n-th year after LOE (step by year); 1.0 before LOE."""
    if months_since_loe <= 0:
        return 1.0
    r1, r2, r3 = LOE_RETENTION[curve]
    y = (months_since_loe - 1) // 12
    return (r1, r2, r3)[min(y, 2)]


# --------------------------------------------------------------------------------------------------------------
# Template definition
# --------------------------------------------------------------------------------------------------------------

@dataclass
class ParamSpec:
    name: str
    default: object
    unit: str = ""
    source: str = ""          # source text; empty means the default is an assumption the team must state
    url: str = ""
    kind: str = "benchmark"   # benchmark | inference | company | finding
    bench: str = ""           # key in REGISTRY when the default is a registered benchmark
    note: str = ""


@dataclass
class FeedRule:
    """A Part 1 finding kind (prefix match) that feeds one DECIDE parameter."""
    kinds: tuple              # finding signal_kind prefixes
    param: str
    field: str                # impact field to read: "base" | "dollars" | "value" (see decide._finding_value)
    sign: float = 1.0
    note: str = ""


@dataclass
class MoveTemplate:
    code: str
    name: str
    case_move: str                    # the case-listed move type this template implements
    probability_structure: str
    params: dict                      # name -> ParamSpec
    feeds: list                       # list[FeedRule]
    builder: object                   # callable(params dict) -> CashPlan
    required_assets: tuple = ()
    deciders: tuple = ("prescribers", "patients", "payers", "regulators", "investors")
    kill_signals: tuple = ()          # ids from kill.KILL_SIGNALS
    summary: str = ""

    def defaults(self):
        return {k: p.default for k, p in self.params.items()}

    def build(self, params=None):
        merged = self.defaults()
        merged.update(params or {})
        return self.builder(merged)


def _ps(name, default, unit="", bench="", source="", url="", kind=None, note=""):
    if bench:
        b = REGISTRY[bench]
        source, url, kind = source or b.source, url or b.url, kind or b.kind
    return ParamSpec(name, default, unit, source, url, kind or ("company" if source else "inference"), bench, note)


def _wrap(*items):
    return {p.name: p for p in items}


# --------------------------------------------------------------------------------------------------------------
# M3: label expansion (the reference case)
# --------------------------------------------------------------------------------------------------------------

def _build_label_expansion(p):
    n_tr, cost_each = int(p["n_trials"]), p["trial_cost_each"]
    tm, ro, ap = int(p["trial_months"]), int(p["readout_month"]), int(p["approval_month"])
    H = ap + int(p["plateau_months"])
    total = n_tr * cost_each
    cost = [(total / tm) if m <= tm else 0.0 for m in range(1, H + 1)]
    events = [(ro, p["p_ph3"], "Phase III readout"), (ap, p["p_nda"], "approval")]
    rev = [p["peak_sales"] * _ramp(m - ap, p["ramp_months"]) / 12.0 * p["cm"] * (1 - p["tax_rate"]) for m in range(1, H + 1)]
    return CashPlan(
        lines=[Line("pivotal trial cost", "out", cost, _ones(H), note=f"{n_tr} trials x ${cost_each}M over {tm} months"),
               Line("incremental label revenue (after tax)", "in", rev, alive_curve(events, H), scaled=True,
                    note=f"peak ${p['peak_sales']}M linear over {p['ramp_months']} months from approval, CM {p['cm']}, tax {p['tax_rate']}")],
        horizon=H, events=events, first_readout=ro,
        notes=[f"P(success from Phase III) = {p['p_ph3']} x {p['p_nda']} = {p['p_ph3'] * p['p_nda']:.4f}",
               f"in-window ramp: {_ramp(24, p['ramp_months']):.0%} of peak 24 months after approval on a "
               f"{p['ramp_months']:.0f}-month linear ramp (benchmark {LABEL_SHARE_24M[0]:.0%}-{LABEL_SHARE_24M[1]:.0%}; "
               f"alternative ramp {LABEL_RAMP_MONTHS_ALT:.0f} months = {_ramp(24, LABEL_RAMP_MONTHS_ALT):.0%})"])


LABEL_EXPANSION = MoveTemplate(
    code="M3", name="Label expansion (new indication for a marketed drug)", case_move="Seek approval for a new indication",
    probability_structure="rNPV: costs weighted by P_reach (1.0 while spent before the readout); revenue by P_alive = Phase III x NDA, BIO 2021 non-NME rates",
    params=_wrap(
        _ps("n_trials", 2, "trials", source="Spec 5.3 M3: default two pivotal trials", kind="design"),
        _ps("trial_cost_each", TRIAL_COST_PLACEBO, "USD M", bench="trial_cost_placebo"),
        _ps("trial_months", 24, "months", source="Spec 5.5 reference: trials spread evenly over months 1-24", kind="design"),
        _ps("readout_month", 24, "month", source="Reference case: readout at month 24", kind="design"),
        _ps("approval_month", 37, "month", source="Reference case: approval at month 37", kind="design"),
        _ps("p_ph3", NON_NME["ph3"], "probability", bench="p_nonnme_ph3"),
        _ps("p_nda", NON_NME["nda"], "probability", bench="p_nonnme_nda"),
        _ps("peak_sales", 800.0, "USD M per year", source="Incremental peak sales from the Part 1 label-gap finding (4.3 h); placeholder 800 in the reference case", kind="finding"),
        _ps("ramp_months", LABEL_RAMP_MONTHS, "months", bench="label_ramp_months"),
        _ps("plateau_months", POST_LAUNCH_MONTHS, "months", source="Spec 5.1: flat peak to 120 months after approval, no LOE", kind="design"),
        _ps("cm", CM_EXISTING, "fraction", bench="cm_existing"),
        _ps("tax_rate", 0.16, "fraction", source="Company effective tax rate t (spec 4.2 translation); 0.16 in the reference case", kind="company"),
    ),
    feeds=[FeedRule(("label_narrower", "label_gap", "label_indication"), "peak_sales", "base", 1.0, "label channel incremental TAM (4.3 h) sets incremental peak sales")],
    builder=_build_label_expansion,
    required_assets=("approved label for the molecule", "commercial footprint in the therapeutic area", "clinical development capacity"),
    kill_signals=("trial_enrollment", "safety"),
    summary="Trial spend now, revenue after approval; value is mostly terminal value, so cash at risk is small against EV.")


# --------------------------------------------------------------------------------------------------------------
# M1: acquire
# --------------------------------------------------------------------------------------------------------------

def _build_acquire(p):
    H = int(p["close_month"]) + 1 + int(p["launch_month_offset"]) + int(p["uptake_months"]) + int(p["plateau_months"])
    H = max(H, 24)
    close = int(p["close_month"])
    price = p["equity_value"] * (1.0 + p["premium"])
    out = _zeros(H)
    out[close - 1] = price
    events = []
    stage = p["stage"]
    launch = close + int(p["launch_month_offset"])
    rates = BIO_TA[p["ta"]]
    if stage in ("ph3", "phase3"):
        events = [(close + int(p["readout_offset"]), rates[2], "Phase III readout"),
                  (launch, rates[3], "approval")]
    elif stage == "nda":
        events = [(launch, rates[3], "approval")]
    alive = alive_curve(events, H)
    cm = p["cm"] - p["royalty_rate"]
    cur, peak = p["current_rev_annual"], p["peak_sales"]
    rev = []
    for m in range(1, H + 1):
        annual = cur + (peak - cur) * _ramp(m - launch, p["uptake_months"]) if m > launch else (cur if stage == "approved" else 0.0)
        rev.append(annual / 12.0 * cm * (1 - p["tax_rate"]))
    lines = [Line("purchase price (equity x (1 + premium))", "out", out, _ones(H), note=f"{p['equity_value']} x {1 + p['premium']:.2f}"),
             Line("acquired product revenue (after tax)", "in", rev, alive, scaled=True, note=f"CM {cm:.4f}")]
    if p["cvr_amount"]:
        c = _zeros(H)
        c[int(p["cvr_month"]) - 1] = p["cvr_amount"]
        lines.append(Line("CVR payment", "out", c, [p["cvr_prob"]] * H, avoidable=True, note="paid only if the trigger is met; market prices CVRs near zero so no saving is counted"))
    mult = price / peak if peak else float("inf")
    notes = [f"Implied price / peak sales = {mult:.2f}x (comps 0.5x-1.0x, Furiex DEFM14A)"]
    if peak and not (EV_PEAK_LOW <= mult <= EV_PEAK_HIGH * 2):
        notes.append("price / peak sales is outside the 0.5x-2.0x comp band: check the peak-sales input")
    first_ro = events[0][0] if events else None
    return CashPlan(lines, H, events, first_ro, notes)


ACQUIRE = MoveTemplate(
    code="M1", name="Acquire a company or asset", case_move="Acquire or license a drug",
    probability_structure="Deal-comp price (premium over equity value); technical risk by BIO TA rates if unapproved; CVR value counted at payout probability",
    params=_wrap(
        _ps("equity_value", 3000.0, "USD M", source="Unaffected equity value of the target; stage ladder: Phase III single asset $3-9B, approved $10-15B (strategic_move KQ3, inference)", kind="inference"),
        _ps("premium", PREMIUM_MEDIAN, "fraction", bench="premium_median"),
        _ps("close_month", 1, "month", source="Spec 5.3 M1: committed outflow at tau = 1", kind="design"),
        _ps("stage", "ph3", "stage", source="approved | nda | ph3", kind="design"),
        _ps("ta", "metabolic", "therapeutic area", source="Selects BIO 2021 Figure 1 rates", kind="design"),
        _ps("readout_offset", 18, "months after close", source="Time to Phase III readout", kind="design"),
        _ps("launch_month_offset", 30, "months after close", source="Months from close to approval and launch (0 if approved)", kind="design"),
        _ps("uptake_months", UPTAKE_MONTHS, "months", bench="uptake_months"),
        _ps("plateau_months", POST_LAUNCH_MONTHS, "months", source="Spec 5.1: to LOE or 10 years after launch", kind="design"),
        _ps("peak_sales", 3000.0, "USD M per year", source="Target peak sales (company or analyst forecast; state the source)", kind="inference"),
        _ps("current_rev_annual", 0.0, "USD M per year", source="Current annual revenue of an approved target", kind="company"),
        _ps("cm", CM_ACQUIRED, "fraction", bench="cm_acquired"),
        _ps("royalty_rate", 0.0, "fraction", source="Royalty owed by the target on the product, if any", kind="inference"),
        _ps("tax_rate", 0.21, "fraction", source="Company effective tax rate", kind="company"),
        _ps("cvr_amount", 0.0, "USD M", source="Max CVR payout", kind="inference"),
        _ps("cvr_month", 24, "month", source="CVR trigger month", kind="design"),
        _ps("cvr_prob", 0.5, "probability", source="P(trigger)", kind="inference"),
    ),
    feeds=[FeedRule(("exclusivity_earlier", "loe"), "peak_sales_replaced", "dollars", 1.0, "LOE gap sizes the revenue the acquisition must replace (strategic fit)")],
    builder=_build_acquire,
    required_assets=("integration capacity", "commercial footprint in the target's therapeutic area", "balance sheet capacity"),
    kill_signals=("year_one_sales", "coverage", "zs_breadth", "zs_return_writing", "zs_depth", "safety"),
    summary="Large committed outflow at close; deal-comp priced; technical risk only if the asset is unapproved.")


# --------------------------------------------------------------------------------------------------------------
# M2: in-license
# --------------------------------------------------------------------------------------------------------------

def _build_inlicense(p):
    ro, ap = int(p["readout_month"]), int(p["approval_month"])
    H = ap + int(p["uptake_months"]) + int(p["plateau_months"])
    events = [(ro, p["p_ph3"], "Phase III readout"), (ap, p["p_nda"], "approval")]
    alive = alive_curve(events, H)
    total = p["total_deal_value"]
    upfront = _zeros(H)
    upfront[0] = total * p["upfront_share"]
    dev = _zeros(H)
    dev[ro - 1] = total * p["dev_milestone_share"]
    sales = _zeros(H)
    sm = min(H, ap + int(p["sales_milestone_lag"]))
    sales[sm - 1] = total * p["sales_milestone_share"]
    trial = [(p["trial_cost"] / ro) if m <= ro else 0.0 for m in range(1, H + 1)]
    cm = p["cm"]
    rev = [p["peak_sales"] * _ramp(m - ap, p["uptake_months"]) / 12.0 for m in range(1, H + 1)]
    net = [r * (cm - p["royalty_rate"]) * (1 - p["tax_rate"]) for r in rev]
    pr_dev = [1.0 if m < ro else p["p_ph3"] for m in range(1, H + 1)]
    return CashPlan(
        lines=[Line("upfront payment", "out", upfront, _ones(H)),
               Line("licensee trial cost", "out", trial, _ones(H)),
               Line("development milestone (on positive readout)", "out", dev, pr_dev, avoidable=True, note="triggered only on success; avoidable"),
               Line("sales milestone", "out", sales, alive, avoidable=True, note="triggered by commercial success"),
               Line("licensed product revenue net of royalty (after tax)", "in", net, alive, scaled=True, note=f"CM {cm}, royalty {p['royalty_rate']}")],
        horizon=H, events=events, first_readout=ro,
        notes=[f"upfront = {p['upfront_share']:.3f} of total deal value ${total}M; milestones are avoidable on failure"])


IN_LICENSE = MoveTemplate(
    code="M2", name="In-license an asset", case_move="Acquire or license a drug",
    probability_structure="rNPV: upfront and trial cost certain; milestones weighted by P_reach; revenue by BIO TA rates; royalty ladders from Goodwin 2025 / LES 2014",
    params=_wrap(
        _ps("total_deal_value", 1500.0, "USD M", source="Headline deal value (upfront + milestones), comps in strategic_move KQ3", kind="inference"),
        _ps("upfront_share", UPFRONT_SHARE, "fraction", bench="upfront_share"),
        _ps("dev_milestone_share", DEV_MILESTONE_SHARE, "fraction", bench="dev_milestone_share"),
        _ps("sales_milestone_share", SALES_MILESTONE_SHARE, "fraction", bench="sales_milestone_share"),
        _ps("sales_milestone_lag", 36, "months after approval", source="Sales milestones modeled 3 years after approval", kind="design"),
        _ps("royalty_rate", ROYALTY_LATE, "fraction", bench="royalty_late"),
        _ps("trial_cost", 100.0, "USD M", source="Licensee-funded Phase III cost (two pivotal trials, Moore 2018 means)", kind="inference"),
        _ps("readout_month", 24, "month", source="Phase III readout", kind="design"),
        _ps("approval_month", 37, "month", source="Approval", kind="design"),
        _ps("p_ph3", BIO_TA["metabolic"][2], "probability", source="BIO 2021 Figure 1 Phase III->NDA, metabolic (set per TA)", url=BIO, kind="benchmark"),
        _ps("p_nda", BIO_TA["metabolic"][3], "probability", source="BIO 2021 Figure 1 NDA->approval, metabolic (set per TA)", url=BIO, kind="benchmark"),
        _ps("peak_sales", 1500.0, "USD M per year", source="Licensed asset peak sales (state the source)", kind="inference"),
        _ps("uptake_months", UPTAKE_MONTHS, "months", bench="uptake_months"),
        _ps("plateau_months", POST_LAUNCH_MONTHS, "months", source="Spec 5.1", kind="design"),
        _ps("cm", CM_ACQUIRED, "fraction", bench="cm_acquired"),
        _ps("tax_rate", 0.21, "fraction", source="Company effective tax rate", kind="company"),
    ),
    feeds=[FeedRule(("exclusivity_earlier", "loe"), "peak_sales_replaced", "dollars", 1.0, "LOE gap sizes the revenue the license must replace (strategic fit)")],
    builder=_build_inlicense,
    required_assets=("development capacity in the therapeutic area", "commercial footprint"),
    kill_signals=("trial_enrollment", "safety"),
    summary="Small upfront, milestone tail avoidable on failure; lowest cash at risk of the deal moves.")


# --------------------------------------------------------------------------------------------------------------
# M4: pricing and access (incl. DTC cash-pay, MFN aligned)
# --------------------------------------------------------------------------------------------------------------

def _build_pricing(p):
    H = int(p["horizon"])
    loe = int(p["loe_month"])
    ira_m = int(p["baseline_start_month"])
    ramp = float(p["ramp_months"])
    build, annual_cost = p["channel_build_cost"], p["channel_annual_cost"]
    price_in, vol_in, cost_out = [], [], []
    for m in range(1, H + 1):
        base = p["base_us_rev_annual"]
        if p["loe_curve"] and loe:
            base *= retention(m - loe, p["loe_curve"])
        if m >= ira_m:
            base += p["baseline_delta_rev_annual"]
        base = max(base, 0.0)
        r = _ramp(m, ramp)
        price_in.append(base * p["share_moved"] * p["price_delta"] * r / 12.0 * CM_PRICE * (1 - p["tax_rate"]))
        vol_in.append(base * p["volume_gain"] * r / 12.0 * CM_VOLUME * (1 - p["tax_rate"]))
        cost_out.append((build / 12.0 if m <= 12 else 0.0) + annual_cost / 12.0)
    ones = _ones(H)
    return CashPlan(
        lines=[Line("net price given up on moved volume (after tax)", "in", price_in, ones, scaled=True, note="CM 1.00: price drops through"),
               Line("volume gained from the new channel (after tax)", "in", vol_in, ones, scaled=True, note="CM 0.70: volume-led"),
               Line("channel build and operating cost", "out", cost_out, ones,
                    note="channel cost is not disclosed anywhere (strategic_move KQ2 Gaps): the team must state it")],
        horizon=H, events=[], first_readout=None,
        notes=["baseline revenue = base x LOE retention + IRA/MFN delta (Part 1 findings); no clinical event, P_alive = 1"])


PRICING = MoveTemplate(
    code="M4", name="Pricing and access (cash-pay / MFN-aligned channel)", case_move="Change pricing or coverage strategy, including a cash-pay or MFN-aligned channel",
    probability_structure="No clinical event. Baseline follows the LOE retention curve and the IRA/MFN step from Part 1; commercial uncertainty is the scenario spread only",
    params=_wrap(
        _ps("base_us_rev_annual", 10000.0, "USD M per year", source="US annual revenue of the brand (company, cite the 10-K)", kind="company"),
        _ps("share_moved", 0.10, "fraction of volume", source="Share of volume moved to the new channel at plateau; precedent ~35% of new Zepbound scripts via self-pay (Walmart/LillyDirect 2025)", url=REGISTRY["self_pay_share"].url, kind="inference"),
        _ps("price_delta", -0.20, "fraction of net price", source="Net price of the new channel versus current net (team input; no product-level net price is public)", kind="inference"),
        _ps("volume_gain", 0.03, "fraction of base volume", source="Incremental patients reached by the channel (team input)", kind="inference"),
        _ps("ramp_months", 12, "months", source="Channel ramp to plateau (team input; payer coverage lag is 6-12 months, Tufts/ICER)", url=REGISTRY["coverage_lag_months"].url, kind="inference"),
        _ps("channel_build_cost", 100.0, "USD M", source="One-time channel build (not disclosed anywhere; flagged)", kind="inference"),
        _ps("channel_annual_cost", 60.0, "USD M per year", source="Channel operating cost (not disclosed anywhere; flagged)", kind="inference"),
        _ps("baseline_delta_rev_annual", 0.0, "USD M per year", source="IRA / MFN / GTN delta on the brand (Part 1 finding, negative = loss)", kind="finding"),
        _ps("baseline_start_month", 15, "month", source="Month the policy step lands (IPAY 2028 = January 2028)", kind="finding"),
        _ps("loe_month", 0, "month", source="Month of loss of exclusivity, 0 if none inside the horizon", kind="finding"),
        _ps("loe_curve", "", "curve", source="biologic | small_molecule (spec 4.3 e)", kind="design"),
        _ps("horizon", 60, "months", source="24-month window plus 36 months of terminal value (price moves decay with policy resets)", kind="design"),
        _ps("tax_rate", 0.2049, "fraction", source="Company effective tax rate t", kind="company"),
    ),
    feeds=[FeedRule(("ira_", "mfp", "mfn_", "gtn_", "gross_to_net"), "baseline_delta_rev_annual", "base", -1.0,
                    "IRA / MFN / GTN finding's DeltaRev is the baseline revenue change the move is measured against"),
           FeedRule(("exclusivity_earlier", "loe"), "loe_month", "month", 1.0, "LOE finding sets the erosion start")],
    builder=_build_pricing,
    required_assets=("approved label", "commercial footprint in the TA", "direct-to-patient fulfilment channel"),
    deciders=("patients", "payers", "regulators", "investors", "prescribers"),
    kill_signals=("self_pay_share", "year_one_sales", "coverage", "sdud_units"),
    summary="Trades net price for reach; cash at risk is channel cost plus revenue given up in the bear case.")


# --------------------------------------------------------------------------------------------------------------
# M5: portfolio shift / LOE defense
# --------------------------------------------------------------------------------------------------------------

def _build_loe_defense(p):
    H = int(p["horizon"])
    loe = int(p["loe_month"])
    curve = p["curve"]
    up = (p["uplift_y1"], p["uplift_y2"], p["uplift_y3"])
    rev, rebate, prog, succ = [], [], [], []
    for m in range(1, H + 1):
        r_base = retention(m - loe, curve)
        if m > loe:
            y = min((m - loe - 1) // 12, 2)
            r_def = min(1.0, r_base + up[y])
        else:
            r_def = r_base
        base_rev = p["rev_at_risk_annual"] / 12.0
        dretained = base_rev * (r_def - r_base)
        rev.append(dretained * CM_PRICE * (1 - p["tax_rate"]))
        rebate.append(base_rev * r_def * p["rebate_depth"] if m > loe else 0.0)
        prog.append(p["program_cost_annual"] / 12.0 if m >= 1 else 0.0)
        lost = base_rev * (1.0 - r_def)
        succ.append(lost * p["switch_capture"] * p["successor_cm"] * (1 - p["tax_rate"]))
    ones = _ones(H)
    return CashPlan(
        lines=[Line("revenue retained by the defense (after tax)", "in", rev, ones, scaled=True, note="price-led biologic erosion, CM 1.00"),
               Line("successor-brand switch capture (after tax)", "in", succ, ones, scaled=True, note="share of lost patients captured by the successor brand"),
               Line("rebate depth paid on retained volume", "out", rebate, ones, note="the Humira trade: margin for volume (AbbVie CFO)"),
               Line("defense program cost", "out", prog, ones)],
        horizon=H, events=[], first_readout=None,
        notes=[f"no-defense retention {curve}: " + "/".join(f"{x:.2f}" for x in LOE_RETENTION[curve])])


LOE_DEFENSE = MoveTemplate(
    code="M5", name="Portfolio shift and LOE defense", case_move="Shift investment across the portfolio",
    probability_structure="LOE retention curves (biologic 0.65/0.35/0.20, small molecule 0.30/0.15/0.10) with and without the defense; difference of two rNPV paths",
    params=_wrap(
        _ps("rev_at_risk_annual", 3000.0, "USD M per year", source="US revenue of the exposed brand (Part 1 LOE / IRA finding or the 10-K)", kind="finding"),
        _ps("loe_month", 3, "month", source="Month of LOE (patent table / Orange-Purple Book)", kind="company"),
        _ps("curve", "biologic", "curve", source="biologic | small_molecule (spec 4.3 e)", kind="design"),
        _ps("uplift_y1", 0.10, "retention points", source="Retention gained by the defense, year 1 after LOE (team input; Humira held ~90% formulary parity at -35%)", kind="inference"),
        _ps("uplift_y2", 0.08, "retention points", source="Year 2 (team input)", kind="inference"),
        _ps("uplift_y3", 0.05, "retention points", source="Year 3 (team input)", kind="inference"),
        _ps("rebate_depth", 0.10, "fraction of retained revenue", source="Extra rebate paid on retained volume (team input)", kind="inference"),
        _ps("program_cost_annual", 50.0, "USD M per year", source="Contracting and patient-support program cost (team input)", kind="inference"),
        _ps("switch_capture", 0.15, "fraction of lost revenue", source="Share of lost patients moved to the successor brand; precedent Skyrizi +49% / Rinvoq +55% 9M 2024", url=REGISTRY["successor_offset"].url, kind="inference"),
        _ps("successor_cm", CM_EXISTING, "fraction", bench="cm_existing"),
        _ps("horizon", 60, "months", source="24-month window plus 36 months (to year 3 after LOE)", kind="design"),
        _ps("tax_rate", 0.2049, "fraction", source="Company effective tax rate t", kind="company"),
    ),
    feeds=[FeedRule(("exclusivity_earlier", "loe", "ira_", "mfp"), "rev_at_risk_annual", "dollars", 1.0, "LOE / IRA finding's revenue at risk is the defended base")],
    builder=_build_loe_defense,
    required_assets=("incumbent brand with payer contracts", "successor brand with supply"),
    kill_signals=("year_one_sales", "coverage", "sdud_units"),
    summary="Values a defense as the difference between two erosion paths; margin traded for volume is an explicit cost.")


# --------------------------------------------------------------------------------------------------------------
# M6: commercial investment
# --------------------------------------------------------------------------------------------------------------

def _build_commercial(p):
    H = int(p["horizon"])
    spend_annual = p["n_reps"] * p["rep_cost_k"] / 1000.0 + p["dtc_spend_annual"]
    ones = _ones(H)
    cost, rev = [], []
    for m in range(1, H + 1):
        if m <= WINDOW:
            ramp = _ramp(m, p["ramp_months"])
            s = spend_annual / 12.0
            cost.append(s)
            dr = p["epsilon"] * (s * 12.0) / PROMO_SHARE * ramp
        else:
            carry = max(0.0, 1.0 - (m - WINDOW) / float(p["carryover_months"]))
            cost.append(0.0)
            dr = p["epsilon"] * spend_annual / PROMO_SHARE * carry
        rev.append(dr / 12.0 * p["cm"] * (1 - p["tax_rate"]))
    return CashPlan(
        lines=[Line("sales force and DTC spend", "out", cost, ones, note=f"${spend_annual:.1f}M per year"),
               Line("promotion-driven revenue (after tax)", "in", rev, ones, scaled=True,
                    note=f"DeltaRev = eps x DeltaSpend / {PROMO_SHARE}, eps {p['epsilon']}")],
        horizon=H, events=[], first_readout=None,
        notes=[f"$1 of spend returns ${p['epsilon'] / PROMO_SHARE:.2f} of revenue at eps = {p['epsilon']}",
               "any campaign material must follow the case promotion rules (approved uses only, fair balance, claims map)"])


COMMERCIAL = MoveTemplate(
    code="M6", name="Commercial investment (sales force, DTC campaign)", case_move="Launch a marketing campaign",
    probability_structure="No clinical event; response elasticity eps (0.06 base, range 0.05-0.30) and the scenario spread carry the risk",
    params=_wrap(
        _ps("n_reps", 200, "reps", source="Incremental reps (ZS sizing: target physicians x calls / calls per rep)", kind="inference"),
        _ps("rep_cost_k", REP_COST, "USD K per rep-year", bench="rep_cost"),
        _ps("dtc_spend_annual", 0.0, "USD M per year", source="DTC TV spend; top brands $260-440M per year (iSpot via Fierce Pharma)", url=REGISTRY["dtc_tv_high"].url, kind="benchmark"),
        _ps("epsilon", EPS_PROMO, "elasticity", bench="eps_promo"),
        _ps("ramp_months", REP_RAMP_MONTHS, "months", bench="rep_ramp_months"),
        _ps("carryover_months", 12, "months", source="Promotion effect decays linearly to zero after spend stops (team input)", kind="design"),
        _ps("cm", CM_EXISTING, "fraction", bench="cm_existing"),
        _ps("horizon", 48, "months", source="24-month window plus 24-month decay", kind="design"),
        _ps("tax_rate", 0.2049, "fraction", source="Company effective tax rate t", kind="company"),
    ),
    feeds=[FeedRule(("label_narrower", "demand_divergence", "call_topic"), "epsilon_note", "base", 1.0, "share-loss or label-gap findings justify the campaign (strategic fit only)")],
    builder=_build_commercial,
    required_assets=("approved indication with promotional claims map", "field force or media buying capability"),
    kill_signals=("zs_breadth", "zs_return_writing", "zs_depth", "year_one_sales", "coverage"),
    summary="At the physician-level elasticity a pure promotion move is EV-negative; included so it is shown, not assumed.")


# --------------------------------------------------------------------------------------------------------------
# M7: manufacturing
# --------------------------------------------------------------------------------------------------------------

def _build_manufacturing(p):
    bm, H = int(p["build_months"]), int(p["horizon"])
    capex = p["capex"]
    out = [(capex / bm) if m <= bm else 0.0 for m in range(1, H + 1)]
    ones = _ones(H)
    depr = capex / p["depr_years"] / 12.0
    shield = [(depr * p["tax_rate"]) if m > bm else 0.0 for m in range(1, H + 1)]
    ts = int(p["tariff_start_month"])
    avoided = [(p["imported_cogs_annual"] * p["tariff_rate"] * p["onshored_share"] / 12.0 * (1 - p["tax_rate"])) if m >= max(ts, bm) else 0.0
               for m in range(1, H + 1)]
    p_t = [p["p_tariff_applies"]] * H
    return CashPlan(
        lines=[Line("plant capex", "out", out, ones, note=f"${capex}M over {bm} months"),
               Line("depreciation tax shield", "in", shield, ones, note=f"capex / {p['depr_years']} years x t, once in service"),
               Line("avoided tariff cost (after tax)", "in", avoided, p_t, note="imported COGS x tariff rate x onshored share, from the later of 2029-01-20 and plant start-up")],
        horizon=H, events=[], first_readout=None,
        notes=["benefit sits almost entirely in terminal value; tariff regime after 2029-01-20 is a scenario, not a forecast"])


MANUFACTURING = MoveTemplate(
    code="M7", name="Build or reshore manufacturing", case_move="Build or reshore manufacturing",
    probability_structure="No clinical event; benefit weighted by P(tariff regime applies after 2029-01-20), an explicit inference",
    params=_wrap(
        _ps("capex", 3500.0, "USD M", source="Plant capex; $1B-$6.5B per plant (DCAT 2025; Lilly $6.5B Texas API site)", url=REGISTRY["plant_capex_high"].url, kind="benchmark"),
        _ps("build_months", PLANT_BUILD_MONTHS, "months", bench="plant_build_months"),
        _ps("depr_years", PLANT_DEPR_YEARS, "years", bench="plant_depr_years"),
        _ps("imported_cogs_annual", 2000.0, "USD M per year", source="Imported patented COGS exposed to duty (Part 1 tariff note, 4.3 d)", kind="finding"),
        _ps("tariff_rate", TARIFF_RATE, "fraction", bench="tariff_rate"),
        _ps("tariff_start_month", TARIFF_START_MONTH, "month", bench="tariff_start_month"),
        _ps("onshored_share", 0.5, "fraction", source="Share of imported COGS the plant replaces (team input)", kind="inference"),
        _ps("p_tariff_applies", 0.5, "probability", source="P(duty applies to the company after 2029-01-20); no published estimate (inference)", kind="inference"),
        _ps("horizon", 168, "months", source="Plant start-up plus 10 years", kind="design"),
        _ps("tax_rate", 0.2049, "fraction", source="Company effective tax rate t", kind="company"),
    ),
    feeds=[FeedRule(("tariff",), "imported_cogs_annual", "dollars", 1.0, "tariff exposure beyond 2029 (4.3 d) is the onshoring move's terminal value")],
    builder=_build_manufacturing,
    required_assets=("site and permits", "technology transfer capability"),
    deciders=("regulators", "investors", "payers"),
    kill_signals=("safety",),
    summary="Capex is front-loaded and the benefit is a tariff hedge after the window; payback is usually beyond 120 months.")


TEMPLATES = {t.code: t for t in (ACQUIRE, IN_LICENSE, LABEL_EXPANSION, PRICING, LOE_DEFENSE, COMMERCIAL, MANUFACTURING)}
ALIASES = {"acquire": "M1", "in_license": "M2", "license": "M2", "label_expansion": "M3", "new_indication": "M3",
           "pricing": "M4", "pricing_access": "M4", "cash_pay": "M4", "portfolio_shift": "M5", "loe_defense": "M5",
           "commercial": "M6", "marketing": "M6", "manufacturing": "M7", "reshore": "M7"}


def get_template(key):
    k = str(key)
    k = ALIASES.get(k.lower(), k.upper())
    if k not in TEMPLATES:
        raise KeyError(f"unknown move template {key!r}; known: {sorted(TEMPLATES)} and {sorted(ALIASES)}")
    return TEMPLATES[k]
