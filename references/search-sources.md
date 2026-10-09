# Search sources and MCP tools

The companion MCP server uses public scholarly APIs. Public access does not mean unlimited access. Respect provider rate limits and terms. Report a provider failure instead of hiding it or implying complete coverage.

## Tools

The server exposes these tools:

- `search_papers`: Search one or more providers and return normalized paper records with source provenance.
- `get_paper`: Look up a paper by DOI, arXiv identifier, or provider identifier where supported.
- `get_citations`: Retrieve papers that cite a Semantic Scholar paper identifier when the provider permits the request.
- `get_references`: Retrieve references listed for a Semantic Scholar paper identifier when the provider permits the request.

The server does not summarize papers or decide inclusion. The skill owns the review workflow and synthesis.

## Providers

| Provider | Main use | Notes |
| --- | --- | --- |
| OpenAlex | Broad scholarly discovery and DOI lookup | Abstracts may be absent. Abstracts are reconstructed from an inverted index when present. |
| Semantic Scholar | Paper metadata and citation graph expansion | Anonymous requests can be rate limited. The adapter reports provider errors. |
| DBLP | Computer science publication records | Strong for CS venue and proceedings records. Abstracts are often absent. |
| arXiv | Computer science preprints | Preprints are not peer-review status evidence. |

## Normalized record

Each result includes available values for `title`, `authors`, `year`, `venue`, `publication_type`, `abstract`, `doi`, `arxiv_id`, `dblp_key`, `provider_ids`, `url`, `citation_count`, `query`, and `source`. Missing values remain empty or null. Do not infer missing metadata.

## Limits and provenance

- Search results include their provider name and submitted query.
- Provider-specific ordering is preserved within each source. Cross-provider order is not a global relevance ranking.
- The server applies per-provider result limits and a short request timeout. A failed provider returns an error entry while other providers can still return records.
- Search is a discovery aid. Review authors must judge relevance, evidence strength, and coverage.
- API availability, policies, fields, and limits can change. Check provider documentation when changing the adapters.
