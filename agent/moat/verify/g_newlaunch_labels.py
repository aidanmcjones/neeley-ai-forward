"""Label version rows for the 2026 launches (Lipfendra, Foundayo), verified at creation against the SPL XML.

For each DailyMed version (history.json): version 1 (earliest) gets a row change_type="initial approval" with the
indications text, boxed warning yes/no and the Drugs@FDA ORIG-1 approval date. Each later version gets one row per
changed key section (same sections and diff rule as agent/moat/product_labels.py), or one "no key-section change"
row so every version is represented. Rows use the exact 18-column header of verified/product/label_changes.csv.

python -m agent.moat.verify.g_newlaunch_labels           # write label_changes_new_launches.csv
python -m agent.moat.verify.g_newlaunch_labels --append  # also append into verified label_changes.csv (backup kept)
"""
import csv
import difflib
import io
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import requests
from lxml import etree

from agent.drug_pack import NS, section_text
from agent.moat.verify.g_fetch import get

ROOT = Path(__file__).resolve().parents[3]
VD = ROOT / "data/moat/verified/product"
CACHE = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/spl_cache")
DM = "https://dailymed.nlm.nih.gov/dailymed"
SECS = {"34067-9": "1 INDICATIONS", "34066-1": "BOXED WARNING", "34070-3": "4 CONTRAINDICATIONS",
        "43685-7": "5 WARNINGS AND PRECAUTIONS", "34071-1": "WARNINGS", "34068-7": "2 DOSAGE AND ADMINISTRATION"}
LAUNCHES = {  # slug: (setid, NDA)
    "lipfendra": ("100ec543-fbd0-44fc-b740-db9cdff39145", "NDA220848"),
    "foundayo": ("8ac446c5-feba-474f-a103-23facb9b5c62", "NDA220934"),
}


def xml(setid, v):
    f = CACHE / f"{setid}_{v}.xml"
    if not f.exists():
        r = requests.get(f"{DM}/getFile.cfm", params={"setid": setid, "type": "zip", "version": v}, timeout=120,
                         headers={"User-Agent": "Neeley AI Forward research"})
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        CACHE.mkdir(parents=True, exist_ok=True)
        f.write_bytes(z.read(next(n for n in z.namelist() if n.lower().endswith(".xml"))))
    return etree.fromstring(f.read_bytes())


def secs(root):
    out = {}
    for s in root.xpath("//v3:section[v3:code]", namespaces=NS):
        code = s.xpath("./v3:code/@code", namespaces=NS)[0]
        if code in SECS and SECS[code] not in out:
            out[SECS[code]] = section_text(s, 2)
    return out


def tops(root):
    out = {}
    for sec in root.xpath("//v3:structuredBody/v3:component/v3:section", namespaces=NS):
        code = (sec.xpath("./v3:code/@code", namespaces=NS) or ["?"])[0]
        title = " ".join(sec.xpath("./v3:title//text()", namespaces=NS)).strip()[:60] or "untitled"
        out[f"{title} ({code})"] = re.sub(r"\s+", " ", " ".join(sec.itertext())).strip()
    return out


def norm(t):
    return re.sub(r"\s+", " ", t).strip()


def sents(t):
    return [x.strip() for x in re.split(r"(?<=[.;:])\s+|\n+", t) if x.strip()]


def diff_excerpt(old, new):
    a, b = sents(old), sents(new)
    rem, add = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag in ("replace", "delete"):
            rem += a[i1:i2]
        if tag in ("replace", "insert"):
            add += b[j1:j2]
    return " ".join(rem)[:700], " ".join(add)[:700]


def squash(t):
    return re.sub(r"[\s#*_|-]+", "", t)


def approval(nda):
    d = get(f'https://api.fda.gov/drug/drugsfda.json?search=application_number:"{nda}"', as_json=True)["results"][0]
    subs = d["submissions"]
    orig = next(s for s in subs if s["submission_type"] == "ORIG" and s["submission_status"] == "AP")
    supp = sorted((s["submission_status_date"], s["submission_number"], s.get("submission_class_code_description", ""))
                  for s in subs if s["submission_type"] == "SUPPL" and s["submission_status"] == "AP")
    iso = lambda x: f"{x[:4]}-{x[4:6]}-{x[6:]}"
    return iso(orig["submission_status_date"]), orig.get("review_priority", ""), [(iso(a), n, c) for a, n, c in supp]


