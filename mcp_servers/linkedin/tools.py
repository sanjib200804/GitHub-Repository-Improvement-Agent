"""LinkedIn API Tools for Model Context Protocol.

Implements official LinkedIn API interactions (OpenID Connect userinfo v2, etc.).
Strictly follows official OAuth authorization without scraping or browser automation.
"""

import os
import urllib.parse
from typing import Any, Dict, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

# Official LinkedIn API endpoints
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_POSTS_URL = "https://api.linkedin.com/rest/posts"


def get_linkedin_token() -> Optional[str]:
    """Retrieve LinkedIn OAuth access token from environment."""
    token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if token and token.strip():
        return token.strip()
    return None


def fetch_linkedin_profile(
    access_token: Optional[str] = None,
    raw: bool = False,
) -> Dict[str, Any]:
    """Fetch the authenticated user's LinkedIn profile using official OpenID Connect API.

    Calls GET https://api.linkedin.com/v2/userinfo with Bearer token.
    Only returns fields actually provided by the official LinkedIn API.

    Args:
        access_token: Optional LinkedIn OAuth 2.0 access token. If omitted,
                      reads from LINKEDIN_ACCESS_TOKEN environment variable.
        raw: If True, returns full raw JSON response from LinkedIn.

    Returns:
        Dictionary containing verified profile info or error details.
    """
    token = access_token or get_linkedin_token()

    # If mock mode is explicitly enabled or in offline test mode
    if os.getenv("LINKEDIN_MOCK", "").lower() in ("true", "1", "yes"):
        return {
            "error": False,
            "mock": True,
            "member_id": "mock_member_12345",
            "name": "Sanjib (Developer)",
            "given_name": "Sanjib",
            "family_name": "",
            "email": "developer@example.com",
            "picture": "https://media.licdn.com/dms/image/mock_avatar.png",
            "message": "Offline Mock Profile: LINKEDIN_MOCK is enabled.",
        }

    if not token:
        return {
            "error": True,
            "message": (
                "LINKEDIN_ACCESS_TOKEN is not configured. Please authorize via OAuth "
                "or set LINKEDIN_ACCESS_TOKEN in .env (or set LINKEDIN_MOCK=true for offline testing)."
            ),
            "authenticated": False,
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "linkedin-mcp-agent/1.0",
    }

    try:
        response = requests.get(LINKEDIN_USERINFO_URL, headers=headers, timeout=15)
    except requests.RequestException as e:
        return {
            "error": True,
            "message": f"Network error contacting LinkedIn API: {str(e)}",
        }

    if response.status_code == 200:
        data = response.json()
        result: Dict[str, Any] = {
            "error": False,
            "mock": False,
            "member_id": data.get("sub"),
            "name": data.get("name"),
            "given_name": data.get("given_name"),
            "family_name": data.get("family_name"),
            "email": data.get("email"),
            "picture": data.get("picture"),
        }
        if raw:
            result["raw_profile"] = data
        return result

    if response.status_code == 401:
        return {
            "error": True,
            "status_code": 401,
            "message": "LinkedIn access token is invalid or expired. Please re-authenticate via OAuth.",
        }

    if response.status_code == 403:
        return {
            "error": True,
            "status_code": 403,
            "message": "Access forbidden (403). Ensure 'openid', 'profile', and 'email' scopes are authorized.",
        }

    return {
        "error": True,
        "status_code": response.status_code,
        "message": f"LinkedIn API returned HTTP {response.status_code}: {response.text}",
    }


