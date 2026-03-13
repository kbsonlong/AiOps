from __future__ import annotations
import os
import json
import asyncio
import operator
from typing import Annotated, Literal, TypedDict, Optional

from langchain_litellm import ChatLiteLLM
from langchain_litellm import ChatLiteLLMRouter
from litellm import Router
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
from aiops.config import load_settings
from aiops.config.validator import validate_settings
from aiops.agents.knowledge_agent import KnowledgeAgent
from aiops.knowledge.vector_store import VectorStoreManager
from aiops.skills import SkillCompositionEngine, SkillDiscoveryService
from aiops.skills.global_registry import get_global_skill_registry
from aiops.workflows.skill_middleware import get_skill_post_middleware_chain, get_skill_pre_middleware_chain
from aiops.core.error_handler import get_logger, log_exception, safe_execute
from aiops.exceptions import AgentException, ConfigException


Severity = Literal["low", "medium", "high", "critical"]
Source = Literal["metrics", "logs", "fault", "security", "knowledge_base"]


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
    context: dict
    detected_skills: list[dict]
    skill_execution_plan: dict
    knowledge_context: Optional[str]
    knowledge_base_result: Optional[str]


class ClassificationResult(BaseModel):
    classifications: list[Classification] = Field(
        description="Agents to invoke with targeted queries and severity level"
    )
    needs_clarification: bool = Field(
        description="True if the user query is ambiguous and needs clarification"
    )
    clarification_message: Optional[str] = Field(
        description="If needs_clarification is True, provide a polite question to ask the user for more details in their language. Otherwise empty."
    )
    user_intent: Optional[Literal["consultation", "operation"]] = Field(
        default=None,
        description="High-level intent: consultation (ask for info) or operation (perform action)"
    )
    user_language: Optional[Literal["zh", "en", "other"]] = Field(
        default=None,
        description="User query language for response formatting"
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

def _classify_fallback(query_text: str) -> list[Classification]:
    lowered = query_text.lower()
    if any(k in lowered for k in ("log", "日志", "error", "exception", "panic", "fatal")):
        return [{"source": "logs", "query": query_text, "severity": "medium"}]
    if any(k in lowered for k in ("cpu", "内存", "memory", "disk", "磁盘", "network", "网络", "prometheus", "metrics", "指标")):
        return [{"source": "metrics", "query": query_text, "severity": "medium"}]
    if any(k in lowered for k in ("漏洞", "入侵", "攻击", "安全", "auth", "permission", "403", "401", "unauthorized")):
        return [{"source": "security", "query": query_text, "severity": "high"}]
    return [{"source": "knowledge_base", "query": query_text, "severity": "low"}]

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
        parser = JsonOutputParser(pydantic_object=ClassificationResult)
        prompt = PromptTemplate(
            template=(
                "You are a helpful AIOps assistant.\n"
                "Analyze the query and decide which agents to call.\n"
                "Return ONLY a valid JSON object matching the schema below.\n"
                "Do NOT include any markdown formatting (like ```json), explanations, or extra text.\n\n"
                "Schema:\n{format_instructions}\n\n"
                "Query: {query}\n\n"
                "Rules:\n"
                "1. Use 'knowledge_base' for queries about 'how-to', 'what is', 'policy', 'introduce', or general knowledge.\n"
                "2. Use 'metrics'/'logs' for system status checks (cpu, memory, error logs).\n"
                "3. AMBIGUITY CHECK: If the query is ambiguous (e.g., 'what is my system version?'), do NOT guess. "
                "Ask for clarification: 'Do you mean the Operating System version (use tools) or the Business System version (use knowledge base)?'. "
                "Set needs_clarification=True and provide a clarification_message in the user's language."
                "\n\nOptional: If useful for downstream processing, also classify the high-level intent (consultation/operation) and language (zh/en/other).\n\n"
                "JSON Response:"
            ),
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
            if obj.needs_clarification:
                return {
                    "query": query_text, 
                    "classifications": [], 
                    "final_answer": obj.clarification_message
                }
            
            # Store intent info in context if available
            context_update = {}
            if obj.user_intent:
                context_update["user_intent"] = obj.user_intent
            if obj.user_language:
                context_update["user_language"] = obj.user_language
                
            return {
                "query": query_text, 
                "classifications": obj.classifications,
                "context": {**state.get("context", {}), **context_update}
            }
    except Exception as e:
        log_exception(
            e,
            operation="router.classify_query",
            logger=get_logger(),
            extra={"query_len": len(query_text)},
        )
        
    return {"query": query_text, "classifications": _classify_fallback(query_text)}


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
    classifications = state.get("classifications", [])
    
    # Check if we have a direct final answer from classification (e.g. clarification)
    # If so, we don't route to any agents, but we still need to end the workflow.
    # However, LangGraph conditional edges must return valid nodes or END.
    # If we return empty list, the graph might stop or error depending on configuration.
    # But wait, if 'classify' node already set 'final_answer', we should probably route to END directly?
    # The current graph structure is classify -> conditional_edge -> agents.
    # If we return [], no agents are called. Then 'skill_orchestrate' is called in parallel?
    # No, 'skill_orchestrate' is a separate parallel branch from 'classify'? 
    # Let's look at the graph definition:
    # .add_edge("skill_middleware_pre", "classify")
    # .add_conditional_edges("classify", route_to_agents, [...])
    # .add_edge("classify", "skill_orchestrate")
    
    # It seems 'classify' goes to 'skill_orchestrate' unconditionally via normal edge,
    # AND to agents via conditional edge.
    
    # If we have a final answer (clarification), we should probably avoid calling agents.
    # So returning [] is correct for the agents part.
    # But 'skill_orchestrate' will still run. That might be okay, or we might want to prevent it.
    
    if not classifications:
        # Check if we have a final answer (clarification) set in the state by 'classify' node
        # But wait, conditional_edges receives 'state' as argument.
        # So we can check state['final_answer'] here.
        if state.get("final_answer"):
            # Return a valid destination that does nothing or goes to end.
            # We can route to 'synthesize' which will just return the final answer.
            # Or we can return [] and let the graph logic handle it (but it seems to continue to orchestrate).
            # The cleanest way in current graph structure (classify -> skill_orchestrate)
            # is to just let it flow. The agents won't be called.
            # 'skill_orchestrate' will run (harmless).
            # Then 'synthesize' will run.
            return []
        return []

    enriched = _ensure_critical_agents(list(classifications), state["query"])
    return [Send(item["source"], {"query": item["query"]}) for item in enriched]


def _safe_extract_content(resp) -> str:
    try:
        # 兼容字典结构
        if isinstance(resp, dict):
            # 优先检查 messages 字段
            if "messages" in resp:
                msgs = resp.get("messages")
                if not msgs:
                    return ""
                last = msgs[-1]
                # 兼容对象或字典
                if hasattr(last, "content"):
                    return _coerce_text(getattr(last, "content"))
                if isinstance(last, dict):
                    return _coerce_text(last.get("content"))
        # 兜底：直接转文本
        return _coerce_text(resp)
    except Exception:
        return ""


def _invoke_agent(agent, query_text: str) -> str:
    def _run() -> str:
        payload = {"messages": [{"role": "user", "content": query_text}]}
        resp = agent.invoke(payload)
        return _safe_extract_content(resp)

    result = safe_execute(
        _run,
        operation="router.invoke_agent",
        fallback=AgentException("agent_invoke_failed").safe_message,
        logger=get_logger(),
        extra={"agent": getattr(agent, "name", type(agent).__name__)},
    )
    return result or AgentException("agent_invoke_failed").safe_message


def make_query_node(agent, source: Source):
    def node(state: AgentInput) -> dict:
        query_text = _normalize_query(state.get("query"))
        content = _invoke_agent(agent, query_text)
        return {"results": [{"source": source, "result": content}]}
    return node


def knowledge_base_node(state: AgentInput, knowledge_agent, vector_store, llm) -> dict:
    """
    执行节点：调用知识库代理 (RAG) 回答一般性问题。
    使用显式 RAG 流程，避免依赖小模型的工具调用能力。
    """
    query_text = _normalize_query(state.get("query"))
    
    # 1. 检索
    # Increase k for better recall
    docs = vector_store.similarity_search(query_text, k=6)
    context = "\n\n".join([f"Document {i+1}:\n{doc.page_content}" for i, doc in enumerate(docs)])
    
    if not docs:
        context = "No relevant documents found."
    
    # 2. 生成
    system_prompt = (
        "You are a helpful and strict Knowledge Base Agent. "
        "Your goal is to answer user questions based ONLY on the provided knowledge base context. "
        "If the information is not in the knowledge base, you must say 'I don't know' or '我不清楚'. "
        "Do NOT make up answers (hallucinate). "
        "Do NOT use outside knowledge. "
        "Keep your answers concise and polite."
        "When answering, please try to extract relevant information from the context as much as possible, rather than strictly matching keywords."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query_text}"}
    ]
    
    response = llm.invoke(messages)
    answer = response.content
    
    return {
        "results": [{"source": "knowledge_base", "result": answer}],
        "knowledge_base_result": answer,
        "knowledge_context": context
    }


def synthesize_results(state: RouterState, router_llm) -> dict:
    """
    汇总节点：收集所有代理的执行结果，生成最终的分析报告。
    
    Args:
        state: 包含所有代理执行结果(results)的状态
        router_llm: 用于生成的 LLM
    """
    # Check if we already have a final answer (e.g. clarification from classify node)
    if state.get("final_answer") and state["final_answer"].strip():
        return {"final_answer": state["final_answer"]}

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
                "If there is a 'knowledge_base' result, ensure it is the primary source for 'how-to' or general knowledge questions. "
                "CRITICAL: If the provided knowledge base result indicates it cannot answer (e.g., 'I don't know', 'not mentioned', 'no information'), "
                "and no other agent provided relevant info, you MUST admit you don't know and return that negative response directly. "
                "Do NOT fabricate an answer, do NOT offer general advice unrelated to the specific question context."
            ),
        },
        {"role": "user", "content": "\n\n".join(formatted)},
    ])
    return {"final_answer": synthesis_response.content}


