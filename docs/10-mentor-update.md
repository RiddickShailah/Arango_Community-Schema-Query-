# Mentor update (short)

**Community Schema index — update + findings**

Shipped in `graphrag_importer` (PR [#228](https://github.com/arangoml/graphrag_importer/pull/228)): Communities index `(partition_id, level)` + `storedValues: [occurrence]`. CI green (unit + integration). DEV image: `v0.0.30-ae18835`.

**Findings**
- Index works on Pilot: EXPLAIN uses `partition_id_level_index`; AQL ~**3.4 ms** (525 rows, `default_1_a`, level ≤ 2).
- Semi-live earlier: **1.34×–1.50×** faster vs baseline.
- Graphs without real `partition_id` (e.g. `NV_Bugs`) can’t exercise this path — used `test_deep_search`.
- Retriever E2E still LLM-heavy: global ~**24 s**, local ~**6 s**. Index helps the AQL slice, not full answer latency.

**Next:** merge → US DEV on that importer image → migrate index → re-time AQL + same 2 questions.
