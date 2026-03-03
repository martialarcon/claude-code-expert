#!/usr/bin/env python3
"""
AI Architect v2 - Auditoría de ítems analizados.

Muestra qué ítems han sido analizados, cuándo, y detecta posibles duplicados.

Uso:
    python scripts/check_analyzed.py [--days N] [--verbose]

Ejemplos:
    python scripts/check_analyzed.py              # Resumen de todos los días
    python scripts/check_analyzed.py --days 7     # Últimos 7 días
    python scripts/check_analyzed.py --verbose    # Muestra títulos por fecha
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow running from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.vector_store import get_vector_store


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auditar ítems analizados en ChromaDB"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=0,
        help="Filtrar últimos N días (0 = todos)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostrar lista de títulos por fecha",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    store = get_vector_store()

    col = store.get_collection("analysis")
    total = col.count()

    if total == 0:
        print("No hay ítems analizados en ChromaDB.")
        return

    # Retrieve all analysis documents (no embedding needed)
    all_data = col.get(include=["metadatas"])
    ids = all_data.get("ids", [])
    metas = all_data.get("metadatas", [])

    # Group by analyzed_at date
    by_date: dict[str, list[dict]] = defaultdict(list)
    no_date: list[dict] = []

    cutoff: datetime | None = None
    if args.days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)

    for doc_id, meta in zip(ids, metas):
        analyzed_at = meta.get("analyzed_at", "")
        if analyzed_at:
            if cutoff:
                try:
                    doc_date = datetime.strptime(analyzed_at, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                    if doc_date < cutoff:
                        continue
                except ValueError:
                    pass
            by_date[analyzed_at].append({"id": doc_id, "meta": meta})
        else:
            no_date.append({"id": doc_id, "meta": meta})

    # Detect duplicate item_ids (same item analyzed more than once)
    item_id_counts: dict[str, list[str]] = defaultdict(list)
    for doc_id, meta in zip(ids, metas):
        item_id = meta.get("item_id", doc_id)
        item_id_counts[item_id].append(doc_id)

    duplicates = {k: v for k, v in item_id_counts.items() if len(v) > 1}

    # ── Output ──────────────────────────────────────────────────────────────
    header = "AI Architect v2 — Auditoría de ítems analizados"
    print(f"\n{'=' * len(header)}")
    print(header)
    print(f"{'=' * len(header)}")
    print(f"Total en ChromaDB (colección 'analysis'): {total}")
    if args.days:
        print(f"Filtro aplicado: últimos {args.days} días")
    print()

    if not by_date and not no_date:
        print("No hay ítems en el rango de fechas especificado.")
        return

    # Summary by date (sorted chronologically)
    print("Ítems por fecha (analyzed_at):")
    print("-" * 45)
    grand_total = 0
    for date_str in sorted(by_date.keys(), reverse=True):
        entries = by_date[date_str]
        count = len(entries)
        grand_total += count
        print(f"  {date_str}  →  {count:3d} ítems")
        if args.verbose:
            for entry in sorted(entries, key=lambda e: int(e["meta"].get("signal_score", "0") or "0"), reverse=True):
                title = entry["meta"].get("title", entry["id"])[:80]
                score = entry["meta"].get("signal_score", "?")
                print(f"      [{score:>2}] {title}")

    if no_date:
        count = len(no_date)
        grand_total += count
        print(f"  (sin fecha)  →  {count:3d} ítems  ⚠️  (analizados antes del fix)")
        if args.verbose:
            for entry in no_date:
                title = entry["meta"].get("title", entry["id"])[:80]
                print(f"           {title}")

    print("-" * 45)
    print(f"  TOTAL en rango     →  {grand_total:3d} ítems")
    print()

    # Duplicate report
    if duplicates:
        print(f"⚠️  Duplicados detectados ({len(duplicates)} item_id con >1 análisis):")
        for item_id, doc_ids in duplicates.items():
            print(f"  item_id={item_id[:40]}  →  {len(doc_ids)} análisis: {doc_ids}")
        print()
    else:
        print("✅ No se detectaron duplicados.")
        print()


if __name__ == "__main__":
    main()
