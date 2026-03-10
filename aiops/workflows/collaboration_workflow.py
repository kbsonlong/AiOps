from __future__ import annotations

from typing import Iterable, List


def consensus_summary(results: Iterable[str]) -> str:
    """Create a lightweight consensus summary from multiple agent outputs."""
    items = [item.strip() for item in results if item.strip()]
    if not items:
        return "No consensus available."
    if len(items) == 1:
        return items[0]
    return " | ".join(items[:3])
