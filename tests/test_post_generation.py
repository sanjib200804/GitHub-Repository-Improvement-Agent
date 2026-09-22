"""Tests for GitHub-to-LinkedIn Post Generation and Multi-MCP Agent Workflows."""

import asyncio
import os
import sys
from unittest.mock import patch, MagicMock
import pytest

from backend.post_generator import (
    generate_project_post,
    generate_project_image,
    create_post_from_github_repo,
)
from backend.mcp_client import multi_mcp_session_scope
from backend.graph import create_post_approval_graph


def test_generate_project_post_structure():
    """Verify generate_project_post follows the authentic developer structure."""
    fake_evidence = {
        "metadata": {
            "name": "ai-website-builder",
            "full_name": "sanjib200804/ai-website-builder",
            "description": "Full-stack AI website builder generating production React code.",
            "language": "TypeScript",
        },
        "manifest": "dependencies: react, next.js, fastapi, langchain",
        "readme": "An AI website builder with drag-and-drop support and automated code generation.",
    }

    with patch.dict(os.environ, {"LINKEDIN_MOCK": "true"}):
        res = generate_project_post("sanjib200804/ai-website-builder", repo_evidence=fake_evidence)
        assert res["error"] is False
        assert res["repo_name"] == "ai-website-builder"
        assert "https://github.com/sanjib200804/ai-website-builder" in res["repo_url"]

        post = res["post_content"]
        # Verify core developer post sections
        assert "🚀 I recently built" in post
        assert "Key features:" in post
        assert "Tech stack:" in post
        assert "One of the most interesting parts was" in post
        assert "I learned" in post
        assert "GitHub:" in post
        assert "#" in post


def test_generate_project_image_fallback():
    """Verify generate_project_image handles unavailable image service gracefully without crashing."""
    with patch.dict(os.environ, {"LINKEDIN_MOCK": ""}):
        img = generate_project_image("sample-repo", "A sample tool", ["Python"])
        assert img is None or isinstance(img, str)


def test_create_post_from_github_repo_hitl_gate():
    """Verify create_post_from_github_repo requires explicit user approval before publishing."""
    fake_evidence = {
        "metadata": {"name": "sample-tool", "full_name": "user/sample-tool", "description": "A demo tool"},
        "manifest": "",
        "readme": "Demo",
    }

    with patch("backend.post_generator.collect_repository_evidence", return_value=fake_evidence):
        with patch.dict(os.environ, {"LINKEDIN_MOCK": "true"}):
            # 1. Without user confirmation (publish=False) -> Awaiting confirmation
            res_unapproved = create_post_from_github_repo("user/sample-tool", publish=False)
            assert res_unapproved["status"] == "awaiting_user_confirmation"
            assert "Explicit user confirmation is required" in res_unapproved["message"]

            # 2. In dry_run mode -> Validates without publishing
            res_dry = create_post_from_github_repo("user/sample-tool", publish=True, dry_run=True)
            assert res_dry["status"] == "dry_run_validated"
            assert res_dry["dry_run"] is True


@pytest.mark.asyncio
async def test_multi_mcp_client_discovery():
    """Verify multi_mcp_session_scope discovers tools from both GitHub and LinkedIn MCP servers."""
    env = os.environ.copy()
    env["LINKEDIN_MOCK"] = "true"

    with patch.dict(os.environ, {"LINKEDIN_MOCK": "true"}):
        async with multi_mcp_session_scope(["github", "linkedin"]) as (sessions, tools):
            assert "github" in sessions
            assert "linkedin" in sessions

            tool_names = [t.name for t in tools]
            # Verify GitHub tools discovered
            assert "get_repository" in tool_names
            assert "read_file" in tool_names
            assert "create_issue" in tool_names

            # Verify LinkedIn tools discovered
            assert "get_profile" in tool_names
            assert "analyze_profile" in tool_names
            assert "create_post" in tool_names
            assert "delete_post" in tool_names
            assert "update_profile" in tool_names


@pytest.mark.asyncio
async def test_post_approval_graph_execution():
    """Verify Post Approval LangGraph routes to execute on approval and aborts when rejected."""
    mock_post_tool = MagicMock()
    mock_post_tool.name = "create_post"

    async def mock_invoke(args):
        return [{"text": '{"error": false, "post_id": "urn:li:share:999", "message": "Published"}'}]

    mock_post_tool.ainvoke = mock_invoke

    app = create_post_approval_graph([mock_post_tool])

    # Case 1: Approved -> Completed
    state_approved = {
        "content": "Test post",
        "image_url": None,
        "user_approved": True,
        "dry_run": True,
        "status": "pending",
        "output": None,
    }
    res_approved = await app.ainvoke(state_approved)
    assert res_approved["status"] == "completed"
    assert res_approved["output"]["post_id"] == "urn:li:share:999"

    # Case 2: Rejected -> Cancelled
    state_rejected = {
        "content": "Test post",
        "image_url": None,
        "user_approved": False,
        "dry_run": True,
        "status": "pending",
        "output": None,
    }
    res_rejected = await app.ainvoke(state_rejected)
    assert res_rejected["status"] == "cancelled"
    assert "safely cancelled" in res_rejected["output"]["message"]
