"""Agent definitions and LLM configuration for GitHub Repository Improvement Agent."""

import os
from typing import Any, Callable, List, Optional
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langgraph.graph import MessagesState

load_dotenv()


def get_llm(model_name: Optional[str] = None) -> BaseChatModel:
    """Initialize and return the configured chat language model.

    Supports:
    1. Google Gemini (via GOOGLE_API_KEY / GEMINI_API_KEY)
    2. OpenAI (via OPENAI_API_KEY)
    3. Groq (via GROQ_API_KEY)
    """
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    if google_key and google_key.strip():
        from langchain_google_genai import ChatGoogleGenerativeAI
        primary_model = model_name or "gemini-3-flash-preview"
        primary_llm = ChatGoogleGenerativeAI(model=primary_model)
        fallback_models = [m for m in ["gemini-3.1-flash-lite-preview", "gemini-3.1-flash-lite"] if m != primary_model]
        fallbacks = [ChatGoogleGenerativeAI(model=fb) for fb in fallback_models]
        return primary_llm.with_fallbacks(fallbacks, exceptions_to_handle=(Exception,))

    if openai_key and openai_key.strip():
        from langchain_openai import ChatOpenAI
        target_model = model_name or "gpt-4o-mini"
        return ChatOpenAI(model=target_model, temperature=0)

    if groq_key and groq_key.strip():
        from langchain_groq import ChatGroq
        target_model = model_name or "llama-3.3-70b-versatile"
        return ChatGroq(model_name=target_model, temperature=0)

    raise ValueError(
        "No supported LLM API key found. Please set GOOGLE_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY in .env"
    )


def extract_message_text(content: Any) -> str:
    """Extract plain text string from LangChain message content (handles string or list of content dicts)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


def create_agent_node(llm: BaseChatModel, tools: List[BaseTool]) -> Callable[[MessagesState], dict]:
    """Create the primary Repository Analyzer agent node function for LangGraph.

    Args:
        llm: Language model instance.
        tools: List of LangChain BaseTool instances (backed by MCP server).

    Returns:
        A callable node function matching LangGraph MessagesState signature.
    """
    llm_with_tools = llm.bind_tools(tools)

    def agent_node(state: MessagesState) -> dict:
        """Agent node: Receives conversation history, decides next tool or final response."""
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    return agent_node
