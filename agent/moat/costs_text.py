"""costs stream: merge XBRL rows with text-derived rows (headcount, advertising, sales force) into company_cost_structure.csv."""
import csv
import glob
import io
import re
from pathlib import Path

from agent.moat.common import note_gap, write

PAGE = re.compile(r"\[\[page (\d+)(?: \| printed ([^\]]+))?\]\]")
FILE = re.compile(r"(?:corpus|moat)/(?:companies|peers)/([A-Z]+)/(10k|20f)_FY(\d{4})")
NUM = r"(\d{1,3}(?:[ ,]\d{3})+)"
HC = [re.compile(rf"(?:had|employed|employs?|have|comprises?|workforce of|total headcount of|Total employees)\D{{0,40}}?{NUM}\s*(?:employees|people|colleagues|staff|full-time employees|permanent)?", re.I),
      re.compile(rf"approximately {NUM} staff members", re.I),
      re.compile(rf"{NUM} employees worldwide", re.I)]
ADV = re.compile(r"(?:Advertising (?:expenses|costs)(?: within[^$]{0,120})?|Global advertising expenses[^$]{0,120}|Advertising and product promotion costs[^$]{0,120}|recorded advertising and promotion expenses of)[^$]{0,200}?\$\s*([\d,.]+)\s*(billion|million)", re.I)
FORCE = re.compile(r"[^.]{0,120}?\b(\d{1,3}[ ,]\d{3})\s+full-time equivalent field force employees[^.]{0,80}")


