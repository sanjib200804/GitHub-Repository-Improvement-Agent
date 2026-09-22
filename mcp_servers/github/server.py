"""GitHub MCP Server.

Exposes GitHub repository inspection and management tools via Model Context Protocol (MCP).
Runs over stdio transport.
"""

from typing import Any, Dict, Optional
from mcp_servers.github.tools import (
    fetch_repository,
    fetch_repository_tree,
    read_repository_file,
    search_repository_code,
    fetch_repository_issues,
    create_repository_issue,
)

try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("github-repository-agent")
except (ImportError, ModuleNotFoundError):
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer(name="github-repository-agent")


@mcp.tool()
def get_repository(repo_url: str) -> Dict[str, Any]:
    """Retrieve metadata and statistics for a GitHub repository."""
    return fetch_repository(repo_url)


@mcp.tool()
def get_repository_tree(
    repo_url: str,
    branch: Optional[str] = None,
    filter_ignored: bool = True,
) -> Dict[str, Any]:
    """Retrieve filtered file tree hierarchy of a GitHub repository."""
    return fetch_repository_tree(repo_url=repo_url, branch=branch, filter_ignored=filter_ignored)


@mcp.tool()
def read_file(
    repo_url: str,
    file_path: str,
    branch: Optional[str] = None,
) -> Dict[str, Any]:
    """Read full text content of a file from a GitHub repository."""
    return read_repository_file(repo_url=repo_url, file_path=file_path, branch=branch)


@mcp.tool()
def search_repository(
    repo_url: str,
    query: str,
    max_results: int = 5,
) -> Dict[str, Any]:
    """Search repository code and documentation for relevant snippets."""
    return search_repository_code(repo_url=repo_url, query=query, max_results=max_results)


@mcp.tool()
def get_issues(
    repo_url: str,
    state: str = "open",
    max_issues: int = 10,
) -> Dict[str, Any]:
    """Fetch recent issues from a GitHub repository."""
    return fetch_repository_issues(repo_url=repo_url, state=state, max_issues=max_issues)


@mcp.tool()
def create_issue(
    repo_url: str,
    title: str,
    body: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Create a new issue on a GitHub repository (requires user approval)."""
    return create_repository_issue(repo_url=repo_url, title=title, body=body, dry_run=dry_run)


def main():
    """Entry point for running the GitHub MCP server over stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
