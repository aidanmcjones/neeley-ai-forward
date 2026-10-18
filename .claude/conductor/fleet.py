"""Fleet snapshot for the conductor agent.

Reads the Claude Code transcripts for this project and prints, per live session:
what the human asked, what it is doing now, files it wrote, artifacts it touched.
Then flags overlaps (two sessions on the same file or artifact).

Run: python -I .claude/conductor/fleet.py [--minutes 90] [--self <session-id-prefix>]
"""
import argparse, collections, glob, json, os, re, time

D = os.path.expanduser(r"~/.claude/projects/C--Users-parke-OneDrive-Desktop-Hackathon")
ART = re.compile(r"claude\.ai/(?:code/)?artifact/[\w-]+")


def text(content):
    if isinstance(content, str):
        return content
    out = []
    for b in content or []:
        if b.get("type") == "text":
            out.append(b["text"])
    return "\n".join(out)


def scan(path):
    s = {"cwd": None, "start": None, "asks": [], "last": "", "files": collections.Counter(),
         "artifacts": set(), "commits": [], "tools": 0}
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        s["cwd"] = r.get("cwd") or s["cwd"]
        s["start"] = s["start"] or r.get("timestamp")
        msg = r.get("message") or {}
        c = msg.get("content")
        if r.get("type") == "user" and not r.get("isMeta"):
            t = text(c).strip()
            if t and not t.startswith("<") and not t.startswith("Another Claude session"):
                s["asks"].append(t)
        if r.get("type") != "assistant":
            continue
        t = text(c).strip()
        if t:
            s["last"] = t
        for b in c if isinstance(c, list) else []:
            if b.get("type") != "tool_use":
                continue
            s["tools"] += 1
            inp = b.get("input") or {}
            if b["name"] in ("Edit", "Write", "NotebookEdit") and inp.get("file_path"):
                s["files"][os.path.normpath(inp["file_path"]).lower()] += 1
            blob = json.dumps(inp)
            if b["name"] == "Artifact":
                s["artifacts"].update(ART.findall(blob))
            m = re.search(r'git commit[^"]*?-m\s+\\?"([^"\\]{0,100})', blob)
            if m:
                s["commits"].append(m.group(1))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=90)
    ap.add_argument("--self", default="")
    a = ap.parse_args()
    now = time.time()
    sessions = {}
    for f in glob.glob(D + "/*.jsonl"):
        sid = os.path.basename(f)[:8]
        if a.self and sid.startswith(a.self):
            continue
        age = (now - os.path.getmtime(f)) / 60
        if age <= a.minutes:
            sessions[sid] = (age, scan(f))
    for sid, (age, s) in sorted(sessions.items(), key=lambda kv: kv[1][0]):
        print("=" * 70)
        print(f"{sid}  started {s['start']}  last write {age:.0f} min ago  tools {s['tools']}")
        print(f"cwd: {s['cwd']}")
        print("asks (latest last):")
        for q in s["asks"][-4:]:
            print("  >", q.replace("\n", " ")[:500])
        print("now:", s["last"].replace("\n", " ")[:600])
        if s["files"]:
            print("wrote:", ", ".join(os.path.basename(p) for p, _ in s["files"].most_common(12)))
        if s["artifacts"]:
            print("artifacts:", ", ".join(sorted(s["artifacts"])))
        if s["commits"]:
            print("commits:", " | ".join(s["commits"][-3:]))
    print("=" * 70)
    owners = collections.defaultdict(set)
    for sid, (_, s) in sessions.items():
        for p in s["files"]:
            owners[("file", p)].add(sid)
        for u in s["artifacts"]:
            owners[("artifact", u)].add(sid)
    clashes = [(k, v) for k, v in owners.items() if len(v) > 1]
    print("OVERLAPS:" if clashes else "OVERLAPS: none")
    for (kind, what), sids in clashes:
        print(f"  {kind} {what}  <- {', '.join(sorted(sids))}")


if __name__ == "__main__":
    main()
