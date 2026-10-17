"""Every FIND constant from docs/quant_model.md section 11.1 (Weight derivation table), one named value each.

The comment on each line gives the source exactly as the table states it. Change a number here only together
with the table in the spec, so the two cannot drift. tests/needle/test_quant_weights.py pins the values.
"""

# ---- exponents and discounting -------------------------------------------------------------------------------
ALPHA = 1.0          # exponent on M. D3: expected-value reading; DeMiguel et al. 2009; Gu-Kelly-Xiu OOS R2 0.33-0.40%
BETA = 1.0           # exponent on O. D3
GAMMA = 1.0          # exponent on E. D3
R = 0.0785           # discount rate. Damodaran Drugs (Pharmaceutical), 228 firms, Jan 2026 WACC
HORIZON_MONTHS = 24  # impact window. materiality_spec section 2; case Part 2
ANCHOR_T_YEARS = 0.5  # t_f for the anchor event: midpoint of the next four quarters (section 4.2)

# ---- materiality noise denominator -----------------------------------------------------------------------------
SIGMA_QUARTERS = 8          # sigma_EPS = 2 x sd(last 8 quarterly surprises). Section 4.2
SIGMA_ANNUALIZE = 2.0       # sqrt(4) annualization of four independent quarterly surprises (inference)
SIGMA_FY1_RATIO = 0.041     # sigma_EPS / FY1-EPS fallback: median of 9 shortlist ratios (section 4.2 table)

# ---- EPS translation (section 4.2, pharma_impact_math KQ7) -----------------------------------------------------
CM_PRICE = 1.00      # price, rebate, MFP, MFN change flows through. KQ7; Drug Channels
CM_VOLUME = 0.70     # volume change. KQ7 (COGS 15-25%, variable selling 5-15%)

# ---- anchor event (section 4.3 a) ------------------------------------------------------------------------------
ANCHOR = 0.03        # margin-compression size for statistical flags: backtest margin_drop >= 3 pts

# ---- obscurity (section 4.4) -----------------------------------------------------------------------------------
H_MONTHS = 3.0       # obscurity half-life, base. Low end of priced_in KQ5 3-6: mega-caps are read by many, so faster
                     # absorption (review A11; Martineau: large-cap PEAD gone since 2006). 6 months is the sensitivity
H_MONTHS_SENSITIVITY = 6.0   # Lazy Prices (persists to 6 months, accrues to 18); the v2 base, reported as a sensitivity
H_VALUE = 0.9        # headline-page coverage. materiality_spec section 3 team rule; case "press-release skim"
Z_VALUE = 1.0        # starter thread. case appendix; binary by design
ATTENTION_QUARTERS = 10   # a_f = share of the last up-to-10 calls in which analysts asked (priced_in_scorecard)
LOE_AGE_MONTHS_DEFAULT = 24.0   # inference: Orange/Purple Book and 10-K patent dates are long public (see notes)

# ---- evidence grades (section 4.5) -----------------------------------------------------------------------------
G_EXACT = 1.00       # verified_exact. test_trust seeded errors
G_FUZZY = 0.90       # verified_fuzzy. citation note KQ4 (inference)
G_LLM = 0.85         # derived_llm. FinanceBench oracle 85% (Islam et al. 2023)
G_ENTAILED = 0.745   # verified_entailed. Liu et al. 2023, 74.5% of citations support their sentence
G_NONE = 0.0         # unsupported / contradicted

# ---- priors pi_k (section 4.6) ---------------------------------------------------------------------------------
DELTA_OOS = 0.26     # data-mining haircut. McLean-Pontiff 2016 out-of-sample decline ("about 26% less")
D_PUB = 0.58         # post-publication decay. McLean-Pontiff 2016; cancels in the anchor ratio (D7)
ALPHA_TZ = 11.39     # anchor hedge return, percent. Thomas-Zhang 2002 inventory change, year t+1


def backtest_pi(h_fired, h_not, haircut=DELTA_OOS):
    """pi_k = (h_fired - h_not) x (1 - 0.26). Section 4.6 route 2."""
    return (h_fired - h_not) * (1 - haircut)


PI_INVENTORY = round(backtest_pi(0.206, 0.143), 4)   # 0.0466. backtest margin_drop 20.6% vs 14.3%
PI_ANCHOR = PI_INVENTORY                              # pi_anchor = pi_inventory (D6)
PI_DIO = round(backtest_pi(0.217, 0.174), 4)         # 0.0318. backtest 21.7% vs 17.4%
PI_RECEIVABLES = round(backtest_pi(0.228, 0.143), 4)  # 0.0629. backtest 22.8% vs 14.3%
PI_DSO = round(backtest_pi(0.256, 0.141), 4)         # 0.0851. backtest 25.6% vs 14.1%
PI_GROSS_MARGIN_DROP = round(0.057 * (1 - DELTA_OOS), 4)  # 0.0422. min(margin 12.2 pts, hard 5.7 pts) x 0.74


