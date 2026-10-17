"""Impact-math channels (docs/quant_model.md section 4.3). Every channel returns an Impact with dRev, dOI and dEPS
for bull / base / bear, the fiscal year of largest in-window impact, t_years, its citations and flags.

EPS translation (section 4.2):  dEPS = dRev . CM . (1 - t) / D      dOI = dRev . CM
Bull is the scenario least harmful to the company (smallest adverse dRev), bear the most harmful.
Dollar amounts are in the company's reporting currency, millions; per-share in that currency.
"""

from dataclasses import dataclass, field
from datetime import date

from . import weights as W
from .data import AS_OF


@dataclass
class Impact:
    channel: str
    formula: str = ""
    d_rev: dict = field(default_factory=dict)      # {"bull", "base", "bear"} millions
    d_oi: dict = field(default_factory=dict)
    d_eps: dict = field(default_factory=dict)      # per share
    cm: float = 1.0
    tax: float = 0.0
    shares: float = 0.0
    fiscal_year: int | None = None
    t_years: float = 0.0
    citations: list = field(default_factory=list)  # list[Citation] for every number in the math
    flags: list = field(default_factory=list)
    adverse: bool = True
    quantified: bool = True

    def to_dict(self):
        d = {k: v for k, v in self.__dict__.items() if k != "citations"}
        d["citation_ids"] = [c.cite_id for c in self.citations]
        return d


def eps(d_rev, cm, tax, shares):
    """dEPS = dRev . CM . (1 - t) / D (section 4.2)."""
    return d_rev * cm * (1 - tax) / shares


def _fill(imp, revs, cm, co):
    imp.cm, imp.tax, imp.shares = cm, co.tax, co.shares
    imp.d_rev = {k: v for k, v in zip(("bull", "base", "bear"), revs)}
    imp.d_oi = {k: v * cm for k, v in imp.d_rev.items()}
    imp.d_eps = {k: eps(v, cm, co.tax, co.shares) for k, v in imp.d_rev.items()}
    return imp


def years_to_mid(fy, as_of=AS_OF):
    """t_f: years from as_of to the midpoint (1 July) of fiscal year fy."""
    return (date(fy, 7, 1) - as_of).days / 365.25


def constants_citations(co):
    return [c for k in ("Rev_TTM", "t", "t_raw", "D", "sigma_EPS") for c in co.citations.get(k, [])]


# ---------------------------------------------------------------- (a) anchor event
def anchor(co):
    """dEPS_anchor = 0.03 . Rev_TTM . (1 - t) / D, t_f = 0.5 years (section 4.3 a). A lower bound on the event size."""
    imp = Impact("anchor", formula=(f"{W.ANCHOR} x Rev_TTM {co.rev_ttm:,.1f} x (1 - t {co.tax:.4f}) / D "
                                    f"{co.shares:,.1f}"), t_years=W.ANCHOR_T_YEARS)
    imp.citations = constants_citations(co)
    r = W.ANCHOR * co.rev_ttm
    return _fill(imp, (r, r, r), 1.0, co)


