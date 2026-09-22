"""Project Post Generator: Converts GitHub Repositories into Professional LinkedIn Posts.

Follows an authentic developer voice (not generic AI hype), highlights real features,
tech stack, key learnings, and repository links. Supports optional project image generation.
"""

import os
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from backend.analyzer import collect_repository_evidence
from mcp_servers.linkedin.tools import create_linkedin_post

load_dotenv()


def _extract_tech_stack_from_evidence(evidence: Dict[str, Any]) -> List[str]:
    """Identify languages and frameworks from repository metadata and manifest files."""
    stack = []
    meta = evidence.get("metadata", {})
    if meta.get("language"):
        stack.append(meta["language"])

    manifest = evidence.get("manifest", "")
    manifest_lower = manifest.lower()
    common_libs = [
        "langchain", "langgraph", "fastapi", "streamlit", "react", "next.js",
        "typescript", "pytorch", "tensorflow", "chromadb", "pydantic", "docker",
        "vue", "express", "django", "flask", "mcp"
    ]
    for lib in common_libs:
        if lib in manifest_lower:
            stack.append(lib.capitalize() if lib != "mcp" else "MCP")

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for s in stack:
        s_norm = s.lower()
        if s_norm not in seen:
            seen.add(s_norm)
            deduped.append(s)

    return deduped or ["Python", "FastAPI"]


def generate_project_image(
    project_name: str,
    description: str,
    tech_stack: List[str],
) -> Optional[str]:
    """Generate or locate an announcement graphic for the project.

    If an image generation service or local banner is available, returns its URI/path.
    If unavailable, safely returns None (post works seamlessly without image).

    Args:
        project_name: Name of the repository.
        description: One-sentence description.
        tech_stack: Primary technologies used.

    Returns:
        Image file path, URL, or None if unavailable.
    """
    # Check if a custom banner already exists in the repository
    potential_banners = [
        os.path.join(os.getcwd(), "banner.png"),
        os.path.join(os.getcwd(), "docs", "banner.png"),
    ]
    for banner in potential_banners:
        if os.path.exists(banner):
            return banner

    # If mock mode or offline, we can provide a mock banner or None
    if os.getenv("LINKEDIN_MOCK", "").lower() in ("true", "1", "yes"):
        return f"https://raw.githubusercontent.com/assets/project_card_{project_name.lower()}.png"

    # Otherwise return None gracefully
    return None


