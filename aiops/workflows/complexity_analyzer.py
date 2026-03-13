from __future__ import annotations

from typing import Dict, List


def analyze_task_complexity(state: Dict, next_state: Dict) -> Dict:
    """Heuristic task complexity analysis."""
    final_answer = (next_state or {}).get("final_answer", "") or ""
    lines = [line.strip() for line in final_answer.splitlines() if line.strip()]
    step_lines = [
        line
        for line in lines
        if line[0].isdigit() or line.startswith("- ") or line.startswith("* ")
    ]
    step_count = len(step_lines)
    complexity_score = min(1.0, step_count / 10.0)
    return {
        "step_count": step_count,
        "complexity_score": complexity_score,
        "workflow_steps": step_lines[:10],
    }
