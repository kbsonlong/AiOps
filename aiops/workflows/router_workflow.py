from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field

from aiops.agents import (
    build_fault_agent,
    build_logs_agent,
    build_metrics_agent,
    build_security_agent,
)
from aiops.skills import SkillCompositionEngine, SkillDiscoveryService, SkillRegistry
from aiops.skills_lib import (
    FAULT_DIAGNOSIS_SKILLS,
    PROMETHEUS_SKILLS,
    SECURITY_SKILLS,
    VICTORIALOGS_SKILLS,
)


Severity = Literal["low", "medium", "high", "critical"]
Source = Literal["metrics", "logs", "fault", "security"]


class AgentInput(TypedDict):
    query: str


class AgentOutput(TypedDict):
    source: Source
    result: str


class Classification(TypedDict):
    source: Source
    query: str
    severity: Severity


class RouterState(TypedDict):
    query: str
    classifications: list[Classification]
    results: Annotated[list[AgentOutput], operator.add]
    final_answer: str
    detected_skills: list[dict]
    skill_execution_plan: dict


class ClassificationResult(BaseModel):
    classifications: list[Classification] = Field(
        description="Agents to invoke with targeted queries and severity level"
    )


def classify_query(state: RouterState, router_llm) -> dict:
    structured_llm = router_llm.with_structured_output(ClassificationResult)
    result = structured_llm.invoke([
        {
            "role": "system",
            "content": (
                "Analyze the query and decide which AIOps agents to call. "
                "Available sources: metrics, logs, fault, security. "
                "For each, produce a focused sub-query and a severity: low, medium, high, critical. "
                "Return only relevant sources."
            ),
        },
        {"role": "user", "content": state["query"]},
    ])
    return {"classifications": result.classifications}


def _ensure_critical_agents(
    classifications: list[Classification],
    query: str,
) -> list[Classification]:
    sources = {item["source"] for item in classifications}
    has_high = any(item["severity"] in ("high", "critical") for item in classifications)
    if not has_high:
        return classifications

    if "fault" not in sources:
        classifications.append(
            {"source": "fault", "query": f"Analyze root cause for: {query}", "severity": "high"}
        )
    if "security" not in sources:
        classifications.append(
            {"source": "security", "query": f"Check security impact for: {query}", "severity": "high"}
        )
    return classifications


def route_to_agents(state: RouterState) -> list[Send]:
    enriched = _ensure_critical_agents(list(state["classifications"]), state["query"])
    return [Send(item["source"], {"query": item["query"]}) for item in enriched]


def query_metrics(state: AgentInput, metrics_agent) -> dict:
    result = metrics_agent.invoke({"messages": [{"role": "user", "content": state["query"]}]})
    return {"results": [{"source": "metrics", "result": result["messages"][-1].content}]}


def query_logs(state: AgentInput, logs_agent) -> dict:
    result = logs_agent.invoke({"messages": [{"role": "user", "content": state["query"]}]})
    return {"results": [{"source": "logs", "result": result["messages"][-1].content}]}


def query_fault(state: AgentInput, fault_agent) -> dict:
    result = fault_agent.invoke({"messages": [{"role": "user", "content": state["query"]}]})
    return {"results": [{"source": "fault", "result": result["messages"][-1].content}]}


def query_security(state: AgentInput, security_agent) -> dict:
    result = security_agent.invoke({"messages": [{"role": "user", "content": state["query"]}]})
    return {"results": [{"source": "security", "result": result["messages"][-1].content}]}


def synthesize_results(state: RouterState, router_llm) -> dict:
    if not state["results"]:
        return {"final_answer": "No results found from any AIOps agent."}

    formatted = [
        f"From {item['source'].title()}:\n{item['result']}"
        for item in state["results"]
    ]
    synthesis_response = router_llm.invoke([
        {
            "role": "system",
            "content": (
                f"Synthesize these results to answer the original question: \"{state['query']}\". "
                "Combine findings, highlight anomalies, and provide actionable next steps."
            ),
        },
        {"role": "user", "content": "\n\n".join(formatted)},
    ])
    return {"final_answer": synthesis_response.content}


def skill_orchestration_node(state: RouterState) -> dict:
    registry = SkillRegistry()
    registry.bulk_register(PROMETHEUS_SKILLS)
    registry.bulk_register(VICTORIALOGS_SKILLS)
    registry.bulk_register(FAULT_DIAGNOSIS_SKILLS)
    registry.bulk_register(SECURITY_SKILLS)
    discovery = SkillDiscoveryService(registry=registry)
    skills = discovery.recommend_skills(state["query"])
    engine = SkillCompositionEngine()
    plan = engine.build_execution_plan(skills, context={"query": state["query"]})
    return {
        "detected_skills": [skill.model_dump() for skill in skills],
        "skill_execution_plan": {"order": plan.execution_order},
    }


def build_workflow(llm, router_llm):
    metrics_agent = build_metrics_agent().build(llm)
    logs_agent = build_logs_agent().build(llm)
    fault_agent = build_fault_agent().build(llm)
    security_agent = build_security_agent().build(llm)

    graph = (
        StateGraph(RouterState)
        .add_node("classify", lambda state: classify_query(state, router_llm))
        .add_node("skill_orchestrate", skill_orchestration_node)
        .add_node("metrics", lambda state: query_metrics(state, metrics_agent))
        .add_node("logs", lambda state: query_logs(state, logs_agent))
        .add_node("fault", lambda state: query_fault(state, fault_agent))
        .add_node("security", lambda state: query_security(state, security_agent))
        .add_node("synthesize", lambda state: synthesize_results(state, router_llm))
        .add_edge(START, "classify")
        .add_conditional_edges("classify", route_to_agents, ["metrics", "logs", "fault", "security"])
        .add_edge("classify", "skill_orchestrate")
        .add_edge("metrics", "synthesize")
        .add_edge("logs", "synthesize")
        .add_edge("fault", "synthesize")
        .add_edge("security", "synthesize")
        .add_edge("skill_orchestrate", "synthesize")
        .add_edge("synthesize", END)
    )
    return graph.compile()


def build_default_workflow():
    llm = init_chat_model("openai:gpt-4.1")
    router_llm = init_chat_model("openai:gpt-4.1-mini")
    return build_workflow(llm, router_llm)
