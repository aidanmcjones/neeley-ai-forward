"""Status whitelist for facts rows in citations.sqlite (review C4).

facts.verify_status is free text written by many scrapers (35+ distinct values in the shared index: verified 13,477,
no_verified_copy 47,883, unverified_onboard 8,741, unchecked 975, no 5,530, dropped 624, ...). Before this module the
quant data layer treated every value except dropped / False / no as "exact" with grade 1.0, so a row nobody checked
was graded like a quote found on the page. The rule is now a whitelist, fail closed:

  fact_status_grade(verify_status) -> (grade, label)
    VERIFIED_STATUSES        -> (1.0, "verified")       exact-equivalent: a person or a script compared the row with
                                                         its source page and it matched (or was corrected to match)
    MACHINE_STATUSES         -> (0.6, "machine data")   licensed or machine feeds with no page copy (I/B/E/S, prices);
                                                         number_match-equivalent ONLY when the value is re-read from
                                                         the table row itself, else unverified
    everything else          -> (0.0, "unverified")     including unverified_onboard and unchecked, flagged
                                                         "not checked"; unknown values land here too

  fact_citation_status(verify_status, reread_ok) -> Citation verification status
    verified  + reread_ok -> "exact"
    machine   + reread_ok -> "number_match"
    otherwise             -> "unverified"
  reread_ok means the caller re-read the value from the facts row and it equals the number being cited. With no value
  to compare (value None) there is no re-read, so the status is unverified.

The quant data layer calls this from agent.needle.quant.data.fact_citation (see docs/gate_wiring.md).
"""

VERIFIED_STATUSES = ("verified", "corrected", "fixed", "yes", "true", "match", "matches page")
# api_exact_distinct: an exact distinct count from a live API query (Open Payments physicians), no page copy
MACHINE_STATUSES = ("no_verified_copy", "api_exact_distinct")
NOT_CHECKED = ("unverified_onboard", "unchecked")
# Table-scoped verified statuses, from the table's own NOTES.md: "pass" means something only where the scraper
# defines it (pipeline/NOTES.md: loe_calendar "stated dates re-found in the FY2025 10-K with page (tenk_page)";
# target_profiles "recomputed from SEC companyfacts; use the verified values"). Elsewhere "pass" stays unverified.
TABLE_VERIFIED = {"pipeline/loe_calendar.csv": ("pass",), "pipeline/target_profiles.csv": ("pass", "recomputed")}


def _key(verify_status):
    if verify_status is True:
        return "true"
    return str(verify_status if verify_status is not None else "").strip().lower()


def fact_status_grade(verify_status, table=None):
    """(grade 0..1, label) for a facts.verify_status value. Unknown values are unverified (fail closed). `table`
    enables that table's own verified statuses (TABLE_VERIFIED)."""
    k = _key(verify_status)
    if k in VERIFIED_STATUSES or k in TABLE_VERIFIED.get(table or "", ()):
        return 1.0, "verified"
    if k in MACHINE_STATUSES:
        return 0.6, "machine data"
    if k in NOT_CHECKED:
        return 0.0, "unverified (not checked)"
    return 0.0, "unverified" + (f" (status {verify_status!r})" if k else " (no status)")


def fact_citation_status(verify_status, reread_ok, table=None):
    """Citation status for a facts-row citation: exact / number_match / unverified (see the module docstring)."""
    if not reread_ok:
        return "unverified"
    grade, label = fact_status_grade(verify_status, table)
    if label == "verified":
        return "exact"
    if label == "machine data":
        return "number_match"
    return "unverified"


# ------------------------------------------------------------------ facts.locator (scraper column, optional)
# The scraper's facts table carries a `locator` column (older sqlite files do not):
#   doc_id#p<page_no>           the row's page is known: a normal page Citation (verify ladder, deep link, viewer link);
#                               agent.moat.cite.cite() and get_page() take the same id
#   fact:<table>#<row_key>      no page: the facts-row citation stays, with the row key in the footnote
#   url:<dataset URL>#<row_key> an API-sourced row: a machine-data citation whose deep link is that URL
# apply_locator(row, base, row_json, index) is called by the quant data layer (agent.needle.quant.data) on the
# facts-row Citation it built with the status whitelist above; with no locator column the citation is unchanged,
# except for the label-section rule below.
#
# Page citation rules (fail closed): the quote must be verbatim on that page, so it is taken, in order, from the row's
# own quote field (QUOTE_FIELDS); for rows that name an indication or a label item (MATCH_FIELDS), from the one line of
# the page that shares at least MIN_SHARED_TERMS terms with the row (a row matched to a line, never a paraphrase).
# A bare value is never used as the quote: "66" found somewhere on a page is not evidence that the page states the
# row's fact (review verify2). Each candidate
# runs through agent.needle.cite.verify.verify; the first that passes is returned. When none passes, the facts-row
# citation is kept (whitelist status) with a note, the page in its location and a viewer link to the locator page.
#
# Label-section rule: a row whose source_row is data/corpus/drugs/<drug>/<file>#<section heading> (epi/indication_map.csv)
# is resolved to the page of document drug:<drug>:<file> whose printed heading equals that section, when the locator
# is not already a page. This is the same page the locator would name; it is used because the shared index still
# gives these rows a url: locator.
#
# url: rows: the deep link is the URL and the citation is labelled machine data, but the status still follows the
# whitelist (fail closed): verified statuses stay exact, machine statuses are number_match, and a row nobody checked
# (unchecked, unverified_onboard, unknown) stays unverified. A URL is where the row came from, not a check of it.

