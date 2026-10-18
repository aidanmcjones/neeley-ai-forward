"""Optional live-model server for the NEEDLE cockpit's Ask screen (stdlib http.server only).

Run from the worktree root:

    PYTHONPATH=. python ui/server.py --port 8787

GET  /api/health -> {"live": true} only when ANTHROPIC_API_KEY is set in the environment or in
                    .env at the repo root (python-dotenv if installed, else a minimal parser).
POST /api/ask    {ticker, question} -> {text, cites, trace, rejected_cites, removed_claims,
                    unsupported_numbers, model, cached}

The answer is grounded: the same term-overlap retrieval as ui/src/lib/retrieve.ts (a simple port)
picks the company's findings, agent.llm.call() gets ONLY those findings as context with a system
prompt that forbids numbers or quotes not in them and requires [finding_id] cites, and the reply
is then verified: unknown [ids] are stripped (rejected_cites), sentences left without a valid
cite are removed (removed_claims), and any number not present in the context is reported
(unsupported_numbers). Without a key the server answers {"live": false} and /api/ask refuses,
so the UI stays offline. Live output is never faked.

The browser calls http://localhost:8787 directly (no Vite proxy), so every response carries
Access-Control-Allow-Origin: *.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "ui" / "public" / "data" / "companies"


def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(env)
        return
    except ImportError:
        pass
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip().removeprefix("export ").strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def is_live() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


# ------------------------------------------------------------------ retrieval (port)

STOP = set(
    """a an the and or but if then of to in on at by for with from into about as is are was were be been being do does
