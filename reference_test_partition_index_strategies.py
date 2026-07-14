"""Unit tests comparing Community Schema index strategies A–F."""

from __future__ import annotations

import json

import pytest

from graphrag.importer.partition_index_strategies import (
    PARTITION_ID_INDEX,
    PARTITION_ID_LEVEL_INDEX,
    PRODUCTION_STRATEGY,
    COMMUNITY_COMPOSITE_SPEC,
    IndexStrategy,
    InMemoryIndexCatalog,
    build_index_plan,
    evaluate_plan,
    migration_aql_ensure_index,
)


COLLECTIONS = [
    "demo_Chunks",
    "demo_Communities",
    "demo_Documents",
    "demo_Entities",
    "demo_Relations",
]
COMMUNITIES = "demo_Communities"
OTHERS = [c for c in COLLECTIONS if c != COMMUNITIES]


def _existing_baseline() -> dict[str, list[str]]:
    return {c: [PARTITION_ID_INDEX] for c in COLLECTIONS}


@pytest.mark.parametrize(
    "strategy,expected_score,expect_pass",
    [
        (IndexStrategy.BASELINE, 3, False),  # others_ok + no_level_on_others + implementable
        (IndexStrategy.A1, 6, False),  # fails no_redundant
        (IndexStrategy.A2, 7, True),
        (IndexStrategy.B, 7, True),
        (IndexStrategy.C, 6, False),  # fails stored occurrence
        (IndexStrategy.D, 7, True),
        (IndexStrategy.E, 1, False),  # only no_level_on_others (no ops)
        (IndexStrategy.F, 5, False),  # fails others_ok + no_level_on_others
    ],
)
def test_strategy_evaluation_scores(strategy, expected_score, expect_pass):
    plan = build_index_plan(strategy, COLLECTIONS, existing_indexes=_existing_baseline())
    result = evaluate_plan(plan, communities_collection=COMMUNITIES, other_collections=OTHERS)
    assert result.score == expected_score, result.details
    assert result.passed is expect_pass
    assert result.max_score == 7


def test_a1_keeps_both_indexes_on_communities():
    plan = build_index_plan(IndexStrategy.A1, COLLECTIONS)
    names = {s.name for s in plan.creates_for(COMMUNITIES)}
    assert names == {PARTITION_ID_INDEX, PARTITION_ID_LEVEL_INDEX}
    composite = next(s for s in plan.creates_for(COMMUNITIES) if s.name == PARTITION_ID_LEVEL_INDEX)
    assert composite.fields == ("partition_id", "level")
    assert composite.stored_values == ("occurrence",)


def test_a2_drops_old_and_creates_composite():
    plan = build_index_plan(IndexStrategy.A2, COLLECTIONS, existing_indexes=_existing_baseline())
    assert plan.drops_for(COMMUNITIES) == [PARTITION_ID_INDEX]
    creates = plan.creates_for(COMMUNITIES)
    assert len(creates) == 1
    assert creates[0].to_arango_payload() == {
        "type": "persistent",
        "fields": ["partition_id", "level"],
        "name": PARTITION_ID_LEVEL_INDEX,
        "inBackground": True,
        "storedValues": ["occurrence"],
    }
    for other in OTHERS:
        assert [s.name for s in plan.creates_for(other)] == [PARTITION_ID_INDEX]


def test_b_matches_a2_effective_ops():
    existing = _existing_baseline()
    a2 = build_index_plan(IndexStrategy.A2, COLLECTIONS, existing_indexes=existing)
    b = build_index_plan(IndexStrategy.B, COLLECTIONS, existing_indexes=existing)
    assert [(op.action, op.collection, op.index_name, op.spec) for op in a2.ops] == [
        (op.action, op.collection, op.index_name, op.spec) for op in b.ops
    ]


def test_c_omits_stored_values():
    plan = build_index_plan(IndexStrategy.C, COLLECTIONS, existing_indexes=_existing_baseline())
    creates = plan.creates_for(COMMUNITIES)
    assert len(creates) == 1
    assert creates[0].fields == ("partition_id", "level")
    assert creates[0].stored_values == ()
    payload = creates[0].to_arango_payload()
    assert "storedValues" not in payload


def test_d_migration_snippet_and_catalog_apply():
    snippet = migration_aql_ensure_index(COMMUNITIES)
    assert PARTITION_ID_LEVEL_INDEX in snippet
    assert "storedValues" in snippet
    assert "occurrence" in snippet
    # Valid JSON embedded in ensureIndex(...)
    start = snippet.index("ensureIndex(") + len("ensureIndex(")
    end = snippet.index(");", start)
    payload = json.loads(snippet[start:end])
    assert payload == COMMUNITY_COMPOSITE_SPEC.to_arango_payload()

    catalog = InMemoryIndexCatalog()
    for c in COLLECTIONS:
        catalog.ensure_collection(c)
        catalog.indexes[c][PARTITION_ID_INDEX] = {
            "type": "persistent",
            "fields": ["partition_id"],
            "name": PARTITION_ID_INDEX,
        }
    plan = build_index_plan(IndexStrategy.D, COLLECTIONS, existing_indexes=_existing_baseline())
    log = catalog.apply(plan)
    assert any(x.startswith(f"drop {COMMUNITIES}.{PARTITION_ID_INDEX}") for x in log)
    assert any(x.startswith(f"create {COMMUNITIES}.{PARTITION_ID_LEVEL_INDEX}") for x in log)
    assert PARTITION_ID_LEVEL_INDEX in catalog.list_index_names(COMMUNITIES)
    assert PARTITION_ID_INDEX not in catalog.list_index_names(COMMUNITIES)
    # Idempotent second apply
    log2 = catalog.apply(plan)
    assert any(x.startswith("skip-create") for x in log2)


def test_e_is_not_implementable():
    plan = build_index_plan(IndexStrategy.E, COLLECTIONS)
    assert plan.ops == []
    result = evaluate_plan(plan, communities_collection=COMMUNITIES, other_collections=OTHERS)
    assert result.passed is False
    assert result.checks["implementable_in_importer"] is False


def test_f_puts_level_on_all_collections_and_fails():
    plan = build_index_plan(IndexStrategy.F, COLLECTIONS)
    for c in COLLECTIONS:
        specs = plan.creates_for(c)
        assert len(specs) == 1
        assert specs[0].fields == ("partition_id", "level")
    result = evaluate_plan(plan, communities_collection=COMMUNITIES, other_collections=OTHERS)
    assert result.checks["no_level_composite_on_non_communities"] is False
    assert result.checks["others_keep_partition_id_index"] is False
    assert result.passed is False


def test_production_strategy_is_b():
    assert PRODUCTION_STRATEGY == IndexStrategy.B


def test_catalog_simulates_baseline_to_a2_upgrade():
    catalog = InMemoryIndexCatalog()
    baseline = build_index_plan(IndexStrategy.BASELINE, COLLECTIONS)
    catalog.apply(baseline)
    assert all(PARTITION_ID_INDEX in catalog.list_index_names(c) for c in COLLECTIONS)

    existing = {c: catalog.list_index_names(c) for c in COLLECTIONS}
    a2 = build_index_plan(IndexStrategy.A2, COLLECTIONS, existing_indexes=existing)
    catalog.apply(a2)
    assert catalog.list_index_names(COMMUNITIES) == [PARTITION_ID_LEVEL_INDEX]
    for other in OTHERS:
        # baseline already created; a2 create may skip-create partition_id_index
        assert PARTITION_ID_INDEX in catalog.list_index_names(other)
