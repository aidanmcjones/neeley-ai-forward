"""Verify label_changes.csv and indication_timeline.csv against the cached SPL XML for each cited version.

Independent of the collector's renderer: section text is rebuilt from raw XML text nodes, compared with all
whitespace removed, and markdown markers / the "SPL UNCLASSIFIED SECTION" display name (not label text) stripped.
"""
import csv
import json
import re
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[3]
CACHE = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/spl_cache")
OUTD = ROOT / "data/moat/verified/product"
NS = {"v3": "urn:hl7-org:v3"}
SECS = {"34067-9": "1 INDICATIONS", "34066-1": "BOXED WARNING", "34070-3": "4 CONTRAINDICATIONS",
        "43685-7": "5 WARNINGS AND PRECAUTIONS", "34071-1": "WARNINGS", "34068-7": "2 DOSAGE AND ADMINISTRATION"}
APPENDIX = ["keytruda", "keytruda-qlex", "opdivo", "opdivo-qvantig", "imfinzi", "tecentriq", "januvia", "janumet",
            "ozempic", "jardiance", "eliquis", "xarelto", "ibrance", "verzenio", "kisqali", "vyndaqel", "vyndamax",
            "amvuttra", "mounjaro", "zepbound", "trulicity", "wegovy", "rybelsus", "skyrizi", "rinvoq", "tremfya",
            "stelara", "cosentyx", "entyvio", "humira", "amjevita", "wezlana", "darzalex", "darzalex-faspro",
            "sarclisa", "tagrisso", "rybrevant", "lazcluze", "farxiga", "repatha", "praluent", "leqvio", "enbrel",
            "biktarvy", "dovato", "cabenuva", "yeztugo", "apretude"]
_xml = {}


def load(setid, v):
    k = (setid, v)
    if k not in _xml:
        f = CACHE / f"{setid}_{v}.xml"
        _xml[k] = etree.fromstring(f.read_bytes()) if f.exists() else None
    return _xml[k]


def meta(root):
    g = lambda p: (root.xpath(p, namespaces=NS) or [""])[0]
    return {"eff": g("/v3:document/v3:effectiveTime/@value"), "setid": g("/v3:document/v3:setId/@root"),
            "ver": g("/v3:document/v3:versionNumber/@value")}


def sections(root):
    out = {}
    for s in root.xpath("//v3:section[v3:code]", namespaces=NS):
        code = s.xpath("./v3:code/@code", namespaces=NS)[0]
        if code in SECS and SECS[code] not in out:
            out[SECS[code]] = s
    return out


def raw_text(sec):
    """All label text in the section (titles + text nodes), excluding code displayNames."""
    parts = []
    for el in sec.iter():
        if not isinstance(el.tag, str):
            continue
        if etree.QName(el).localname in ("title", "text"):
            parts.append(" ".join(el.itertext()))
    return " ".join(parts)


def strip_markup(t):
    t = t.replace("SPL UNCLASSIFIED SECTION", " ")
    t = re.sub(r"(^|\s)#{1,6}(?=\s)", " ", t)
    t = re.sub(r"(^|\s)-(?=\s)", " ", t)
    return t


def squash(t):
    return re.sub(r"\s+", "", t)


