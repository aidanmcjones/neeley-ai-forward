"""Product fine-print comparator: a product vs its rivals on label, safety, dosing, protection timeline,
IRA status and Medicare spend, plus Signals where a label difference should show up in the numbers.

  python -m agent.needle.detect.labels [--ticker BMY]
  run(ticker) -> list[Signal]; also writes out/<TICKER>/labels_table.json (full side-by-side tables)

Every profile field is {"value": ..., "source": "label §1" | "orange_book_patents.csv" | ...}.
Label facts carry Evidence(doc_id="drug:<slug>:label_sections.md", page=None, quote=<verbatim>);
verify_label(ev) confirms the quote occurs in that file and fills ev.citation.
"""

import json
import re
import statistics
from functools import lru_cache

import pandas as pd

from agent.needle.detect import CASE_SETS, OUT, ROOT, cli
from agent.needle.schema import Evidence, Signal

DRUGS = ROOT / "data" / "corpus" / "drugs"
DETECTOR = "labels"
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]


# ---------------------------------------------------------------- label parsing
def _norm(s):
    s = (s or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def _label_path(slug):
    return DRUGS / slug / "label_sections.md"


@lru_cache(maxsize=None)
def _label_text(slug):
    p = _label_path(slug)
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


_HEAD = re.compile(r"^(#{2,6})\s*(.*)$")


@lru_cache(maxsize=None)
def _parse(slug):
    """-> dict(sections={n: text}, subs={n: [(num, title, text)]}, boxed=(heading, text)|None, setid, url)"""
    text = _label_text(slug)
    lines = text.splitlines()
    sections, boxed = {}, None
    cur = None  # ("sec", n) | ("box",) | ("other",)
    buf = {}
    boxed_head = None
    for ln in lines:
        m = _HEAD.match(ln)
        if m and len(m.group(1)) == 2:
            title = m.group(2).strip()
            mm = re.match(r"(\d+)\b", title)
            if mm and int(mm.group(1)) not in buf:
                cur = ("sec", int(mm.group(1)))
                buf[cur] = []
                buf[cur].append(ln)
                continue
            if re.match(r"WARNING\b", title, re.I) and boxed_head is None:
                cur = ("box",)
                boxed_head = title
                buf[cur] = []
                continue
            cur = ("other",)
            continue
        if cur and cur[0] != "other":
            buf[cur].append(ln)
    for k, v in buf.items():
        if k[0] == "sec":
            sections[k[1]] = "\n".join(v)
    if ("box",) in buf:
        boxed = (boxed_head, "\n".join(buf[("box",)]))
    m = re.search(r"setid=([0-9a-f-]+)", text[:600])
    um = re.search(r"source:\s*(\S+)", text[:600])
    return {"sections": sections, "boxed": boxed, "setid": m.group(1) if m else "",
            "url": um.group(1) if um else ""}


def _subs(sec_text, n):
    """### n.x subsections of a section body -> [(num, title, body)]."""
    out, cur = [], None
    for ln in sec_text.splitlines():
        m = re.match(r"^###\s*(%d\.\d+)\s*(.*)$" % n, ln)
        if m:
            cur = [m.group(1), m.group(2).strip(), []]
            out.append(cur)
            continue
        if re.match(r"^#{1,3}\s", ln):
            cur = None
            continue
        if cur is not None:
            cur[2].append(ln)
    return [(a, b, "\n".join(c)) for a, b, c in out]


def _paras(body):
    """Clean text paragraphs of a body (no headings, bullets stripped)."""
    out = []
    for p in re.split(r"\n\s*\n", body):
        ls = [l for l in p.splitlines() if not l.startswith("#")]
        t = " ".join(ls).strip()
        t = re.sub(r"^[-•o\s]+(?=\w)", "", t).strip()
        if len(t.split()) >= 6:
            out.append(t)
    return out


def _clip(t, n=40):
    w = t.split()
    return " ".join(w[:n])


def _ev(slug, quote):
    q = _clip(_norm(quote), 55)
    return Evidence(doc_id=f"drug:{slug}:label_sections.md", page=None, quote=q) if q else None


def _snippet_around(body, rx, width=14):
    """Verbatim <=2*width-word window from the single line containing the first regex match."""
    for ln in body.splitlines():
        m = rx.search(ln)
        if m:
            words = ln.split()
            pre = len(ln[:m.start()].split())
            lo = max(0, pre - width)
            s = " ".join(words[lo:lo + 2 * width + 4])
            s = re.sub(r"^[-•o\s]+(?=\w)", "", s)
            return s
    return ""


def verify_label(ev):
    """Confirm ev.quote occurs in the label file named by ev.doc_id; set ev.citation. Returns bool."""
    m = re.match(r"drug:([^:]+):(.+)$", ev.doc_id or "")
    if not m:
        return False
    slug, fname = m.groups()
    p = DRUGS / slug / fname
    if not p.exists():
        return False
    q = _norm(ev.quote)
    if not q:
        return False
    raw = p.read_text(encoding="utf-8", errors="replace")
    if q not in _norm(raw):
        return False
    setid_m = re.search(r"setid=([0-9a-f-]+)", raw[:600])
    setid = setid_m.group(1) if setid_m else "?"
    sec, label = "?", ""
    cur = "?"
    chunks = []
    block = []

    def flush():
        if block:
            chunks.append((cur, "\n".join(block)))

    for ln in raw.splitlines():
        hm = _HEAD.match(ln)
        if hm:
            flush()
            block = []
            title = hm.group(2).strip()
            nm = re.match(r"(\d+(?:\.\d+)*)\b", title)
            if nm:
                cur = nm.group(1)
            elif len(hm.group(1)) == 2:
                cur = "Boxed Warning" if re.match(r"WARNING\b", title, re.I) else title[:40]
            block.append(ln)
        else:
            block.append(ln)
    flush()
    for c, t in chunks:
        if q in _norm(t):
            sec = c
            break
    name = slug.replace("-", " ").title()
    ev.citation = f"{name} label " + (sec if sec == "Boxed Warning" else f"§{sec}") + f" (DailyMed setid {setid})"
    return True


# ---------------------------------------------------------------- csv helpers
def _csv(slug, name):
    p = DRUGS / slug / name
    if not p.exists():
        return None
    try:
        d = pd.read_csv(p, dtype=str)
    except Exception:
        return None
    return d if len(d) else None


def _dates(series):
    return pd.to_datetime(series, errors="coerce").dropna()


def _f(value, source, **kw):
    d = {"value": value, "source": source}
    d.update(kw)
    return d


def _iso(ts):
    return None if ts is None or pd.isna(ts) else ts.strftime("%Y-%m-%d")


# ---------------------------------------------------------------- dosing / route
FREQS = [  # (key, regex, doses per year)
    ("three times daily", r"\b(three times (?:a day|daily)|3 times (?:a day|daily))\b", 1095),
    ("twice daily", r"\b(twice[- ](?:a day|daily)|two times (?:a day|daily)|every 12 hours)\b", 730),
    ("once daily", r"\b(once[- ](?:a day|daily)|one time (?:a day|daily)|1 time (?:a day|daily)|once per day|every 24 hours|daily)\b", 365),
    ("once weekly", r"\b(once[- ](?:a week|weekly)|every week|weekly|once per week)\b", 52),
    ("every N days", r"\bevery (\d+) days\b", None),
    ("every N weeks", r"\bevery (\d+)(?:\s*(?:to|or|-)\s*\d+)? weeks?\b", None),
    ("every N months", r"\bevery (\d+)(?:\s*(?:to|or|-)\s*\d+)? months?\b", None),
    ("monthly", r"\b(once[- ]monthly|every month|monthly|once a month)\b", 12),
]


def _dosing(sec2):
    counts = {}
    first_rx = {}
    for key, rx, per_year in FREQS:
        r = re.compile(rx, re.I)
        for m in r.finditer(sec2):
            if key == "every N weeks":
                n = int(m.group(1)); k, py = f"every {n} weeks", 52 / n
            elif key == "every N days":
                n = int(m.group(1)); k, py = f"every {n} days", 365 / n
            elif key == "every N months":
                n = int(m.group(1)); k, py = f"every {n} months", 12 / n
            else:
                k, py = key, per_year
            if n_ok(k):
                counts.setdefault(k, [0, py, r])[0] += 1
    if not counts:
        return None
    best = max(counts.items(), key=lambda kv: kv[1][0])
    return {"frequency": best[0], "doses_per_year": round(best[1][1], 1), "regex": best[1][2],
            "all": {k: v[0] for k, v in counts.items()}}


def n_ok(k):
    m = re.search(r"every (\d+)", k)
    return not m or int(m.group(1)) > 0


ROUTE_RX = {"oral": r"\b(oral(?:ly)?|tablets?|capsules?)\b",
            "subcutaneous": r"\b(subcutaneous(?:ly)?|prefilled (?:pen|syringe)|autoinjector|pen)\b",
            "intravenous": r"\b(intravenous(?:ly)?|infusion|vials?)\b"}
OB_ROUTE = {"ORAL": "oral", "SUBCUTANEOUS": "subcutaneous", "INTRAVENOUS": "intravenous", "INJECTION": "injection"}


def _routes(slug, sec2, sec3):
    ob = _csv(slug, "orange_book_products.csv")
    if ob is not None:
        rs = []
        for v in ob["DF;Route"].dropna():
            r = v.split(";")[-1].strip().upper()
            r = OB_ROUTE.get(r, r.lower())
            if r not in rs:
                rs.append(r)
        if rs and "injection" not in rs:
            return rs, rs[0], "orange_book_products.csv"
    pbk = _csv(slug, "purple_book.csv")
    if pbk is not None and "Route of Administration" in pbk:
        nm = slug.replace("-", " ").lower()
        own = pbk[pbk["Proprietary Name"].fillna("").str.lower().str.strip() == nm]
        act = own[own["Marketing Status"].fillna("") != "Disc"]
        vc = (act if len(act) else own)["Route of Administration"].dropna().str.lower().str.strip().value_counts()
        if len(vc):
            return list(vc.index), vc.index[0], "purple_book.csv"
    basis = sec3 if sec3.strip() else sec2
    cnt = {k: len(re.findall(rx, basis, re.I)) for k, rx in ROUTE_RX.items()}
    cnt = {k: v for k, v in cnt.items() if v}
    if not cnt:
        return [], None, "label §3"
    # "tablets" in an injectable label is rare; a subcutaneous/IV hit outranks oral words in sec 2/3
    rs = sorted(cnt, key=lambda k: -cnt[k])
    return rs, rs[0], "label §3" if sec3.strip() else "label §2"


# ---------------------------------------------------------------- profile
@lru_cache(maxsize=None)
def _profile(slug):
    d = DRUGS / slug
    P = {"slug": slug}
    lab = _parse(slug)
    secs = lab["sections"]
    if not _label_path(slug).exists():
        P["_missing_label"] = True
    P["label_url"] = _f(lab["url"] or None, "label_sections.md first line")
    P["_evidence"] = {}

    # indications
    s1 = secs.get(1, "")
    subs = _subs(s1, 1)
    titles = [re.sub(r"\s+", " ", t) for _, t, _ in subs]
    if not titles and s1.strip():
        bul = [re.sub(r"^-\s*•?\s*", "", l).strip() for l in s1.splitlines()
               if re.match(r"^-\s+\S", l) and not re.match(r"^-\s+o\s", l)]
        titles = [_clip(b, 14) for b in bul]
        if not titles:
            titles = [_clip(p, 14) for p in _paras(s1)[:1]]
    P["indications"] = _f(titles, "label §1", count=len(titles))
    P["indication_count"] = _f(len(titles) if s1.strip() else None, "label §1")
    q = None
    ps = _paras(re.sub(r"(?m)^#{1,6}.*$", "", s1.split("\n### 1.")[0])) if s1 else []
    if ps:
        q = ps[0]
    elif subs:
        sp = _paras(subs[0][2])
        q = sp[0] if sp else None
    P["_evidence"]["indications"] = _ev(slug, q) if q else None

    # boxed warning
    bw = lab["boxed"]
    if bw:
        paras = _paras(bw[1])
        body = paras[0] if paras else bw[0]
        P["boxed_warning"] = _f(True, "label boxed warning", text=_clip(_norm(" ".join(paras) or bw[0]), 40),
                                heading=bw[0])
        P["_evidence"]["boxed_warning"] = _ev(slug, body)
    else:
        P["boxed_warning"] = _f(False if s1.strip() else None, "label (no WARNING heading)", text="")
        P["_evidence"]["boxed_warning"] = None

    # contraindications
    s4 = secs.get(4, "")
    if s4.strip():
        body = re.sub(r"(?m)^#{1,6}.*$", "", s4)
        items = [l for l in body.splitlines() if re.match(r"^-\s", l)]
        items = [l for l in items if len(re.sub(r"[-•\s]", "", l)) > 2]
        if not items:
            items = [p for p in _paras(body) if not re.match(r"none\b", p, re.I)]
            body_none = re.search(r"\bnone\b", body, re.I) and not items
            n = 0 if body_none else len(items)
        else:
            n = len(items)
        P["contraindications"] = _f(n, "label §4")
        ps4 = _paras(body)
        P["_evidence"]["contraindications"] = _ev(slug, ps4[0]) if ps4 else None
    else:
        P["contraindications"] = _f(None, "label §4 not found")
        P["_evidence"]["contraindications"] = None

    # route, dosing
    s2, s3 = secs.get(2, ""), secs.get(3, "")
    rs, primary, rsrc = _routes(slug, s2, s3)
    P["route"] = _f(primary, rsrc, all=rs)
    dz = _dosing(s2) if s2.strip() else None
    if dz:
        P["dosing_frequency"] = _f(dz["frequency"], "label §2", doses_per_year=dz["doses_per_year"], all=dz["all"])
        sn = _snippet_around(s2, dz["regex"])
        P["_evidence"]["dosing_frequency"] = _ev(slug, sn) if sn else None
    else:
        P["dosing_frequency"] = _f(None, "label §2 (no frequency pattern)", doses_per_year=None)
        P["_evidence"]["dosing_frequency"] = None

    # REMS
    scan = "\n".join(secs.get(i, "") for i in (1, 2, 4, 5)) + (lab["boxed"][1] if lab["boxed"] else "")
    rm = re.compile(r"\bREMS\b|Risk Evaluation and Mitigation", re.I)
    if scan.strip():
        sn = _snippet_around(scan, rm)
        P["rems"] = _f(bool(sn), "label §1-5")
        P["_evidence"]["rems"] = _ev(slug, sn) if sn else None
    else:
        P["rems"] = _f(None, "label")
        P["_evidence"]["rems"] = None

    # Orange Book
    pat = _csv(slug, "orange_book_patents.csv")
    ends = []
    if pat is not None:
        p2 = pat[pat.get("Delist_Flag", pd.Series(index=pat.index, dtype=str)).fillna("") != "Y"]
        p2 = p2.assign(_d=pd.to_datetime(p2["Patent_Expire_Date_Text"], errors="coerce")).dropna(subset=["_d"])
        if len(p2):
            top = p2.sort_values("_d").iloc[-1]
            P["latest_patent_expiry"] = _f(_iso(top["_d"]), "orange_book_patents.csv", patent_no=top["Patent_No"])
            P["patent_count"] = _f(int(p2["Patent_No"].nunique()), "orange_book_patents.csv")
            ends.append(top["_d"])
        else:
            P["latest_patent_expiry"] = _f(None, "orange_book_patents.csv (no dated rows)")
            P["patent_count"] = _f(0, "orange_book_patents.csv")
    else:
        P["latest_patent_expiry"] = _f(None, "orange_book_patents.csv not in pack")
        P["patent_count"] = _f(None, "orange_book_patents.csv not in pack")
    ex = _csv(slug, "orange_book_exclusivity.csv")
    if ex is not None:
        ex = ex.assign(_d=pd.to_datetime(ex["Exclusivity_Date"], errors="coerce")).dropna(subset=["_d"])
        pairs = sorted({(r["Exclusivity_Code"], _iso(r["_d"])) for _, r in ex.iterrows()}, key=lambda x: x[1])
        P["exclusivity"] = _f([{"code": c, "date": d_} for c, d_ in pairs], "orange_book_exclusivity.csv",
                              latest=pairs[-1][1] if pairs else None)
        if pairs:
            ends.append(pd.Timestamp(pairs[-1][1]))
    else:
        P["exclusivity"] = _f([], "orange_book_exclusivity.csv not in pack", latest=None)

    # Purple Book
    pb = _csv(slug, "purple_book.csv")
    if pb is not None:
        nm = slug.replace("-", " ").lower()
        pn = pb["Proprietary Name"].fillna("").str.lower().str.strip()
        own = pb[pn == nm]
        if own.empty:
            own = pb[pb["Ref. Product Proprietary Name"].isna()]
        refname = own["Proprietary Name"].iloc[0] if len(own) else slug
        bios = pb[pb["Ref. Product Proprietary Name"].fillna("").str.lower().str.strip() == refname.lower().strip()]
        bios_names = sorted({n for n in bios["Proprietary Name"].dropna() if n.lower() != refname.lower()})
        cols = ["Exclusivity Expiration Date", "Ref. Product Exclusivity Exp. Date", "Orphan Exclusivity Exp. Date",
                "First Interchangeable Exclusivity Exp. Date"]
        ed = {}
        for c in cols:
            ds = _dates(own[c]) if c in own else []
            if len(ds):
                ed[c] = _iso(max(ds))
        lic = own[own["Submission Type"].fillna("") == "Original"] if "Submission Type" in own else own
        ap = _dates(lic["Approval Date"]) if len(lic) else []
        derived = None
        if len(ap):
            derived = _iso(min(ap) + pd.DateOffset(years=12))
        P["purple_exclusivity"] = _f(ed, "purple_book.csv", derived_12y_reference_exclusivity=derived,
                                     first_licensed=_iso(min(ap)) if len(ap) else None)
        P["biosimilars_referencing"] = _f(len(bios_names), "purple_book.csv", names=bios_names)
        for v in list(ed.values()) + ([derived] if derived else []):
            ends.append(pd.Timestamp(v))
    else:
        P["purple_exclusivity"] = _f({}, "purple_book.csv not in pack", derived_12y_reference_exclusivity=None)
        P["biosimilars_referencing"] = _f(None, "purple_book.csv not in pack", names=[])
    P["protection_end"] = _f(_iso(max(ends)) if ends else None,
                             "max of orange_book_patents/exclusivity.csv, purple_book.csv (12y derived for biologics)")

    # Paragraph IV
    pv = _csv(slug, "paragraph_iv.csv")
    if pv is not None:
        tot = pd.to_numeric(pv.get("NUMBER OF ANDAs SUBMITTED"), errors="coerce").sum()
        P["paragraph_iv"] = _f(len(pv), "paragraph_iv.csv", andas_submitted=int(tot))
    else:
        P["paragraph_iv"] = _f(0 if (d / "label_sections.md").exists() and pat is not None else None,
                               "paragraph_iv.csv not in pack", andas_submitted=None)

    # IRA
    ira = _csv(slug, "ira_negotiation.csv")
    if ira is not None:
        ipay = pd.to_numeric(ira["IPAY"], errors="coerce").dropna()
        y = int(ipay.min()) if len(ipay) else None
        rows = ira[pd.to_numeric(ira["IPAY"], errors="coerce") == y]
        mfp = pd.to_numeric(rows["Single MFP per 30 DES"], errors="coerce").dropna()
        eff = _dates(rows["MFP Effective Date"])
        P["ira"] = _f({"selected": True, "ipay": y, "mfp_per_30_days": float(statistics.median(mfp)) if len(mfp) else None,
                       "mfp_effective": _iso(min(eff)) if len(eff) else None}, "ira_negotiation.csv")
    else:
        P["ira"] = _f({"selected": False, "ipay": None, "mfp_per_30_days": None, "mfp_effective": None},
                      "ira_negotiation.csv not in pack (not selected)")

    # Medicare
    P["medicare"] = _medicare(slug, primary, P["ira"]["value"])
    return P


def _med_years(df, spend_col):
    out = []
    for y in YEARS:
        c = f"{spend_col}_{y}"
        if c in df and pd.to_numeric(df[c], errors="coerce").notna().any():
            out.append(y)
    return out


def _medicare(slug, primary, ira):
    res = {}
    pd_ = _csv(slug, "medicare_partd_spending.csv")
    if pd_ is not None:
        df = pd_[pd_["Mftr_Name"] == "Overall"]
        yrs = _med_years(df, "Tot_Spndng")
        if len(df) and yrs:
            y = yrs[-1]
            n = lambda c: pd.to_numeric(df[f"{c}_{y}"], errors="coerce").sum(min_count=1)
            sp, cl, be = n("Tot_Spndng"), n("Tot_Clms"), n("Tot_Benes")
            res["D"] = {"part": "D", "year": y, "spend": float(sp), "claims": float(cl), "beneficiaries": float(be),
                        "avg_per_claim": float(sp / cl) if cl else None,
                        "brands": sorted(set(df["Brnd_Name"])), "source": "medicare_partd_spending.csv"}
    pb_ = _csv(slug, "medicare_partb_spending.csv")
    if pb_ is not None:
        first = slug.split("-")[0].lower()
        sel = pb_[pb_["Brnd_Name"].fillna("").str.lower().str.contains(first, regex=False)]
        df = sel if len(sel) else pb_
        yrs = _med_years(df, "Tot_Spndng")
        if len(df) and yrs:
            y = yrs[-1]
            n = lambda c: pd.to_numeric(df[f"{c}_{y}"], errors="coerce").sum(min_count=1)
            sp, cl, be = n("Tot_Spndng"), n("Tot_Clms"), n("Tot_Benes")
            res["B"] = {"part": "B", "year": y, "spend": float(sp), "claims": float(cl), "beneficiaries": float(be),
                        "avg_per_claim": float(sp / cl) if cl else None,
                        "brands": sorted(set(df["Brnd_Name"])), "source": "medicare_partb_spending.csv"}
    if not res:
        return {"value": None, "source": "medicare_part[bd]_spending.csv: no spend rows"}
    best = max(res.values(), key=lambda r: r["spend"] or 0)
    best = dict(best)
    best["other_part"] = {k: v for k, v in res.items() if v["part"] != best["part"]}
    # IRA maximum fair price vs average Part D claim (approximate: a claim is about 30 days)
    if ira and ira.get("mfp_per_30_days") and best["part"] == "D" and best["avg_per_claim"]:
        best["mfp_vs_avg_claim_pct"] = round(100 * (ira["mfp_per_30_days"] / best["avg_per_claim"] - 1), 1)
    return {"value": best, "source": best["source"]}


def profile(slug):
    """Fine-print profile of one product; each field {"value", "source"}."""
    return _profile(slug)


# ---------------------------------------------------------------- compare
def _cell(P, field):
    """Plain table cell from a profile field."""
    f = P.get(field)
    if f is None:
        return None
    v = f["value"]
    if field == "indications":
        return f"{f['count']}"
    if field == "boxed_warning":
        return "Yes: " + f["text"] if v else ("No" if v is False else None)
    if field == "exclusivity":
        return "; ".join(f"{e['code']} {e['date']}" for e in v) or None
    if field == "purple_exclusivity":
        parts = [f"{k.replace(' Exp. Date', '').replace(' Expiration Date', '')}: {d}" for k, d in v.items()]
        if f.get("derived_12y_reference_exclusivity"):
            parts.append(f"12y from first licence (derived): {f['derived_12y_reference_exclusivity']}")
        return "; ".join(parts) or None
    if field == "paragraph_iv":
        return None if v is None else f"{v} filings"
    if field == "ira":
        if not v["selected"]:
            return "Not selected"
        s = f"Selected IPAY {v['ipay']}"
        if v["mfp_per_30_days"]:
            s += f", MFP ${v['mfp_per_30_days']:,.2f}/30 days"
        return s
    if field == "route":
        return "/".join(f["all"]) or None
    if field == "medicare":
        if not v:
            return None
        return (f"Part {v['part']} {v['year']}: ${v['spend']:,.0f} spend, {v['claims']:,.0f} claims, "
                f"{v['beneficiaries']:,.0f} benes, ${v['avg_per_claim']:,.0f}/claim"
                + (f"; MFP is {v['mfp_vs_avg_claim_pct']}% vs avg claim" if "mfp_vs_avg_claim_pct" in v else ""))
    return v


TABLE_FIELDS = [
    ("Approved indications (count)", "indications"), ("Boxed warning", "boxed_warning"),
    ("Contraindications (items)", "contraindications"), ("REMS", "rems"), ("Route", "route"),
    ("Dosing frequency", "dosing_frequency"), ("Latest patent expiry", "latest_patent_expiry"),
    ("Patent count", "patent_count"), ("Orange Book exclusivity", "exclusivity"),
    ("Purple Book exclusivity", "purple_exclusivity"), ("Biosimilars referencing", "biosimilars_referencing"),
    ("Paragraph IV filings", "paragraph_iv"), ("Protection ends (latest)", "protection_end"),
    ("IRA negotiation", "ira"), ("Medicare spend (latest year)", "medicare"), ("Label source", "label_url"),
]


def _table(slug, rivals):
    Ps = {s: profile(s) for s in [slug] + rivals}
    rows = []
    for title, key in TABLE_FIELDS:
        rows.append({"field": title, "product": _cell(Ps[slug], key), "source": Ps[slug][key]["source"],
                     "rivals": {r: _cell(Ps[r], key) for r in rivals},
                     "rival_sources": {r: Ps[r][key]["source"] for r in rivals}})
    return rows


def _med(P):
    return P["medicare"]["value"]


def _sig(ticker, kind, slug, detail, evs=None, value=None, peer=None, period="", meta=None):
    evs = [e for e in (evs or []) if e is not None]
    for e in evs:
        if not verify_label(e):
            return None
    m = {"product": slug}
    m.update(meta or {})
    return Signal(ticker=ticker, detector=DETECTOR, kind=kind, period=period, value=value, peer_median=peer,
                  detail=detail, evidence=evs, meta=m)


def compare(ticker):
    """-> {product_slug: {"rivals": [...], "table": rows, "signals": [Signal]}}"""
    ticker = ticker.upper()
    res = {}
    for slug, rivals in CASE_SETS[ticker].items():
        P = profile(slug)
        sigs = []
        S = lambda *a, **k: sigs.append(x) if (x := _sig(ticker, *a, **k)) else None
        ev = P["_evidence"]

        # label breadth vs rival median
        rc = {r: profile(r)["indication_count"]["value"] for r in rivals}
        known = [v for v in rc.values() if v is not None]
        pc = P["indication_count"]["value"]
        if pc is not None and known:
            med = statistics.median(known)
            rev = [ev["indications"]] + [profile(r)["_evidence"]["indications"] for r in rivals if rc[r] == max(known)]
            if pc <= med - 2:
                S("label_narrower", slug, f"{slug} lists {pc} indications vs rival median {med:g} ({rc}); "
                  "narrower label should show up as a smaller addressable patient pool", rev, pc, med,
                  meta={"data": {"rival_counts": rc}})
            elif pc >= med + 2:
                S("label_broader", slug, f"{slug} lists {pc} indications vs rival median {med:g} ({rc}); "
                  "broader label supports more volume growth routes", rev, pc, med,
                  meta={"data": {"rival_counts": rc}})

        for r in rivals:
            R = profile(r)
            # boxed warning
            pb, rb = P["boxed_warning"]["value"], R["boxed_warning"]["value"]
            if pb and rb is False:
                S("boxed_warning_disadvantage", slug, f"{slug} carries a boxed warning ({P['boxed_warning']['heading']}); "
                  f"{r} does not", [ev["boxed_warning"], R["_evidence"]["indications"]], meta={"rival": r})
            elif rb and pb is False:
                S("boxed_warning_advantage", slug, f"{r} carries a boxed warning ({R['boxed_warning']['heading']}); "
                  f"{slug} does not", [R["_evidence"]["boxed_warning"], ev["indications"]], meta={"rival": r})

            # dosing burden
            pr, rr = P["route"]["value"], R["route"]["value"]
            pd_, rd = P["dosing_frequency"].get("doses_per_year"), R["dosing_frequency"].get("doses_per_year")
            burden, why = None, ""
            if pr == "intravenous" and rr in ("oral", "subcutaneous"):
                burden, why = "burden", f"{slug} is {pr} (clinic infusion) vs {r} {rr}"
            elif rr == "intravenous" and pr in ("oral", "subcutaneous"):
                burden, why = "advantage", f"{slug} is {pr} vs {r} intravenous"
            if burden is None and pd_ and rd:
                if pd_ >= 2 * rd:
                    burden, why = "burden", f"{slug} {P['dosing_frequency']['value']} ({pd_:g}/yr) vs {r} {R['dosing_frequency']['value']} ({rd:g}/yr)"
                elif rd >= 2 * pd_:
                    burden, why = "advantage", f"{slug} {P['dosing_frequency']['value']} ({pd_:g}/yr) vs {r} {R['dosing_frequency']['value']} ({rd:g}/yr)"
            if burden:
                S("dosing_burden" if burden == "burden" else "dosing_advantage", slug, why,
                  [ev["dosing_frequency"], R["_evidence"]["dosing_frequency"]], pd_, rd,
                  meta={"rival": r, "data": {"route": [pr, rr], "doses_per_year": [pd_, rd]}})

            # exclusivity timeline
            pe, re_ = P["protection_end"]["value"], R["protection_end"]["value"]
            if pe and re_:
                gap = (pd.Timestamp(re_) - pd.Timestamp(pe)).days / 365.25
                if gap >= 1:
                    S("exclusivity_earlier", slug, f"{slug} protection ends {pe}, {gap:.1f} years before {r} ({re_}); "
                      "earlier loss of exclusivity", None, None, None,
                      meta={"rival": r, "data": {"product_end": pe, "rival_end": re_, "gap_years": round(gap, 2),
                            "files": ["orange_book_patents.csv", "orange_book_exclusivity.csv", "purple_book.csv"],
                            "product_fields": {k: P[k]["value"] for k in ("latest_patent_expiry", "exclusivity", "purple_exclusivity")},
                            "rival_fields": {k: R[k]["value"] for k in ("latest_patent_expiry", "exclusivity", "purple_exclusivity")}}})

            # IRA
            pi, ri = P["ira"]["value"], R["ira"]["value"]
            if pi["selected"] and (not ri["selected"] or (ri["ipay"] and pi["ipay"] < ri["ipay"])):
                S("ira_exposed", slug, f"{slug} IRA-selected (IPAY {pi['ipay']}, MFP/30d {pi['mfp_per_30_days']}) while "
                  f"{r} is " + ("not selected" if not ri["selected"] else f"selected later (IPAY {ri['ipay']})"),
                  None, pi["ipay"], ri["ipay"], meta={"rival": r, "data": {"product": pi, "rival": ri,
                                                     "file": "ira_negotiation.csv"}})

            # spend per claim
            pm, rm_ = _med(P), _med(R)
            if pm and rm_ and pm["part"] == rm_["part"] and pm["avg_per_claim"] and rm_["avg_per_claim"]:
                pct = pm["avg_per_claim"] / rm_["avg_per_claim"] - 1
                if abs(pct) >= 0.25:
                    S("spend_per_claim_gap", slug, f"{slug} Part {pm['part']} spend/claim ${pm['avg_per_claim']:,.0f} "
                      f"({pm['year']}) is {abs(pct):.0%} {'higher' if pct > 0 else 'lower'} than {r} "
                      f"${rm_['avg_per_claim']:,.0f} ({rm_['year']}); gross, before rebates", None,
                      pm["avg_per_claim"], rm_["avg_per_claim"], period=str(pm["year"]),
                      meta={"rival": r, "pct_gap": round(pct, 3),
                            "data": {"files": [pm["source"], rm_["source"]], "product": pm, "rival": rm_}})
        res[slug] = {"rivals": rivals, "table": _table(slug, rivals), "signals": sigs}
    return res


def _jsonable(o):
    if isinstance(o, re.Pattern):
        return o.pattern
    return str(o)


def run(ticker):
    ticker = ticker.upper()
    comp = compare(ticker)
    out = OUT / ticker / "labels_table.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ticker": ticker, "products": {s: {"rivals": c["rivals"], "table": c["table"]} for s, c in comp.items()}}
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_jsonable), encoding="utf-8")
    return [s for c in comp.values() for s in c["signals"]]


if __name__ == "__main__":
    cli("labels", run)
