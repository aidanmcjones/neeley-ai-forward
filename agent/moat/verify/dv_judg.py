"""Hand judgments from reading each sampled deal row against its source page (Opus verifier, 2026-10-17).
Keys: s = verified | corrected | dropped; fix = field -> corrected value (None blanks it); role = ok | swapped | junk | blank_filled | na;
et = error_type for ai_wrong; dup = kept deal_id when dropped as a duplicate; note = short reason."""
J = {}


def j(i, s="verified", role="ok", et=None, dup=None, note="", **fix):
    J[i] = dict(s=s, role=role, et=et, dup=dup, note=note, fix=fix)


# batch 1
j("D0038", "corrected", target_or_licensor="Forty Seven", note="target parsed as 'For'", role="junk")
j("D0044", acquirer_or_licensee="Astellas", role="blank_filled")
j("D0053")
j("D0057", "corrected", total_potential_usd_m=570.0, et="total_equals_milestones", note="total set to milestones only; 60 upfront + 510 milestones")
j("D0067", "dropped", et="not_a_deal", note="Celgene purchase-price allocation line (inventory fair value $4,511m) read as a license total")
j("D0118", "dropped", dup="D0126", note="10-K restatement of the Biogen-Denali $560m upfront already in D0126")
j("D0119", "corrected", role="swapped", acquirer_or_licensee="", target_or_licensor="Lytix Biopharma AS", et="role_swapped",
  note="filer paid Lytix; Lytix is licensor")
j("D0142", "dropped", et="termination_fee", note="Immunomedics merger termination fee $732.1m stored as acquisition value")
j("D0146", "corrected", stage_at_deal="", et="stage_wrong", note="Vicineum was a product candidate (BLA not yet approved); 'marketed' came from 'commercialize'")
j("D0148", "dropped", dup="D0126", et="component_double_count", note="$160m ROFN upfront is part of the $560m Biogen-Denali upfront")
j("D0154")
j("D0158", "dropped", dup="D0141", note="closing 8-K for Gilead-Immunomedics, same $21bn")
j("D0162", "dropped", dup="D0177", et="equity_read_as_total", note="Sage-Biogen 10-K paragraph; total 650 is the stock purchase, not deal value")
j("D0164", "corrected", milestones_usd_m=None, total_potential_usd_m=None, et="received_milestone_as_potential",
  note="$50m is a milestone already received, not the potential milestone pool")
j("D0173", "corrected", upfront_usd_m=584.0, total_potential_usd_m=584.0, acquirer_or_licensee="Sumitovant", target_or_licensor="Urovant",
  role="blank_filled", et="enterprise_vs_equity", note="text gives equity value $584m and EV $681m; table convention is equity value")
j("D0174", "dropped", et="not_a_deal", note="2018 sale of Masthercell subsidiary stake (CDMO), recapped in a 2020 8-K; not a drug license")
j("D0177", "corrected", milestones_usd_m=1595.0, total_potential_usd_m=2470.0, acquirer_or_licensee="Biogen", role="blank_filled",
  et="milestone_partial", note="milestones 475+520+300+300; row took one $525m opt-out figure")
j("D0183", "corrected", stage_at_deal="", note="platform patent assignment; 'preclinical' came from the phrase 'research collaboration'", et="stage_wrong")
j("D0186", "dropped", et="manufacturing_agreement", note="WuXi cell line license fee $0.2m is a manufacturing license, not a drug deal")
j("D0189", acquirer_or_licensee="Bayer", role="blank_filled")
j("D0193", "corrected", deal_type="asset purchase", upfront_usd_m=30.0, milestones_usd_m=11.0, total_potential_usd_m=41.0,
  acquirer_or_licensee="Medexus Pharmaceuticals", stage_at_deal="marketed", role="junk", et="wrong_numbers",
  note="IXINITY sale: $30m upfront, $11m milestones; row had 100/60 from 'in excess of' estimates; licensee was 'Exchange Commission'")
j("D0203", "corrected", deal_type="license", stage_at_deal="", et="stage_wrong", note="Berubicin HPI license; not marketed, not an asset purchase")
j("D0213", "corrected", total_potential_usd_m=162.0, target_or_licensor="NiKang", role="blank_filled", et="total_equals_milestones")
j("D0228", "corrected", stage_at_deal="", acquirer_or_licensee="Eli Lilly", role="blank_filled", et="stage_wrong",
  note="Ph1 refers to a different Precision program on the page")
j("D0232", "corrected", milestones_usd_m=None, total_potential_usd_m=None, et="received_milestone_as_potential",
  note="$5m is a milestone received, not potential")
j("D0238", "corrected", upfront_usd_m=None, stage_at_deal="", role="swapped", acquirer_or_licensee="Sentynl Therapeutics",
  target_or_licensor="Cyprium Therapeutics (Fortress)", et="role_swapped", note="$20m is upfront plus regulatory milestones through NDA; NDA not yet filed")
j("D0240", acquirer_or_licensee="Immedica", role="junk")
j("D0247", "corrected", stage_at_deal="Ph2", note="bemarituzumab described as 'Phase 3 ready' after Phase 2", et="stage_wrong")
j("D0250", "dropped", et="termination_fee", note="Acer-Relief termination agreement payment, not an acquisition")
j("D0269", "dropped", dup="D0247", et="merger_as_license", note="Amgen-Five Prime closing 8-K typed license/filed")
j("D0286", "dropped", et="supply_agreement", note="Gavi advance purchase agreement prepayment for COVID vaccine")
j("D0299", "corrected", total_potential_usd_m=1250.0, stage_at_deal="", acquirer_or_licensee="Amgen", target_or_licensor="Kyowa Kirin",
  role="blank_filled", et="total_equals_milestones", note="400 upfront + 850 milestones; KHK4083 was clinical, not marketed")
j("D0312", acquirer_or_licensee="Horizon Therapeutics", role="blank_filled")
j("D0313")
j("D0316", "corrected", target_or_licensor="", role="junk", note="licensor parsed as 'July 2021'")
j("D0327", "corrected", role="swapped", acquirer_or_licensee="Pfizer", target_or_licensor="Arvinas", milestones_usd_m=1400.0,
  total_potential_usd_m=2050.0, deal_type="co-development", et="role_swapped", note="Pfizer paid Arvinas; milestones 400 approval + 1000 commercial")
j("D0333", "corrected", therapeutic_area="oncology", et="ta_wrong", note="plinabulin is oncology (CIN); RMB converted in source text")
j("D0334", "corrected", total_potential_usd_m=None, et="total_less_than_milestones", note="total 180 below milestones 762; doc gives per-program caps only")
j("D0347", "corrected", role="swapped", acquirer_or_licensee="AbbVie", target_or_licensor="REGENXBIO", et="role_swapped")
j("D0350", "corrected", total_potential_usd_m=3150.0, et="total_equals_milestones")
j("D0366", "dropped", dup="D0350", note="Adaptimmune 10-K restatement; '4.2' is an unrelated GSK milestone")
j("D0375")
j("D0383", "dropped", et="not_biopharma", note="Canopy Growth cannabis call option")
j("D0388", "corrected", deal_type="asset purchase", stage_at_deal="", et="stage_wrong", note="NSI-189 sale; 'late-stage' describes Palisade")

# batch 2
j("D0389", "corrected", milestones_usd_m=None, total_potential_usd_m=250.0, et="threshold_as_milestone",
  note="$1bn is the JEMPERLI sales threshold; milestones ($105m) flow to Sagard, not to the seller")
j("D0404", "corrected", total_potential_usd_m=21.1, note="$5.0m cash + $16.1m stock to Combangio holders", et="total_partial")
j("D0405", "dropped", dup="D0404", et="duplicate", note="Kala-Combangio, same $16.1m stock value; quote not on cited page")
j("D0407", "corrected", deal_type="acquisition", acquirer_or_licensee="Pacira", target_or_licensor="Flexion Therapeutics", role="junk",
  et="merger_as_license", note="closing 8-K of Pacira-Flexion tender; licensee was 'Wells Fargo Bank'; $734.3m includes debt repayment")
j("D0425", "corrected", upfront_usd_m=0.136, milestones_usd_m=5.099, total_potential_usd_m=5.235, et="thousands_as_millions",
  note="10-K table in $ thousands: $136 upfront and $5,099 milestones; row read $5,099 as upfront in millions")
j("D0435", "corrected", deal_type="asset purchase", milestones_usd_m=76.0, total_potential_usd_m=81.0, target_or_licensor="Amplyx (Pfizer)",
  role="junk", et="total_less_than_milestones", note="milestones $7m to Amplyx + $69m Novartis pass-through; row had ms 69, total 7")
