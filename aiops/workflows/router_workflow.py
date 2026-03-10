from __future__ import annotations
import os
import json
import asyncio
import operator
from typing import Annotated, Literal, TypedDict, Optional

from langchain_litellm import ChatLiteLLM
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field

from aiops.agents import (
    build_fault_agent,
    build_logs_agent,
    build_metrics_agent,
    build_security_agent,
)
from aiops.agents.customer_service import CustomerServiceAgent
from knowledge.vector_store import VectorStoreManager
from aiops.skills import SkillCompositionEngine, SkillDiscoveryService, SkillRegistry
from aiops.skills_lib import (
    FAULT_DIAGNOSIS_SKILLS,
    PROMETHEUS_SKILLS,
    SECURITY_SKILLS,
    VICTORIALOGS_SKILLS,
)


Severity = Literal["low", "medium", "high", "critical"]
Source = Literal["metrics", "logs", "fault", "security", "customer_service"]


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
    knowledge_context: Optional[str]
    customer_service_result: Optional[str]


class ClassificationResult(BaseModel):
    classifications: list[Classification] = Field(
        description="Agents to invoke with targeted queries and severity level"
    )

def _coerce_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        # List of messages
        if value and isinstance(value[0], dict) and "role" in value[0]:
            # Prefer last user message if present
            for msg in reversed(value):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    return _coerce_text(msg.get("content"))
            return _coerce_text(value[-1].get("content") if isinstance(value[-1], dict) else value[-1])
        # List of content parts or mixed values
        parts = []
        for item in value:
            if isinstance(item, dict):
                if "text" in item:
                    parts.append(_coerce_text(item.get("text")))
                elif "content" in item:
                    parts.append(_coerce_text(item.get("content")))
                else:
                    parts.append(json.dumps(item, ensure_ascii=True))
            else:
                parts.append(_coerce_text(item))
        return "\n".join([p for p in parts if p])
    if isinstance(value, dict):
        if "content" in value:
            return _coerce_text(value.get("content"))
        return json.dumps(value, ensure_ascii=True)
    return str(value)

def _normalize_query(raw) -> str:
    text = _coerce_text(raw)
    return text.strip() if text else ""


