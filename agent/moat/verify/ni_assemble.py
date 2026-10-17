"""New-indication rebuild, step 3: classify each supplement from its approval letter ('provides for' paragraph)
plus the section 1 diff, pick the pivotal trial from the section 14 diff, pull CT.gov dates, and stage the table at
/tmp/ni/assembled.csv. ni_write.py writes the outputs through common.write."""
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd
import pymupdf

from agent.moat.verify.cv_newind import MAKER
from agent.moat.verify.ni_build import ct_fields, ct_get, ct_search, months, norm, pdate, trials_in

LET = Path("/tmp/ni/letters")
STOP = set("""the of and for with to in a an or patients patient adult adults who have has is are be by on at as
this that from treatment use indication indications include including new your application supplemental biologics
license supplement provides provide proposes approved approval labeling prescribing information keytruda""".split())

NON = re.compile(r"dosing regimen|dosage regimen|new dos|dose |formulation|presentation|pre-?filled|autoinjector|"
                 r"on-?body|manufactur|pregnan|lactation|\bpllr\b|\bplr\b|vaccin|advertis|promotional|medication guide|"
                 r"storage|shelf|container|vial|infusion time|infusion rate|subcutaneous administration|interchangeab|"
                 r"safety (information|update|data)|warnings and precautions|adverse reactions section|"
                 r"long-term|three-year|four-year|five-year|radiographic data|update[sd]? (to )?the|revise the|"
                 r"regular approval|traditional approval|verif(y|ied|ication) (and describe )?(the )?clinical benefit|"
                 r"confirmatory|overall survival (data|results)|final (overall survival|os)|removal|remove|"
                 r"every (\d|six|four|three) weeks|q[2-6]w|weight-based|fixed dose|loading dose", re.I)
PED = re.compile(r"pediatric|paediatric|adolescent|children|years of age|years and older|aged \d|ages \d|"
                 r"down to|\d+ years", re.I)
EXT = re.compile(r"extend|expand|patient population|to include pediatric|lower the age|age range", re.I)
NEWIND = re.compile(r"new indication|an indication for|indication for the treatment|new indications|"
                    r"for the treatment of|for the (first-line|adjuvant|neoadjuvant|maintenance)|to reduce the risk|"
                    r"to improve|for use in|in combination with|as monotherapy|as a single agent|for the prevention|"
                    r"to slow|to delay|to lower|reduce (the )?risk", re.I)


def letter(appl, supp):
    p = LET / f"{appl}_{supp}.pdf"
    if not p.exists():
        return ""
    try:
        t = " ".join(pg.get_text() for pg in pymupdf.open(p))
    except Exception:  # noqa: BLE001
        return ""
    t = re.sub(r"\s+", " ", t)
    m = re.search(r"(provides? for|proposes?|request to supplement your [^.]{0,120}? to|is to)\s(.{0,450})", t, re.I)
    if not m:
        return ""
    s = m.group(0)
    cut = re.search(r"(APPROVAL & LABELING|We have completed|has been approved|have been approved)", s)
    return s[: cut.start()].strip() if cut else s


def toks(s):
    return {w for w in re.findall(r"[a-z][a-z0-9-]{2,}", (s or "").lower()) if w not in STOP}


def classify(p, add):
    """Return (supplement_type, reason)."""
    lp = p.lower()
    big_add = [a for a in add if a[3] < 0.85]
    newsec = any(a[4] for a in add)
    ped_ext = [a for a in add if a[3] >= 0.6 and PED.search(a[2])]
    if not p and ped_ext and len(ped_ext) == len(big_add or ped_ext) and not newsec:
        return "non_indication", "pediatric extension (section 1 sentence gained a pediatric age range)"
    if p:
        non = NON.search(p)
        ind = NEWIND.search(p) or "indication" in lp
        if re.search(r"regular approval|traditional approval|full approval|conversion|convert", lp) and \
                not re.search(r"new indication", lp):
            return "non_indication", "conversion of an accelerated approval (letter)"
        if PED.search(p) and EXT.search(p) and not re.search(r"new indication", lp):
            return "non_indication", "pediatric extension (letter)"
        if non and not re.search(r"new indication|expand the indication|an indication for|indication for the", lp):
            if not (ind and big_add and not re.search(r"dosing|dosage|formulation|presentation|manufactur", lp)):
                return "non_indication", f"letter: {non.group(0)}"
        if re.search(r"expand(ed|ing)? (the )?(indication|patient population)|broaden", lp):
            return "expanded_population", "letter: expand the indication"
        if ind:
            if newsec or re.search(r"new indication|an indication for", lp):
                return "new_indication", "letter names an indication; new label subsection" if newsec else "letter: new indication"
            if big_add:
                return "expanded_population", "letter names an indication; added sentence within an existing label subsection"
            return "new_indication" if not add else "expanded_population", "letter names an indication"
        return ("expanded_population" if big_add else "non_indication"), "letter not classifiable; decided by section 1 diff"
    if newsec:
        return "new_indication", "no letter text; new section 1 subsection"
    if big_add:
        return "expanded_population", "no letter text; new section 1 sentence"
    return "non_indication", "no letter text; section 1 unchanged"


