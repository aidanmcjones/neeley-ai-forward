"""The case appendix as data: shortlist companies, starter threads, products and the rivals listed for each.

Source: docs/case/fine_print_case.pdf, "Appendix: Company Shortlist & Competitive Sets" (page 5).
Drug keys match the `drug` column of the citation index (lower case, hyphenated, e.g. "darzalex-faspro").
Maker tickers match docs.ticker in the index. Boehringer is "BOEHRINGER", Roche is "ROCHE", ViiV is reported by GSK.
"""

SHORTLIST = ["MRK", "BMY", "PFE", "LLY", "NVO", "ABBV", "JNJ", "AZN", "AMGN", "GILD"]

COMPANY_NAMES = {
    "MRK": "Merck", "BMY": "Bristol Myers Squibb", "PFE": "Pfizer", "LLY": "Eli Lilly", "NVO": "Novo Nordisk",
    "ABBV": "AbbVie", "JNJ": "Johnson & Johnson", "AZN": "AstraZeneca", "AMGN": "Amgen", "GILD": "Gilead",
    "NVS": "Novartis", "ROCHE": "Roche", "BOEHRINGER": "Boehringer Ingelheim", "BBIO": "BridgeBio", "ALNY": "Alnylam",
    "TAK": "Takeda", "SNY": "Sanofi", "REGN": "Regeneron", "GSK": "GSK (ViiV Healthcare)",
}

# Foreign filers file a 20-F (or, for Roche and Boehringer, an annual report with no SEC form).
FOREIGN_FILERS = {"NVO", "AZN", "NVS", "TAK", "SNY", "GSK", "ROCHE", "BOEHRINGER"}

STARTER_THREADS = {
    "MRK": "Keytruda's 2028 patent expiry; Januvia and Janumet lost U.S. exclusivity in 2026 and now face generics and a Medicare negotiated price.",
    "BMY": "Eliquis and Opdivo both lose U.S. exclusivity in 2028, putting a large share of revenue at risk.",
    "PFE": "Ibrance faces generic pressure from 2027 while the company rebuilds its growth story.",
    "LLY": "Mounjaro and Zepbound lead the obesity market, but price cuts and the race for a pill are reshaping it; Trulicity loses exclusivity in 2027.",
    "NVO": "Medicare's negotiated price for semaglutide takes effect January 2027, about 71% below the 2025 list price.",
    "ABBV": "Life after Humira: how fast Skyrizi and Rinvoq are filling the revenue gap.",
    "JNJ": "Stelara biosimilar erosion, Medicare drug-price negotiation, and the shift toward newer immunology and cancer drugs.",
    "AZN": "Cancer-drug growth, near-term exclusivity losses (generic Farxiga was approved in 2026), and exposure to U.S. pricing politics as a UK-based company.",
    "AMGN": "Enbrel and Repatha lose U.S. exclusivity around 2029 while Amgen bets on obesity drugs.",
    "GILD": "A dominant HIV franchise, and how long that dominance can hold.",
}

# {ticker: {product_key: [(rival_key, maker_ticker, note), ...]}}
# A product_key that joins two drugs with "/" (e.g. "skyrizi/rinvoq") is one competitive set shared by both.
COMPETITIVE_SETS = {
    "MRK": {
        "keytruda": [("opdivo", "BMY", ""), ("imfinzi", "AZN", ""), ("tecentriq", "ROCHE", "")],
        "januvia": [("sitagliptin", "GENERIC", "generic sitagliptin"), ("ozempic", "NVO", ""), ("jardiance", "BOEHRINGER", "Boehringer Ingelheim/Lilly")],
    },
    "BMY": {
        "eliquis": [("xarelto", "JNJ", "")],
        "opdivo": [("keytruda", "MRK", ""), ("tecentriq", "ROCHE", "")],
    },
    "PFE": {
        "ibrance": [("verzenio", "LLY", ""), ("kisqali", "NVS", "")],
        "vyndaqel": [("attruby", "BBIO", ""), ("amvuttra", "ALNY", "")],
    },
    "LLY": {
        "mounjaro/zepbound": [("ozempic", "NVO", ""), ("wegovy", "NVO", "injection and the Wegovy pill")],
        "trulicity": [("ozempic", "NVO", ""), ("wegovy", "NVO", "")],
    },
    "NVO": {
        "ozempic/wegovy": [("mounjaro", "LLY", ""), ("zepbound", "LLY", ""), ("foundayo", "LLY", "oral GLP-1 pill")],
    },
    "ABBV": {
        "skyrizi/rinvoq": [("tremfya", "JNJ", ""), ("stelara", "JNJ", ""), ("cosentyx", "NVS", ""), ("entyvio", "TAK", ""),
                           ("amjevita", "AMGN", "Humira biosimilar")],
    },
    "JNJ": {
        "stelara/tremfya": [("skyrizi", "ABBV", ""), ("rinvoq", "ABBV", ""), ("wezlana", "AMGN", "Stelara biosimilar")],
        "darzalex": [("sarclisa", "SNY", "")],
    },
    "AZN": {
        "tagrisso": [("rybrevant", "JNJ", "with Lazcluze"), ("lazcluze", "JNJ", "")],
        "farxiga": [("dapagliflozin", "GENERIC", "generic dapagliflozin"), ("jardiance", "BOEHRINGER", "Boehringer Ingelheim/Lilly")],
        "imfinzi": [("keytruda", "MRK", "")],
    },
    "AMGN": {
        "repatha": [("praluent", "REGN", ""), ("leqvio", "NVS", ""), ("lipfendra", "MRK", "first oral PCSK9")],
        "enbrel": [("skyrizi", "ABBV", ""), ("rinvoq", "ABBV", ""), ("humira", "ABBV", "biosimilars; Amjevita is Amgen's own")],
    },
    "GILD": {
        "biktarvy": [("dovato", "GSK", "ViiV"), ("cabenuva", "GSK", "ViiV")],
        "yeztugo": [("apretude", "GSK", "ViiV")],
    },
}

# Background only per the case: MariTide cannot be the Part 1 product; incumbents it would face.
BACKGROUND_ONLY = {"AMGN": {"maritide": [("zepbound", "LLY", ""), ("wegovy", "NVO", "")]}}


def products(ticker):
    """Product keys for a shortlist company, split on '/'."""
    out = []
    for k in COMPETITIVE_SETS.get(ticker.upper(), {}):
        out += k.split("/")
    return out


def rivals(ticker, product=None):
    """[(rival_key, maker_ticker, note)] for one product (or all of the company's products)."""
    sets = COMPETITIVE_SETS.get(ticker.upper(), {})
    out = []
    for k, rv in sets.items():
        if product is None or product.lower() in k.split("/"):
            out += rv
    return out


def all_drugs():
    """Every product and rival key named in the appendix, excluding the generic placeholders."""
    keys = set()
    for sets in COMPETITIVE_SETS.values():
        for k, rv in sets.items():
            keys.update(k.split("/"))
            keys.update(r for r, maker, _ in rv if maker != "GENERIC")
    return sorted(keys)


def maker_tickers():
    """Every rival maker named in the appendix (no shortlist companies, no generics)."""
    return sorted({m for sets in COMPETITIVE_SETS.values() for rv in sets.values() for _, m, _ in rv if m != "GENERIC"})
