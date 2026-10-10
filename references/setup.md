# Setup

## Install the skill

Copy `cs-lit-review` to a Codex skill folder:

- Project: `.agents/skills/cs-lit-review/`
- Personal: `$CODEX_HOME/skills/cs-lit-review/` or `~/.codex/skills/cs-lit-review/`

## Configure the MCP server

Install Python 3.11 or later and `uv`. Add this entry to Codex `config.toml`. Replace the example path with the full path to `mcp-server`:

```toml
[mcp_servers.cs_lit_review]
command = "uv"
args = ["--directory", "C:/path/to/cs-lit-review/mcp-server", "run", "cs-lit-review-mcp"]
startup_timeout_sec = 30
```

Restart Codex. If the MCP server is unavailable, use supported web search and state that provider search was unavailable.

## Provider access

The server searches OpenAlex, Semantic Scholar, DBLP, and arXiv. It paces requests, retries transient errors, and caches successful responses in memory for 24 hours. It returns provider errors with any successful results.

To use a Semantic Scholar API key, set `SEMANTIC_SCHOLAR_API_KEY` in the environment that starts Codex. Do not store the key in the repository or Codex config. A key does not remove provider limits.
