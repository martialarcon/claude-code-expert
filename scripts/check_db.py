#!/usr/bin/env python3
"""Check ChromaDB status."""
import sys
sys.path.insert(0, '/home/jetson/developer/projects/claude-code-expert')

from src.storage.vector_store import get_vector_store

store = get_vector_store()

print("=" * 50)
print("CHROMADB STATUS")
print("=" * 50)

# Get all collections
for coll_name in ["items", "analysis", "synthesis", "snapshots"]:
    try:
        count = store.count(coll_name)
        print(f"\n[{coll_name}]: {count} documentos")

        if count > 0:
            # Show sample
            col = store.get_collection(coll_name)
            results = col.get(limit=3, include=["metadatas", "documents"])
            for i, (id, meta, doc) in enumerate(zip(results['ids'], results['metadatas'], results['documents'])):
                print(f"  - {id}")
                print(f"    meta: {meta}")
                print(f"    preview: {(doc or '')[:100]}...")
    except Exception as e:
        print(f"\n[{coll_name}]: ERROR - {e}")

print("\n" + "=" * 50)