# ---------------------------------------------------------------- (b) IRA negotiation
def ira(co, drug, G, d, g_pre, ipay, k_factor=None, cites=()):
    """dRev_IPAY = G_Medicare . max(0, d - g_pre), CM = 1.00, step on 1 January of the IPAY year (section 4.3 b).
    d and g_pre are (bull, base, bear) tuples or scalars. For a class with no g_pre prior, the KQ2 cross-check
    (net hit = k x list discount, k = 0.3 / 0.4 / 0.5) is used instead and flagged.
    G is the CMS Part B+D spend in USD millions; it is converted to the reporting currency by co.fx (default 1)."""
    dd = d if isinstance(d, tuple) else (d, d, d)
    imp = Impact("ira", fiscal_year=ipay, t_years=years_to_mid(ipay))
    fx = getattr(co, "fx", 1.0)
    if k_factor:
        revs = tuple(G * fx * di * k for di, k in zip(dd, k_factor))
        imp.formula = f"G {G:,.3f} x d {dd} x k {k_factor} (KQ2 cross-check: net hit = k x list discount)"
        imp.flags.append("IRA: net hit = k x list discount (KQ2 cross-check, inference)")
    else:
        gg = g_pre if isinstance(g_pre, tuple) else (g_pre, g_pre, g_pre)
        # bull pairs the smallest discount with the largest concession already paid, bear the reverse
        revs = (G * fx * max(0.0, dd[0] - gg[-1]), G * fx * max(0.0, dd[1] - gg[1]), G * fx * max(0.0, dd[2] - gg[0]))
        imp.formula = f"G {G:,.3f} x (d {dd} - g_pre {gg if len(set(gg)) > 1 else gg[0]})"
    if fx != 1.0:
        imp.formula += f" x FX {fx}"
    if ipay * 12 > (AS_OF.year * 12 + AS_OF.month - 1) + W.HORIZON_MONTHS:
        imp.flags.append("IRA effective date outside the 24-month window: dEPS = 0")
        revs = (0.0, 0.0, 0.0)
    if date(ipay, 1, 1) <= AS_OF:
        imp.flags.append("MFP already effective before as_of: in reported numbers, dEPS = 0")
        revs = (0.0, 0.0, 0.0)
    imp.citations = list(cites) + constants_citations(co)
    return _fill(imp, revs, W.CM_PRICE, co)


# ---------------------------------------------------------------- (c) MFN and (d) tariff
def mfn(co, rev_us, s=W.S_MFN, cites=()):
    """dRev = s_MFN . Rev_US, s base 0.0065 (0.003-0.010), CM = 1.00 (section 4.3 c). TrumpRx modeled neutral."""
    imp = Impact("mfn", formula=f"s_MFN {s} x Rev_US {rev_us:,.1f}", fiscal_year=AS_OF.year + 1,
                 t_years=years_to_mid(AS_OF.year + 1))
    imp.citations = list(cites) + constants_citations(co)
    return _fill(imp, tuple(x * rev_us for x in s), W.CM_PRICE, co)


def tariff_note(cogs_imported_patented, rates=(0.15, 0.20, 1.00)):
    """Section 4.3 d: MFN signers pay zero duty until 2029-01-20, outside the window, so this is a beyond-window note:
    dCOGS_after_2029 = COGS_imported_patented . tau_rate. Returns {rate: dCOGS}; never a scored dEPS."""
    return {r: cogs_imported_patented * r for r in rates}


# ---------------------------------------------------------------- (e) loss of exclusivity
def loe(co, product, rev_pre, loe_date, biologic, cites=(), as_of=AS_OF):
    """dRev_y = Rev_pre . (1 - R(y)); CM 1.00 biologic (price-led), 0.70 small molecule (volume-led). The scored year
    is the fiscal year of largest in-window impact (section 4.2). LOE outside the window gives dEPS = 0."""
    R = W.R_BIOLOGIC if biologic else W.R_SMALL_MOLECULE
    cm = W.CM_PRICE if biologic else W.CM_VOLUME
    end_m = as_of.year * 12 + as_of.month - 1 + W.HORIZON_MONTHS
    best = (0.0, None, None)
    for i, r in enumerate(R):
        fy = loe_date.year + i
        if fy * 12 > end_m or fy < as_of.year:
            continue
        # fraction of fiscal year fy after the LOE date (year 1 is partial)
        frac = 1.0 if i else max(0.0, (date(fy, 12, 31) - loe_date).days / 365.25)
        hit = rev_pre * (1 - r) * frac
        if hit > best[0]:
            best = (hit, fy, i + 1)
    imp = Impact("loe", fiscal_year=best[1], t_years=years_to_mid(best[1]) if best[1] else 0.0)
    imp.formula = (f"Rev_pre {rev_pre:,.1f} x (1 - R(y{best[2]}) {R[best[2] - 1] if best[2] else 'n/a'})"
                   f" [{'biologic' if biologic else 'small molecule'}; LOE {loe_date.isoformat()}]")
    if best[1] is None:
        imp.flags.append("LOE outside the 24-month window: dEPS = 0")
    imp.citations = list(cites) + constants_citations(co)
    lo, hi = best[0] * 0.8, best[0] * 1.2
    return _fill(imp, (lo, best[0], hi), cm, co)


