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
MACHINE_STATUSES = ("no_verified_copy",)
NOT_CHECKED = ("unverified_onboard", "unchecked")


def _key(verify_status):
    if verify_status is True:
        return "true"
    return str(verify_status if verify_status is not None else "").strip().lower()


def fact_status_grade(verify_status):
    """(grade 0..1, label) for a facts.verify_status value. Unknown values are unverified (fail closed)."""
    k = _key(verify_status)
    if k in VERIFIED_STATUSES:
        return 1.0, "verified"
    if k in MACHINE_STATUSES:
        return 0.6, "machine data"
    if k in NOT_CHECKED:
        return 0.0, "unverified (not checked)"
    return 0.0, "unverified" + (f" (status {verify_status!r})" if k else " (no status)")


def fact_citation_status(verify_status, reread_ok):
    """Citation status for a facts-row citation: exact / number_match / unverified (see the module docstring)."""
    if not reread_ok:
        return "unverified"
    grade, label = fact_status_grade(verify_status)
    if label == "verified":
        return "exact"
    if label == "machine data":
        return "number_match"
    return "unverified"
