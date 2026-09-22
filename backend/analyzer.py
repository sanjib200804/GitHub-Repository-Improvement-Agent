"""Repository Analysis Engine.

Performs grounded code and documentation audits:
1. Gathers factual context via MCP tools (metadata, tree, README, issues).
2. Performs semantic RAG queries for code patterns, error handling, and tests.
3. Evaluates:
   - Documentation (README quality, setup instructions, usage, missing sections).
   - Codebase & Structure (file layout, missing configs, test setup, error handling, security).
4. Generates practical, evidence-grounded improvement suggestions with explicit "Why Useful" rationales.
"""

import json
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from mcp_server.github_tools import (
    fetch_repository,
    fetch_repository_tree,
    read_repository_file,
    fetch_repository_issues,
)
from backend.rag import RepositoryRAG
from backend.agent import get_llm, extract_message_text

load_dotenv()


class ImprovementSuggestion(BaseModel):
    category: str = Field(description="Area of improvement: Documentation, Testing, Architecture, Configuration, Security")
    title: str = Field(description="Short title of the improvement")
    recommendation: str = Field(description="Concrete actionable recommendation")
    why_useful: str = Field(description="Detailed explanation of why this improvement is valuable")
    evidence: str = Field(description="Specific file, path, or observed fact supporting this suggestion")


class DocumentationAudit(BaseModel):
    readme_found: bool
    readme_quality_score: int = Field(description="Score from 1 to 10")
    project_description_assessment: str
    installation_instructions_status: str
    usage_instructions_status: str
    missing_documentation_elements: List[str]


class CodebaseAudit(BaseModel):
    project_structure_assessment: str
    missing_configurations: List[str] = Field(description="e.g. .gitignore, CI/CD, linter config, Dockerfile")
    tests_detected: bool
    test_framework_status: str
    error_handling_observations: List[str]
    security_observations: List[str]


class RepositoryAnalysisReport(BaseModel):
    repository_name: str
    repository_url: str
    overall_health_score: int = Field(description="Overall score from 1 to 100")
    executive_summary: str
    documentation_audit: DocumentationAudit
    codebase_audit: CodebaseAudit
    improvements: List[ImprovementSuggestion]


def collect_repository_evidence(repo_url: str) -> Dict[str, Any]:
    """Gather all raw context from the repository via GitHub API and RAG."""
    # 1. Metadata
    meta = fetch_repository(repo_url)

    # 2. File Tree
    tree = fetch_repository_tree(repo_url)

    # 3. Read README if available
    readme_content = ""
    for potential_readme in ["README.md", "README", "readme.md", "README.rst"]:
        res = read_repository_file(repo_url, potential_readme)
        if not res.get("error"):
            readme_content = res.get("content", "")
            break

    # 4. Read Top-level Configurations
    config_samples = {}
    for cfg in ["pyproject.toml", "package.json", "setup.py", "requirements.txt", "Dockerfile", ".gitignore"]:
        res = read_repository_file(repo_url, cfg)
        if not res.get("error"):
            config_samples[cfg] = res.get("content", "")[:1000]

    # 5. Existing Issues
    issues_res = fetch_repository_issues(repo_url, max_issues=5)
    issues = issues_res.get("issues", []) if not issues_res.get("error") else []

    # 6. RAG Context
    rag_context = ""
    try:
        rag = RepositoryRAG.index_repository(repo_url=repo_url, max_files=10)
        rag_context = rag.retrieve_context("error handling exceptions database testing configuration", top_k=3)
    except Exception:
        rag_context = "(RAG index unavailable or empty)"

    return {
        "metadata": meta,
        "tree_summary": tree.get("tree_summary", "(No tree)"),
        "total_files": tree.get("filtered_files_count", 0),
        "file_list": [f.get("path") for f in tree.get("files", [])[:40]],
        "readme_content": readme_content[:3000],
        "config_samples": config_samples,
        "issues": issues,
        "rag_context": rag_context,
    }


