# Pilot + Retriever Findings Report

**Date:** 2026-07-15  
**Author:** Shailah Riddick  
**Ticket:** Optimize Community Schema query via composite persistent index `(partition_id, level)` + `storedValues: ["occurrence"]`  
**Importer PRs:** [#228](https://github.com/arangoml/graphrag_importer/pull/228) (focused), [#227](https://github.com/arangoml/graphrag_importer/pull/227) (strategy suite)

---

## Executive summary

We implemented the ticket index in `graphrag_importer`, validated it on synthetic + semi-live ArangoDB benches, then **migrated and profiled it on Pilot** against the live `test_deep_search` graph. The community schema AQL path uses `partition_id_level_index` (~**3.4 ms** for ~525 rows). We also ran full **global** and **local** retriever questions end-to-end against that graph.

| Layer | Metric | Result |
|-------|--------|--------|
| Hot AQL (Community Schema) | Profile wall | **~3.384 ms** (525 rows, level ≤ 2, partition `default_1_a`) |
| Index plan | EXPLAIN | Uses **`partition_id_level_index`** with `storedValues: [occurrence]` |
| Retriever Q1 global | `WALL_TIME_SEC` / shell `real` | **24.135 s** / **~26.0 s** |
| Retriever Q2 local | `WALL_TIME_SEC` / shell `real` | **5.852 s** / **~7.7 s** |

**Interpretation:** End-to-end retriever time is dominated by LLM map/reduce (global) and embedding + context + LLM (local). The ticket index correctly accelerates the **AQL** slice that previously risked full community document materialization.

---

## 1. What we shipped in the importer

Production behavior (solution **B = A2**):

- Create `partition_id_level_index` on Communities:
  - fields: `["partition_id", "level"]`
  - `storedValues: ["occurrence"]`
  - `inBackground: true`
- Drop redundant Communities-only `partition_id_index`
- Leave other collections on single-field `partition_id_index`
- Provide migration helper for existing DBs
- Unit coverage for index creation / naming

Focused PR: **graphrag_importer#228**  
Broader strategy evaluation PR: **#227**

---

## 2. Earlier evidence (pre-pilot)

### Rubric (strategies A–F)

| Strategy | Score | Verdict |
|----------|------:|---------|
| baseline | 3/7 | Fail |
| A1 | 6/7 | Fail (redundant index) |
| **A2 / B** | **7/7** | **Ship** |
| C | 6/7 | Fail (no storedValues) |
| D | 7/7 | Companion migration |
| E / F | ≤5/7 | Out of importer scope / wrong collections |

### Semi-live ArangoDB 3.12.4 (local)

| Docs | Baseline median | Solution B | Speedup |
|-----:|----------------:|-----------:|--------:|
| 50k | 18.63 ms | 13.86 ms | 1.34× |
| 150k | 55.40 ms | 36.92 ms | 1.50× |

Synthetic scale model @ 250k: covering path ~3.89 ms vs baseline ~10.26 ms; **0** full document fetches when `storedValues` covers the RETURN projection.

---

## 3. Pilot validation (`802zarto`)

### Environment

| Setting | Value |
|---------|--------|
| Host | `https://802zarto.rnd.pilot.arango.ai` |
| Database | `_system` |
| Project / prefix | `GENAI_PROJECT_NAME=test_deep_search` |
| Communities collection | `test_deep_search_Communities` |
| Partition | `default_1_a` |
| Level | `2` (`FILTER c.level <= 2`) |

### Graph discovery notes

- Empty personal DB `shailah_riddick` was not useful for this test.
- `NV_Bugs_Communities` could take the index, but **`partition_id` values were null** → ticket FILTER shape ineffective.
- **`test_deep_search_*`** collections are the correct notebook graph for end-to-end validation.

### Index migration on Pilot

Created / ensured `partition_id_level_index` on `test_deep_search_Communities`.

### AQL profile (Community Schema hot path)

- Rows returned: **525** (levels 0–2 under partition `default_1_a`)
- Profile time: **~3.384 ms**
- EXPLAIN: uses **`partition_id_level_index`** with covering `occurrence`

This is the direct proof for the ticket’s AQL claim.

---

## 4. Retriever end-to-end questions (Pilot)

Harness: restored / adapted `retrievers.test_main` for current package APIs (JWT via Arango `/_open/auth`, skip Integration Service metadata for standalone Mac). Docker local_dev path was blocked (no Docker on this Mac).

### Q1 — Global

- **Query:** “What are the main themes or communities in this dataset?”
- **Type:** global · level 2 · partition `default_1_a`
- **Timing:** `WALL_TIME_SEC=24.135` · shell real ~26.0 s
- **Behavior:** vector path skipped (`embedding_model` unset) → **occurrence-based** community retrieval · **512** communities · LLM map/reduce (22 groups)
- **Answer quality:** Strong thematic summary (ArangoSearch/views/analyzers, geospatial, indexes, AQL planning, graphs, transactions, example datasets)

### Q2 — Local

- **Query:** “Tell me about ArangoSearch views and how they relate to analyzers and indexes.”
- **Type:** local · partition `default_1_a`
- **Timing:** `WALL_TIME_SEC=5.852` · shell real ~7.7 s
- **Behavior:** embedding OK · primary AQL **10** results · large cited context · concise cited answer
- **Retrieval slice (from logs):** embedding ~1.3 s · AQL + context ~2.8 s · LLM finishes by ~5.85 s total

---

## 5. Findings & implications

1. **Ticket index works on Pilot.** EXPLAIN and profile confirm `partition_id_level_index` with `storedValues`.
2. **AQL latency is sub-10 ms** on this graph’s Community Schema filter (~525 matching docs). Semi-live benches show larger wins as community count grows.
3. **E2E retriever latency ≠ AQL latency.** Global ~24 s and local ~6 s are mostly LLM (and embeddings for local). Do not claim the composite index alone cut 24 s → milliseconds end-to-end.
4. **Partition hygiene matters.** Graphs without real `partition_id` values (e.g. `NV_Bugs`) cannot exercise this optimization.
5. **Operational gaps for local Mac testing:** current retrievers package removed `test_main`; service path needs Integration Service (`9201`). Standalone JWT + direct retriever calls are fine for offline timing.
6. **Remaining ticket walkthrough step:** deploy importer #228 to **US DEV**, ensure Communities index exists there, re-time the same two questions for a before/after E2E narrative if US DEV baseline lacked the index.

---

## 6. Recommended status updates for the ticket

- [x] Implement composite + storedValues in importer  
- [x] Unit tests  
- [x] Synthetic / semi-live AQL benches  
- [x] Pilot migrate + EXPLAIN/profile on real Communities collection  
- [x] Two retriever questions on notebook graph (`test_deep_search`)  
- [ ] US DEV deploy + re-measure  
- [ ] Close ticket with AQL evidence + E2E timings (clearly labeled)

---

## 7. Links

| Resource | URL |
|----------|-----|
| Focused importer PR | https://github.com/arangoml/graphrag_importer/pull/228 |
| Strategy suite PR | https://github.com/arangoml/graphrag_importer/pull/227 |
| This tracking repo | https://github.com/RiddickShailah/Arango_Community-Schema-Query- |
| Interactive slideshow | [`docs/interactive/index.html`](interactive/index.html) |
| PowerPoint | [`docs/Community_Schema_Optimization.pptx`](Community_Schema_Optimization.pptx) |
