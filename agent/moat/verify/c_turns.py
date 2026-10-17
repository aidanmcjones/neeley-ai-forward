"""Verified qa_turns (speaker attribution fixes) and per-transcript quotability grades.

Inputs: tables/qa_turns.csv, tables/transcripts_index.csv (written by calls_tables to ROOT/tables), cross_source.csv.
Outputs under data/moat/verified/calls/: qa_turns.csv, transcript_grades.csv, roster_check.csv.
"""
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

from agent.moat.common import ROOT
from agent.moat.verify.c_cross import SRC, V, load, squash
from agent.moat.verify.c_roster import ANALYST, EXEC, FIRM, NOT_FIRM

TAB = ROOT / "tables"
CO = {"ABBV": "AbbVie", "AMGN": "Amgen", "AZN": "AstraZeneca", "BMY": "Bristol Myers Squibb", "GILD": "Gilead Sciences",
      "JNJ": "Johnson & Johnson", "LLY": "Eli Lilly and Company", "MRK": "Merck & Co.", "NVO": "Novo Nordisk", "PFE": "Pfizer"}
OFFICIAL_COPY = {("MRK", "2025Q2"): "MRK_2025Q2_official.pdf", ("JNJ", "2024Q3"): "JNJ_2024Q3_official.pdf",
                 ("JNJ", "2025Q2"): "JNJ_2025Q2_official.pdf", ("JNJ", "2026Q2"): "JNJ_2026Q2_official.pdf",
                 **{("PFE", q): f"PFE_{q}_official.pdf" for q in ("2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2")}}
DATE_FIX = {("BMY", "2025Q3"): ("2025-10-30", "index used fool.com article date 2025-11-27; MarketBeat/BMY call date 2025-10-30"),
            ("NVO", "2025Q3"): ("2025-11-05", "index used fool.com article date 2025-12-11; Novo reported 9M 2025 on 2025-11-05")}
JUNK_NAME = re.compile(r"^\d\d:\d\d:\d\d$| vs\. |^Forget |^Unknown|^Unidentified|^Analyst$|^Speaker \d|^Julianne$")


def demoji(s):
    try:
        return s.encode("latin-1").decode("utf-8") if "Ã" in s or "â" in s else s
    except Exception:
        return s.replace("\u202f", " ")


def build_maps():
    ex = {}
    for t, d in EXEC.items():
        for canon, al in d.items():
            for a in [canon] + al:
                ex[(t, a.lower())] = canon
    an = {}
    for canon, al in ANALYST.items():
        for a in [canon] + al:
            an[a.lower()] = canon
    fm = {}
    for canon, al in FIRM.items():
        for a in [canon] + al:
            fm[a.lower()] = canon
    return ex, an, fm


def roster_check():
    """Each canonical executive: does the surname appear in the company's own filings / releases / official transcripts?"""
    out = []
    for t, d in EXEC.items():
        docs = []
        for base in (ROOT / "data" / "corpus" / "companies" / t, ROOT / "data" / "moat" / "companies" / t):
            for p in base.rglob("*.md"):
                if "transcripts" in p.parts:
                    continue
                docs.append(p)
        texts = []
        for p in docs:
            try:
                texts.append((p, p.read_text(errors="replace")))
            except Exception:
                pass
        for canon, al in d.items():
            last = canon.split()[-1]
            firsts = {a.split()[0][:3] for a in [canon] + al}
            pat = re.compile(rf"\b({'|'.join(re.escape(f) for f in firsts)})\w*\.?(\s+[A-Z]\w*\.?){{0,2}}\s+{re.escape(last)}\b")
            hits = [p for p, s in texts if pat.search(s)]
            kinds = sorted({re.sub(r"[_\d-]+", "", p.stem)[:14] for p in hits})[:6]
            out.append({"ticker": t, "executive": canon, "found_in_company_docs": "yes" if hits else "no",
                        "n_docs": len(hits), "doc_kinds": ";".join(kinds), "example": str(hits[0].relative_to(ROOT)) if hits else ""})
    return out