def main():
    st = pd.read_csv("/tmp/ni/stage.csv")
    st["provides"] = [letter(a, s) for a, s in zip(st.appl_no, st.supplement_number)]
    recs = []
    for r in st.to_dict("records"):
        add = json.loads(r["s1_added"]) if isinstance(r.get("s1_added"), str) else []
        nt = json.loads(r["new_trials"]) if isinstance(r.get("new_trials"), str) else []
        typ, why = classify(r["provides"], add)
        r["supplement_type"], r["type_reason"] = typ, why
        # best indication sentence
        pt = toks(r["provides"])
        best = max(add, key=lambda a: (len(pt & toks(a[2])), a[4], -a[3]), default=None)
        r["indication_added"] = (best[2] if best else "")[:300]
        r["label_section"] = best[0] if best else ""
        r["_cands"] = nt
        recs.append(r)
    df = pd.DataFrame(recs)
    out = []
    for r in recs:
        r = dict(r)
        nt = r.pop("_cands")
        r.update(pivotal_nct="", pivotal_trial_name="", match_method="none", match_confidence="none", trial_note="")
        if r["supplement_type"] == "non_indication" or r["status"] != "diffed":
            if r["status"] != "diffed":
                r["trial_note"] = r.get("note", "")
            out.append(r)
            continue
        # resolve name-only candidates via CT.gov acronym search
        for c in nt:
            if not c.get("nct") and c.get("name") and r["generic"]:
                hits = ct_search(c["name"], r["generic"])
                if len(hits) == 1:
                    c["nct"], c["via"] = hits[0], "label_s14_name_ctgov"
        nt = [c for c in nt if c.get("nct")]
        A = date.fromisoformat(r["approval_date"])
        pt = toks(r["provides"]) | toks(r["indication_added"])
        lt = toks(r["provides"])
        grp = df[(df.drug == r["drug"]) & (df.version == r["version"]) & (df.supplement_type != "non_indication")]
        letter_pick = None
        if len(lt) >= 4:
            pool = window_cands(r["setid"], A)
            if pool:
                sc = sorted(pool, key=lambda c: len(lt & toks(c["ctx"])), reverse=True)
                top = len(lt & toks(sc[0]["ctx"]))
                second = len(lt & toks(sc[1]["ctx"])) if len(sc) > 1 and sc[1]["nct"] != sc[0]["nct"] else -1
                if top >= 4 and top > second:
                    letter_pick = dict(sc[0], letter_score=top, letter_margin=top - second)
        if not nt and not letter_pick:
            r["trial_note"] = "section 14 diff names no new trial with a resolvable NCT"
            out.append(r)
            continue

        def score(c):
            ctx = SPL_CTX(r, c)
            return (len(pt & toks(ctx)), c.get("new_sec", False))
        fresh = [c for c in nt if c.get("fresh", True)]
        ranked = sorted(fresh or nt, key=score, reverse=True) + ([c for c in nt if c not in fresh] if fresh else [])
        if letter_pick:
            ranked = [letter_pick] + [x for x in ranked if x["nct"] != letter_pick["nct"]]
        c = ranked[0]
        d = ct_get(c["nct"])
        f = ct_fields(d) if d else {}
        s, pc = pdate(f.get("start_date")), pdate(f.get("primary_completion_date"))
        r.update(pivotal_nct=c["nct"], pivotal_trial_name=c.get("name") or f.get("acronym") or "",
                 match_method="label_s14_nct" if c["via"].startswith("label_s14_nct") else c["via"],
                 enrollment=f.get("enrollment"), start_date=f.get("start_date"),
                 primary_completion_date=f.get("primary_completion_date"),
                 months_start_to_completion=months(s, pc) if s and pc else None,
                 months_completion_to_approval=months(pc, A) if pc else None,
                 ct_sponsor=f.get("sponsor"), ct_title=f.get("title"), ct_phase=f.get("phases"),
                 s14_section=c["sec"], s14_heading=c["head"], s14_version=c.get("version", r["version"]), n_candidates=len(nt),
                 other_candidates=";".join(x["nct"] for x in ranked[1:6]), group_n=len(grp))
        problems = []
        if not c.get("fresh", True):
            problems.append("trial already named elsewhere in the prior label (section renamed or re-used)")
        if c["via"] != "label_s14_nct":
            problems.append(f"NCT via {c['via']}")
        if letter_pick:
            r["letter_score"] = letter_pick["letter_score"]
        if len(grp) > 1 and not letter_pick:
            problems.append(f"{len(grp)} indication supplements share label v{int(r['version'])}")
        if letter_pick and abs((date.fromisoformat(letter_pick["eff"]) - A).days) > 60:
            problems.append(f"label version {(date.fromisoformat(letter_pick['eff']) - A).days} days from approval")
        if not letter_pick and abs(r["lag_days"]) > 30:
            problems.append(f"label version {int(r['lag_days'])} days from approval")
        if pc and pc > A:
            r["months_start_to_completion"] = None
            r["months_completion_to_approval"] = None
            r["months_note"] = ("CT.gov primary completion postdates approval (approval rested on an interim analysis; "
                                "CT.gov date was updated to the final analysis); months withheld")
        if not letter_pick and r["provides"] and len(lt) >= 4:
            problems.append("approval letter text does not match the trial's section 14 context")
        GEN = {"cancer", "carcinoma", "tumor", "tumors", "metastatic", "advanced", "solid", "previously", "treated",
               "untreated", "study", "trial", "phase", "randomized", "versus", "placebo", "combination",
               "participants", "subjects", "efficacy", "safety", "first-line", "chemotherapy", "disease", "active",
               "moderate", "severe", "moderately", "severely", "recurrent", "unresectable", "locally", "adjuvant",
               "plus", "alone", "compared", "standard", "care", "therapy", "pediatric", "years", "age", "older"}
        ct_t = toks(f.get("title", "") + " " + f.get("conditions", "")) - GEN
        if lt and not (lt - GEN) & ct_t:
            problems.append("CT.gov title and conditions share no disease term with the approval letter")
        mk = MAKER.get(r["drug"], "")
        if mk and f.get("sponsor") and not re.search(mk, f["sponsor"], re.I):
            problems.append(f"CT.gov sponsor {f['sponsor']}")
        if not letter_pick and len(ranked) > 1 and ranked[1].get("fresh", True) and score(ranked[0])[0] == score(ranked[1])[0] \
                and ranked[0]["sec"] != ranked[1]["sec"]:
            problems.append("tie between candidate trials")
        r["match_confidence"] = "plausible" if problems else "pivotal_confirmed"
        r["trial_note"] = "; ".join(problems)
        out.append(r)
    pd.DataFrame(out).to_csv("/tmp/ni/assembled.csv", index=False)
    o = pd.DataFrame(out)
    print(o.supplement_type.value_counts(), o.match_confidence.value_counts(), sep="\n")


