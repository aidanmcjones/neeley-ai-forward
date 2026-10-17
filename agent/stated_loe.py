"""Company-stated loss-of-exclusivity (LOE) dates, quoted from each drug maker's own latest 10-K.

FDA Orange Book patent dates mislead (settlements set the real generic entry date), so the demo shows the date the
company itself states, next to the FDA data, with an exact quote and a citation.

Row schema (one row per company x product x basis):
  cik, company, product, ingredient, us_loe, eu_loe, japan_loe (each as written, null if not stated),
  basis, quote (exact text from the filing, max 400 chars), accession, form, period, section, source_url

Storage: R2 key derived/company_stated_loe.jsonl (local copy agent/cache/company_stated_loe.jsonl, the demo source).

  load(ciks=None)       rows from R2 (falls back to the local copy)
  locate_sections(cik)  patent / exclusivity / litigation passages of the company's latest 10-K, as offsets
  extract(cik)          rebuild one company's rows with Claude over only those passages (needs ANTHROPIC_API_KEY)

Usage:
  python -m agent.stated_loe --ciks 310158,14272            # print rows from the store
  python -m agent.stated_loe --ciks 310158 --extract        # re-extract with Claude and merge into the store
  python -m agent.stated_loe --push                         # upload the local copy to R2
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from agent.tenk import Store, load_text

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / "agent" / "cache" / "company_stated_loe.jsonl"
R2_KEY = "derived/company_stated_loe.jsonl"
INDEX_KEY = "index/tenk_index.jsonl"

FIELDS = ["cik", "company", "product", "ingredient", "us_loe", "eu_loe", "japan_loe", "basis", "quote",
          "accession", "form", "period", "section", "source_url"]

# Headings / phrases that mark the patent and exclusivity discussion (Item 1 / MD&A)
PATENT_PAT = re.compile(
    r"(estimated minimum market exclusivity|Patents, Trademarks|Patents and Other Intellectual Property|"
    r"Intellectual Property (Rights|Protection)|Our Intellectual Property Portfolio|Market Exclusivity|"
    r"basic product patent|Year of Expiration|Estimated Expiry Date|Patent Expiration|loss of exclusivity)", re.I)
# Phrases that mark settlement-set or expected generic / biosimilar entry in litigation and contingency text
LITIGATION_PAT = re.compile(
    r"(no generic entry|generic entry (is )?expected|permitt?ing their launch|permitted to launch|"
    r"precluded from launching|settlement (and license )?agreements?|settled .{0,60}generic|"
    r"not (be )?permitted to launch|biosimilar.{0,40}launch)", re.I)

WINDOW = 3500        # characters kept around each litigation hit
MAX_CHARS = 120_000  # cap on text sent to the model per company


# ---------------------------------------------------------------- store

def _store_rows():
    data = Store().get(R2_KEY)
    if data:
        return [json.loads(l) for l in data.decode().splitlines() if l.strip()]
    if LOCAL.exists():
        return [json.loads(l) for l in LOCAL.read_text().splitlines() if l.strip()]
    return []


def load(ciks=None):
    """All rows (or only those for the given CIKs) from R2, falling back to the local copy."""
    rows = _store_rows()
    if ciks:
        want = {int(c) for c in ciks}
        rows = [r for r in rows if int(r["cik"]) in want]
    return rows


def save(rows, push=True):
    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    LOCAL.parent.mkdir(parents=True, exist_ok=True)
    LOCAL.write_text(body)
    if push:
        Store().put(R2_KEY, body.encode(), "application/x-ndjson")


# ---------------------------------------------------------------- locating text

def latest_10k(cik):
    """Index row of the company's most recent 10-K (not 10-K/A)."""
    data = Store().get(INDEX_KEY)
    if not data:
        raise RuntimeError("index/tenk_index.jsonl not found in the store")
    best = None
    for line in data.decode().splitlines():
        r = json.loads(line)
        if int(r["cik"]) == int(cik) and r["form"] == "10-K" and (best is None or r["period"] > best["period"]):
            best = r
    if not best:
        raise LookupError(f"no 10-K indexed for CIK {cik}")
    return best