def make_skill_middleware_pre_node():
    chain = get_skill_pre_middleware_chain()

    def node(state: RouterState) -> dict:
        updated = chain.run(state)
        update: dict = {}
        if updated.get("query") != state.get("query"):
            update["query"] = updated.get("query")
        if updated.get("context") != state.get("context"):
            update["context"] = updated.get("context", {})
        return update

    return node


def make_synthesize_with_middlewares_node(router_llm):
    chain = get_skill_post_middleware_chain()

    def terminal(state: RouterState) -> dict:
        update = synthesize_results(state, router_llm)
        return {**state, **update}

    def node(state: RouterState) -> dict:
        final_state = chain.run(state, terminal=terminal)
        update: dict = {"final_answer": final_state.get("final_answer", "")}
        if "context" in final_state:
            update["context"] = final_state.get("context", {})
        return update

    return node


def skill_orchestration_node(state: RouterState) -> dict:
    """
    技能编排节点：基于查询动态发现和规划原子技能的执行顺序。
    
    使用 SkillRegistry 和 SkillCompositionEngine 来构建执行计划。
    """
    registry = get_global_skill_registry()
    discovery = SkillDiscoveryService(registry=registry)
    query_text = _normalize_query(state.get("query"))
    skills = discovery.recommend_skills(query_text)
    engine = SkillCompositionEngine()
    plan = engine.build_execution_plan(skills, context={"query": query_text})
    return {
        "detected_skills": [skill.model_dump() for skill in skills],
        "skill_execution_plan": {"order": plan.execution_order},
    }