def generate_project_post(
    repo_url: str,
    repo_evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convert GitHub project context into a high-impact, professional LinkedIn post.

    Adheres strictly to the authentic developer announcement format:
    - Project name & short explanation
    - Key features (bullet points)
    - Tech stack (bullet points)
    - Interesting technical challenge
    - Key learning
    - GitHub repository link
    - Targeted hashtags

    Args:
        repo_url: Full GitHub URL or owner/repo shorthand.
        repo_evidence: Optional pre-collected repository evidence.

    Returns:
        Dictionary with draft content, tech_stack, repo_url, and optional image_url.
    """
    evidence = repo_evidence or collect_repository_evidence(repo_url)
    meta = evidence.get("metadata", {})
    repo_name = meta.get("name") or repo_url.split("/")[-1]
    repo_desc = meta.get("description") or "An open-source software engineering tool"
    repo_link = f"https://github.com/{meta.get('full_name', repo_url.replace('https://github.com/', ''))}"
    tech_stack = _extract_tech_stack_from_evidence(evidence)

    # Attempt LLM generation if available
    llm_draft = None
    if not os.getenv("LINKEDIN_MOCK", "").lower() in ("true", "1", "yes"):
        try:
            from backend.agent import get_llm
            llm = get_llm()
            prompt = (
                f"You are a skilled software developer writing a LinkedIn post about a project you just built.\n"
                f"Repository: {repo_name}\n"
                f"Description: {repo_desc}\n"
                f"Tech Stack: {', '.join(tech_stack)}\n"
                f"README snippet: {evidence.get('readme', '')[:1000]}\n"
                f"GitHub Link: {repo_link}\n\n"
                f"Format the post following this EXACT structure:\n"
                f"🚀 I recently built [{repo_name}]\n\n"
                f"[Short explanation: what it does and the concrete problem it solves]\n\n"
                f"Key features:\n"
                f"• [Feature 1]\n"
                f"• [Feature 2]\n"
                f"• [Feature 3]\n\n"
                f"Tech stack:\n"
                f"{chr(10).join(f'• {t}' for t in tech_stack[:5])}\n\n"
                f"One of the most interesting parts was [specific technical detail or architectural challenge].\n\n"
                f"I learned [valuable engineering takeaway].\n\n"
                f"GitHub:\n"
                f"{repo_link}\n\n"
                f"#AI #SoftwareEngineering #Python #GitHub\n\n"
                f"RULES:\n"
                f"- Write authentically like a student or software engineer showcasing real work.\n"
                f"- Avoid hollow AI buzzwords (e.g., 'supercharge', 'game changer', 'unleash').\n"
                f"- Ground every feature in the actual repository evidence provided."
            )
            resp = llm.invoke(prompt)
            llm_draft = resp.content if hasattr(resp, "content") else str(resp)
        except Exception:
            llm_draft = None

    if not llm_draft:
        # High-quality deterministic developer template
        llm_draft = (
            f"🚀 I recently built {repo_name}\n\n"
            f"{repo_desc.rstrip('.')}. It was designed to solve practical developer workflow challenges "
            f"by combining structured protocol interactions with robust automation.\n\n"
            f"Key features:\n"
            f"• Automated repository analysis and grounded documentation auditing\n"
            f"• Deep Model Context Protocol (MCP) integration over standardized JSON-RPC stdio\n"
            f"• Safe Human-in-the-Loop approval gates for external write actions\n\n"
            f"Tech stack:\n"
            f"{chr(10).join(f'• {t}' for t in tech_stack[:5])}\n\n"
            f"One of the most interesting parts was architecting the communication flow across multiple MCP servers "
            f"so the agent can safely inspect external resources before requesting user confirmation.\n\n"
            f"I learned how standardized protocol architectures eliminate custom tool lock-in while preserving "
            f"strict safety boundaries around write operations.\n\n"
            f"GitHub:\n"
            f"{repo_link}\n\n"
            f"#SoftwareEngineering #AI #Python #GitHub #OpenSource"
        )

    image_path = generate_project_image(repo_name, repo_desc, tech_stack)

    return {
        "error": False,
        "repo_name": repo_name,
        "repo_url": repo_link,
        "post_content": llm_draft.strip(),
        "tech_stack": tech_stack,
        "image_url": image_path,
    }


def create_post_from_github_repo(
    repo_url: str,
    publish: bool = False,
    dry_run: bool = True,
    include_image: bool = True,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """End-to-end workflow: Read GitHub project -> Generate LinkedIn post -> Publish with confirmation.

    Workflow:
    1. Collect GitHub repository evidence (metadata, tree, README, manifest).
    2. Synthesize professional LinkedIn announcement post.
    3. Determine optional image banner.
    4. If publish=False or dry_run=True: Return draft for Human-in-the-Loop review.
    5. If publish=True and dry_run=False: Call official LinkedIn create_post tool.

    Args:
        repo_url: Target GitHub repository URL.
        publish: If True, proceeds with publishing. Requires user approval.
        dry_run: If True, executes safe validation without mutating LinkedIn.
        include_image: Whether to attach an announcement image.
        access_token: Optional LinkedIn OAuth token.

    Returns:
        Dictionary with draft, status, confirmation state, and publication output.
    """
    draft = generate_project_post(repo_url)
    content = draft["post_content"]
    image = draft["image_url"] if include_image else None

    # Step 4: Human-in-the-Loop Safety Check
    if not publish or dry_run:
        return {
            "error": False,
            "status": "awaiting_user_confirmation" if not publish else "dry_run_validated",
            "repo_url": draft["repo_url"],
            "draft_post": content,
            "image_url": image,
            "user_approved": publish,
            "dry_run": dry_run,
            "message": (
                "Post draft generated successfully. Review the draft above. "
                "Explicit user confirmation is required before publishing to LinkedIn."
            ),
        }

    # Step 5: User Confirmed - Publish via LinkedIn MCP tool
    result = create_linkedin_post(
        content=content,
        image_url=image,
        dry_run=False,
        access_token=access_token,
    )
    return {
        "error": result.get("error", False),
        "status": "published" if not result.get("error") else "publication_failed",
        "repo_url": draft["repo_url"],
        "draft_post": content,
        "image_url": image,
        "user_approved": True,
        "dry_run": False,
        "publication_result": result,
        "message": result.get("message"),
    }
