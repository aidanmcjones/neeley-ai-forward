from agent.moat.common import note_gap
for t in ("GSK", "SNY", "TAK"):
    note_gap("peers", t, "results 6-Ks 2023-2025", "collector too slow (hundreds of 6-Ks per filer, one folder index call each at the shared SEC rate limit); stopped at timebox. NVS partly done (11), GSK 5, SNY 1, TAK 0. Rerun: python -m agent.moat.peers_filings q SNY,TAK,GSK (resumable)")
note_gap("peers", "GSK", "manifests/peers.jsonl", "stale rows for ~50 small GSK/NVS 6-K files deleted from disk after a too-loose filter; drop rows whose path does not exist")
