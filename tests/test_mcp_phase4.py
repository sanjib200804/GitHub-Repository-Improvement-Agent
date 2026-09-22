"""Phase 4 MCP Protocol Test: Minimal LangGraph Agent Workflow.

Demonstrates and verifies:
1. Building the minimal LangGraph agent: START -> agent -> tools (MCP) -> agent -> END.
2. The agent deciding which MCP tool to call based on user input.
3. LangGraph ToolNode executing the MCP tool over stdio transport.
4. Returning MCP tool results back to the agent node.
5. Generating the final user-facing response.
"""

import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.graph import run_repository_agent


async def run_phase4_langgraph_verification():
    print("=" * 60)
    print("  PHASE 4: LANGGRAPH AGENT & MCP TOOLS VERIFICATION")
    print("=" * 60)

    prompt = "What is the primary description and stars count of the repository octocat/Hello-World? Use your tools to check."
    print(f"\n[1] Sending User Request to LangGraph Agent:\n    '{prompt}'\n")

    result = await run_repository_agent(prompt)
    messages = result["messages"]

    print(f"[2] Execution Trace ({len(messages)} graph steps):")
    tool_calls_observed = []

    for idx, msg in enumerate(messages):
        msg_type = msg.type
        print(f"\n    Step {idx + 1}: [{msg_type.upper()}]")
        if msg_type == "human":
            print(f"      Content: {msg.content}")
        elif msg_type == "ai":
            if getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    tool_calls_observed.append(tc["name"])
                    print(f"      Decision: CALL TOOL -> '{tc['name']}' with args: {tc['args']}")
            else:
                text = msg.content if isinstance(msg.content, str) else str(msg.content)[:200]
                print(f"      Final Answer:\n        {text}")
        elif msg_type == "tool":
            raw_content = msg.content if isinstance(msg.content, str) else str(msg.content)
            print(f"      MCP Tool Output: {raw_content[:150]}...")

    # Assertions
    assert len(tool_calls_observed) > 0, "Expected at least one MCP tool call by the agent"
    assert "get_repository" in tool_calls_observed, "Expected 'get_repository' tool to be selected"
    assert len(result["final_answer"]) > 0, "Expected non-empty final response"
    assert "Hello-World" in result["final_answer"] or "first repository" in result["final_answer"].lower()

    print("\n" + "=" * 60)
    print("  ALL PHASE 4 LANGGRAPH MCP CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)


@pytest.mark.asyncio
async def test_mcp_phase4():
    await run_phase4_langgraph_verification()


if __name__ == "__main__":
    asyncio.run(run_phase4_langgraph_verification())
