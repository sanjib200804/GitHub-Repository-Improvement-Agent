"""Personal AI Action Agent — Main Interactive Application.

Integrates GitHub and LinkedIn capabilities via Model Context Protocol (MCP):
1. Repository Analysis, Documentation Auditing, and 12-section README generation.
2. Human-in-the-Loop GitHub issue creation.
3. GitHub ➔ LinkedIn announcement post synthesis and publishing.
4. LinkedIn profile auditing following Part 4 specifications.
5. Autonomous Multi-MCP action agent queries.
"""

import argparse
import asyncio
import os
import sys

# Ensure workspace root is in sys.path when executed directly as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.mcp_client import mcp_session_scope, multi_mcp_session_scope
from backend.analyzer import analyze_repository, format_report_as_markdown
from backend.readme_generator import generate_improved_readme
from backend.post_generator import generate_project_post, create_post_from_github_repo
from backend.graph import (
    create_issue_approval_graph,
    create_post_approval_graph,
    run_action_agent,
)
from mcp_servers.linkedin.tools import analyze_linkedin_profile, fetch_linkedin_profile


async def run_github_pipeline(repo_url: str, auto_approve_issue: bool = False, dry_run: bool = True):
    """Execute repository audit, README generation, and issue proposal."""
    print("\n" + "=" * 70)
    print("      GITHUB REPOSITORY IMPROVEMENT AGENT (POWERED BY MCP)       ")
    print("=" * 70)
    print(f"\n[Target Repository]: {repo_url}")

    async with mcp_session_scope() as (session, tools):
        print(f"[MCP Status]: Connected to GitHub MCP Server over stdio.")
        print(f"[Discovered Tools ({len(tools)})]: {', '.join([t.name for t in tools])}\n")

        print("-" * 70)
        print("STEP 1: PERFORMING GROUNDED REPOSITORY AUDIT (MCP + RAG)")
        print("-" * 70)
        report = analyze_repository(repo_url)
        print("\n" + format_report_as_markdown(report))

        print("\n" + "-" * 70)
        print("STEP 2: GENERATING IMPROVED 12-SECTION README")
        print("-" * 70)
        improved_readme = generate_improved_readme(repo_url, analysis_report=report)
        print("\n" + improved_readme[:1000] + "\n... [Remaining sections generated successfully] ...\n")

        out_filename = f"IMPROVED_README_{report.repository_name}.md"
        with open(out_filename, "w", encoding="utf-8") as f:
            f.write(improved_readme)
        print(f"[Saved]: Full improved README written to '{out_filename}'")

        print("\n" + "-" * 70)
        print("STEP 3: PROPOSED GITHUB ISSUE (HUMAN-IN-THE-LOOP)")
        print("-" * 70)

        if not report.improvements:
            print("No improvements flagged for issue creation.")
            return

        top_improvement = report.improvements[0]
        issue_title = f"[{top_improvement.category}] {top_improvement.title}"
        issue_body = (
            f"### Proposed Improvement\n\n"
            f"**Recommendation:**\n{top_improvement.recommendation}\n\n"
            f"**Why This Is Useful:**\n{top_improvement.why_useful}\n\n"
            f"**Observed Evidence:**\n`{top_improvement.evidence}`\n\n"
            f"---\n*Generated autonomously by GitHub Repository Improvement Agent (MCP)*"
        )

        print(f"Proposed Title: {issue_title}")
        print(f"Proposed Body:\n{issue_body}\n")

        approved = auto_approve_issue
        if not auto_approve_issue:
            prompt_input = input(">> Submit this issue to GitHub? (y/N): ").strip().lower()
            approved = prompt_input in ("y", "yes")

        app = create_issue_approval_graph(tools=tools)
        result = await app.ainvoke({
            "repo_url": repo_url,
            "issue_title": issue_title,
            "issue_body": issue_body,
            "user_approved": approved,
            "dry_run": dry_run,
            "status": "pending",
            "output": None,
        })
        print(f"\n[HITL Result]: Status = {result['status']}")
        if result.get("output"):
            print(f"Message: {result['output'].get('message')}")
            if result["output"].get("html_url"):
                print(f"Issue URL: {result['output'].get('html_url')}")