did have has had it its this that these those there here what which who whom whose why how when where i me my we our us
you your he she they them their his her than so very can could should would will may might must just also any all some
more most much many such not no only own same too vs versus please tell show give explain describe company""".split()
)
GROUPS = {
    "ira": ["ira", "negotiation", "negotiated", "medicare", "mfp", "cms", "ipay"],
    "loe": ["loe", "exclusivity", "generic", "biosimilar", "patent", "cliff", "expiry", "protection"],
    "gtn": ["gtn", "rebate", "net", "discount", "340b", "pricing", "price", "nadac", "wac"],
    "inventory": ["inventory", "channel", "stocking", "stock", "days", "dio", "wholesaler"],
    "receivables": ["receivables", "receivable", "dso"],
    "call": ["call", "qa", "deflect", "analyst", "analysts", "asked", "transcript"],
    "label": ["label", "indication", "indications", "boxed", "dosing", "dose", "rems", "route"],
    "mfn": ["mfn", "favored"],
    "tariff": ["tariff", "tariffs", "manufacturing", "sites", "supply"],
    "forecast": ["forecast", "predict", "q3", "guidance", "consensus"],
    "margin": ["margin", "margins"],
    "tax": ["tax", "etr"],
    "rnd": ["rnd", "research", "pipeline"],
}
WORD_GROUP = {w: g for g, ws in GROUPS.items() for w in ws}


def stem(w: str) -> str:
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def terms(text: str) -> set[str]:
    low = re.sub(r"q\s*&\s*a", " qa ", (text or "").lower())
    low = re.sub(r"r\s*&\s*d", " rnd ", low).replace("_", " ")
    out: set[str] = set()
    for t in re.split(r"[^a-z0-9.]+", low):
        t = t.strip(".")
        if len(t) < 2 or t in STOP:
            continue
        out.add(stem(t))
        g = WORD_GROUP.get(t) or WORD_GROUP.get(stem(t))
        if g:
            out.add("#" + g)
    return out


def finding_text(f: dict) -> str:
    v = f.get("vector") or {}
    ev = f.get("evidence") or []
    return " ".join(
        [f.get("finding") or "", f.get("signal_kind") or "", " ".join(v.get("topics") or [])]
        + [e.get("quote") or "" for e in ev[:2]]
    )


def retrieve(company: dict, question: str, k: int = 8) -> list[dict]:
    fs = company.get("findings") or []
    docs = [(f, terms(finding_text(f))) for f in fs]
    df: dict[str, int] = {}
    for _, ts in docs:
        for t in ts:
            df[t] = df.get(t, 0) + 1
    n = max(1, len(docs))
    q = terms(question)
    scored = []
    for f, ts in docs:
        s = sum(math.log(1 + n / df[t]) * (0.7 if t.startswith("#") else 1.0) for t in q if t in ts)
        if f.get("verdict") != "verified":
            s *= 0.6
        if s > 0:
            scored.append((s, f.get("score") or 0, f))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    seen, out = set(), []
    for _, _, f in scored:
        key = (f.get("finding") or "").strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
        if len(out) >= k:
            break
    return out


def context_for(findings: list[dict]) -> dict[str, str]:
    ctx = {}
    for f in findings:
        imp = (f.get("impact") or {}).get("formula") or ""
        v = f.get("vector") or {}
        lines = [f"finding: {f.get('finding')}", f"verdict: {f.get('verdict')}", f"signal: {f.get('signal_kind')}"]
        if imp:
            lines.append(f"impact formula: {imp}")
        if v.get("obscurity_note"):
            lines.append(f"obscurity: {v['obscurity_note']}")
        for e in (f.get("evidence") or [])[:2]:
            lines.append(f"quote ({e.get('citation')}): {e.get('quote')}")
        ctx[f["id"]] = "\n".join(lines)
    return ctx


SYSTEM = (
    "You answer questions for a pharmaceutical CEO using ONLY the findings provided as documents. "
    "Each document's source name is a finding id. Rules: (1) Every sentence must end with one or more "
    "cites in square brackets using the exact finding id, like [LLY-forensics-185801]. (2) Do not state "
    "any number, date, percentage or quote that does not appear verbatim in the provided findings. "
    "(3) Do not use outside knowledge. (4) If the findings do not answer the question, say exactly: "
    "'The verified findings do not answer this.' (5) At most 5 sentences, plain prose, no headings, no lists."
)

CITE_RE = re.compile(r"\[([A-Za-z0-9_.:-]+)\]")
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def verify(text: str, ctx: dict[str, str]) -> dict:
    valid = set(ctx)
    rejected = sorted({m for m in CITE_RE.findall(text) if m not in valid})
    cleaned = CITE_RE.sub(lambda m: m.group(0) if m.group(1) in valid else "", text)
    sentences = re.split(r"(?<=[.!?\]])\s+(?=[A-Z'\"(])", cleaned.strip())
    kept, removed = [], []
    for s in sentences:
        s = re.sub(r"\s{2,}", " ", s).strip()
        if not s:
            continue
        if CITE_RE.search(s) or s.startswith("The verified findings do not answer"):
            kept.append(s)
        else:
            removed.append(s)
    out = " ".join(kept)
    blob = " ".join(ctx.values()).replace(",", "")
    plain = CITE_RE.sub("", out)
    unsupported = sorted({x for x in NUM_RE.findall(plain) if x.replace(",", "") not in blob})
    cites = []
    for m in CITE_RE.findall(out):
        if m not in cites:
            cites.append(m)
    return {"text": out, "cites": cites, "rejected_cites": rejected, "removed_claims": removed, "unsupported_numbers": unsupported}


def answer(ticker: str, question: str) -> dict:
    path = DATA / f"{ticker}.json"
    if not path.exists():
        return {"error": f"Could not load /data/companies/{ticker}.json"}
    company = json.loads(path.read_text())
    found = retrieve(company, question)
    if not found:
        return {"text": "The verified findings do not answer this.", "cites": [], "trace": [], "rejected_cites": [], "removed_claims": [], "unsupported_numbers": []}
    ctx = context_for(found)
    from agent.llm import call  # imported lazily: needs anthropic installed and a key

    prompt = f"Company: {company.get('name') or ticker} ({ticker}).\nQuestion: {question}\nAnswer from the findings above, citing [finding_id] after every sentence."
    out = call(prompt, ctx, system=SYSTEM)
    v = verify(out.get("text") or "", ctx)
    by_id = {f["id"]: f for f in found}
    trace = []
    for fid in v["cites"]:
        for e in (by_id[fid].get("evidence") or [])[:2]:
            label = e.get("citation") or e.get("doc_id")
            if label and label not in trace:
                trace.append(label)
    return {**v, "trace": trace, "model": out.get("model"), "cached": bool(out.get("cached"))}


# ------------------------------------------------------------------------------ http


class Handler(BaseHTTPRequestHandler):
    server_version = "needle-ask/1"

    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:  # CORS preflight
        self._send(204, {})

    def do_GET(self) -> None:
        if self.path.split("?")[0] == "/api/health":
            self._send(200, {"live": is_live()})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path.split("?")[0] != "/api/ask":
            self._send(404, {"error": "not found"})
            return
        if not is_live():
            self._send(503, {"live": False, "error": "ANTHROPIC_API_KEY is not set; live mode is off"})
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            ticker = str(body.get("ticker") or "").upper()
            question = str(body.get("question") or "").strip()
            if not re.fullmatch(r"[A-Z]{1,6}", ticker) or not question:
                self._send(400, {"error": "need {ticker, question}"})
                return
            out = answer(ticker, question[:500])
            self._send(404 if "error" in out else 200, out)
        except Exception as e:  # report honestly; the UI falls back to offline
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt: str, *args) -> None:
        print("[needle-ask]", fmt % args)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    load_env()
    print(f"[needle-ask] http://{a.host}:{a.port}  live={is_live()}  data={DATA}")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
