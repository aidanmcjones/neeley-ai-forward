"""DECIDE kill signals (docs/quant_model.md Section 5.6): numeric thresholds, data source, lag, and the formula that
turns a breach into a revised EV.

Revised EV after a breach (Bayes on scenarios, then the real-options stop rule):

    p'_s  = p_s L_s / sum_u p_u L_u            L_s = P(breach | s)
    EV'   = sum_s p'_s EV^remaining_s          remaining cash flows after the check month, sunk costs excluded
    stop if EV' < V_abandon = salvage - exit costs

Choices where the spec is silent (all logged in docs/decide.md): breaches from the same evidence family (the three ZS
launch metrics) count as ONE update, because they are one underlying observation; a "replace_bear" breach (year-one
sales, Medicaid units) sets p_bear to at least 0.70 and spreads the rest over base and bull in proportion; "review"
signals never change EV.
"""

from dataclasses import dataclass, field

from agent.needle.quant.moves import SCENARIOS, WACC, r_monthly

# Likelihoods P(breach | scenario): ZS (18 specialty biologic launches): none of the unsuccessful met each threshold,
# ~90% of successful launches did, so P(breach | bear) = 1.0 and P(breach | bull) = 0.10; base 0.55 is the midpoint (inference).
ZS_LIKELIHOOD = {"bear": 1.0, "base": 0.55, "bull": 0.10}
# Commercial coverage < 50% of lives at month 6: ICER pattern; bear 1.0, bull 0.5 (inference); base midpoint 0.75 (inference).
COVERAGE_LIKELIHOOD = {"bear": 1.0, "base": 0.75, "bull": 0.50}
P_BEAR_AFTER_MISS = 0.70   # Deloitte 2022: ~70% of year-one misses keep missing; McKinsey 2014: misses continue two more years


@dataclass
class KillSignal:
    id: str
    name: str
    threshold: str            # human-readable numeric threshold
    value: float              # numeric threshold
    direction: str            # "below" | "above"
    unit: str
    source: str               # where to read it
    lag: str                  # publication lag
    check_month: int
    action: str               # "bayes" | "replace_bear" | "review"
    family: str               # breaches in one family are one observation
    likelihood: dict = field(default_factory=dict)
    basis: str = ""           # citation of the threshold
    url: str = ""

    def breached(self, observed):
        return observed < self.value if self.direction == "below" else observed > self.value


KILL_SIGNALS = {s.id: s for s in (
    KillSignal("zs_breadth", "ZS breadth: priority-target prescribers with >= 1 new patient", "< 30%", 0.30, "below", "share",
               "paid claims (IQVIA / Symphony); no free equivalent", "claims weekly; visible by month 3", 6, "bayes", "zs",
               ZS_LIKELIHOOD, "ZS, 18 specialty biologic launches: ~90% of successes met each threshold, none of the failures did"),
    KillSignal("zs_return_writing", "ZS return-writing rate", "< 50%", 0.50, "below", "share", "paid claims", "claims weekly", 6,
               "bayes", "zs", ZS_LIKELIHOOD, "ZS: all three met = nine times more likely to succeed"),
    KillSignal("zs_depth", "ZS depth: writers with >= 3 patients", "< 30%", 0.30, "below", "share", "paid claims", "claims weekly", 6,
               "bayes", "zs", ZS_LIKELIHOOD, "ZS"),
    KillSignal("year_one_sales", "Year-one net sales vs forecast", "< 80% of forecast", 0.80, "below", "ratio",
               "company 10-Q product revenue", "about 40 days after quarter end", 12, "replace_bear", "year_one", {},
               "Deloitte 2022: ~70% of year-one misses keep missing; McKinsey 2014: misses typically continue two years"),
    KillSignal("coverage", "Commercial coverage", "< 50% of commercial lives", 0.50, "below", "share",
               "payer policy trackers (paid); proxy: company commentary", "monthly to quarterly", 6, "bayes", "coverage",
               COVERAGE_LIKELIHOOD, "Tufts / ICER: half of payers lacked policies for H2 2024 approvals by December 2024"),
    KillSignal("sdud_units", "Medicaid units vs plan", "< 80% of plan", 0.80, "below", "ratio", "Medicaid SDUD (CMS)",
               "states submit within 60 days of quarter end; posting lags 1-2 quarters", 9, "replace_bear", "year_one", {},
               "same persistence rule as year-one sales"),
    KillSignal("safety", "Safety: FAERS serious reports", "+50% YoY and above the rivals' median", 0.50, "above", "yoy change",
               "FAERS quarterly files", "about one quarter; counts follow publicity", 3, "review", "safety", {},
               "engine threshold, agent/needle/detect/supply.py; no published likelihood: human review, not an EV update"),
    KillSignal("self_pay_share", "Self-pay channel share of new scripts (DTC moves)", "< 35%", 0.35, "below", "share",
               "company disclosure", "quarterly earnings", 6, "bayes", "zs", ZS_LIKELIHOOD,
               "LillyDirect precedent 35% in Q2 2025 (Walmart/Lilly release); likelihood follows the ZS rule"),
    KillSignal("trial_enrollment", "Trial enrollment pace", "< 80% of plan", 0.80, "below", "ratio", "ClinicalTrials.gov (sponsor updated)",
               "sponsor updates, often months late", 6, "review", "trial", {}, "review trigger, no published likelihood"),
)}

