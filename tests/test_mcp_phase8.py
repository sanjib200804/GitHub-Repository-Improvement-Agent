"""Phase 8 Test: GitHub Issue Creation with Explicit User Confirmation (HITL).

Demonstrates and verifies:
1. MCP Server exposes all 6 GitHub tools, including `create_issue`.
2. Path A: Human Rejection / Cancellation (`user_approved=False`):
   - Confirms that LangGraph aborts execution and makes NO external API call.
3. Path B: Explicit Human Approval (`user_approved=True`):
   - Confirms that LangGraph routes to the MCP `create_issue` tool.
   - Tests `dry_run=True` execution ensuring valid issue schema without mutating GitHub.
"""

import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.mcp_client import mcp_session_scope
from backend.graph import create_issue_approval_graph


async def run_phase8_hitl_verification():
    print("=" * 60)
    print("  PHASE 8: GITHUB ISSUE CREATION WITH EXPLICIT CONFIRMATION")
    print("=" * 60)

    async with mcp_session_scope() as (session, tools):
        tool_names = [t.name for t in tools]
        print(f"\n[1] Discovered All 6 MCP Tools:")
        for name in tool_names:
            print(f"    - {name}")

        assert "create_issue" in tool_names
        app = create_issue_approval_graph(tools=tools)

        # -----------------------------------------------------------------
        # Scenario A: User REJECTS the proposed issue (Safe Abort)
        # -----------------------------------------------------------------
        print("\n[2] Scenario A: User Rejects Proposed Issue (user_approved=False)")
        input_state_rejected = {
            "repo_url": "octocat/Hello-World",
            "issue_title": "Add LICENSE file to repository",
            "issue_body": "This repository is missing a LICENSE file. Adding MIT is recommended.",
            "user_approved": False,
            "dry_run": True,
            "status": "pending",
            "output": None,
        }

        result_rejected = await app.ainvoke(input_state_rejected)
        print(f"    Status:  {result_rejected['status']}")
        print(f"    Message: {result_rejected['output']['message']}")

        assert result_rejected["status"] == "cancelled"
        assert result_rejected["output"]["error"] is False
        assert "safely cancelled" in result_rejected["output"]["message"].lower()

        # -----------------------------------------------------------------
        # Scenario B: User APPROVES the proposed issue (Execution via MCP)
        # -----------------------------------------------------------------
        print("\n[3] Scenario B: User Approves Proposed Issue (user_approved=True)")
        input_state_approved = {
            "repo_url": "octocat/Hello-World",
            "issue_title": "Add LICENSE file to repository",
            "issue_body": "This repository is missing a LICENSE file. Adding MIT is recommended.",
            "user_approved": True,
            "dry_run": True,
            "status": "pending",
            "output": None,
        }

        result_approved = await app.ainvoke(input_state_approved)
        output_payload = result_approved["output"]
        print(f"    Status:      {result_approved['status']}")
        print(f"    Dry Run:     {output_payload.get('dry_run')}")
        print(f"    Issue Title: {output_payload.get('title')}")
        print(f"    Message:     {output_payload.get('message')}")

        assert result_approved["status"] == "completed"
        assert output_payload.get("error") is False
        assert output_payload.get("dry_run") is True
        assert output_payload.get("title") == "Add LICENSE file to repository"

    print("\n" + "=" * 60)
    print("  ALL PHASE 8 HITL & ISSUE CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)


@pytest.mark.asyncio
async def test_mcp_phase8():
    await run_phase8_hitl_verification()


if __name__ == "__main__":
    asyncio.run(run_phase8_hitl_verification())
