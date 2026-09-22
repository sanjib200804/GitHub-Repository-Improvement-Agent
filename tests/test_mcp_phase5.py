"""Phase 5 MCP & RAG Verification Test.

Demonstrates and verifies:
1. Selective file filtering (ignoring noise/binaries/lockfiles, prioritizing code and docs).
2. MCP tool discovery for all 4 tools including `search_repository`.
3. Executing `search_repository` over MCP stdio protocol.
4. Indexing repository into Chroma vector database with embeddings.
5. Semantic context retrieval for LLM grounding.
"""

import asyncio
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.mcp_client import mcp_session_scope
from backend.rag import RepositoryRAG, is_important_file


def test_selective_file_filtering():
    """Verify that RAG filter rules ignore build/noise files and keep key code/docs."""
    # Important files to keep
    assert is_important_file("README.md") is True
    assert is_important_file("src/main.py") is True
    assert is_important_file("pyproject.toml") is True
    assert is_important_file("Dockerfile") is True
    assert is_important_file("components/App.tsx") is True

    # Noise/Lockfiles to reject
    assert is_important_file("package-lock.json") is False
    assert is_important_file("poetry.lock") is False
    assert is_important_file("bundle.min.js") is False
    assert is_important_file("styles.min.css") is False
    assert is_important_file("logo.png") is False
    assert is_important_file("app.pyc") is False


async def run_phase5_rag_and_mcp_verification():
    print("=" * 60)
    print("  PHASE 5: REPOSITORY RAG & MCP SEARCH VERIFICATION")
    print("=" * 60)

    # 1. Verify MCP Search Tool
    async with mcp_session_scope() as (session, tools):
        tool_names = [t.name for t in tools]
        print(f"\n[1] Discovered {len(tools)} tools on MCP Server:")
        for name in tool_names:
            print(f"    - {name}")

        assert "search_repository" in tool_names
        search_tool = next(t for t in tools if t.name == "search_repository")

        print("\n[2] Executing 'search_repository' over MCP:")
        res = await search_tool.ainvoke({
            "repo_url": "octocat/Hello-World",
            "query": "README",
        })
        res_text = res[0]["text"] if isinstance(res, list) else str(res)
        search_data = json.loads(res_text)
        print(f"    Search Query:   {search_data.get('query')}")
        print(f"    Total Results:  {search_data.get('total_results')}")
        assert search_data.get("error") is False
        assert search_data.get("total_results") >= 1

    # 2. Verify Selective RAG Indexing & Semantic Retrieval
    print("\n[3] Building Chroma Vector Store for 'octocat/Hello-World'...")
    rag = RepositoryRAG.index_repository(repo_url="octocat/Hello-World", max_files=5)
    print(f"    Repository indexed: {rag.repo_url}")

    print("\n[4] Performing Semantic Search on Chroma:")
    query = "Where is the welcome message or greeting defined?"
    retrieved = rag.retrieve_context(query=query, top_k=2)
    print(f"    Query: '{query}'")
    print(f"    Retrieved Context:\n{retrieved}")

    assert "Hello World!" in retrieved
    assert "README" in retrieved

    print("\n" + "=" * 60)
    print("  ALL PHASE 5 RAG & MCP CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)


@pytest.mark.asyncio
async def test_mcp_phase5():
    await run_phase5_rag_and_mcp_verification()


if __name__ == "__main__":
    test_selective_file_filtering()
    asyncio.run(run_phase5_rag_and_mcp_verification())
