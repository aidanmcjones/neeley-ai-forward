"""Per-drug fine-print pack for every product named in the Fine Print case appendix.

For each drug: the manufacturer's current FDA label from DailyMed (SPL XML split into numbered sections such as
"5.2 Bleeding", which is how labels are cited), and that drug's rows from the bulk FDA / CMS files agent/public_data.py downloads
into data/external/ (Orange Book products, patents and exclusivity; Purple Book incl. biosimilars that reference
it; Paragraph IV challenges; IRA negotiation list and maximum fair price; Medicare Part D and Part B spending).
Writes data/corpus/drugs/<drug>/ and appends to data/corpus/manifest.jsonl.

Usage:
  python -m agent.public_data      # once, for data/external/
  python -m agent.drug_pack
  python -m agent.drug_pack --drugs eliquis,xarelto
"""

import argparse
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from lxml import etree

from agent.corpus import Manifest

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "data" / "external"
OUT = ROOT / "data" / "corpus" / "drugs"
DM = "https://dailymed.nlm.nih.gov/dailymed"
NS = {"v3": "urn:hl7-org:v3"}

# slug: (DailyMed search name, labeler regex for the maker's own SPL, ingredient for Orange/Purple Book, case company)
DRUGS = {
    "keytruda": ("KEYTRUDA", r"MERCK", "PEMBROLIZUMAB", "MRK"),
    "keytruda-qlex": ("KEYTRUDA QLEX", r"MERCK", "PEMBROLIZUMAB", "MRK"),
    "januvia": ("JANUVIA", r"MERCK", "SITAGLIPTIN", "MRK"),
    "janumet": ("JANUMET", r"MERCK", "SITAGLIPTIN", "MRK"),
    "lipfendra": ("LIPFENDRA", r"MERCK", "ENLICITIDE", "MRK"),
    "opdivo": ("OPDIVO", r"SQUIBB", "NIVOLUMAB", "BMY"),
    "opdivo-qvantig": ("OPDIVO QVANTIG", r"SQUIBB", "NIVOLUMAB", "BMY"),
    "eliquis": ("ELIQUIS", r"SQUIBB", "APIXABAN", "BMY"),
    "ibrance": ("IBRANCE", r"PFIZER", "PALBOCICLIB", "PFE"),
    "vyndaqel": ("VYNDAQEL", r"PFIZER|FOLDRX", "TAFAMIDIS", "PFE"),
    "vyndamax": ("VYNDAMAX", r"PFIZER|FOLDRX", "TAFAMIDIS", "PFE"),
    "mounjaro": ("MOUNJARO", r"LILLY", "TIRZEPATIDE", "LLY"),
    "zepbound": ("ZEPBOUND", r"LILLY", "TIRZEPATIDE", "LLY"),
    "trulicity": ("TRULICITY", r"LILLY", "DULAGLUTIDE", "LLY"),
    "verzenio": ("VERZENIO", r"LILLY", "ABEMACICLIB", "LLY"),
    "foundayo": ("FOUNDAYO", r"LILLY", "ORFORGLIPRON", "LLY"),
    "ozempic": ("OZEMPIC", r"NOVO", "SEMAGLUTIDE", "NVO"),
    "wegovy": ("WEGOVY", r"NOVO", "SEMAGLUTIDE", "NVO"),
    "rybelsus": ("RYBELSUS", r"NOVO", "SEMAGLUTIDE", "NVO"),
    "skyrizi": ("SKYRIZI", r"ABBVIE", "RISANKIZUMAB", "ABBV"),
    "rinvoq": ("RINVOQ", r"ABBVIE", "UPADACITINIB", "ABBV"),
    "humira": ("HUMIRA", r"ABBVIE", "ADALIMUMAB", "ABBV"),
    "stelara": ("STELARA", r"JANSSEN|JOHNSON", "USTEKINUMAB", "JNJ"),
    "tremfya": ("TREMFYA", r"JANSSEN|JOHNSON", "GUSELKUMAB", "JNJ"),
    "darzalex": ("DARZALEX", r"JANSSEN|JOHNSON", "DARATUMUMAB", "JNJ"),
    "darzalex-faspro": ("DARZALEX FASPRO", r"JANSSEN|JOHNSON", "DARATUMUMAB", "JNJ"),
    "xarelto": ("XARELTO", r"JANSSEN|JOHNSON", "RIVAROXABAN", "JNJ"),
    "rybrevant": ("RYBREVANT", r"JANSSEN|JOHNSON", "AMIVANTAMAB", "JNJ"),
    "lazcluze": ("LAZCLUZE", r"JANSSEN|JOHNSON", "LAZERTINIB", "JNJ"),
    "tagrisso": ("TAGRISSO", r"ASTRAZENECA", "OSIMERTINIB", "AZN"),
    "farxiga": ("FARXIGA", r"ASTRAZENECA", "DAPAGLIFLOZIN", "AZN"),
    "imfinzi": ("IMFINZI", r"ASTRAZENECA", "DURVALUMAB", "AZN"),
    "repatha": ("REPATHA", r"AMGEN", "EVOLOCUMAB", "AMGN"),
    "enbrel": ("ENBREL", r"AMGEN|IMMUNEX", "ETANERCEPT", "AMGN"),
    "amjevita": ("AMJEVITA", r"AMGEN", "ADALIMUMAB", "AMGN"),
    "wezlana": ("WEZLANA", r"AMGEN|NUVAILA", "USTEKINUMAB", "AMGN"),
    "biktarvy": ("BIKTARVY", r"GILEAD", "BICTEGRAVIR", "GILD"),
    "yeztugo": ("YEZTUGO", r"GILEAD", "LENACAPAVIR", "GILD"),
    # rival products
    "tecentriq": ("TECENTRIQ", r"GENENTECH|ROCHE", "ATEZOLIZUMAB", "Roche"),
    "jardiance": ("JARDIANCE", r"BOEHRINGER", "EMPAGLIFLOZIN", "Boehringer/Lilly"),
    "kisqali": ("KISQALI", r"NOVARTIS", "RIBOCICLIB", "NVS"),
    "cosentyx": ("COSENTYX", r"NOVARTIS", "SECUKINUMAB", "NVS"),
    "leqvio": ("LEQVIO", r"NOVARTIS", "INCLISIRAN", "NVS"),
    "entyvio": ("ENTYVIO", r"TAKEDA", "VEDOLIZUMAB", "TAK"),
    "sarclisa": ("SARCLISA", r"SANOFI|AVENTIS", "ISATUXIMAB", "SNY"),
    "praluent": ("PRALUENT", r"REGENERON|SANOFI", "ALIROCUMAB", "REGN"),
    "attruby": ("ATTRUBY", r"BRIDGEBIO|EIDOS", "ACORAMIDIS", "BBIO"),
    "amvuttra": ("AMVUTTRA", r"ALNYLAM", "VUTRISIRAN", "ALNY"),
    "dovato": ("DOVATO", r"VIIV", "DOLUTEGRAVIR", "GSK"),
    "cabenuva": ("CABENUVA", r"VIIV", "CABOTEGRAVIR", "GSK"),
    "apretude": ("APRETUDE", r"VIIV", "CABOTEGRAVIR", "GSK"),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def get(url, **kw):
    r = requests.get(url, timeout=90, headers={"User-Agent": "Neeley AI Forward hackathon"}, **kw)
    r.raise_for_status()
    return r


# ---------------------------------------------------------------- DailyMed label

def find_setid(name, labeler):
    """The maker's own SPL (not a repackager's), newest first. Exact brand match before broader titles."""
    data = get(f"{DM}/services/v2/spls.json", params={"drug_name": name, "pagesize": 100}).json()["data"]
    mine = [d for d in data if re.search(labeler, d["title"].rsplit("[", 1)[-1], re.I)]
    exact = [d for d in mine if re.match(rf"{re.escape(name)}\b(?! (QLEX|QVANTIG|FASPRO))", d["title"], re.I)]
    pool = exact or mine
    pool.sort(key=lambda d: datetime.strptime(d["published_date"], "%b %d, %Y"), reverse=True)
    return pool[0] if pool else None


def section_text(sec, depth=2):
    title = " ".join(sec.xpath("./v3:title//text()", namespaces=NS)).strip()
    code = sec.xpath("./v3:code/@displayName", namespaces=NS)
    body = []
    for t in sec.xpath("./v3:text", namespaces=NS):
        for el in t.iter():
            tag = etree.QName(el).localname if isinstance(el.tag, str) else ""
            if tag in ("paragraph", "item", "tr", "caption"):
                line = " ".join(" ".join(el.itertext()).split())
                if line:
                    body.append(("- " if tag == "item" else "") + line)
    out = []
    if title or code:
        out.append(f"{'#' * min(depth, 6)} {title or code[0]}")
    out += body
    for child in sec.xpath("./v3:component/v3:section", namespaces=NS):
        out.append(section_text(child, depth + 1))
    return "\n\n".join(x for x in out if x)


def label_markdown(xml, meta):
    root = etree.fromstring(xml)
    secs = root.xpath("//v3:structuredBody/v3:component/v3:section", namespaces=NS)
    head = (f"<!-- source: {DM}/drugInfo.cfm?setid={meta['setid']}\n     title: {meta['title']}\n"
            f"     spl_version: {meta['spl_version']}  published: {meta['published_date']}  retrieved: {now()} -->\n\n")
    return head + "\n\n".join(section_text(s) for s in secs) + "\n"


# ---------------------------------------------------------------- bulk slices

class Bulk:
    def __init__(self):
        z = zipfile.ZipFile(EXT / "orange_book.zip")
        rd = lambda n: pd.read_csv(z.open(n), sep="~", dtype=str)
        self.ob_products, self.ob_patents, self.ob_excl = rd("products.txt"), rd("patent.txt"), rd("exclusivity.txt")
        rows, header = [], None
        for line in (EXT / "purple_book_2026_09.csv").read_text(encoding="utf-8", errors="replace").splitlines():
            cells = next(iter(pd.read_csv(io.StringIO(line), header=None, dtype=str).values.tolist()), [])
            if cells and cells[0] == "N/R/U":
                header = cells
            elif header and len(cells) == len(header) and isinstance(cells[1], str):
                rows.append(dict(zip(header, cells)))
        self.purple = pd.DataFrame(rows)
        self.p4 = pd.read_excel(EXT / "paragraph_iv.xlsx", header=1, dtype=str)
        iz = zipfile.ZipFile(EXT / "ira_selected_drugs_mfp.zip")
        self.ira = pd.read_csv(iz.open(next(n for n in iz.namelist() if n.endswith(".csv"))), dtype=str)
        self.partd = pd.read_csv(EXT / "partd_spending_dy24.csv", dtype=str)
        self.partb = pd.read_csv(EXT / "partb_spending_dy24.csv", dtype=str)

    @staticmethod
    def match(df, cols, pattern):
        cols = [c for c in cols if c in df.columns]
        mask = pd.Series(False, index=df.index)
        for c in cols:
            mask |= df[c].fillna("").str.contains(pattern, case=False, regex=True)
        return df[mask]

    def slices(self, brand, ingredient):
        b = rf"\b{re.escape(brand.split()[0])}\b"
        prods = self.match(self.ob_products, ["Trade_Name"], b)
        appl = set(prods["Appl_No"])
        return {
            "orange_book_products.csv": prods,
            "orange_book_patents.csv": self.ob_patents[self.ob_patents["Appl_No"].isin(appl)],
            "orange_book_exclusivity.csv": self.ob_excl[self.ob_excl["Appl_No"].isin(appl)],
            "purple_book.csv": self.match(self.purple, ["Proprietary Name", "Ref. Product Proprietary Name",
                                                        "Proper Name"], rf"{b}|\b{ingredient}\b"),
            "paragraph_iv.csv": self.match(self.p4, list(self.p4.columns[:4]), b),
            "ira_negotiation.csv": self.match(self.ira, list(self.ira.columns), b),
            "medicare_partd_spending.csv": self.match(self.partd, ["Brnd_Name"], b),
            "medicare_partb_spending.csv": self.match(self.partb, ["Brnd_Name", "HCPCS_Desc"], b),
        }


# ---------------------------------------------------------------- run

def write(manifest, slug, rel, data: bytes, source, doc_type, company, quality="official"):
    path = OUT / slug / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    manifest.add({"doc_id": f"drug:{slug}:{rel}", "ticker": company, "group": "drugs", "doc_type": doc_type,
                  "form": None, "filed": None, "period": None, "accession": None, "source_url": source,
                  "retrieved_at": now(), "path": str(path.relative_to(ROOT)).replace("\\", "/"), "pages": None,
                  "pages_with_folio": None, "chars": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                  "source_quality": quality, "sections": None})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drugs")
    a = ap.parse_args()
    manifest = Manifest(ROOT / "data" / "corpus" / "manifest.jsonl")
    bulk = Bulk()
    slugs = a.drugs.lower().split(",") if a.drugs else list(DRUGS)
    missing = []
    for slug in slugs:
        name, labeler, ingredient, company = DRUGS[slug]
        try:
            meta = find_setid(name, labeler)
            if meta:
                xml = get(f"{DM}/services/v2/spls/{meta['setid']}.xml").content
                # labels are cited by section number ("5.2 Bleeding"); DailyMed redirects scripted PDF downloads
                write(manifest, slug, "label_sections.md", label_markdown(xml, meta).encode("utf-8"),
                      f"{DM}/drugInfo.cfm?setid={meta['setid']}", "fda_label", company)
            else:
                missing.append(f"{slug}: no DailyMed SPL from labeler /{labeler}/")
        except Exception as e:
            missing.append(f"{slug}: DailyMed error {e}")
        for rel, df in bulk.slices(name, ingredient).items():
            if len(df):
                write(manifest, slug, rel, df.to_csv(index=False).encode(), f"data/external ({rel})",
                      "drug_reference_data", company)
        print(f"{slug}: {'label ok' if meta else 'NO LABEL'}")
    (OUT / "_missing.txt").write_text("\n".join(missing) + "\n", encoding="utf-8")
    print("missing:", *missing, sep="\n  ")


if __name__ == "__main__":
    main()
