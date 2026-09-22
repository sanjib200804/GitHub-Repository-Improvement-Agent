"""Unit and MCP Integration Tests for LinkedIn Server and OAuth Module."""

import asyncio
import json
import os
import sys
from unittest.mock import patch, MagicMock
import pytest
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

from mcp_servers.linkedin.oauth import get_authorization_url, exchange_code_for_token
from mcp_servers.linkedin.tools import fetch_linkedin_profile


def test_oauth_authorization_url_missing_client_id():
    """Test get_authorization_url returns error when no client_id is available."""
    with patch.dict(os.environ, {"LINKEDIN_CLIENT_ID": ""}, clear=True):
        res = get_authorization_url(client_id=None)
        assert res["error"] is True
        assert "LINKEDIN_CLIENT_ID is missing" in res["message"]
        assert res["authorization_url"] is None


def test_oauth_authorization_url_success():
    """Test get_authorization_url creates a valid LinkedIn OAuth URL."""
    res = get_authorization_url(
        client_id="test_client_id_123",
        redirect_uri="http://localhost:8000/callback",
        scopes=["openid", "profile", "email"],
        state="secure_test_csrf",
    )
    assert res["error"] is False
    assert "https://www.linkedin.com/oauth/v2/authorization" in res["authorization_url"]
    assert "client_id=test_client_id_123" in res["authorization_url"]
    assert "response_type=code" in res["authorization_url"]
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcallback" in res["authorization_url"]
    assert "state=secure_test_csrf" in res["authorization_url"]
    assert "openid" in res["authorization_url"]


def test_exchange_code_validation():
    """Test exchange_code_for_token validates empty inputs."""
    res_empty_code = exchange_code_for_token(code="")
    assert res_empty_code["error"] is True

    with patch.dict(os.environ, {"LINKEDIN_CLIENT_ID": "", "LINKEDIN_CLIENT_SECRET": ""}, clear=True):
        res_missing_secrets = exchange_code_for_token(code="some_code", client_id=None, client_secret=None)
        assert res_missing_secrets["error"] is True
        assert "LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET are required" in res_missing_secrets["message"]


def test_fetch_profile_unconfigured():
    """Test fetch_linkedin_profile without token or mock returns a helpful error."""
    with patch.dict(os.environ, {"LINKEDIN_ACCESS_TOKEN": "", "LINKEDIN_MOCK": ""}, clear=True):
        res = fetch_linkedin_profile(access_token=None)
        assert res["error"] is True
        assert "LINKEDIN_ACCESS_TOKEN is not configured" in res["message"]


def test_fetch_profile_mock_mode():
    """Test fetch_linkedin_profile returns structured mock profile when LINKEDIN_MOCK is set."""
    with patch.dict(os.environ, {"LINKEDIN_MOCK": "true"}, clear=True):
        res = fetch_linkedin_profile()
        assert res["error"] is False
        assert res["mock"] is True
        assert "member_id" in res
        assert "name" in res


