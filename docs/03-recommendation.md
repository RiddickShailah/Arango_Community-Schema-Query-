# Recommendation

## Preferred approach

1. **Option A2** (or **B** if we want a cleaner structure now):
   - Communities → `partition_id_level_index` on `["partition_id", "level"]` with `storedValues=["occurrence"]`
   - Drop redundant single-field `partition_id_index` on Communities only
   - Other collections keep `partition_id_index`
2. **Extend** `create_persistent_index` to accept `stored_values` (do not raw-duplicate `add_index` forever).
3. **Option D** for existing deployments if latency is already visible in prod (script or ops note).
4. Do **not** ship Option C unless ArangoDB version forces it.
5. Do **not** change global indexing for all collections (Option F).

## Implementation checklist

- [ ] Decide A2 vs B
- [ ] Add `stored_values` (and keep `inBackground: true`)
- [ ] Communities path creates `partition_id_level_index`
- [ ] Remove or stop creating `partition_id_index` on Communities
- [ ] Fix/field-order-aware existence check if needed
- [ ] Unit test for index payload
- [ ] Integration assertion on Communities indexes
- [ ] Release note / migration for existing DBs (if in scope)
- [ ] Confirm retriever still benefits (EXPLAIN / latency before-after)

## Open questions

- Is dropping the old Communities `partition_id_index` name safe for any external ops/scripts?
- Minimum ArangoDB version for `storedValues` in our deployment?
- Are indexes still only created when `partition_id` is present on the import job?
