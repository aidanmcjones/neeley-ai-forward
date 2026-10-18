"""Onboard any drug maker into the moat dataset with one command.

  python -m agent.moat.onboard_company REGN [--years 5] [--quarters 10] [--budget 45] [--products 6] [--ibes]
                                             [--skip step1,step2] [--no-index]

Steps (each logs to data/moat/onboard/<T>/steps.jsonl; a failure records a gap and the run continues):
  resolve       CIK, registrant name, exchange, former names (company_tickers_exchange.json + submissions)
  subsidiaries  Exhibit 21 (10-K) or Exhibit 8 (20-F) entities; their distinctive names extend the alias list
  sec_filings   annual reports x years, 10-Qs since 2023 (or results 6-Ks), 8-Ks since 2023 (primary + EX-99/10/2),
                DEF 14A proxies since 2024 (+ incentive metric rows), CORRESP/UPLOAD comment letters since 2019;
                page-marked with agent.corpus.paged_text/render; URLs already in data/corpus are not refetched
  xbrl_panel    product revenue rows from every 10-Q/10-K/20-F XBRL instance since 2023 (ProductOrServiceAxis)
  transcripts   last N earnings calls from MarketBeat (Quartr text; third_party, grade C unless a Bloomberg PDF exists)
  attention     analyst Q&A topic counts per quarter from those transcripts (agent.moat.market_topics regexes)
  products      XBRL product members + Orange/Purple Book applicant match, ranked by Medicare 2024 spend
  pricing       Part D and Part B 2024 spend rows and NADAC history for the top products
  policy        IRA selected-drug rows, mentions in the saved government documents (CMS, White House MFN, tariff),
                FDA registered establishments by country (drls_reg)
  consensus     I/B/E/S via WRDS (only with --ibes: WRDS sends a Duo push)
  insiders      Form 4 officer and director transactions since 2024 (US filers)
  index         python -m agent.moat.index --add, then the coverage summary in agent.moat.progress bucket terms
"""

import argparse
import csv
import io
import json
import re
import time
import zipfile
from collections import Counter, defaultdict
from datetime import date, timedelta

import agent.tenk as tenk
from agent.corpus import filings, folder_docs, paged_text, quarter_label, render
from agent.moat import onboard_lib as L
from agent.moat.common import OUT, ROOT, write

STEPS = ["resolve", "subsidiaries", "sec_filings", "xbrl_panel", "transcripts", "attention", "products", "pricing",
         "policy", "consensus", "insiders", "index"]


def sec_get(url, as_json=False):
    tenk.MIN_INTERVAL = 0.3  # shared SEC limit with other workers
    return tenk.sec_get(url, as_json=as_json)


def url_of(cik, acc, name):
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{name}"


