"""LangGraph workflow definition for GitHub Repository Improvement Agent.

Graph Architectures:
1. Main Repository Agent Graph (Autonomous reasoning & tool execution)
2. Interactive Issue Approval Graph (Human-In-The-Loop explicit confirmation before mutation)
"""

import json
from typing import Any, Dict, List, Optional, TypedDict
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from backend.agent import get_llm, create_agent_node, extract_message_text
from backend.mcp_client import mcp_session_scope, multi_mcp_session_scope


def create_repository_agent_graph(
    tools: List[BaseTool],
    llm: Optional[BaseChatModel] = None,
):
    """Construct and compile the smallest working LangGraph agent with MCP tools.

    Args:
        tools: List of LangChain BaseTool instances connected to the MCP server.
        llm: Language model to drive reasoning (defaults to get_llm()).

    Returns:
        Compiled LangGraph runnable application.
    """
    if llm is None:
        llm = get_llm()

    agent_node = create_agent_node(llm, tools)
    tool_node = ToolNode(tools)

    workflow = StateGraph(MessagesState)

    # Add Nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # Add Edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    return workflow.compile()


async def run_repository_agent(prompt: str) -> dict:
    """Convenience helper to run the agent graph inside a single GitHub MCP session scope."""
    async with mcp_session_scope() as (session, tools):
        app = create_repository_agent_graph(tools=tools)
        result = await app.ainvoke({"messages": [("user", prompt)]})
        last_message = result["messages"][-1]
        final_answer = extract_message_text(last_message.content)
        return {
            "final_answer": final_answer,
            "messages": result["messages"],
        }


async def run_action_agent(
    prompt: str,
    server_names: Optional[List[str]] = None,
) -> dict:
    """Run the Personal Action Agent connected to multiple MCP servers (GitHub + LinkedIn)."""
    async with multi_mcp_session_scope(server_names) as (sessions, tools):
        app = create_repository_agent_graph(tools=tools)
        result = await app.ainvoke({"messages": [("user", prompt)]})
        last_message = result["messages"][-1]
        final_answer = extract_message_text(last_message.content)
        return {
            "final_answer": final_answer,
            "messages": result["messages"],
            "tools_count": len(tools),
        }



# =====================================================================
# Phase 8: Human-in-the-Loop (HITL) Issue Creation Workflow
# =====================================================================

class IssueWorkflowState(TypedDict):
    repo_url: str
    issue_title: str
    issue_body: str
    user_approved: Optional[bool]
    dry_run: bool
    status: str
    output: Optional[Dict[str, Any]]


def create_issue_approval_graph(tools: List[BaseTool]):
    """Construct a LangGraph graph with explicit Human-in-the-Loop verification for creating issues.

    Workflow:
      START
        │
        ▼
      [Review Proposed Issue Node]
        │
        ├─ (user_approved: True) ──► [Execute MCP create_issue] ──► END
        │
        └─ (user_approved: False/None) ──► [Abort Issue Creation] ──► END
    """
    create_tool = next((t for t in tools if t.name == "create_issue"), None)

    async def review_node(state: IssueWorkflowState) -> dict:
        """Inspect proposed issue and status."""
        return {
            "status": "pending_approval" if state.get("user_approved") is None else "reviewed"
        }

    async def execute_node(state: IssueWorkflowState) -> dict:
        """Invoke MCP create_issue tool ONLY after explicit confirmation."""
        if not create_tool:
            return {
                "status": "error",
                "output": {"error": True, "message": "create_issue tool not found on MCP server"},
            }
        res = await create_tool.ainvoke({
            "repo_url": state["repo_url"],
            "title": state["issue_title"],
            "body": state["issue_body"],
            "dry_run": state.get("dry_run", False),
        })
        text = res[0]["text"] if isinstance(res, list) and "text" in res[0] else str(res)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"raw": text}
        return {"status": "completed", "output": parsed}

    async def abort_node(state: IssueWorkflowState) -> dict:
        """Safely cancel issue creation if user denies or skips approval."""
        return {
            "status": "cancelled",
            "output": {
                "error": False,
                "message": "Issue creation safely cancelled upon user instruction. No changes were made to GitHub.",
            },
        }

    def route_decision(state: IssueWorkflowState) -> str:
        if state.get("user_approved") is True:
            return "execute"
        return "abort"

    workflow = StateGraph(IssueWorkflowState)
    workflow.add_node("review", review_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("abort", abort_node)

    workflow.add_edge(START, "review")
    workflow.add_conditional_edges("review", route_decision, {
        "execute": "execute",
        "abort": "abort",
    })
    workflow.add_edge("execute", END)
    workflow.add_edge("abort", END)

    return workflow.compile()


# =====================================================================
# LinkedIn Post Human-in-the-Loop (HITL) Workflow
# =====================================================================

class PostWorkflowState(TypedDict):
    content: str
    image_url: Optional[str]
    user_approved: Optional[bool]
    dry_run: bool
    status: str
    output: Optional[Dict[str, Any]]


def create_post_approval_graph(tools: List[BaseTool]):
    """Construct a LangGraph graph with explicit Human-in-the-Loop verification for LinkedIn posts.

    Workflow:
      START
        │
        ▼
      [Review Proposed Post Node]
        │
        ├─ (user_approved: True) ──► [Execute MCP create_post] ──► END
        │
        └─ (user_approved: False/None) ──► [Abort Post Publication] ──► END
    """
    post_tool = next((t for t in tools if t.name == "create_post"), None)

    async def review_node(state: PostWorkflowState) -> dict:
        """Inspect proposed post and approval status."""
        return {
            "status": "pending_approval" if state.get("user_approved") is None else "reviewed"
        }

    async def execute_node(state: PostWorkflowState) -> dict:
        """Invoke MCP create_post tool ONLY after explicit human confirmation."""
        if not post_tool:
            return {
                "status": "error",
                "output": {"error": True, "message": "create_post tool not found on MCP server"},
            }
        res = await post_tool.ainvoke({
            "content": state["content"],
            "image_url": state.get("image_url"),
            "dry_run": state.get("dry_run", False),
        })
        text = res[0]["text"] if isinstance(res, list) and "text" in res[0] else str(res)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"raw": text}
        return {"status": "completed", "output": parsed}

    async def abort_node(state: PostWorkflowState) -> dict:
        """Safely cancel post publication if user denies or skips approval."""
        return {
            "status": "cancelled",
            "output": {
                "error": False,
                "message": "Post publication safely cancelled upon user instruction. No changes were made to LinkedIn.",
            },
        }

    def route_decision(state: PostWorkflowState) -> str:
        if state.get("user_approved") is True:
            return "execute"
        return "abort"

    workflow = StateGraph(PostWorkflowState)
    workflow.add_node("review", review_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("abort", abort_node)

    workflow.add_edge(START, "review")
    workflow.add_conditional_edges("review", route_decision, {
        "execute": "execute",
        "abort": "abort",
    })
    workflow.add_edge("execute", END)
    workflow.add_edge("abort", END)

    return workflow.compile()

