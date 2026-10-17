from agent.moat.common import note_gap

G = [("NVO", "material agreements", "20-F exhibit index not parseable as linked table; Exhibit 4.x agreements not listed"),
     ("AZN", "material agreements", "20-F exhibit index not parseable as linked table"),
     ("ABBV", "exec_comp_metrics", "short-term incentive weights are an image chart in the proxy; 0 rows 2024-2026"),
     ("ALL", "exec_comp_metrics", "regex candidate list (percent + metric keyword on plan pages); printed folio mostly '?', use pdf_page; needs manual check"),
     ("MRK", "material agreements", "no license/collaboration agreements filed as exhibits (SEC staff asked about Keytruda licenses 2025-04-10)"),
     ("PFE", "material agreements", "no license/collab exhibits matched in latest two 10-Ks"),
     ("ALL", "sec_comment_letters", "CORRESP/UPLOAD primary docs only; attached exhibits not collected; topic keywords are regex on full letter")]
for g in G:
    note_gap("secx", *g)