def build():
    with (VD / "label_changes.csv").open(newline="") as f:
        header = next(csv.reader(f))
    rows, checks = [], []
    for slug, (setid, nda) in LAUNCHES.items():
        hist = get(f"{DM}/services/v2/spls/{setid}/history.json", as_json=True)["data"]["history"]
        appr, prio, supps = approval(nda)
        prev, prev_v, prev_tp = None, "", {}
        for i, h in enumerate(sorted(hist, key=lambda h: h["spl_version"])):
            v = h["spl_version"]
            pub = datetime.strptime(h["published_date"], "%b %d, %Y").strftime("%Y-%m-%d")
            root = xml(setid, v)
            eff = root.xpath("/v3:document/v3:effectiveTime/@value", namespaces=NS)[0][:8]
            eff = f"{eff[:4]}-{eff[4:6]}-{eff[6:]}"
            assert root.xpath("/v3:document/v3:setId/@root", namespaces=NS)[0] == setid
            assert int(root.xpath("/v3:document/v3:versionNumber/@value", namespaces=NS)[0]) == v
            s = secs(root)
            tp = tops(root)
            src = f"{DM}/getFile.cfm?setid={setid}&type=zip&version={v}"
            out = []
            if i == 0:
                bw = ("yes (" + norm(s["BOXED WARNING"]).lstrip("# ").split(" In ")[0][:80] + ")") if s.get("BOXED WARNING") else "no"
                ind = norm(s.get("1 INDICATIONS", ""))
                note = (f"version 1 of {len(hist)} on DailyMed (SPL version {v}); initial approval {appr} "
                        f"({nda} ORIG-1 AP, {prio} review, Drugs@FDA via api.fda.gov); boxed_warning={bw}; "
                        f"SPL effectiveTime {eff}; indications text verbatim from SPL v{v} (whitespace-normalized)")
                out.append(["1 INDICATIONS", "initial approval", "", ind[:700], note])
                checks.append((slug, v, "1 INDICATIONS", ind[:700], s.get("1 INDICATIONS", "")))
            else:
                changed = []
                for sec in sorted(set(prev) | set(s)):
                    o, n = prev.get(sec), s.get(sec)
                    if (o and n and norm(o) == norm(n)) or (not o and not n):
                        continue
                    if o and not n:
                        ct, (eo, en) = "removed", (norm(o)[:700], "")
                    elif n and not o:
                        ct, (eo, en) = "added", ("", norm(n)[:700])
                    else:
                        ct, (eo, en) = "modified", diff_excerpt(o, n)
                    changed.append(sec)
                    note = (f"SPL effectiveTime {eff}, DailyMed published {pub}; old excerpt from SPL v{prev_v}, new "
                            f"excerpt from SPL v{v}; Drugs@FDA labeling supplements AP: "
                            + "; ".join(f"S-{n} {a} {c}" for a, n, c in supps))
                    out.append([sec, ct, eo, en, note])
                    checks.append((slug, v, sec, en, n or ""))
                if not changed:
                    other = [k for k in sorted(set(prev_tp) | set(tp)) if prev_tp.get(k) != tp.get(k)]
                    out.append(["(key sections)", "no key-section change", "", "",
                                f"SPL v{v} effectiveTime {eff}, DailyMed published {pub}: sections "
                                f"{', '.join(SECS.values())} identical to v{prev_v}; sections that did change: "
                                f"{'; '.join(other) or 'none'}; Drugs@FDA labeling supplements AP: "
                                + "; ".join(f"S-{n} {a} {c}" for a, n, c in supps)])
            for sec, ct, eo, en, note in out:
                vals = dict(drug=slug, setid=setid, version=v, effective_date=eff, section=sec, change_type=ct,
                            old_excerpt=eo, new_excerpt=en, source=src, source_row=f"{setid}:v{v}:{sec}",
                            dailymed_published_date=pub, prev_version=prev_v, verify_status="verified_at_source",
                            verify_note=note)
                rows.append([vals[c] for c in header])
            prev, prev_v, prev_tp = s, v, tp
    # every new excerpt must appear in its cited SPL section text (whitespace and markdown markers ignored)
    for slug, v, sec, en, full in checks:
        for x in sents(en):
            assert squash(x)[:150] in squash(full), (slug, v, sec, x[:80])
    return header, rows


def main():
    header, rows = build()
    out = VD / "label_changes_new_launches.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(out, len(rows))
    for r in rows:
        print(r[:6], r[13][:160])
    if "--append" in sys.argv:
        main_f = VD / "label_changes.csv"
        bak = VD / "label_changes_before_new_launches.csv"
        if not bak.exists():
            shutil.copy2(main_f, bak)
        with bak.open(newline="") as f:
            base = list(csv.reader(f))
        assert base[0] == header
        base = [r for r in base if r[0] not in LAUNCHES]
        with main_f.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerows(base + rows)
        print("appended", len(rows), "to", main_f, "total data rows", len(base) - 1 + len(rows))


if __name__ == "__main__":
    main()
