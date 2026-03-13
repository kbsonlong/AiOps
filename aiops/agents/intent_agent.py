from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


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
    def __init__(self, llm):
        self.llm = llm

    def detect_query_intent(self, query: str) -> QueryIntent:
        structured = self.llm.with_structured_output(QueryIntent)
        return structured.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "You are an intent classifier for an AIOps system. "
                        "Classify the user's query intent.\n"
                        "- consultation: asks for information, explanation, documentation, concept definition.\n"
                        "- operation: asks to perform an action, check status, diagnose, analyze, troubleshoot.\n"
                        "Also detect the query language: zh/en/other.\n"
                        "Return only the structured output."
                    ),
                },
                {"role": "user", "content": query},
            ]
        )

    def gate_synthesis(self, query: str, knowledge_text: str) -> SynthesisGate:
        structured = self.llm.with_structured_output(SynthesisGate)
        return structured.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "You decide whether to synthesize a knowledge base response.\n"
                        "Input: user query + the knowledge base agent text.\n"
                        "If the knowledge text contains useful information (definitions, steps, partial answers), "
                        "set needs_synthesis=True and leave response empty.\n"
                        "If the knowledge text is a negative/unknown response (cannot answer / not found), "
                        "set needs_synthesis=False and provide a polite response in the SAME language as the user query, "
                        "stating the knowledge base does not contain this information.\n"
                        "Return only the structured output."
                    ),
                },
                {
                    "role": "user",
                    "content": f"User Query:\n{query}\n\nKnowledge Base Text:\n{knowledge_text}",
                },
            ]
        )
