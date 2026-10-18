# case_labels: side-by-side label sections

What it answers: how a product's FDA label, REMS, label changes, exclusivity dates, price series and head-to-head trials line up against the rivals the case lists for it.

Call: `agent.moat.case_labels.label_compare(drug, rivals=None, sections=("indications","boxed_warning","contraindications","warnings","rems","dosing","exclusivity","pricing"))`

`drug` is a case key (keytruda, skyrizi, vyndaqel). `rivals` defaults to the rivals in `agent/moat/case_sets.py` for that product (every shortlist company's sets are searched); a list of keys overrides it. Unknown drug returns `[]`.

## Fields returned

Every row: `ticker, kind, drug, maker, section, text (<=600 chars), citation, url, locator, source_id, quote_grade, license`.

- `kind="label_section"`: `heading, full_text_chars, label_effective, label_doc_type, has_boxed_warning, pages_in_section`; plus `n_indications` (indications), `boxed_warning_terms` (boxed_warning), `dosing_summary` (list of route and frequency phrases, dosing). `text` starts at the section's first page, so its first 200 characters verify with `cite.verify_quote(text[:200], doc_id, page_no)` on the locator page.
- `kind="rems"`: `rems_active, elements`, from `product/rems.csv`.
- `kind="label_change"`: latest 5 per drug from `product/label_changes_key.csv` (falls back to `label_changes.csv`); `effective_date, version, materiality`.
- `kind="exclusivity"`: one row per territory from `pipeline/loe_calendar.csv` with `orange_book_last_patent, exclusivity_latest_date, purple_book_ref_exclusivity, company_stated_loe, first_generic_or_biosimilar`; the locator is the 10-K page when the table row names one.
- `kind="pricing"`: `pricing/gtn_exposure.csv` (list-like and net-like series, IRA fields) and the latest year of `pricing/gtn_proxy.csv`.
- `kind="head_to_head"`: `product/h2h_by_pair.csv` pair verdicts and direct trials from `product/head_to_head.csv` for (drug, rival) pairs, matched through the ingredient names in `rems.csv`; extra fields `rival, pair`.
- `kind="matrix"`: one row per section, `matrix = {drug: one-line summary}`, `citation` and `locator` joined with " ; ".
- Table rows also carry `verify_status, source, source_row, table, row_key`; `locator` is the facts locator.

## Data sources and limits

- Labels: latest `fda_label_version` doc per drug (dated, four sections plus boxed warning), unless its date is before 2025-01-01, in which case the current full `fda_label` doc is used (`STALE_BEFORE` in the module). Drugs with no version doc use the full label, which is split into subsections, so `full_text_chars` and `text` cover the first subsection page only for some drugs; `n_indications` counts numbered sub-headings.
- `label_effective` is empty for full-label docs (no date in the index).
- `dosing_summary` is regex phrase matching over the first 2,500 characters of the dosing section; it is a pointer, not a regimen.
- `has_boxed_warning` is false when no boxed-warning page exists in the chosen doc.
- `h2h_by_pair.csv` has no `verify_status` column, so those rows carry an empty one.

## CLI example

```
python -m agent.moat.case_labels vyndaqel --section indications dosing
[label_section] vyndaqel indications :: ## 1. INDICATIONS AND USAGE VYNDAQEL and VYNDAMAX are indicated for the treatment of the cardiomyopathy ...
    Vyndaqel label, section 1. INDICATIONS AND USAGE <drug:vyndaqel:label_sections.md#p1>
[label_section] vyndaqel dosing :: ### 2.1 Recommended Dosage The recommended dosage is either VYNDAQEL 80 mg ... orally once daily ...
    Vyndaqel label, section 2.1 Recommended Dosage <drug:vyndaqel:label_sections.md#p2>
```

## Known gaps

- Generic placeholders in the case sets (sitagliptin, dapagliflozin) have no label docs and return no label rows.
- Exclusivity and pricing rows exist only for brands in `loe_calendar.csv` and the pricing tables; others show "no data in the index" in the matrix.
- Rival products whose label is only in the full `fda_label` doc give subsection-level pages, not whole-section text.
