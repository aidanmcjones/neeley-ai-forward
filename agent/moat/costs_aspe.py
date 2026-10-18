import pymupdf
d = pymupdf.open("/tmp/costs_dl/aspe/rpt_erg.pdf")
for n in (30, 31):
    print("=== PAGE", n)
    print(" ".join(d[n-1].get_text().split())[:3500])
