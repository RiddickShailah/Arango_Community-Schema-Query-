# Findings summary (one-pager)

## Ticket
Optimize Community Schema AQL via `partition_id_level_index` on Communities:
`(partition_id, level)` + `storedValues: ["occurrence"]` in **graphrag_importer**.

## Shipped
- Solution **B (= A2)** · PR **[#228](https://github.com/arangoml/graphrag_importer/pull/228)** · commit `ae18835`
- DEV image: `v0.0.30-ae18835`
- CI: unit + integration green
- Migration script for existing DBs

## Findings

| Proof | Result |
|-------|--------|
| EXPLAIN on Pilot | Uses `partition_id_level_index` (+ stored `occurrence`) |
| AQL profile | **~3.4 ms** · 525 rows · partition `default_1_a` · level ≤ 2 |
| Semi-live benches | **1.34×–1.50×** vs baseline (50k / 150k) |
| Bad test graph | `NV_Bugs` — null `partition_id` (skipped) |
| Good test graph | `test_deep_search` on Pilot `_system` |
| Global Q1 E2E | **24.135 s** WALL · ~26 s real · 512 communities |
| Local Q2 E2E | **5.852 s** WALL · ~7.7 s real · 10 entities |

**Takeaway:** Index solves the **AQL / document-fetch** problem. E2E seconds are mostly **LLM-bound** — report AQL and E2E separately.

## US DEV (open)
See [`community_schema_us_dev_build_request.md`](community_schema_us_dev_build_request.md): merge → confirm image → migrate index → fill US DEV timing row.

## Artifacts
- Full findings: [`08-pilot-retriever-findings.md`](08-pilot-retriever-findings.md)
- Mentor note: [`10-mentor-update.md`](10-mentor-update.md)
- Slideshow: [`interactive/index.html`](interactive/index.html)
- PowerPoint: [`Community_Schema_Optimization.pptx`](Community_Schema_Optimization.pptx)
