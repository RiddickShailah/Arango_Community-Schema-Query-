"""
Partition / Communities index strategies for Community Schema query optimization.

Each solution variant from the design brainstorm is expressed as an
``IndexPlan`` of create/drop operations. Plans are pure data so they can be
unit-tested without ArangoDB, and the importer can apply the chosen plan.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional


PARTITION_ID_INDEX = "partition_id_index"
PARTITION_ID_LEVEL_INDEX = "partition_id_level_index"


@dataclass(frozen=True)
class IndexSpec:
    """Declarative persistent-index definition."""

    name: str
    fields: tuple[str, ...]
    stored_values: tuple[str, ...] = ()
    in_background: bool = True

    def to_arango_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "persistent",
            "fields": list(self.fields),
            "name": self.name,
            "inBackground": self.in_background,
        }
        if self.stored_values:
            payload["storedValues"] = list(self.stored_values)
        return payload


@dataclass(frozen=True)
class IndexOp:
    """One create or drop against a collection."""

    action: str  # "create" | "drop"
    collection: str
    spec: Optional[IndexSpec] = None
    index_name: Optional[str] = None

    def __post_init__(self) -> None:
        if self.action not in {"create", "drop"}:
            raise ValueError(f"Unsupported action: {self.action}")
        if self.action == "create" and self.spec is None:
            raise ValueError("create ops require spec")
        if self.action == "drop" and not self.index_name:
            raise ValueError("drop ops require index_name")


@dataclass
class IndexPlan:
    """Ordered operations plus metadata for reporting."""

    strategy: str
    description: str
    ops: list[IndexOp] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def creates_for(self, collection: str) -> list[IndexSpec]:
        return [
            op.spec
            for op in self.ops
            if op.action == "create" and op.collection == collection and op.spec is not None
        ]

    def drops_for(self, collection: str) -> list[str]:
        return [
            op.index_name
            for op in self.ops
            if op.action == "drop" and op.collection == collection and op.index_name
        ]


class IndexStrategy(str, Enum):
    """Named solutions from the brainstorm."""

    BASELINE = "baseline"  # today's behavior
    A1 = "A1"  # composite + keep old partition_id_index on Communities
    A2 = "A2"  # composite + drop old partition_id_index on Communities
    B = "B"  # data-driven specs (encodes A2 content)
    C = "C"  # composite without storedValues
    D = "D"  # A2 + migration ops for existing DBs
    E = "E"  # retriever-side (not implementable in importer)
    F = "F"  # composite on ALL collections (anti-pattern)


DEFAULT_PARTITION_SPEC = IndexSpec(name=PARTITION_ID_INDEX, fields=("partition_id",))
COMMUNITY_COMPOSITE_SPEC = IndexSpec(
    name=PARTITION_ID_LEVEL_INDEX,
    fields=("partition_id", "level"),
    stored_values=("occurrence",),
)
COMMUNITY_COMPOSITE_NO_STORED = IndexSpec(
    name=PARTITION_ID_LEVEL_INDEX,
    fields=("partition_id", "level"),
)


def _is_communities(collection: str) -> bool:
    return collection.endswith("_Communities") or collection == "Communities"


def build_index_plan(
    strategy: IndexStrategy | str,
    collections: Iterable[str],
    *,
    existing_indexes: Optional[dict[str, list[str]]] = None,
) -> IndexPlan:
    """
    Build an index plan for ``collections``.

    ``existing_indexes`` maps collection -> list of existing index names.
    Used by strategies that drop/migrate (A2, D).
    """
    strategy = IndexStrategy(strategy)
    collections = sorted(set(collections))
    existing_indexes = existing_indexes or {}

    if strategy == IndexStrategy.BASELINE:
        return _plan_baseline(collections)
    if strategy == IndexStrategy.A1:
        return _plan_a1(collections)
    if strategy == IndexStrategy.A2:
        return _plan_a2(collections, existing_indexes)
    if strategy == IndexStrategy.B:
        return _plan_b(collections, existing_indexes)
    if strategy == IndexStrategy.C:
        return _plan_c(collections, existing_indexes)
    if strategy == IndexStrategy.D:
        return _plan_d(collections, existing_indexes)
    if strategy == IndexStrategy.E:
        return IndexPlan(
            strategy=strategy.value,
            description="Retriever-side optimization (cache / query rewrite / skinny collection).",
            notes=[
                "Not implementable in graphrag_importer; owned by the retriever service.",
                "Importer still must provide a usable Communities index for best results.",
            ],
        )
    if strategy == IndexStrategy.F:
        return _plan_f(collections)
    raise ValueError(f"Unknown strategy: {strategy}")


def _plan_baseline(collections: list[str]) -> IndexPlan:
    ops = [
        IndexOp(action="create", collection=c, spec=DEFAULT_PARTITION_SPEC) for c in collections
    ]
    return IndexPlan(
        strategy=IndexStrategy.BASELINE.value,
        description="Current behavior: partition_id_index on every collection.",
        ops=ops,
        notes=["Does not optimize level filter or occurrence covering reads."],
    )


def _plan_a1(collections: list[str]) -> IndexPlan:
    ops: list[IndexOp] = []
    for c in collections:
        ops.append(IndexOp(action="create", collection=c, spec=DEFAULT_PARTITION_SPEC))
        if _is_communities(c):
            ops.append(IndexOp(action="create", collection=c, spec=COMMUNITY_COMPOSITE_SPEC))
    return IndexPlan(
        strategy=IndexStrategy.A1.value,
        description="Add Communities composite index; keep old partition_id_index everywhere.",
        ops=ops,
        notes=["Redundant partition_id coverage on Communities (extra write/disk cost)."],
    )


def _plan_a2(collections: list[str], existing: dict[str, list[str]]) -> IndexPlan:
    ops: list[IndexOp] = []
    for c in collections:
        if _is_communities(c):
            if PARTITION_ID_INDEX in existing.get(c, []):
                ops.append(
                    IndexOp(action="drop", collection=c, index_name=PARTITION_ID_INDEX)
                )
            ops.append(IndexOp(action="create", collection=c, spec=COMMUNITY_COMPOSITE_SPEC))
        else:
            ops.append(IndexOp(action="create", collection=c, spec=DEFAULT_PARTITION_SPEC))
    return IndexPlan(
        strategy=IndexStrategy.A2.value,
        description="Communities composite+storedValues; drop redundant partition_id_index there.",
        ops=ops,
        notes=["Preferred importer-side solution for Community Schema latency."],
    )


def community_index_specs() -> dict[str, list[IndexSpec]]:
    """Data-driven specs used by Option B (A2 content, declarative form)."""
    return {
        # Keys are logical roles; callers map CollectionNames.* at apply time.
        "communities": [COMMUNITY_COMPOSITE_SPEC],
        "default": [DEFAULT_PARTITION_SPEC],
    }


def _plan_b(collections: list[str], existing: dict[str, list[str]]) -> IndexPlan:
    # Same effective outcome as A2, built from declarative specs.
    specs = community_index_specs()
    ops: list[IndexOp] = []
    for c in collections:
        wanted = specs["communities"] if _is_communities(c) else specs["default"]
        if _is_communities(c) and PARTITION_ID_INDEX in existing.get(c, []):
            ops.append(IndexOp(action="drop", collection=c, index_name=PARTITION_ID_INDEX))
        for spec in wanted:
            ops.append(IndexOp(action="create", collection=c, spec=spec))
    return IndexPlan(
        strategy=IndexStrategy.B.value,
        description="Data-driven index specs encoding A2 for Communities + default elsewhere.",
        ops=ops,
        notes=["Preferred structure if more index variants are expected later."],
    )


def _plan_c(collections: list[str], existing: dict[str, list[str]]) -> IndexPlan:
    ops: list[IndexOp] = []
    for c in collections:
        if _is_communities(c):
            if PARTITION_ID_INDEX in existing.get(c, []):
                ops.append(
                    IndexOp(action="drop", collection=c, index_name=PARTITION_ID_INDEX)
                )
            ops.append(
                IndexOp(action="create", collection=c, spec=COMMUNITY_COMPOSITE_NO_STORED)
            )
        else:
            ops.append(IndexOp(action="create", collection=c, spec=DEFAULT_PARTITION_SPEC))
    return IndexPlan(
        strategy=IndexStrategy.C.value,
        description="Composite (partition_id, level) without storedValues.",
        ops=ops,
        notes=["Speeds FILTER; still may fetch full docs for occurrence."],
    )


def _plan_d(collections: list[str], existing: dict[str, list[str]]) -> IndexPlan:
    plan = _plan_a2(collections, existing)
    plan.strategy = IndexStrategy.D.value
    plan.description = (
        "A2 create/drop plan plus explicit migration semantics for existing DBs "
        "(idempotent ensureIndex, inBackground)."
    )
    plan.notes = [
        "Same importer ops as A2; additionally suitable as a one-shot migration script.",
        "Uses inBackground=True on all create specs.",
        "Idempotent: drops only if partition_id_index exists; creates if missing.",
    ]
    # Migration flavor: if composite already exists, skip re-create by filtering at apply time.
    # Plan itself still lists creates; apply_index_plan handles existence.
    return plan


def _plan_f(collections: list[str]) -> IndexPlan:
    ops = [
        IndexOp(action="create", collection=c, spec=COMMUNITY_COMPOSITE_SPEC)
        for c in collections
    ]
    return IndexPlan(
        strategy=IndexStrategy.F.value,
        description="Apply Communities composite to ALL collections (anti-pattern).",
        ops=ops,
        notes=[
            "level/occurrence are not meaningful on Documents/Chunks/Entities/Relations.",
            "Rejected for production.",
        ],
    )


@dataclass
class PlanEvaluation:
    strategy: str
    passed: bool
    score: int
    max_score: int
    checks: dict[str, bool]
    details: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# Acceptance criteria focused on the Community Schema AQL need.
_EVAL_MAX = 7


def evaluate_plan(
    plan: IndexPlan,
    *,
    communities_collection: str,
    other_collections: Iterable[str],
) -> PlanEvaluation:
    """
    Score a plan against Community Schema optimization goals.

    Checks:
      1. Communities gets composite fields (partition_id, level)
      2. Communities composite includes storedValues occurrence (covering)
      3. Index name is partition_id_level_index
      4. Non-communities keep partition_id index
      5. Communities does not keep redundant sole partition_id_index (prefer drop)
      6. Does not put level composite on non-communities
      7. Plan is implementable in importer (not E)
    """
    others = list(other_collections)
    community_creates = plan.creates_for(communities_collection)
    community_create_names = {s.name for s in community_creates}

    has_composite = any(s.fields == ("partition_id", "level") for s in community_creates)
    has_stored = any(
        s.fields == ("partition_id", "level") and "occurrence" in s.stored_values
        for s in community_creates
    )
    has_named = any(s.name == PARTITION_ID_LEVEL_INDEX for s in community_creates)
    others_ok = (
        all(
            any(
                s.name == PARTITION_ID_INDEX and s.fields == ("partition_id",)
                for s in plan.creates_for(c)
            )
            for c in others
        )
        if others
        else True
    )
    # When a composite exists, do not also create partition_id_index on Communities.
    no_redundant = has_composite and PARTITION_ID_INDEX not in community_create_names
    no_level_on_others = not any(
        any(s.fields == ("partition_id", "level") for s in plan.creates_for(c)) for c in others
    )
    implementable = plan.strategy != IndexStrategy.E.value and bool(plan.ops)

    checks = {
        "communities_composite_fields": has_composite,
        "communities_stored_occurrence": has_stored,
        "communities_index_name": has_named,
        "others_keep_partition_id_index": others_ok,
        "communities_no_redundant_partition_index": no_redundant,
        "no_level_composite_on_non_communities": no_level_on_others,
        "implementable_in_importer": implementable,
    }

    score = sum(1 for v in checks.values() if v)
    details = [f"{'PASS' if v else 'FAIL'}: {k}" for k, v in checks.items()]
    details.extend(plan.notes)

    return PlanEvaluation(
        strategy=plan.strategy,
        passed=score == _EVAL_MAX,
        score=score,
        max_score=_EVAL_MAX,
        checks=checks,
        details=details,
    )


class InMemoryIndexCatalog:
    """Minimal catalog simulating Arango collection indexes for plan application tests."""

    def __init__(self) -> None:
        self.indexes: dict[str, dict[str, dict[str, Any]]] = {}

    def ensure_collection(self, name: str) -> None:
        self.indexes.setdefault(name, {})

    def list_index_names(self, collection: str) -> list[str]:
        return list(self.indexes.get(collection, {}).keys())

    def apply(self, plan: IndexPlan) -> list[str]:
        """Apply plan idempotently; return log of actions taken."""
        log: list[str] = []
        for op in plan.ops:
            self.ensure_collection(op.collection)
            if op.action == "drop":
                assert op.index_name is not None
                if op.index_name in self.indexes[op.collection]:
                    del self.indexes[op.collection][op.index_name]
                    log.append(f"drop {op.collection}.{op.index_name}")
                else:
                    log.append(f"skip-drop {op.collection}.{op.index_name}")
            elif op.action == "create":
                assert op.spec is not None
                if op.spec.name in self.indexes[op.collection]:
                    log.append(f"skip-create {op.collection}.{op.spec.name}")
                else:
                    self.indexes[op.collection][op.spec.name] = op.spec.to_arango_payload()
                    log.append(f"create {op.collection}.{op.spec.name}")
        return log


def migration_aql_ensure_index(collection_name: str) -> str:
    """Option D helper: JS snippet suitable for arangosh one-shot migration."""
    payload = json.dumps(COMMUNITY_COMPOSITE_SPEC.to_arango_payload())
    return (
        f'db._collection("{collection_name}").ensureIndex({payload});\n'
        f'try {{ db._collection("{collection_name}").dropIndex("{PARTITION_ID_INDEX}"); }} '
        f"catch (e) {{ /* missing is fine */ }}"
    )


# Production default used by ImportGraphToADB.initialize
PRODUCTION_STRATEGY = IndexStrategy.B
