#!/usr/bin/env python3
"""
facebook.py — Model Context Protocol (MCP) server for Facebook Pages.

Exposes the parts of the Facebook Graph API that matter for publishing book
posts: page discovery, publishing/scheduling posts, reading post insights, and
listing/moderating comments. It is the Facebook counterpart of the
`novelist-*` servers (`tools/server.py`, `tools/book_server.py`).

Credentials are read from the environment (never from the JSON config, so
tokens stay out of source control):

    FB_USER_ACCESS_TOKEN   long-lived user token with pages_manage_posts,
                           pages_read_engagement, pages_manage_engagement
    FB_APP_SECRET          optional; enables appsecret_proof request signing
    FB_GRAPH_VERSION       optional; Graph API version (default v21.0)

Run:
    python tools/mcpbangla/mcpfacebook/facebook.py

Every tool returns a JSON string. Failures return
``{"ok": false, "error": "..."}`` instead of raising, so the agent can report
an actionable message rather than a transport error.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent

# Make the shared `env` loader importable and load <writer>/.env before reading
# FB_* settings. This works no matter which directory the MCP client launches us
# from, because the path is anchored to this file.
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))

from env import bootstrap as _bootstrap_env  # noqa: E402

_bootstrap_env()

from mcp.server.fastmcp import FastMCP  # noqa: E402

GRAPH_VERSION = os.getenv("FB_GRAPH_VERSION", "v21.0")
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
TIMEOUT = int(os.getenv("FB_TIMEOUT", "30"))

mcp = FastMCP("novelist-facebook")

# Meta app secrets are 32 hex characters.
_SECRET_RE = re.compile(r"[0-9a-fA-F]{32}")
_secret_warned = False


# ---------------------------------------------------------------------------
# Graph API plumbing
# ---------------------------------------------------------------------------

class FacebookError(RuntimeError):
    """A Graph API call failed."""


def _token() -> str:
    token = os.getenv("FB_USER_ACCESS_TOKEN", "").strip()
    if not token:
        raise FacebookError(
            "FB_USER_ACCESS_TOKEN is not set. Export a long-lived user token with "
            "pages_manage_posts, pages_read_engagement and pages_manage_engagement "
            "(see tools/mcpbangla/mcpfacebook/README.md)."
        )
    return token


def _app_secret() -> str:
    """Return a usable app secret, or ``""`` when the configured one is invalid.

    Meta displays the credential as ``<app_id>|<app_secret>`` in some views, and
    a real app secret is exactly 32 hex characters. ``appsecret_proof`` must be
    computed over the bare secret, so the ``<id>|`` prefix is stripped.

    An invalid value is treated as *not configured* instead of being signed:
    a wrong proof makes every Graph call fail with "Invalid appsecret_proof",
    which is far worse than running unsigned with a server-side token. A warning
    names the problem so the value can be corrected.
    """
    global _secret_warned

    raw = os.getenv("FB_APP_SECRET", "").strip().strip("\"'")
    if not raw:
        return ""
    if "|" in raw:
        raw = raw.rsplit("|", 1)[1].strip()
    if _SECRET_RE.fullmatch(raw):
        return raw

    if not _secret_warned:
        _secret_warned = True
        print(
            f"[novelist-facebook] WARNING: FB_APP_SECRET is not a valid app secret "
            f"({len(raw)} chars; expected 32 hex characters). Ignoring it and running "
            "without appsecret_proof signing. Copy the secret from Meta App Dashboard "
            "-> Settings -> Basic -> App secret -> Show, then restart the server.",
            file=sys.stderr,
        )
    return ""


def _appsecret_proof(token: str) -> Optional[str]:
    secret = _app_secret()
    if not secret:
        return None
    return hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def _request(
    method: str,
    path: str,
    params: Optional[dict] = None,
    body: Optional[dict] = None,
    token: Optional[str] = None,
) -> Any:
    token = (token or _token()).strip()
    if not token:
        raise FacebookError("FB_USER_ACCESS_TOKEN is not set.")
    query = dict(params or {})
    proof = _appsecret_proof(token)

    if body is not None:
        # Keep the token out of the URL for write calls.
        body = dict(body)
        body["access_token"] = token
        if proof:
            body["appsecret_proof"] = proof
    else:
        query["access_token"] = token
        if proof:
            query["appsecret_proof"] = proof

    url = f"{GRAPH_BASE}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"

    data = urllib.parse.urlencode(body).encode("utf-8") if body else None
    request = urllib.request.Request(url, data=data, method=method.upper())
    if data:
        request.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw).get("error", {}).get("message", raw)
        except json.JSONDecodeError:
            detail = raw
        raise FacebookError(f"Graph API {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise FacebookError(f"Graph API unreachable: {exc.reason}") from exc


def _json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _fail(exc: Exception) -> str:
    return _json({"ok": False, "error": str(exc)})


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@mcp.tool()
def list_pages() -> str:
    """List the Facebook Pages the configured user token can manage.

    Returns each page's id, name, category, and the page-scoped access token
    (needed by the other tools when acting on a page the user does not own).
    """
    try:
        result = _request(
            "GET",
            "me/accounts",
            params={
                "fields": "id,name,category,access_token,tasks",
                "limit": 100,
            },
        )
        return _json({"ok": True, "pages": result.get("data", [])})
    except Exception as exc:  # noqa: BLE001 - reported to the agent verbatim
        return _fail(exc)


@mcp.tool()
def get_page(page_id: str) -> str:
    """Return one Page's profile fields.

    Args:
        page_id: The Page id (from ``list_pages``).
    """
    try:
        result = _request(
            "GET",
            page_id,
            params={"fields": "id,name,category,fan_count,followers_count,link,about"},
        )
        return _json({"ok": True, "page": result})
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

@mcp.tool()
def publish_post(
    page_id: str,
    message: str,
    link: Optional[str] = None,
    scheduled_publish_time: Optional[str] = None,
    page_token: Optional[str] = None,
) -> str:
    """Publish or schedule a text post on a Page.

    Args:
        page_id: Target Page id.
        message: The post body (UTF-8; Bengali is fine).
        link: Optional URL to attach.
        scheduled_publish_time: ISO 8601 UTC timestamp (YYYY-MM-DDTHH:MM:SSZ).
            When set, the post is created as a scheduled post instead of going
            live immediately.
        page_token: Optional Page access token. Defaults to the user token.
    """
    try:
        body: dict[str, Any] = {"message": message}
        if link:
            body["link"] = link
        if scheduled_publish_time:
            body["scheduled_publish_time"] = _to_unix(scheduled_publish_time)
            body["published"] = "false"

        token = (page_token or os.getenv("FB_USER_ACCESS_TOKEN", "")).strip()
        if not token:
            raise FacebookError("FB_USER_ACCESS_TOKEN is not set.")

        result = _request("POST", f"{page_id}/feed", body=body, token=token)
        mode = "scheduled" if scheduled_publish_time else "published"
        return _json(
            {
                "ok": True,
                "mode": mode,
                "post_id": result.get("id"),
                "scheduled_publish_time": scheduled_publish_time,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)


@mcp.tool()
def publish_photo(
    page_id: str,
    image_path: str,
    caption: str = "",
    scheduled_publish_time: Optional[str] = None,
) -> str:
    """Publish a photo with a caption to a Page.

    Args:
        page_id: Target Page id.
        image_path: Absolute or repo-relative path to a local image file.
        caption: Photo caption (may contain Bengali).
        scheduled_publish_time: Optional ISO 8601 UTC timestamp to schedule.
    """
    try:
        path = Path(image_path)
        if not path.is_absolute():
            path = (SCRIPT_DIR.parent.parent.parent / image_path).resolve()
        if not path.exists():
            raise FacebookError(f"Image not found: {path}")

        token = _token()
        fields: dict[str, Any] = {"caption": caption, "access_token": token}
        proof = _appsecret_proof(token)
        if proof:
            fields["appsecret_proof"] = proof
        if scheduled_publish_time:
            fields["scheduled_publish_time"] = _to_unix(scheduled_publish_time)
            fields["published"] = "false"

        boundary = "----novelistfacebookboundary"
        parts: list[bytes] = []
        for name, value in fields.items():
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode("utf-8")
            )
        parts.append(
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"source\"; "
                f"filename=\"{path.name}\"\r\nContent-Type: application/octet-stream\r\n\r\n"
            ).encode("utf-8")
            + path.read_bytes()
            + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        payload = b"".join(parts)

        request = urllib.request.Request(f"{GRAPH_BASE}/{page_id}/photos", data=payload, method="POST")
        request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
        return _json({"ok": True, "photo_id": result.get("id")})
    except urllib.error.HTTPError as exc:
        return _fail(FacebookError(f"Graph API {exc.code}: {exc.read().decode('utf-8', 'replace')}"))
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)


@mcp.tool()
def list_posts(page_id: str, limit: int = 10) -> str:
    """List a Page's recent posts, newest first.

    Args:
        page_id: Target Page id.
        limit: Maximum number of posts to return (default 10).
    """
    try:
        result = _request(
            "GET",
            f"{page_id}/posts",
            params={
                "fields": "id,message,created_time,permalink_url,shares,full_picture",
                "limit": max(1, min(limit, 100)),
            },
        )
        return _json({"ok": True, "posts": result.get("data", [])})
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)


@mcp.tool()
def delete_post(post_id: str) -> str:
    """Delete one of the Page's posts.

    Args:
        post_id: The post id (``<page_id>_<post_id>``).
    """
    try:
        _request("DELETE", post_id)
        return _json({"ok": True, "deleted": post_id})
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

@mcp.tool()
def list_comments(post_id: str, limit: int = 25) -> str:
    """List comments on a post.

    Args:
        post_id: The post id (``<page_id>_<post_id>``).
        limit: Maximum number of comments (default 25).
    """
    try:
        result = _request(
            "GET",
            f"{post_id}/comments",
            params={
                "fields": "id,message,from,created_time,like_count,is_hidden",
                "limit": max(1, min(limit, 100)),
            },
        )
        return _json({"ok": True, "comments": result.get("data", [])})
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)


@mcp.tool()
def reply_to_comment(comment_id: str, message: str) -> str:
    """Reply to a comment.

    Args:
        comment_id: The comment id.
        message: Reply body (may contain Bengali).
    """
    try:
        result = _request("POST", f"{comment_id}/comments", body={"message": message})
        return _json({"ok": True, "comment_id": result.get("id")})
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)


@mcp.tool()
def set_comment_hidden(comment_id: str, hidden: bool = True) -> str:
    """Hide or unhide a comment (moderation).

    Args:
        comment_id: The comment id.
        hidden: True to hide, False to unhide.
    """
    try:
        _request("POST", comment_id, body={"is_hidden": "true" if hidden else "false"})
        return _json({"ok": True, "comment_id": comment_id, "hidden": hidden})
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------

@mcp.tool()
def get_page_insights(
    page_id: str,
    metric: str = "page_impressions_unique",
    period: str = "day",
) -> str:
    """Read a Page insight metric series.

    Args:
        page_id: Target Page id.
        metric: Insight metric name (default ``page_impressions_unique``).
        period: ``day``, ``week``, ``days_28``, or ``lifetime``.
    """
    try:
        result = _request(
            "GET",
            f"{page_id}/insights",
            params={"metric": metric, "period": period},
        )
        return _json({"ok": True, "metric": metric, "period": period, "data": result.get("data", [])})
    except Exception as exc:  # noqa: BLE001
        return _fail(exc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_unix(timestamp: str) -> int:
    """Convert an ISO 8601 UTC timestamp to a Unix epoch second."""
    text = timestamp.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise FacebookError(
            f"Invalid scheduled_publish_time '{timestamp}'. Use ISO 8601 UTC, "
            "e.g. 2026-11-01T09:00:00Z."
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def main() -> None:
    if not os.getenv("FB_USER_ACCESS_TOKEN", "").strip():
        print(
            "[novelist-facebook] WARNING: FB_USER_ACCESS_TOKEN is not set; "
            "tools will return an actionable error until it is exported.",
            file=sys.stderr,
        )
    mcp.run()


if __name__ == "__main__":
    main()