j("D0437", "corrected", stage_at_deal="", therapeutic_area="cardiovascular", acquirer_or_licensee="Ji Xing", role="blank_filled",
  et="ta_wrong", note="omecamtiv mecarbil is heart failure; $50m is upfront plus near-term milestones; not marketed")
j("D0451", acquirer_or_licensee="Merck")
j("D0452")
j("D0470", "corrected", stage_at_deal="", note="license amendment payment; no stage stated")
j("D0475", "dropped", dup="D0404", et="duplicate", note="Kala-Combangio pro forma exhibit")
j("D0478", "corrected", total_potential_usd_m=None, equity_usd_m=70.0, acquirer_or_licensee="CSL Vifor", role="junk",
  et="equity_read_as_total", note="$70m is a share sale to CSL Vifor, not deal value")
j("D0479")
j("D0487", "corrected", stage_at_deal="", acquirer_or_licensee="Roche", role="junk", et="stage_wrong",
  note="OpRegen was clinical, not marketed; licensee parsed as 'Lineage is eligible'")
j("D0496", target_or_licensor="Biosion", role="blank_filled")
j("D0506", "corrected", stage_at_deal="marketed", acquirer_or_licensee="Organon", role="junk", et="stage_wrong",
  note="XACIATO was approved (Dec 2021) before the Mar 2022 Organon deal; licensee parsed as 'Older'")
j("D0520", "corrected", stage_at_deal="marketed", note="fostamatinib commercial license; stage filled from page")
j("D0521", "corrected", deal_type="asset purchase", role="swapped", acquirer_or_licensee="Endo International plc",
  target_or_licensor="Nevakar Injectables, Inc", et="role_swapped", note="Endo acquired six candidates from Nevakar")
j("D0528", "corrected", upfront_usd_m=11600.0, total_potential_usd_m=11600.0, acquirer_or_licensee="Pfizer", target_or_licensor="Biohaven",
  role="blank_filled", et="debt_payoff_as_price", note="$1.26bn is Biohaven debt and preferred redemption; transaction consideration ~$11.6bn on the same 8-K")
j("D0551", "dropped", et="historical_deal_misdated", note="2018 Biogen-Karyopharm KPT-350 terms recapped in a 2022 8-K")
j("D0559", "dropped", role="swapped", et="historical_deal_misdated",
  note="2017 Sarepta-BioMarin license (Sarepta is licensee) dated by its 2021 amendment; out of window")
j("D0580", "corrected", deal_type="asset purchase", stage_at_deal="marketed", acquirer_or_licensee="Axsome Therapeutics",
  target_or_licensor="Jazz Pharmaceuticals", role="swapped", et="role_swapped", note="Axsome bought Sunosi from Jazz")
j("D0581", "dropped", et="not_a_deal", note="SomaLogic merger agreement SAFE definitions")
j("D0588", "dropped", et="termination_fee", note="ChemoCentryx-Amgen termination fee $119m")
j("D0589", acquirer_or_licensee="GSK")
j("D0592", "dropped", et="historical_deal_misdated", note="Lantheus-GE flurpiridaz sublicense (2017) dated Sep 2022 from a later Phase 3 sentence")
j("D0596")
j("D0616")
j("D0620", "corrected", deal_type="acquisition", note="Pasithea buys Alpha-5 integrin from sellers; $1m upfront cash")
j("D0621", "dropped", et="financing", note="Oaktree term loan commitments $100m")
j("D0624", "corrected", stage_at_deal="marketed", acquirer_or_licensee="LG Chem", target_or_licensor="AVEO", role="blank_filled",
  et="stage_wrong", note="AVEO had marketed FOTIVDA; 'preclinical' came from 'from discovery to clinical'")
j("D0628", acquirer_or_licensee="Sumitovant", target_or_licensor="Myovant", role="blank_filled",
  note="$2.9bn total company value; $1.7bn for the 48% not owned")
j("D0630", "dropped", et="historical_deal_misdated", note="2019 GSK-Lyell terms recapped at termination in 2022")
j("D0636", "dropped", dup="D0635", et="threshold_as_price", note="J&J-Abiomed CVR net sales threshold $3.7bn read as deal value")
j("D0646")
j("D0661", "dropped", et="settlement", note="settlement payment to former FWB holders")
j("D0668", "corrected", deal_type="acquisition", upfront_usd_m=27800.0, total_potential_usd_m=27800.0, acquirer_or_licensee="Amgen",
  target_or_licensor="Horizon Therapeutics", stage_at_deal="marketed", role="blank_filled", et="financing_as_price",
  note="$28.5bn is the bridge loan; equity value $27.8bn on the same page")
j("D0671", acquirer_or_licensee="GSK")
j("D0680", "dropped", dup="D0635", et="threshold_as_price", note="Abiomed CVR threshold again")
j("D0681", "corrected", stage_at_deal="", acquirer_or_licensee="Opus Genetics", role="junk", et="stage_wrong",
  note="IC-100/IC-200 were development candidates; buyer parsed as 'IC-200'")
j("D0683", "dropped", et="termination_fee", note="Akebia pays BioVectra to terminate supply agreements")
j("D0689", "dropped", et="not_a_deal", note="capitalized license expense amortization note (2018 LG Chem deal)")
j("D0692")
j("D0695")
j("D0707", "dropped", et="not_a_deal", note="Theravance investor slide: capital return program and royalty sale summary")

# batch 3
j("D0710", acquirer_or_licensee="Genentech", role="blank_filled", note="milestones are per Hit Program")
j("D0718", "dropped", dup="D0732", note="Axsome 10-K restatement of Pharmanovia $66m upfront")
j("D0732", "corrected", therapeutic_area="neurology", stage_at_deal="marketed", acquirer_or_licensee="Pharmanovia", role="blank_filled",
  et="stage_wrong", note="Sunosi (solriamfetol) was approved; row had Ph3 and renal/GI")
j("D0749", "dropped", et="termination_fee", note="Seagen-Pfizer merger termination fee $1.65bn")
j("D0752", "dropped", et="not_a_deal", note="convertible note change-of-control definition ('license with upfront of at least $25 million')")
j("D0757", "corrected", role="swapped", acquirer_or_licensee="Vertex", target_or_licensor="CRISPR Therapeutics AG", et="role_swapped",
  note="Vertex pays CRISPR for non-exclusive rights")
j("D0758")
j("D0761", "corrected", milestones_usd_m=503.0, total_potential_usd_m=593.0, acquirer_or_licensee="GSK", role="junk", et="threshold_as_milestone",
  note="milestones 70 reg + 115 commercial + 242.5 sales + 75.5 development; $1bn is a sales threshold")
j("D0766", "dropped", et="not_biopharma", note="TPG-OneOncology provider platform valuation")
j("D0767", "dropped", et="not_a_deal", note="merger agreement boilerplate ($1,000,000 contract threshold)")
j("D0773", "corrected", therapeutic_area="infectious disease", et="ta_wrong", note="Amoytop option on Aligos hepatitis B compounds")
j("D0774", "dropped", et="manufacturing_agreement", note="Oxford Biomedica licence and supply: upfront plus vector manufacturing cost")
j("D0777", "corrected", acquirer_or_licensee="J&J", role="junk", note="licensee parsed as 'J&J in October 2024 related'")
j("D0787", "corrected", milestones_usd_m=25.0, total_potential_usd_m=400.0, acquirer_or_licensee="", role="junk", et="wrong_numbers",
  note="royalty financing: $375m upfront + $25m milestone; CSL Behring is the royalty payer, not the purchaser")
j("D0794", "dropped", et="manufacturing_agreement", note="uBriGene buys Mustang's manufacturing facility")
j("D0807", "corrected", stage_at_deal="filed", therapeutic_area="neurology", target_or_licensor="Santhera", role="junk", et="stage_wrong",
  note="vamorolone 'currently under FDA review'; licensor parsed as EyePoint; CHF only for the equity price")
j("D0810", "corrected", stage_at_deal="", target_or_licensor="Pharmosa", role="blank_filled", et="stage_wrong", note="L606 was clinical, not marketed")
j("D0813", "corrected", deal_type="asset purchase", milestones_usd_m=750.0, total_potential_usd_m=2500.0, therapeutic_area="ophthalmology",
  acquirer_or_licensee="Bausch + Lomb", target_or_licensor="Novartis", role="blank_filled", et="wrong_numbers",
  note="XIIDRA sale: $1.75bn upfront + up to $750m milestones; row had milestones 2500")
j("D0823", "corrected", target_or_licensor="Neuren", role="junk", note="licensor parsed as 'Trofinetide'")
j("D0824", "dropped", et="historical_deal_misdated", note="GBT-Syros Dec 2019 deal recapped at 2023 termination")
j("D0851", "dropped", dup="D0813", note="Novartis 6-K of the same XIIDRA sale")
j("D0853", "dropped", et="not_a_deal", note="earn-out worked example in a purchase agreement")
j("D0856", "dropped", et="not_biopharma", note="Dyadic animal-free food protein platform license")
j("D0857", "corrected", upfront_usd_m=7.0, total_potential_usd_m=132.5, acquirer_or_licensee="Everest Medicines", role="junk",
  et="total_as_upfront", note="$132.5m is total payments; upfront is $7m")
