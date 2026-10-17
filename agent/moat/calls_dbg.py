import re
import agent.moat.calls_mb as m
from agent.corpus import html_to_text

text = html_to_text(open("/tmp/gd/raw/PFE_2024Q3.html").read())
for mm in list(re.finditer(r"\n Analyst\n", text))[:2]:
    print(repr(text[mm.start() - 150: mm.start() + 200]))
