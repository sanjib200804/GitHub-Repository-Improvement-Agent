"""GitHub API operations for repository metadata, tree structure, and file reading."""

import os
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

load_dotenv()

# Directories to ignore when filtering repository tree for code & documentation analysis
IGNORED_DIRS: Set[str] = {
    ".git",
    ".github",  # Can be inspected specifically if needed, but omitted from default tree noise
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".eggs",
    "develop-eggs",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    "coverage",
    ".coverage",
}

# Binary and media file extensions that should not be parsed as text
BINARY_EXTENSIONS: Set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".svg",
    ".mp4",
    ".mov",
    ".avi",
    ".mp3",
    ".wav",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".whl",
    ".pyc",
    ".pyo",
    ".pdf",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".bin",
    ".pkl",
    ".pickle",
    ".h5",
    ".onnx",
    ".pb",
}


def parse_github_url(repo_url: str) -> Tuple[str, str]:
    """Parse a GitHub repository URL or shorthand string into (owner, repo)."""
    clean_url = repo_url.strip()
    if clean_url.endswith(".git"):
        clean_url = clean_url[:-4]

    # Handle full URL
    if clean_url.startswith("http://") or clean_url.startswith("https://"):
        parsed = urlparse(clean_url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(path_parts) >= 2:
            return path_parts[0], path_parts[1]
        raise ValueError(
            f"Invalid GitHub URL format: '{repo_url}'. Expected 'https://github.com/owner/repo'"
        )

    # Handle 'owner/repo' shorthand
    parts = [p for p in clean_url.strip("/").split("/") if p]
    if len(parts) == 2:
        return parts[0], parts[1]

    raise ValueError(
        f"Invalid repository identifier: '{repo_url}'. "
        f"Provide a full GitHub URL (e.g., https://github.com/owner/repo) or 'owner/repo'."
    )


def get_github_headers(raw_content: bool = False) -> Dict[str, str]:
    """Build request headers for GitHub REST API, optionally using GITHUB_TOKEN."""
    accept_val = "application/vnd.github.raw+json" if raw_content else "application/vnd.github.v3+json"
    headers = {
        "Accept": accept_val,
        "User-Agent": "github-mcp-agent/1.0",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token and token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"
    return headers


def fetch_repository(repo_url: str) -> Dict[str, Any]:
    """Fetch repository metadata from the GitHub REST API."""
    owner, repo = parse_github_url(repo_url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    try:
        response = requests.get(api_url, headers=get_github_headers(), timeout=15)
    except requests.RequestException as e:
        return {
            "error": True,
            "message": f"Network error contacting GitHub API: {str(e)}",
            "repo_url": repo_url,
        }

    if response.status_code == 200:
        data = response.json()
        return {
            "error": False,
            "name": data.get("name"),
            "full_name": data.get("full_name"),
            "owner": data.get("owner", {}).get("login"),
            "description": data.get("description"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "language": data.get("language"),
            "default_branch": data.get("default_branch", "main"),
            "open_issues_count": data.get("open_issues_count", 0),
            "license": data.get("license", {}).get("name") if data.get("license") else None,
            "html_url": data.get("html_url"),
        }

    if response.status_code == 404:
        return {
            "error": True,
            "message": f"Repository '{owner}/{repo}' not found (404). Check spelling or private status.",
            "repo_url": repo_url,
        }

    if response.status_code == 403:
        rate_limit_reset = response.headers.get("X-RateLimit-Reset", "unknown")
        return {
            "error": True,
            "message": (
                "GitHub API rate limit exceeded or access forbidden (403). "
                f"Rate limit reset epoch: {rate_limit_reset}. "
                "Consider setting GITHUB_TOKEN in .env to increase the rate limit to 5,000 req/hr."
            ),
            "repo_url": repo_url,
        }

    return {
        "error": True,
        "message": f"GitHub API returned error HTTP {response.status_code}: {response.text}",
        "repo_url": repo_url,
    }


def _is_path_ignored(path: str) -> bool:
    """Check if a path contains any ignored directory segments."""
    parts = path.replace("\\", "/").split("/")
    for part in parts:
        if part in IGNORED_DIRS or part.startswith(".git"):
            return True
    return False


def _is_binary_file(path: str) -> bool:
    """Check if a file path ends with a known binary extension."""
    _, ext = os.path.splitext(path.lower())
    return ext in BINARY_EXTENSIONS


def _build_tree_hierarchy(paths: List[str]) -> str:
    """Convert a flat list of file paths into an indented visual tree hierarchy string."""
    tree: Dict[str, Any] = {}
    for p in sorted(paths):
        parts = p.split("/")
        curr = tree
        for part in parts:
            if part not in curr:
                curr[part] = {}
            curr = curr[part]

    lines: List[str] = []

    def render(node: Dict[str, Any], prefix: str = "") -> None:
        entries = sorted(node.keys())
        for idx, name in enumerate(entries):
            is_last = idx == len(entries) - 1
            connector = "\\-- " if is_last else "|-- "
            child_prefix = "    " if is_last else "|   "
            lines.append(f"{prefix}{connector}{name}")
            if node[name]:  # has children (directory)
                render(node[name], prefix + child_prefix)

    render(tree)
    return "\n".join(lines)


def fetch_repository_tree(
    repo_url: str,
    branch: Optional[str] = None,
    filter_ignored: bool = True,
) -> Dict[str, Any]:
    """Fetch recursive file tree for a repository from GitHub Git Trees API."""
    owner, repo = parse_github_url(repo_url)

    # If branch is not specified, resolve default branch via fetch_repository
    resolved_branch = branch
    if not resolved_branch:
        repo_info = fetch_repository(repo_url)
        if repo_info.get("error"):
            return repo_info
        resolved_branch = repo_info.get("default_branch", "main")

    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{resolved_branch}?recursive=1"

    try:
        response = requests.get(api_url, headers=get_github_headers(), timeout=20)
    except requests.RequestException as e:
        return {
            "error": True,
            "message": f"Network error contacting GitHub API: {str(e)}",
            "repo_url": repo_url,
        }

    if response.status_code == 404:
        return {
            "error": True,
            "message": f"Repository tree for '{owner}/{repo}' at branch '{resolved_branch}' not found (404).",
            "repo_url": repo_url,
            "branch": resolved_branch,
        }

    if response.status_code == 403:
        return {
            "error": True,
            "message": "GitHub API rate limit exceeded or access forbidden (403). Set GITHUB_TOKEN in .env.",
            "repo_url": repo_url,
        }

    if response.status_code != 200:
        return {
            "error": True,
            "message": f"GitHub API error HTTP {response.status_code}: {response.text}",
            "repo_url": repo_url,
        }

    data = response.json()
    raw_items = data.get("tree", [])
    is_truncated = data.get("truncated", False)

    file_paths: List[str] = []
    filtered_items: List[Dict[str, Any]] = []

    for item in raw_items:
        path = item.get("path", "")
        item_type = item.get("type")  # 'blob' for file, 'tree' for dir

        if filter_ignored:
            if _is_path_ignored(path):
                continue
            if item_type == "blob" and _is_binary_file(path):
                continue

        if item_type == "blob":
            file_paths.append(path)
            filtered_items.append({
                "path": path,
                "size": item.get("size", 0),
            })

    tree_str = _build_tree_hierarchy(file_paths) if file_paths else "(No matching files)"

    return {
        "error": False,
        "repo": f"{owner}/{repo}",
        "branch": resolved_branch,
        "is_truncated": is_truncated,
        "total_items_in_repo": len(raw_items),
        "filtered_files_count": len(filtered_items),
        "files": filtered_items,
        "tree_summary": tree_str,
    }


def read_repository_file(
    repo_url: str,
    file_path: str,
    branch: Optional[str] = None,
    max_size_kb: int = 250,
) -> Dict[str, Any]:
    """Read file contents from a repository."""
    owner, repo = parse_github_url(repo_url)
    clean_path = file_path.strip().lstrip("/")

    if _is_binary_file(clean_path):
        return {
            "error": True,
            "message": f"File '{clean_path}' is a binary or media file and cannot be read as text.",
            "repo": f"{owner}/{repo}",
            "file_path": clean_path,
        }

    # If branch is not specified, resolve default branch
    resolved_branch = branch
    if not resolved_branch:
        repo_info = fetch_repository(repo_url)
        if repo_info.get("error"):
            return repo_info
        resolved_branch = repo_info.get("default_branch", "main")

    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{clean_path}?ref={resolved_branch}"

    try:
        response = requests.get(api_url, headers=get_github_headers(raw_content=True), timeout=20)
    except requests.RequestException as e:
        return {
            "error": True,
            "message": f"Network error contacting GitHub API: {str(e)}",
            "repo": f"{owner}/{repo}",
            "file_path": clean_path,
        }

    if response.status_code == 404:
        return {
            "error": True,
            "message": f"File '{clean_path}' not found in '{owner}/{repo}' on branch '{resolved_branch}' (404).",
            "repo": f"{owner}/{repo}",
            "file_path": clean_path,
            "branch": resolved_branch,
        }

    if response.status_code == 403:
        return {
            "error": True,
            "message": "GitHub API rate limit exceeded or access forbidden (403). Set GITHUB_TOKEN in .env.",
            "repo": f"{owner}/{repo}",
            "file_path": clean_path,
        }

    if response.status_code != 200:
        return {
            "error": True,
            "message": f"GitHub API error HTTP {response.status_code}: {response.text}",
            "repo": f"{owner}/{repo}",
            "file_path": clean_path,
        }

    raw_text = response.text
    size_bytes = len(raw_text.encode("utf-8"))
    max_bytes = max_size_kb * 1024
    truncated = False

    if size_bytes > max_bytes:
        raw_text = raw_text[:max_bytes] + f"\n\n... [TRUNCATED: File size {size_bytes} bytes exceeds {max_size_kb}KB limit] ..."
        truncated = True

    return {
        "error": False,
        "repo": f"{owner}/{repo}",
        "file_path": clean_path,
        "branch": resolved_branch,
        "size_bytes": size_bytes,
        "truncated": truncated,
        "content": raw_text,
    }


def search_repository_code(repo_url: str, query: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for relevant files and code matching a query within a repository.

    Uses the GitHub Search Code API with fallback to repository tree path matching.
    """
    owner, repo = parse_github_url(repo_url)
    clean_query = query.strip()
    api_url = f"https://api.github.com/search/code?q={clean_query}+repo:{owner}/{repo}&per_page={max_results}"

    try:
        response = requests.get(api_url, headers=get_github_headers(), timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("total_count", 0) > 0:
                items = []
                for item in data.get("items", []):
                    items.append({
                        "path": item.get("path"),
                        "name": item.get("name"),
                        "html_url": item.get("html_url"),
                    })
                return {
                    "error": False,
                    "repo": f"{owner}/{repo}",
                    "query": clean_query,
                    "total_results": len(items),
                    "items": items,
                }
    except requests.RequestException:
        pass

    # Fallback: Search against file tree paths (matches filenames and paths)
    tree_res = fetch_repository_tree(repo_url)
    if tree_res.get("error"):
        return tree_res

    matched_items = []
    q_lower = clean_query.lower()
    for f in tree_res.get("files", []):
        path = f.get("path", "")
        if q_lower in path.lower():
            matched_items.append({
                "path": path,
                "name": os.path.basename(path),
                "html_url": f"https://github.com/{owner}/{repo}/blob/{tree_res.get('branch', 'main')}/{path}",
            })
            if len(matched_items) >= max_results:
                break

    return {
        "error": False,
        "repo": f"{owner}/{repo}",
        "query": clean_query,
        "total_results": len(matched_items),
        "items": matched_items,
    }


def fetch_repository_issues(
    repo_url: str,
    state: str = "open",
    max_issues: int = 10,
) -> Dict[str, Any]:
    """Retrieve existing GitHub issues for a repository."""
    owner, repo = parse_github_url(repo_url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues?state={state}&per_page={max_issues}"

    try:
        response = requests.get(api_url, headers=get_github_headers(), timeout=15)
    except requests.RequestException as e:
        return {
            "error": True,
            "message": f"Network error contacting GitHub API: {str(e)}",
            "repo": f"{owner}/{repo}",
        }

    if response.status_code == 200:
        data = response.json()
        issues = []
        for item in data:
            # Filter out pull requests if any (GitHub Issues API includes PRs)
            if "pull_request" in item:
                continue
            issues.append({
                "number": item.get("number"),
                "title": item.get("title"),
                "state": item.get("state"),
                "user": item.get("user", {}).get("login"),
                "created_at": item.get("created_at"),
                "comments": item.get("comments", 0),
                "labels": [lbl.get("name") for lbl in item.get("labels", [])],
                "html_url": item.get("html_url"),
            })
        return {
            "error": False,
            "repo": f"{owner}/{repo}",
            "state": state,
            "total_issues_fetched": len(issues),
            "issues": issues,
        }

    if response.status_code == 404:
        return {
            "error": True,
            "message": f"Repository '{owner}/{repo}' not found (404).",
            "repo": f"{owner}/{repo}",
        }

    return {
        "error": True,
        "message": f"GitHub API error HTTP {response.status_code}: {response.text}",
        "repo": f"{owner}/{repo}",
    }


def create_repository_issue(
    repo_url: str,
    title: str,
    body: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Create a new issue on a GitHub repository."""
    owner, repo = parse_github_url(repo_url)

    if dry_run:
        return {
            "error": False,
            "dry_run": True,
            "repo": f"{owner}/{repo}",
            "title": title,
            "body": body,
            "message": "Dry-run mode: Issue payload validated successfully without mutating GitHub.",
        }

    token = os.getenv("GITHUB_TOKEN")
    if not token or not token.strip():
        return {
            "error": True,
            "message": "GITHUB_TOKEN is required to create an issue on GitHub. Please configure GITHUB_TOKEN in .env.",
            "repo": f"{owner}/{repo}",
        }

    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    payload = {"title": title, "body": body}

    try:
        response = requests.post(api_url, json=payload, headers=get_github_headers(), timeout=15)
    except requests.RequestException as e:
        return {
            "error": True,
            "message": f"Network error contacting GitHub API: {str(e)}",
            "repo": f"{owner}/{repo}",
        }

    if response.status_code == 201:
        data = response.json()
        return {
            "error": False,
            "dry_run": False,
            "repo": f"{owner}/{repo}",
            "issue_number": data.get("number"),
            "title": data.get("title"),
            "html_url": data.get("html_url"),
            "message": f"Issue #{data.get('number')} created successfully!",
        }

    if response.status_code in (403, 404):
        return {
            "error": True,
            "status_code": response.status_code,
            "message": (
                f"GitHub API error HTTP {response.status_code}: Either repository '{owner}/{repo}' does not exist, "
                "or your GITHUB_TOKEN lacks write/issues permission on this repository."
            ),
            "repo": f"{owner}/{repo}",
        }

    return {
        "error": True,
        "status_code": response.status_code,
        "message": f"GitHub API error HTTP {response.status_code}: {response.text}",
        "repo": f"{owner}/{repo}",
    }
