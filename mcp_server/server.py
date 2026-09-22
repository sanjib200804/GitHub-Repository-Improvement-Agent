"""GitHub MCP Server.

Exposes GitHub repository tools via the Model Context Protocol (MCP).
Can be run over stdio (standard input/output) for integration with MCP clients,
or imported directly.
"""

from typing import Any, Dict, Optional
from mcp_server.github_tools import (
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
    """Retrieve metadata and statistics for a GitHub repository.

    Args:
        repo_url: Full GitHub repository URL (e.g., 'https://github.com/owner/repo')
                  or shorthand ('owner/repo').

    Returns:
        A dictionary containing repository details:
        - name: Repository name
        - full_name: owner/repo
        - description: Repository description
        - owner: Owner username
        - stars: Number of stargazers
        - forks: Number of forks
        - language: Primary programming language
        - default_branch: Default git branch (main/master)
        - open_issues_count: Total open issues and PRs
        - license: Name of open source license, if any
        - html_url: Web URL to the repository
    """
    return fetch_repository(repo_url)


@mcp.tool()
def get_repository_tree(repo_url: str, branch: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve the recursive file and directory tree of a GitHub repository.

    Filters out dependency directories (node_modules, .venv), caches (__pycache__),
    build directories (dist, build), and binary media files to focus on source code
    and documentation.

    Args:
        repo_url: Full GitHub repository URL or 'owner/repo'.
        branch: Optional git branch/ref (defaults to the repository's default branch).

    Returns:
        A dictionary containing:
        - repo: owner/repo
        - branch: Branch evaluated
        - total_items_in_repo: Total items found in git tree
        - filtered_files_count: Count of code and documentation files
        - files: List of file objects with 'path' and 'size'
        - tree_summary: Formatted visual directory tree string
    """
    return fetch_repository_tree(repo_url=repo_url, branch=branch)


@mcp.tool()
def read_file(repo_url: str, file_path: str, branch: Optional[str] = None) -> Dict[str, Any]:
    """Read the content of a specific text file from a GitHub repository.

    Args:
        repo_url: Full GitHub repository URL or 'owner/repo'.
        file_path: Relative path to the file within the repository (e.g., 'README.md' or 'src/app.py').
        branch: Optional git branch/ref (defaults to the repository's default branch).

    Returns:
        A dictionary containing:
        - repo: owner/repo
        - file_path: File path requested
        - branch: Branch from which file was read
        - size_bytes: File size in bytes
        - truncated: Boolean flag indicating if file was truncated due to size limits
        - content: Textual content of the file
    """
    return read_repository_file(repo_url=repo_url, file_path=file_path, branch=branch)


@mcp.tool()
def search_repository(repo_url: str, query: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for relevant files and code within a GitHub repository.

    Args:
        repo_url: Full GitHub repository URL or 'owner/repo'.
        query: Keyword or symbol to search for (e.g., 'main', 'test', 'docker', 'FastAPI').
        max_results: Maximum number of search results to return (default: 10).

    Returns:
        A dictionary containing:
        - repo: owner/repo
        - query: Search query executed
        - total_results: Number of matching files found
        - items: List of matching items with 'path', 'name', and 'html_url'
    """
    return search_repository_code(repo_url=repo_url, query=query, max_results=max_results)


@mcp.tool()
def get_issues(repo_url: str, state: str = "open", max_issues: int = 10) -> Dict[str, Any]:
    """Retrieve existing GitHub issues for a repository.

    Args:
        repo_url: Full GitHub repository URL or 'owner/repo'.
        state: Issue state filter ('open', 'closed', 'all'). Default is 'open'.
        max_issues: Maximum number of issues to return (default: 10).

    Returns:
        A dictionary containing:
        - repo: owner/repo
        - state: Issue state queried
        - total_issues_fetched: Count of retrieved issues
        - issues: List of issue objects with number, title, state, user, labels, url
    """
    return fetch_repository_issues(repo_url=repo_url, state=state, max_issues=max_issues)


@mcp.tool()
def create_issue(
    repo_url: str,
    title: str,
    body: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Create a new issue on a GitHub repository.

    NOTE: This is an action tool that modifies GitHub. It requires explicit user
    confirmation before invocation.

    Args:
        repo_url: Full GitHub repository URL or 'owner/repo'.
        title: Title of the issue.
        body: Markdown body description of the problem or proposed improvement.
        dry_run: If True, validates payload without modifying GitHub (default: False).

    Returns:
        A dictionary containing:
        - error: Boolean error flag
        - repo: owner/repo
        - issue_number: Number of the created issue (if successful)
        - title: Issue title
        - html_url: Web URL to the newly created issue
        - message: Confirmation message
    """
    return create_repository_issue(repo_url=repo_url, title=title, body=body, dry_run=dry_run)


def main():
    """Entry point for running the MCP server over stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
