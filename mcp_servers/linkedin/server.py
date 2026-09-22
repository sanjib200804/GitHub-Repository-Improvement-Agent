"""LinkedIn MCP Server.

Exposes official LinkedIn profile and action tools via Model Context Protocol (MCP).
Runs over stdio transport.
"""

from typing import Any, Dict, Optional
from mcp_servers.linkedin.tools import (
    fetch_linkedin_profile,
    analyze_linkedin_profile,
    create_linkedin_post,
    delete_linkedin_post,
    update_linkedin_profile,
)

try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("linkedin-action-agent")
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer(name="linkedin-action-agent")


@mcp.tool()
def get_profile(raw: bool = False) -> Dict[str, Any]:
    """Retrieve the authenticated user's LinkedIn profile information via official API.

    Calls the official LinkedIn OpenID Connect userinfo endpoint (GET /v2/userinfo).
    Returns verified profile identity fields (member_id, name, given_name, email, picture).

    Args:
        raw: If True, includes raw API response dictionary. Defaults to False.

    Returns:
        A dictionary containing:
        - error: Boolean error status
        - member_id: Unique member identifier (sub)
        - name: Full display name
        - email: Primary email address (if scope granted)
        - picture: Profile picture URL (if available)
    """
    return fetch_linkedin_profile(raw=raw)


@mcp.tool()
def analyze_profile(
    headline: Optional[str] = None,
    about: Optional[str] = None,
    skills: Optional[str] = None,
    experience: Optional[str] = None,
    education: Optional[str] = None,
    projects: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze a LinkedIn profile and provide professional improvement recommendations.

    Evaluates headline, about section, skills, experience, and projects.
    Returns descriptive feedback without scores, along with improved suggestions.

    Args:
        headline: Current LinkedIn headline.
        about: Current About / summary section.
        skills: Comma-separated skills or list of skills.
        experience: Brief overview of work experience.
        education: Educational background details.
        projects: Notable project names or descriptions.

    Returns:
        A dictionary containing:
        - strengths: List of profile strengths
        - missing_information: List of missing elements
        - improvement_suggestions: Actionable recommendations
        - suggested_headline: High-impact suggested headline
        - suggested_about: Suggested narrative About section
        - suggested_skills: Targeted modern tech skills
        - project_recommendations: Recommendations for highlighting projects
        - overall_improvements: Strategic improvement summary
        - formatted_report: Formatted markdown report
    """
    return analyze_linkedin_profile(
        headline=headline,
        about=about,
        skills=skills,
        experience=experience,
        education=education,
        projects=projects,
    )


@mcp.tool()
def create_post(
    content: str,
    image_url: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Create and publish a LinkedIn post via official REST API.

    NOTE: This is an action tool modifying external social media.
    Requires explicit user confirmation before execution.

    Args:
        content: Text content and commentary of the post.
        image_url: Optional image URL or media asset to attach.
        dry_run: If True, validates payload without publishing (default: False).

    Returns:
        A dictionary containing:
        - error: Boolean error status
        - dry_run: Whether execution was a dry run
        - post_id: Published post identifier (if successful)
        - message: Confirmation message
    """
    return create_linkedin_post(content=content, image_url=image_url, dry_run=dry_run)


@mcp.tool()
def delete_post(
    post_id: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Delete a post on LinkedIn using the official REST API.

    NOTE: This is a destructive action tool.
    Requires explicit user confirmation before execution.

    Args:
        post_id: Identifier or URN of the post to delete.
        dry_run: If True, validates post identifier without deleting (default: False).

    Returns:
        A dictionary containing:
        - error: Boolean error status
        - dry_run: Whether execution was a dry run
        - post_id: Post identifier
        - message: Deletion confirmation or limitation details
    """
    return delete_linkedin_post(post_id=post_id, dry_run=dry_run)


@mcp.tool()
def update_profile(
    headline: Optional[str] = None,
    about: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Prepare and validate profile updates, adhering strictly to official API capabilities.

    NOTE: This modifies personal profile data.
    Requires explicit user confirmation before execution.

    Args:
        headline: Proposed new headline.
        about: Proposed new About summary section.
        dry_run: If True, prepares and validates updates without sending external mutations (default: False).

    Returns:
        A dictionary containing:
        - error: Boolean error status
        - dry_run: Whether execution was a dry run
        - proposed_headline: Proposed headline
        - proposed_about: Proposed About section
        - message: Update status or official API limitation explanation
    """
    return update_linkedin_profile(headline=headline, about=about, dry_run=dry_run)


def main():
    """Entry point for running the LinkedIn MCP server over stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
