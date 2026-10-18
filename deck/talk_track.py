T = [
"""SLIDE 1 · 20 sec

AIDAN: I'm Aidan. I'm a founding forward-deployed engineer at Vulcan Technologies, a Y Combinator company, and a pre-med biology major here at TCU. I built the system.

PARKER: I'm Parker. I'm a finance major in Neeley, and I cover healthcare as an analyst at Summit TX Capital. I pressure-tested the findings and made the call.""",

"""SLIDE 2 · 40 sec · AIDAN

The case asks two things: find what a drugmaker's filings hide, then make one CEO decision.

The hard part is AI. It makes up page numbers, and it will argue for any strategy.

So we scraped our own database: 7,005 documents and 78,392 pages.

Skill one sends ten blind readers through all ten companies, and two skeptic agents try to kill every finding. 141 candidates, 25 kept, Amgen came out first.

Skill two does the same for the CEO move.

And no number reaches the screen unless it links back to its page.

Hand to Parker.""",

"""SLIDE 3 · 60 sec · PARKER

Amgen was the only one of the ten with two findings that are material, non-obvious and high-confidence.

Our Sharpest Needle: Amgen carries a $2.4 billion intangible for TAVNEOS, about 5.2 times its sales, and the FDA has formally proposed pulling the drug.

Between the Q1 and Q2 10-Qs the impairment wording softened, and no call or release mentions the number.

A full write-off is about $4.23 a share.

The other four back it up. We marked rows four and five obvious, because management has talked about them.""",

"""SLIDE 4 · 40 sec · PARKER

Repatha against Praluent, Leqvio and Merck's new pill, Lipfendra.

Repatha has the best label: it's the only one whose outcomes claim includes heart procedures.

What limits it is price. Amgen guides net price down mid-single digits, and each 1% is about $30 million.

We call it not priced in, at medium confidence, because no product-level analyst estimates exist.""",

"""SLIDE 5 · 60 sec · PARKER, then AIDAN

PARKER: As CEO, we commit $12.5 million and 12 people to offer the FDA a fully funded TAVNEOS trial instead of withdrawal. Trial money moves only if the FDA agrees.

The most we lose is $12.5 million, to defend a $2.3 billion U.S. asset. We break even if the offer raises the odds of keeping the drug by 3 points.

AIDAN: We rejected Repatha rebates, about $424 million for a sales lift we couldn't support, and a Repatha campaign, which was already management's plan and left out side effects.

We'll know we're wrong if the FDA denies the hearing, gives no go-ahead by month 12, or U.S. sales drop under $114 million a quarter.

And to be straight with you: there's no FDA precedent for accepting this. That's why we cap the spend.""",

"""SLIDE 6 · rest of the time · AIDAN drives, PARKER narrates

AIDAN: This is the live product. Scan the code if you want to follow along on your phone.

[Click Find the needle. Wait for the answer.]

AIDAN: Every number has a footnote.

[Click the $2.4B footnote. The 10-Q opens at page 16.]

PARKER: That's the exact sentence in Amgen's 10-Q.

[Click The CEO Move.]

PARKER: Same check on the move: the budget, the math, and what would prove us wrong.

AIDAN: Two reusable skills, our own database, and every answer cited. Happy to take questions.""",

"""APPENDIX · not presented · Q&A prep

Why only medium confidence? No product-level analyst estimates exist.

What are the asterisks? Numbers no filing states: the $12.5M budget, 12 people, the month-12 deadline and the $413M yearly run-rate. Each is labelled in the model.

Is the $2.4B already in the stock? Analysts asked about TAVNEOS once in 10 calls, and the stock rose 2.4% on the filing.

How do you stop the AI making things up? Every number is checked against its page by code, a fresh agent re-checks all of them, and a person reads the page behind every needle.

Why not Merck? It ranked second. Its best finding, about $1.56B of IRS exposure, was smaller per share than Amgen's.""",
]