CURATED = [
 ("ABBV",2021,50000,"corpus","moat/companies/ABBV/10k_FY2021.md",15,"AbbVie employed approximately 50,000 employees in over 70 countries as of January 31, 2022"),
 ("ABBV",2022,50000,"x","moat/companies/ABBV/10k_FY2022.md",14,"AbbVie employed approximately 50,000 employees in over 70 countries as of January 31, 2023"),
 ("ABBV",2023,50000,"x","moat/companies/ABBV/10k_FY2023.md",14,"AbbVie employed approximately 50,000 employees in over 70 countries as of January 31, 2024"),
 ("ABBV",2024,55000,"x","corpus/companies/ABBV/10k_FY2024.md",14,"AbbVie employed approximately 55,000 employees in over 70 countries as of January 31, 2025"),
 ("ABBV",2025,57000,"x","corpus/companies/ABBV/10k_FY2025.md",15,"AbbVie employed approximately 57,000 employees in over 70 countries as of December 31, 2025"),
 ("AMGN",2021,24200,"x","moat/companies/AMGN/10k_FY2021.md",28,"approximately 24,200 staff members in over 50 countries"),
 ("AMGN",2022,25200,"x","moat/companies/AMGN/10k_FY2022.md",28,"approximately 25,200 staff members in over 50 countries"),
 ("AMGN",2023,26700,"x","moat/companies/AMGN/10k_FY2023.md",31,"approximately 26,700 staff members in over 50 countries"),
 ("AMGN",2024,28000,"x","corpus/companies/AMGN/10k_FY2024.md",30,"approximately 28,000 staff members in over 50 countries"),
 ("AMGN",2025,31500,"x","corpus/companies/AMGN/10k_FY2025.md",31,"approximately 31,500 staff members in over 50 countries, including approximately 13,000 staff members outside the United States"),
 ("AZN",2021,83100,"x","moat/companies/AZN/20f_FY2021.md",108,"The number of people employed by the Group at the end of 2021 was 83,100"),
 ("AZN",2022,83500,"x","moat/companies/AZN/20f_FY2022.md",110,"The number of people employed by the Group at the end of 2022 was 83,500"),
 ("AZN",2023,89900,"x","moat/companies/AZN/20f_FY2023.md",114,"The number of people employed by the Group at the end of 2023 was 89,900"),
 ("AZN",2024,94300,"x","corpus/companies/AZN/20f_FY2024.md",111,"The number of people employed by the Group at the end of 2024 was 94,300"),
 ("AZN",2025,96100,"x","corpus/companies/AZN/20f_FY2025.md",107,"The number of people employed by the Group at the end of 2025 was 96,100"),
 ("BMY",2021,32200,"x","moat/companies/BMY/10k_FY2021.md",23,"As of December 31, 2021, we had approximately 32,200 employees in 45 countries"),
 ("BMY",2022,34300,"x","moat/companies/BMY/10k_FY2022.md",22,"As of December 31, 2022, we had approximately 34,300 employees in 44 countries"),
 ("BMY",2023,34100,"x","moat/companies/BMY/10k_FY2023.md",22,"As of December 31, 2023, we had approximately 34,100 employees in 43 countries"),
 ("BMY",2024,34100,"x","corpus/companies/BMY/10k_FY2024.md",23,"As of December 31, 2024, we had approximately 34,100 employees in 43 countries"),
 ("BMY",2025,32500,"x","corpus/companies/BMY/10k_FY2025.md",24,"As of December 31, 2025, we had approximately 32,500 employees in 43 countries"),
 ("GILD",2021,14400,"x","moat/companies/GILD/10k_FY2021.md",12,"As of December 31, 2021, Gilead had approximately 14,400 employees"),
 ("GILD",2022,17000,"x","moat/companies/GILD/10k_FY2022.md",13,"As of December 31, 2022, Gilead had approximately 17,000 employees"),
 ("GILD",2023,18000,"x","moat/companies/GILD/10k_FY2023.md",12,"As of December 31, 2023, Gilead had approximately 18,000 employees"),
 ("GILD",2024,17600,"x","corpus/companies/GILD/10k_FY2024.md",11,"As of December 31, 2024, Gilead had approximately 17,600 employees"),
 ("GILD",2025,17000,"x","corpus/companies/GILD/10k_FY2025.md",11,"As of December 31, 2025, Gilead had approximately 17,000 employees"),
 ("JNJ",2021,134500,"x","moat/companies/JNJ/10k_FY2021.md",7,"approximately 134,500 employees worldwide"),
 ("JNJ",2022,141700,"x","moat/companies/JNJ/10k_FY2022.md",7,"approximately 141,700 employees worldwide"),
 ("JNJ",2023,152700,"x","moat/companies/JNJ/10k_FY2023.md",7,"approximately 152,700 employees worldwide"),
 ("JNJ",2024,138100,"x","corpus/companies/JNJ/10k_FY2024.md",6,"approximately 138,100 employees worldwide"),
 ("JNJ",2025,138200,"x","corpus/companies/JNJ/10k_FY2025.md",6,"approximately 138,200 employees worldwide"),
 ("LLY",2021,35000,"x","moat/companies/LLY/10k_FY2021.md",20,"At the end of 2021, we employed approximately 35,000 people, including approximately 19,600 employees outside the U"),
 ("LLY",2022,39000,"x","moat/companies/LLY/10k_FY2022.md",21,"At the end of 2022, we employed approximately 39,000 people"),
 ("LLY",2023,43000,"x","moat/companies/LLY/10k_FY2023.md",22,"At the end of 2023, we employed approximately 43,000 people"),
 ("LLY",2024,47000,"x","corpus/companies/LLY/10k_FY2024.md",23,"At the end of 2024, we employed approximately 47,000 people"),
 ("LLY",2025,50000,"x","corpus/companies/LLY/10k_FY2025.md",24,"At the end of 2025, we employed approximately 50,000 people, including approximately 27,000 employees outside the U"),
 ("MRK",2021,68000,"x","moat/companies/MRK/10k_FY2021.md",25,"As of December 31, 2021, the Company had approximately 68,000 employees worldwide"),
 ("MRK",2022,69000,"x","moat/companies/MRK/10k_FY2022.md",22,"As of December 31, 2022, the Company had approximately 69,000 employees worldwide"),
 ("MRK",2023,72000,"x","moat/companies/MRK/10k_FY2023.md",23,"As of December 31, 2023, the Company had approximately 72,000 employees worldwide"),
 ("MRK",2024,75000,"x","corpus/companies/MRK/10k_FY2024.md",24,"As of December 31, 2024, the Company had approximately 75,000 employees worldwide"),
 ("MRK",2025,75000,"x","corpus/companies/MRK/10k_FY2025.md",25,"As of December 31, 2025, the Company had approximately 75,000 employees worldwide"),
 ("NVO",2021,48478,"x","moat/companies/NVO/20f_FY2021_d2.md",7,"48,478 employees worldwide"),
 ("NVO",2022,55185,"x","moat/companies/NVO/20f_FY2022_d2.md",93,"Total employees 55,185 48,478 45,323"),
 ("NVO",2024,77349,"x","corpus/companies/NVO/20f_FY2024_d2.md",15,"which now comprises 77,349 colleagues worldwide"),
 ("NVO",2025,69505,"x","corpus/companies/NVO/20f_FY2025_d2.md",1,"69,505 employees worldwide"),
 ("PFE",2021,79000,"x","moat/companies/PFE/10k_FY2021.md",17,"As of December 31, 2021, we employed approximately 79,000 people worldwide"),
 ("PFE",2022,83000,"x","moat/companies/PFE/10k_FY2022.md",17,"As of December 31, 2022, we employed approximately 83,000 people worldwide"),
 ("PFE",2023,88000,"x","moat/companies/PFE/10k_FY2023.md",21,"As of December 31, 2023, including Seagen colleagues, we employed approximately 88,000 people worldwide"),
 ("PFE",2024,81000,"x","corpus/companies/PFE/10k_FY2024.md",20,"As of December 31, 2024, we employed approximately 81,000 people worldwide"),
 ("PFE",2025,75000,"x","corpus/companies/PFE/10k_FY2025.md",21,"As of December 31, 2025, we employed approximately 75,000 people worldwide"),
 ("REGN",2025,15410,"x","corpus/peers/REGN/10k_FY2025.md",35,"As of December 31, 2025, we had 15,410 full-time employees"),
 ("ALNY",2025,2500,"x","corpus/peers/ALNY/10k_FY2025.md",38,"As of December 31, 2025, we employed approximately 2,500 full-time employees"),
 ("TAK",2024,49281,"x","corpus/peers/TAK/20f_FY2026.md",116,"As of March 31, 2024, 2025 and 2026, we had 49,281, 47,455 and 47,029 employees on a consolidated basis (FY ending Mar 2024)"),
 ("TAK",2025,47455,"x","corpus/peers/TAK/20f_FY2026.md",116,"As of March 31, 2024, 2025 and 2026, we had 49,281, 47,455 and 47,029 employees (FY ending Mar 2025)"),
 ("TAK",2026,47029,"x","corpus/peers/TAK/20f_FY2026.md",116,"As of March 31, 2024, 2025 and 2026, we had 49,281, 47,455 and 47,029 employees (FY ending Mar 2026)"),
]