def build_workflow(llm, router_llm, settings=None):
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
    
    vector_store = VectorStoreManager(settings=settings)
    knowledge_agent = KnowledgeAgent(vector_store).build(llm)

    graph = (
        StateGraph(RouterState)
        .add_node("skill_middleware_pre", make_skill_middleware_pre_node())
        .add_node("classify", lambda state: classify_query(state, router_llm))
        .add_node("skill_orchestrate", skill_orchestration_node)
        .add_node("metrics", make_query_node(metrics_agent, "metrics"))
        .add_node("logs", make_query_node(logs_agent, "logs"))
        .add_node("fault", make_query_node(fault_agent, "fault"))
        .add_node("security", make_query_node(security_agent, "security"))
        .add_node("knowledge_base", lambda state: knowledge_base_node(state, knowledge_agent, vector_store, llm))
        .add_node("synthesize", make_synthesize_with_middlewares_node(router_llm))
        .add_node("skill_middleware_post", lambda state: {})
        .add_edge(START, "skill_middleware_pre")
        .add_edge("skill_middleware_pre", "classify")
        .add_conditional_edges("classify", route_to_agents, ["metrics", "logs", "fault", "security", "knowledge_base"])
        .add_edge("classify", "skill_orchestrate")
        .add_edge("metrics", "synthesize")
        .add_edge("logs", "synthesize")
        .add_edge("fault", "synthesize")
        .add_edge("security", "synthesize")
        .add_edge("knowledge_base", "synthesize")
        .add_edge("skill_orchestrate", "synthesize")
        .add_edge("synthesize", "skill_middleware_post")
        .add_edge("skill_middleware_post", END)
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
    settings = load_settings()
    validation = validate_settings(settings)
    if not validation.valid:
        raise ConfigException(validation.to_message())

    # Main LLM for complex tasks (synthesis, agent execution)
    llm_model = os.getenv("LLM_MODEL", "gpt-4o")
    llm_key = os.getenv("LITELLM_API_KEY","")
    llm_base = os.getenv("LITELLM_API_BASE","")
    llm = ChatLiteLLM(model=llm_model, temperature=0, timeout=30, api_key=llm_key, api_base=llm_base, max_tokens=4096,custom_llm_provider="openai",api_version="2024-10-21")
    
    # Router LLM for classification (faster, cheaper)
    router_llm_model = os.getenv("ROUTER_LLM_MODEL", "gpt-4o-mini")
    router_llm = ChatLiteLLM(model=router_llm_model, temperature=0, timeout=30, api_key=llm_key, api_base=llm_base, max_tokens=4096,custom_llm_provider="openai",api_version="2024-10-21")
    return build_workflow(llm, router_llm, settings=settings)


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
    
    metrics_res = _safe_extract_content(results[0])
    logs_res = _safe_extract_content(results[1])
    
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
            {"source": "fault", "result": _safe_extract_content(fault_res)}
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
