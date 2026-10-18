"""verified/secx/agreements_checked.csv (keep/drop per collector row) and agreement_terms.csv (public economics, cited)."""
import csv
import re

from agent.moat.verify.s_write import out

SRC = "data/moat/tables/material_agreements.csv"
rows = list(csv.DictReader(open(SRC)))


def classify(r):
    t = r["title"].lower()
    if re.search(r"resignation, appointment and acceptance", t):
        return "drop", "debt trustee succession under the indenture (Exhibit 4.3), not a commercial agreement"
    if re.search(r"agreement between amgen inc\. and james bradner|transition services and general release|employee proprietary information", t):
        return "drop", "executive employment / separation / employee form agreement, not a product or license agreement"
    if "kenvue" in t or "johnson & johnson consumer inc" in t:
        return "keep (separation)", "Kenvue consumer separation IP/trademark agreement; not a pharma license, keep only for spin-off context"
    if "share purchase agreement" in t:
        return "keep (equity)", "BeiGene equity stake tied to the oncology collaboration"
    if re.search(r"collaboration|co-development|license|letter agreement", t):
        return "keep", "product collaboration or license"
    return "review", ""


chk = []
for r in rows:
    c, why = classify(r)
    chk.append(dict(ticker=r["ticker"], exhibit=r["exhibit"], title=r["title"][:220], agreement_date=r["agreement_date"],
                    from_filed=r["from_filed"], verdict=c, reason=why, redaction="yes" if re.search(r"omitted|†", r["title"]) else "not stated in title",
                    url=r["url"], path=r["path"]))
print({v: sum(1 for x in chk if x["verdict"] == v) for v in {x["verdict"] for x in chk}}, len(chk))

A = "data/moat/companies/BMY/agreements/2016_10b_Amended_and_Restated_Co_Development_and_Co_Promoti.md"
A2 = "data/moat/companies/BMY/agreements/2016_10c_Second_Amendment_to_Amended_and_Restated_Co_Develo.md"
A4 = "data/moat/companies/BMY/agreements/2016_10d_Fourth_Amendment_to_Amended_and_Restated_Co_Develo.md"
K = "data/corpus/companies/BMY/10k_FY2025.md"
J = "data/corpus/companies/JNJ/10k_FY2025.md"
TC = ["agreement", "term", "value", "redacted", "pdf_page", "printed_page", "quote", "quote_file", "note"]
T = [
    dict(agreement="BMY-Pfizer Eliquis (apixaban) co-development and co-promotion, 2007 A&R", term="Upfront payment Pfizer to BMS",
         value="$250,000,000", redacted="no", pdf_page=117, printed_page=106, quote_file=A,
         quote="COLLABORATOR shall pay to BMS a nonrefundable, noncreditable payment of Two Hundred Fifty Million Dollars ($250,000,000)"),
    dict(agreement="BMY-Pfizer Eliquis", term="Net profit / net loss split", value="50% / 50% worldwide (ex Japan unless option exercised)",
         redacted="no", pdf_page=123, printed_page=112, quote_file=A,
         quote="each Party shall receive fifty percent (50%) of all Net Profit and bear fifty percent (50%) of all Net Loss, as applicable, with respect to each Product in the Territory"),
    dict(agreement="BMY-Pfizer Eliquis", term="Development cost share (apixaban)", value="BMS 40% / Pfizer 60%",
         redacted="no", pdf_page=76, printed_page=65, quote_file=A,
         quote="shared by the Parties so that BMS bears forty percent (40%) and COLLABORATOR bears sixty percent (60%) of such costs.",
         note="10-K FY2025 says Pfizer funds 50%-60% depending on study"),
    dict(agreement="BMY-Pfizer Eliquis", term="Apixaban milestones (NDA acceptance, US launch, MAA acceptance, EU launch, by indication)",
         value="amounts not public", redacted="yes ([*] in table)", pdf_page=118, printed_page=107, quote_file=A,
         quote="Commencement of Phase III Clinical Trials for Prevention of Major Adverse Cardiovascular Events in Acute Coronary Syndrome [*] [*] [*] [*]",
         note="milestone grid redacted under confidential treatment; collector text layer lost the table cells"),
    dict(agreement="BMY-Pfizer Eliquis", term="Milestones for New Collaboration Compounds (VTE, AF stroke, ACS)", value="amounts not public",
         redacted="yes", pdf_page=121, printed_page=110, quote_file=A, quote="(in millions) (in millions) (in millions) [*] [*] [*] [*]"),
    dict(agreement="BMY-Pfizer Eliquis, Second Amendment (2012)", term="Pfizer Exclusive Territory: Pfizer pays BMS compensation on net sales",
         value="rate redacted", redacted="yes", pdf_page=11, printed_page=11, quote_file=A2,
         quote="total compensation with respect to sales of the Apixaban Product calculated each PFIZER Quarter equal to [*]."),
    dict(agreement="BMY-Pfizer Eliquis, Fourth Amendment (2015)", term="Pfizer 2015 Exclusive Territory: tiered rate on aggregate annual net sales",
         value="tiers and rates redacted", redacted="yes", pdf_page=11, printed_page=11, quote_file=A4,
         quote="total compensation with respect to sales of the Apixaban Product calculated each PFIZER Quarter equal to [*] according to the following table:"),
    dict(agreement="BMY-Pfizer Eliquis (10-K description)", term="Current public summary", value="profits and losses shared equally except Pfizer-only countries (sales-based fee / cost plus % of net price)",
         redacted="no", pdf_page=87, printed_page=85, quote_file=K,
         quote="Profits and losses are shared equally on a global basis except in certain countries where Pfizer commercializes Eliquis and pays BMS a sales-based fee."),
    dict(agreement="JNJ-Genmab Darzalex license", term="Royalty rate", value="12% to 20% of total Darzalex net sales", redacted="agreement not filed",
         pdf_page=8, printed_page=3, quote_file=J, quote="Royalty rate ranges from 12% to 20% of total DARZALEX net sales.",
         note="disclosed only after SEC comment letter 2025-04-16; J&J declined to file the agreement as an exhibit"),
    dict(agreement="JNJ-Genmab Darzalex license", term="Royalties paid", value="~$2.4B (FY2025), ~$2.0B (FY2024)", redacted="agreement not filed",
         pdf_page=8, printed_page=3, quote_file=J, quote="For the fiscal 2025 and 2024, royalty amounts to Genmab were approximately $2.4 billion and $2.0 billion, respectively."),
    dict(agreement="JNJ-Genmab Darzalex license", term="Term (patent expiry of licensed families)", value="US 2029; Europe 2031/2032 in select countries",
         redacted="agreement not filed", pdf_page=8, printed_page=3, quote_file=J,
         quote="The two patent families both expire in the United States in 2029, and in Europe, compound/use patent protection in select countries extends to 2031/2032."),
]

if __name__ == "__main__":
    out("agreements_checked.csv", list(chk[0].keys()), chk, f"derived: {SRC}")
    out("agreement_terms.csv", TC, T, "derived: BMS 10-Q 2016 exhibits 10c-10e (EDGAR), BMS and J&J FY2025 10-K")
