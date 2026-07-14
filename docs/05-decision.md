# Decision: Community Schema index strategy

**Status:** Accepted  
**Ticket:** Optimize Community Schema query via composite persistent index in `graphrag_importer`  
**Chosen solution:** **B** (data-driven specs) with the same behavior as **A2**  
**Production constant:** `PRODUCTION_STRATEGY = IndexStrategy.B` in `graphrag/importer/partition_index_strategies.py`

## Ticket requirement

Reduce retriever latency for:

```aql
FOR c IN @@communities_collection
    FILTER c.partition_id IN @partition_ids
    FILTER c.level <= @level
    RETURN {
        _key: c._key,
        level: c.level,
        occurrence: c.occurrence
    }
```

by creating:

```js
ensureIndex({
  type: "persistent",
  fields: ["partition_id", "level"],
  storedValues: ["occurrence"],
  name: "partition_id_level_index",
  inBackground: true
});
```

Today the importer creates only `partition_id_index` on `["partition_id"]`.

## Decision

**Use solution B (= A2 behavior).**

| What | Detail |
|------|--------|
| Communities | Create `partition_id_level_index` on `["partition_id", "level"]` with `storedValues: ["occurrence"]` |
| Communities | Drop / stop creating redundant `partition_id_index` |
| Other collections | Keep `partition_id_index` on `["partition_id"]` |
| Implementation style | Declarative per-collection specs (B), encoding A2 |

### Why B / A2 is best for this ticket

1. **Matches the proposed `ensureIndex` exactly** — fields, stored values, name, and background build.
2. **`storedValues: ["occurrence"]` is required** for the RETURN clause; without it the engine still tends to load fat Community documents (`report_string`, embeddings, etc.).
3. **Composite field order matches the filters** — `partition_id IN …` then `level <= …`.
4. **No redundant Communities index** — A2/B drop the lone `partition_id_index` on Communities; leading `partition_id` on the composite still serves partition-only lookups.
5. **Scoped correctly** — only Communities has meaningful `level` / `occurrence`; other collections keep the simple partition index.
6. **B over raw A2** — same ops, clearer to extend later; production uses the specs table rather than an ad-hoc special case alone.

## Alternatives considered

| Solution | Verdict | Why not (for this ticket) |
|----------|---------|---------------------------|
| **A1** | Rejected as primary | Creates the composite but **keeps** Communities `partition_id_index` → extra write/disk cost |
| **A2** | Accepted behaviorally | Correct behavior; B packages the same plan declaratively |
| **B** | **Accepted (ship)** | Same as A2 + maintainable specs |
| **C** | Rejected | Composite without `storedValues` — incomplete vs ticket, weaker covering reads |
| **D** | Optional companion | Same index as A2/B; use as **migration** for existing DBs (`scripts/migrate_communities_partition_level_index.py`), not instead of importer change |
| **E** | Out of scope | Retriever cache / query rewrite — not “change importer index creation” |
| **F** | Rejected | Applies `level` composite to all collections — incorrect |

## Evidence

Strategy rubric (**7 checks** aligned with the ticket):

| Strategy | Score | Result |
|----------|-------|--------|
| baseline | 3/7 | FAIL |
| A1 | 6/7 | FAIL (redundant index) |
| **A2 / B / D** | **7/7** | **PASS** |
| C | 6/7 | FAIL (no storedValues) |
| E | 1/7 | FAIL (not in importer) |
| F | 5/7 | FAIL (wrong collections) |

Scalable synthetic bench (`docs/scale_bench/`): covering path (A2/B/D) keeps **0 full document fetches** and ~**1%** of baseline bytes read as community counts grow (1k → 250k).

Full comparison write-up: [`community_schema_index_results.md`](community_schema_index_results.md)  
Scale data: [`scale_bench/community_schema_scale_results.md`](scale_bench/community_schema_scale_results.md)

## Code map

| Piece | Location |
|-------|----------|
| Strategy definitions + `PRODUCTION_STRATEGY` | `graphrag/importer/partition_index_strategies.py` |
| Apply plan during init | `ImportGraphToADB._ensure_partition_indexes()` in `import_graph_to_adb.py` |
| `storedValues` support | `ImportGraphToADB.create_persistent_index(..., stored_values=...)` |
| Index name constants | `CollectionIndexNames` in `graphrag/naming.py` |
| Unit tests (strategies) | `tests/unit/test_partition_index_strategies.py` |
| Unit tests (scale) | `tests/unit/test_community_schema_scale.py` |
| Existing-DB migration helper | `scripts/migrate_communities_partition_level_index.py` |

## Follow-ups (not required to close the ticket)

- Integration assert that Communities has `partition_id_level_index` after import
- Run Option D migration on live DBs that will not be re-initialized
- Retriever-side EXPLAIN / latency verification against a real Communities collection

## Semi-live validation (local ArangoDB 3.12.4)

Harness: `scripts/semi_live_community_schema_bench.py`  
Reports: `docs/semi_live/`

Same Community Schema AQL against a real single-node ArangoDB; only indexes change between phases.

| Docs | baseline median | B median | Speedup | EXPLAIN uses |
|------|----------------:|---------:|--------:|--------------|
| 50k | 18.63 ms | 13.86 ms | **1.34×** | `partition_id_level_index` |
| 150k | 55.40 ms | 36.92 ms | **1.50×** | `partition_id_level_index` |

Observed index after B: `fields=["partition_id","level"]`, `storedValues=["occurrence"]`; old `partition_id_index` removed. Result counts identical across phases.