j("D0861", "dropped", dup="D0813", note="Bausch + Lomb 10-K note on XIIDRA")
j("D0863", "corrected", target_or_licensor="Vanderbilt University", role="junk", note="licensor parsed as 'July 2025'")
j("D0864", "dropped", dup="D0893", et="received_milestone_as_potential", note="Entrada 10-K; 17.5 is a received milestone")
j("D0872", "dropped", dup="D0668", et="merger_as_license", note="Amgen-Horizon closing 8-K typed license")
j("D0874", "corrected", upfront_usd_m=4800.0, total_potential_usd_m=4800.0, acquirer_or_licensee="Bristol Myers Squibb", target_or_licensor="Mirati",
  role="blank_filled", et="cvr_in_price", note="$4.8bn equity value; $5.8bn includes CVR")
j("D0885", "corrected", acquirer_or_licensee="Pierre Fabre", role="junk", note="tab-cel expansion; licensee parsed as 'Drug Administration'")
j("D0893")
j("D0894", "corrected", role="swapped", acquirer_or_licensee="AbbVie", target_or_licensor="Aldeyra Therapeutics", stage_at_deal="filed",
  et="role_swapped", note="AbbVie option on reproxalap; FDA decision pending")
j("D0905", "corrected", role="swapped", acquirer_or_licensee="AnaptysBio", target_or_licensor="Centessa", therapeutic_area="immunology",
  et="role_swapped", note="Anaptys pays Centessa $7m for ANB101")
j("D0907", "corrected", milestones_usd_m=None, total_potential_usd_m=None, acquirer_or_licensee="Gilead", et="received_milestone_as_potential",
  note="$47m is variable consideration already earned")
j("D0910", "dropped", dup="D0909", et="merger_as_license", note="AbbVie-ImmunoGen own 8-K typed license")
j("D0911", "corrected", acquirer_or_licensee="Janssen", role="junk", note="buyer parsed as 'European Union'")
j("D0919", "corrected", deal_type="acquisition", upfront_usd_m=8700.0, therapeutic_area="psychiatry", acquirer_or_licensee="AbbVie",
  target_or_licensor="Cerevel Therapeutics", stage_at_deal="", role="blank_filled", et="merger_as_license",
  note="AbbVie-Cerevel $8.7bn equity value typed license / infectious disease")
j("D0920", "corrected", stage_at_deal="preclinical", acquirer_or_licensee="Dr. Reddy's", role="junk", et="stage_wrong",
  note="COYA 302 IND not yet accepted; Phase 2 is a future milestone")
j("D0926", "corrected", stage_at_deal="marketed", therapeutic_area="oncology", acquirer_or_licensee="Pfizer", target_or_licensor="Seagen",
  role="blank_filled", et="stage_wrong", note="closing release; Seagen had marketed ADCs; row had 'filed' and infectious disease")
j("D0927", "dropped", dup="D0926", et="duplicate", note="same Pfizer-Seagen page typed license")
j("D0928")
j("D0929", "dropped", et="not_a_deal", note="fairness opinion implied equity value range")
j("D0931", "corrected", milestones_usd_m=159.0, total_potential_usd_m=171.0, therapeutic_area="", et="wrong_numbers",
  note="Vyleesi sale: $12m upfront + $159m sales milestones = $171m")
j("D0932", "dropped", et="not_biopharma", note="MDNA early cancer detection diagnostics assets")
j("D0939", "dropped", dup="D0938", et="merger_as_license", note="BMS-Karuna own 8-K typed license")

# batch 4
j("D0940")
j("D0949", "corrected", milestones_usd_m=1581.0, total_potential_usd_m=1841.0, acquirer_or_licensee="Lantheus", target_or_licensor="POINT Biopharma",
  role="blank_filled", et="milestone_partial", note="PNT2002 $281m + $1.3bn sales milestones; deal dated 2023-12-31 but entered 'during 2022'")
j("D0968", "corrected", target_or_licensor="Harvard", role="junk", note="licensor parsed as 'Harvard as partial consideration'")
j("D0971", "dropped", et="not_a_deal", note="revenue recognition of the last portion of a GSK upfront")
j("D0974", "corrected", milestones_usd_m=1400.0, total_potential_usd_m=1450.0, acquirer_or_licensee="Janssen", role="junk",
  et="total_double_count", note="$1.45bn 'license and milestone payments' already includes the $50m upfront")
j("D0983", "corrected", acquirer_or_licensee="", role="junk", note="licensee parsed as 'ASU 606'; Japan distribution agreement")
j("D0985", "corrected", milestones_usd_m=4300.0, total_potential_usd_m=4500.0, et="milestone_partial",
  note="$1.3bn development + $3.0bn commercial milestones")
j("D0987", "corrected", stage_at_deal="", note="stage 'filed' not supported in the paragraph")
j("D0988", "dropped", et="historical_deal_misdated", note="$100m upfront was March 2019; row dated 2023-12-31")
j("D0991", "corrected", milestones_usd_m=None, total_potential_usd_m=None, et="total_less_than_milestones",
  note="milestones 491.3 > total 75; $75m dev milestones partly achieved and partly removed")
j("D1001", "corrected", milestones_usd_m=None, total_potential_usd_m=None, et="reimbursement_as_milestone", note="$44.5m is R&D reimbursement")
j("D1007", "corrected", total_potential_usd_m=367.0, stage_at_deal="", therapeutic_area="oncology", et="stage_wrong",
  note="CFT8919 (EGFR L858R degrader) was early-stage; 357 milestones + 10 upfront")
j("D1016")
j("D1017", "corrected", stage_at_deal="preclinical", milestones_usd_m=None, total_potential_usd_m=None, deal_type="asset purchase",
  note="'preclinical ROR1 ADC' on page; ms 5 not supported")
j("D1024")
j("D1025", "corrected", upfront_usd_m=None, milestones_usd_m=64.25, total_potential_usd_m=None, stage_at_deal="", acquirer_or_licensee="ReproNovo",
  role="junk", et="milestones_as_upfront", note="upfront undisclosed; $64.25m is the milestone pool; row also invented 300 milestones")
j("D1037", "dropped", et="milestone_event_as_deal", note="8-K announces a $40m milestone on the 2022 Roche-Repare deal, not a new deal")
j("D1038", "corrected", milestones_usd_m=330.0, acquirer_or_licensee="Takeda", role="blank_filled", et="total_as_milestones",
  note="$300m upfront + $330m milestones = $630m deal value")
j("D1041", "dropped", et="historical_deal_misdated", note="2019 Neurocrine-Voyager agreement")
j("D1042", "corrected", milestones_usd_m=None, total_potential_usd_m=None, acquirer_or_licensee="GSK", role="junk",
  note="milestone pool not stated in paragraph; licensee parsed as 'Meiji's regulatory documents'")
j("D1046")
j("D1053", "corrected", stage_at_deal="preclinical", acquirer_or_licensee="Otsuka", role="junk", et="stage_wrong",
  note="headline: sale of preclinical PD-1 agonist; row had Ph3")
j("D1055", "corrected", milestones_usd_m=40.0, total_potential_usd_m=65.0, et="milestone_partial", note="$10m regulatory + $30m sales milestones")
j("D1062", "dropped", et="financing", note="Series J preferred stock covenants")
j("D1064", "dropped", et="manufacturing_agreement", note="Germfree-Orgenesis manufacturing asset purchase")
j("D1065", "corrected", upfront_usd_m=None, role="swapped", acquirer_or_licensee="Bayer", target_or_licensor="BridgeBio (Eidos)",
  et="role_swapped", note="$310m covers upfront plus regulatory and sales milestones through 2026; Bayer is licensee")
j("D1071", "dropped", dup="D0695", note="Astellas-Cartesian Xork termination recap")
j("D1073", "dropped", dup="D1046", et="merger_as_license", note="Gilead-CymaBay closing")
j("D1085", "dropped", et="financing", note="Juvenescence warrant proceeds")
j("D1090", "dropped", dup="D1064", et="manufacturing_agreement")
j("D1107", "dropped", et="financing", note="Organon indenture asset-sale basket")
j("D1108", "corrected", upfront_usd_m=None, total_potential_usd_m=625.5, therapeutic_area="oncology", et="total_double_count",
  note="$11.5m is upfront plus near-term payments, already inside the $625.5m total")
