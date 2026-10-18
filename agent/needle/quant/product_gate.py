"""Numeric-gate maps for the product fine print (docs/gate_wiring.md 4, review C5, D9).

Every number product.md prints is checked by agent.needle.cite.gate. This module supplies what each number needs:

  verified    facts-row citations re-read through the status whitelist (data.fact_row_citation / fact_by_key):
              NADAC and Part D gross per claim -> pricing/gtn_proxy.csv row; list-like / net-like percents ->
              pricing/gtn_exposure.csv row; MFP, list price, % cut, TrumpRx cash prices -> policy/policy_exposure.csv
              row; analyst attention -> market/priced_in_scorecard.csv row.
  derived     the channel math (G, d, dRev per case, dOI, the dollar ranges in sentences) re-computed from operands.
  assumed     labelled: model constants (capture, GTN, shares of volume, k, m_avoided), counts the code takes from a
              cited label section ("count of ... in the cited label section"), and table values with no verified facts
              row (Medicare Part D claims and spend from the drug pack, Orange Book patent counts, the LOE curve
              quantiles): label "unverified table value: <file> <key>". The table row is named in the label and in the
              cell's JSON refs.

cell_maps(cmp_, row, ent, cell) -> (citations, derived, assumptions)
channel_maps(cmp_, ch) -> (citations, derived, assumptions)
limiter_maps(cmp_, top, reasons_ctx) -> (citations, derived, assumptions)
"""

import re

from agent.needle.cite.gate import derived_entry

from . import data as DATA
from . import weights as W

TABLE = "unverified table value: {file} {key} (no verified facts row; see the JSON refs)"
COUNT = "count of {what} in the cited label section (counted by code from the label text)"
CONST = "constant: {name} (ASSUMED scenario parameter, no published elasticity)"
NOTE_A = {"loe_horizon": {"value": "6", "label": "design: LOE channel horizon of 6 years (product.py _channels)"}}


