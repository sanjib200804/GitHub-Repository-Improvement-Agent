"""GitHub Repository Improvement Agent — Streamlit Web Application.

A sleek, modern web interface that connects to the GitHub MCP Server:
- Inspects repository structure & metadata
- Performs grounded Documentation & Codebase audits
- Generates a production-grade 12-section README.md
- Interactively proposes GitHub issues with explicit Human-in-the-Loop (HITL) approval
- Provides an interactive AI agent chat tab powered by LangGraph & MCP tools
"""

import asyncio
import os
import sys
import streamlit as st

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.mcp_client import mcp_session_scope, multi_mcp_session_scope
from backend.analyzer import (
    collect_repository_evidence,
    analyze_repository,
    format_report_as_markdown,
)
from backend.readme_generator import generate_improved_readme
from backend.graph import (
    run_repository_agent,
    run_action_agent,
    create_issue_approval_graph,
    create_post_approval_graph,
)
from backend.post_generator import generate_project_post
from mcp_servers.github.tools import fetch_repository, fetch_repository_tree
from mcp_servers.linkedin.tools import analyze_linkedin_profile, fetch_linkedin_profile
from mcp_servers.linkedin.oauth import get_authorization_url

# -----------------------------------------------------------------------------
# Streamlit Page Config & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Personal AI Action Agent",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6c757d;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #e9ecef;
    }
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Helper: Run Async functions inside Streamlit
# -----------------------------------------------------------------------------
def run_async(coro):
    return asyncio.run(coro)

# -----------------------------------------------------------------------------
# Sidebar: Configuration & MCP Info
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🤖 Personal AI Action Agent")
    st.caption("Multi-MCP Architecture (GitHub + LinkedIn) powered by LangGraph")

    st.markdown("---")
    st.subheader("Connected MCP Servers")
    st.success("🟢 GitHub MCP: `mcp_servers.github.server`")
    st.success("🟢 LinkedIn MCP: `mcp_servers.linkedin.server`")

    with st.expander("🛠️ Active MCP Tools (11 total)"):
        st.markdown("""
        **GitHub Tools:**
        - `get_repository`
        - `get_repository_tree`
        - `read_file`
        - `search_repository`
        - `get_issues`
        - `create_issue` *(HITL)*

        **LinkedIn Tools:**
        - `get_profile`
        - `analyze_profile`
        - `create_post` *(HITL)*
        - `delete_post` *(HITL)*
        - `update_profile` *(HITL)*
        """)

    st.markdown("---")
    st.subheader("Authentication Status")
    has_github = bool(os.getenv("GITHUB_TOKEN"))
    if has_github:
        st.info("🔑 GITHUB_TOKEN: Configured (5,000 req/hr)")
    else:
        st.warning("⚠️ GITHUB_TOKEN: Unauthenticated (60 req/hr)")

    has_linkedin = bool(os.getenv("LINKEDIN_ACCESS_TOKEN"))
    is_mock = os.getenv("LINKEDIN_MOCK", "").lower() in ("true", "1", "yes")
    if has_linkedin:
        st.info("💼 LINKEDIN_ACCESS_TOKEN: Configured")
    elif is_mock:
        st.info("🧪 LINKEDIN_MOCK: Enabled (Offline Testing)")
    else:
        st.caption("💡 Tip: Set LINKEDIN_MOCK=true in .env for instant offline testing.")

    with st.expander("🔗 Generate LinkedIn OAuth URL"):
        if st.button("Generate Authorization Link", use_container_width=True):
            oauth_res = get_authorization_url()
            if oauth_res.get("error"):
                st.error(oauth_res.get("message"))
            else:
                st.markdown(f"**[Click here to authorize LinkedIn]({oauth_res.get('authorization_url')})**")


