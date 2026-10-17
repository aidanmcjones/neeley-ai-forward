from agent.moat.common import note_gap

G = [
    ("JNJ", "2026Q2 transcript", "official LSEG PDF text lost its spaces (words run together); usable for search by stripped text only; Q&A rows have spaceless text"),
    ("ABBV", "2026Q2 transcript", "corpus third-party text has inline 'Analyst (Name).' markers; Q&A parsed heuristically, only 10 turns recovered"),
    ("PFE", "2025Q2 transcript", "MarketBeat page has anonymous 'Speaker N' labels; used bullfincher.io (third_party, speaker names, merged consecutive paragraphs)"),
    ("LLY", "2025Q2 transcript", "same as PFE 2025Q2: bullfincher.io used"),
    ("AMGN", "2025Q2 transcript", "same as PFE 2025Q2: bullfincher.io used"),
    ("GILD", "2025Q2 transcript", "same as PFE 2025Q2: bullfincher.io used; only ~39 turns because consecutive same-speaker paragraphs merge"),
    ("NVO", "2025Q2 transcript", "roic.ai used (no analyst firms; firm filled from operator intro where parseable)"),
    ("ALL", "quality", "all new 2024Q1-2025Q2 calls are third_party (Quartr via MarketBeat, bullfincher, roic); no official transcripts reachable; whisper fallback not needed because every missing call had a text source; yt-dlp is not installed"),
    ("ALL", "quote check", "verify any quote against webcast replay before it enters the findings table"),
]
for t, i, r in G:
    note_gap("calls", t, i, r)
