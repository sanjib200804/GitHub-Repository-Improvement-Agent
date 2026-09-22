"""LinkedIn OAuth 2.0 Helper Module.

Handles official LinkedIn OAuth 2.0 authorization URL generation
and authorization code exchange for access tokens.
"""

import os
import urllib.parse
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

# Standard LinkedIn OAuth endpoints
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

# Default recommended scopes for OpenID Connect + Post Sharing
DEFAULT_SCOPES = ["openid", "profile", "email", "w_member_social"]


def get_authorization_url(
    client_id: Optional[str] = None,
    redirect_uri: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    state: str = "linkedin_mcp_auth",
) -> Dict[str, Any]:
    """Generate official LinkedIn OAuth 2.0 authorization URL for the user to visit.

    Args:
        client_id: LinkedIn App Client ID. Defaults to env LINKEDIN_CLIENT_ID.
        redirect_uri: Registered callback URL. Defaults to env LINKEDIN_REDIRECT_URI.
        scopes: List of OAuth permissions requested. Defaults to openid, profile, email, w_member_social.
        state: Unique CSRF protection string.

    Returns:
        Dictionary with authorization_url, client_id, and scopes.
    """
    cid = client_id or os.getenv("LINKEDIN_CLIENT_ID")
    r_uri = redirect_uri or os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/callback")
    active_scopes = scopes or DEFAULT_SCOPES

    if not cid:
        return {
            "error": True,
            "message": "LINKEDIN_CLIENT_ID is missing. Please provide client_id or set LINKEDIN_CLIENT_ID in .env",
            "authorization_url": None,
        }

    params = {
        "response_type": "code",
        "client_id": cid,
        "redirect_uri": r_uri,
        "state": state,
        "scope": " ".join(active_scopes),
    }

    url = f"{LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return {
        "error": False,
        "authorization_url": url,
        "client_id": cid,
        "redirect_uri": r_uri,
        "scopes": active_scopes,
        "state": state,
    }


def exchange_code_for_token(
    code: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    redirect_uri: Optional[str] = None,
) -> Dict[str, Any]:
    """Exchange temporary authorization code for a LinkedIn OAuth 2.0 access token.

    Args:
        code: The authorization code returned by LinkedIn redirect.
        client_id: LinkedIn App Client ID.
        client_secret: LinkedIn App Client Secret.
        redirect_uri: Registered callback URL matching the authorization request.

    Returns:
        Dictionary with access_token, expires_in, or error details.
    """
    cid = client_id or os.getenv("LINKEDIN_CLIENT_ID")
    csecret = client_secret or os.getenv("LINKEDIN_CLIENT_SECRET")
    r_uri = redirect_uri or os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/callback")

    if not code or not code.strip():
        return {
            "error": True,
            "message": "Authorization code cannot be empty.",
        }

    if not cid or not csecret:
        return {
            "error": True,
            "message": "LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET are required.",
        }

    payload = {
        "grant_type": "authorization_code",
        "code": code.strip(),
        "redirect_uri": r_uri,
        "client_id": cid,
        "client_secret": csecret,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "linkedin-mcp-agent/1.0",
    }

    try:
        response = requests.post(LINKEDIN_TOKEN_URL, data=payload, headers=headers, timeout=15)
        data = response.json()
        if response.status_code == 200 and "access_token" in data:
            return {
                "error": False,
                "access_token": data.get("access_token"),
                "expires_in": data.get("expires_in"),
                "scope": data.get("scope"),
                "message": "Access token obtained successfully.",
            }
        else:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": data.get("error_description", data.get("message", response.text)),
                "raw_response": data,
            }
    except requests.RequestException as e:
        return {
            "error": True,
            "message": f"Network error contacting LinkedIn token endpoint: {str(e)}",
        }