def loose(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


def frags(excerpt):
    t = strip_markup(excerpt)
    pieces = re.split(r"(?<=[.;:])\s+", t)
    return [p for p in (squash(x) for x in pieces) if len(p) >= 4]


def coverage(excerpt, target):
    """Greedy: fraction of the excerpt's characters covered by verbatim chunks (>=8 chars) of the target."""
    ex, tg = squash(strip_markup(excerpt)), squash(target)
    if not ex:
        return 1.0, ""
    pos, hit, first_miss = 0, 0, ""
    while pos < len(ex):
        lo, hi = 0, len(ex) - pos
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if ex[pos:pos + mid] in tg:
                lo = mid
            else:
                hi = mid - 1
        if lo >= 8 or (lo > 0 and pos + lo == len(ex)):
            hit += lo
            pos += lo
        else:
            first_miss = first_miss or ex[pos:pos + 60]
            pos += max(lo, 1)
    return hit / len(ex), first_miss


def prev_version(setid, v):
    vs = sorted(int(p.stem.split("_")[1]) for p in CACHE.glob(f"{setid}_*.xml"))
    lower = [x for x in vs if x < v]
    return lower[-1] if lower else None


def sents(t):
    return [x.strip() for x in re.split(r"(?<=[.;:])\s+", re.sub(r"\s+", " ", t)) if len(x.strip()) > 3]


def sentence_diff(old, new):
    so, sn = sents(old), sents(new)
    lo, ln = {loose(x) for x in so}, {loose(x) for x in sn}
    return [x for x in sn if loose(x) not in lo], [x for x in so if loose(x) not in ln]


def verify_changes():
    rows = list(csv.DictReader(open(ROOT / "data/moat/tables/label_changes.csv")))
    out, stats, key = [], {}, []
    for r in rows:
        setid, v, sec = r["setid"], int(r["version"]), r["section"]
        note, status = [], "verified"
        cur = load(setid, v)
        pv = prev_version(setid, v)
        prev = load(setid, pv) if pv else None
        if cur is None:
            r.update(verify_status="dropped", verify_note="SPL version not in cache; cannot verify")
            out.append(r)
            continue
        m = meta(cur)
        if m["setid"] != setid or m["ver"] != str(v):
            status = "dropped"
            note.append(f"XML setid/version mismatch {m['setid']} v{m['ver']}")
        eff = f"{m['eff'][:4]}-{m['eff'][4:6]}-{m['eff'][6:8]}"
        if eff != r["effective_date"]:
            note.append(f"effective_date {r['effective_date']} is DailyMed published date; SPL effectiveTime is {eff}")
            r["dailymed_published_date"] = r["effective_date"]
            r["effective_date"] = eff
            status = "fixed"
        cs, ps = sections(cur), (sections(prev) if prev is not None else {})
        nt = raw_text(cs[sec]) if sec in cs else ""
        ot = raw_text(ps[sec]) if sec in ps else ""
        dn = set(cur.xpath("//v3:section/v3:code/@displayName", namespaces=NS))
        if prev is not None:
            dn |= set(prev.xpath("//v3:section/v3:code/@displayName", namespaces=NS))
        ne, oe = r["new_excerpt"], r["old_excerpt"]
        for x in sorted(dn, key=len, reverse=True):
            ne, oe = ne.replace(f"# {x}", "# "), oe.replace(f"# {x}", "# ")
        cn, mn = coverage(ne, nt)
        co, mo = coverage(oe, ot)
        r["prev_version"] = pv or ""
        if not frags(r["new_excerpt"]) and not frags(r["old_excerpt"]):
            status = "dropped"
            note.append("excerpts contain only headings/markup (no label text): renderer artifact")
        elif nt and ot and loose(nt) == loose(ot):
            status = "dropped"
            note.append(f"section text identical to v{pv} after removing whitespace/punctuation/markup: formatting-only change")
        elif cn < 0.90 or co < 0.90:
            status = "dropped"
            note.append(f"excerpt not verbatim in SPL: new {cn:.0%} found in v{v}, old {co:.0%} found in v{pv}; "
                        f"first unmatched: {(mn or mo)[:60]}")
        else:
            note.append(f"old excerpt verbatim in SPL v{pv} ({co:.0%}), new excerpt verbatim in SPL v{v} ({cn:.0%}), "
                        "whitespace-normalized" + ("; unmatched remainder is table-cell ordering, quote tables from the "
                                                   "SPL directly" if min(cn, co) < 0.97 else ""))
        r["verify_status"], r["verify_note"] = status, "; ".join(note)
        stats[status] = stats.get(status, 0) + 1
        out.append(r)
        if (status != "dropped" and r["drug"] in APPENDIX and r["section"] in ("BOXED WARNING", "1 INDICATIONS")
                and r["effective_date"] >= "2023-01-01"):
            add, rem = sentence_diff(ot, nt)
            key.append({"drug": r["drug"], "setid": setid, "version": v, "prev_version": pv,
                        "effective_date": r["effective_date"], "section": sec,
                        "sentences_added": " || ".join(add)[:2500], "sentences_removed": " || ".join(rem)[:2500],
                        "source": r["source"], "prev_source": r["source"].replace(f"version={v}", f"version={pv}")})
    cols = list(rows[0].keys()) + ["prev_version", "dailymed_published_date", "verify_status", "verify_note"]
    with open(OUTD / "label_changes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols, restval="")
        w.writeheader()
        w.writerows(out)
    (OUTD / "_label_key_raw.json").write_text(json.dumps(key, indent=1))
    print("label_changes", stats, "key", len(key))
    return stats


def count_inds(sec):
    subs = sec.xpath("./v3:component/v3:section", namespaces=NS)
    return [" ".join(" ".join(c.xpath("./v3:title//text()", namespaces=NS)).split()) for c in subs]


def verify_timeline():
    rows = list(csv.DictReader(open(ROOT / "data/moat/tables/indication_timeline.csv")))
    stats = {}
    for r in rows:
        cur = load(r["setid"], int(r["version"]))
        note, status = [], "verified"
        if cur is None:
            r.update(verify_status="dropped", verify_note="SPL version not in cache")
            stats["dropped"] = stats.get("dropped", 0) + 1
            continue
        m = meta(cur)
        eff = f"{m['eff'][:4]}-{m['eff'][4:6]}-{m['eff'][6:8]}"
        if eff != r["effective_date"]:
            note.append(f"effective_date {r['effective_date']} is DailyMed published date; SPL effectiveTime is {eff}")
            r["dailymed_published_date"] = r["effective_date"]
            r["effective_date"] = eff
            status = "fixed"
        sec = sections(cur).get("1 INDICATIONS")
        titles = [t for t in count_inds(sec) if t] if sec is not None else []
        if titles and len(titles) != int(r["n_indications"]):
            note.append(f"n_indications {r['n_indications']} but XML has {len(titles)} titled subsections")
            r["n_indications"] = len(titles)
            status = "fixed"
        if not titles:
            note.append("no titled 1.x subsections; n_indications is a paragraph-count heuristic, use with care")
        r["n_indications_note"] = ("count of 1.x subsections (one subsection can hold several tumor types or "
                                   "settings); not a count of FDA-approved indications") if titles else "heuristic"
        r["verify_status"], r["verify_note"] = status, "; ".join(note) or "date and subsection count match SPL XML"
        stats[status] = stats.get(status, 0) + 1
    cols = list(rows[0].keys())
    for c in ["dailymed_published_date", "n_indications_note", "verify_status", "verify_note"]:
        if c not in cols:
            cols.append(c)
    with open(OUTD / "indication_timeline.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols, restval="")
        w.writeheader()
        w.writerows(rows)
    print("indication_timeline", stats)


if __name__ == "__main__":
    OUTD.mkdir(parents=True, exist_ok=True)
    verify_changes()
    verify_timeline()