def test_fetch_profile_live_mocked_http_200():
    """Test fetch_linkedin_profile with mocked 200 HTTP response from LinkedIn."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "sub": "user_abc_789",
        "name": "Jane Developer",
        "given_name": "Jane",
        "family_name": "Developer",
        "email": "jane@example.com",
        "picture": "https://example.com/avatar.jpg",
    }

    with patch("requests.get", return_value=mock_response):
        res = fetch_linkedin_profile(access_token="fake_token_123")
        assert res["error"] is False
        assert res["member_id"] == "user_abc_789"
        assert res["name"] == "Jane Developer"
        assert res["email"] == "jane@example.com"


def test_analyze_linkedin_profile_descriptive():
    """Verify analyze_linkedin_profile returns descriptive recommendations without numeric scores."""
    from mcp_servers.linkedin.tools import analyze_linkedin_profile

    sample_input = {
        "headline": "Junior Developer",
        "about": "Looking for opportunities in software.",
        "skills": ["Python", "JavaScript"],
        "projects": "Built a website and API.",
    }

    with patch.dict(os.environ, {"LINKEDIN_MOCK": "true"}):
        res = analyze_linkedin_profile(profile_data=sample_input)
        assert res["error"] is False
        assert "suggested_headline" in res
        assert "suggested_about" in res
        assert "suggested_skills" in res
        assert "project_recommendations" in res
        assert "overall_improvements" in res
        assert "formatted_report" in res

        report = res["formatted_report"]
        assert "PROFILE ANALYSIS" in report
        assert "Headline" in report
        assert "Suggested:" in report
        assert "About" in report
        assert "Skills" in report
        assert "Projects" in report

        # Verify no numeric scores are included
        for score in ["/10", "/100", "%", "8/10", "90%"]:
            assert score not in report, f"Found numeric score {score} in report!"


def test_analyze_linkedin_profile_llm_mocked():
    """Verify analyze_linkedin_profile parses LLM response correctly when LLM succeeds."""
    from mcp_servers.linkedin.tools import analyze_linkedin_profile

    mock_llm_resp = MagicMock()
    mock_llm_resp.content = json.dumps({
        "current_analysis": "Promising developer profile with modern foundations.",
        "strengths": ["Strong interest in AI and Python"],
        "missing_information": ["Metrics on project throughput"],
        "improvement_suggestions": ["Include architecture diagrams"],
        "suggested_headline": "AI Engineer | LangGraph & Multi-Agent Systems",
        "suggested_about": "Passionate software engineer building agentic AI tools.",
        "suggested_skills": ["Python", "LangGraph", "MCP", "FastAPI"],
        "project_recommendations": ["Feature the GitHub repo improvement agent"],
        "overall_improvements": "Focus on narrative and production outcomes.",
    })

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_llm_resp

    with patch.dict(os.environ, {"LINKEDIN_MOCK": "false"}):
        with patch("backend.agent.get_llm", return_value=mock_llm):
            res = analyze_linkedin_profile(headline="Junior Dev", skills="Python")
            assert res["error"] is False
            assert res["suggested_headline"] == "AI Engineer | LangGraph & Multi-Agent Systems"
            assert "PROFILE ANALYSIS" in res["formatted_report"]



def test_create_linkedin_post_validation():
    """Verify create_linkedin_post rejects empty content."""
    from mcp_servers.linkedin.tools import create_linkedin_post
    res = create_linkedin_post(content="")
    assert res["error"] is True
    assert "cannot be empty" in res["message"]


def test_create_linkedin_post_dry_run():
    """Verify create_linkedin_post in dry_run mode validates payload safely."""
    from mcp_servers.linkedin.tools import create_linkedin_post
    res = create_linkedin_post(
        content="Excited to release my new open-source agent project!",
        dry_run=True,
    )
    assert res["error"] is False
    assert res["dry_run"] is True
    assert "Dry-run mode" in res["message"]
    assert "author" in res


def test_create_linkedin_post_live_mocked():
    """Verify create_linkedin_post with mocked HTTP 201 response."""
    from mcp_servers.linkedin.tools import create_linkedin_post
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.headers = {"x-restli-id": "urn:li:share:987654321"}

    with patch("requests.post", return_value=mock_resp):
        with patch.dict(os.environ, {"LINKEDIN_MOCK": "false", "LINKEDIN_PERSON_URN": "urn:li:person:user_123"}):
            res = create_linkedin_post(
                content="New release announcement.",
                dry_run=False,
                access_token="valid_token_xyz",
            )
            assert res["error"] is False
            assert res["dry_run"] is False
            assert res["post_id"] == "urn:li:share:987654321"


def test_delete_linkedin_post_validation_and_dry_run():
    """Verify delete_linkedin_post input checks and dry run mode."""
    from mcp_servers.linkedin.tools import delete_linkedin_post
    empty_res = delete_linkedin_post(post_id="")
    assert empty_res["error"] is True

    dry_res = delete_linkedin_post(post_id="urn:li:share:123", dry_run=True)
    assert dry_res["error"] is False
    assert dry_res["dry_run"] is True
    assert "validated without mutating" in dry_res["message"]


def test_update_linkedin_profile_validation_and_api_limit():
    """Verify update_linkedin_profile prepares in dry run and clearly reports API limitation on live attempt."""
    from mcp_servers.linkedin.tools import update_linkedin_profile
    empty_res = update_linkedin_profile()
    assert empty_res["error"] is True

    dry_res = update_linkedin_profile(headline="Senior AI Engineer", dry_run=True)
    assert dry_res["error"] is False
    assert dry_res["dry_run"] is True
    assert dry_res["proposed_headline"] == "Senior AI Engineer"

    with patch.dict(os.environ, {"LINKEDIN_MOCK": "false"}):
        live_res = update_linkedin_profile(headline="Senior AI Engineer", dry_run=False)
        assert live_res["error"] is True
        assert live_res["status_code"] == 403
        assert "Official LinkedIn API Limitation" in live_res["message"]


@pytest.mark.asyncio
async def test_linkedin_mcp_server_stdio():
    """Verify spawning mcp_servers.linkedin.server, discovering all 5 tools, and calling them over stdio."""
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = os.environ.copy()
    env["LINKEDIN_MOCK"] = "true"  # Ensure offline predictability

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_servers.linkedin.server"],
        env=env,
        cwd=workspace_root,
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init_res = await session.initialize()
            assert init_res is not None

            # 1. Discover tools - all 5 core tools must be present
            tools_list = await session.list_tools()
            tool_names = [t.name for t in tools_list.tools]
            expected_tools = ["get_profile", "analyze_profile", "create_post", "delete_post", "update_profile"]
            for expected in expected_tools:
                assert expected in tool_names, f"Tool '{expected}' not found in tools/list!"

            # 2. Call get_profile tool
            call_res = await session.call_tool("get_profile", arguments={})
            assert call_res is not None
            assert not getattr(call_res, "is_error", getattr(call_res, "isError", False))

            # 3. Call analyze_profile tool
            analyze_call = await session.call_tool(
                "analyze_profile",
                arguments={
                    "headline": "Student & Aspiring AI Developer",
                    "skills": "Python, FastMCP, LangChain",
                },
            )
            assert analyze_call is not None
            assert not getattr(analyze_call, "is_error", getattr(analyze_call, "isError", False))

            # 4. Call create_post with dry_run=True
            post_call = await session.call_tool(
                "create_post",
                arguments={
                    "content": "Testing MCP create_post over stdio!",
                    "dry_run": True,
                },
            )
            assert post_call is not None
            assert not getattr(post_call, "is_error", getattr(post_call, "isError", False))
            assert "Dry-run mode" in post_call.content[0].text

            # 5. Call update_profile with dry_run=True
            update_call = await session.call_tool(
                "update_profile",
                arguments={
                    "headline": "AI Systems Engineer | LangGraph & MCP",
                    "dry_run": True,
                },
            )
            assert update_call is not None
            assert not getattr(update_call, "is_error", getattr(update_call, "isError", False))
            assert "Dry-run mode" in update_call.content[0].text

            # 6. Call delete_post with dry_run=True
            delete_call = await session.call_tool(
                "delete_post",
                arguments={
                    "post_id": "urn:li:share:12345",
                    "dry_run": True,
                },
            )
            assert delete_call is not None
            assert not getattr(delete_call, "is_error", getattr(delete_call, "isError", False))
            assert "Dry-run mode" in delete_call.content[0].text