def classify_query(state: RouterState, router_llm) -> dict:
    """
    路由分类节点：分析用户查询意图，决定需要调用的 AIOps 代理。
    
    Args:
        state: 当前路由状态，包含原始查询
        router_llm: 用于分类的 LLM 模型
        
    Returns:
        dict: 更新后的状态，包含分类结果列表
    """
    query_text = _normalize_query(state.get("query"))
    try:
        structured_llm = router_llm.with_structured_output(ClassificationResult)
        result = structured_llm.invoke([
            {
                "role": "system",
                "content": (
                    "Analyze the query and decide which AIOps agents to call. "
                    "Available sources: metrics, logs, fault, security, customer_service. "
                    "For each, produce a focused sub-query and a severity: low, medium, high, critical. "
                    "Return only relevant sources. "
                    "Use 'customer_service' for queries about 'how-to', 'what is', 'policy', or general knowledge."
                ),
            },
            {"role": "user", "content": query_text},
        ])
        if result is not None:
            return {"query": query_text, "classifications": result.classifications}
    except Exception as e:
        # Silently fail or log warning if needed, but for user experience we just fallback
        pass

    # Fallback: Manual JSON prompting with forced JSON mode
    try:
        parser = JsonOutputParser(pydantic_object=ClassificationResult)
        prompt = PromptTemplate(
            template="You are a helpful AIOps assistant.\nAnalyze the query and decide which agents to call.\nReturn ONLY a valid JSON object matching the schema below.\nDo NOT include any markdown formatting (like ```json), explanations, or extra text.\n\nSchema:\n{format_instructions}\n\nQuery: {query}\n\nJSON Response:",
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        
        # Note: Removing bind(response_format) as it caused empty output with some Ollama models
        chain = prompt | router_llm | parser
        result = chain.invoke({"query": query_text})
        
        # Validate result
        if isinstance(result, dict):
            # Try to validate with Pydantic model
            obj = ClassificationResult.model_validate(result)
            return {"query": query_text, "classifications": obj.classifications}
    except Exception as e:
        print(f"Error: JSON fallback also failed. {e}")
        
    # Return empty classifications if all fails
    return {"query": query_text, "classifications": []}


def _ensure_critical_agents(
    classifications: list[Classification],
    query: str,
) -> list[Classification]:
    """
    安全策略增强：确保高严重性事件自动触发故障诊断和安全检查。
    
    如果检测到严重程度为 high 或 critical 的事件，
    强制添加 fault 和 security 代理的调用。
    """
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
    """
    条件路由逻辑：根据分类结果生成并行执行的 Send 对象。
    
    将任务分发给 metrics, logs, fault, security 等代理。
    """
    enriched = _ensure_critical_agents(list(state["classifications"]), state["query"])
    return [Send(item["source"], {"query": item["query"]}) for item in enriched]


def query_metrics(state: AgentInput, metrics_agent) -> dict:
    """
    执行节点：调用指标监控代理 (Prometheus/Grafana) 查询系统指标。
    """
    query_text = _normalize_query(state.get("query"))
    result = metrics_agent.invoke({"messages": [{"role": "user", "content": query_text}]})
    return {"results": [{"source": "metrics", "result": result["messages"][-1].content}]}


def query_logs(state: AgentInput, logs_agent) -> dict:
    """
    执行节点：调用日志分析代理 (Elasticsearch/Loki) 检索系统日志。
    """
    query_text = _normalize_query(state.get("query"))
    result = logs_agent.invoke({"messages": [{"role": "user", "content": query_text}]})
    return {"results": [{"source": "logs", "result": result["messages"][-1].content}]}


def query_fault(state: AgentInput, fault_agent) -> dict:
    """
    执行节点：调用故障诊断代理进行根因分析。
    """
    query_text = _normalize_query(state.get("query"))
    result = fault_agent.invoke({"messages": [{"role": "user", "content": query_text}]})
    return {"results": [{"source": "fault", "result": result["messages"][-1].content}]}


def query_security(state: AgentInput, security_agent) -> dict:
    """
    执行节点：调用安全审计代理检查潜在风险。
    """
    query_text = _normalize_query(state.get("query"))
    result = security_agent.invoke({"messages": [{"role": "user", "content": query_text}]})
    return {"results": [{"source": "security", "result": result["messages"][-1].content}]}


def customer_service_node(state: AgentInput, customer_service_agent) -> dict:
    """
    执行节点：调用客户服务代理 (RAG) 回答一般性问题。
    """
    query_text = _normalize_query(state.get("query"))
    result = customer_service_agent.invoke({"messages": [{"role": "user", "content": query_text}]})
    answer = result["messages"][-1].content
    return {
        "results": [{"source": "customer_service", "result": answer}],
        "customer_service_result": answer
    }


def synthesize_results(state: RouterState, router_llm) -> dict:
    """
    汇总节点：收集所有代理的执行结果，生成最终的分析报告。
    
    Args:
        state: 包含所有代理执行结果(results)的状态
        router_llm: 用于生成的 LLM
    """
    if not state["results"]:
        return {"final_answer": "No results found from any AIOps agent."}

    query_text = _normalize_query(state.get("query"))
    formatted = [
        f"From {item['source'].title()}:\n{item['result']}"
        for item in state["results"]
    ]
    synthesis_response = router_llm.invoke([
        {
            "role": "system",
            "content": (
                f"Synthesize these results to answer the original question: \"{query_text}\". "
                "Combine findings, highlight anomalies, and provide actionable next steps. "
                "If there is a 'customer_service' result, ensure it is the primary source for 'how-to' or general knowledge questions."
            ),
        },
        {"role": "user", "content": "\n\n".join(formatted)},
    ])
    return {"final_answer": synthesis_response.content}


def skill_orchestration_node(state: RouterState) -> dict:
    """
    技能编排节点：基于查询动态发现和规划原子技能的执行顺序。
    
    使用 SkillRegistry 和 SkillCompositionEngine 来构建执行计划。
    """
    registry = SkillRegistry()
    registry.bulk_register(PROMETHEUS_SKILLS)
    registry.bulk_register(VICTORIALOGS_SKILLS)
    registry.bulk_register(FAULT_DIAGNOSIS_SKILLS)
    registry.bulk_register(SECURITY_SKILLS)
    discovery = SkillDiscoveryService(registry=registry)
    query_text = _normalize_query(state.get("query"))
    skills = discovery.recommend_skills(query_text)
    engine = SkillCompositionEngine()
    plan = engine.build_execution_plan(skills, context={"query": query_text})
    return {
        "detected_skills": [skill.model_dump() for skill in skills],
        "skill_execution_plan": {"order": plan.execution_order},
    }


def build_workflow(llm, router_llm):
    """
    构建 LangGraph 工作流图。
    
    定义节点(Nodes)和边(Edges)，编译成可执行的应用。
    流程结构:
    1. classify: 初始分类
    2. 并行执行: metrics, logs, fault, security, skill_orchestrate
    3. synthesize: 汇总所有结果
    """
    metrics_agent = build_metrics_agent().build(llm)
    logs_agent = build_logs_agent().build(llm)
    fault_agent = build_fault_agent().build(llm)
    security_agent = build_security_agent().build(llm)
    
    vector_store = VectorStoreManager()
    customer_service_agent = CustomerServiceAgent(vector_store).build(llm)

    graph = (
        StateGraph(RouterState)
        .add_node("classify", lambda state: classify_query(state, router_llm))
        .add_node("skill_orchestrate", skill_orchestration_node)
        .add_node("metrics", lambda state: query_metrics(state, metrics_agent))
        .add_node("logs", lambda state: query_logs(state, logs_agent))
        .add_node("fault", lambda state: query_fault(state, fault_agent))
        .add_node("security", lambda state: query_security(state, security_agent))
        .add_node("customer_service", lambda state: customer_service_node(state, customer_service_agent))
        .add_node("synthesize", lambda state: synthesize_results(state, router_llm))
        .add_edge(START, "classify")
        .add_conditional_edges("classify", route_to_agents, ["metrics", "logs", "fault", "security", "customer_service"])
        .add_edge("classify", "skill_orchestrate")
        .add_edge("metrics", "synthesize")
        .add_edge("logs", "synthesize")
        .add_edge("fault", "synthesize")
        .add_edge("security", "synthesize")
        .add_edge("customer_service", "synthesize")
        .add_edge("skill_orchestrate", "synthesize")
        .add_edge("synthesize", END)
    )
    return graph.compile()




def build_default_workflow():
    """
    Build the default workflow using LiteLLM for multi-provider support.
    
    You can switch providers by changing the model name, e.g.:
    - OpenAI: "gpt-4o", "gpt-4o-mini"
    - Anthropic: "claude-3-opus-20240229"
    - Ollama: "ollama/llama3"
    - Azure: "azure/gpt-4"
    """
    # Main LLM for complex tasks (synthesis, agent execution)
    llm_model = os.getenv("LLM_MODEL", "gpt-4o")
    llm_key = os.getenv("LITELLM_API_KEY","")
    llm_base = os.getenv("LITELLM_API_BASE","")
    llm = ChatLiteLLM(model=llm_model, temperature=0, timeout=30, api_key=llm_key, api_base=llm_base, max_tokens=4096)
    
    # Router LLM for classification (faster, cheaper)
    router_llm_model = os.getenv("ROUTER_LLM_MODEL", "gpt-4o-mini")
    router_llm = ChatLiteLLM(model=router_llm_model, temperature=0, timeout=30, api_key=llm_key, api_base=llm_base, max_tokens=4096)
    
    return build_workflow(llm, router_llm)


# -------------------------------------------------------------------------
# 示例：并行执行 Metrics 和 Logs 并汇总给 Fault Agent 的高级用法
# -------------------------------------------------------------------------

async def diagnosis_node(state: RouterState, metrics_agent, logs_agent, fault_agent) -> dict:
    """
    组合执行节点：并行运行 Metrics 和 Logs，结果汇总给 Fault 进行分析。
    
    这是一个演示函数，展示如何在一个节点内并行调度多个 Agent，
    并将它们的结果作为上下文传递给下游 Agent。
    """
    # 使用 ainvoke 并行执行监控和日志查询
    query_text = _normalize_query(state.get("query"))
    results = await asyncio.gather(
        metrics_agent.ainvoke({"messages": [{"role": "user", "content": query_text}]}),
        logs_agent.ainvoke({"messages": [{"role": "user", "content": query_text}]})
    )
    
    metrics_res = results[0]["messages"][-1].content
    logs_res = results[1]["messages"][-1].content
    
    # 将上下文传递给故障诊断 Agent
    fault_prompt = (
        f"Based on the collected data, analyze the root cause for: {query_text}\n\n"
        f"--- Metrics Data ---\n{metrics_res}\n\n"
        f"--- Logs Data ---\n{logs_res}"
    )
    
    fault_res = await fault_agent.ainvoke({"messages": [{"role": "user", "content": fault_prompt}]})
    
    return {
        "results": [
            {"source": "metrics", "result": metrics_res},
            {"source": "logs", "result": logs_res},
            {"source": "fault", "result": fault_res["messages"][-1].content}
        ]
    }

def build_diagnosis_workflow():
    """
    构建一个专注于故障诊断的工作流，展示如何并行执行并汇总。
    
    这个 Workflow 强制执行诊断流程：
    1. Classify (决定是否需要诊断)
    2. Diagnosis Node (并行运行 Metrics + Logs -> Fault)
    3. Synthesize (最终格式化)
    """
    # 从环境变量或默认值获取配置，因为 LangGraph Server 调用时不传参数
    llm_model = os.getenv("LLM_MODEL", "gpt-4o")
    llm_key = os.getenv("LITELLM_API_KEY", "")
    llm_base = os.getenv("LITELLM_API_BASE", "")
    router_llm_model = os.getenv("ROUTER_LLM_MODEL", "gpt-4o-mini")
    
    llm = ChatLiteLLM(model=llm_model, temperature=0, timeout=30, api_key=llm_key, api_base=llm_base, max_tokens=4096)
    router_llm = ChatLiteLLM(model=router_llm_model, temperature=0, timeout=30, api_key=llm_key, api_base=llm_base, max_tokens=4096)

    metrics_agent = build_metrics_agent().build(llm)
    logs_agent = build_logs_agent().build(llm)
    fault_agent = build_fault_agent().build(llm)
    
    # 包装成无需参数的 callable
    async def run_diagnosis(state):
        return await diagnosis_node(state, metrics_agent, logs_agent, fault_agent)

    graph = (
        StateGraph(RouterState)
        .add_node("classify", lambda state: classify_query(state, router_llm))
        .add_node("diagnosis", run_diagnosis)
        .add_node("synthesize", lambda state: synthesize_results(state, router_llm))
        
        .add_edge(START, "classify")
        # 简单逻辑：如果分类器认为涉及 fault，则进入诊断流程，否则直接结束或走其他路径
        # 这里仅作演示，直接连接到 diagnosis
        .add_edge("classify", "diagnosis") 
        .add_edge("diagnosis", "synthesize")
        .add_edge("synthesize", END)
    )
    return graph.compile()