def pages(f):
    txt = open(f, errors="ignore").read()
    parts = PAGE.split(txt)
    return [(parts[i], parts[i + 1], parts[i + 2]) for i in range(1, len(parts) - 2, 3)]


def src(f, pg, pr):
    return f"{f} p.{pg}" + (f" (printed {pr})" if pr else "")


def main():
    rows = []
    files = sorted(set(glob.glob("data/corpus/companies/*/*.md") + glob.glob("data/corpus/peers/*/*.md")
                       + glob.glob("data/moat/companies/*/*.md")))
    for f in files:
        m = FILE.search(f)
        if not m or "_d2" in f and "NVO" not in f:
            continue
        tk, form, fy = m.group(1), m.group(2), int(m.group(3))
        if not Path(f).exists():
            continue
        pg_list = pages(f)
        hits = [(pg, pr, ADV.search(body)) for pg, pr, body in pg_list]
        hits = [h for h in hits if h[2] and not re.search(r"risk|could|may ", h[2].group(0)[:80], re.I)]
        if hits:
            pg, pr, a = hits[-1]
            amt = float(a.group(1).replace(",", "").rstrip(".")) * (1e9 if a.group(2).lower() == "billion" else 1e6)
            rows.append({"ticker": tk, "group": "", "fiscal_year": fy, "metric": "advertising_text", "value": amt, "unit": "USD",
                         "concept": "text:advertising expense (first figure = filing FY)", "period_end": "", "form": form, "filed": "",
                         "page_cite": f"p.{pg}" + (f" printed {pr}" if pr else ""), "source": f, "source_row": f"{tk}|advertising|FY{fy}|p{pg}",
                         "note": " ".join(a.group(0).split())[:300]})
        for pg, pr, body in pg_list:
            fo = FORCE.search(body)
            if fo:
                rows.append({"ticker": tk, "group": "", "fiscal_year": fy, "metric": "field_force_fte", "value": int(re.sub(r"[ ,]", "", fo.group(1))), "unit": "FTE",
                             "concept": "text:field force employees", "period_end": "", "form": form, "filed": "", "page_cite": f"p.{pg}",
                             "source": f, "source_row": f"{tk}|field_force|FY{fy}|p{pg}", "note": " ".join(fo.group(0).split())[:300]})
                break
    for tk, fy, v, _g, path, pg, q in CURATED:
        rows.append({"ticker": tk, "group": "", "fiscal_year": fy, "metric": "headcount_text", "value": v, "unit": "employees",
                     "concept": "text:employees (10-K Item 1 / 20-F)", "period_end": "", "form": "", "filed": "", "page_cite": f"p.{pg}",
                     "source": "data/" + path, "source_row": f"{tk}|headcount|FY{fy}|p{pg}", "note": q})
    x = list(csv.DictReader(open("data/moat/tables/company_cost_structure_xbrl.csv")))
    for r in x:
        r.setdefault("note", "")
    allrows = x + rows
    cols = ["ticker", "group", "fiscal_year", "metric", "value", "unit", "concept", "period_end", "form", "filed", "page_cite", "note", "source", "source_row"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(allrows)
    write("costs", "tables/company_cost_structure.csv", buf.getvalue(), group="costs", doc_type="table", source_url="SEC XBRL + filings", upload=False)
    print(len(x), len(rows), len(allrows))
    for r in rows:
        if r["metric"] != "headcount_text":
            print(r["ticker"], r["fiscal_year"], r["metric"], r["value"], r["page_cite"])


main()
