# Search sources and tools

The MCP server searches public scholarly APIs. Public access is rate-limited. Report tool and provider errors. Do not imply complete coverage when a source fails.

## Tools

| Tool | Use |
| --- | --- |
| `search_papers` | Search one or more providers. Returns normalized records with source details. |
| `get_paper` | Look up a paper by DOI or arXiv ID. |
| `get_citations` | Find papers that cite a Semantic Scholar paper ID or DOI. |
| `get_references` | Find references for a Semantic Scholar paper ID or DOI. |

The server retrieves and normalizes metadata. The skill screens papers and writes the review.

## Providers

| Provider | Use and limits |
| --- | --- |
| OpenAlex | Broad discovery and DOI lookup. Abstracts may be missing. |
| Semantic Scholar | Paper metadata and citation links. Anonymous requests can be rate-limited. Set `SEMANTIC_SCHOLAR_API_KEY` in the server environment to send a key. |
| DBLP | Computer science venues and proceedings. Abstracts are often missing. |
| arXiv | Preprints. An arXiv record does not show peer-review status. |

Records may include title, authors, year, venue, publication type, abstract, DOI, arXiv ID, DBLP key, provider IDs, URL, citation count, query, and source. Missing fields stay empty or null. Do not infer them.

## Limits and errors

- `search_papers` returns 10 records per provider by default. Set `limit_per_source` from 1 to 25. With four providers, one query returns up to 40 records by default or 100 at the maximum. Queries can return duplicates.
- Citation and reference tools return 20 records by default and allow up to 25 per call.
- Count all direct and citation results toward the same raw-record budget. Deduplicate before screening.
- Requests time out after 20 seconds. The server retries transient network errors and HTTP 429/5xx responses up to three times with backoff. It honors `Retry-After` for 429 responses.
- The server spaces Semantic Scholar requests by 1 second, DBLP by 2 seconds, and arXiv by 3 seconds. Successful responses stay in a 512-entry in-memory cache for 24 hours. The cache clears when the server restarts.
- A failed provider does not block results from other providers. Record every failed call, including errors that recovered after retry. State the error and its coverage impact in the review.
- Limits may depend on a shared network address or API key. Pacing cannot guarantee that a provider accepts every request.

Provider order is not a global relevance ranking. Use the records as discovery aids. Judge relevance and evidence from the papers. Check current provider documentation when API behavior changes.