def format_profile_analysis_markdown(analysis: Dict[str, Any]) -> str:
    """Format profile analysis into the requested Part 4 descriptive format without numeric scores."""
    headline_curr = analysis.get("current_headline") or "(Not provided)"
    headline_sugg = analysis.get("suggested_headline") or "(No suggestion)"
    about_curr = analysis.get("current_about") or "(Not provided)"
    about_sugg = analysis.get("suggested_about") or "(No suggestion)"
    
    curr_skills = analysis.get("current_skills") or []
    skills_curr = ", ".join(curr_skills) if isinstance(curr_skills, list) else str(curr_skills)
    if not skills_curr:
        skills_curr = "(Not provided)"

    sugg_skills = analysis.get("suggested_skills") or []
    skills_sugg = ", ".join(sugg_skills) if isinstance(sugg_skills, list) else str(sugg_skills)

    proj_list = analysis.get("project_recommendations") or []
    if isinstance(proj_list, list) and proj_list:
        proj_recs = "\n".join(f"• {p}" for p in proj_list)
    else:
        proj_recs = str(proj_list or "• Highlight 2-3 production-ready GitHub repositories with architecture diagrams and live links.")

    overall = analysis.get("overall_improvements") or "Focus on quantifiable achievements, clear narrative, and relevant technical keywords."

    return (
        "PROFILE ANALYSIS\n\n"
        "Headline\n"
        f"Current:\n{headline_curr}\n\n"
        f"Suggested:\n{headline_sugg}\n\n"
        "About\n"
        f"Current:\n{about_curr}\n\n"
        f"Suggested:\n{about_sugg}\n\n"
        "Skills\n"
        f"Current:\n{skills_curr}\n\n"
        f"Suggested:\n{skills_sugg}\n\n"
        "Projects\n"
        f"Recommendations:\n{proj_recs}\n\n"
        f"Overall improvements:\n{overall}"
    )


def _rule_based_profile_analysis(
    headline: Optional[str],
    about: Optional[str],
    skills: Any,
    experience: Any,
    education: Any,
    projects: Any,
) -> Dict[str, Any]:
    """Deterministic fallback analyzer when LLM is offline or unconfigured."""
    headline_clean = (headline or "").strip()
    about_clean = (about or "").strip()

    skills_list = []
    if isinstance(skills, list):
        skills_list = [str(s).strip() for s in skills if str(s).strip()]
    elif isinstance(skills, str) and skills.strip():
        skills_list = [s.strip() for s in skills.split(",") if s.strip()]

    strengths = []
    missing_info = []
    suggestions = []

    if headline_clean:
        strengths.append(f"Clear existing headline: '{headline_clean}'")
        if "|" in headline_clean or "•" in headline_clean:
            strengths.append("Structured headline utilizing delimiters.")
        else:
            suggestions.append("Incorporate role, core technology stack, and domain impact into headline.")
    else:
        missing_info.append("Missing professional headline.")
        suggestions.append("Add a high-impact headline targeting your ideal role.")

    if about_clean:
        if len(about_clean) > 200:
            strengths.append("Substantial About section providing professional narrative.")
        else:
            suggestions.append("Expand About section to detail your engineering journey, key achievements, and current focus.")
    else:
        missing_info.append("Missing About / summary section.")
        suggestions.append("Craft an engaging 3-paragraph About section highlighting technical competencies and career trajectory.")

    if skills_list:
        strengths.append(f"Explicit skill inventory provided ({len(skills_list)} skills).")
    else:
        missing_info.append("No technical skills explicitly listed.")
        suggestions.append("Enrich skills section with both foundational and modern framework keywords.")

    suggested_headline = (
        f"AI Systems Engineer | Full-Stack Developer | Building Autonomous Agents with LangGraph & MCP"
        if not headline_clean
        else f"{headline_clean} | Agentic AI & Systems"
    )

    suggested_about = (
        "I am an engineer focused on building practical, scalable AI systems, developer tooling, and modern full-stack web applications. "
        "My recent work involves designing autonomous agent workflows using LangGraph and the Model Context Protocol (MCP) to bridge LLMs with real-world APIs.\n\n"
        "I have built end-to-end applications integrating vector databases, Retrieval-Augmented Generation (RAG), and streaming user interfaces. "
        "I thrive on writing clean, well-tested code, understanding protocols from first principles, and delivering intuitive developer experiences.\n\n"
        "Let's connect to discuss AI engineering, open-source architectures, and distributed systems."
    )

    suggested_skills = [
        "Python",
        "LangChain",
        "LangGraph",
        "Model Context Protocol (MCP)",
        "Retrieval-Augmented Generation (RAG)",
        "FastAPI",
        "Docker",
        "REST APIs",
        "Git",
    ]

    project_recs = [
        "Feature your flagship GitHub repositories with clear problem statements and live deployment links.",
        "Add measurable impact statements (e.g. 'Substantially reduced query latency using vector indexing').",
        "Include architecture flow diagrams in project descriptions or pinned media.",
    ]

    overall = (
        "Your profile has a solid foundation. Elevate it by replacing generic summaries with a story-driven narrative, "
        "highlighting hands-on protocol implementations (such as MCP), and pinning your best GitHub open-source repositories."
    )

    analysis_data = {
        "error": False,
        "current_headline": headline_clean,
        "suggested_headline": suggested_headline,
        "current_about": about_clean,
        "suggested_about": suggested_about,
        "current_skills": skills_list,
        "suggested_skills": suggested_skills,
        "strengths": strengths,
        "missing_information": missing_info,
        "improvement_suggestions": suggestions,
        "project_recommendations": project_recs,
        "overall_improvements": overall,
        "current_analysis": "Descriptive profile evaluation based on completeness, keyword alignment, and professional presentation.",
    }
    analysis_data["formatted_report"] = format_profile_analysis_markdown(analysis_data)
    return analysis_data


