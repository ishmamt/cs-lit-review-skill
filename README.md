# Computer Science Literature Review

A Codex skill that searches computer science papers and writes sourced literature reviews. The MCP server searches OpenAlex, Semantic Scholar, DBLP, and arXiv.

## Install

Install Python 3.11 or later and [uv](https://docs.astral.sh/uv/). Clone this repository into your Codex skills folder:

```sh
git clone <repository-url> ~/.codex/skills/cs-lit-review
```

On Windows, use `$env:USERPROFILE\.codex\skills\cs-lit-review`. If `CODEX_HOME` is set, use `$CODEX_HOME/skills/cs-lit-review`.

Add this MCP server entry to Codex `config.toml`. Replace the path with the full path to this repository's `mcp-server` folder. Use forward slashes in Windows paths.

```toml
[mcp_servers.cs_lit_review]
command = "uv"
args = ["--directory", "/path/to/cs-lit-review/mcp-server", "run", "cs-lit-review-mcp"]
startup_timeout_sec = 30
```

Restart Codex. See [setup.md](references/setup.md) for provider access and API-key setup.

## Use

Ask Codex for a literature review. Give a year range and depth, or the skill will ask before searching. Comprehensive mode targets 60 included papers, screens 240 candidates, and retrieves up to 960 records. Quick, focused, and systematic modes are also available. Reviews group papers in compact comparisons and list search errors at the end.

## License

MIT. See [LICENSE](LICENSE).
