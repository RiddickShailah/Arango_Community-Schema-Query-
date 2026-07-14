# Strategy comparison results

Generated: 2026-07-14 17:38 UTC

Acceptance rubric (7 checks): Communities composite `(partition_id, level)`, `storedValues: occurrence`, index name `partition_id_level_index`, other collections keep `partition_id_index`, no redundant Communities `partition_id_index`, no level composite on non-Communities, implementable in importer.

| Strategy | Score | Result | Summary |
|----------|-------|--------|---------|
| baseline | 3/7 | FAIL | Current behavior: partition_id_index on every collection. |
| A1 | 6/7 | FAIL | Add Communities composite index; keep old partition_id_index everywhere. |
| A2 | 7/7 | PASS | Communities composite+storedValues; drop redundant partition_id_index there. |
| B | 7/7 | PASS | Data-driven index specs encoding A2 for Communities + default elsewhere. |
| C | 6/7 | FAIL | Composite (partition_id, level) without storedValues. |
| D | 7/7 | PASS | A2 create/drop plan plus explicit migration semantics for existing DBs (idempotent ensureIndex, inBackground). |
| E | 1/7 | FAIL | Retriever-side optimization (cache / query rewrite / skinny collection). |
| F | 5/7 | FAIL | Apply Communities composite to ALL collections (anti-pattern). |

## Verdict

- **Winners (7/7):** A2, B, D — same effective Communities indexing; B is the production structure (`PRODUCTION_STRATEGY`), D adds migration packaging.
- **A1 (6/7):** Works but keeps a redundant Communities `partition_id_index`.
- **C (6/7):** Faster filters, but misses covering `occurrence` reads.
- **Baseline (3/7):** Today's importer behavior — insufficient.
- **F (fail):** Incorrectly indexes `level` on all collections.
- **E (fail in-repo):** Retriever-owned follow-up, not importer work.

Pytest status: **17 passed** (`tests/unit/test_partition_index_strategies.py`, `--noconftest`)

## Per-strategy detail

### baseline

Current behavior: partition_id_index on every collection.

**Score:** 3/7 — FAIL

Checks:

- ❌ `communities_composite_fields`
- ❌ `communities_stored_occurrence`
- ❌ `communities_index_name`
- ✅ `others_keep_partition_id_index`
- ❌ `communities_no_redundant_partition_index`
- ✅ `no_level_composite_on_non_communities`
- ✅ `implementable_in_importer`

Apply log (simulated existing DB with partition_id_index):

```
skip-create demo_Chunks.partition_id_index
skip-create demo_Communities.partition_id_index
skip-create demo_Documents.partition_id_index
skip-create demo_Entities.partition_id_index
skip-create demo_Relations.partition_id_index
```

Notes:

- Does not optimize level filter or occurrence covering reads.

### A1

Add Communities composite index; keep old partition_id_index everywhere.

**Score:** 6/7 — FAIL

Checks:

- ✅ `communities_composite_fields`
- ✅ `communities_stored_occurrence`
- ✅ `communities_index_name`
- ✅ `others_keep_partition_id_index`
- ❌ `communities_no_redundant_partition_index`
- ✅ `no_level_composite_on_non_communities`
- ✅ `implementable_in_importer`

Apply log (simulated existing DB with partition_id_index):

```
skip-create demo_Chunks.partition_id_index
skip-create demo_Communities.partition_id_index
create demo_Communities.partition_id_level_index
skip-create demo_Documents.partition_id_index
skip-create demo_Entities.partition_id_index
skip-create demo_Relations.partition_id_index
```

Notes:

- Redundant partition_id coverage on Communities (extra write/disk cost).

### A2

Communities composite+storedValues; drop redundant partition_id_index there.

**Score:** 7/7 — PASS

Checks:

- ✅ `communities_composite_fields`
- ✅ `communities_stored_occurrence`
- ✅ `communities_index_name`
- ✅ `others_keep_partition_id_index`
- ✅ `communities_no_redundant_partition_index`
- ✅ `no_level_composite_on_non_communities`
- ✅ `implementable_in_importer`

Apply log (simulated existing DB with partition_id_index):

```
skip-create demo_Chunks.partition_id_index
drop demo_Communities.partition_id_index
create demo_Communities.partition_id_level_index
skip-create demo_Documents.partition_id_index
skip-create demo_Entities.partition_id_index
skip-create demo_Relations.partition_id_index
```

