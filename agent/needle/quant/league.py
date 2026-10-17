"""League score and Sharpest Needle (docs/quant_model.md sections 4.8 and 4.9).

L_c = (sum of top-5 S_f, one row per underlying fact) . min(1, N_eff,c / N*),  N_eff = (sum_b S_b)^2 / sum_b S_b^2,  N* = 3
Needle = argmax S_f subject to O >= 0.5, E >= 0.90, confidence != LOW, z = 0, adverse or quantified.
If none passes: the argmax of S among findings with O at or above the company's median O, labelled provisional.
If that pool is also empty of positive S, a documented fallback relaxes the O floor to the company's top-quartile O
and flags "floor relaxed" (coordinator review item B5: a 6-month half-life puts every February 10-K item below 0.5).
"""

from . import weights as W


def n_eff(block_scores):
    """Inverse Herfindahl of score mass across evidence blocks."""
    tot = sum(block_scores.values())
    sq = sum(v * v for v in block_scores.values())
    return (tot * tot / sq) if sq > 0 else 0.0


def dedupe_facts(findings):
    """Keep the highest-S row per underlying fact (review S1: AZN's receivables +14.7-pt gap appeared twice, as the
    time-series flag and as its peer-outlier twin). Rows without a fact_key are their own fact. Returns
    (kept, dropped) with dropped rows flagged "same fact as <id>"."""
    kept, dropped, seen = [], [], {}
    for f in sorted(findings, key=lambda f: -f.S):
        k = getattr(f, "fact_key", "") or ""
        if k and k in seen:
            if hasattr(f, "flags") and not any(x.startswith("same fact as") for x in f.flags):
                f.flags.append(f"same fact as {seen[k].id}: counted once in the league (review S1)")
            dropped.append(f)
            continue
        if k:
            seen[k] = f
        kept.append(f)
    return kept, dropped


def league_score(findings, n_star=W.N_STAR, top_n=W.TOP_N):
    """(L_c, top list, N_eff, block masses). findings: objects with .S and .family.block. One underlying fact
    contributes one row (dedupe_facts)."""
    kept, _ = dedupe_facts([f for f in findings if f.S > 0])
    top = sorted(kept, key=lambda f: -f.S)[:top_n]
    blocks = {}
    for f in top:
        blocks[f.family.block] = blocks.get(f.family.block, 0.0) + f.S
    ne = n_eff(blocks)
    total = sum(f.S for f in top)
    return total * min(1.0, ne / n_star) if top else 0.0, top, ne, blocks


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return 0.0 if not n else xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _quantile(xs, q):
    xs = sorted(xs)
    if not xs:
        return 0.0
    return xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))]


def sharpest_needle(findings):
    """(finding or None, status) where status is "strict", "provisional", "floor relaxed" or "none"."""
    pool = [f for f in findings if f.needle_eligible and f.S > 0]
    if pool:
        return max(pool, key=lambda f: f.S), "strict"
    scored = [f for f in findings if f.S > 0 and f.vector["z"] == 0]
    if not scored:
        return None, "none"
    med = _median([f.vector["O"] for f in findings])
    prov = [f for f in scored if f.vector["O"] >= med and f.confidence != "LOW"]
    if prov:
        return max(prov, key=lambda f: f.S), "provisional"
    q75 = _quantile([f.vector["O"] for f in scored], 0.75)
    relaxed = [f for f in scored if f.vector["O"] >= q75]
    return (max(relaxed, key=lambda f: f.S), "floor relaxed") if relaxed else (None, "none")
