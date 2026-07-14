# Code touchpoints (graphrag_importer)

Primary implementation repo: `arangoml/graphrag_importer`.

## Index creation (main change)

**File:** `graphrag/importer/import_graph_to_adb.py`

| Location | Today | Change |
|----------|-------|--------|
| `initialize()` ~L447–462 | Loop all collections → `partition_id_index` on `["partition_id"]` | Special-case Communities (or drive from specs) |
| `create_persistent_index()` ~L1625–1695 | Builds `add_index` payload without `storedValues` | Add optional `stored_values` → `storedValues` |
| Existence check in `create_persistent_index` | Compares `set(fields)` | Prefer ordered list compare for composites |
| `import_community_reports()` ~L2075+ | Writes `level`, `occurrence`, `partition_id` | No schema change required for this ticket |

## Helpers / naming

**File:** `graphrag/naming.py`

- `CollectionNames.COMMUNITIES` → `{PROJECT_NAME}_Communities`
- `IndexHelper.create_persistent_index` — optional to extend if used for this path
- `IndexHelper.create_relations_to_type_index` — unrelated; leave alone

## Tests to update / add

| File | Idea |
|------|------|
| `tests/unit/test_graphrag_importer.py` → `test_create_persistent_index` | Cover `stored_values` / composite fields |
| New unit test on `initialize` indexing | Assert Communities gets `partition_id_level_index` payload |
| `tests/integration/test_integration_graphrag.py` | After import, assert composite index exists on Communities (near existing vector-index check ~L1282) |

## Docs in product repo (optional follow-up)

- `docs/user_facing_documentation.md` — Communities fields already documented; could mention the index if ops-facing.

## What not to change

- Retriever AQL (other service), unless later Phase 2.
- Community document schema / import of `level` & `occurrence` (already present).
- Global `partition_id_index` on non-Communities collections.
