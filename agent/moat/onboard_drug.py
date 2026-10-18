"""Onboard any branded drug into the moat dataset with one command.

  python -m agent.moat.onboard_drug "Dupixent" [--vs "tralokinumab,lebrikizumab"] [--rivals 4] [--budget 20]
                                               [--skip step1,step2] [--no-index]

Steps (logged to data/moat/onboard/drug_<slug>/steps.jsonl; failures record a gap and the run continues):
  identify     Orange/Purple Book row (applicant, ingredient, application number, modality) and the owner ticker
  label        DailyMed SPL for the applicant's own label (agent.drug_pack.find_setid), section-marked markdown
  versions     DailyMed SPL version history for that setid
  reference    Orange Book products/patents/exclusivity, Purple Book, Paragraph IV, IRA rows (agent.drug_pack.Bulk)
  pricing      Medicare Part D and Part B 2024 spend rows, NADAC 2024 to 2026, Medicaid SDUD national 2023 to 2025
  policy       mentions in the saved government documents (CMS IRA, White House MFN, tariff)
  rivals       competitive set: --vs, else same ATC class (RxClass), else same FDA EPC class, ranked by Medicare spend
  head_to_head ClinicalTrials.gov trials and PubMed RCT / meta-analyses naming the drug and each rival
  open_payments only if the rx stream ships an Open Payments module (agent.moat.rx_open_payments); else a gap
  index        python -m agent.moat.index --add, then the coverage summary (agent.moat.progress.onboard_drug_buckets)
"""

import argparse
import importlib.util
import json
import re
import time

from agent.moat import onboard_lib as L
from agent.moat.common import OUT