def _merge(spans, gap=500):
    spans = sorted(spans)
    out = []
    for a, b in spans:
        if out and a <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def locate_sections(cik, row=None, text=None):
    """Patent / exclusivity passages (Item 1 and Item 7) and settlement / litigation passages (Item 3, Item 8).

    Returns {"row": index row, "patent": [(start, end), ...], "litigation": [(start, end), ...]} with offsets into
    the full filing text (agent.tenk.load_text). Only these passages need to go to the model.
    """
    row = row or latest_10k(cik)
    text = text if text is not None else load_text(row)
    sec = row.get("sections", {})

    def span(item):
        return tuple(sec[item]) if item in sec else None

    patent = []
    for item in ("1", "7"):
        s = span(item)
        if not s:
            continue
        hits = [m.start() for m in PATENT_PAT.finditer(text, s[0], s[1])]
        # a dense cluster of hits marks the IP section; each hit pulls in the text around it
        for h in hits:
            patent.append((max(s[0], h - 600), min(s[1], h + 2500)))
    litigation = []
    for item in ("1", "1A", "3", "7", "8"):
        s = span(item)
        if not s:
            continue
        for m in LITIGATION_PAT.finditer(text, s[0], s[1]):
            litigation.append((max(s[0], m.start() - WINDOW // 2), min(s[1], m.start() + WINDOW // 2)))
    return {"row": row, "patent": [tuple(x) for x in _merge(patent)], "litigation": [tuple(x) for x in _merge(litigation)]}


def passages(loc, text):
    """Concatenate located passages (patent first) up to MAX_CHARS, labelled with their offsets."""
    parts, used = [], 0
    for kind in ("patent", "litigation"):
        for a, b in loc[kind]:
            chunk = text[a:b]
            if used + len(chunk) > MAX_CHARS:
                chunk = chunk[: max(0, MAX_CHARS - used)]
            if chunk:
                parts.append(f"[{kind} passage, offsets {a}-{b}]\n{chunk}")
                used += len(chunk)
            if used >= MAX_CHARS:
                return "\n\n".join(parts)
    return "\n\n".join(parts)


# ---------------------------------------------------------------- extraction with Claude

PROMPT = """You are reading passages from {company}'s latest 10-K (period {period}). Extract the company's OWN stated
loss-of-exclusivity (LOE) dates for every product named in a patent / exclusivity table, and every generic or
biosimilar entry date set by a settlement or license agreement in the litigation text.

Return ONLY a JSON array. One object per product and basis, with exactly these keys:
  product      brand name as written
  ingredient   active ingredient if stated, else null
  us_loe       US date exactly as written (for example "2028", "April 2028", "2031 (with pediatric exclusivity)"), else null
  eu_loe       EU date as written, else null
  japan_loe    Japan date as written, else null
  basis        short label, for example "estimated minimum market exclusivity", "compound patent expiry incl. PTE",
               "settlement permits generic entry", "regulatory data protection", "generics have entered the market"
  quote        the EXACT sentence or table row text copied character for character from the passages (max 400 chars)
  section      where it appears, for example "Item 1 Intellectual Property" or "Item 8 Note 20 Legal Proceedings"

Rules:
- Never use outside knowledge. If the passages do not state a date, use null. Never infer or round a date.
- The quote must be a verbatim substring of the passages. Do not paraphrase.
- When a settlement sets a generic entry date different from the patent date, emit two rows (one per basis).
- Table cells flattened by HTML conversion: read columns in order; if a column cannot be assigned, use null.
"""


def _parse_json(text):
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        raise ValueError("model returned no JSON array")
    return json.loads(m.group(0))


def _norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def extract(cik, merge=False):
    """Rebuild one company's rows from its latest 10-K. Requires ANTHROPIC_API_KEY.

    Each returned quote is checked as a verbatim substring of the filing text; rows that fail are dropped.
    With merge=True the company's rows in the store are replaced and the store is re-pushed.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set; extract() needs it. load() serves the cached rows.")
    from agent.llm import call

    row = latest_10k(cik)
    text = load_text(row)
    loc = locate_sections(cik, row, text)
    body = passages(loc, text)
    prompt = PROMPT.format(company=row["company"], period=row["period"])
    out = call(prompt, context={"10-K passages": body}, effort="high")
    flat = _norm(text)
    rows = []
    for r in _parse_json(out["text"]):
        quote = _norm(r.get("quote"))
        if not quote or quote[:400] not in flat:
            continue  # unverifiable quote: drop
        rows.append({
            "cik": int(cik), "company": row["company"], "product": r.get("product"), "ingredient": r.get("ingredient"),
            "us_loe": r.get("us_loe"), "eu_loe": r.get("eu_loe"), "japan_loe": r.get("japan_loe"),
            "basis": r.get("basis"), "quote": quote[:400], "accession": row["accession"], "form": row["form"],
            "period": row["period"], "section": r.get("section"), "source_url": row.get("source_url"),
        })
    if merge:
        keep = [x for x in _store_rows() if int(x["cik"]) != int(cik)]
        save(keep + rows)
    return rows


# ---------------------------------------------------------------- CLI

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ciks", help="comma-separated CIKs (default: all rows)")
    p.add_argument("--extract", action="store_true", help="re-extract these CIKs with Claude and merge into the store")
    p.add_argument("--locate", action="store_true", help="print located passage offsets for these CIKs")
    p.add_argument("--push", action="store_true", help="upload the local copy to R2")
    a = p.parse_args()
    ciks = [int(c) for c in a.ciks.split(",")] if a.ciks else None

    if a.push:
        rows = [json.loads(l) for l in LOCAL.read_text().splitlines() if l.strip()]
        save(rows)
        print(f"pushed {len(rows)} rows to {R2_KEY}")
        return
    if a.locate:
        for c in ciks or []:
            loc = locate_sections(c)
            print(c, loc["row"]["company"], "patent", loc["patent"], "litigation", len(loc["litigation"]), "passages")
        return
    if a.extract:
        if not ciks:
            sys.exit("--extract needs --ciks")
        for c in ciks:
            rows = extract(c, merge=True)
            print(f"{c}: {len(rows)} verified rows")
        return
    rows = load(ciks)
    for r in rows:
        print(f"{r['company'][:22]:22} {str(r['product'])[:34]:34} US {str(r['us_loe'])[:30]:30} | {r['basis'][:60]}")
    print(f"{len(rows)} rows")


if __name__ == "__main__":
    main()
