"""Extract deal rows from page-marked 8-K documents in data/moat/deals/ -> data/moat/scratch/deals_8k_rows.jsonl"""
import json, re, sys
from pathlib import Path
from agent.moat.deals_lib import *

OUTD = Path("data/moat/deals")
SKIP_TITLE = re.compile(r"financial results|first quarter|second quarter|third quarter|fourth quarter|full[- ]year|business update|"
                        r"quarter ended|corporate update|to present at|conference|investor day|public offering|offering of|pricing of|"
                        r"reverse stock|annual meeting|nasdaq|private placement|inducement", re.I)
DEAL_KW = re.compile(r"license|licens|collaborat|acquir|merger|asset purchase|option|royalt", re.I)


def window(q):
    q = q.strip()
    if len(q) <= 300:
        return q
    a = amounts(q)
    i = a[0][1] if a else 0
    lo = max(0, i - 150)
    return q[lo:lo + 300].strip()


def clean_name(n):
    n = re.sub(r"\s+\(.*", "", n.split("  ")[0]).strip()
    n = re.sub(r"\s*/[A-Za-z]{2,3}/?$", "", n)
    return n.title() if n.isupper() else n


def tok(n):
    w = re.sub(r"[^a-z0-9 ]", "", n.lower()).split()
    return w[0] if w else "zzzz"


def role(s, ft, ct):
    m = re.search(r"\b(will receive|is eligible to receive|are eligible to receive|is entitled to receive|eligible to receive|received|receives|will pay|has paid|paid|will make|to pay|pays|made)\b", s, re.I)
    if not m:
        return None
    subj = s[:m.start()].lower()
    fin = ft in subj or bool(re.search(r"\bwe\b|\bthe company\b|\bour\b", subj))
    cin = bool(ct) and ct in subj
    verb = m.group(1).lower()
    recv = "receiv" in verb or "entitled" in verb
    if fin == cin:
        return None
    if recv:
        return "filer_licensor" if fin else "filer_licensee"
    return "filer_licensee" if fin else "filer_licensor"