# ---------------------------------------------------------------- (f) gross-to-net
def gtn(co, rev_net, gtn_level, d_gtn, cites=()):
    """dRev = -Rev_gross . dGTN, Rev_gross = Rev_net / (1 - GTN), CM = 1.00 (section 4.3 f)."""
    gross = rev_net / (1 - gtn_level)
    imp = Impact("gtn", formula=f"Rev_gross {gross:,.1f} (= {rev_net:,.1f} / (1 - {gtn_level})) x dGTN {d_gtn}",
                 fiscal_year=AS_OF.year + 1, t_years=years_to_mid(AS_OF.year + 1))
    imp.citations = list(cites) + constants_citations(co)
    dd = d_gtn if isinstance(d_gtn, tuple) else (d_gtn, d_gtn, d_gtn)
    return _fill(imp, tuple(gross * x for x in dd), W.CM_PRICE, co)


# ---------------------------------------------------------------- (g) inventory and receivables
def excess(x_now, x_prior, g_rev):
    """excess_X = X_t - X_{t-4} . (1 + g_rev): the exposure shown on the row, not the scored impact (section 4.3 g)."""
    return x_now - x_prior * (1 + g_rev)


def dio(inventory, cogs_q, days=91.25):
    """DIO = inventory / COGS_q . 91.25 (annual filers: 365 and FY figures)."""
    return inventory / cogs_q * days


def dso(receivables, rev_q, days=91.25):
    return receivables / rev_q * days


def dso_reversal(co, dso_series, rev_q, days=91.25, cites=()):
    """Channel-stuffing test (section 4.3 g ii): DSO_t - mean(DSO_{t-4..t-1}) > 7 days switches receivables to the
    reversal channel, expected reversal = excess days x daily revenue. Returns an Impact or None when the test fails.
    The wholesaler-language half of the test needs text comparison and is flagged as not checked."""
    if len(dso_series) < 5:
        return None
    ex_days = dso_series[-1] - sum(dso_series[-5:-1]) / 4
    if ex_days <= W.DSO_STAR:
        return None
    rev = ex_days * rev_q / days
    imp = Impact("dso_reversal", formula=f"excess DSO {ex_days:.1f} days x daily revenue {rev_q / days:,.2f}",
                 fiscal_year=AS_OF.year + 1, t_years=W.ANCHOR_T_YEARS)
    imp.flags.append("wholesaler-inventory language change not checked")
    imp.citations = list(cites) + constants_citations(co)
    return _fill(imp, (rev * 0.5, rev, rev), W.CM_VOLUME, co)


# ---------------------------------------------------------------- (h) label breadth and product fine print
def boxed_warning_added(co, us_rev, class_wide=False, cites=()):
    """-10% to -25% of US volume over 12-18 months, near 0 if class-wide; CM 0.70 (section 4.3 h)."""
    lo, hi = W.BOXED_WARNING
    revs = (0.0, 0.0, 0.0) if class_wide else (-lo * us_rev, -(lo + hi) / 2 * us_rev, -hi * us_rev)
    imp = Impact("label_boxed_warning", formula=f"US revenue {us_rev:,.1f} x {W.BOXED_WARNING}",
                 fiscal_year=AS_OF.year + 1, t_years=years_to_mid(AS_OF.year + 1))
    imp.citations = list(cites) + constants_citations(co)
    return _fill(imp, revs, W.CM_VOLUME, co)