j("D1116")
j("D1117", "dropped", dup="D1116", et="duplicate", note="Evommune-AprilBio second 10-K paragraph")
j("D1128", "dropped", dup="D1108", et="duplicate", note="same Verastem-GenFleet slide")
j("D1138", "corrected", milestones_usd_m=None, note="$1.395m purchase price, $0.1m at closing")
j("D1139", "dropped", et="historical_deal_misdated", note="Genentech-Relay termination recap (2020 deal)")
j("D1140", "dropped", et="settlement", note="Beam settlement with a research institution")
j("D1142", "corrected", upfront_usd_m=None, milestones_usd_m=None, total_potential_usd_m=406.5, acquirer_or_licensee="IDEAYA",
  target_or_licensor="Biocytogen", role="swapped", et="total_as_upfront", note="$406.5m is total potential; upfront undisclosed")
j("D1148", acquirer_or_licensee="Pharmacosmos", target_or_licensor="G1 Therapeutics", role="blank_filled")
j("D1150", "dropped", et="historical_deal_misdated", note="Takeda-Ovid soticlestat 2021 deal recapped in 10-K")
j("D1154", "corrected", acquirer_or_licensee="Emergent", stage_at_deal="marketed", role="junk",
  note="TEMBEXA sale; licensee parsed as 'Accounting Standards Codification'; date is a later 10-K reference")
j("D1155", "dropped", dup="D0856", et="not_biopharma")
j("D1156", "corrected", deal_type="asset purchase", milestones_usd_m=600.0, total_potential_usd_m=1300.0, role="swapped",
  acquirer_or_licensee="Merck", target_or_licensor="Curon Biopharmaceutical", et="role_swapped",
  note="$300m development + $300m regulatory milestones")
j("D1157", "dropped", dup="D0592", et="historical_deal_misdated")

# batch 5
j("D1165", acquirer_or_licensee="Bristol Myers Squibb", role="blank_filled")
j("D1172")
j("D1175", "corrected", deal_type="royalty monetization", therapeutic_area="", et="royalty_sale_as_license",
  note="sale of Vertex Cas9 license payments to DRI")
j("D1179", "dropped", role="swapped", et="historical_deal_misdated", note="Iterum in-licensed sulopenem from Pfizer (2015); row had Pfizer as licensee")
j("D1185", "dropped", et="aggregate_not_deal", note="$167.5m is the sum of upfronts from several 2024 licenses")
j("D1191", "dropped", et="financing", note="Hercules term loan definitions")
j("D1192", "dropped", et="not_biopharma", note="acquisition of a physician practice platform (RCA)")
j("D1193", "dropped", et="not_biopharma", note="acquisition of 71% of a physician practice group (GIA)")
j("D1223", "dropped", dup="D0757", et="received_milestone_as_potential", note="CRISPR 10-K revenue paragraph; $200m is the CASGEVY approval milestone")
j("D1234", "dropped", et="historical_deal_misdated", note="Mallinckrodt-Silence upfront received in 2019")
j("D1237", "dropped", et="aggregate_not_deal", note="Sarepta aggregate future milestone commitments ($2.3bn, $10.3bn Arrowhead)")
j("D1253", "dropped", et="component_double_count", note="$69.4m is the part of the ALK upfront allocated to the EEA license")
j("D1269", "corrected", milestones_usd_m=None, total_potential_usd_m=None, acquirer_or_licensee="", target_or_licensor="Mabworks", role="junk",
  et="cost_as_milestone", note="$12.0m is total CLYM116 program cost")
j("D1274", "corrected", role="swapped", acquirer_or_licensee="iBio", target_or_licensor="AstralBio", stage_at_deal="", et="role_swapped",
  note="iBio pays AstralBio the $750,000 upfront fee")
j("D1276", "corrected", therapeutic_area="", note="TA 'neurology' not supported on page")
j("D1281", "dropped", dup="D1212", et="duplicate", note="Takeda-Keros effectiveness 8-K; same $200m upfront as Dec 2024 announcement")
j("D1293", "corrected", upfront_usd_m=20.0, total_potential_usd_m=20.0, note="XOMA-Pulmokine upfront cash $20.0m net")
j("D1308")
j("D1309", "corrected", deal_type="asset purchase", milestones_usd_m=15.0, et="total_as_milestones",
  note="$84m upfront + $15m contingent = $99m")
j("D1317", "corrected", milestones_usd_m=960.0, total_potential_usd_m=1005.0, stage_at_deal="", acquirer_or_licensee="Novo Nordisk",
  role="junk", et="milestone_partial", note="$485m regulatory/launch + $475m sales milestones; LX9851 not marketed")
j("D1320", "corrected", milestones_usd_m=13.0, total_potential_usd_m=24.0, therapeutic_area="rare disease", et="milestone_partial",
  note="$11m regulatory + $2m commercial; sebetralstat is HAE, not neurology")
j("D1322")
j("D1328", "dropped", et="historical_deal_misdated", note="SymBio upfront received in 2011")
j("D1330", "corrected", stage_at_deal="marketed", acquirer_or_licensee="Merck KGaA", target_or_licensor="SpringWorks Therapeutics",
  role="blank_filled", note="USD equity value; EUR given only for EV")
j("D1333", "corrected", total_potential_usd_m=475.0, stage_at_deal="Ph3", et="total_equals_milestones",
  note="'Dimerix' Phase 3 drug candidate'; total = 30 + 445")
j("D1344", "corrected", milestones_usd_m=None, total_potential_usd_m=2200.0, et="per_program_as_total",
  note="$500m milestones is per program; page states total potential exceeding $2.2bn")
j("D1352", "corrected", total_potential_usd_m=None, note="milestones and option fees are per candidate")
j("D1353", note="$250m first tranche of the Royalty Pharma-Revolution facility")
j("D1360", "corrected", milestones_usd_m=None, total_potential_usd_m=None, et="threshold_as_milestone", note="1000 not a milestone pool")
j("D1383", "corrected", role="swapped", acquirer_or_licensee="", target_or_licensor="Saniona", et="role_swapped",
  note="filer paid Saniona $42.5m; Saniona is licensor")
j("D1391", "corrected", therapeutic_area="oncology", et="ta_wrong", note="Imdelltra (tarlatamab) royalty")
j("D1399", note="TAPI milestones are manufacturing-related")
j("D1411", "corrected", milestones_usd_m=None, total_potential_usd_m=None, equity_usd_m=325.0, acquirer_or_licensee="Sarepta",
  target_or_licensor="Arrowhead", role="blank_filled", et="equity_read_as_milestone", note="$325m is equity investment, not milestones")
j("D1413", "corrected", total_potential_usd_m=None, acquirer_or_licensee="", target_or_licensor="RemeGen", role="junk",
  et="warrant_as_total", note="$177.4m is the warrant fair value")
j("D1420", "corrected", deal_type="asset purchase", acquirer_or_licensee="Biossil", role="junk")
j("D1422", "corrected", target_or_licensor="InnoCare", role="junk", note="$100m is upfront plus near-term milestones; licensor parsed as 'Primary Progressive MS'")
j("D1424", note="$2.1bn includes $1.50/share CVR")
j("D1430", "corrected", deal_type="acquisition", note="Life Molecular Imaging acquisition, not a license")
j("D1441", "dropped", dup="D0602", et="duplicate", note="Spero corporate deck restating the 2022 GSK tebipenem terms")
j("D1442")
j("D1453", "dropped", et="not_biopharma", note="Cencora-OneOncology")
j("D1458", "corrected", milestones_usd_m=25.0, total_potential_usd_m=32.3, target_or_licensor="Athanor", role="junk",
  et="threshold_as_milestone", note="$500m is an asset-sale proceeds trigger; the milestone is $25m")
j("D1464", "corrected", total_potential_usd_m=1160.0, acquirer_or_licensee="Novartis", et="total_equals_upfront")
j("D1469", "dropped", et="historical_deal_misdated", note="2018 Acadia-Neuren agreement")
j("D1472", "dropped", et="historical_deal_misdated", note="AstraZeneca-Ionis collaboration terms in a FY2025 10-K; original deal predates window")
j("D1473", "dropped", et="historical_deal_misdated", note="Novartis-Ionis pelacarsen terms (2017/2019) in a FY2025 10-K")
j("D1482", "corrected", milestones_usd_m=None, total_potential_usd_m=None, acquirer_or_licensee="", role="junk",
  note="no milestone pool in paragraph")
