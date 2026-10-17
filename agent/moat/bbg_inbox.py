"""Pull Parker's Bloomberg exports out of Aidan's inbox into data/corpus/_inbox/bloomberg/.

Parker shares the terminal PDFs through Adobe cloud links (and sometimes as attachments). This script reads Mail.app,
finds every Adobe share link or PDF attachment from Parker in the last 2 days, downloads each new one through the
logged-in Chrome tab (Adobe's share page is a JS app, so curl only gets HTML), and files it with a tidy name plus a
sidecar .json holding the original title, link, sender and time. Idempotent: a seen.json keeps the links done.

Run:  python -m agent.moat.bbg_inbox            # one pass
      python -m agent.moat.bbg_inbox --watch    # every 2 minutes
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
INBOX = ROOT / "data" / "corpus" / "_inbox" / "bloomberg"
SEEN = INBOX / "seen.json"
DOWNLOADS = Path.home() / "Downloads"
DL_SCRIPT = Path(__file__).with_name("adobe_dl.applescript")
SENDERS = ("parkerkingsbury", "kingsbury")
TICKERS = {"astrazeneca": "AZN", "gilead": "GILD", "novo nordisk": "NVO", "amgen": "AMGN", "merck": "MRK",
           "bristol": "BMY", "pfizer": "PFE", "lilly": "LLY", "abbvie": "ABBV", "johnson": "JNJ"}

MAIL_AS = '''
tell application "Mail"
  set out to ""
  set msgs to (messages of inbox whose date received > ((current date) - 2 * days))
  repeat with m in msgs
    set s to sender of m
    if (s contains "kingsbury") or (s contains "Kingsbury") or (s contains "KINGSBURY") then
      set out to out & "<<MSG>>" & (date received of m as string) & "<<F>>" & s & "<<F>>" & subject of m & "<<F>>"
      repeat with a in mail attachments of m
        set out to out & (name of a) & ";"
      end repeat
      set out to out & "<<F>>" & content of m & linefeed
    end if
  end repeat
  return out
end tell
'''


def mail_messages():
    raw = subprocess.run(["osascript", "-e", MAIL_AS], capture_output=True, text=True).stdout
    out = []
    for chunk in raw.split("<<MSG>>")[1:]:
        parts = chunk.split("<<F>>")
        if len(parts) < 5:
            continue
        date, sender, subject, atts, body = parts[:5]
        links = sorted(set(re.findall(r"https://acrobat\.adobe\.com/id/[A-Za-z0-9:%._-]+", body)))
        out.append({"date": date, "sender": sender, "subject": subject, "attachments": [a for a in atts.split(";") if a],
                    "links": links, "body": body[:400]})
    return out


def tidy_name(title, subject):
    text = f"{title} {subject}"
    tk = next((v for k, v in TICKERS.items() if k in text.lower()), "UNK")
    m = re.search(r"Earnings Call (\d{4})(\d{2,4})\b", text)
    if m:
        y, rest = int(m.group(1)), m.group(2)
        # Bloomberg writes the call date without zero padding: 2026429 = Apr 29, 2026506 = May 6, 20251106 = Nov 6
        mo = next((int(rest[:k]) for k in (2, 1) if 1 <= int(rest[:k]) <= 12 and 1 <= int(rest[k:] or "0") <= 31), None)
        if mo is None:
            return f"{tk}_{re.sub(r'[^A-Za-z0-9._-]+', '_', title)[:80]}.pdf"
        # a call held in month mo reports the quarter that ended the month before (Apr call = Q1, Jul = Q2, Oct/Nov = Q3, Jan/Feb = Q4 prior year)
        q = {1: ("Q4", y - 1), 2: ("Q4", y - 1), 3: ("Q4", y - 1), 4: ("Q1", y), 5: ("Q1", y), 6: ("Q1", y),
             7: ("Q2", y), 8: ("Q2", y), 9: ("Q2", y), 10: ("Q3", y), 11: ("Q3", y), 12: ("Q3", y)}[mo]
        return f"{tk}_{q[1]}{q[0]}_transcript_bbg.pdf"
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", title)[:80]
    return f"{tk}_{base}.pdf"


def download(link):
    before = {p.name for p in DOWNLOADS.glob("*.pdf")}
    res = subprocess.run(["osascript", str(DL_SCRIPT), link], capture_output=True, text=True, timeout=180)
    title = res.stdout.strip().split("|")[-1].strip().replace(" - Adobe cloud storage", "")
    for _ in range(30):
        new = [p for p in DOWNLOADS.glob("*.pdf") if p.name not in before and not p.name.endswith(".crdownload")]
        if new and all(time.time() - p.stat().st_mtime > 2 for p in new):
            return title, max(new, key=lambda p: p.stat().st_mtime), res.stdout.strip()
        time.sleep(2)
    return title, None, res.stdout.strip()


def one_pass():
    INBOX.mkdir(parents=True, exist_ok=True)
    seen = json.loads(SEEN.read_text()) if SEEN.exists() else {}
    got = []
    for msg in mail_messages():
        for link in msg["links"]:
            if link in seen:
                continue
            title, path, log = download(link)
            if not path:
                print(f"FAILED {link} ({log})", flush=True)
                continue
            name = tidy_name(title, msg["subject"])
            dest = INBOX / name
            if dest.exists():
                dest = INBOX / (dest.stem + "_" + datetime.now().strftime("%H%M%S") + ".pdf")
            shutil.move(str(path), dest)
            dest.with_suffix(".json").write_text(json.dumps({"title": title, "link": link, "sender": msg["sender"],
                                                             "received": msg["date"], "subject": msg["subject"],
                                                             "source_quality": "official_bloomberg"}, indent=1))
            seen[link] = {"file": dest.name, "at": datetime.now().isoformat()}
            SEEN.write_text(json.dumps(seen, indent=1))
            got.append(dest.name)
            print(f"GOT {dest.name}  <- {title}", flush=True)
        for a in msg["attachments"]:
            if a.lower().endswith(".pdf") and a not in seen:
                print(f"ATTACHMENT (not auto-saved yet): {a} in '{msg['subject']}'", flush=True)
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true")
    args = ap.parse_args()
    while True:
        try:
            got = one_pass()
            if not got:
                print(f"{datetime.now():%H:%M} nothing new", flush=True)
        except Exception as e:  # keep watching
            print(f"ERROR {type(e).__name__}: {e}", flush=True)
        if not args.watch:
            break
        time.sleep(120)


if __name__ == "__main__":
    main()
