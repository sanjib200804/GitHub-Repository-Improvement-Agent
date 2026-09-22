"""README Generator Engine for GitHub Repositories.

Synthesizes repository evidence collected via MCP tools (metadata, file tree,
manifest configs, code context) and analysis recommendations to generate a
comprehensive, production-grade README.md following the required 12-section layout:
1. Project Title
2. Description
3. Features
4. Tech Stack
5. Architecture
6. Installation
7. Environment Variables
8. Usage
9. Project Structure
10. API / MCP Tools
11. Examples
12. Future Improvements
"""

import json
from typing import Dict, Optional
from dotenv import load_dotenv

from backend.analyzer import (
    collect_repository_evidence,
    analyze_repository,
    RepositoryAnalysisReport,
)
from backend.agent import get_llm, extract_message_text

load_dotenv()

REQUIRED_README_SECTIONS = [
    "Project Title",
    "Description",
    "Features",
    "Tech Stack",
    "Architecture",
    "Installation",
    "Environment Variables",
    "Usage",
    "Project Structure",
    "API / MCP Tools",
    "Examples",
    "Future Improvements",
]


def generate_improved_readme(
    repo_url: str,
    analysis_report: Optional[RepositoryAnalysisReport] = None,
) -> str:
    """Generate a comprehensive, improved README for a GitHub repository.

    Args:
        repo_url: Full GitHub repository URL or shorthand ('owner/repo').
        analysis_report: Precomputed analysis report (optional; will be generated if not provided).

    Returns:
        A complete, beautifully formatted Markdown README string.
    """
    evidence = collect_repository_evidence(repo_url)

    if analysis_report is None:
        analysis_report = analyze_repository(repo_url)

    # Format improvements to guide the "Future Improvements" section
    improvements_summary = []
    for imp in analysis_report.improvements:
        improvements_summary.append(f"- **{imp.title}** ({imp.category}): {imp.recommendation} (Reason: {imp.why_useful})")

    improvements_text = "\n".join(improvements_summary) if improvements_summary else "- No major improvements required."

    system_prompt = (
        "You are an expert technical writer and principal software architect. "
        "Your task is to generate a comprehensive, modern, production-quality README.md "
        "for the given GitHub repository based STRICTLY on actual repository context retrieved "
        "via GitHub MCP tools and RAG.\n\n"
        "Formatting Guidelines:\n"
        "1. Follow the required 12-section structure faithfully.\n"
        "2. Ground every section in reality: use the real project name, real files from the tree, "
        "real language/dependencies, and real configuration files.\n"
        "3. In 'Future Improvements', incorporate the specific suggestions identified during repository analysis.\n"
        "4. Do NOT invent phantom dependencies or fake architecture; reflect the actual repository faithfully."
    )

    user_prompt = f"""
Generate an improved, complete README.md for the repository: {repo_url}

=== ACTUAL REPOSITORY CONTEXT ===
- Name: {evidence['metadata'].get('name', 'Repository')}
- Full Name: {evidence['metadata'].get('full_name')}
- Description: {evidence['metadata'].get('description') or 'No description provided'}
- Primary Language: {evidence['metadata'].get('language') or 'General'}
- Default Branch: {evidence['metadata'].get('default_branch', 'main')}
- Stars: {evidence['metadata'].get('stars')} | Forks: {evidence['metadata'].get('forks')}

=== REPOSITORY TREE STRUCTURE ===
{evidence['tree_summary']}

=== DETECTED MANIFESTS & CONFIGURATIONS ===
{list(evidence['config_samples'].keys())}

=== CURRENT README EXCERPT ===
{evidence['readme_content'] if evidence['readme_content'] else '(Empty or no README)'}

=== IDENTIFIED AUDIT IMPROVEMENTS ===
{improvements_text}

=== REQUIRED README STRUCTURE ===
Your output MUST be a complete Markdown document containing all 12 of the following sections:
# <Project Title>
## Description
## Features
## Tech Stack
## Architecture
## Installation
## Environment Variables
## Usage
## Project Structure
## API / MCP Tools
## Examples
## Future Improvements

Generate the complete, polished Markdown README now:
"""

    llm = get_llm()
    response = llm.invoke([
        ("system", system_prompt),
        ("user", user_prompt),
    ])

    raw_markdown = extract_message_text(response.content)

    # Clean markdown wrapper if LLM wrapped in outer ```markdown ... ```
    cleaned = raw_markdown.strip()
    if cleaned.startswith("```markdown"):
        cleaned = cleaned[11:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return cleaned.strip()