j("D1492", "dropped", et="historical_deal_misdated", note="Incyte-MacroGenics retifanlimab (2017) typed royalty monetization")
j("D1494", "dropped", dup="D0433", et="duplicate", note="Foghorn 10-K restatement of the Dec 2021 Lilly $300m upfront")
j("D1498")
j("D1507", "corrected", therapeutic_area="rare disease", note="Shionogi-Maze MZE001 (Pompe); deal was 2024")
j("D1521", "dropped", et="financing", note="Bausch Health term loan amendment")
j("D1528", "corrected", target_or_licensor="Amicus", note="$5,235m aggregate transaction value includes debt repayment")
j("D1530", "corrected", milestones_usd_m=115.0, total_potential_usd_m=135.0, et="milestone_partial", note="$50m development + $65m sales")
j("D1534", "corrected", milestones_usd_m=38.0, total_potential_usd_m=38.3, acquirer_or_licensee="Rasayana", role="junk", et="milestone_partial",
  note="$16m development + $22m sales")
j("D1535", acquirer_or_licensee="Gilead", target_or_licensor="Arcellx", role="blank_filled")
j("D1539", "corrected", milestones_usd_m=126.0, total_potential_usd_m=127.0, stage_at_deal="preclinical", et="total_equals_milestones")
j("D1541", "corrected", deal_type="asset purchase", milestones_usd_m=20.0, total_potential_usd_m=35.0, et="total_double_count",
  note="up to $35m = $15m upfront + $20m milestones")
j("D1544", "dropped", et="financing", note="warrant revenue milestone definition")
j("D1556", "dropped", dup="D1535", et="merger_as_license", note="Gilead closing 8-K, funds used $7.1bn")
j("D1572", "dropped", dup="D1571", et="merger_as_license")
j("D1577", "corrected", upfront_usd_m=None, milestones_usd_m=None, total_potential_usd_m=1100.0, target_or_licensor="Innovent", stage_at_deal="",
  role="blank_filled", et="total_as_upfront", note="~$1.1bn is upfront plus all milestones; Phase 2 is planned")
j("D1578", "dropped", et="financing", note="indenture lien basket")
j("D1579", "corrected", milestones_usd_m=1100.0, total_potential_usd_m=2650.0, therapeutic_area="cardiovascular", et="total_as_milestones",
  note="$1.55bn upfront + $1.1bn milestones = $2.65bn")
j("D1581", "dropped", et="financing", note="Mirador PIPE $132m")
j("D1589", note="$40m upfront and R&D payments on option exercise")
j("D1595", "corrected", role="swapped", acquirer_or_licensee="PTC Therapeutics", target_or_licensor="Sangamo Therapeutics", stage_at_deal="",
  therapeutic_area="rare disease", et="role_swapped", note="PTC buys ST-920 from Sangamo")
j("D1598", "dropped", dup="D1571", et="merger_as_license")
j("D1600", "corrected", role="swapped", acquirer_or_licensee="Yarrow Bioscience", target_or_licensor="GenSci", et="role_swapped",
  note="GenSci received the $70m upfront, so GenSci is licensor")
j("D1604")
j("D1607", "corrected", total_potential_usd_m=8000.0, acquirer_or_licensee="Sanofi", target_or_licensor="Regeneron", stage_at_deal="",
  therapeutic_area="", role="blank_filled", et="stage_wrong", note="Sixth Amendment: $1.0bn upfront + $7.0bn milestones; row had stage filed, infectious disease")
j("D0248", "dropped", et="financing", note="incremental term loan $1.6bn to fund an acquisition, typed acquisition")

# extras A (benchmark feeder rows, n<10 cells; quote-level review)
j("D0007")
j("D0011", "corrected", role="swapped", acquirer_or_licensee="Incyte", target_or_licensor="MorphoSys", et="role_swapped",
  note="MorphoSys receives the $750m upfront; Incyte is licensee")
j("D0017", "corrected", role="swapped", acquirer_or_licensee="Recognify (ATAI)", target_or_licensor="Allergan", stage_at_deal="", therapeutic_area="",
  et="role_swapped", note="Recognify paid Allergan; stage/TA not stated")
j("D0025", "corrected", stage_at_deal="", acquirer_or_licensee="Pfizer", role="blank_filled", et="stage_wrong", note="no stage in quote; asset was not marketed")
j("D0048", "corrected", milestones_usd_m=450.0, stage_at_deal="", acquirer_or_licensee="Supernus", role="blank_filled", et="total_equals_milestones",
  note="$475m total includes the $25m upfront; NV-5138 was clinical, not marketed")
j("D0056")
j("D0059", "dropped", et="settlement", note="Krystal-PeriphaGen 2022 litigation settlement plus asset transfer; dated 2020")
j("D0060", "dropped", dup="D0059", et="settlement")
j("D0063", "dropped", dup="D0059", et="settlement")
j("D0076", "corrected", milestones_usd_m=None, total_potential_usd_m=None, et="received_milestone_as_potential", note="$3.0m milestone already achieved")
j("D0081", "dropped", dup="D0076", et="duplicate")
j("D0083", "corrected", upfront_usd_m=None, et="equity_in_upfront", note="$100m is upfront cash plus equity combined")
j("D0086", "corrected", stage_at_deal="", et="stage_wrong", note="SEL-212 was in Phase 3, not marketed")
j("D0087", "corrected", target_or_licensor="Takeda", role="junk")
j("D0089", "dropped", et="historical_deal_misdated", note="milestone received under a Sep 2019 KemPharm license")
j("D0090", "corrected", total_potential_usd_m=865.0, acquirer_or_licensee="AbbVie", role="blank_filled", et="total_less_than_milestones")
j("D0093")
j("D0094", "corrected", stage_at_deal="marketed", target_or_licensor="Regeneron", role="junk", note="ARCALYST was approved; licensor parsed as 'FDA-approved'")
j("D0107", "corrected", role="swapped", acquirer_or_licensee="Angelini", target_or_licensor="Ovid Therapeutics", et="role_swapped")
j("D0114", "corrected", stage_at_deal="", therapeutic_area="hematology", acquirer_or_licensee="", role="junk", et="ta_wrong",
  note="ciraparantag is anticoagulant reversal; licensee parsed as 'AMSTERDAM'")
j("D0116")
j("D0131")
j("D0140", "corrected", role="swapped", acquirer_or_licensee="Gilead", target_or_licensor="Jounce Therapeutics", et="role_swapped")
j("D0143", "corrected", milestones_usd_m=2600.0, total_potential_usd_m=3200.0, therapeutic_area="oncology", et="milestone_partial",
  note="$850m + $1.75bn milestones")
j("D0153", acquirer_or_licensee="Takeda", role="junk")
j("D0156", acquirer_or_licensee="Vifor Pharma", role="junk")
j("D0160", "corrected", therapeutic_area="hematology", acquirer_or_licensee="Sobi", role="junk", et="ta_wrong", note="systemic pegcetacoplan")
j("D0176")
j("D0228", "dropped", dup="D0176", note="receipt of the Lilly $100m upfront already in D0176; 'Ph1' was another program")
j("D0188", "dropped", et="royalty_financing_as_license", note="BioCryst royalty purchase; $150m/$230m are net sales tiers, not payments")
j("D0192", "corrected", stage_at_deal="Ph1", et="stage_wrong", note="'clinical stage SHP2' inhibitor")
j("D0195", "corrected", upfront_usd_m=880.0, total_potential_usd_m=880.0, stage_at_deal="", acquirer_or_licensee="Eli Lilly", target_or_licensor="Prevail",
  role="blank_filled", et="cvr_in_price", note="$880m at closing; $1.04bn includes CVR")
j("D0214", "dropped", dup="D0153", et="wrong_parties", note="Takeda-Arrowhead fazirsiran $300m labelled Lilly/Foghorn")
j("D0216", "dropped", dup="D0153", et="duplicate")
j("D0218", "corrected", deal_type="acquisition", stage_at_deal="", et="stage_wrong", note="AzurRx acquires First Wave Bio")
j("D0226", "corrected", acquirer_or_licensee="", role="junk", note="licensee parsed as 'Jefferies LLC' (underwriter)")
j("D0234", "corrected", acquirer_or_licensee="Bristol Myers Squibb", role="junk")
j("D0235")
j("D0236", "corrected", acquirer_or_licensee="Almirall", role="junk")
j("D0243", "corrected", role="swapped", acquirer_or_licensee="Taysha", target_or_licensor="Hannah's Hope Fund", et="role_swapped")
j("D0263", "corrected", stage_at_deal="", therapeutic_area="infectious disease", acquirer_or_licensee="Janssen", role="blank_filled", et="ta_wrong",
  note="Cidara influenza Cloudbreak program")
