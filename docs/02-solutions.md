# Solution brainstorm

Options ordered from closest-to-ticket to more speculative.

## Option A — Communities-only composite index

Keep `partition_id_index` on other collections. For Communities create `partition_id_level_index` with `fields=["partition_id","level"]` and `storedValues=["occurrence"]`.

| Sub-option | Behavior |
|------------|----------|
| **A1** | Add composite; leave old `partition_id_index` on Communities |
| **A2** | Add composite; drop/replace old `partition_id_index` on Communities |

**Pros:** Matches proposed `ensureIndex`; small blast radius; leading `partition_id` still useful.  
**Cons:** Needs `storedValues` support; A1 doubles index write cost on Communities; old DBs need migration.

## Option B — Data-driven index specs

Per-collection index definitions (table/config) instead of one hard-coded loop.

**Pros:** Clear, extensible, easy to test.  
**Cons:** Slightly more structure than a one-line special case.

## Option C — Composite without `storedValues`

Only change fields to `["partition_id","level"]`.

**Pros:** Smaller API change; still speeds FILTER.  
**Cons:** Full doc reads for `occurrence` remain — misses a large latency win.

## Option D — Importer change + existing-DB migration

Same as A/B for new graphs, plus a one-shot `ensureIndex` (or ops note) for live `*_Communities` collections.

**Pros:** Fixes production without waiting for re-import.  
**Cons:** Extra ops/docs; need `inBackground: true`.

## Option E — Retriever-side changes

Cache schema, rewrite query, or maintain a skinny side collection.

**Pros:** Can help beyond indexing.  
**Cons:** Outside importer ticket; more moving parts. Treat as follow-up.

## Option F — Apply composite to all collections

**Skip.** `level` / `occurrence` are not meaningful on Documents/Chunks/Entities/Relations.

## Design issues to decide during implementation

1. Special-case in the loop vs Option B specs table.
2. Extend `create_persistent_index(..., stored_values=...)`.
3. Idempotency / rename: old `partition_id_index` will not disappear automatically.
4. Existence check currently uses `set(fields)` — field **order** should matter for composites.
5. Tests: unit assert on `add_index` payload; integration assert index on Communities.
6. Gate: today indexes are created only when `self.partition_id` is set — confirm that remains correct.