class Company:
    def __init__(self, ticker, a):
        self.t = ticker.upper()
        self.a = a
        self.run = L.Run(self.t, a.budget, "company")
        self.p = {}
        self.fs = []
        self.in_corpus = set()
        self.foreign = False
        self.products = []

    # ------------------------------------------------------------ resolve
    def resolve(self):
        hit = L.resolve_cik(self.t, L.tickers_exchange())
        if not hit:
            raise SystemExit(f"{self.t}: not in SEC company_tickers_exchange.json")
        sub, fs = filings(hit["cik"], "2019-01-01")
        tenk.MIN_INTERVAL = 0.3
        self.fs = fs
        forms = Counter(f["form"] for f in fs)
        self.foreign = forms["20-F"] > 0 and forms["10-K"] == 0
        former = [x.get("name", "") for x in sub.get("formerNames", [])]
        self.p = {"ticker": self.t, "cik": hit["cik"], "name": sub.get("name") or hit["name"],
                  "exchange": hit["exchange"], "sic": sub.get("sic"), "sic_description": sub.get("sicDescription"),
                  "state_of_incorporation": sub.get("stateOfIncorporation"), "former_names": former,
                  "foreign_private_issuer": self.foreign, "filings_since_2019": len(fs),
                  "aliases": L.aliases(sub.get("name") or hit["name"], former),
                  "source": f"https://data.sec.gov/submissions/CIK{hit['cik']:010d}.json",
                  "source_row": f"cik={hit['cik']}"}
        from agent.moat.secx_lib import corpus_urls
        self.in_corpus = corpus_urls()
        tenk.MIN_INTERVAL = 0.3
        self.save_profile()
        return {k: self.p[k] for k in ("cik", "name", "exchange", "foreign_private_issuer", "aliases")}

    def save_profile(self):
        write(self.run.stream, f"onboard/{self.t}/profile.json", json.dumps(self.p, indent=1), ticker=self.t,
              group="onboard", doc_type="profile", source_url=self.p["source"])

    @property
    def cik(self):
        return self.p["cik"]

    # ------------------------------------------------------------ documents
    def save(self, rel, url, doc_type, f, raw=None):
        """Fetch, page-mark and write one SEC document. Returns new, exists, already_collected (URL in data/corpus or another moat stream) or failed."""
        if url in self.in_corpus:
            return "already_collected"
        if (OUT / rel).exists():
            return "exists"
        try:
            raw = raw if raw is not None else sec_get(url)
        except Exception as e:
            self.run.gap(rel, repr(e))
            return "failed"
        pages = paged_text(raw)
        hdr = (f"<!-- source: {url}\n     ticker: {self.t}  type: {doc_type}  form: {f['form']}  filed: {f['filed']}  "
               f"period: {f['period']}\n     retrieved: {L.now()} -->\n")
        self.run.doc(rel, render(pages, hdr), ticker=self.t, group="companies", doc_type=doc_type, form=f["form"],
                     period=f["period"], filed=f["filed"], source_url=url, pages=len(pages),
                     pages_with_folio=sum(1 for p, _ in pages if p))
        return "new"

    def sec_filings(self):
        t, cik, c = self.t, self.cik, Counter()
        annual_form = "20-F" if self.foreign else "10-K"
        ann = [f for f in self.fs if f["form"] == annual_form]
        seen_fy = []
        for f in sorted(ann, key=lambda x: x["period"] or "", reverse=True):
            fy = (f["period"] or f["filed"])[:4]
            if fy in seen_fy:
                continue
            seen_fy.append(fy)
            if len(seen_fy) > self.a.years:
                break
            stem = f"{annual_form.lower().replace('-', '')}_FY{fy}"
            c["annual_" + self.save(f"companies/{t}/{stem}.md", url_of(cik, f["accession"], f["primary_doc"]),
                                    "annual_report", f)] += 1
        if not self.foreign:
            for f in self.fs:
                if f["form"] == "10-Q" and (f["period"] or "") >= "2023-01-01":
                    c["quarterly_" + self.save(f"companies/{t}/10q_{quarter_label(f['period'])}.md",
                                               url_of(cik, f["accession"], f["primary_doc"]), "quarterly_report", f)] += 1
        else:
            c.update(self.results_6k())
        if self.run.left() > 300:
            c.update(self.current_reports())
        for f in [x for x in self.fs if x["form"] == "DEF 14A" and x["filed"] >= "2024-01-01"]:
            rel = f"companies/{t}/proxy_{f['filed'][:4]}.md"
            c["proxy_" + self.save(rel, url_of(cik, f["accession"], f["primary_doc"]), "proxy_statement", f)] += 1
        c["proxy_metric_rows"] = self.proxy_metrics()
        c.update(self.letters())
        return dict(c)

    def results_6k(self):
        pat = re.compile(r"financial report|first (three|six|nine) months|(first|second|third|fourth)[- ]quarter|"
                         r"\bQ[1-4]\b|half[- ]year|full[- ]year|results", re.I)
        c, checked, kept = Counter(), 0, 0
        for f in self.fs:
            if f["form"] != "6-K" or f["filed"] < "2023-01-01" or int(f["filed"][5:7]) not in (1, 2, 4, 5, 7, 8, 10, 11):
                continue
            if checked >= 60 or kept >= 14 or self.run.left() < 300:
                break
            checked += 1
            try:
                docs = folder_docs(self.cik, f["accession"])
            except Exception as e:
                self.run.gap(f"6-K {f['accession']}", repr(e))
                continue
            for n, u in docs:
                if not n.lower().endswith((".htm", ".html")) or "-index" in n:
                    continue
                try:
                    raw = sec_get(u)
                except Exception:
                    continue
                head = tenk.html_to_text(raw)[:4000]
                if not pat.search(head) or len(raw) < 40000 or re.search(r"repurchase|voting rights", head[:1500], re.I):
                    continue
                c["6k_" + self.save(f"companies/{self.t}/6k/{f['filed']}_{f['accession']}.md", u,
                                    "foreign_current_report", f, raw)] += 1
                kept += 1
                break
        c["6k_checked"] = checked
        return c

    def current_reports(self):
        from agent.moat.secx_8k import EX
        c = Counter()
        if self.foreign:
            return c
        n = 0
        for f in reversed([x for x in self.fs if x["form"] == "8-K" and x["filed"] >= "2023-01-01"]):
            if n >= self.a.max_8k or self.run.left() < 300:
                c["8k_capped"] += 1
                continue
            try:
                docs = folder_docs(self.cik, f["accession"])
            except Exception as e:
                self.run.gap(f"8-K {f['accession']}", repr(e))
                continue
            keep = [(nm, u) for nm, u in docs if nm.lower().endswith((".htm", ".html", ".txt"))
                    and (nm == f["primary_doc"] or EX.search(nm)) and "index" not in nm.lower()]
            for nm, u in keep:
                stem = re.sub(r"\.[a-z]+$", "", nm)
                r = self.save(f"companies/{self.t}/8k/{f['filed']}_{f['accession']}_{stem}.md", u, "current_report_8k", f)
                c["8k_" + r] += 1
                n += r == "new"
        return c

    def proxy_metrics(self):
        from agent.moat.secx_proxy import metrics
        rows = []
        for p in sorted((OUT / "companies" / self.t).glob("proxy_*.md")):
            body = p.read_text(encoding="utf-8")
            url = (re.search(r"source: (\S+)", body) or [None, ""])[1]
            for r in metrics(body, self.t, p.stem[-4:], url):
                r["source"] = url
                r["source_row"] = f"{self.t}:companies/{self.t}/{p.name}#p{r['pdf_page']}"
                rows.append(r)
        return self.run.table("exec_comp_metrics", rows, ticker=self.t, source_url="SEC DEF 14A")

    def letters(self):
        from agent.moat.secx_letters import TOPICS
        c, rows = Counter(), []
        for f in [x for x in self.fs if x["form"] in ("CORRESP", "UPLOAD")]:
            url = url_of(self.cik, f["accession"], f["primary_doc"])
            rel = f"companies/{self.t}/sec_letters/{f['filed']}_{f['form']}_{f['accession']}.md"
            try:
                raw = sec_get(url)
            except Exception as e:
                self.run.gap(rel, repr(e))
                continue
            c["letter_" + self.save(rel, url, "sec_comment_letter", f, raw)] += 1
            kws = [k for k, p in TOPICS.items() if re.search(p, raw[:400000], re.I)]
            rows.append({"ticker": self.t, "date": f["filed"], "form": f["form"], "accession": f["accession"],
                         "topics": ";".join(kws), "url": url, "path": "data/moat/" + rel, "source": url,
                         "source_row": f"accession={f['accession']}"})
        c["letter_rows"] = self.run.table("sec_comment_letters", rows, ticker=self.t, source_url="SEC EDGAR CORRESP/UPLOAD")
        return c

    # ------------------------------------------------------------ subsidiaries
    def subsidiaries(self):
        form, pat = SUBS_PATTERNS["20-F" if self.foreign else "10-K"]
        ann = [f for f in self.fs if f["form"] == form]
        if not ann:
            raise RuntimeError(f"no {form} found")
        f = ann[-1]
        ex = [(n, u) for n, u in folder_docs(self.cik, f["accession"])
              if re.search(pat, n, re.I) and n.lower().endswith((".htm", ".html", ".txt"))]
        if not ex:
            raise RuntimeError(f"no subsidiaries exhibit in {f['accession']}")
        name, url = ex[0]
        raw = sec_get(url)
        rows = parse_subsidiaries(raw)
        for i, r in enumerate(rows):
            r.update(ticker=self.t, filed=f["filed"], url=url, source=url, source_row=f"{name}#row{i + 1}")
        self.run.table("subsidiaries", rows, ["ticker", "entity", "country", "filed", "url"], url, self.t)
        self.p["aliases"] = L.aliases(self.p["name"], self.p["former_names"], [r["entity"] for r in rows])
        self.save_profile()
        return {"entities": len(rows), "aliases": self.p["aliases"]}

    # ------------------------------------------------------------ XBRL
    def xbrl_panel(self):
        from agent.gap_data import parse_product_revenue
        from agent.moat.filings_panel import COLS, GEO, PROD
        rows, nfil = [], 0
        for f in [x for x in self.fs if x["form"] in ("10-Q", "10-K", "20-F") and x["filed"] >= "2023-01-01"]:
            if self.run.left() < 240:
                self.run.gap("xbrl_panel", "time budget: stopped early")
                break
            acc = f["accession"]
            folder = f"https://www.sec.gov/Archives/edgar/data/{self.cik}/{acc.replace('-', '')}"
            try:
                names = [x["name"] for x in sec_get(f"{folder}/index.json", as_json=True)["directory"]["item"]]
                inst = next((n for n in names if n.endswith("_htm.xml")), None) or next(
                    (n for n in names if re.fullmatch(r"[a-z]+-\d{8}\.xml", n)), None)
                if not inst:
                    self.run.gap(f"xbrl {acc}", "no instance xml")
                    continue
                xml = sec_get(f"{folder}/{inst}").encode()
                nfil += 1
                for r in parse_product_revenue(xml):
                    d = r["dims"]
                    prod = [v for k, v in d.items() if PROD.search(k)]
                    geo = [v for k, v in d.items() if GEO.search(k)]
                    oth = {k.split(":")[-1]: v for k, v in d.items() if not PROD.search(k) and not GEO.search(k)}
                    rows.append({"ticker": self.t, "accession": acc, "form": f["form"], "period_start": r["start"],
                                 "period_end": r["end"], "days": r["days"], "concept": r["concept"],
                                 "product_member": ";".join(prod), "geography": ";".join(geo),
                                 "other_dims": json.dumps(oth, sort_keys=True) if oth else "", "value_usd": r["value"],
                                 "source": f"{folder}/{inst}",
                                 "source_row": "|".join(f"{k.split(':')[-1]}={v}" for k, v in sorted(d.items()))})
            except Exception as e:
                self.run.gap(f"xbrl {acc}", repr(e))
        n = self.run.table("product_revenue_quarterly", rows, list(COLS), "SEC EDGAR XBRL instances", self.t)
        members = Counter(m for r in rows for m in r["product_member"].split(";") if m)
        return {"filings_parsed": nfil, "rows": n, "product_members": len(members)}

    # ------------------------------------------------------------ transcripts
    def transcripts(self):
        from agent.moat import calls_mb as M
        exch = {"nasdaq": "NASDAQ", "nyse": "NYSE"}.get(str(self.p.get("exchange")).lower(), "NYSE")
        listing = f"https://www.marketbeat.com/stocks/{exch}/{self.t}/earnings/"
        code, html = M.get(listing)
        links = sorted(set(re.findall(r"/earnings/reports/(\d{4})-(\d{1,2})-(\d{1,2})-([0-9a-z\-]+)/", html)))
        if not links:
            raise RuntimeError(f"MarketBeat listing {listing} -> HTTP {code}, no report links")
        slug = Counter(x[3] for x in links).most_common(1)[0][0]
        cands = {}
        for y, m, d, s in links:
            if s == slug:
                dt = date(int(y), int(m), int(d))
                if dt <= date.today():
                    cands[dt] = f"https://www.marketbeat.com/earnings/reports/{y}-{m}-{d}-{slug}/"
        # older calls: earnings 8-K (item 2.02) or results 6-K dates, plus the next business day
        for f in self.fs:
            if f["filed"] >= "2023-10-01" and ((f["form"] == "8-K" and "2.02" in f["items"]) or
                                               (f["form"] == "6-K" and self.foreign)):
                dt = date.fromisoformat(f["filed"])
                for k in (0, -1, 1):
                    x = dt + timedelta(days=k)
                    if x.weekday() < 5:
                        cands.setdefault(x, f"https://www.marketbeat.com/earnings/reports/{x.year}-{x.month}-{x.day}-{slug}/")
        by_q = {}
        for dt in sorted(cands, reverse=True):
            q = M.quarter_of(dt)
            if q in by_q or dt.month in (3, 6, 9, 12):
                continue
            if len(by_q) >= self.a.quarters:
                break
            if self.run.left() < 120:
                self.run.gap("transcripts", "time budget: stopped early")
                break
            rel = f"companies/{self.t}/transcripts/{q}_transcript.md"
            if (OUT / rel).exists():
                by_q[q] = {"quarter": q, "status": "exists", "url": cands[dt], "path": "data/moat/" + rel}
                continue
            code, h = M.get(cands[dt])
            time.sleep(0.5)
            if code != 200 or not M.has_call(h):
                continue
            turns = M.parse(h)
            if not turns or len(turns) < 5:
                self.run.gap(f"{q} transcript", f"{cands[dt]} parsed to {len(turns or [])} turns")
                continue
            iso = dt.isoformat()
            bbg = ROOT / "data/corpus/_inbox/bloomberg" / f"{self.t}_{q}_transcript_bbg.pdf"
            md, pages = M.render(turns, cands[dt], "third_party", iso, self.t, q)
            self.run.doc(rel, md, ticker=self.t, group="companies", doc_type="transcript", period=q, filed=iso,
                         source_url=cands[dt], quality="third_party", pages=pages)
            by_q[q] = {"quarter": q, "status": "new", "url": cands[dt], "path": "data/moat/" + rel,
                       "call_date": iso, "turns": len(turns),
                       "analyst_turns": sum(1 for x in turns if x["kind"] == "analyst"),
                       "grade": "A (Bloomberg PDF in inbox)" if bbg.exists() else "C"}
        rows = [dict(v, ticker=self.t, source=v["url"], source_row=f"{self.t}:{v['path'][10:]}") for v in by_q.values()]
        self.run.table("transcripts_index", rows, ticker=self.t, source_url=listing)
        return {"slug": slug, "quarters": sorted(by_q), "new": sum(1 for v in by_q.values() if v["status"] == "new")}

    def attention(self):
        from agent.moat.market_topics import TOPIC_RE
        turn = re.compile(r"^\*\*(.+?) \((Analyst[^)]*)\):\*\* (.*)$")
        rows = []
        for p in sorted((OUT / "companies" / self.t / "transcripts").glob("*_transcript.md")):
            q = p.name[:6]
            page, n_an = 1, 0
            hits = defaultdict(list)
            for line in p.read_text(encoding="utf-8").splitlines():
                m = L.PAGE_RE.match(line.strip())
                if m:
                    page = int(m.group(1))
                    continue
                m = turn.match(line)
                if not m:
                    continue
                n_an += 1
                for k, rx in TOPIC_RE.items():
                    if rx.search(m.group(3)):
                        hits[k].append(page)
            doc = f"{self.t}:companies/{self.t}/transcripts/{p.name}"
            for k in TOPIC_RE:
                rows.append({"ticker": self.t, "quarter": q, "topic": k, "analyst_turns": n_an,
                             "turns_with_topic": len(hits[k]), "source": f"data/moat/companies/{self.t}/transcripts/{p.name}",
                             "source_row": f"{doc}#p{hits[k][0]}" if hits[k] else doc})
        return self.run.table("analyst_topics", rows, ticker=self.t, source_url="derived from onboarded transcripts")

    # ------------------------------------------------------------ products and pricing
    def products_step(self):
        al = alias_re = L.alias_regex(self.p["aliases"])
        appl = L.applicant_products(alias_re)
        members = Counter()
        prq = OUT / "onboard" / self.t / "product_revenue_quarterly.csv"
        if prq.exists():
            with open(prq) as f:
                for r in csv.DictReader(f):
                    for m in r["product_member"].split(";"):
                        if m:
                            members[m] += 1
        names = {}
        for m in members:
            nm = member_name(m)
            if nm:
                names.setdefault(nm.upper().split()[0], m)
        d, b = L.spend_frames()
        cand = dict(appl)
        for first, m in names.items():
            if first not in {k.split()[0] for k in cand}:
                cand[first] = {"brand": first, "ingredient": "", "appl_no": "", "applicant": "", "modality": ""}
        out = []
        for k, v in cand.items():
            first = k.split()[0]
            pat = rf"^{re.escape(first)}\b"
            dd = d[d["Brnd_Name"].fillna("").str.contains(pat, case=False, regex=True)]
            bb = b[b["Brnd_Name"].fillna("").str.contains(pat, case=False, regex=True)]
            out.append(dict(v, ticker=self.t, xbrl_member=names.get(first, ""),
                            partd_spend_2024=round(dd[dd["Mftr_Name"] == "Overall"]["spend_2024"].sum() or dd["spend_2024"].sum()),
                            partb_spend_2024=round(bb["spend_2024"].sum()),
                            source="FDA Orange Book products.txt / Purple Book (data/external)" if v["appl_no"] else "SEC XBRL ProductOrServiceAxis",
                            source_row=f"Appl_No={v['appl_no']}|applicant={v['applicant']}" if v["appl_no"] else names.get(first, "")))
        out.sort(key=lambda r: (-(r["partd_spend_2024"] + r["partb_spend_2024"]), len(r["brand"])))
        # one product per brand family: ENTRESTO SPRINKLE and KISQALI FEMARA CO-PACK share the spend rows of
        # ENTRESTO / KISQALI (the spend match is on the first word), so keep the first, highest-spend variant
        fam, top = set(), []
        for r in out:
            first = r["brand"].split()[0]
            if first not in fam and r["partd_spend_2024"] + r["partb_spend_2024"] > 0:
                fam.add(first)
                top.append(r)
        self.products = top[:self.a.products]
        if not self.products:
            self.products = out[:self.a.products]
        self.run.table("products", out, ticker=self.t, source_url="FDA Orange/Purple Book + SEC XBRL + CMS 2024 spend")
        return {"candidates": len(out), "top": [r["brand"] for r in self.products]}

    def pricing(self):
        pd_rows, pb_rows, nadac = [], [], []
        for p in self.products:
            br = p["brand"]
            pd_rows += [dict(r, ticker=self.t) for r in L.spend_rows(br, "D")]
            pb_rows += [dict(r, ticker=self.t) for r in L.spend_rows(br, "B")]
            try:
                nadac += [dict(r, ticker=self.t) for r in L.nadac_rows(br)]
            except Exception as e:
                self.run.gap(f"nadac {br}", repr(e))
        res = {"partd_rows": self.run.table("partd_spending", pd_rows, ticker=self.t, source_url=L.PARTD_URL),
               "partb_rows": self.run.table("partb_spending", pb_rows, ticker=self.t, source_url=L.PARTB_URL),
               "nadac_rows": self.run.table("nadac_history", nadac, ticker=self.t,
                                            source_url="https://data.medicaid.gov (NADAC)")}
        for p in self.products:
            if not any(r["drug"] == L.slug(p["brand"]) for r in pd_rows + pb_rows):
                self.run.gap(f"pricing {p['brand']}", "no Part D or Part B 2024 rows for this brand")
        return res

    # ------------------------------------------------------------ policy
    def policy(self):
        brands = [p["brand"].split()[0] for p in self.products]
        terms = self.p["aliases"] + [b.lower() for b in brands if len(b) > 3]
        rx = L.alias_regex(terms)
        rows = [dict(r, ticker=self.t) for r in L.gov_mentions(rx, self.t)]
        res = {"gov_mention_rows": self.run.table("policy_mentions", rows, ticker=self.t,
                                                  source_url="data/moat/policy_gov (saved government documents)")}
        res["ira_rows"] = self.run.table("ira_selected", ira_rows(rx, self.t), ticker=self.t,
                                         source_url="data/external/ira_selected_drugs_mfp.zip")
        try:
            res["site_rows"] = self.run.table("manufacturing_sites", sites_rows(L.alias_regex(self.p["aliases"]), self.t),
                                              ticker=self.t, source_url="https://www.accessdata.fda.gov/cder/drls_reg.zip")
        except Exception as e:
            self.run.gap("manufacturing sites", repr(e))
            res["site_rows"] = f"failed: {e!r}"[:200]
        forces = Counter(r["force"] for r in rows)
        res["forces"] = dict(forces)
        return res

    # ------------------------------------------------------------ consensus
    def consensus(self):
        if not self.a.ibes:
            self.run.gap("I/B/E/S consensus", "skipped: WRDS needs a Duo push; rerun with --ibes")
            return "skipped (no --ibes)"
        import psycopg2
        from agent.moat import ibes
        conn = psycopg2.connect(host="wrds-pgdata.wharton.upenn.edu", port=9737, dbname="wrds",
                                user=ibes.wrds_username(), sslmode="require", connect_timeout=120)
        out = {}
        for name, (table, sql, keys) in ibes.QUERIES.items():
            cur = conn.cursor()
            try:
                cur.execute(sql, ((self.t,),) if sql.count("%s") == 1 else ((self.t,), ibes.SINCE))
                text, n = ibes.to_csv(cur, table, keys)
                write(self.run.stream, f"onboard/{self.t}/{name}.csv", text, ticker=self.t, group="onboard",
                      doc_type="consensus_table", source_url=f"WRDS {table}", quality="licensed_wrds")
                out[name] = n
            except Exception as e:
                conn.rollback()
                out[name] = f"failed {e!r}"[:120]
            finally:
                cur.close()
        conn.close()
        return out

    # ------------------------------------------------------------ insiders
    def insiders(self):
        if self.foreign:
            self.run.gap("insider trades", "foreign private issuer: no Form 4")
            return "skipped (foreign private issuer)"
        from agent.moat.secx_form4 import COLS, parse
        tenk.MIN_INTERVAL = 0.3
        fs = [f for f in self.fs if f["form"] in ("4", "4/A") and f["filed"] >= "2024-01-01"]
        rows = []
        for i, f in enumerate(fs):
            if self.run.left() < 150:
                self.run.gap("insider trades", f"time budget: parsed {i} of {len(fs)} Form 4s")
                break
            url = url_of(self.cik, f["accession"], f["primary_doc"].split("/")[-1])
            try:
                for j, r in enumerate(parse(sec_get(url), self.t, url, f["accession"])):
                    rows.append(dict(r, source=url, source_row=f"accession={f['accession']}|txn={j + 1}"))
            except Exception as e:
                self.run.gap(f"form4 {f['accession']}", repr(e)[:150])
        n = self.run.table("insider_trades", rows, list(COLS), "SEC EDGAR Form 4", self.t)
        return {"form4_filings": len(fs), "rows": n}