j("D0265", "dropped", et="historical_deal_misdated", note="2019 KemPharm-Commave license")
j("D0271", "corrected", acquirer_or_licensee="", role="junk")
j("D0273", "corrected", milestones_usd_m=352.5, total_potential_usd_m=362.5, acquirer_or_licensee="Boston Pharmaceuticals", role="junk")
j("D0274")
j("D0290", "corrected", role="swapped", acquirer_or_licensee="New Life", target_or_licensor="Sonnet BioTherapeutics", et="role_swapped")
j("D0304", "corrected", stage_at_deal="", et="stage_wrong", note="ensifentrine not yet approved")
j("D0324", "dropped", dup="D0304", et="duplicate")
j("D0327", "dropped", dup="D0329", role="swapped", et="role_swapped", note="Pfizer 10-K restatement of the Arvinas deal with roles swapped")
j("D0329", acquirer_or_licensee="Pfizer", role="blank_filled")
j("D0335", "corrected", stage_at_deal="", therapeutic_area="neurology", acquirer_or_licensee="Bristol Myers Squibb", role="blank_filled", et="stage_wrong",
  note="tau program; row had marketed and renal/GI")
j("D0338", "corrected", therapeutic_area="oncology", et="ta_wrong")
j("D0343", "corrected", acquirer_or_licensee="Takeda", role="junk")
j("D0353", "corrected", upfront_usd_m=None, total_potential_usd_m=1500.0, et="total_as_upfront", note="$1.5bn is upfront plus all milestones")
j("D0359", "corrected", milestones_usd_m=790.0, stage_at_deal="", et="total_as_milestones", note="$135m + $655m milestones; $845m total")
j("D0360", "corrected", therapeutic_area="immunology", et="ta_wrong", note="axatilimab cGVHD")
j("D0370", "dropped", et="not_a_deal", note="Radionetics spin-out financing; $140m is not an upfront")
j("D0377")
j("D0380", "dropped", dup="D0407", et="threshold_as_price", note="$500m is a ZILRETTA sales CVR threshold, not the price")
j("D0381", "corrected", upfront_usd_m=400.0, total_potential_usd_m=400.0, et="wrong_numbers", note="$400m equity at closing ($9.10/share with CVR ~$450m); row took $80m synergies")
j("D0386", "corrected", stage_at_deal="", et="stage_wrong")
j("D0400", "corrected", therapeutic_area="psychiatry", et="ta_wrong")
j("D0401", "corrected", upfront_usd_m=None, milestones_usd_m=740.0, total_potential_usd_m=1240.0, stage_at_deal="", acquirer_or_licensee="Pfizer",
  role="blank_filled", et="total_as_upfront", note="$1.24bn is upfront plus milestones combined")
j("D0429", "corrected", milestones_usd_m=3385.0, total_potential_usd_m=3585.0, et="milestone_partial", note="$485m + $2.9bn milestones")
j("D0434", "corrected", total_potential_usd_m=1545.0, acquirer_or_licensee="Horizon", role="blank_filled", et="total_equals_milestones")
j("D0439")
j("D0445", "corrected", total_potential_usd_m=11.8, et="total_equals_upfront")
j("D0463", "corrected", role="swapped", acquirer_or_licensee="Ultragenyx", target_or_licensor="Regeneron", et="role_swapped",
  note="Regeneron receives the $30m upfront")
j("D0466")
j("D0467")
j("D0469", "corrected", role="swapped", acquirer_or_licensee="Journey Medical", target_or_licensor="VYNE", et="role_swapped",
  note="Journey buys VYNE's MST franchise; acquirer parsed as 'East West Bank'")
j("D0471")
j("D0489", "corrected", total_potential_usd_m=None, et="equity_read_as_total", note="$20m is the equity purchase")
j("D0497", "dropped", et="historical_deal_misdated", note="Gilead-Hookipa original 2018 agreement upfront")

# extras B
j("D0498", "corrected", deal_type="asset purchase", milestones_usd_m=None, total_potential_usd_m=None, acquirer_or_licensee="Sentynl", role="junk",
  et="total_equals_milestones", note="sales milestones not quantified in quote")
j("D0499", "corrected", acquirer_or_licensee="Thea Open Innovation", role="junk", note="licensee parsed as 'Retinitis Pigmentosa'")
j("D1016", "dropped", dup="D0499", et="duplicate", note="Kiora 10-K restatement of the Thea KIO-301 deal, misdated 2024")
j("D0502", "corrected", total_potential_usd_m=None, stage_at_deal="", et="stage_wrong", note="IGM IgM platform; not marketed; total not supported")
j("D0508", "dropped", dup="D0705", et="duplicate", note="Spruce-Kaken 10-K paragraph")
j("D0705", "corrected", stage_at_deal="", therapeutic_area="rare disease", et="stage_wrong", note="tildacerfont was in Phase 2")
j("D0514", "dropped", et="not_a_deal", note="amendment removing ~$100m of milestones owed to Vyera")
j("D0518", "corrected", stage_at_deal="", et="stage_wrong")
j("D0525", "corrected", deal_type="royalty monetization", et="royalty_financing_as_license",
  note="$100m upfront + $160m on approval is a vonoprazan revenue-interest financing")
j("D0526", "corrected", target_or_licensor="Sumitomo Pharma", role="junk")
j("D0530", "corrected", milestones_usd_m=815.0, total_potential_usd_m=905.0, stage_at_deal="", et="total_double_count",
  note="$905m includes the $90m upfront; BBP-398 was Phase 1")
j("D0545", "corrected", stage_at_deal="", therapeutic_area="oncology", et="ta_wrong", note="camonsertib is oncology; stage not stated")
j("D0549", "dropped", et="historical_deal_misdated", note="termination recap of an earlier Fulcrum agreement")
j("D0552", "corrected", total_potential_usd_m=1475.0, et="total_equals_milestones")
j("D0554", note="$890m includes CVR")
j("D0557")
j("D0563", "dropped", dup="D0506", et="duplicate", note="Organon-Dare XACIATO license after the March option; roles were swapped")
j("D0577", "dropped", et="historical_deal_misdated", note="terminated Roche-Sesen license recap")
j("D0579", "corrected", therapeutic_area="", acquirer_or_licensee="Vertex", role="blank_filled")
j("D0583", "corrected", target_or_licensor="CSPC", role="junk")
j("D0586", "corrected", acquirer_or_licensee="", role="junk")
j("D0591", "dropped", et="historical_deal_misdated", note="original agreement upfront recap")
j("D0593", "corrected", upfront_usd_m=None, milestones_usd_m=425.0, et="milestones_as_upfront", note="upfront undisclosed; $425m is milestones")
j("D0595", "dropped", dup="D0593", et="milestones_as_upfront")
j("D0600", "corrected", role="swapped", acquirer_or_licensee="NeuroBo", target_or_licensor="Dong-A ST", therapeutic_area="metabolic", et="role_swapped",
  note="Dong-A receives the upfront in NeuroBo preferred stock")
j("D0602", "corrected", milestones_usd_m=525.0, total_potential_usd_m=591.0, acquirer_or_licensee="GSK", role="junk", et="threshold_as_milestone",
  note="milestones up to $525m (per D0642 on the same deal)")
j("D0642", "dropped", dup="D0602", et="duplicate")
j("D1042", "dropped", dup="D0602", et="historical_deal_misdated", note="Spero 10-K restatement of the 2022 GSK deal dated 2024")
j("D0625", "corrected", therapeutic_area="", note="Jatenzo bankruptcy sale")
j("D0632", "corrected", acquirer_or_licensee="Astellas", therapeutic_area="neurology", stage_at_deal="", role="junk", et="ta_wrong")
j("D0635", "dropped", et="not_biopharma", note="Abiomed is a medical device company")
j("D0640", "dropped", et="aggregate_not_deal", note="$700-750m covers two targets (Oyster Point and Famy)")
j("D0645", "dropped", dup="D0506", et="duplicate", note="10-K mention of the Organon $10m upfront")
j("D0665", note="JPY converted in source text (Y3.5bn = $26.0m)")
j("D0669", "dropped", et="market_size_as_value", note="$25bn is a dysmenorrhea market size estimate")
j("D0684")
j("D0700")
j("D0703")
j("D0706", "corrected", stage_at_deal="marketed", target_or_licensor="Albireo", role="junk", et="stage_wrong", note="Bylvay was approved")
j("D0727", "corrected", total_potential_usd_m=535.0, stage_at_deal="", target_or_licensor="Goldfinch Bio", et="total_equals_milestones",
  note="milestones are per candidate; lead candidate clinical-stage")
j("D0731")
j("D0893", "dropped", dup="D0731", et="duplicate", note="Entrada 8-K amendment restating the Vertex terms")
j("D0751", "corrected", stage_at_deal="", et="stage_wrong")
j("D0755", "corrected", role="swapped", acquirer_or_licensee="Moderna", target_or_licensor="Generation Bio", et="role_swapped")
j("D0765", "corrected", stage_at_deal="", acquirer_or_licensee="Merck", target_or_licensor="Prometheus Biosciences", role="blank_filled", et="stage_wrong",
  note="PRA023 was clinical, not preclinical")
