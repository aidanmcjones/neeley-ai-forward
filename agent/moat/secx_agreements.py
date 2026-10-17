import re, html
from agent.moat.secx_lib import *

PRODUCTS = {
    "MRK": "Keytruda|pembrolizumab|Januvia|Janumet|sitagliptin|enlicitide|Lipfendra|Welireg|Gardasil|Lynparza|Lenvima|Verquvo",
    "BMY": "Eliquis|apixaban|Opdivo|nivolumab|Ono|Pfizer|Camzyos|Cobenfy|Karuna|Breyanzi|Abecma",
    "PFE": "Ibrance|palbociclib|Vyndaqel|tafamidis|Seagen|Padcev|Comirnaty|Paxlovid|Metsera|Xtandi",
    "LLY": "Mounjaro|Zepbound|tirzepatide|Trulicity|dulaglutide|orforglipron|Foundayo|Jardiance|empagliflozin|Boehringer|Verzenio",
    "NVO": "semaglutide|Ozempic|Wegovy|Rybelsus|insulin",
    "ABBV": "Skyrizi|risankizumab|Rinvoq|upadacitinib|Humira|adalimumab|Imbruvica|Janssen|Genmab|Botox",
    "JNJ": "Stelara|ustekinumab|Tremfya|guselkumab|Darzalex|daratumumab|Genmab|Rybrevant|Lazcluze|Xarelto|Imbruvica|Carvykti|Legend",
    "AZN": "Tagrisso|osimertinib|Farxiga|dapagliflozin|Imfinzi|durvalumab|Daiichi|Enhertu|Lynparza|Ultomiris",
    "AMGN": "Enbrel|etanercept|Repatha|evolocumab|MariTide|Otezla|Prolia|Tezspire|Pfizer",
    "GILD": "Biktarvy|bictegravir|Yeztugo|lenacapavir|Sunlenca|Trodelvy|Veklury|Arcus|Galapagos|Kite|Janssen",
}
TITLE_OK = re.compile(r"licen[sc]e|collaborat|acquisition|merger|purchase|development|commercializ|supply|distribut|"
                      r"settlement|royalt|co-?promotion|agreement and plan|option|asset|joint venture|partnership|agreement", re.I)
TITLE_NO = re.compile(r"credit|indenture|notes|employment|severance|retention|incentive|stock|compensation|deferred|"
                      r"change in control|director|award|registration rights|time sharing|non-compete|underwrit|morgan stanley|pension|(?<!and )plan(?! of)|executive|loan|facility|underwriting|commercial paper|"
                      r"supplemental|trust|bylaws|certificate|consulting|separation", re.I)
DATE = re.compile(r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}")


def exhibits(raw, base, cik):
    out = []
    for tr in re.split(r"(?i)<tr\b", raw)[1:]:
        tr = tr.split("</tr>")[0]
        cells = [html.unescape(re.sub(r"<[^>]+>", " ", c)) for c in re.split(r"(?i)</td>", tr)]
        cells = [" ".join(c.split()) for c in cells]
        cells = [c for c in cells if c]
        joined = " ".join(cells)
        m = re.match(r"^[>\s\(\)\*,†‡#]*(?:\(\d+\)\s*)?((?:10|4)(?:\.\d+|\([a-z0-9]+\)|[a-z]{1,2}\.))", joined)
        if not cells or not m:
            continue
        num = m.group(1)
        href = re.search(r'(?i)href="([^"]+\.(?:htm|html|txt))"', tr)
        if not href:
            continue
        h = href.group(1)
        if h.startswith("http"):
            url = h
        elif h.startswith("/"):
            url = "https://www.sec.gov" + h
        else:
            url = base + h
        am = re.search(r'(?is)<a\b[^>]*href="[^"]+"[^>]*>(.*?)</a>', tr)
        desc = max([c.lstrip("> ") for c in cells], key=len)
        if len(desc) < 25 and am:
            desc = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", am.group(1))).split())
        d = DATE.findall(joined)
        out.append({"exhibit": num, "title": desc[:400], "agreement_date": d[0] if d else "", "url": url,
                    "row_text": " ".join(cells)[:700]})
    return out


def acc_year(url):
    m = re.search(r"/data/\d+/(\d{10})(\d{2})(\d{6})/", url)
    if not m:
        return None
    yy = int(m.group(2))
    return 1900 + yy if yy > 80 else 2000 + yy


def main():
    allrows, fetched = [], 0
    for t, cik in ciks().items():
        _, fs = filings(cik, "2024-01-01")
        ann = [f for f in fs if f["form"] in ("10-K", "20-F")][-2:]
        seen, rows = set(), []
        for f in ann:
            base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{f['accession'].replace('-', '')}/"
            try:
                raw = sec_get(base + f["primary_doc"])
            except Exception as e:
                note_gap("secx", t, f"exhibit index {f['accession']}", repr(e))
                continue
            for e in exhibits(raw, base, cik):
                if e["url"] in seen:
                    continue
                seen.add(e["url"])
                e.update(ticker=t, from_filing=f["accession"], from_filed=f["filed"], form=f["form"],
                         year=acc_year(e["url"]))
                rows.append(e)
        # keep license/collaboration/acquisition style agreements
        keep = [r for r in rows if TITLE_OK.search(r["title"]) and not TITLE_NO.search(r["title"])]
        print(t, len(rows), "exhibits", len(keep), "agreements", flush=True)
        n = 0
        for r in keep:
            r["path"], r["product_hits"] = "", ""
            prod_title = re.search(PRODUCTS[t], r["title"] + " " + r["row_text"], re.I)
            if r["year"] and (r["year"] >= 2022 or prod_title) and n < 25:
                try:
                    raw = sec_get(r["url"])
                except Exception as e:
                    note_gap("secx", t, f"agreement {r['url']}", repr(e))
                    continue
                hits = sorted(set(m.lower() for m in re.findall(PRODUCTS[t], raw[:600000], re.I)))
                r["product_hits"] = ";".join(hits)
                if hits or r["year"] >= 2022:
                    slug = re.sub(r"[^A-Za-z0-9]+", "_", r["exhibit"] + "_" + r["title"][:50]).strip("_")
                    rel = f"companies/{t}/agreements/{r['year']}_{slug}.md"
                    save_doc(rel, r["url"], raw, t, "material_agreement",
                             {"form": r["form"], "filed": str(r["year"]), "period": r["agreement_date"]})
                    r["path"] = "data/moat/" + rel
                    n += 1
        allrows += keep
        write_csv("tables/material_agreements.csv",
                  ["ticker", "exhibit", "title", "agreement_date", "year", "form", "from_filed", "url", "product_hits", "path"],
                  allrows)


if __name__ == "__main__":
    main()