SPLD = json.loads(Path("/tmp/ni/spl_parsed.json").read_text())


def window_cands(sid, A):
    """Trials first named in section 14 by any label version effective from 10 days before to 200 days after A."""
    vers = sorted(((int(k), v) for k, v in SPLD.get(sid, {}).items()), key=lambda x: (x[1]["eff"], x[0]))
    seen, out = set(), []
    for i, (vn, v) in enumerate(vers):
        cur = {}
        for sec, (head, t) in v["s14"].items():
            for n, k in trials_in(t):
                cur.setdefault(k, (sec, head, n, t))
        prev_heads = {norm(h) for h, _ in vers[i - 1][1]["s14"].values()} if i > 0 else set()
        if i > 0:
            dd = (date.fromisoformat(v["eff"]) - A).days
            if -10 <= dd <= 200:
                for sec, (head, t) in v["s14"].items():
                    if norm(head) not in prev_heads:
                        for n, k in trials_in(t):
                            if k in seen:
                                j = t.find(k)
                                out.append({"sec": sec, "head": head, "name": n, "nct": k, "via": "label_s14_nct",
                                            "fresh": True, "reused": True, "version": vn, "eff": v["eff"],
                                            "ctx": head + " " + head + " " + t[max(0, j - 700): j + 300]})
            if -10 <= dd <= 200:
                for k, (sec, head, n, t) in cur.items():
                    if k not in seen:
                        j = t.find(k)
                        out.append({"sec": sec, "head": head, "name": n, "nct": k, "via": "label_s14_nct",
                                    "fresh": True, "version": vn, "eff": v["eff"],
                                    "ctx": head + " " + t[max(0, j - 700): j + 300]})
        seen |= set(cur)
    return out


def SPL_CTX(r, c):
    if c.get("ctx"):
        return c["ctx"]
    v = SPLD.get(r["setid"], {}).get(str(int(r["version"])), {})
    head, t = v.get("s14", {}).get(c["sec"], ["", ""])
    i = t.find(c["nct"]) if c.get("nct") else -1
    return head + " " + (t[max(0, i - 500): i + 300] if i >= 0 else t[:800])


if __name__ == "__main__":
    main()