j("D0779", "dropped", et="financing", note="Ovid buys Graviton Series A preferred")
j("D0780")
j("D0782", "corrected", stage_at_deal="", et="stage_wrong")
j("D0792", "dropped", et="milestone_event_as_deal", note="Chiesi $20m approval milestone")
j("D0795", "dropped", et="not_a_deal", note="Seagen fairness opinion NOL value")
j("D0796")
j("D0802", "corrected", stage_at_deal="", target_or_licensor="AOP Orphan", role="junk", note="2021 AOP license recapped in 2023 8-K")
j("D0808", "corrected", deal_type="royalty monetization", therapeutic_area="", et="royalty_sale_as_license", note="Blackstone royalty purchase")
j("D0819")
j("D0821", "dropped", dup="D0506", et="duplicate")
j("D0838", "corrected", upfront_usd_m=60.0, total_potential_usd_m=60.0, et="cvr_in_price", note="$60m aggregate cash plus CVR")
j("D0839", "corrected", total_potential_usd_m=70.25, et="total_equals_milestones")
j("D0841", "corrected", role="swapped", acquirer_or_licensee="Day One", target_or_licensor="Sprint Bioscience", et="role_swapped")
j("D0855", "corrected", deal_type="asset purchase", milestones_usd_m=700.0, total_potential_usd_m=1000.0, stage_at_deal="", et="total_as_milestones",
  note="up to $1bn total including $300m upfront")
j("D0865")
j("D0871", "corrected", stage_at_deal="", acquirer_or_licensee="Sanofi", role="junk", note="EUR converted in source (EUR 469m = $500m)")
j("D0875", "corrected", milestones_usd_m=305.0, total_potential_usd_m=320.0, et="milestone_partial")
j("D0877", "corrected", milestones_usd_m=None, total_potential_usd_m=None, note="$2bn milestone figure not in the quoted paragraph")
j("D0878", "dropped", dup="D0506", et="duplicate")
j("D0884", "dropped", et="not_a_deal", note="23andMe non-exclusive data license")
j("D0906")
j("D0916", "corrected", stage_at_deal="", target_or_licensor="Mereo", note="leflutrozole: $1.0m upfront")
j("D1025", "dropped", dup="D0916", et="milestones_as_upfront")
j("D0930", "dropped", dup="D0911", et="received_milestone_as_potential")
j("D0933", "dropped", et="historical_deal_misdated", note="upfront received January 2019")
j("D0935", "dropped", et="not_a_deal", note="amendment reducing an option fee")
j("D0938", "corrected", therapeutic_area="psychiatry", acquirer_or_licensee="Bristol Myers Squibb", target_or_licensor="Karuna", role="blank_filled", et="ta_wrong")
j("D0993", "corrected", milestones_usd_m=None, total_potential_usd_m=None, acquirer_or_licensee="Gilead", role="junk", et="received_milestone_as_potential")
j("D1000", "corrected", stage_at_deal="", et="stage_wrong")
j("D1018", "dropped", dup="D1038", et="duplicate")
j("D1020", "dropped", dup="D0761", et="duplicate")
j("D1029")
j("D1031")

# extras C
j("D1031", "dropped", et="not_biopharma", note="Philip Morris (PMPSA) license amendment, inhalation tech")
j("D1032", "dropped", dup="D1031", et="not_biopharma")
j("D1033", "corrected", stage_at_deal="", target_or_licensor="Bausch + Lomb", role="junk", note="$2m cash plus $3m stock")
j("D1034", "corrected", role="swapped", upfront_usd_m=None, milestones_usd_m=138.35, acquirer_or_licensee="Lee's Pharm", target_or_licensor="Windtree",
  et="milestones_as_upfront", note="Windtree receives; $3.1m is upfront plus pre-development and development milestones")
j("D1038", "dropped", dup="D1039", et="total_as_milestones", note="Protagonist 10-K; 8-K row kept")
j("D1039", "corrected", milestones_usd_m=330.0, total_potential_usd_m=630.0, therapeutic_area="hematology", acquirer_or_licensee="Takeda",
  role="blank_filled", et="milestone_partial", note="$300m + $330m = $630m per Protagonist 10-K; rusfertide is hematology")
j("D1044", "dropped", et="financing", note="Zevra-Acer bridge loan")
j("D1048", "corrected", upfront_usd_m=None, therapeutic_area="", et="milestones_as_upfront", note="$9m = upfront plus research milestones")
j("D1051", "corrected", stage_at_deal="", et="stage_wrong")
j("D1075", "corrected", milestones_usd_m=3.5, total_potential_usd_m=33.5, et="total_double_count", note="$33.5m total includes $30m upfront (payable in stock)")
j("D1078", "corrected", upfront_usd_m=30.0, equity_usd_m=13.5, total_potential_usd_m=634.0, et="equity_in_upfront", note="$43.5m includes $13.5m equity")
j("D1087", "dropped", dup="D1108", et="total_double_count")
j("D1110", "corrected", upfront_usd_m=70.0, milestones_usd_m=565.0, total_potential_usd_m=635.0, et="equity_in_upfront",
  note="$70m upfront + $30m R&D funding; option fees $100m + milestones $465m")
j("D1127", "dropped", et="market_size_as_value", note="$100bn obesity market forecast read as upfront")
j("D1147", "corrected", therapeutic_area="oncology", et="ta_wrong", note="masked T-cell engagers; plus $75m escrowed milestone")
j("D1152")
j("D1159", "dropped", dup="D1147", et="duplicate")
j("D1163", "corrected", milestones_usd_m=118.5, et="total_as_milestones", note="$15m upfront and near-term + $118.5m = $133.5m")
j("D1174", "corrected", target_or_licensor="Pharmosa", role="blank_filled")
j("D1182", "corrected", total_potential_usd_m=2422.0, et="total_equals_milestones")
j("D1467", "dropped", dup="D1182", et="duplicate")
j("D1195", "corrected", therapeutic_area="", et="ta_wrong")
j("D1197")
j("D1198", "corrected", stage_at_deal="", therapeutic_area="oncology", et="cvr_in_price", note="$1.5bn 'up to' includes CVR; Poseida CAR-T was clinical")
j("D1238", "dropped", dup="D0993", et="received_milestone_as_potential")
j("D1269", "dropped", dup="D1277", et="cost_as_milestone")
j("D1277", "corrected", stage_at_deal="", therapeutic_area="immunology", et="stage_wrong")
j("D1280", "corrected", upfront_usd_m=500.0, equity_usd_m=70.0, milestones_usd_m=700.0, total_potential_usd_m=1200.0, stage_at_deal="marketed",
  et="equity_in_upfront", note="Novavax deck: ~$570m = $500m upfront + $70m equity; date is the deck, deal was Q2 2024")
j("D1307", "dropped", dup="D1280", et="duplicate")
j("D1282", "corrected", therapeutic_area="oncology", stage_at_deal="", et="ta_wrong", note="$47m is upfront plus near-term milestones")
j("D1296")
j("D1303", "dropped", dup="D1317", et="received_milestone_as_potential")
j("D1304", "dropped", dup="D1317", et="duplicate")
j("D1306", "dropped", dup="D0116", et="duplicate")
j("D1313", "corrected", total_potential_usd_m=160.0, acquirer_or_licensee="Kaken", role="junk", et="total_equals_milestones")
j("D1315")
j("D1325")
j("D1340", "corrected", upfront_usd_m=30.0, milestones_usd_m=560.0, total_potential_usd_m=590.0, stage_at_deal="Ph3", role="swapped",
  acquirer_or_licensee="Amicus", target_or_licensor="Dimerix", et="aud_as_usd",
  note="row took AU$48m and AU$892m; USD terms are $30m upfront and $560m milestones")
j("D1333", "dropped", dup="D1340", et="duplicate")
j("D1342", "dropped", et="not_a_deal", note="SPAC business combination equity value")
j("D1345", "dropped", et="financing", note="Jade merger financing $334.2m")
j("D1355", acquirer_or_licensee="Sanofi", role="junk")
j("D1357")
j("D1358", "corrected", target_or_licensor="Genrix Bio", role="junk")
j("D1361", note="$795m at $8.50/share; excludes CVR")
j("D1368", "corrected", total_potential_usd_m=4045.0, note="$45m upfront + $80m warrants; milestones exceed $4bn", upfront_usd_m=45.0, et="warrant_in_upfront")
j("D1413", "dropped", dup="D1368", et="warrant_as_total")
j("D1373", "corrected", upfront_usd_m=7.5, milestones_usd_m=None, total_potential_usd_m=None, et="received_milestone_as_potential",
  note="$7.5m upfront; $12.5m is a milestone received")
