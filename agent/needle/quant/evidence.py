"""Evidence E and the deterministic confidence label (docs/quant_model.md sections 4.5 and 4.7).

E_f = min over key claims j of [ 1 - prod_{i in cites(j)} (1 - g_i) ]          (section 4.5)

Citations come from agent.needle.cite (verified against citations.sqlite). The package's ladder statuses map to the
spec's grades as follows (Implementation notes in docs/quant_model.md record the mapping):
  exact, substring           -> verified_exact   g = 1.00
  fuzzy                      -> verified_fuzzy   g = 0.90
  number_match               -> g = 0.745 (the number is on the cited page but the quote did not verify; graded at
                                the entailed level because the spec has no rung for it)
  unverified                 -> unsupported      g = 0
Table and XBRL rows re-read by code carry status "exact" (spec: "Table rows from verified moat tables ... are
citations like any other: verified_exact when code re-reads the row value"). Derived numbers take the weakest
operand's grade (derived_code).
"""

from dataclasses import replace

from agent.needle.cite.index import load_index
from agent.needle.cite.locator import Citation
from agent.needle.cite.verify import verify as cite_verify
from agent.findings import _norm

from . import data
from . import weights as W

GRADE = {"exact": W.G_EXACT, "substring": W.G_EXACT, "fuzzy": W.G_FUZZY, "number_match": W.G_ENTAILED,
         "unverified": W.G_NONE}

OFFICIAL_RAW = {"annual_report", "quarterly_report", "cms_fact_sheet", "mfp_explanation", "fda_label",
                "fda_label_version", "drug_reference_data", "policy_8k"}


def grade(c):
    """g for one Citation (section 4.5 table). A derived citation carries its weakest operand's grade as its score."""
    if c.verification.status == "derived":
        return float(c.verification.score or 0.0)
    return GRADE.get(c.verification.status, 0.0)


def from_evidence(ev, index=None):
    """Engine Evidence -> verified Citation (spec 6.2 adapter). A missing page on a section-paged label is located by
    finding the quote among the document's pages; a wrong page is never corrected (the verifier reports it)."""
    idx = index or data.index()
    page = ev.page
    if page is None and ev.quote and idx.resolve(ev.doc_id) is not None:
        nq = _norm(ev.quote)
        for n, (_, text) in idx.pages(ev.doc_id).items():
            if nq and nq[:200] in _norm(text):
                page = n
                break
    c = Citation(canonical_id=ev.doc_id, page=page, quote=ev.quote or "", claim_type="quote", speaker=ev.speaker or "")
    return cite_verify(c, idx)


def noisy_or(grades):
    """1 - prod(1 - g_i): independent citations of one claim (section 4.5, inference: independence)."""
    out = 1.0
    for g in grades:
        out *= (1 - g)
    return 1 - out


def evidence_score(claims):
    """E = min over key claims of noisy-OR of that claim's citations. `claims` is a list of lists of Citations.
    Citations of one claim from the same document count once (same issuer and filing = one source)."""
    if not claims:
        return 0.0
    vals = []
    for cites in claims:
        best = {}
        for c in cites:
            best[c.canonical_id] = max(best.get(c.canonical_id, 0.0), grade(c))
        vals.append(noisy_or(best.values()) if best else 0.0)
    return min(vals)


def source_family(c):
    """Document family for n_ind (section 4.7): company filing, transcript, government agency, FDA label, table, ..."""
    raw = c.raw_doc_type or ""
    if raw in ("transcript", "transcript_source"):
        return f"transcript:{c.ticker}"
    if raw.startswith("cms") or raw.startswith("mfp") or c.canonical_id.startswith("policy_gov:"):
        return "government"
    if raw.startswith("fda_label") or c.canonical_id.startswith("drug:"):
        return f"fda_label:{c.canonical_id.split(':')[1] if ':' in c.canonical_id else ''}"
    if c.canonical_id.startswith("xbrl:") or c.canonical_id.startswith("tables/"):
        return f"table:{c.canonical_id}"
    return f"filing:{c.ticker}"


def n_independent(cites):
    """Number of independent sources among page citations (different issuers or document families)."""
    fams = {source_family(c) for c in cites if c.verification.ok and c.canonical_id not in ("derived",)
            and not c.canonical_id.startswith("xbrl:") and not c.canonical_id.startswith("tables/")}
    return len(fams)


def official_verbatim(c):
    """Quoted verbatim (exact or substring) from an official primary source: SEC filing, CMS, FDA, Orange/Purple Book."""
    return c.verification.status in ("exact", "substring") and (
        (c.raw_doc_type or "") in OFFICIAL_RAW or c.canonical_id.startswith("policy_gov:")
        or c.canonical_id.startswith("drug:"))


def confidence(E, n_ind, key_quoted_official, any_llm_or_entailed, diagnostic, contradicted, diagnostics_pass,
               trial_fails=False):
    """ICD 203 style label (section 4.7). Returns (label, reasons). Deterministic; the LLM never sets it."""
    reasons = []
    if trial_fails:
        return "LOW", ["courtroom trial ruled the finding fails (veto)"]
    if contradicted:
        return "LOW", ["a citation is contradicted"]
    high = [E >= W.E_HIGH, n_ind >= 2 or key_quoted_official, not any_llm_or_entailed, diagnostic, diagnostics_pass]
    names = [f"E {E:.3f} >= {W.E_HIGH}", "two independent sources or a verbatim official primary source",
             "no LLM-derived or entailed key claim", "diagnostic family", "mandatory diagnostics pass"]
    if all(high):
        return "HIGH", names
    reasons = [f"not HIGH: fails '{n}'" for n, ok in zip(names, high) if not ok]
    if E >= W.E_MED:
        return "MEDIUM", reasons
    return "LOW", reasons + [f"E {E:.3f} < {W.E_MED}"]
