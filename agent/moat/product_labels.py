"""DailyMed label version history: changed key sections per version + indication-count timeline."""
import csv
import difflib
import io
import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests
from lxml import etree

from agent.drug_pack import DRUGS, NS, section_text
from agent.moat.common import write, note_gap, OUT

DM = "https://dailymed.nlm.nih.gov/dailymed"
H = {"User-Agent": "Neeley AI Forward hackathon"}
ROOT = Path(__file__).resolve().parent.parent.parent
CACHE = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/spl_cache")
SECS = {"34067-9": "1 INDICATIONS", "34066-1": "BOXED WARNING", "34070-3": "4 CONTRAINDICATIONS",
        "43685-7": "5 WARNINGS AND PRECAUTIONS", "34071-1": "WARNINGS", "34068-7": "2 DOSAGE AND ADMINISTRATION"}
PRIORITY = ["keytruda", "opdivo", "imfinzi", "tecentriq", "eliquis", "xarelto", "ibrance", "verzenio", "kisqali",
            "vyndaqel", "vyndamax", "attruby", "amvuttra", "ozempic", "wegovy", "mounjaro", "zepbound", "foundayo",
            "januvia", "jardiance", "skyrizi", "rinvoq", "humira", "amjevita", "stelara", "wezlana", "tremfya",
            "cosentyx", "entyvio", "enbrel", "darzalex", "sarclisa", "tagrisso", "rybrevant", "lazcluze", "farxiga",
            "repatha", "praluent", "leqvio", "lipfendra", "biktarvy", "dovato", "cabenuva", "yeztugo", "apretude"]
ORDER = PRIORITY + [d for d in DRUGS if d not in PRIORITY]


def get(url, **kw):
    for i in range(3):
        try:
            r = requests.get(url, headers=H, timeout=120, **kw)
            r.raise_for_status()
            return r
        except Exception:
            if i == 2:
                raise


def setid_of(slug):
    t = (ROOT / "data/corpus/drugs" / slug / "label_sections.md").read_text(encoding="utf-8")[:600]
    return re.search(r"setid=([0-9a-f-]{36})", t).group(1)


def fetch_xml(setid, ver):
    f = CACHE / f"{setid}_{ver}.xml"
    if f.exists():
        return f.read_bytes()
    z = zipfile.ZipFile(io.BytesIO(get(f"{DM}/getFile.cfm", params={"setid": setid, "type": "zip", "version": ver}).content))
    name = next(n for n in z.namelist() if n.lower().endswith(".xml"))
    raw = z.read(name)
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_bytes(raw)
    return raw


def extract(raw):
    root = etree.fromstring(raw)
    out, ind_titles = {}, []
    for s in root.xpath("//v3:section[v3:code]", namespaces=NS):
        code = s.xpath("./v3:code/@code", namespaces=NS)[0]
        if code in SECS and SECS[code] not in out:
            out[SECS[code]] = section_text(s, 2)
            if code == "34067-9":
                for c in s.xpath("./v3:component/v3:section", namespaces=NS):
                    t = " ".join(c.xpath("./v3:title//text()", namespaces=NS)).strip()
                    if t:
                        ind_titles.append(t)
    if "1 INDICATIONS" in out and not ind_titles:
        ind_titles = [l.lstrip("- ")[:120] for l in out["1 INDICATIONS"].split("\n\n")[1:] if len(l) > 40]
    return out, ind_titles


def norm(t):
    return re.sub(r"\s+", " ", t).strip()


def sents(t):
    return [x.strip() for x in re.split(r"(?<=[.;:])\s+|\n+", t) if x.strip()]


def diff_excerpt(old, new):
    a, b = sents(old), sents(new)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    rem, add = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            rem += a[i1:i2]
        if tag in ("replace", "insert"):
            add += b[j1:j2]
    return " ".join(rem)[:700], " ".join(add)[:700]


def do_drug(slug):
    setid = setid_of(slug)
    hist = get(f"{DM}/services/v2/spls/{setid}/history.json").json()["data"]["history"]
    vers = sorted(hist, key=lambda h: h["spl_version"])
    chg, tl, docs = [], [], []
    prev = None
    for h in vers:
        v = h["spl_version"]
        d = datetime.strptime(h["published_date"], "%b %d, %Y").strftime("%Y-%m-%d")
        src = f"{DM}/getFile.cfm?setid={setid}&type=zip&version={v}"
        try:
            secs, titles = extract(fetch_xml(setid, v))
        except Exception as e:
            note_gap("product", slug, f"label v{v}", str(e))
            continue
        tl.append([slug, setid, v, d, len(titles), " | ".join(titles)[:1500], src, f"{setid}:v{v}"])
        changed = []
        if prev is not None:
            for sec in sorted(set(prev) | set(secs)):
                o, n = prev.get(sec), secs.get(sec)
                if o and n and norm(o) == norm(n):
                    continue
                if not o and not n:
                    continue
                if o and not n:
                    ct, (eo, en) = "removed", (norm(o)[:700], "")
                elif n and not o:
                    ct, (eo, en) = "added", ("", norm(n)[:700])
                else:
                    ct, (eo, en) = "modified", diff_excerpt(o, n)
                changed.append(sec)
                chg.append([slug, setid, v, d, sec, ct, eo, en, src, f"{setid}:v{v}:{sec}"])
        if changed:
            body = "".join(f"[[page {i} | printed {sec}]]\n\n{secs[sec]}\n\n" for i, sec in enumerate(
                [s for s in SECS.values() if s in secs], 1))
            docs.append((v, d, src, body, changed))
        prev = secs
    for v, d, src, body, changed in docs:
        write("product", f"drugs/{slug}/label_v{v}.md", f"<!-- changed sections: {', '.join(changed)}; effective {d} -->\n" + body,
              ticker=slug, group="drugs", doc_type="fda_label_version", period=d, source_url=src, upload=False)
    return chg, tl


def tocsv(rows, cols):
    f = io.StringIO()
    w = csv.writer(f)
    w.writerow(cols)
    w.writerows(rows)
    return f.getvalue()


def main():
    allc, allt = [], []
    with ThreadPoolExecutor(5) as ex:
        futs = {s: ex.submit(do_drug, s) for s in ORDER}
        for s, f in futs.items():
            try:
                c, t = f.result()
                allc += c
                allt += t
                print(s, len(t), len(c), flush=True)
            except Exception as e:
                note_gap("product", s, "label history", repr(e))
                print(s, "ERR", e, flush=True)
    write("product", "tables/label_changes.csv",
          tocsv(allc, ["drug", "setid", "version", "effective_date", "section", "change_type", "old_excerpt",
                       "new_excerpt", "source", "source_row"]), group="product", doc_type="table")
    write("product", "tables/indication_timeline.csv",
          tocsv(allt, ["drug", "setid", "version", "effective_date", "n_indications", "indications", "source",
                       "source_row"]), group="product", doc_type="table")
    print(len(allc), len(allt))


main()