j("D1390", "corrected", upfront_usd_m=303.0, total_potential_usd_m=303.0, et="cvr_in_price", note="$303m equity at closing; $360m with CVR")
j("D1409", "dropped", et="not_a_deal", note="AnaptysBio cash runway slide (GSK Jemperli milestone)")
j("D1423", "dropped", et="not_a_deal", note="AnaptysBio cash runway slide")
j("D1437", "dropped", et="not_a_deal", note="AnaptysBio cash runway slide")
j("D1418")
j("D1433", "corrected", stage_at_deal="Ph2", acquirer_or_licensee="Dynavax", role="junk", et="stage_wrong", note="post-Phase 2b program; not marketed")
j("D1436", "corrected", role="swapped", acquirer_or_licensee="Lyell", target_or_licensor="ImmPACT/ICT", et="role_swapped", note="ICT receives $40m from Lyell")
j("D1438", "corrected", upfront_usd_m=None, milestones_usd_m=82.0, total_potential_usd_m=82.0, stage_at_deal="", et="milestones_as_upfront")
j("D1440", note="$285m includes CVR")
j("D1452", "corrected", total_potential_usd_m=497.5, et="total_equals_milestones", note="$7m + $3m upfront + milestones")
j("D1533", "corrected", note="$3.5m cash; $7.0m incl JV shares")
j("D1542", "corrected", upfront_usd_m=3.5, et="equity_in_upfront", note="$3.5m cash + $3.5m in-kind equity")
j("D1545", "corrected", therapeutic_area="oncology", acquirer_or_licensee="Merck", target_or_licensor="Terns", role="blank_filled", et="ta_wrong")
j("D1547")
j("D1548")
j("D1565", "corrected", deal_type="acquisition", acquirer_or_licensee="", target_or_licensor="Nuvalent", role="junk", et="merger_as_license",
  note="GBP 8.0bn converted in source")
j("D1570", "dropped", et="financing", note="financing proceeds used for an acquisition")
j("D1580", "corrected", deal_type="acquisition", acquirer_or_licensee="", role="junk", et="merger_as_license", note="$2.8bn upfront equity + $1.0bn CVR")
j("D1584", "corrected", stage_at_deal="", et="stage_wrong")
j("D1585", note="'up to $8.0bn' includes CVR")
j("D1586", "corrected", role="swapped", acquirer_or_licensee="Pfizer", target_or_licensor="Innovent Biologics", therapeutic_area="", et="role_swapped")
j("D1587", "dropped", et="threshold_as_price", note="CVR sales-threshold table")
j("D1593", "dropped", dup="D0782", et="historical_deal_misdated")
j("D1597", "corrected", role="swapped", acquirer_or_licensee="Medicus Pharma", target_or_licensor="Pfizer", milestones_usd_m=None, total_potential_usd_m=None,
  et="role_swapped", note="Medicus paid Pfizer $12m")
j("D1606", "corrected", stage_at_deal="", therapeutic_area="", et="stage_wrong", note="Sanofi-Regeneron Sixth Amendment")
j("D1607", "dropped", dup="D1606", et="duplicate")
j("D1608")
j("D1610", "corrected", upfront_usd_m=65.0, equity_usd_m=25.0, milestones_usd_m=None, et="equity_in_upfront",
  note="$135m = $65m cash + $25m equity + $45m near-term milestones")
j("D1611", acquirer_or_licensee="Ono", role="blank_filled")

# acquisitions pass: every remaining unchecked acquisition row (quote-level)
for k in ["D0013", "D0144", "D0151", "D0194", "D0239", "D0356", "D0361", "D0412", "D0473", "D0485", "D0516", "D0553", "D0556",
          "D0574", "D0605", "D0735", "D0750", "D0770", "D0793", "D0803", "D0806", "D0843", "D0883", "D0909", "D1026", "D1052",
          "D1096", "D1161", "D1178", "D1323", "D1335", "D1346", "D1349", "D1387", "D1404", "D1408", "D1439", "D1460", "D1526",
          "D1540", "D1557", "D1571", "D1575", "D0134", "D0150"]:
    j(k)
for k in ["D0064", "D0801", "D0923", "D1312"]:
    j(k, note="value is 'up to' and includes CVR")
j("D0130", "corrected", stage_at_deal="", acquirer_or_licensee="Johnson & Johnson", target_or_licensor="Momenta", et="stage_wrong",
  note="nipocalimab was clinical; 'marketed' not supported")
j("D0133", "corrected", acquirer_or_licensee="Nestle Health Science", target_or_licensor="Aimmune", role="junk", note="parties parsed as 'S.A'/'Aim'")
j("D0141", "corrected", stage_at_deal="", acquirer_or_licensee="Gilead", target_or_licensor="Immunomedics", role="blank_filled",
  note="Trodelvy was approved in April 2020; Ph3 label not supported")
j("D0302", "corrected", stage_at_deal="", et="stage_wrong", note="Constellation had no marketed product")
j("D0486", "dropped", dup="D0485", et="duplicate", note="same Collegium-BDSI release; $650m not the equity value")
j("D0570", "dropped", et="not_biopharma", note="Meridian Bioscience diagnostics")
j("D0822", "dropped", dup="D0780", et="duplicate", note="Astellas-Iveric closing")
j("D1213", "dropped", dup="D1178", et="duplicate", note="Lumos closing")
j("D1366", "dropped", et="not_biopharma", note="Enzo Biochem life-science products")
j("D1456", acquirer_or_licensee="BioMarin", target_or_licensor="Amicus", role="blank_filled")
j("D1528", "dropped", dup="D1456", et="debt_payoff_as_price", note="$5,235m includes Amicus debt repayment; equity value $4.8bn in D1456")
j("D1599", "dropped", dup="D1571", et="duplicate", note="AbbVie-Apogee closing")
j("D0257", "dropped", et="not_a_deal", note="CVR agreement definition")
j("D0261", "corrected", deal_type="asset purchase", upfront_usd_m=12.5, milestones_usd_m=144.0, total_potential_usd_m=156.5,
  et="milestones_as_upfront", note="Journey-Dermira APA: $12.5m upfront + $144m milestones")
j("D0519", "dropped", et="not_biopharma", note="GeneDx diagnostics sale")
j("D0608", "corrected", total_potential_usd_m=350.0, et="wrong_numbers", note="$255m upfront + up to $95m contingent")
j("D0629", "corrected", upfront_usd_m=23.5, total_potential_usd_m=23.5, et="cvr_in_price", note="$23.5m at closing plus CVRs")
j("D0641", "dropped", et="not_a_deal", note="banker transaction fee")
j("D0648", "dropped", et="threshold_as_price", note="CVR net sales threshold")
j("D0786", "dropped", et="not_a_deal", note="option fee and expense reimbursement")
j("D0812", "corrected", upfront_usd_m=34.6, total_potential_usd_m=34.6, et="cvr_in_price", note="$34.6m at closing; ~$310m includes CVR")
j("D0832", "dropped", et="historical_deal_misdated", note="Nov 2021 merger consideration recapped in 2023")
j("D0837", "corrected", upfront_usd_m=109.0, total_potential_usd_m=109.0, et="cvr_in_price", note="$109m at closing; $213m with CVR")
j("D0876", "dropped", dup="D0838", et="cvr_in_price")
j("D0997", "corrected", total_potential_usd_m=None, note="2020 Asana merger: $20m cash + $30m preferred; $110m not supported")
j("D1036", "dropped", et="not_a_deal", note="CVR agreement boilerplate")
j("D1162", "dropped", et="not_a_deal", note="CVR agreement boilerplate")
j("D1063", "dropped", et="not_a_deal", note="fairness opinion net cash")
j("D1239", "dropped", et="not_a_deal", note="R&D expense paragraph")
j("D1278", "corrected", deal_type="acquisition", acquirer_or_licensee="Lantheus", target_or_licensor="Life Molecular Imaging", role="junk")
j("D1430", "dropped", dup="D1278", et="duplicate", note="Lantheus 10-K on the LMI acquisition")
j("D1297", "dropped", et="threshold_as_price", note="bluebird CVR sales threshold")
j("D1405", "dropped", et="threshold_as_price", note="DURECT CVR milestone aggregate")
j("D1426", "dropped", et="not_a_deal", note="unexecuted competing Novo proposal for Metsera")
j("D1432", "dropped", et="not_a_deal", note="unexecuted competing Novo proposal for Metsera")
j("D1427", "corrected", deal_type="license", acquirer_or_licensee="Lexicon", target_or_licensor="Prelude Therapeutics", role="junk",
  et="license_as_acquisition", note="$35m upfront + $25m equity license")
j("D1549", "corrected", deal_type="asset purchase", note="product portfolio sale to Cosette")
j("D1574", "dropped", et="not_a_deal", note="CVR draft note")
j("D1603", "dropped", et="threshold_as_price", note="CVR aggregate")