Notes:

- Preferred importer-side solution for Community Schema latency.

### B

Data-driven index specs encoding A2 for Communities + default elsewhere.

**Score:** 7/7 — PASS

Checks:

- ✅ `communities_composite_fields`
- ✅ `communities_stored_occurrence`
- ✅ `communities_index_name`
- ✅ `others_keep_partition_id_index`
- ✅ `communities_no_redundant_partition_index`
- ✅ `no_level_composite_on_non_communities`
- ✅ `implementable_in_importer`

Apply log (simulated existing DB with partition_id_index):

```
skip-create demo_Chunks.partition_id_index
drop demo_Communities.partition_id_index
create demo_Communities.partition_id_level_index
skip-create demo_Documents.partition_id_index
skip-create demo_Entities.partition_id_index
skip-create demo_Relations.partition_id_index
```

Notes:

- Preferred structure if more index variants are expected later.

### C

Composite (partition_id, level) without storedValues.

**Score:** 6/7 — FAIL

Checks:

- ✅ `communities_composite_fields`
- ❌ `communities_stored_occurrence`
- ✅ `communities_index_name`
- ✅ `others_keep_partition_id_index`
- ✅ `communities_no_redundant_partition_index`
- ✅ `no_level_composite_on_non_communities`
- ✅ `implementable_in_importer`

Apply log (simulated existing DB with partition_id_index):

```
skip-create demo_Chunks.partition_id_index
drop demo_Communities.partition_id_index
create demo_Communities.partition_id_level_index
skip-create demo_Documents.partition_id_index
skip-create demo_Entities.partition_id_index
skip-create demo_Relations.partition_id_index
```

Notes:

- Speeds FILTER; still may fetch full docs for occurrence.

### D

A2 create/drop plan plus explicit migration semantics for existing DBs (idempotent ensureIndex, inBackground).

**Score:** 7/7 — PASS

Checks:

- ✅ `communities_composite_fields`
- ✅ `communities_stored_occurrence`
- ✅ `communities_index_name`
- ✅ `others_keep_partition_id_index`
- ✅ `communities_no_redundant_partition_index`
- ✅ `no_level_composite_on_non_communities`
- ✅ `implementable_in_importer`

Apply log (simulated existing DB with partition_id_index):

```
skip-create demo_Chunks.partition_id_index
drop demo_Communities.partition_id_index
create demo_Communities.partition_id_level_index
skip-create demo_Documents.partition_id_index
skip-create demo_Entities.partition_id_index
skip-create demo_Relations.partition_id_index
```

Notes:

- Same importer ops as A2; additionally suitable as a one-shot migration script.
- Uses inBackground=True on all create specs.
- Idempotent: drops only if partition_id_index exists; creates if missing.

### E

Retriever-side optimization (cache / query rewrite / skinny collection).

**Score:** 1/7 — FAIL

Checks:

- ❌ `communities_composite_fields`
- ❌ `communities_stored_occurrence`
- ❌ `communities_index_name`
- ❌ `others_keep_partition_id_index`
- ❌ `communities_no_redundant_partition_index`
- ✅ `no_level_composite_on_non_communities`
- ❌ `implementable_in_importer`

Apply log (simulated existing DB with partition_id_index):

```
(no importer ops)
```

Notes:

- Not implementable in graphrag_importer; owned by the retriever service.
- Importer still must provide a usable Communities index for best results.

### F

Apply Communities composite to ALL collections (anti-pattern).

**Score:** 5/7 — FAIL

Checks:

- ✅ `communities_composite_fields`
- ✅ `communities_stored_occurrence`
- ✅ `communities_index_name`
- ❌ `others_keep_partition_id_index`
- ✅ `communities_no_redundant_partition_index`
- ❌ `no_level_composite_on_non_communities`
- ✅ `implementable_in_importer`

Apply log (simulated existing DB with partition_id_index):

```
create demo_Chunks.partition_id_level_index
create demo_Communities.partition_id_level_index
create demo_Documents.partition_id_level_index
create demo_Entities.partition_id_level_index
create demo_Relations.partition_id_level_index
```

Notes:

- level/occurrence are not meaningful on Documents/Chunks/Entities/Relations.
- Rejected for production.