import re as _re

QUOTE_FIELDS = ("quote", "evidence_quote", "verbatim", "snippet", "text_quote")
MATCH_FIELDS = ("indication", "sub_indication")
MIN_SHARED_TERMS = 2
_PAGE_LOC = _re.compile(r"^(?P<doc>.+)#p(?P<page>\d+)$")
_LABEL_SRC = _re.compile(r"^data/corpus/drugs/(?P<drug>[^/]+)/(?P<file>[^#]+)#(?P<heading>[^|]+)")
_STOP = {"the", "and", "with", "for", "who", "are", "from", "that", "this", "into", "use", "adults", "adult",
         "patients", "patient", "years", "older", "aged", "least", "one", "treatment", "indicated", "combination"}


def is_bulk_url(url):
    """A dataset API endpoint or a bulk download (zip, csv, json): opening it does not show the cited row (review
    verify2: the CMS Part D API link did not show the cited 250 prescribers; the SPUF zip is 2.5 GB)."""
    u = str(url or "").lower().split("?")[0]
    return "/api/" in u or "/data-api/" in u or u.endswith((".zip", ".csv", ".json", ".gz", ".xlsx", ".txt"))


def row_locator(r):
    """facts.locator for a sqlite Row or dict, '' when the column is absent (older sqlite) or empty."""
    try:
        keys = r.keys()
    except AttributeError:
        keys = list(r) if isinstance(r, dict) else []
    return str(r["locator"] or "").strip() if "locator" in keys else ""


def parse_locator(loc):
    """{"kind": page | fact | url, ...} or None. page: doc_id, page; fact: table, row_key; url: url, row_key."""
    loc = str(loc or "").strip()
    if not loc:
        return None
    if loc.startswith("fact:"):
        table, _, rk = loc[5:].rpartition("#")
        return {"kind": "fact", "table": table or loc[5:], "row_key": rk if table else ""}
    if loc.startswith("url:"):
        url, sep, rk = loc[4:].rpartition("#")
        if not sep or not rk.isdigit():
            url, rk = loc[4:], ""
        return {"kind": "url", "url": url, "row_key": rk}
    m = _PAGE_LOC.match(loc)
    if m:
        return {"kind": "page", "doc_id": m.group("doc"), "page": int(m.group("page"))}
    return None


def _terms(s):
    out = set()
    for w in _re.findall(r"[a-z0-9]+", str(s or "").lower()):
        if (len(w) >= 3 or any(ch.isdigit() for ch in w) and len(w) >= 2) and w not in _STOP:
            out.add(w[:6])
    return out


def _lines(text):
    for raw in (text or "").splitlines():
        s = raw.strip()
        s = _re.sub(r"^(?:[-*]\s*)?(?:[•o]\s+)?", "", s).strip()
        if len(s) >= 20 and not s.startswith("#"):
            yield s


def match_line(text, row_json):
    """(line, shared terms) for the page line that shares the most MATCH_FIELDS terms with the row, or (None, 0)."""
    want = set()
    for k in MATCH_FIELDS:
        want |= _terms((row_json or {}).get(k))
    if not want:
        return None, 0
    best, n = None, 0
    for ln in _lines(text):
        k = len(want & _terms(ln))
        if k > n:
            best, n = ln, k
    return (best, n) if n >= MIN_SHARED_TERMS else (None, n)


def _row_terms(row_json):
    out = set()
    for k in MATCH_FIELDS:
        out |= _terms((row_json or {}).get(k))
    return out


def label_page(row, index):
    """(doc_id, page) for a label-section source_row (see the module notes), or None."""
    try:
        src = str(row["source_row"] or "")
    except (KeyError, IndexError):
        return None
    m = _LABEL_SRC.match(src)
    if not m or index is None:
        return None
    doc = f"drug:{m.group('drug')}:{m.group('file')}"
    try:
        rec = index.resolve(doc)
        if rec is None:
            return None
        heading = m.group("heading").strip().lower()
        for n, (folio, _text) in sorted(index.pages(rec.canonical_id).items()):
            if str(folio or "").strip().lower() == heading:
                return rec.canonical_id, n
    except Exception:
        return None
    return None


