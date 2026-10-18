"""NDC-11 map for the 52 drugs: brand packages (any labeler) and generic-ingredient packages. Writes to scratch json."""
import json, re, zipfile
from agent.drug_pack import DRUGS

z = zipfile.ZipFile("data/external/openfda_ndc.json.zip")
res = json.loads(z.read(z.namelist()[0]))["results"]
def n11(p):
    a, b, c = p.split("-")
    return a.zfill(5) + b.zfill(4) + c.zfill(2)
out = {}
for slug, (name, lab, ing, tk) in DRUGS.items():
    brand, generic = [], []
    ingw = ing.upper()
    for r in res:
        bn = (r.get("brand_name") or "").upper()
        ai = " ".join(a["name"] for a in r.get("active_ingredients", [])).upper()
        isb = bn == name or bn.startswith(name + " ")
        if isb and not (slug == "keytruda" and "QLEX" in bn) and not (slug == "opdivo" and ("QVANTIG" in bn)) and not (slug == "darzalex" and "FASPRO" in bn):
            for p in r.get("packaging", []):
                brand.append(dict(ndc11=n11(p["package_ndc"]), labeler=r["labeler_name"], brand=r["brand_name"], desc=p["description"], product_ndc=r["product_ndc"], pkg_ndc=p["package_ndc"]))
        elif ingw.split()[0] in ai and bn != name and not isb and r.get("marketing_category", "") in ("ANDA", "NDA AUTHORIZED GENERIC", "BLA") and bn != "" and False:
            pass
        if not isb and ingw in ai and r.get("marketing_category") in ("ANDA", "NDA AUTHORIZED GENERIC") and len(r.get("active_ingredients", [])) == 1:
            generic.append(dict(ndc_product=r["product_ndc"], labeler=r["labeler_name"], generic_name=r["generic_name"]))
    out[slug] = dict(brand=brand, n_generic_products=len(generic), generic_name=ing)
    print(slug, len(brand), len(generic))
json.dump(out, open("/Users/aidanjones/.claude/jobs/9174fb40/tmp/w/pricing_ndc.json", "w"))
