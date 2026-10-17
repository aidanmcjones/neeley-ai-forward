"""Serve the citation viewer route with the standard library only (review D6, C14).

    python -m agent.needle.cite.viewer_server --port 8765 [--host 127.0.0.1] [--db PATH] [--public]

GET /viewer?doc=<canonical_id>&page=<n>&q=<quote> answers with viewer.render_viewer's HTML (the page text with the
quote in <mark>) wrapped in a minimal page. GET / and /health answer "ok". Anything else is 404. deeplink.viewer_link
builds absolute links to VIEWER_BASE (default http://127.0.0.1:8765), so footnotes in .md files open this server.
--public refuses licensed documents (render_viewer public=True). The UI session may mount the same handler in
ui/server.py: call viewer_response(query_string, db_path, public) and send (status, content_type, body).
"""

import argparse
import html
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .viewer import render_viewer

PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,
initial-scale=1"><title>Source page</title><style>body{{font:15px/1.5 system-ui,sans-serif;margin:16px;max-width:60rem;
background:#fff;color:#111}}mark{{background:#ffe066}}pre{{white-space:pre-wrap}}@media (prefers-color-scheme:dark)
{{body{{background:#111;color:#eee}}mark{{background:#8a6d00;color:#fff}}}}</style></head><body>{body}</body></html>"""


def viewer_response(query, db_path=None, public=False):
    """(status, content_type, body bytes) for the query string of a /viewer request."""
    qs = parse_qs(query or "")
    doc = (qs.get("doc") or [""])[0]
    if not doc:
        return 400, "text/plain; charset=utf-8", b"missing doc"
    try:
        page = int((qs.get("page") or ["1"])[0])
    except ValueError:
        return 400, "text/plain; charset=utf-8", b"bad page"
    q = (qs.get("q") or [""])[0]
    try:
        body = render_viewer(doc, page, q, db_path=db_path, public=public)
    except BaseException as e:            # a missing sqlite raises SystemExit in agent.moat.cite.db
        body = f'<div class="srcpage">Source text unavailable: {html.escape(type(e).__name__)}</div>'
    return 200, "text/html; charset=utf-8", PAGE.format(body=body).encode("utf-8")


def make_handler(db_path=None, public=False):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):                 # noqa: N802
            u = urlsplit(self.path)
            if u.path in ("/", "/health"):
                status, ctype, body = 200, "text/plain; charset=utf-8", b"ok"
            elif u.path.rstrip("/") == "/viewer":
                status, ctype, body = viewer_response(u.query, db_path, public)
            else:
                status, ctype, body = 404, "text/plain; charset=utf-8", b"not found"
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass
    return Handler


def serve(port=8765, host="127.0.0.1", db_path=None, public=False, background=False):
    """Start the server. background=True returns (server, thread) after starting it on a daemon thread; port 0 picks
    a free port (server.server_address[1])."""
    srv = ThreadingHTTPServer((host, port), make_handler(db_path, public))
    if background:
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        return srv, t
    try:
        srv.serve_forever()
    finally:
        srv.server_close()
    return srv, None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Serve /viewer?doc=&page=&q= for citation footnotes.")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--db", default=None, help="citations.sqlite (default: env CITATIONS_DB or agent.moat.cite.DB)")
    ap.add_argument("--public", action="store_true", help="refuse licensed documents")
    a = ap.parse_args(argv)
    print(f"viewer on http://{a.host}:{a.port}/viewer?doc=...&page=...&q=...")
    serve(a.port, a.host, a.db, a.public)


if __name__ == "__main__":
    main()