# ---------------------------------------------------------------- helpers (module level so tests can use them)

# subsidiaries exhibit file names: 'regn-ex_211x12312025x10k.htm', 'ex21.htm', 'exhibit21-1.htm', 'nvs-ex8.htm'
SUBS_PATTERNS = {"10-K": ("10-K", r"ex(?:h|hibit)?[-_]?21(?!\d\d)"),
                 "20-F": ("20-F", r"ex(?:h|hibit)?[-_]?8(?:[._-]?1)?(?!\d)")}

def member_name(member):
    """'regn:EyleaHDMember' -> 'Eylea HD'; generic members (Total, Other, Collaboration...) -> ''."""
    m = member.split(":")[-1]
    m = re.sub(r"Member$", "", m)
    if re.search(r"(?i)^(total|other|all|product|net|collaboration|royalt|segment|us|ex|international|"
                 r"rest|corporate|alliance|license|contract|service|revenue|sales|united|europe|japan|china)", m):
        return ""
    words = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", m).split()
    return " ".join(words) if words else ""


def parse_subsidiaries(raw):
    """Exhibit 21 / 8 entity rows: same table and line logic as agent.moat.secx_subs."""
    import html as H
    rows = []
    for tr in re.split(r"(?i)<tr\b", raw)[1:]:
        cells = [" ".join(H.unescape(re.sub(r"<[^>]+>", " ", c)).split()) for c in re.split(r"(?i)</td>", tr.split("</tr>")[0])]
        cells = [c for c in cells if c and c not in ("$", ")")]
        if len(cells) >= 2 and not re.search(r"(?i)^(name|subsidiar|entity|jurisdiction|legal)", cells[0]):
            rows.append({"entity": cells[0], "country": cells[1]})
        elif len(cells) == 1 and len(cells[0]) > 3:
            rows.append({"entity": cells[0], "country": ""})
    if not rows:
        for ln in tenk.html_to_text(raw).splitlines():
            ln = ln.strip()
            if len(ln) > 3 and not re.match(r"(?i)(exhibit|subsidiaries|name of)", ln):
                parts = re.split(r"\s{2,}|\t|\s[-–—]\s|,\s(?=[A-Z][a-z]+$)", ln)
                rows.append({"entity": parts[0], "country": parts[1] if len(parts) > 1 else ""})
    rows = [dict(r, entity=r["entity"].lstrip("> ").strip()) for r in rows]
    return [r for r in rows if not re.match(r"(?i)^(name|subsidiar|exhibit|list of|legal entity|entity)", r["entity"])
            and not re.match(r"(?i)^(jurisdiction|country|state)", r["country"] or "zz")]