class Drug:
    def __init__(self, brand, a):
        self.brand = brand.strip()
        self.slug = L.slug(self.brand)
        self.a = a
        self.run = L.Run(f"drug_{self.slug}", a.budget, "drug")
        self.info = {"brand": self.brand, "slug": self.slug}
        self.rivals = []
        self.bulk = None

    @property
    def ingredient(self):
        return self.info.get("ingredient") or ""

    def owner_ticker(self, applicant):
        from agent.moat.index import COMPANY
        names = dict(COMPANY)
        for p in (OUT / "onboard").glob("*/profile.json"):
            d = json.loads(p.read_text())
            names[d["ticker"]] = d["name"]
            for al in d.get("aliases", [])[:1]:
                if re.search(rf"\b{re.escape(al)}\b", str(applicant), re.I):
                    return d["ticker"]
        for t, n in names.items():
            if re.search(rf"\b{re.escape(L.company_key(n))}\b", str(applicant), re.I):
                return t
        return ""

    def identify(self):
        row = L.product_for_brand(self.brand)
        if row:
            self.info.update(row)
        self.info["ticker"] = self.owner_ticker(self.info.get("applicant", "")) if row else ""
        return self.info

    def label(self):
        from agent import drug_pack as DP
        labeler = re.escape(L.company_key(self.info.get("applicant") or "")[:6]) if self.info.get("applicant") else "."
        meta = DP.find_setid(self.brand.upper(), labeler) or (DP.find_setid(self.brand.upper(), ".") if labeler != "." else None)
        if not meta:
            raise RuntimeError(f"no DailyMed SPL for {self.brand} (labeler /{labeler}/)")
        self.info.update(setid=meta["setid"], spl_title=meta["title"], spl_version=meta["spl_version"],
                         published=meta["published_date"])
        if not self.ingredient:
            m = re.search(r"\(([^)]+)\)", meta["title"])
            self.info["ingredient"] = m.group(1).lower() if m else ""
        xml = DP.get(f"{DP.DM}/services/v2/spls/{meta['setid']}.xml").content
        md = DP.label_markdown(xml, meta)
        heads = len(re.findall(r"^#{1,4} ", md, re.M))
        self.run.doc(f"drugs/{self.slug}/label_sections.md", md, ticker=self.info.get("ticker") or None, group="drugs",
                     doc_type="fda_label", period=meta["published_date"],
                     source_url=f"{DP.DM}/drugInfo.cfm?setid={meta['setid']}", pages=heads)
        return {"setid": meta["setid"], "title": meta["title"], "sections": heads}

    def versions(self):
        from agent import drug_pack as DP
        setid = self.info.get("setid")
        if not setid:
            raise RuntimeError("no setid (label step failed)")
        url = f"{DP.DM}/services/v2/spls/{setid}/history.json"
        rows, page = [], 1
        while True:
            j = DP.get(url, params={"pagesize": 100, "page": page}).json()
            data = j.get("data", {})
            for r in (data.get("history", []) if isinstance(data, dict) else data):
                rows.append({"drug": self.slug, "setid": setid, "spl_version": r.get("spl_version"),
                             "published_date": r.get("published_date"), "source": url,
                             "source_row": f"setid={setid}|spl_version={r.get('spl_version')}"})
            if page >= int(j.get("metadata", {}).get("total_pages", 1) or 1):
                break
            page += 1
        return self.run.table("label_versions", rows, ticker=self.info.get("ticker") or None,
                              source_url=url)

    def reference(self):
        from agent import drug_pack as DP
        t0 = time.time()
        self.bulk = self.bulk or DP.Bulk()
        ing = (self.ingredient or self.brand).split()[0].upper()
        out = {"bulk_load_s": round(time.time() - t0, 1)}
        src = {"orange_book_products.csv": "data/external/orange_book.zip (products.txt)",
               "orange_book_patents.csv": "data/external/orange_book.zip (patent.txt)",
               "orange_book_exclusivity.csv": "data/external/orange_book.zip (exclusivity.txt)",
               "purple_book.csv": "data/external/purple_book_2026_09.csv",
               "paragraph_iv.csv": "data/external/paragraph_iv.xlsx",
               "ira_negotiation.csv": "data/external/ira_selected_drugs_mfp.zip"}
        for rel, df in self.bulk.slices(self.brand.upper(), ing).items():
            if rel not in src:
                continue  # Part D / Part B come from the pricing step with line-level source_row
            rows = []
            for i, r in df.iterrows():
                key = "|".join(f"{c}={r[c]}" for c in ("Appl_No", "Product_No", "Patent_No", "Exclusivity_Code",
                                                         "BLA Number") if c in df.columns and isinstance(r[c], str))
                rows.append(dict({k: v for k, v in r.items()}, drug=self.slug, source=src[rel],
                                 source_row=key or f"row={i}"))
            out[rel[:-4]] = self.run.table(rel[:-4], rows, ticker=self.info.get("ticker") or None, source_url=src[rel])
            if not rows:
                self.run.gap(f"{self.slug} {rel[:-4]}", "no rows in the bulk file for this brand / ingredient")
        return out

    def pricing(self):
        tk = self.info.get("ticker") or None
        out = {"partd": self.run.table("partd_spending", L.spend_rows(self.brand, "D", self.slug), ticker=tk,
                                       source_url=L.PARTD_URL),
               "partb": self.run.table("partb_spending", L.spend_rows(self.brand, "B", self.slug), ticker=tk,
                                       source_url=L.PARTB_URL)}
        for name, fn, yrs in (("nadac_history", L.nadac_rows, (2024, 2025, 2026)),
                              ("medicaid_sdud", L.sdud_rows, (2023, 2024, 2025))):
            try:
                out[name] = self.run.table(name, fn(self.brand, yrs, self.slug), ticker=tk,
                                           source_url="https://data.medicaid.gov")
            except Exception as e:
                self.run.gap(f"{self.slug} {name}", repr(e))
                out[name] = f"failed {e!r}"[:120]
        for k, v in out.items():
            if not v:
                self.run.gap(f"{self.slug} {k}", "no rows (not in this channel, or not listed under the brand name)")
        return out

    def policy(self):
        terms = [self.brand.lower()] + ([self.ingredient.split()[0].lower()] if self.ingredient else [])
        rows = L.gov_mentions(L.alias_regex(terms), self.slug)
        return self.run.table("policy_mentions", rows, ticker=self.info.get("ticker") or None,
                              source_url="data/moat/policy_gov (saved government documents)")

    def find_rivals(self):
        own = self.ingredient.split()[0].lower() if self.ingredient else ""
        if self.a.vs:
            self.rivals = [{"ingredient": x.strip().lower(), "brand": "", "class": "user supplied", "spend_2024": ""}
                           for x in self.a.vs.split(",") if x.strip()]
        else:
            if not own:
                raise RuntimeError("no ingredient to classify")
            d, b = L.spend_frames()
            found = {}
            for source in ("ATC", "FDASPL"):
                for cid, cname in L.rx_classes(own, source):
                    for ing in L.rx_members(cid, source):
                        w = ing.split()[0]
                        if w == own or len(w) < 4:
                            continue
                        for part, df in (("D", d), ("B", b)):
                            hit = df[df["Gnrc_Name"].fillna("").str.lower().str.contains(re.escape(w))]
                            if "Mftr_Name" in hit.columns:
                                hit = hit[hit["Mftr_Name"] == "Overall"]
                            # branded products only: generics (brand name == generic name) are not a rival brand
                            hit = hit[hit["Brnd_Name"].fillna("").str.lower().str.rstrip("*")
                                      != hit["Gnrc_Name"].fillna("").str.lower()]
                            sp = float(hit["spend_2024"].sum())
                            cur = found.setdefault(w, {"ingredient": w, "brand": "", "class": f"{source} {cid} {cname}",
                                                       "spend_2024": 0.0})
                            cur["spend_2024"] += sp
                            if len(hit) and not cur["brand"]:
                                cur["brand"] = str(hit.sort_values("spend_2024").iloc[-1]["Brnd_Name"])
                        time.sleep(0.1)
                if found:
                    break
            self.rivals = sorted(found.values(), key=lambda r: -r["spend_2024"])[:self.a.rivals]
        rows = [dict(r, drug=self.slug, source="https://rxnav.nlm.nih.gov/REST/rxclass + CMS 2024 spend",
                     source_row=f"{r['class']}|{r['ingredient']}") for r in self.rivals]
        self.run.table("competitive_set", rows, ticker=self.info.get("ticker") or None,
                       source_url="https://rxnav.nlm.nih.gov/REST/rxclass")
        return [f"{r['ingredient']} ({r['brand']})" for r in self.rivals]

    def head_to_head(self):
        from agent.moat import product_h2h as P
        own = (self.ingredient or self.brand).split()[0].lower()
        rows, prow = [], []
        for r in self.rivals:
            b = r["ingredient"]
            try:
                for s in P.ct(own, b):
                    p = s["protocolSection"]
                    nct = p["identificationModule"]["nctId"]
                    po = [o.get("measure") for o in p.get("outcomesModule", {}).get("primaryOutcomes", [])]
                    rows.append({"nct_id": nct, "drugs": f"{own} vs {b}", "design": P.design(s, own, b),
                                 "phase": "/".join(p.get("designModule", {}).get("phases", [])),
                                 "status": p["statusModule"].get("overallStatus"),
                                 "results_posted": "y" if s.get("hasResults") else "n",
                                 "title": p["identificationModule"].get("briefTitle"),
                                 "primary_outcome": " | ".join(x for x in po if x)[:400],
                                 "start_date": p["statusModule"].get("startDateStruct", {}).get("date", ""),
                                 "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", ""),
                                 "url": f"https://clinicaltrials.gov/study/{nct}",
                                 "source": f"https://clinicaltrials.gov/api/v2/studies/{nct}", "source_row": nct})
            except Exception as e:
                self.run.gap(f"{own}-{b} ctgov", repr(e))
            try:
                for pid, t, y, pt in P.pubmed(own, b):
                    prow.append({"pmid": pid, "drugs": f"{own} vs {b}", "title": t, "year": y, "pubtypes": "; ".join(pt),
                                 "url": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                                 "source": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", "source_row": pid})
            except Exception as e:
                self.run.gap(f"{own}-{b} pubmed", repr(e))
            time.sleep(0.4)
        tk = self.info.get("ticker") or None
        n1 = self.run.table("head_to_head", rows, ticker=tk, source_url="https://clinicaltrials.gov/api/v2/studies")
        n2 = self.run.table("head_to_head_pubmed", prow, ticker=tk, source_url="https://pubmed.ncbi.nlm.nih.gov/")
        return {"trials": n1, "true_h2h": sum(1 for r in rows if r["design"] == "head_to_head_separate_arms"),
                "pubmed": n2}

    def open_payments(self):
        """General payments naming the brand, by nature of payment, using the same datastore query as the rx
        stream's agent/moat/rx_openpay.py (not imported: that module runs its full collection on import)."""
        if not importlib.util.find_spec("agent.moat.rx_openpay"):
            self.run.gap("open payments", "rx stream Open Payments module not present yet")
            return "skipped (no rx Open Payments module)"
        import requests
        pn = "name_of_drug_or_biological_or_device_or_medical_supply_"
        nat = "nature_of_payment_or_transfer_of_value"
        rows = []
        for year, ds in OPEN_PAYMENTS_GENERAL.items():
            u = f"https://openpaymentsdata.cms.gov/api/1/datastore/query/{ds}/0"
            for slot in range(1, 6):
                body = {"conditions": [{"property": f"{pn}{slot}", "operator": "=", "value": self.brand.title()}],
                        "properties": [nat, {"expression": {"operator": "sum", "operands": ["total_amount_of_payment_usdollars"]}, "alias": "usd"},
                                       {"expression": {"operator": "count", "operands": ["record_id"]}, "alias": "n"}],
                        "groupings": [nat], "limit": 500, "results": True, "schema": False}
                if self.run.left() < 60:
                    self.run.gap("open payments", f"time budget: stopped at PY{year} slot {slot}")
                    break
                try:
                    r = requests.post(u, json=body, timeout=self.a.op_timeout)
                    r.raise_for_status()
                except Exception as e:  # the datastore is slow; one timeout means the rest will be too
                    self.run.gap("open payments", f"PY{year} slot {slot}: {e!r}"[:300])
                    return self.run.table("open_payments", rows, ticker=self.info.get("ticker") or None,
                                          source_url="https://openpaymentsdata.cms.gov") or f"partial: {e!r}"[:120]
                for x in r.json().get("results", []):
                    rows.append({"drug": self.slug, "brand": self.brand.upper(), "program_year": year, "product_slot": slot,
                                 "nature_of_payment": x.get(nat), "total_usd": x.get("usd"), "n_payments": x.get("n"),
                                 "source": f"https://openpaymentsdata.cms.gov/dataset/{ds}",
                                 "source_row": f"general_payments PY{year} product_{slot}={self.brand.title()}|nature={x.get(nat)}"})
                time.sleep(0.3)
        return self.run.table("open_payments", rows, ticker=self.info.get("ticker") or None,
                              source_url="https://openpaymentsdata.cms.gov")


# program-year dataset ids, same as agent/moat/rx_openpay.py GEN
OPEN_PAYMENTS_GENERAL = {2023: "fb3a65aa-c901-4a38-a813-b04b00dfa2a9", 2024: "e6b17c6a-2534-4207-a4a1-6746a14911ff"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brand")
    ap.add_argument("--vs", default="", help="comma list of rival ingredients (default: inferred)")
    ap.add_argument("--rivals", type=int, default=4)
    ap.add_argument("--budget", type=float, default=20, help="minutes")
    ap.add_argument("--op-timeout", type=float, default=90, help="seconds per Open Payments query")
    ap.add_argument("--skip", default="")
    ap.add_argument("--no-index", action="store_true")
    a = ap.parse_args(argv)
    d = Drug(a.brand, a)
    run = d.run
    run.skip = set(filter(None, a.skip.split(","))) | ({"index"} if a.no_index else set())
    plan = [("identify", d.identify), ("label", d.label), ("versions", d.versions), ("reference", d.reference),
            ("pricing", d.pricing), ("policy", d.policy), ("rivals", d.find_rivals), ("head_to_head", d.head_to_head),
            ("open_payments", d.open_payments)]
    for name, fn in plan:
        if name in run.skip:
            run.log(name, "skipped", reason="--skip")
            continue
        run.step(name, fn)
    (run.dir / "info.json").write_text(json.dumps(d.info, indent=1, default=str))
    from agent.moat.onboard_company import index_and_summary, print_summary
    res, cov = index_and_summary(run, d.slug, "drug")
    summ = run.finish({"brand": d.brand, "info": d.info, "rivals": d.rivals, "index": res, "coverage": cov})
    print_summary(summ)
    return summ


if __name__ == "__main__":
    main()
