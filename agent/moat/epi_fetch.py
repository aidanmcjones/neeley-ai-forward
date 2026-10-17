"""Fetch source pages for the epi stream, save page-marked under epi/sources via common.write."""
import html
import re
import subprocess

from agent.moat.common import header, write


def text_of(raw):
    raw = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<(br|/p|/div|/li|/h\d|/tr|/table)[^>]*>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
    return re.sub(r"\n\s*\n+", "\n", raw).strip()


def fetch(name, url, pdf=False):
    p = subprocess.run(["curl", "-sL", "-m", "120", "-A", "Mozilla/5.0 (Macintosh) research", url, "-o",
                        f"/tmp/epi_{name}.bin", "-w", "%{http_code}"], capture_output=True, text=True)
    code = p.stdout.strip()
    data = open(f"/tmp/epi_{name}.bin", "rb").read()
    if code != "200":
        return code, None
    if pdf or data[:4] == b"%PDF":
        subprocess.run(["pdftotext", "-layout", f"/tmp/epi_{name}.bin", f"/tmp/epi_{name}.txt"])
        pages = open(f"/tmp/epi_{name}.txt", errors="ignore").read().split("\f")
        body = "".join(f"[[page {i} | printed {i}]]\n{pg}\n" for i, pg in enumerate(pages, 1) if pg.strip())
        n = len(pages)
    else:
        body = "[[page 1 | printed 1]]\n" + text_of(data.decode("utf-8", "ignore")) + "\n"
        n = 1
    rel = f"epi/sources/{name}.md"
    write("epi", rel, header(url) + body, group="epi", doc_type="epi_source", source_url=url, pages=n,
          quality="official")
    return code, rel
