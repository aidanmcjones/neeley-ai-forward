"""New-indication rebuild, step 1: parse every cached DailyMed SPL version (tmp spl_cache) into section 1, section 14
and Recent Major Changes text by subsection. Output /tmp/ni/spl_parsed.json keyed by setid -> version."""
import json
import re
import sys
from pathlib import Path

from lxml import etree

CACHE = Path("/Users/aidanjones/.claude/jobs/9174fb40/tmp/spl_cache")
OUT = Path("/tmp/ni/spl_parsed.json")
NS = {"v": "urn:hl7-org:v3"}
CODES = {"34067-9": "s1", "34092-7": "s14", "43683-2": "rmc"}


def txt(el):
    return re.sub(r"\s+", " ", " ".join(el.itertext())).strip()


def title(sec):
    t = sec.find("v:title", NS)
    return txt(t) if t is not None else ""


def parse(path):
    root = etree.parse(str(path)).getroot()
    eff = root.find("v:effectiveTime", NS).get("value")[:8]
    out = {"eff": f"{eff[:4]}-{eff[4:6]}-{eff[6:8]}", "s1": {}, "s14": {}, "rmc": ""}
    for sec in root.iter("{urn:hl7-org:v3}section"):
        c = sec.find("v:code", NS)
        key = CODES.get(c.get("code") if c is not None else "")
        if not key:
            continue
        if key == "rmc":
            out["rmc"] = txt(sec)
            continue
        subs = [s for s in sec.findall("v:component/v:section", NS)]
        named = [s for s in subs if re.match(r"\s*\d+(\.\d+)?", title(s))]
        if named:
            for s in named:
                t = title(s)
                m = re.match(r"\s*(\d+(?:\.\d+)?)\s*(.*)", t)
                out[key][m.group(1)] = [m.group(2).strip(), txt(s)]
        else:
            out[key]["0"] = [title(sec), txt(sec)]
    return out


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    res = json.loads(OUT.read_text()) if OUT.exists() else {}
    for f in sorted(CACHE.glob("*.xml")):
        sid, v = f.stem.rsplit("_", 1)
        if v in res.get(sid, {}):
            continue
        try:
            res.setdefault(sid, {})[v] = parse(f)
        except Exception as e:  # noqa: BLE001
            print("fail", f.name, e, file=sys.stderr)
    OUT.write_text(json.dumps(res))
    print(len(res), sum(len(x) for x in res.values()))


if __name__ == "__main__":
    main()
