import gzip, json, glob, re
for t,g in [("NVO","companies"),("AZN","companies"),("GSK","peers"),("SNY","peers"),("TAK","peers"),("NVS","peers")]:
    d = json.load(gzip.open(f"data/corpus/{g}/{t}/xbrl_companyfacts.json.gz"))
    f = d["facts"]["ifrs-full"]
    print(t, [k for k in f if re.search(r"Revenue$|CostOfSales|ResearchAnd|SellingGeneral|Distribution|Administrative|Employees|Advertis|PropertyPlant.*(Purchase|Acqui)|PurchaseOfProperty|Marketing|Selling", k)])
