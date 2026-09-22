"""Phase 6 Test: Repository Analysis Engine Verification.

Demonstrates and verifies:
1. Discovery and execution of `get_issues` tool over MCP.
2. Multi-tier evidence collection (MCP metadata, tree, README, issues, and RAG).
3. Structured repository analysis into Documentation and Codebase audits.
4. Actionable improvement recommendations with 'why_useful' rationales.
5. Markdown report formatting.
"""

import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.mcp_client import mcp_session_scope
from backend.analyzer import (
    collect_repository_evidence,
    analyze_repository,
    format_report_as_markdown,
    RepositoryAnalysisReport,
)


def test_mcp_get_issues_tool():
    """Verify that get_issues tool executes properly over MCP."""
    async def _run():
        async with mcp_session_scope() as (session, tools):
            tool_names = [t.name for t in tools]
            assert "get_issues" in tool_names, "Expected 'get_issues' in MCP tools"

            issues_tool = next(t for t in tools if t.name == "get_issues")
            res = await issues_tool.ainvoke({
                "repo_url": "octocat/Hello-World",
                "state": "open",
                "max_issues": 3,
            })
            assert res is not None
    asyncio.run(_run())


def test_collect_evidence():
    """Verify raw evidence collection across MCP and RAG layers."""
    evidence = collect_repository_evidence("octocat/Hello-World")
    assert "metadata" in evidence
    assert "tree_summary" in evidence
    assert "readme_content" in evidence
    assert evidence["metadata"].get("name") == "Hello-World"


def test_analyze_repository_real():
    """Run full AI analysis on repository and assert grounded findings."""
    print("=" * 60)
    print("  PHASE 6: REPOSITORY ANALYSIS ENGINE VERIFICATION")
    print("=" * 60)

    report = analyze_repository("octocat/Hello-World")
    assert isinstance(report, RepositoryAnalysisReport)
    assert report.repository_name == "Hello-World"
    assert 1 <= report.overall_health_score <= 100
    assert len(report.improvements) >= 1

    # Verify that each improvement has concrete recommendation, why_useful, and evidence
    for imp in report.improvements:
        assert len(imp.recommendation) > 0
        assert len(imp.why_useful) > 0
        assert len(imp.evidence) > 0
        print(f"\n[Improvement] [{imp.category}] {imp.title}")
        print(f"  Recommendation: {imp.recommendation}")
        print(f"  Why Useful:     {imp.why_useful}")
        print(f"  Evidence:       {imp.evidence}")

    # Verify Markdown formatting
    md = format_report_as_markdown(report)
    assert "# Repository Improvement Audit:" in md
    assert "## 1. Documentation Audit" in md
    assert "## 2. Codebase & Structure Audit" in md
    assert "## 3. Practical Improvements & Rationales" in md

    print("\n" + "=" * 60)
    print("  ALL PHASE 6 ANALYSIS CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_mcp_get_issues_tool())
    test_collect_evidence()
    test_analyze_repository_real()
