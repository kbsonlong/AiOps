from __future__ import annotations

import warnings
from typing import Literal, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

# Deprecation warning
warnings.warn(
    "IntentAgent is deprecated and will be removed in a future version. "
    "Intent detection has been merged into the classify_query node in router_workflow.py. "
    "This class is kept for backward compatibility only.",
    DeprecationWarning,
    stacklevel=2
)


class QueryIntent(BaseModel):
    intent: Literal["consultation", "operation"] = Field(
        description="consultation: information/explanation/documentation/definition; operation: perform/check/diagnose/analyze/execute"
    )
    language: Literal["zh", "en", "other"] = Field(description="User query language")
    reason: str = Field(description="Short reason")


class SynthesisGate(BaseModel):
    needs_synthesis: bool = Field(
        description="True if the knowledge base text contains useful info that should be synthesized; False if it is a negative/unknown response."
    )
    response: Optional[str] = Field(
        description="If needs_synthesis is False, provide a polite response in the same language as the user query. Otherwise empty."
    )
    language: Optional[Literal["zh", "en", "other"]] = Field(description="User query language")
    reason: str = Field(description="Short reason")


class IntentAgent:
    """Intent detection agent (DEPRECATED).

    .. deprecated::
        Intent detection has been merged into the `classify_query` node
        in `router_workflow.py`. This class is kept for backward compatibility
        only and will be removed in a future version.

        Use `classify_query` function from `aiops.workflows.router_workflow`
        for combined intent and classification detection.
    """

    def __init__(self, llm):
        warnings.warn(
            f"{self.__class__.__name__} is deprecated. "
            "Use classify_query from router_workflow instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.llm = llm
    def __init__(self, llm):
        self.llm = llm

    def detect_query_intent(self, query: str) -> QueryIntent:
        parser = JsonOutputParser(pydantic_object=QueryIntent)
        prompt = PromptTemplate(
            template=(
                "You are an intent classifier for an AIOps system.\n"
                "Classify the user's query intent:\n"
                "- consultation: asks for information, explanation, documentation, concept definition.\n"
                "- operation: asks to perform an action, check status, diagnose, analyze, troubleshoot.\n"
                "Also detect the query language: zh/en/other.\n\n"
                "Return ONLY a valid JSON object matching the schema below.\n"
                "Do NOT include any markdown formatting, explanations, or extra text.\n\n"
                "Schema:\n{format_instructions}\n\n"
                "Query: {query}\n\n"
                "JSON Response:"
            ),
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        result = (prompt | self.llm | parser).invoke({"query": query})
        if isinstance(result, dict):
            return QueryIntent.model_validate(result)
        return QueryIntent.model_validate_json(str(result))

    def gate_synthesis(self, query: str, knowledge_text: str) -> SynthesisGate:
        parser = JsonOutputParser(pydantic_object=SynthesisGate)
        prompt = PromptTemplate(
            template=(
                "You decide whether to synthesize a knowledge base response.\n"
                "Input: user query + the knowledge base agent text.\n"
                "If the knowledge text contains useful information (definitions, steps, partial answers), "
                "set needs_synthesis=true and leave response empty.\n"
                "If the knowledge text is a negative/unknown response (cannot answer / not found), "
                "set needs_synthesis=false and provide a polite response in the SAME language as the user query, "
                "stating the knowledge base does not contain this information.\n\n"
                "Return ONLY a valid JSON object matching the schema below.\n"
                "Do NOT include any markdown formatting, explanations, or extra text.\n\n"
                "Schema:\n{format_instructions}\n\n"
                "User Query: {query}\n\n"
                "Knowledge Base Text: {knowledge_text}\n\n"
                "JSON Response:"
            ),
            input_variables=["query", "knowledge_text"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        result = (prompt | self.llm | parser).invoke({"query": query, "knowledge_text": knowledge_text})
        if isinstance(result, dict):
            return SynthesisGate.model_validate(result)
        return SynthesisGate.model_validate_json(str(result))