def analyze_linkedin_profile(
    headline: Optional[str] = None,
    about: Optional[str] = None,
    skills: Optional[Any] = None,
    experience: Optional[Any] = None,
    education: Optional[Any] = None,
    projects: Optional[Any] = None,
    profile_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Analyze a LinkedIn profile and provide professional improvement recommendations.

    Evaluates headline, about section, skills, experience, and projects.
    Returns descriptive feedback, suggested headline, suggested About section,
    and targeted skills. Follows the strict rule of descriptive feedback without numeric scores.

    Args:
        headline: Current LinkedIn headline.
        about: Current About / summary section.
        skills: List of current skills or comma-separated string.
        experience: Summary of work experience or list of roles.
        education: Educational background details.
        projects: Notable projects or GitHub links.
        profile_data: Optional dictionary containing all profile fields above.

    Returns:
        Structured dictionary with analysis findings, recommendations, and formatted report.
    """
    # Unpack profile_data if passed as a dictionary
    if profile_data and isinstance(profile_data, dict):
        headline = headline or profile_data.get("headline")
        about = about or profile_data.get("about")
        skills = skills or profile_data.get("skills")
        experience = experience or profile_data.get("experience")
        education = education or profile_data.get("education")
        projects = projects or profile_data.get("projects")

    # If all fields empty, attempt fetching available account identity via OIDC
    if not any([headline, about, skills, experience, education, projects]):
        fetched = fetch_linkedin_profile()
        if not fetched.get("error"):
            headline = f"Software Engineer | {fetched.get('name', 'Developer')}"

    # Return immediate rule-based analysis in mock mode or offline test environments
    if os.getenv("LINKEDIN_MOCK", "").lower() in ("true", "1", "yes"):
        return _rule_based_profile_analysis(
            headline=headline,
            about=about,
            skills=skills,
            experience=experience,
            education=education,
            projects=projects,
        )

    # Try LLM-assisted analysis if LLM is configured
    try:
        from backend.agent import get_llm
        llm = get_llm()
        prompt = (
            f"You are a professional tech career strategist and LinkedIn profile auditor.\n"
            f"Analyze the following LinkedIn profile information:\n"
            f"- Headline: {headline or '(Not specified)'}\n"
            f"- About Section: {about or '(Not specified)'}\n"
            f"- Skills: {skills or '(Not specified)'}\n"
            f"- Experience: {experience or '(Not specified)'}\n"
            f"- Projects: {projects or '(Not specified)'}\n\n"
            f"Generate a professional, actionable profile analysis.\n"
            f"RULES:\n"
            f"1. DO NOT assign scores such as 8/10 or 90%. Keep feedback purely descriptive.\n"
            f"2. Provide a compelling, modern suggested headline (e.g. Role | Tech Stack | Value).\n"
            f"3. Provide a warm, narrative-driven 2-3 paragraph suggested About section.\n"
            f"4. Suggest high-value skills relevant to modern engineering (e.g. Python, LangGraph, MCP, RAG, FastAPI).\n"
            f"5. Suggest concrete ways to showcase GitHub projects with problem, stack, and outcome.\n\n"
            f"Format your response as valid JSON with keys: "
            f"'current_analysis', 'strengths', 'missing_information', 'improvement_suggestions', "
            f"'suggested_headline', 'suggested_about', 'suggested_skills', 'project_recommendations', 'overall_improvements'."
        )
        resp = llm.invoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)
        # Extract JSON from LLM response
        import json
        import re
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            data["error"] = False
            data["current_headline"] = headline or ""
            data["current_about"] = about or ""
            data["current_skills"] = skills or []
            data["formatted_report"] = format_profile_analysis_markdown(data)
            return data
    except Exception:
        # Fall back to reliable rule-based analyzer on any exception or offline environment
        pass

    return _rule_based_profile_analysis(
        headline=headline,
        about=about,
        skills=skills,
        experience=experience,
        education=education,
        projects=projects,
    )


def create_linkedin_post(
    content: str,
    image_url: Optional[str] = None,
    dry_run: bool = False,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new post on LinkedIn using the official REST API (POST /rest/posts).

    Requires explicit user confirmation before execution.

    Args:
        content: Text commentary to publish.
        image_url: Optional image link or asset identifier.
        dry_run: If True, validates payload without making external write requests.
        access_token: Optional OAuth access token with w_member_social scope.

    Returns:
        Dictionary containing post result, status, or validation details.
    """
    if not content or not content.strip():
        return {
            "error": True,
            "message": "Post content cannot be empty.",
        }

    token = access_token or get_linkedin_token()

    if dry_run or os.getenv("LINKEDIN_MOCK", "").lower() in ("true", "1", "yes"):
        return {
            "error": False,
            "dry_run": True,
            "content": content.strip(),
            "image_url": image_url,
            "author": "urn:li:person:mock_member_12345",
            "message": "Dry-run mode: Post payload validated successfully without mutating LinkedIn.",
        }

    if not token:
        return {
            "error": True,
            "message": (
                "LINKEDIN_ACCESS_TOKEN is required to publish a LinkedIn post. "
                "Please configure LINKEDIN_ACCESS_TOKEN in .env or authenticate via OAuth."
            ),
        }

    # Determine author person URN
    author_urn = os.getenv("LINKEDIN_PERSON_URN")
    if not author_urn:
        profile = fetch_linkedin_profile(access_token=token)
        if profile.get("error"):
            return {
                "error": True,
                "message": f"Could not determine LinkedIn author identity: {profile.get('message')}",
            }
        author_urn = f"urn:li:person:{profile.get('member_id')}"

    payload: Dict[str, Any] = {
        "author": author_urn,
        "commentary": content.strip(),
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": "202401",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
        "User-Agent": "linkedin-mcp-agent/1.0",
    }

    try:
        response = requests.post(LINKEDIN_POSTS_URL, json=payload, headers=headers, timeout=15)
    except requests.RequestException as e:
        return {
            "error": True,
            "message": f"Network error contacting LinkedIn Posts API: {str(e)}",
        }

    if response.status_code == 201:
        post_id = response.headers.get("x-restli-id") or response.headers.get("x-linkedin-id")
        return {
            "error": False,
            "dry_run": False,
            "post_id": post_id,
            "author": author_urn,
            "message": "LinkedIn post created successfully!",
        }

    if response.status_code == 401:
        return {
            "error": True,
            "status_code": 401,
            "message": "LinkedIn access token is invalid or expired. Please re-authenticate via OAuth.",
        }

    if response.status_code == 403:
        return {
            "error": True,
            "status_code": 403,
            "message": (
                "Forbidden (403): Your LinkedIn access token lacks the 'w_member_social' permission "
                "required to publish posts on your behalf."
            ),
        }

    return {
        "error": True,
        "status_code": response.status_code,
        "message": f"LinkedIn API returned HTTP {response.status_code}: {response.text}",
    }


def delete_linkedin_post(
    post_id: str,
    dry_run: bool = False,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a post on LinkedIn using official REST API (DELETE /rest/posts/{urn}).

    Requires explicit user confirmation before execution.

    Args:
        post_id: Identifier or URN of the post to delete.
        dry_run: If True, validates post identifier without deleting.
        access_token: Optional OAuth access token.

    Returns:
        Dictionary containing deletion result or error details.
    """
    if not post_id or not post_id.strip():
        return {
            "error": True,
            "message": "post_id cannot be empty.",
        }

    clean_id = post_id.strip()
    token = access_token or get_linkedin_token()

    if dry_run or os.getenv("LINKEDIN_MOCK", "").lower() in ("true", "1", "yes"):
        return {
            "error": False,
            "dry_run": True,
            "post_id": clean_id,
            "message": f"Dry-run mode: Deletion of post '{clean_id}' validated without mutating LinkedIn.",
        }

    if not token:
        return {
            "error": True,
            "message": "LINKEDIN_ACCESS_TOKEN is required to delete a post.",
        }

    encoded_id = urllib.parse.quote(clean_id, safe="")
    url = f"{LINKEDIN_POSTS_URL}/{encoded_id}"

    headers = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": "202401",
        "X-Restli-Protocol-Version": "2.0.0",
        "User-Agent": "linkedin-mcp-agent/1.0",
    }

    try:
        response = requests.delete(url, headers=headers, timeout=15)
    except requests.RequestException as e:
        return {
            "error": True,
            "message": f"Network error contacting LinkedIn API: {str(e)}",
        }

    if response.status_code in (200, 204):
        return {
            "error": False,
            "dry_run": False,
            "post_id": clean_id,
            "message": f"Post '{clean_id}' deleted successfully.",
        }

    if response.status_code == 404:
        return {
            "error": True,
            "status_code": 404,
            "message": f"Post '{clean_id}' was not found on LinkedIn.",
        }

    if response.status_code == 403:
        return {
            "error": True,
            "status_code": 403,
            "message": (
                f"Forbidden (403): Cannot delete post '{clean_id}'. "
                "Ensure your token has owner permissions for this post."
            ),
        }

    return {
        "error": True,
        "status_code": response.status_code,
        "message": f"LinkedIn API returned HTTP {response.status_code}: {response.text}",
    }


def update_linkedin_profile(
    headline: Optional[str] = None,
    about: Optional[str] = None,
    dry_run: bool = False,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Prepare and validate profile updates, adhering strictly to official API capabilities.

    Requires explicit user confirmation before execution.

    Args:
        headline: Proposed new headline.
        about: Proposed new About section.
        dry_run: If True, prepares and validates updates without sending external mutations.
        access_token: Optional OAuth access token.

    Returns:
        Dictionary detailing proposed changes and API status.
    """
    if not headline and not about:
        return {
            "error": True,
            "message": "At least one of 'headline' or 'about' must be provided to update profile.",
        }

    if dry_run or os.getenv("LINKEDIN_MOCK", "").lower() in ("true", "1", "yes"):
        return {
            "error": False,
            "dry_run": True,
            "proposed_headline": headline,
            "proposed_about": about,
            "message": "Dry-run mode: Profile updates prepared and validated. Awaiting user confirmation before publishing.",
        }

    return {
        "error": True,
        "status_code": 403,
        "proposed_headline": headline,
        "proposed_about": about,
        "message": (
            "Official LinkedIn API Limitation: Direct automated updating of member headlines/summaries "
            "is restricted to LinkedIn Enterprise / Partner applications and is not available to standard "
            "developer OAuth tokens. Browser automation and web scraping are strictly prohibited by design."
        ),
    }
