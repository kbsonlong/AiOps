from __future__ import annotations

from typing import Dict, Iterable

from aiops.utils.formatters import redact_secrets


def format_report(query: str, results: Iterable[Dict[str, object]]) -> str:
    lines = [f"Query: {query}", ""]
    for item in results:
        source = item.get("source", "unknown")
        content = str(item.get("result", ""))
        lines.append(f"[{source}]")
        lines.append(redact_secrets(content))
        lines.append("")
    return "\n".join(lines).strip() + "\n"
