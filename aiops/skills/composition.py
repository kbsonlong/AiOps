from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import networkx as nx

from aiops.skills.models import SkillDefinition


@dataclass(slots=True)
class SkillExecutionPlan:
    skills: Dict[str, SkillDefinition] = field(default_factory=dict)
    execution_order: List[List[str]] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    context: Dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SkillCompositionEngine:
    def build_execution_plan(
        self,
        skills: List[SkillDefinition],
        context: Optional[Dict[str, object]] = None,
    ) -> SkillExecutionPlan:
        plan = SkillExecutionPlan(context=context or {})
        for skill in skills:
            plan.skills[skill.id] = skill

        graph = self._build_dependency_graph(skills)
        order = self._topological_layers(graph)
        # Default to sequential execution when no dependency edges exist.
        if len(order) == 1 and len(skills) > 1 and graph.number_of_edges() == 0:
            order = [[skill.id] for skill in skills]
        plan.execution_order = order
        plan.parallel_groups = [group for group in order if len(group) > 1]
        return plan

    @staticmethod
    def _build_dependency_graph(skills: List[SkillDefinition]) -> nx.DiGraph:
        graph = nx.DiGraph()
        for skill in skills:
            graph.add_node(skill.id)
        # Placeholder for future dependency rules.
        return graph

    @staticmethod
    def _topological_layers(graph: nx.DiGraph) -> List[List[str]]:
        try:
            layers = list(nx.topological_generations(graph))
        except nx.NetworkXUnfeasible:
            return [[node] for node in graph.nodes]
        return [list(layer) for layer in layers]
