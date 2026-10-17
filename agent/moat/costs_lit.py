"""Page-mark the Sertkaya 2024 JAMA Netw Open XML as text and print its tables (costs stream)."""
import re
import sys
import xml.etree.ElementTree as ET

root = ET.parse("/tmp/costs_dl/sertkaya/sertkaya.xml").getroot()


def txt(e):
    return " ".join("".join(e.itertext()).split())


out = []
for tw in root.iter("table-wrap"):
    lab = txt(tw.find("label")) if tw.find("label") is not None else ""
    cap = txt(tw.find("caption")) if tw.find("caption") is not None else ""
    out.append(f"## {lab} {cap}")
    for tr in tw.iter("tr"):
        out.append(" | ".join(txt(c) for c in tr))
print("\n".join(out)[:9000])
body = txt(root.find(".//body"))
for m in re.finditer(r"[^.]*(phase 1|phase 2|phase 3|per patient|per-patient)[^.]*\.", body, re.I):
    print("TXT:", m.group(0)[:400])
