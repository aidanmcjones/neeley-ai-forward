from agent.needle.detect import labels as L


def test_eliquis_profile():
    p = L.profile("eliquis")
    assert p["indications"]["count"] >= 5
    assert p["boxed_warning"]["value"] is True
    assert p["route"]["value"] == "oral"
    assert p["latest_patent_expiry"]["value"]


def test_xarelto_sane():
    assert L.profile("xarelto")["indications"]["count"] >= L.profile("eliquis")["indications"]["count"] - 2


def test_compare_bmy_and_evidence():
    c = L.compare("BMY")
    t = c["eliquis"]["table"]
    assert t and "xarelto" in t[0]["rivals"]
    assert any(r["rivals"]["xarelto"] is not None for r in t)
    for ps in c.values():
        for s in ps["signals"]:
            for ev in s.evidence:
                assert L.verify_label(ev) and ev.citation
    p = L.profile("eliquis")
    ev = p["_evidence"]["boxed_warning"]
    assert L.verify_label(ev) and "Boxed Warning" in ev.citation
    bad = L.Evidence(doc_id="drug:eliquis:label_sections.md", quote="this sentence is not in the label at all")
    assert not L.verify_label(bad)
