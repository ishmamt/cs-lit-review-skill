# Setup

## Install the skill

Copy the `cs-lit-review` folder into a Codex skill location. For a project-local skill, use `.agents/skills/cs-lit-review/`. For a personal skill, use `$CODEX_HOME/skills/cs-lit-review/` or `~/.codex/skills/cs-lit-review/` when `CODEX_HOME` is not set.

## Run the MCP server

Install `uv` and Python 3.11 or later. The server uses the Python MCP SDK and the standard library. It does not need API keys for its current providers.

Add an MCP server entry to Codex configuration. Replace the example path with the absolute path to the package's `mcp-server` directory:

```toml
[mcp_servers.cs_lit_review]
command = "uv"
args = ["--directory", "C:/path/to/cs-lit-review/mcp-server", "run", "cs-lit-review-mcp"]
startup_timeout_sec = 30
```

Restart Codex after you change the MCP configuration. The skill uses the MCP tools when the server is available. If it is not available, use supported web search and state that the dedicated provider search was unavailable.

## Provider access

The server calls the public APIs for OpenAlex, Semantic Scholar, DBLP, and arXiv. It spaces DBLP and arXiv requests, retries transient network errors and HTTP 429/5xx responses with bounded backoff, and caches successful responses in memory for 24 hours. A provider failure is returned next to successful results from other providers.

For Semantic Scholar, set `SEMANTIC_SCHOLAR_API_KEY` in the environment that starts Codex to send an API key. Do not put the key in the repository or Codex config file. A key does not remove the need to respect the provider's current limits.