def _page_citation(base, doc_id, page, row, row_json, index, how):
    """A verified page Citation from the first quote candidate that passes, else None (with the reasons)."""
    from dataclasses import replace
    from .locator import Citation, Verification
    from .verify import verify
    cands = []
    for k in QUOTE_FIELDS:
        q = str((row_json or {}).get(k) or "").strip()
        if q:
            cands.append((q, base.claim_type, base.value, base.unit))
    why = []
    try:
        got = index.get_page(doc_id, page) if index is not None else None
    except Exception:
        got = None
    if got is not None:
        ln, _n = match_line(got[2], row_json)
        if ln:
            cands.append((ln, "quote", None, ""))
        elif how.startswith("source_row label section") and got[1] and _terms(got[1]) & _row_terms(row_json):
            # the row names this subsection ("1.1 Melanoma"): the first line under that heading that names the row's
            # indication is the verbatim evidence ("KEYTRUDA is indicated for ... melanoma.")
            want = _row_terms(row_json)
            ln = next((x for x in _lines(got[2]) if want & _terms(x)), None)
            if ln:
                cands.append((ln, "quote", None, ""))
    for q, ct, val, unit in cands:
        try:
            c = verify(Citation(canonical_id=doc_id, page=page, quote=q, claim_type=ct or "quote", value=val,
                                unit=unit or ""), index)
        except Exception as e:                                   # fail closed: try the next candidate
            why.append(f"verify error: {e}")
            continue
        if c.verification.ok:
            note = (f"facts row {row['row_key']} ({row['verify_status']}); page from {how}"
                    + (f"; {c.verification.detail}" if c.verification.detail else ""))
            return replace(c, verification=Verification(c.verification.status, c.verification.score,
                                                        c.verification.checked_at, note),
                           confidence_note=note, license=base.license or c.license), why
        why.append(f"{q[:40]!r}: {c.verification.detail or c.verification.status}")
    return None, why


def apply_locator(row, base, row_json=None, index=None, value_mismatch=False):
    """The facts-row Citation `base` re-pointed by facts.locator (see the notes above). `row` is the facts row
    (sqlite Row or dict), `row_json` its parsed row_json, `index` a DocIndex (agent.needle.cite.index.load_index).
    value_mismatch: the caller's cited value differs from the row; the citation is then never upgraded to a page."""
    from dataclasses import replace
    from .deeplink import build_viewer_link
    loc = parse_locator(row_locator(row))
    if value_mismatch:
        return base
    page_ref = None
    if loc and loc["kind"] == "page":
        page_ref = (loc["doc_id"], loc["page"], f"facts.locator {row_locator(row)}")
    else:
        lp = label_page(row, index)
        if lp:
            page_ref = (lp[0], lp[1], f"source_row label section ({lp[0]} page {lp[1]})")
    if page_ref is not None and index is not None:
        cit, why = _page_citation(base, page_ref[0], page_ref[1], row, row_json, index, page_ref[2])
        if cit is not None:
            return cit
        note = (base.confidence_note + "; " if base.confidence_note else "") + \
            f"{page_ref[2]}: no quote verified on page {page_ref[1]} ({'; '.join(why[:3]) or 'no candidate'})"
        out = replace(base, confidence_note=note, verification=replace(base.verification, detail=note),
                      location=f"{base.location or 'row ' + str(row['row_key'])}; {page_ref[0]} page {page_ref[1]}")
        try:
            out.viewer_link = build_viewer_link(replace(out, canonical_id=page_ref[0], page=page_ref[1], quote=""))
        except Exception:
            pass
        return out
    if loc and loc["kind"] == "url":
        url = loc["url"]
        status = base.verification.status
        bulk = is_bulk_url(url)
        note = (base.confidence_note + "; " if base.confidence_note else "") + \
            f"machine data: API row {loc['row_key'] or row['row_key']} at {url} (no page copy)" + \
            ("; the URL returns the whole dataset or a bulk file, so the row key is the citation (no deep link)"
             if bulk else "")
        return replace(base, deep_link="" if bulk else url, source_url=url, page_scheme="none", raw_doc_type="machine_data",
                       doc_type=base.doc_type or "machine_data", confidence_note=note,
                       verification=replace(base.verification, status=status, detail=note))
    if loc and loc["kind"] == "fact":
        rk = row["row_key"]
        return replace(base, location=f"row {rk}", quote=base.quote if rk in (base.quote or "") else f"{rk} {base.quote}")
    return base
