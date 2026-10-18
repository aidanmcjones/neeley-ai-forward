"""Shared helper for the pipeline target verifiers."""
import re


def toks(s):
    s = re.sub(r"[^a-z0-9 ]", " ", str(s).lower())
    stop = {"inc", "corp", "corporation", "ltd", "llc", "plc", "co", "sa", "ag", "nv", "gmbh", "the", "and", "a",
            "pharmaceuticals", "pharmaceutical", "pharma", "therapeutics", "bio", "biosciences", "biotechnology",
            "holdings", "company", "limited", "wholly", "owned", "subsidiary", "of", "s"}
    return {w for w in s.split() if w not in stop and len(w) > 1}