async def run_linkedin_post_pipeline(repo_url: str, auto_approve: bool = False, live: bool = False):
    """Synthesize an authentic developer LinkedIn post and publish with confirmation."""
    print("\n" + "=" * 70)
    print("      GITHUB ➔ LINKEDIN POST WORKFLOW (HUMAN-IN-THE-LOOP)        ")
    print("=" * 70)

    print(f"\nAnalyzing repository '{repo_url}' and drafting announcement post...")
    draft = generate_project_post(repo_url)
    print("\n" + "-" * 70)
    print("DRAFT LINKEDIN POST:")
    print("-" * 70)
    print(draft["post_content"])
    print("-" * 70)

    approved = auto_approve
    if not auto_approve:
        prompt_input = input("\n>> Publish this post to LinkedIn? (y/N): ").strip().lower()
        approved = prompt_input in ("y", "yes")

    dry_run = not live
    result = create_post_from_github_repo(
        repo_url=repo_url,
        publish=approved,
        dry_run=dry_run,
    )
    print(f"\n[Publication Status]: {result['status']}")
    print(f"Message: {result['message']}")
    if result.get("publication_result"):
        print(f"Details: {result['publication_result']}")


def run_linkedin_profile_audit(headline: str = "", about: str = "", skills: str = ""):
    """Analyze LinkedIn profile presentation following Part 4 guidelines."""
    print("\n" + "=" * 70)
    print("           LINKEDIN PROFILE AUDIT & RECOMMENDATIONS               ")
    print("=" * 70)

    if not headline and not about and not skills:
        prof = fetch_linkedin_profile()
        if not prof.get("error"):
            print(f"Connected to authenticated profile: {prof.get('name')}")
            headline = f"Software Engineer | {prof.get('name')}"

    analysis = analyze_linkedin_profile(
        headline=headline or "Software Engineer | Full-Stack & AI Systems",
        about=about or "Building autonomous agents with LangGraph and MCP.",
        skills=skills or "Python, LangGraph, MCP, FastAPI",
    )
    print("\n" + analysis.get("formatted_report", ""))


async def run_agent_chat(prompt: str):
    """Send an instruction to the Multi-MCP autonomous action agent."""
    print("\n" + "=" * 70)
    print("               MULTI-MCP PERSONAL ACTION AGENT                   ")
    print("=" * 70)
    print(f"User Query: {prompt}\n")
    res = await run_action_agent(prompt)
    print(f"Agent Answer:\n{res['final_answer']}")
    print(f"\n[Tools Activated]: {res.get('tools_count', 0)} MCP tools across GitHub & LinkedIn")


def main():
    parser = argparse.ArgumentParser(description="Personal AI Action Agent (GitHub + LinkedIn Multi-MCP)")
    parser.add_argument("repo", nargs="?", default="octocat/Hello-World", help="GitHub repository URL or slug")
    parser.add_argument("--post", action="store_true", help="Run GitHub-to-LinkedIn post generation workflow")
    parser.add_argument("--profile", action="store_true", help="Run LinkedIn profile audit workflow")
    parser.add_argument("--agent", type=str, help="Run autonomous Multi-MCP agent with a custom prompt")
    parser.add_argument("--live", action="store_true", help="Execute live mutation (default is safe dry-run)")
    parser.add_argument("-y", "--yes", action="store_true", help="Explicitly confirm and auto-approve write actions without interactive prompt")

    args = parser.parse_args()

    if args.agent:
        asyncio.run(run_agent_chat(args.agent))
    elif args.profile:
        run_linkedin_profile_audit()
    elif args.post:
        asyncio.run(run_linkedin_post_pipeline(args.repo, auto_approve=args.yes, live=args.live))
    else:
        asyncio.run(run_github_pipeline(args.repo, auto_approve_issue=args.yes, dry_run=not args.live))


if __name__ == "__main__":
    main()