def analyze_repository(repo_url: str) -> RepositoryAnalysisReport:
    """Analyze a repository and produce a structured improvement report."""
    evidence = collect_repository_evidence(repo_url)

    system_prompt = (
        "You are an expert Principal Software Engineer and Code Reviewer. "
        "Analyze the provided GitHub repository evidence thoroughly and objectively.\n"
        "Rules:\n"
        "1. Do NOT claim the code has a bug or issue unless you have direct evidence from the provided context.\n"
        "2. For every improvement suggestion, you MUST explain 'why_useful' clearly and cite specific 'evidence'.\n"
        "3. Provide realistic scores and actionable suggestions."
    )

    user_prompt = f"""
Analyze this GitHub Repository: {repo_url}

=== REPOSITORY METADATA ===
{json.dumps(evidence["metadata"], indent=2)}

=== FILE TREE STRUCTURE ===
{evidence["tree_summary"]}

=== DETECTED FILES (Sample) ===
{evidence["file_list"]}

=== README CONTENT ===
{evidence["readme_content"] if evidence["readme_content"] else "(No README found)"}

=== DETECTED CONFIGURATIONS ===
{list(evidence["config_samples"].keys())}

=== COMMUNITY ISSUES (Sample) ===
{[i.get("title") for i in evidence["issues"]]}

=== RAG CODE CONTEXT ===
{evidence["rag_context"]}

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "repository_name": "{evidence['metadata'].get('name', repo_url)}",
  "repository_url": "{repo_url}",
  "overall_health_score": <1-100>,
  "executive_summary": "<concise summary of repo state>",
  "documentation_audit": {{
    "readme_found": <true/false>,
    "readme_quality_score": <1-10>,
    "project_description_assessment": "<assessment>",
    "installation_instructions_status": "<status>",
    "usage_instructions_status": "<status>",
    "missing_documentation_elements": ["<elem1>", ...]
  }},
  "codebase_audit": {{
    "project_structure_assessment": "<assessment>",
    "missing_configurations": ["<item1>", ...],
    "tests_detected": <true/false>,
    "test_framework_status": "<status>",
    "error_handling_observations": ["<obs1>", ...],
    "security_observations": ["<obs1>", ...]
  }},
  "improvements": [
    {{
      "category": "<Documentation | Testing | Architecture | Configuration | Security>",
      "title": "<title>",
      "recommendation": "<concrete recommendation>",
      "why_useful": "<clear explanation of why this matters>",
      "evidence": "<file or reason>"
    }}
  ]
}}
"""

    llm = get_llm()
    response = llm.invoke([
        ("system", system_prompt),
        ("user", user_prompt),
    ])

    raw_text = extract_message_text(response.content)

    # Clean markdown json code fences if present
    clean_json = raw_text.strip()
    if clean_json.startswith("```json"):
        clean_json = clean_json[7:]
    elif clean_json.startswith("```"):
        clean_json = clean_json[3:]
    if clean_json.endswith("```"):
        clean_json = clean_json[:-3]
    clean_json = clean_json.strip()

    data = json.loads(clean_json)
    return RepositoryAnalysisReport.model_validate(data)


def format_report_as_markdown(report: RepositoryAnalysisReport) -> str:
    """Render the analysis report into a visually clear GitHub markdown report."""
    md = [
        f"# Repository Improvement Audit: {report.repository_name}",
        f"**Repository URL:** {report.repository_url}  ",
        f"**Overall Health Score:** {report.overall_health_score}/100\n",
        f"## Executive Summary\n{report.executive_summary}\n",
        "## 1. Documentation Audit",
        f"- **README Found:** {'Yes' if report.documentation_audit.readme_found else 'No'}",
        f"- **README Quality Score:** {report.documentation_audit.readme_quality_score}/10",
        f"- **Project Description:** {report.documentation_audit.project_description_assessment}",
        f"- **Installation Instructions:** {report.documentation_audit.installation_instructions_status}",
        f"- **Usage Instructions:** {report.documentation_audit.usage_instructions_status}",
        "- **Missing Documentation Elements:**",
    ]
    for elem in report.documentation_audit.missing_documentation_elements:
        md.append(f"  - {elem}")

    md.extend([
        "\n## 2. Codebase & Structure Audit",
        f"- **Project Structure:** {report.codebase_audit.project_structure_assessment}",
        f"- **Tests Detected:** {'Yes' if report.codebase_audit.tests_detected else 'No'}",
        f"- **Test Framework Status:** {report.codebase_audit.test_framework_status}",
        "- **Missing Configurations:**",
    ])
    for cfg in report.codebase_audit.missing_configurations:
        md.append(f"  - {cfg}")

    if report.codebase_audit.error_handling_observations:
        md.append("- **Error Handling Observations:**")
        for obs in report.codebase_audit.error_handling_observations:
            md.append(f"  - {obs}")

    if report.codebase_audit.security_observations:
        md.append("- **Security & Secrets Observations:**")
        for sec in report.codebase_audit.security_observations:
            md.append(f"  - {sec}")

    md.append("\n## 3. Practical Improvements & Rationales")
    for idx, imp in enumerate(report.improvements, 1):
        md.extend([
            f"### {idx}. [{imp.category}] {imp.title}",
            f"- **Recommendation:** {imp.recommendation}",
            f"- **Why It's Useful:** {imp.why_useful}",
            f"- **Evidence:** `{imp.evidence}`\n",
        ])

    return "\n".join(md)