def _f(x):
    try:
        return float(str(x).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return None


def _assume(A, key, value, label, unit=""):
    v = _f(value)
    if v is None:
        return
    A[key] = {"value": f"{v:.12g}", "label": label, "unit": unit}


def _leaves(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _leaves(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _leaves(v, f"{path}[{i}]")
    elif isinstance(obj, bool) or obj is None:
        return
    elif isinstance(obj, (int, float)):
        yield path, float(obj)
    elif isinstance(obj, str):
        for m in re.finditer(r"-?\d[\d,]*(?:\.\d+)?", obj):
            if re.fullmatch(r"(?:19|20)\d\d", m.group()):
                continue
            yield path, float(m.group().replace(",", ""))


def _fact(table, fld, value, **kw):
    try:
        c = DATA.fact_row_citation(table, fld, value, **kw)
    except Exception:
        return None
    return c if c.verification.ok else None


# ------------------------------------------------------------------ table cells
BPCIA = "design rule: 12-year US reference-product exclusivity for biologics (42 U.S.C. 262(k)(7)), counted from approval"


def _date_label(A, key, value, label):
    if value not in (None, ""):
        A[key] = {"value": str(value), "label": label, "kind": "date"}


def _timeline_dates(cmp_, ent, det, cites, A):
    """Dates in a timeline cell (gate.date_check): the company-stated LOE is cited to its pipeline/loe_calendar.csv
    row (a 10-K page citation through facts.locator when the row verifies); Orange Book, Purple Book and the derived
    12-year date are table values with no verified facts row, labelled with their file (review verify2 3)."""
    slug = ent.get("slug") or ""
    cs = det.get("company_stated") or {}
    if cs.get("us_loe"):
        try:
            from . import verified_tables as VT
            got = VT.loe(ent.get("ticker") or cmp_.ticker, (ent.get("name") or slug).split(" ")[0])
            if got and got[1].citations and got[1].citations[0].verification.ok:
                cites.append(got[1].citations[0])
        except Exception:
            pass
    pb = det.get("purple_book") or {}
    _date_label(A, "pb.12y", pb.get("derived_12y"), TABLE.format(file=f"data/corpus/drugs/{slug}/purple_book.csv",
                                                                  key="approval date + 12 years (BPCIA rule)"))
    A["pb.12y.rule"] = {"value": "12y", "label": BPCIA, "kind": "date"}
    for k, v in (pb.get("exclusivity") or {}).items():
        _date_label(A, f"pb.{k}", v, TABLE.format(file=f"data/corpus/drugs/{slug}/purple_book.csv", key=k))
    pe = str(det.get("protection_end_regulatory") or "")
    src = "orange_book_patents.csv / purple_book.csv"
    _date_label(A, "pe", pe, TABLE.format(file=f"data/corpus/drugs/{slug}/{src}", key="protection end"))
    _date_label(A, "pe.year", pe[:4], TABLE.format(file=f"data/corpus/drugs/{slug}/{src}", key="protection end year"))
    _date_label(A, "ob.latest", det.get("orange_book_latest_patent"),
                TABLE.format(file=f"data/corpus/drugs/{slug}/orange_book_patents.csv", key="latest patent expiry"))
    for x in det.get("orange_book_exclusivity") or []:
        _date_label(A, f"ob.{x.get('code')}", x.get("date"),
                    TABLE.format(file=f"data/corpus/drugs/{slug}/orange_book_exclusivity.csv", key=x.get("code")))


def cell_maps(cmp_, row, ent, cell):
    cites, Dm, A = [], {}, {}
    slug = ent.get("slug") or ""
    det = cell.detail or {}
    # review verify2 3: no blanket labels on label-row numbers. Counts derive from cited items (count operands);
    # what is left must verify in a quote or fail.
    if row == "approved_uses" and det.get("names") is not None:
        from .gatewire import indication_count
        got = indication_count(slug)
        if got and got[0] == len(det["names"]):
            n, ops, cl = got
            cites += cl
            Dm["n_uses"] = derived_entry(n, " + ".join(ops), ops)
    if row == "safety":
        byid = {c.cite_id: c for c in cell.citations if c.verification.ok}
        wc = [byid[i] for i in det.get("warning_cite_ids") or [] if i in byid]
        titles = det.get("warnings_and_precautions") or []
        if titles and len(wc) == len(titles) and len(set(det["warning_cite_ids"])) == len(titles):
            Dm["n_warn"] = derived_entry(len(wc), " + ".join(f"w{i}" for i in range(len(wc))),
                                         {f"w{i}": {"value": 1, "citation": c, "count": True} for i, c in enumerate(wc)})
        if det.get("contraindications") == 0 and det.get("contra_cite_id") in byid:
            _assume(A, "ci0", 0, COUNT.format(what="contraindication items (label section 4 lists none; cited)"))
    if row == "dosing":
        for path, v in _leaves({k: x for k, x in det.items() if k in ("doses_per_year",)}):
            _assume(A, f"dosing.{path}", v, "derived by code from the cited dosing interval: doses per year")
    if row == "timeline":
        f = f"data/corpus/drugs/{slug}/orange_book_patents.csv"
        _timeline_dates(cmp_, ent, det, cites, A)
        for path, v in _leaves(det):
            _assume(A, f"tl.{path}", v, TABLE.format(file=f if "orange" in path else "drug pack", key=path))
        cnt = re.search(r"\((\d+) patents\)", cell.value or "")
        if cnt:
            _assume(A, "patents", cnt.group(1), TABLE.format(file=f, key="patent rows"))
        disc = re.search(r"(\d+) year\(s\) (?:later|earlier)", cell.value or "")
        cs = (det.get("company_stated") or {}).get("us_loe")
        ob = str(det.get("protection_end_regulatory") or "")[:4]
        if disc and cs and ob.isdigit() and re.search(r"\d{4}", str(cs)):
            y = int(re.search(r"\d{4}", str(cs)).group())
            Dm["loe_gap"] = derived_entry(abs(int(ob) - y), "abs(a - b)", {
                "a": {"value": int(ob), "assumption": TABLE.format(file=f, key="protection end year")},
                "b": {"value": y, "assumption": "company-stated LOE year (cited 10-K row)"}})
    if row == "pricing":
        gp = det.get("price_proxies") or {}
        yr = gp.get("year")
        for k, v in gp.items():
            if k in ("year", "asp_hcpcs"):
                continue
            c = _fact("pricing/gtn_proxy.csv", k, v, where={"drug": slug, "year": yr}) if yr else None
            if c is not None:
                cites.append(c)
            else:
                _assume(A, f"gp.{k}", v, TABLE.format(file="verified/pricing/gtn_proxy.csv", key=f"{slug}|{yr} {k}"))
        ge = det.get("gtn_exposure") or {}
        for k in ("list_like_pct", "net_like_pct"):
            if ge.get(k) is not None:
                c = _fact("pricing/gtn_exposure.csv", k, ge[k], where={"drug": slug})
                if c is not None:
                    cites.append(c)
                else:
                    _assume(A, f"ge.{k}", ge[k], TABLE.format(file="verified/pricing/gtn_exposure.csv", key=f"{slug} {k}"),
                            "%")
        call = str(ge.get("exposure_call") or "")
        for i, (path, v) in enumerate(_leaves(call)):
            _assume(A, f"ge.call{i}", v, TABLE.format(file="verified/pricing/gtn_exposure.csv", key=f"{slug} exposure_call"))
            _assume(A, f"ge.callp{i}", v, TABLE.format(file="verified/pricing/gtn_exposure.csv", key=f"{slug} exposure_call"),
                    "%")
        for x in det.get("ira", []) + det.get("mfn_cash", []):
            rid = x.get("row_id")
            c = None
            if rid:
                try:
                    c = DATA.fact_by_key("policy/policy_exposure.csv", rid, "value", value=x.get("value"))
                except Exception:
                    c = None
            if c is not None and c.verification.ok:
                cites.append(c)
                if "percent" in str(x.get("unit", "")).lower() and _f(x.get("value")) is not None:
                    Dm[f"pol.{rid}"] = derived_entry(_f(x["value"]), "a", {"a": (_f(x["value"]), c)}, "%")
            else:
                for path, v in _leaves(x.get("value")):
                    _assume(A, f"pol.{rid}.{path}", v, TABLE.format(file="verified/policy/policy_exposure.csv", key=rid))
        if re.search(r"30-day", cell.value or ""):
            _assume(A, "days30", 30, "unit of the CMS price: a 30-day supply")
        ira = det.get("ira_status") or {}
        if ira.get("mfp_per_30_days") is not None:
            _assume(A, "ira_mfp", ira["mfp_per_30_days"], TABLE.format(file=f"data/corpus/drugs/{slug} ira profile",
                                                                       key="mfp_per_30_days"))
        for path, v in _leaves({k: v for k, v in det.items() if k in ("medicare", "company_gtn_anchor")}):
            _assume(A, f"pr.{path}", v, TABLE.format(file="drug pack / company_list_vs_net.csv", key=path))
    return cites, Dm, A


# ------------------------------------------------------------------ channel math
def channel_maps(cmp_, ch):
    """(citations, derived, assumptions) for one channel dict from product._channels."""
    from . import product as P
    i, ch_name = ch["inputs"], ch["channel"]
    cites, Dm, A = [], {}, {}
    me = cmp_.entities[0]
    slug = me.get("slug") or ""
    cases = ("bull", "base", "bear")
    ops = {}
    exprs = {}
    if ch_name == "ira_mfp":
        claims = {"value": i["claims"], "assumption": TABLE.format(file=f"data/corpus/drugs/{slug}/medicare_partd_spending.csv",
                                                                   key="Part D claims")}
        lp = {"value": i["list30"], "assumption": TABLE.format(file="policy_exposure / drug pack", key="list price per 30 days")}
        mp = {"value": i["mfp30"], "assumption": TABLE.format(file="policy_exposure / drug pack", key="MFP per 30 days")}
        for x in cmp_.rows["pricing"][me["name"]].detail.get("ira", []):
            c = DATA.fact_by_key("policy/policy_exposure.csv", x["row_id"], "value", value=x["value"])
            if c.verification.ok and _f(x["value"]) == _f(i["list30"]):
                lp = (i["list30"], c)
                cites.append(c)
            if c.verification.ok and _f(x["value"]) == _f(i["mfp30"]):
                mp = (i["mfp30"], c)
                cites.append(c)
        ops = {"n": claims, "l": lp, "p": mp}
        k = i["k"] if isinstance(i["k"], tuple) else (i["k"],) * 3
        for j, case in enumerate(cases):
            ops[f"k{j}"] = {"value": k[j], "assumption": "constant: IRA class factor k (impact.ira_class_rule)"}
            ops[f"m{j}"] = {"value": W.M_MDP_AVOIDED[j], "assumption": "constant: M_MDP_AVOIDED (CMS MDP guidance)"}
            exprs[case] = f"-(n * l) * max(0, k{j} * (1 - p / l) - m{j})"
        Dm["G"] = derived_entry(i["claims"] * i["list30"], "n * l", {"n": claims, "l": lp})
        Dm["d"] = derived_entry((1 - i["mfp30"] / i["list30"]) * 100, "(1 - p / l) * 100", {"p": mp, "l": lp}, "%")
        Dm["gap30"] = derived_entry(i["list30"] - i["mfp30"], "l - p", {"l": lp, "p": mp})
        _assume(A, "days30", 30, "unit of the CMS price: a 30-day supply")
    elif ch_name == "ira_expected":
        sp = {"value": i["medicare_spend"], "assumption": TABLE.format(
            file=f"data/corpus/drugs/{slug}/medicare_part*_spending.csv", key=f"{i['year']} gross spend")}
        import statistics
        cuts = sorted(i["cuts_pct"])
        q = statistics.quantiles(cuts, n=4)
        qs = (q[0], statistics.median(cuts), q[2])
        lab = "quartile / median of the verified CMS negotiated cuts (policy_exposure.csv IRA rows, computed by code)"
        from . import impact as IM
        prof = P._labels().profile(slug)
        part_d = ((prof["medicare"]["value"] or {}).get("part") == "D")
        kk, low = IM.ira_class_k(me["name"], P._indication_text(prof))
        kk = kk if isinstance(kk, tuple) else (kk,) * 3
        mm = W.M_MDP_AVOIDED if part_d else (0.0, 0.0, 0.0)
        for j, case in enumerate(cases):
            ops[f"d{j}"] = {"value": qs[j] / 100, "assumption": lab}
            _assume(A, f"cut{j}", qs[j], lab)
            _assume(A, f"cutp{j}", qs[j], lab, "%")
            ops[f"k{j}"] = {"value": kk[j], "assumption": "constant: IRA class factor k"}
            ops[f"m{j}"] = {"value": mm[j], "assumption": "constant: M_MDP_AVOIDED (0 for Part B)"}
            exprs[case] = f"-s * max(0, k{j} * d{j} - m{j})"
        ops["s"] = sp
        _assume(A, "spend", i["medicare_spend"], sp["assumption"])
        _assume(A, "ncuts", len(cuts), lab)
    elif ch_name == "loe_erosion":
        rv = {"value": i["revenue"], "assumption": TABLE.format(file="product_revenue_quarterly.csv / IP table",
                                                                key="annual product revenue")}
        rc = cmp_.context.get("_revenue_cite")
        if rc is not None and getattr(rc, "verification", None) is not None and rc.verification.ok and rc.value:
            # case audit H3: the revenue operand is the cited product-sales line (value in USD millions on the page)
            rv = {"value": i["revenue"], "citation": rc, "text": str(rc.value), "unit": ""}
        band = i["band"]
        lab = TABLE.format(file="agent/cache/loe_curves.csv", key=f"{i['modality']} US t=1 pct_of_peak quantiles")
        qv = {"bull": band["q75"], "base": band["median"], "bear": band["q25"]}
        for case in cases:
            ops[f"q_{case}"] = {"value": qv[case], "assumption": lab}
            _assume(A, f"q_{case}", qv[case], lab)
            _assume(A, f"qp_{case}", qv[case], lab, "%")
            exprs[case] = f"-r * (1 - q_{case} / 100)"
        ops["r"] = rv
        _assume(A, "n", band["n"], lab)
        Dm["erosion"] = derived_entry(100 - band["median"], "100 - q", {"q": {"value": band["median"], "assumption": lab}},
                                      "%")
        if rc is not None:
            cites.append(rc)
    elif ch_name == "label_breadth_medicare":
        f = "data/corpus/drugs/<slug>/medicare_partd_spending.csv"
        rc_ = {"value": i["rival_claims"], "assumption": TABLE.format(file=f, key=f"{i['rival']} {i['year']} claims")}
        oc = {"value": i["own_claims"], "assumption": TABLE.format(file=f, key=f"{me['name']} {i['year']} claims")}
        med = P._labels().profile(slug)["medicare"]["value"] or {}
        avg = {"value": med.get("avg_per_claim"), "assumption": TABLE.format(file=f, key=f"{me['name']} {i['year']} "
                                                                                       "gross spend per claim")}
        for case, cap, g in (("bear", 0.50, 0.50), ("base", 0.35, 0.60), ("bull", 0.20, 0.70)):
            ops[f"c_{case}"] = {"value": cap, "assumption": CONST.format(name="capture rate")}
            ops[f"g_{case}"] = {"value": g, "assumption": CONST.format(name="GTN")}
            exprs[case] = f"-(rc - oc) * c_{case} * a * (1 - g_{case})"
        ops.update({"rc": rc_, "oc": oc, "a": avg})
        for key, v in (("rc", i["rival_claims"]), ("oc", i["own_claims"]), ("avg", med.get("avg_per_claim"))):
            _assume(A, key, v, (rc_ if key == "rc" else oc if key == "oc" else avg)["assumption"])
        _assume(A, "ri", i["rival_indications"], COUNT.format(what=f"{i['rival']} approved uses"))
        _assume(A, "oi", i["own_indications"], COUNT.format(what=f"{me['name']} approved uses"))
        for v in (50, 35, 20, 60, 70):
            _assume(A, f"cg{v}", v, CONST.format(name="capture / GTN percent"))
            _assume(A, f"cgp{v}", v, CONST.format(name="capture / GTN percent"), "%")
    elif ch_name == "mfn_cash_price":
        pr = cmp_.rows["pricing"][me["name"]]
        cash = {"value": i["cash"], "assumption": TABLE.format(file="verified/policy/policy_exposure.csv",
                                                               key="TrumpRx cash price")}
        for x in pr.detail.get("mfn_cash", []):
            c = DATA.fact_by_key("policy/policy_exposure.csv", x["row_id"], "value", value=x["value"])
            if c.verification.ok and f"${i['cash']:,.0f}" in str(x["value"]):
                cash = {"value": i["cash"], "citation": c, "text": f"${i['cash']:,.0f}"}
                cites.append(c)
        lst = {"value": i["list_month"], "assumption": TABLE.format(file="White House page", key="list per month")}
        for c in pr.citations:
            if re.search(r"from \$" + re.escape(f"{i['list_month']:,.0f}") + r" per month", c.quote or ""):
                lst = {"value": i["list_month"], "citation": c, "text": f"${i['list_month']:,.0f}"}
                cites.append(c)
        rv = {"value": i["revenue"], "assumption": TABLE.format(file="product_revenue_quarterly.csv / IP table",
                                                                key="annual product revenue")}
        rc = cmp_.context.get("_revenue_cite")
        if rc is not None:
            cites.append(rc)
        for case, sh in (("bear", 0.40), ("base", 0.25), ("bull", 0.10)):
            ops[f"s_{case}"] = {"value": sh, "assumption": CONST.format(name="share of volume moved to the cash price")}
            exprs[case] = f"-r * s_{case} * (1 - c / l)"
        ops.update({"r": rv, "c": cash, "l": lst})
        Dm["cut"] = derived_entry((1 - i["cash"] / i["list_month"]) * 100, "(1 - c / l) * 100", {"c": cash, "l": lst}, "%")
        Dm["rev_b"] = derived_entry(i["revenue"], "r", {"r": rv})
        for v in (40, 25, 10):
            _assume(A, f"sh{v}", v, CONST.format(name="share of volume moved"))
            _assume(A, f"shp{v}", v, CONST.format(name="share of volume moved"), "%")
    elif ch_name == "boxed_warning_share":
        rv = {"value": i["revenue"], "assumption": TABLE.format(file="product_revenue_quarterly.csv / IP table",
                                                                key="annual product revenue")}
        for case, sh in (("bear", 0.25), ("base", 0.10), ("bull", 0.0)):
            ops[f"s_{case}"] = {"value": sh, "assumption": "constant: boxed warning volume loss (pharma_impact_math KQ6)"}
            exprs[case] = f"-r * s_{case}"
        ops["r"] = rv
        for v in (10, 25, 12, 18):
            _assume(A, f"bw{v}", v, "constant: boxed warning 10-25% of US volume over 12-18 months (KQ6)")
            _assume(A, f"bwp{v}", v, "constant: boxed warning 10-25% of US volume over 12-18 months (KQ6)", "%")
    for key, o in ops.items():        # every labelled operand printed in the formula is labelled where it prints
        if isinstance(o, dict) and "assumption" in o:
            _assume(A, f"op.{key}", o["value"], o["assumption"])
    for case, expr in exprs.items():
        v = ch["dRev"][case]
        Dm[f"dRev_{case}"] = derived_entry(v, expr, ops)
        Dm[f"dRevR_{case}"] = derived_entry(round(v), "round(x)", {"x": {"derived": f"dRev_{case}"}})
        Dm[f"dRevAbs_{case}"] = derived_entry(abs(v), "abs(x)", {"x": {"derived": f"dRev_{case}"}})
        Dm[f"dOI_{case}"] = derived_entry(round(v * ch["cm"]), "round(x * cm)", {
            "x": {"derived": f"dRev_{case}"}, "cm": {"value": ch["cm"], "assumption": "constant: contribution margin CM"}})
    _assume(A, "cm", ch["cm"], "constant: contribution margin CM (spec 4.3: 1.0 price-led, 0.70 volume-led)")
    if "revenue" in i:
        Dm["rev"] = derived_entry(i["revenue"], "r", {"r": ops.get("r") or {"value": i["revenue"], "assumption":
                                                                            TABLE.format(file="product revenue", key="")}})
    return cites, Dm, A


def limiter_maps(cmp_, top, topic_rows):
    """Citations for the priced-in reasons: the market/priced_in_scorecard.csv facts row of each topic."""
    cites, Dm, A = [], {}, {}
    for topic, sc in topic_rows:
        if not sc:
            continue
        for fld, unit, scale in (("share_of_quarters_asked", "%", 100), ("analyst_turns_on_topic", "", 1),
                                 ("share_of_all_analyst_turns", "%", 100)):
            v = sc.get(fld)
            c = _fact("market/priced_in_scorecard.csv", fld, v, ticker=cmp_.ticker, where={"topic": topic})
            if c is None:
                _assume(A, f"{topic}.{fld}", (_f(v) or 0) * scale, TABLE.format(file="verified/market/priced_in_scorecard.csv",
                                                                               key=f"{cmp_.ticker} {topic} {fld}"), unit)
                continue
            cites.append(c)
            if scale != 1:
                Dm[f"{topic}.{fld}"] = derived_entry(_f(v) * scale, "x * 100", {"x": (_f(v), c)}, unit)
    return cites, Dm, A
