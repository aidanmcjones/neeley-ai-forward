"""Print the context blocks for given row ids from _ctx.txt."""
import sys

from agent.moat.common import ROOT

txt = (ROOT / "data/moat/verified/policy/_ctx.txt").read_text().replace("\x00", "")
ids = set(sys.argv[1:])
for blk in txt.split("\n\n=== "):
    rid = blk.lstrip("= ").split(" ", 1)[0]
    if rid in ids:
        print("=== " + blk.lstrip("= ")[:2200], "\n")