# -----------------------------------------------------------------------------
# Main Header
# -----------------------------------------------------------------------------
st.markdown('<div class="main-header">🚀 GitHub Repository Improvement Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Analyze any repository, audit code & documentation, generate READMEs, and propose issues via Model Context Protocol.</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------
if "repo_input_value" not in st.session_state:
    st.session_state["repo_input_value"] = "octocat/Hello-World"
if "analysis_data" not in st.session_state:
    st.session_state["analysis_data"] = None
if "generated_readme" not in st.session_state:
    st.session_state["generated_readme"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

def select_preset(preset_url: str):
    st.session_state["repo_input_value"] = preset_url

# -----------------------------------------------------------------------------
# Target Repository Input
# -----------------------------------------------------------------------------
col_input, col_btn = st.columns([4, 1])

with col_input:
    repo_url = st.text_input(
        "Enter GitHub Repository URL or 'owner/repo'",
        key="repo_input_value",
        placeholder="e.g. https://github.com/octocat/Hello-World or pallets/flask",
    )

with col_btn:
    st.write("")
    st.write("")
    analyze_btn = st.button("🔍 Analyze Repository", type="primary", use_container_width=True)

# Quick Preset Buttons
st.caption("Quick examples:")
p1, p2, p3, _ = st.columns([1.2, 1.2, 1.2, 4])
with p1:
    st.button("octocat/Hello-World", on_click=select_preset, args=("octocat/Hello-World",), use_container_width=True)
with p2:
    st.button("pallets/flask", on_click=select_preset, args=("pallets/flask",), use_container_width=True)
with p3:
    st.button("tiangolo/fastapi", on_click=select_preset, args=("tiangolo/fastapi",), use_container_width=True)

# -----------------------------------------------------------------------------
# Execute Analysis on Click
# -----------------------------------------------------------------------------
if analyze_btn and repo_url:
    with st.spinner("Connecting to MCP server and auditing repository..."):
        try:
            # 1. Fetch metadata & tree
            meta = fetch_repository(repo_url)
            if meta.get("error"):
                st.error(f"Error: {meta.get('message')}")
            else:
                tree = fetch_repository_tree(repo_url)
                # 2. Run analysis
                report = analyze_repository(repo_url)
                # 3. Generate README
                readme = generate_improved_readme(repo_url, analysis_report=report)

                st.session_state["analysis_data"] = {
                    "meta": meta,
                    "tree": tree,
                    "report": report,
                }
                st.session_state["generated_readme"] = readme
                st.success("Analysis and README generation complete!")
        except Exception as e:
            st.error(f"Execution Error: {str(e)}")

# -----------------------------------------------------------------------------
# Results Presentation
# -----------------------------------------------------------------------------
if st.session_state["analysis_data"]:
    data = st.session_state["analysis_data"]
    meta = data["meta"]
    tree = data["tree"]
    report = data["report"]
    readme = st.session_state["generated_readme"]

    # Metrics Row
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Health Score", f"{report.overall_health_score}/100")
    with m2:
        st.metric("Stars", f"{meta.get('stars', 0):,}")
    with m3:
        st.metric("Forks", f"{meta.get('forks', 0):,}")
    with m4:
        st.metric("Files Indexed", tree.get("filtered_files_count", 0))
    with m5:
        st.metric("Language", meta.get("language") or "N/A")

    # Tabs for Detailed Breakdown
    tab_audit, tab_readme, tab_tree, tab_hitl, tab_linkedin_post, tab_linkedin_profile, tab_chat = st.tabs([
        "📊 Audit & Improvements",
        "📝 Generated README",
        "📂 Repository Tree",
        "🛡️ Propose Issue (HITL)",
        "📢 Post to LinkedIn (HITL)",
        "💼 LinkedIn Profile Auditor",
        "💬 Ask Multi-MCP Agent",
    ])

    # Tab 1: Audit & Improvements
    with tab_audit:
        st.subheader("Executive Summary")
        st.write(report.executive_summary)

        st.markdown("---")
        col_doc, col_code = st.columns(2)

        with col_doc:
            st.markdown("### 📖 Documentation Audit")
            st.write(f"**README Found:** {'✅ Yes' if report.documentation_audit.readme_found else '❌ No'}")
            st.write(f"**README Quality Score:** {report.documentation_audit.readme_quality_score}/10")
            st.write(f"**Installation Status:** {report.documentation_audit.installation_instructions_status}")
            st.write(f"**Usage Status:** {report.documentation_audit.usage_instructions_status}")
            if report.documentation_audit.missing_documentation_elements:
                st.markdown("**Missing Elements:**")
                for elem in report.documentation_audit.missing_documentation_elements:
                    st.write(f"- {elem}")

        with col_code:
            st.markdown("### 💻 Codebase & Structure Audit")
            st.write(f"**Project Structure:** {report.codebase_audit.project_structure_assessment}")
            st.write(f"**Tests Detected:** {'✅ Yes' if report.codebase_audit.tests_detected else '❌ No'}")
            st.write(f"**Test Framework:** {report.codebase_audit.test_framework_status}")
            if report.codebase_audit.missing_configurations:
                st.markdown("**Missing Configurations:**")
                for cfg in report.codebase_audit.missing_configurations:
                    st.write(f"- {cfg}")

        st.markdown("---")
        st.subheader("💡 Practical Improvement Suggestions")
        for idx, imp in enumerate(report.improvements, 1):
            with st.expander(f"#{idx} [{imp.category}] {imp.title}", expanded=(idx == 1)):
                st.markdown(f"**Recommendation:**\n{imp.recommendation}")
                st.info(f"**Why Useful:** {imp.why_useful}")
                st.caption(f"Evidence: `{imp.evidence}`")

    # Tab 2: Generated README
    with tab_readme:
        st.subheader("Generated Production-Grade README")
        st.caption("Structured into 12 sections based on actual repository context and audit findings.")

        st.download_button(
            label="📥 Download README.md",
            data=readme,
            file_name=f"README_{meta.get('name', 'project')}.md",
            mime="text/markdown",
        )

        with st.expander("👁️ Preview Rendered Markdown", expanded=True):
            st.markdown(readme)

        with st.expander("📄 View Raw Markdown Source"):
            st.code(readme, language="markdown")

    # Tab 3: Repository Tree
    with tab_tree:
        st.subheader("Repository Structure")
        st.caption(f"Total files: {tree.get('total_items_in_repo', 0)} (Filtered for code & docs: {tree.get('filtered_files_count', 0)})")
        st.code(tree.get("tree_summary", "(Empty)"), language="text")

    # Tab 4: Human-in-the-Loop Issue Proposal
    with tab_hitl:
        st.subheader("🛡️ Propose GitHub Issue (Human-in-the-Loop)")
        st.markdown("""
        The agent proposes a high-priority improvement issue based on the audit.
        **No issue is created on GitHub without your explicit approval.**
        """)

        if report.improvements:
            top_imp = report.improvements[0]
            default_title = f"[{top_imp.category}] {top_imp.title}"
            default_body = (
                f"### Proposed Improvement\n\n"
                f"**Recommendation:**\n{top_imp.recommendation}\n\n"
                f"**Why This Is Useful:**\n{top_imp.why_useful}\n\n"
                f"**Observed Evidence:**\n`{top_imp.evidence}`\n\n"
                f"---\n*Generated by GitHub Repository Improvement Agent (MCP)*"
            )

            issue_title_input = st.text_input("Issue Title", value=default_title)
            issue_body_input = st.text_area("Issue Body", value=default_body, height=180)

            live_publish_issue = st.checkbox(
                "🚀 Publish as real issue to GitHub repository (requires write permissions on GITHUB_TOKEN)",
                value=False,
                help="If unchecked, runs in safe Dry-Run mode to validate without writing to GitHub.",
            )

            c_approve, c_reject, _ = st.columns([2, 1.5, 2.5])

            with c_approve:
                btn_label = "🚀 Approve & Publish to GitHub" if live_publish_issue else "✅ Approve (Dry Run)"
                if st.button(btn_label, type="primary", use_container_width=True):
                    with st.spinner("Invoking MCP create_issue tool..."):
                        async def submit_approved():
                            async with mcp_session_scope() as (sess, tools):
                                app = create_issue_approval_graph(tools)
                                return await app.ainvoke({
                                    "repo_url": repo_url,
                                    "issue_title": issue_title_input,
                                    "issue_body": issue_body_input,
                                    "user_approved": True,
                                    "dry_run": not live_publish_issue,
                                    "status": "pending",
                                    "output": None,
                                })
                        res = run_async(submit_approved())
                        out = res.get("output", {})
                        if out.get("error"):
                            st.error(f"Error: {out.get('message')}")
                        else:
                            st.success(f"Status: {res['status']} — {out.get('message')}")
                            if out.get("html_url"):
                                st.markdown(f"🔗 **[View Created GitHub Issue #{out.get('issue_number')}]({out.get('html_url')})**")
                        st.json(out)

            with c_reject:
                if st.button("❌ Reject / Cancel Issue", use_container_width=True):
                    async def submit_rejected():
                        async with mcp_session_scope() as (sess, tools):
                            app = create_issue_approval_graph(tools)
                            return await app.ainvoke({
                                "repo_url": repo_url,
                                "issue_title": issue_title_input,
                                "issue_body": issue_body_input,
                                "user_approved": False,
                                "dry_run": True,
                                "status": "pending",
                                "output": None,
                            })
                    res = run_async(submit_rejected())
                    st.warning(f"Status: {res['status']}")
                    st.write(res["output"].get("message"))
        else:
            st.info("No issues currently flagged for this repository.")

    # Tab 5: Post Project to LinkedIn (HITL)
    with tab_linkedin_post:
        st.subheader("📢 Announce Project on LinkedIn (Human-in-the-Loop)")
        st.caption("Synthesizes repository evidence into an authentic developer announcement post.")

        if "linkedin_draft" not in st.session_state or st.session_state.get("draft_repo") != repo_url:
            with st.spinner("Analyzing project and drafting LinkedIn post..."):
                draft_data = generate_project_post(repo_url)
                st.session_state["linkedin_draft"] = draft_data
                st.session_state["draft_repo"] = repo_url

        draft_data = st.session_state["linkedin_draft"]

        post_content_input = st.text_area(
            "Review & Edit Post Commentary",
            value=draft_data.get("post_content", ""),
            height=260,
        )

        if draft_data.get("image_url"):
            st.caption(f"Attached Banner: `{draft_data.get('image_url')}`")

        live_publish_post = st.checkbox(
            "🚀 Publish live post to LinkedIn (requires LINKEDIN_ACCESS_TOKEN with w_member_social)",
            value=False,
            help="If unchecked, safely validates the post payload in Dry-Run mode without publishing.",
        )

        col_post_ok, col_post_cancel, _ = st.columns([2, 1.5, 2.5])

        with col_post_ok:
            post_btn_label = "🚀 Approve & Publish to LinkedIn" if live_publish_post else "✅ Approve Post (Dry Run)"
            if st.button(post_btn_label, type="primary", use_container_width=True):
                with st.spinner("Invoking LinkedIn MCP create_post tool..."):
                    async def submit_post_approved():
                        from backend.mcp_client import get_server_parameters
                        from mcp.client.stdio import stdio_client
                        from mcp.client.session import ClientSession
                        from langchain_mcp_adapters.tools import load_mcp_tools

                        params = get_server_parameters("linkedin")
                        async with stdio_client(params) as (read_stream, write_stream):
                            async with ClientSession(read_stream, write_stream) as session:
                                await session.initialize()
                                tools = await load_mcp_tools(session)
                                app = create_post_approval_graph(tools)
                                return await app.ainvoke({
                                    "content": post_content_input,
                                    "image_url": draft_data.get("image_url"),
                                    "user_approved": True,
                                    "dry_run": not live_publish_post,
                                    "status": "pending",
                                    "output": None,
                                })

                    res = run_async(submit_post_approved())
                    out = res.get("output", {})
                    if out.get("error"):
                        st.error(f"Error: {out.get('message')}")
                    else:
                        st.success(f"Status: {res['status']} — {out.get('message')}")
                        if out.get("post_id"):
                            st.info(f"Published Post ID: `{out.get('post_id')}`")
                    st.json(out)

        with col_post_cancel:
            if st.button("❌ Reject / Cancel Post", use_container_width=True):
                st.warning("Post publication cancelled. No changes were made to LinkedIn.")

    # Tab 6: LinkedIn Profile Auditor
    with tab_linkedin_profile:
        st.subheader("💼 LinkedIn Profile Auditor & Recommendations")
        st.caption("Descriptive, actionable profile evaluation without numerical scores (following Part 4 specs).")

        col_audit_btn, col_load_btn = st.columns([2, 2])
        with col_load_btn:
            if st.button("📥 Load Profile from LinkedIn (OIDC)", use_container_width=True):
                prof = fetch_linkedin_profile()
                if prof.get("error"):
                    st.warning(prof.get("message"))
                else:
                    st.success(f"Loaded Profile: {prof.get('name')} ({prof.get('member_id')})")
                    st.session_state["audited_name"] = prof.get("name")

        prof_headline = st.text_input("Current Headline", value="Software Engineer | Full-Stack & AI Systems")
        prof_about = st.text_area("Current About / Summary", value="Building developer tooling and AI agent workflows with LangGraph and MCP.", height=100)
        prof_skills = st.text_input("Current Skills (comma-separated)", value="Python, LangGraph, MCP, FastAPI, Docker, TypeScript")

        if st.button("🔍 Run Profile Audit", type="primary", use_container_width=True):
            with st.spinner("Auditing profile presentation and formulating recommendations..."):
                analysis = analyze_linkedin_profile(
                    headline=prof_headline,
                    about=prof_about,
                    skills=prof_skills,
                )
                st.session_state["profile_analysis"] = analysis

        if "profile_analysis" in st.session_state:
            pa = st.session_state["profile_analysis"]
            st.markdown("---")
            st.markdown(f"```text\n{pa.get('formatted_report', '')}\n```")

            with st.expander("💡 View Raw Audit Data"):
                st.json(pa)

    # Tab 7: Interactive Multi-MCP Agent Chat
    with tab_chat:
        st.subheader("💬 Ask the Multi-MCP Personal Agent")
        st.caption("Autonomous LangGraph agent with real-time access to both GitHub and LinkedIn MCP tools.")

        for role, text in st.session_state["chat_history"]:
            with st.chat_message(role):
                st.write(text)

        user_query = st.chat_input(f"Ask anything about {repo_url} or LinkedIn actions...")
        if user_query:
            st.session_state["chat_history"].append(("user", user_query))
            with st.chat_message("user"):
                st.write(user_query)

            with st.chat_message("assistant"):
                with st.spinner("Agent is reasoning across GitHub & LinkedIn MCP tools..."):
                    async def chat_multi_agent():
                        full_prompt = f"Repository context: '{repo_url}'. User instruction: {user_query}"
                        return await run_action_agent(full_prompt)

                    resp = run_async(chat_multi_agent())
                    ans = resp["final_answer"]
                    st.write(ans)
                    st.caption(f"Reasoned using {resp.get('tools_count', 0)} active MCP tools")
                    st.session_state["chat_history"].append(("assistant", ans))

