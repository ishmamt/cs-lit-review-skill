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
| Semantic Scholar | Paper metadata and citation graph expansion | Anonymous requests can be rate limited. Set `SEMANTIC_SCHOLAR_API_KEY` in the server environment to send an API key. |
| DBLP | Computer science publication records | Strong for CS venue and proceedings records. Abstracts are often absent. |
| arXiv | Computer science preprints | Preprints are not peer-review status evidence. |

## Normalized record

Each result includes available values for `title`, `authors`, `year`, `venue`, `publication_type`, `abstract`, `doi`, `arxiv_id`, `dblp_key`, `provider_ids`, `url`, `citation_count`, `query`, and `source`. Missing values remain empty or null. Do not infer missing metadata.

## Limits and provenance

- Search results include their provider name and submitted query.
- Provider-specific ordering is preserved within each source. Cross-provider order is not a global relevance ranking.
- `search_papers` returns up to 10 records per provider per query by default. The caller can set `limit_per_source` from 1 to 25.
- Limits apply to each query, not to the full review. With all four providers, one query can return up to 40 records by default or 100 at the maximum. Multiple queries can return duplicates.
- Citation and reference expansion returns up to 20 records per request by default and caps requests at 25.
- The review workflow tracks raw records across queries, then deduplicates them before screening. It applies a separate unique-candidate screening budget and a target for included papers.
- Count records from citation and reference expansion toward the same raw-record budget as query results.
- The server applies a 20-second request timeout, bounded retries with backoff for transient network errors and HTTP 429/5xx responses, and provider-specific request pacing (2 seconds for DBLP and 3 seconds for arXiv). It honors `Retry-After` on HTTP 429 responses.
- Successful API responses are cached in memory for 24 hours. The cache is cleared when the MCP server process restarts.
- A failed provider returns an error entry while other providers can still return records. Rate limits are shared with other users of the same public API key or network address, so pacing cannot guarantee that a provider will accept every request.
- Search is a discovery aid. Review authors must judge relevance, evidence strength, and coverage.
- The review workflow adapts query rounds to coverage gaps and new relevant-paper yield. It reports raw, deduplicated, screened, and included counts, along with provider errors.
- API availability, policies, fields, and limits can change. Check provider documentation when changing the adapters.
