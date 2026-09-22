"""Unit tests for GitHub utility functions."""

import pytest
from mcp_server.github_tools import (
    parse_github_url,
    fetch_repository,
    fetch_repository_tree,
    read_repository_file,
    search_repository_code,
    _is_path_ignored,
    _is_binary_file,
)


def test_parse_github_url_standard():
    owner, repo = parse_github_url("https://github.com/octocat/Hello-World")
    assert owner == "octocat"
    assert repo == "Hello-World"


def test_parse_github_url_with_git_suffix():
    owner, repo = parse_github_url("https://github.com/octocat/Hello-World.git")
    assert owner == "octocat"
    assert repo == "Hello-World"


def test_parse_github_url_trailing_slash():
    owner, repo = parse_github_url("https://github.com/octocat/Hello-World/")
    assert owner == "octocat"
    assert repo == "Hello-World"


def test_parse_github_url_shorthand():
    owner, repo = parse_github_url("octocat/Hello-World")
    assert owner == "octocat"
    assert repo == "Hello-World"


def test_parse_github_url_invalid():
    with pytest.raises(ValueError):
        parse_github_url("not-a-valid-url")


def test_fetch_repository_real_repo():
    result = fetch_repository("octocat/Hello-World")
    assert result.get("error") is False
    assert result.get("name") == "Hello-World"
    assert result.get("owner") == "octocat"
    assert "stars" in result
    assert "default_branch" in result


def test_fetch_repository_nonexistent_repo():
    result = fetch_repository("this-owner-should-not-exist-12345/this-repo-should-not-exist-999")
    assert result.get("error") is True
    assert "not found" in result.get("message", "").lower()


def test_is_path_ignored():
    assert _is_path_ignored(".git/config") is True
    assert _is_path_ignored("node_modules/express/index.js") is True
    assert _is_path_ignored("src/__pycache__/app.cpython-312.pyc") is True
    assert _is_path_ignored(".venv/bin/activate") is True
    assert _is_path_ignored("src/components/Button.tsx") is False


def test_is_binary_file():
    assert _is_binary_file("logo.png") is True
    assert _is_binary_file("app.pyc") is True
    assert _is_binary_file("archive.zip") is True
    assert _is_binary_file("README.md") is False
    assert _is_binary_file("main.py") is False


def test_fetch_repository_tree_real_repo():
    result = fetch_repository_tree("octocat/Hello-World")
    assert result.get("error") is False
    assert result.get("repo") == "octocat/Hello-World"
    assert "files" in result
    assert len(result["files"]) >= 1
    assert "tree_summary" in result
    assert "README" in result["tree_summary"]


def test_read_repository_file_real_repo():
    result = read_repository_file("octocat/Hello-World", "README")
    assert result.get("error") is False
    assert "Hello World!" in result.get("content", "")
    assert result.get("file_path") == "README"


def test_read_repository_file_nonexistent():
    result = read_repository_file("octocat/Hello-World", "nonexistent_file_xyz.py")
    assert result.get("error") is True
    assert "not found" in result.get("message", "").lower()


def test_read_repository_file_binary_rejection():
    result = read_repository_file("octocat/Hello-World", "image.png")
    assert result.get("error") is True
    assert "binary" in result.get("message", "").lower()


def test_search_repository_code_real_repo():
    result = search_repository_code("octocat/Hello-World", "README")
    assert result.get("error") is False
    assert result.get("total_results") >= 1
    paths = [item["path"] for item in result.get("items", [])]
    assert "README" in paths
