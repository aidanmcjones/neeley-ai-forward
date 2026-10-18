"""Wave 3: fetch 10-Q text for cover-page shares and balance-sheet debt checks; print snippets.
Usage: pw3_docs.py URL_OR_CIK:ACC regex [regex ...]"""
import re, sys, time, html, pathlib, requests
UA = {"User-Agent": "Aidan Jones aidan@justinianhq.com"}
CACHE = pathlib.Path("data/moat/verify/pp_cache/w3")
CACHE.mkdir(parents=True, exist_ok=True)


def get(url):
    p = CACHE / re.sub(r"[^A-Za-z0-9.]+", "_", url.split("/Archives/edgar/data/")[-1])[-150:]
    if p.exists():
        return p.read_text()
    time.sleep(0.3)
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    p.write_text(r.text)
    return r.text


def main_doc(cik, acc):
    a = acc.replace("-", "")
    j = requests.get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/index.json", headers=UA, timeout=60).json()
    names = [x["name"] for x in j["directory"]["item"] if x["name"].endswith(".htm") and "index" not in x["name"]]
    names.sort(key=lambda n: ("ex" in n.lower(), len(n)))
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{a}/{names[0]}"


def text(raw):
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?is)<ix:header>.*?</ix:header>", " ", raw)
    raw = re.sub(r"(?i)</(td|th)>", " | ", raw)
    raw = re.sub(r"(?i)</(p|div|tr|br)>", "\n", raw)
    t = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return re.sub(r"[ \t\xa0]+", " ", t)


if __name__ == "__main__":
    src = sys.argv[1]
    url = src if src.startswith("http") else main_doc(*src.split(":"))
    t = text(get(url))
    print("URL", url, "chars", len(t))
    for pat in sys.argv[2:]:
        for m in list(re.finditer(pat, t, re.I))[:4]:
            s = t[max(0, m.start() - 300): m.end() + 400].replace("\n", " / ")
            print(f"--- [{pat}] @{m.start()}: {s}\n")
