#!/usr/bin/env python3
"""
Option D: one-shot migration helper for existing Communities collections.

Prints arangosh JS that creates partition_id_level_index with storedValues
occurrence and drops the redundant partition_id_index.

Usage:
  python scripts/migrate_communities_partition_level_index.py myproj_Communities
  python scripts/migrate_communities_partition_level_index.py --all-from-env
"""

from __future__ import annotations

import argparse
import os
import sys

# Allow running from repo root without install.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graphrag.importer.partition_index_strategies import (  # noqa: E402
    migration_aql_ensure_index,
)
from graphrag.naming import CollectionNames  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "collection",
        nargs="?",
        help="Communities collection name, e.g. nvbugs_b1_Communities",
    )
    parser.add_argument(
        "--all-from-env",
        action="store_true",
        help=f"Use CollectionNames.COMMUNITIES from {os.getenv('GENAI_PROJECT_NAME', 'GENAI_PROJECT_NAME')}",
    )
    args = parser.parse_args()

    if args.all_from_env:
        collection = CollectionNames.COMMUNITIES
    elif args.collection:
        collection = args.collection
    else:
        parser.error("Provide a collection name or --all-from-env")

    print("// Migration: Community Schema composite persistent index")
    print(migration_aql_ensure_index(collection))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
