from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class MergeResult:
    merged: str
    conflicts: List[str]


def simple_merge(base: str, current: str, incoming: str) -> MergeResult:
    """Naive 3-way merge that flags line-level conflicts."""
    if current == incoming:
        return MergeResult(merged=current, conflicts=[])
    if current == base:
        return MergeResult(merged=incoming, conflicts=[])
    if incoming == base:
        return MergeResult(merged=current, conflicts=[])
    diff = difflib.unified_diff(current.splitlines(), incoming.splitlines(), lineterm="")
    conflicts = list(diff)
    merged = "\n".join(
        [
            "<<<<<<< current",
            current,
            "=======",
            incoming,
            ">>>>>>> incoming",
        ]
    )
    return MergeResult(merged=merged, conflicts=conflicts)
