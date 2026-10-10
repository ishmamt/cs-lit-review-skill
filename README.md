# Computer Science Literature Review

A Codex skill that searches computer science papers and writes sourced literature reviews. Its companion MCP server searches OpenAlex, Semantic Scholar, DBLP, and arXiv.

## Install

Install Python 3.11 or later and [uv](https://docs.astral.sh/uv/).

Clone this repository into your personal Codex skills folder. Replace `<repository-url>` with this repository's GitHub URL.

```sh
git clone <repository-url> ~/.codex/skills/cs-lit-review
```

In PowerShell, use `$env:USERPROFILE\.codex\skills\cs-lit-review` as the destination. If you set `CODEX_HOME`, use `$CODEX_HOME/skills/cs-lit-review` instead.

Add this server entry to your Codex `config.toml`. Replace the example path with the absolute path to the cloned repository's `mcp-server` folder. Use forward slashes in Windows paths.

```toml
[mcp_servers.cs_lit_review]
command = "uv"
args = ["--directory", "/path/to/cs-lit-review/mcp-server", "run", "cs-lit-review-mcp"]
startup_timeout_sec = 30
```

Restart Codex. The skill and its scholarly search tools will then be available across projects. The current providers use public APIs and do not need API keys.

## Use

Ask Codex to review a computer science research topic. Give a year range if you have one. The skill asks when it is missing, then searches in adaptive rounds and follows useful citation trails. The default focused mode targets about 30 relevant papers, screens up to 80 unique candidates, and retrieves up to 320 raw records. Quick and systematic modes are also available. The Markdown review reports search and screening counts.

## License

This project uses the MIT License. See [LICENSE](LICENSE).