def main():
    ex, an, fm = build_maps()
    rows = list(csv.DictReader((TAB / "qa_turns.csv").open()))
    idx = list(csv.DictReader((TAB / "transcripts_index.csv").open()))
    cross = list(csv.DictReader((V / "cross_source.csv").open())) if (V / "cross_source.csv").exists() else []
    roster = roster_check()
    with (V / "roster_check.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, list(roster[0]))
        w.writeheader()
        w.writerows(roster)
    # analyst firm evidence: per (canonical analyst, quarter) firms from clean rows
    seen = defaultdict(Counter)
    analyst_names = Counter()
    for r in rows:
        if r["role"] != "analyst":
            continue
        s = demoji(r["speaker"].strip())
        m = re.match(r"^(.*?), Analyst at (.+)$", s)
        firm = m.group(2) if m else demoji(r["firm"].strip())
        s = m.group(1) if m else s
        c = an.get(s.lower(), s)
        analyst_names[c] += 1
        if firm not in NOT_FIRM and len(firm) < 45:
            seen[(c, r["quarter"])][fm.get(firm.lower(), firm)] += 1

    def qnum(q):
        return int(q[:4]) * 4 + int(q[-1])

    def infer_firm(c, q, same_call):
        if same_call:
            return same_call.most_common(1)[0][0], "same analyst elsewhere in this call"
        best = None
        for (cc, qq), cnt in seen.items():
            if cc == c:
                d = abs(qnum(qq) - qnum(q))
                if best is None or d < best[0]:
                    best = (d, cnt.most_common(1)[0][0], qq)
        if best and best[0] <= 2:
            return best[1], f"same analyst on another call in {best[2]}"
        return "", ""

    # official-copy sentence check for calls with an official PDF
    off_text = {}
    for key, fn in OFFICIAL_COPY.items():
        p = SRC / fn
        if p.exists():
            off_text[key] = squash(" ".join(t["text"] for t in load("lseg_pdf", p)))

    out, fixes = [], Counter()
    for r in rows:
        t, q = r["ticker"], r["quarter"]
        s0 = r["speaker"]
        s = demoji(s0.strip())
        firm0 = demoji(r["firm"].strip())
        role0 = r["role"]
        notes = []
        m = None if (t, s.lower()) in ex else re.match(r"^(.*?), (?:Analyst at (.+)|(.+))$", s)
        if s in ("Analyst", "Unknown Analyst") and role0 == "analyst":
            row = dict(r)
            row.update({"speaker_verified": "", "role_verified": "analyst", "firm_verified": fm.get(firm0.lower(), "") if firm0 not in NOT_FIRM else "",
                        "verify_note": "analyst unnamed in source (placeholder label)"})
            fixes["analyst unnamed placeholder"] += 1
            out.append(row)
            continue
        if m and m.group(2):
            s, firm0 = m.group(1), m.group(2)
            notes.append("name field held 'Name, Analyst at Firm'; split")
        elif m and len(s) > 25 and (t, m.group(1).lower()) in ex:
            s = m.group(1)
            notes.append("title stripped from name field")
        speaker, role, firm = s, role0, firm0
        if (t, s.lower()) not in ex and (JUNK_NAME.search(s) or len(s.split()) > 6 or s[:1].islower() or s.endswith((".", "?", "!"))):
            speaker, role, firm = "", "unattributed", ""
            notes.append(f"speaker label '{s0[:40]}' is not a person (timestamp, sentence, headline or placeholder); text unattributable")
            fixes["unattributable speaker label"] += 1
        elif s.strip() == "Operator":
            role, firm = "operator", ""
            notes.append("operator was tagged executive")
            fixes["operator tagged as executive"] += 1
        elif (t, s.lower()) in ex:
            speaker, firm = ex[(t, s.lower())], CO[t]
            if speaker != s:
                notes.append(f"name normalized from '{s}'")
                fixes["executive name variant or misspelling"] += 1
            if role0 != "executive":
                role = "executive"
                notes.append(f"role fixed {role0}->executive ({speaker} is a {t} officer)")
                fixes["executive tagged as analyst"] += 1
        else:
            canon = an.get(s.lower(), s)
            if canon != s:
                notes.append(f"analyst name normalized from '{s}'")
                fixes["analyst name variant or ASR misspelling"] += 1
            speaker = canon
            if role0 == "executive":
                if canon in ANALYST or analyst_names[canon] >= 2:
                    role = "analyst"
                    notes.append(f"role fixed executive->analyst ({canon} is a sell-side analyst, not a {t} officer)")
                    fixes["analyst tagged as executive"] += 1
                    firm0 = ""
                else:
                    role = "executive_unverified"
                    notes.append(f"labeled executive but '{canon}' is not in the {t} officer roster")
                    fixes["unverified executive name"] += 1
            if role == "analyst":
                f = fm.get(firm0.lower(), firm0)
                if f in NOT_FIRM or len(f) >= 45 or f in CO.values() or f.lower() in ("kite", "alexion, astrazeneca rare disease", "johnson and johnson", "gilead sciences", "jujubank"):
                    same = Counter()
                    for (cc, qq), cnt in seen.items():
                        if cc == canon and qq == q:
                            same.update(cnt)
                    nf, how = infer_firm(canon, q, same)
                    if firm0 and len(firm0) >= 45:
                        notes.append("firm field held answer text (parser spill)")
                        fixes["firm field holds transcript text"] += 1
                    if nf:
                        notes.append(f"firm '{firm0[:30]}' -> '{nf}' inferred from {how}")
                        fixes["missing or placeholder analyst firm filled"] += 1
                    else:
                        notes.append("analyst firm unknown")
                    f = nf
                elif f != firm0:
                    fixes["firm name variant normalized"] += 1
                firm = f
                near = Counter()
                for (cc, qq), cnt in seen.items():
                    if cc == canon and abs(qnum(qq) - qnum(q)) <= 1:
                        near.update(cnt)
                if firm and near and firm not in near and near.most_common(1)[0][1] >= 2:
                    notes.append(f"firm '{firm}' conflicts with same analyst's firm on other calls this period ('{near.most_common(1)[0][0]}'); check")
                    fixes["analyst firm conflicts with other calls"] += 1
        row = dict(r)
        row.update({"speaker_verified": speaker, "role_verified": role, "firm_verified": firm})
        key = (t, q)
        if key in off_text and role == "executive":
            ss = [x for x in re.split(r"(?<=[.?!])\s+", r["text"]) if len(x.split()) >= 6]
            if t == "JNJ" and q == "2026Q2":
                pass
            elif ss:
                hit = sum(1 for x in ss if squash(x) in off_text[key])
                row["official_sentence_match_pct"] = round(100 * hit / len(ss), 1)
        row["verify_note"] = "; ".join(notes)
        out.append(row)

    # JNJ 2026Q2: replace spaceless official rows with the MarketBeat copy, sentence-checked against the official PDF
    jnj = [r for r in out if (r["ticker"], r["quarter"]) == ("JNJ", "2026Q2")]
    if (SRC / "JNJ_2026Q2_mb.html").exists() and ("JNJ", "2026Q2") in off_text:
        out = [r for r in out if (r["ticker"], r["quarter"]) != ("JNJ", "2026Q2")]
        mb = load("mb_html", SRC / "JNJ_2026Q2_mb.html")
        qa = next((i for i, x in enumerate(mb) if x["name"] == "Operator" and re.search(r"question", x["text"], re.I) and i > 2), 0)
        for x in mb[qa:]:
            if x.get("kind") not in ("analyst", "executive"):
                continue
            nm = demoji(x["name"])
            if x["kind"] == "executive":
                nm2 = ex.get(("JNJ", nm.lower()), nm)
                firm = CO["JNJ"]
            else:
                nm2 = an.get(nm.lower(), nm)
                rr = x.get("role", "")
                firm = fm.get(rr.rsplit(" at ", 1)[1].lower(), rr.rsplit(" at ", 1)[1]) if " at " in rr else ""
            ss = [y for y in re.split(r"(?<=[.?!])\s+", x["text"]) if len(y.split()) >= 6]
            hit = sum(1 for y in ss if squash(y) in off_text[("JNJ", "2026Q2")])
            out.append({"ticker": "JNJ", "quarter": "2026Q2", "speaker": nm, "role": x["kind"], "firm": firm, "text": x["text"],
                        "path": "data/moat/verified/calls/src/JNJ_2026Q2_mb.html", "page": "",
                        "speaker_verified": nm2, "role_verified": x["kind"], "firm_verified": firm,
                        "official_sentence_match_pct": round(100 * hit / len(ss), 1) if ss else "",
                        "verify_note": f"replaces {len(jnj)} spaceless LSEG rows; text from MarketBeat/Quartr, each sentence checked against the official LSEG PDF with spaces stripped"})
        fixes["JNJ 2026Q2 spaceless rows replaced by sentence-checked clean copy"] = len(jnj)

    # grades
    cs = {(c["ticker"], c["quarter"]): c for c in cross}
    by_call = defaultdict(list)
    for r in out:
        by_call[(r["ticker"], r["quarter"])].append(r)
    grades = []
    for i in idx:
        t, q = i["ticker"], i["quarter"]
        cr = cs.get((t, q))
        rs = by_call.get((t, q), [])
        unattr = sum(1 for r in rs if r["role_verified"] in ("unattributed", "executive_unverified"))
        g, why, quote_from = "C", "single third-party copy, speakers named", i["path"]
        if i["source_quality"] == "official" and i["format"] == "lseg":
            g, why = "A", "official LSEG/Refinitiv edited transcript from company IR"
        if (t, q) == ("JNJ", "2026Q2"):
            g, why = "A", ("original official PDF text lost its spaces (unquotable as stored); clean MarketBeat copy sentence-checked "
                           "against it; quote only rows with official_sentence_match_pct=100 or re-read the PDF")
            quote_from = "data/moat/verified/calls/src/JNJ_2026Q2_official.pdf (check) + src/JNJ_2026Q2_mb.html (text)"
        elif (t, q) in OFFICIAL_COPY and i["source_quality"] != "official":
            g = "A"
            why = (f"third-party copy matches official LSEG PDF on {cr['exec_word_agreement_pct']}% of executive words"
                   if cr else "official LSEG PDF fetched") + "; quote from the official PDF, not the third-party text"
            quote_from = f"data/moat/verified/calls/src/{OFFICIAL_COPY[(t, q)]}"
        elif cr and i["source_quality"] != "official":
            agree = float(cr.get("overlap_exec_agreement_pct") or cr.get("exec_word_agreement_pct") or 0)
            cov = float(cr.get("coverage_of_a_pct") or 0)
            if agree >= 90 and cov >= 80:
                g, why = "B", f"two independent third-party copies agree on {agree}% of executive words (coverage {cov}%)"
            else:
                why = f"second copy compared but weak: agreement {agree}% over {cov}% coverage; single-source"
        if i["n_qa_turns"] and int(i["n_qa_turns"]) < 15 and (t, q) != ("JNJ", "2026Q2"):
            g, why = "D", f"only {i['n_qa_turns']} Q&A turns recovered; speaker attribution unreliable"
        if rs and unattr / len(rs) > 0.25:
            g, why = "D", f"{unattr}/{len(rs)} Q&A rows unattributable"
        cd, cnote = DATE_FIX.get((t, q), (i["call_date"], ""))
        grades.append({"ticker": t, "quarter": q, "grade": g, "reason": why, "source_quality": i["source_quality"],
                       "source_url": i["source_url"], "path": i["path"], "quote_from": quote_from,
                       "call_date": i["call_date"], "call_date_verified": cd, "date_note": cnote,
                       "n_qa_rows": len(rs), "n_rows_unattributable": unattr,
                       "cross_check": f"{cr['source_a']} vs {cr['source_b']}" if cr else ""})
    gmap = {(g["ticker"], g["quarter"]): g["grade"] for g in grades}
    for r in out:
        r["grade"] = gmap.get((r["ticker"], r["quarter"]), "")
        ok_row = r["role_verified"] == "executive" and r["grade"] in ("A", "B")
        if (r["ticker"], r["quarter"]) == ("JNJ", "2026Q2"):
            ok_row = ok_row and r.get("official_sentence_match_pct") == 100.0
        r["quotable"] = "yes" if ok_row else "no"
    cols = ["ticker", "quarter", "speaker", "role", "firm", "speaker_verified", "role_verified", "firm_verified", "grade",
            "quotable", "official_sentence_match_pct", "verify_note", "text", "path", "page"]
    out.sort(key=lambda r: (r["ticker"], r["quarter"]))
    with (V / "qa_turns.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    gc = list(grades[0])
    with (V / "transcript_grades.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, gc)
        w.writeheader()
        w.writerows(grades)
    print("rows", len(out), "fixes", dict(fixes))
    per = defaultdict(Counter)
    for g in grades:
        per[g["ticker"]][g["grade"]] += 1
    for t in sorted(per):
        print(t, dict(sorted(per[t].items())))
    print("roster not found:", [(r["ticker"], r["executive"]) for r in roster if r["found_in_company_docs"] == "no"])
    with (V / "fix_counts.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fix", "count"])
        for k, v in fixes.most_common():
            w.writerow([k, v])


if __name__ == "__main__":
    main()
