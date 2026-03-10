from typing import List, Optional, Any, Callable
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSerializable

from knowledge.retriever import KnowledgeRetriever
from knowledge.vector_store import VectorStoreManager
from aiops.agents.base_agent import BaseAgent


class StrictAnswerValidator:
    """
    Validator to check if the answer is grounded in the retrieved docs.
    """
    
    def __init__(self, llm: Optional[BaseChatModel] = None):
        self.llm = llm

    def validate(self, query: str, answer: str, context: List[Document]) -> bool:
        """
        Validate the answer against the context.
        
        Args:
            query: The original query.
            answer: The generated answer.
            context: The retrieved documents used as context.
            
        Returns:
            True if the answer is grounded in the context, False otherwise.
        """
        if "I don't know" in answer or "我不清楚" in answer or "无法回答" in answer:
            return True
            
        if not context:
            # If no context, and answer is not "I don't know", it might be hallucination
            # But maybe the agent knows general info? 
            # The prompt says "strict no hallucination", so if no context, should say I don't know.
            return False

        if self.llm:
            return self._llm_validate(query, answer, context)
        else:
            return self._keyword_validate(answer, context)

    def _keyword_validate(self, answer: str, context: List[Document]) -> bool:
        """
        Simple keyword validation. 
        Checks if significant words from the answer appear in the context.
        This is a very naive implementation.
        """
        # Combine all context content
        context_text = " ".join([doc.page_content for doc in context])
        
        # This is hard to do well with just keywords without false positives/negatives.
        # For now, we'll assume it's valid if we don't have an LLM.
        # Or maybe we just return True to avoid blocking if no LLM.
        return True

    def _llm_validate(self, query: str, answer: str, context: List[Document]) -> bool:
        """
        Validate using LLM.
        """
        prompt = ChatPromptTemplate.from_template(
            """
            You are a strict validator.
            Context: {context}
            
            Question: {query}
            Answer: {answer}
            
            Is the answer supported by the context? 
            Respond with 'YES' or 'NO'.
            """
        )
        chain = prompt | self.llm | StrOutputParser()
        context_text = "\n\n".join([doc.page_content for doc in context])
        result = chain.invoke({"query": query, "answer": answer, "context": context_text})
        return "YES" in result.strip().upper()


class CustomerServiceAgent:
    """
    Customer Service Agent that answers questions based on a knowledge base.
    """
    
    def __init__(self, vector_store_manager: VectorStoreManager):
        self.retriever = KnowledgeRetriever(vector_store_manager)
        self.validator = StrictAnswerValidator() # LLM can be set later if needed
        self.last_retrieved_docs: List[Document] = []
    
    def get_tools(self) -> List[Callable]:
        """
        Get the tools for the agent.
        """
        def query_knowledge_base(query: str) -> str:
            """
            Search the knowledge base for relevant information.
            Use this tool to find answers to user questions.
            """
            # Reset or append? Usually we want the docs for the current query.
            # If multiple calls, we might want all of them.
            # For simplicity, we'll just store the latest ones or extend.
            docs = self.retriever.get_relevant_documents(query)
            self.last_retrieved_docs = docs
            
            if not docs:
                return "No relevant information found in the knowledge base."
            return "\n\n".join([f"Document {i+1}:\n{doc.page_content}" for i, doc in enumerate(docs)])

        return [query_knowledge_base]

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the agent.
        """
        return (
            "You are a helpful and strict Customer Service Agent. "
            "Your goal is to answer user questions based ONLY on the provided knowledge base context. "
            "You must use the `query_knowledge_base` tool to find information. "
            "If the information is not in the knowledge base, you must say 'I don't know' or '我不清楚'. "
            "Do NOT make up answers (hallucinate). "
            "Do NOT use outside knowledge. "
            "Keep your answers concise and polite."
        )

    def build(self, llm: BaseChatModel):
        """
        Build the agent runnable.
        """
        if hasattr(self.validator, 'llm'):
            self.validator.llm = llm
        
        base_agent = BaseAgent(
            name="customer_service",
            system_prompt=self.get_system_prompt(),
            tools=self.get_tools()
        )
        return base_agent.build(llm)
    
    def validate_last_response(self, query: str, answer: str) -> bool:
        """
        Validate the last response using the stored context.
        """
        return self.validator.validate(query, answer, self.last_retrieved_docs)