def process(path):
    raw = path.read_text()
    m = re.search(r"source: (\S+) .*?docs=(\S+) -->", raw)
    url = m.group(1) if m else ""
    mm = re.search(r"<!-- acc=(\S+) cik=(\d+) filer=(.*?) filed=(\S+) -->", raw)
    if not mm:
        return None
    acc, cik, filer, filed = mm.groups()
    filer = clean_name(filer)
    pages = re.split(r"\[\[page (\d+) \| printed ([^\]]+)\]\]", raw)
    body = ""
    pagemap = []  # (start offset, page, printed)
    for i in range(1, len(pages), 3):
        pagemap.append((len(body), pages[i], pages[i + 1]))
        body += pages[i + 2]
    bt = re.sub(r"\s+", " ", body)
    pm = re.search(r"PRESS RELEASE|News Release|FOR IMMEDIATE RELEASE|Exhibit 99\.?\s?1", bt)
    if pm:
        start = pm.end()
    else:
        im0 = re.search(r"Item\s+(?:1\.01|8\.01|2\.01|7\.01)", bt)
        start = im0.start() if im0 else 0
    head = bt[start:start + 900]
    if SKIP_TITLE.search(bt[start:start + 350]):
        return None
    if not DEAL_KW.search(bt[start:start + 3000]):
        return None
    sents = sentences(bt)
    dt = deal_type(bt[start:start + 3000])
    row = dict(date=filed, deal_type=dt, acquirer_or_licensee="", target_or_licensor="", asset="", modality="",
               therapeutic_area="", indication="", stage_at_deal="", upfront_usd_m=None, equity_usd_m=None,
               milestones_usd_m=None, total_potential_usd_m=None, royalty_terms="", territory="",
               deal_value_to_peak_sales_note="", source=url, source_row="", quote="", confidence="")
    ctx = bt[start:start + 3500]
    quote = None
    if dt == "acquisition":
        tot, quote = acq_econ(sents)
        a, tg = parties_acq(head)
        row["acquirer_or_licensee"], row["target_or_licensor"] = a, tg
        row["upfront_usd_m"] = tot
        row["total_potential_usd_m"] = tot
        cvr = [s for s in sents if re.search(r"contingent value right|CVR", s) and amounts(s)]
        if cvr:
            row["deal_value_to_peak_sales_note"] = ("CVR: " + cvr[0])[:250]
            ca = amounts(cvr[0])
            if tot and ca and re.search(r"per share", cvr[0], re.I):
                pass
        conf = "high" if (tot and a and tg) else "medium"
        if not quote or not tot:
            return None
        row["confidence"] = conf
    else:
        up, eq, ms, tot, quote = econ(sents, dt)
        if up is None and tot is None and ms is None:
            return None
        row.update(upfront_usd_m=up, equity_usd_m=eq, milestones_usd_m=ms, total_potential_usd_m=tot)
        if tot is None and up is not None and ms is not None:
            row["total_potential_usd_m"] = up + ms + (eq or 0) if False else up + ms
        ft = tok(filer)
        cpm = None
        for cm in re.finditer(r"(?:with|from|and|by|to)\s+(" + ORG + r")(?= for | to |,|;|\.| \(| regarding| on |$| a | an |\s[a-z])", head):
            cand = cm.group(1).strip()
            if tok(cand) != ft and len(cand) > 2 and cand.split()[0] not in ("Exhibits", "Exhibit", "San", "New", "The", "Phase", "A", "An", "Exclusive", "Global", "Worldwide", "U.S", "US", "Japan", "China"):
                cpm = cand
                break
        cp = cpm or ""
        r = None
        qs = quote or ""
        for s in sents:
            if re.search(r"up-?front", s, re.I) and amounts(s):
                r = role(s, ft, tok(cp) if cp else "")
                if r:
                    break
        conf = "high"
        if r is None:
            hl = head.lower()
            if re.search(r"(in-?license|license from|licensed from|rights from|obtain|acquire).{0,80}", hl) and ft in hl[:hl.find("licens") + 1 if "licens" in hl else 0]:
                r = "filer_licensee"
            conf = "medium"
        if r is None:
            r = "filer_licensor"
            conf = "low:role"
        if not cp:
            conf = "low:role" if conf == "low:role" else "medium"
        if r == "filer_licensor":
            row["target_or_licensor"], row["acquirer_or_licensee"] = filer, cp
        else:
            row["acquirer_or_licensee"], row["target_or_licensor"] = filer, cp
        row["confidence"] = conf
    # descriptive fields
    row["modality"] = classify(ctx, MODS)
    row["therapeutic_area"] = classify(ctx, TAS)
    row["stage_at_deal"] = stage_of(ctx)
    im = re.search(r"(?:treatment|prevention|management) of ([^\.;]{3,90}?)(?:\.|;| and | in | with | by |,|$)", ctx)
    row["indication"] = im.group(1).strip() if im else ""
    am = re.search(r"\b([A-Z]{1,5}[-‑ ]?\d{2,6}[A-Za-z]?)\b", ctx)
    if am and not am.group(1).startswith(("EX", "FY", "Q", "ASCO", "ESMO", "SEC", "ISO")) and am.group(1) not in ("COVID-19", "Q1", "Q2", "Q3", "Q4") and not am.group(1).startswith("NCT"):
        row["asset"] = am.group(1)
    else:
        xm = re.search(r"(?:rights to|license (?:to|for)|develop and commercialize|candidate|program) ([^\.;,]{5,70})", head)
        row["asset"] = xm.group(1).strip() if xm else ""
    row["territory"] = terr(ctx)
    row["royalty_terms"] = royalty_text(sents)
    pn = peak_note(sents)
    if pn and not row["deal_value_to_peak_sales_note"]:
        row["deal_value_to_peak_sales_note"] = pn
    q = window(quote or "")
    row["quote"] = q
    # page of quote
    off = bt.find(q[:60]) if q else -1
    pg, pr = "1", "?"
    if off >= 0:
        # map by raw body: find in body
        bo = body.replace("\n", " ").find(q[:40]) if q else -1
        for st, p, pt in pagemap:
            if bo >= 0 and st <= bo:
                pg, pr = p, pt
    row["source_row"] = f"{path.name} [[page {pg} | printed {pr}]]"
    row["_acc"] = acc
    return row


if __name__ == "__main__":
    out = open("data/moat/scratch/deals_8k_rows.jsonl", "w")
    n = k = 0
    for p in sorted(OUTD.glob("*.md")):
        n += 1
        try:
            r = process(p)
        except Exception as e:
            print("ERR", p.name, e)
            continue
        if r:
            k += 1
            out.write(json.dumps(r) + "\n")
    print(n, "docs", k, "rows")