def ira_rows(rx, key):
    import pandas as pd
    z = zipfile.ZipFile(L.EXT / "ira_selected_drugs_mfp.zip")
    name = next(n for n in z.namelist() if n.endswith(".csv"))
    df = pd.read_csv(z.open(name), dtype=str)
    rows = []
    for i, r in df.iterrows():
        txt = " | ".join(str(v) for v in r.values if isinstance(v, str))
        m = rx.search(txt)
        if m:
            rows.append(dict({k: v for k, v in r.items()}, key=key, matched=m.group(0),
                             source=f"data/external/ira_selected_drugs_mfp.zip ({name})", source_row=f"line={i + 2}"))
    return rows


def sites_rows(rx, key):
    p = L.CACHE / "drls_reg.zip"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(L.http_get("https://www.accessdata.fda.gov/cder/drls_reg.zip", timeout=180).content)
    from agent.moat.policy_sites import EXCLUDE, country
    z = zipfile.ZipFile(p)
    name = next(n for n in z.namelist() if n.lower().endswith(".txt"))
    raw = z.read(name).decode("latin-1").splitlines()
    hdr = [h.strip() for h in raw[0].split("\t")]
    out, seen = [], set()
    for ln, line in enumerate(raw[1:], 2):
        rec = dict(zip(hdr, [x.strip() for x in line.split("\t")]))
        nm, reg = rec.get("FIRM_NAME", ""), rec.get("REGISTRANT_NAME", "")
        hit = "firm_name" if rx.search(nm) and not re.search(EXCLUDE, nm, re.I) else (
            "registrant_name" if rx.search(reg) and not re.search(EXCLUDE, reg, re.I) else "")
        if not hit or (rec.get("FEI_NUMBER"), rec.get("ADDRESS")) in seen:
            continue
        seen.add((rec.get("FEI_NUMBER"), rec.get("ADDRESS")))
        out.append({"ticker": key, "fei_number": rec.get("FEI_NUMBER"), "firm_name": nm, "registrant_name": reg,
                    "matched_on": hit, "country": country(rec.get("ADDRESS", "")), "operations": rec.get("OPERATIONS"),
                    "has_manufacture_op": "Y" if "MANUFACTURE" in (rec.get("OPERATIONS") or "") else "N",
                    "expiration_date": rec.get("EXPIRATION_DATE"),
                    "source": "https://www.accessdata.fda.gov/cder/drls_reg.zip", "source_row": f"{name} line {ln}"})
    return out