def rems_vs_rival(co, new_start_rev, cites=()):
    """-5% to -15% of new starts (KQ6 inference)."""
    lo, hi = W.REMS
    imp = Impact("label_rems", formula=f"new-start revenue {new_start_rev:,.1f} x {W.REMS}",
                 fiscal_year=AS_OF.year + 1, t_years=years_to_mid(AS_OF.year + 1))
    imp.citations = list(cites) + constants_citations(co)
    return _fill(imp, (-lo * new_start_rev, -(lo + hi) / 2 * new_start_rev, -hi * new_start_rev), W.CM_VOLUME, co)


def dosing(co, starter_rev, advantage=True, cites=()):
    """Once-weekly vs daily: +10% to +15% revenue per starter over two years (HR 0.80)."""
    lo, hi = W.WEEKLY_VS_DAILY
    sign = -1 if advantage else 1   # adverse dRev positive by convention; an advantage is a negative loss
    imp = Impact("label_dosing", formula=f"starter revenue {starter_rev:,.1f} x {W.WEEKLY_VS_DAILY}",
                 fiscal_year=AS_OF.year + 1, t_years=years_to_mid(AS_OF.year + 1), adverse=not advantage)
    imp.citations = list(cites) + constants_citations(co)
    return _fill(imp, tuple(sign * x * starter_rev for x in (lo, (lo + hi) / 2, hi)), W.CM_VOLUME, co)


def label_unquantified(co, kind):
    """Static label comparisons (indication count, existing boxed warning, dosing, REMS) need new-start share or a TAM
    build (section 4.3 h) that the data layer does not hold; the row is context for the Part 1 product comparison."""
    imp = Impact("label", formula=f"{kind}: static label difference already in the revenue run-rate; "
                                  "new-start share / TAM inputs not in the data layer", quantified=False)
    imp.flags.append("label channel: not quantified (no in-window change; inputs missing)")
    return _fill(imp, (0.0, 0.0, 0.0), W.CM_VOLUME, co)


# ---------------------------------------------------------------- (i) footnote items
def footnote(co, item, amount=None, rate_change=None, pretax_ttm=None, product_rev=None, rng=None, cites=()):
    """Section 4.3 i. item in {contingent_consideration, royalty_change, litigation_accrued,
    litigation_reasonably_possible, tax_rate_change, impairment_booked}. Returns (Impact, pi)."""
    imp = Impact(f"footnote_{item}", fiscal_year=AS_OF.year + 1, t_years=years_to_mid(AS_OF.year + 1))
    imp.citations = list(cites) + constants_citations(co)
    pi = W.PI_CONTRACTUAL
    if item == "contingent_consideration":
        d = amount or 0.0
        imp.formula = f"change in disclosed fair value {d:,.1f}"
        _fill(imp, (d, d, d), 1.0, co)
    elif item == "royalty_change":
        d = (rate_change or 0.0) * (product_rev or 0.0)
        imp.formula = f"d royalty {rate_change} x product revenue {product_rev}"
        _fill(imp, (d, d, d), 1.0, co)
    elif item in ("litigation_accrued", "impairment_booked"):
        imp.formula = "already in reported numbers: dEPS = 0 unless the accrual is changed"
        imp.flags.append(f"{item}: booked, already in reported numbers")
        _fill(imp, (0.0, 0.0, 0.0), 1.0, co)
    elif item == "litigation_reasonably_possible":
        lo, hi = rng or (0.0, 0.0)
        mid = (lo + hi) / 2
        imp.formula = f"midpoint of disclosed range ({lo:,.1f}, {hi:,.1f})"
        _fill(imp, (lo, mid, hi), 1.0, co)
        pi = W.PI_REASONABLY_POSSIBLE
    elif item == "tax_rate_change":
        d = (rate_change or 0.0) * (pretax_ttm or 0.0)
        imp.formula = f"d t {rate_change} x pretax_TTM {pretax_ttm}"
        imp.cm, imp.tax, imp.shares = 1.0, 0.0, co.shares
        imp.d_rev = {"bull": 0.0, "base": 0.0, "bear": 0.0}
        imp.d_oi = dict(imp.d_rev)
        imp.d_eps = {k: d / co.shares for k in ("bull", "base", "bear")}
    return imp, pi