def anchor_pi(alpha_k, d_k=D_PUB):
    """pi_k = pi_anchor x [alpha_k (1 - d_k)] / [alpha_TZ (1 - d_TZ)]. Section 4.6 route 3 (decay cancels)."""
    return PI_ANCHOR * (alpha_k * (1 - d_k)) / (ALPHA_TZ * (1 - D_PUB))


PI_MISSTATEMENT = round(anchor_pi(12.0), 4)    # 0.0491. Beneish-Lee-Nichols 2013, 1%/month x 12 (inference)
PI_RISK_FACTOR = round(anchor_pi(5.52), 4)     # 0.0226. Lazy Prices VW Jaccard 0.46%/month x 12
PI_LITIGATION_TEXT = round(anchor_pi(8.52), 4)  # 0.0349. Lazy Prices 71 bps/month x 12
PI_MDNA = round(anchor_pi(1.98), 4)            # 0.0081. Lazy Prices Table VII 11-22 bps/month, midpoint x 12
PI_INSIDER = round(anchor_pi(4.92), 4)         # 0.0201. Cohen-Malloy-Pomorski 82 bps/month x 6
PI_8K = round(anchor_pi(1.5), 4)               # 0.0061. Lerman-Livnat 2010 lower end 1.5%
PI_MIN = round(anchor_pi(1.34), 4)             # 0.0055. Chen-Hollander-Law (WP) zero-question calls 1.34%
PI_NONE = 0.0028                               # pi_min / 2 = 0.00275 rounded up as the spec prints it; tier halving (inference)
PI_CONTRACTUAL = 1.0                           # scheduled or booked events, by definition
PI_REASONABLY_POSSIBLE = 0.5                   # ASC 450 midpoint (inference)
PI_FAVORABLE_LEVEL = 0.0                       # favorable level outlier with no scenario (section 4.6 last row)

# ---- IRA channel (section 4.3 b) -------------------------------------------------------------------------------
ONC_D_BULL, ONC_D_BASE, ONC_D_BEAR = 0.38, 0.50, 0.60  # Imbruvica, Ibrance, Pomalyst (CMS IPAY 2026-2027)
M_MDP_CATASTROPHIC = 0.20    # MDP rate replaced by the MFP, catastrophic phase. CMS MDP final guidance
M_MDP_INITIAL = 0.10         # initial phase
G_PRE_GLP1 = (0.60, 0.675, 0.75)        # GLP-1 pre-MFP concession, low / mid / high (Drug Channels; inference)
G_PRE_INSULIN = 0.75                    # insulin pre-cut (inference)
G_PRE_IMMUNOLOGY = (0.50, 0.575, 0.65)  # immunology (inference)
IRA_HEADLINE_RANGE = (0.38, 0.85)       # headline list-discount range across cycles 1-2

# ---- MFN, LOE, label (sections 4.3 c, e, h) --------------------------------------------------------------------
S_MFN = (0.003, 0.0065, 0.010)        # Medicaid MFN share of US revenue: Pfizer <1% of US net; midpoint inference
R_BIOLOGIC = (0.65, 0.35, 0.20)       # LOE retention years 1/2/3. Humira, Stelara, IQVIA (KQ4)
R_SMALL_MOLECULE = (0.30, 0.15, 0.10)  # LOE retention years 1/2/3. KQ4; IQVIA "traditional 90% erosion"
BOXED_WARNING = (-0.10, -0.25)        # US volume over 12-18 months. Mayo Clin Proc; PMC8159769
REMS = (-0.05, -0.15)                 # new starts. KQ6 inference
WEEKLY_VS_DAILY = (0.10, 0.15)        # revenue per starter over 2 years. HR 0.80 (0.71-0.90)
DSO_STAR = 7.0                        # days of DSO excess that switch receivables to the reversal channel (KQ5)

# ---- confidence, Needle, league (sections 4.7-4.9) -------------------------------------------------------------
E_HIGH = 0.95        # between fuzzy (0.90) and exact (1.00)
E_MED = 0.745        # the entailed grade
NEEDLE_O = 0.5       # "roughly even chance" midpoint (ICD 203 bands). Applied to the discussion term D, not to O:
                     # decay stays inside S only (review R1, A11, B5)
NEEDLE_E = 0.90      # quoted evidence only
N_STAR = 3           # blocks for full league credit. Lazy Prices A-9; Beneish-Lee-Nichols; inference
TOP_N = 5            # findings summed: the case minimum of five findings
K_PEERS = 6          # nearest financial peers off-shortlist (inference: engine needs >= 4)