def index_and_summary(run, key, kind="company"):
    from agent.moat import index, progress
    res = run.step("index", index.add) if "index" not in run.skip else "skipped"
    cov = progress.onboard_buckets(key) if kind == "company" else progress.onboard_drug_buckets(key)
    return res, cov


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--quarters", type=int, default=10)
    ap.add_argument("--products", type=int, default=6)
    ap.add_argument("--budget", type=float, default=45, help="minutes")
    ap.add_argument("--max-8k", type=int, default=80, help="max new 8-K documents")
    ap.add_argument("--ibes", action="store_true", help="query I/B/E/S on WRDS (Duo push)")
    ap.add_argument("--skip", default="", help="comma list of steps to skip")
    ap.add_argument("--no-index", action="store_true")
    a = ap.parse_args(argv)
    c = Company(a.ticker, a)
    run = c.run
    run.skip = set(filter(None, a.skip.split(","))) | ({"index"} if a.no_index else set())
    if run.step("resolve", c.resolve) is None:
        return run.finish({"error": "resolve failed"})
    plan = [("subsidiaries", c.subsidiaries), ("sec_filings", c.sec_filings), ("xbrl_panel", c.xbrl_panel),
            ("transcripts", c.transcripts), ("attention", c.attention), ("products", c.products_step),
            ("pricing", c.pricing), ("policy", c.policy), ("consensus", c.consensus), ("insiders", c.insiders)]
    for name, fn in plan:
        if name in run.skip:
            run.log(name, "skipped", reason="--skip")
            continue
        run.step(name, fn)
    res, cov = index_and_summary(run, c.t)
    summ = run.finish({"ticker": c.t, "name": c.p.get("name"), "index": res, "coverage": cov})
    print_summary(summ)
    return summ


def print_summary(summ):
    print("\n==== onboard summary", summ.get("key"), summ.get("name") or "")
    print(f"time {summ['seconds']}s  docs {summ['docs']}  pages {summ['pages']}  tables {summ['tables']}  rows {summ['rows']}")
    for k, v in summ.get("steps", {}).items():
        print(f"  {k:14s} {v}")
    cov = summ.get("coverage") or {}
    for k, v in cov.items():
        if isinstance(v, dict) and "have" in v:
            print(f"  [{k:16s}] {v['have']}/{v['need']} {v.get('note', '')}")


if __name__ == "__main__":
    main()
