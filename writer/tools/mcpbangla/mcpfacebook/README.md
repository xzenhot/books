# novelist-facebook — Facebook Pages MCP server

A stdio [Model Context Protocol](https://modelcontextprotocol.io) server that
gives the writing agents Page publishing tools: publish or schedule a post,
upload a photo, read insights, and moderate comments. It is the Facebook
counterpart of `tools/server.py` (search) and `tools/book_server.py` (book API).

```text
tools/mcpbangla/mcpfacebook/facebook.py
```

## Credentials

Create a Meta app, then generate a **long-lived user access token** with:

```text
pages_manage_posts
pages_read_engagement
pages_manage_engagement
```

Export it in `.env` (already git-ignored) or in the MCP server's `env` block:

```dotenv
FB_USER_ACCESS_TOKEN=EAAG...
FB_APP_SECRET=...            # optional; enables appsecret_proof signing
FB_GRAPH_VERSION=v21.0       # optional; default v21.0
FB_TIMEOUT=30                # optional; seconds
```

Tokens are **never** written to the JSON config — keep them in the environment.

`FB_APP_SECRET` must be the bare 32-character hex secret (Meta App Dashboard →
Settings → Basic → App secret → **Show**). If a pasted value is malformed — for
example the `<app_id>|<secret>` pair the console sometimes shows, or a truncated
string — the server logs a warning and runs **without** `appsecret_proof`
signing rather than failing every call with "Invalid appsecret_proof". A missing
proof is safe when the token itself is a server-side secret.

## Tools

| Tool | Purpose |
|------|---------|
| `list_pages` | Pages the token can manage, with page tokens |
| `get_page` | One Page's profile, fan/follower counts |
| `publish_post` | Publish or schedule a text post (`scheduled_publish_time`) |
| `publish_photo` | Upload a local image with a caption |
| `list_posts` | Recent posts with permalinks |
| `delete_post` | Delete a Page post |
| `list_comments` | Comments on a post |
| `reply_to_comment` | Reply to a comment |
| `set_comment_hidden` | Hide/unhide a comment |
| `get_page_insights` | A Page insight metric series |

Every tool returns a JSON string. Failures return
`{"ok": false, "error": "..."}` so the calling agent gets an actionable message
instead of a transport error.

## Running

```text
python tools/mcpbangla/mcpfacebook/facebook.py
```

The interpreter you point the MCP client at must have `mcp` and `python-dotenv`
installed (see `requirements.txt`).

One-off check — runs the server on stdio and waits for a client:

```text
python tools/mcpbangla/mcpfacebook/facebook.py
```

The quickest real check is `copilot mcp list`, which shows whether the client
loaded the server, or `/mcp` inside VS Code / Copilot CLI.

## Client configuration

Use the shape your client expects — **VS Code reads `servers`**, while
**Copilot CLI reads `mcpServers`**:

```json
{
  "servers": {
    "novelist-facebook": {
      "type": "stdio",
      "command": "python",
      "args": ["d:\\lab\\github\\books\\writer\\tools\\mcpbangla\\mcpfacebook\\facebook.py"],
      "env": { "FB_USER_ACCESS_TOKEN": "${input:fb-user-access-token}" }
    }
  }
}
```

VS Code can prompt for the tokens instead of hardcoding them. This is exactly
what [`.vscode/mcp.json`](../../../.vscode/mcp.json) does:

```json
{
  "inputs": [
    { "id": "fb-user-access-token", "type": "promptString", "password": true,
      "description": "Facebook long-lived user access token" },
    { "id": "fb-app-secret", "type": "promptString", "password": true,
      "description": "Facebook app secret (optional)" }
  ]
}
```

## Notes

- Facebook's Graph API **cannot return a friend list**. Since April 2018
  `/me/friends` returns only friends who also use the same app, so it is normally
  empty; `user_friends` is not grantable to ordinary apps and `friendlists` is
  removed. This is a platform restriction, not a token problem — every API
  version returns `{"data":[]}`.
- To get a friend list, use Facebook's own export (Settings → Your Facebook
  Information → Download your information → tick **Friends** → JSON) and read it
  with `tools/friends_export.py`.
- `publish_post` and `publish_photo` are write operations — they publish to the
  live Page. Only call them after the book's quality gate passes.
- `scheduled_publish_time` must be an ISO 8601 UTC timestamp
  (`YYYY-MM-DDTHH:MM:SSZ`) and at least 10 minutes in the future — a Graph API
  rule, not this server's.
- This server talks to the Graph API only. It does not run Meta's hosted
  developer-tools MCP endpoint (`https://mcp.facebook.com/devtools`), which uses
  OAuth and a different tool surface.