PART_D_NOTE = "Medicare Part D Prescriber PUF lags about 18 months, so it can confirm but never trigger within 24 months."


def signals_for(result_or_codes):
    ids = getattr(result_or_codes, "kill_signals", result_or_codes)
    return [KILL_SIGNALS[i] for i in ids]


def bayes_update(p, likelihood):
    z = sum(p[s] * likelihood[s] for s in SCENARIOS)
    return {s: p[s] * likelihood[s] / z for s in SCENARIOS}


@dataclass
class RevisedEV:
    breaches: list
    check_month: int
    p_prior: dict
    p_posterior: dict
    ev_original: float
    ev_remaining_prior: float
    ev_revised: float
    ev_revised_total: float      # EV' plus the already-sunk expected PV through the check month: comparable with EV
    delta_vs_prior: float
    stop: bool
    abandon_value: float
    review: list
    notes: list

    def to_dict(self):
        return dict(self.__dict__)


def remaining_ev(result, check_month, p=None):
    """sum_s p_s * PV at as_of of expected flows strictly after the check month (sunk costs excluded)."""
    r = r_monthly(result.wacc)
    p = p or result.p_scenario
    return sum(p[s] * sum(x * (1 + r) ** (-m) for m, x in enumerate(result.expected_cf[s], 1) if m > check_month)
               for s in SCENARIOS)


def through_pv(result, check_month):
    r = r_monthly(result.wacc)
    return sum(result.p_scenario[s] * sum(x * (1 + r) ** (-m) for m, x in enumerate(result.expected_cf[s], 1) if m <= check_month)
               for s in SCENARIOS)


def revise_ev(result, breaches):
    """breaches: iterable of signal ids or KillSignal objects that tripped. Returns RevisedEV."""
    sigs = [KILL_SIGNALS[b] if isinstance(b, str) else b for b in breaches]
    p0 = dict(result.p_scenario)
    p = dict(p0)
    review, notes, used = [], [], set()
    for sg in sigs:
        if sg.action == "review":
            review.append(sg.id)
            continue
        if sg.action == "bayes":
            if sg.family in used:
                notes.append(f"{sg.id}: same evidence family ({sg.family}) as an earlier breach, counted once")
                continue
            used.add(sg.family)
            p = bayes_update(p, sg.likelihood)
    if any(sg.action == "replace_bear" for sg in sigs):
        rest = p["base"] + p["bull"]
        pb = max(p["bear"], P_BEAR_AFTER_MISS)
        p = {"bear": pb, "base": (1 - pb) * p["base"] / rest, "bull": (1 - pb) * p["bull"] / rest}
    cm = max([sg.check_month for sg in sigs] or [0])
    prior_rem = remaining_ev(result, cm, p0)
    rev = remaining_ev(result, cm, p)
    stop = rev < result.abandon_value
    if review:
        notes.append("review-only signals tripped (" + ", ".join(review) + "): human review, EV not changed by the model")
    return RevisedEV(
        breaches=[sg.id for sg in sigs], check_month=cm, p_prior=p0, p_posterior=p, ev_original=result.ev,
        ev_remaining_prior=prior_rem, ev_revised=rev, ev_revised_total=through_pv(result, cm) + rev,
        delta_vs_prior=rev - prior_rem, stop=stop, abandon_value=result.abandon_value, review=review, notes=notes)
