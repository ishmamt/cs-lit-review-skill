"""MCP server for free scholarly metadata APIs."""

from __future__ import annotations

import asyncio
import email.utils
import json
import os
import random
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError

from mcp.server.fastmcp import FastMCP

SERVER = FastMCP("cs-lit-review")
DEFAULT_SOURCES = ["openalex", "semanticscholar", "dblp", "arxiv"]
MAX_LIMIT = 25
TIMEOUT_SECONDS = 20
USER_AGENT = "cs-lit-review-mcp/0.1 (scholarly metadata discovery)"
RETRY_LIMIT = 3
CACHE_TTL_SECONDS = 24 * 60 * 60
CACHE_MAX_ENTRIES = 512
PROVIDER_INTERVALS = {"dblp": 2.0, "arxiv": 3.0}
_provider_locks: dict[str, threading.Lock] = {}
_provider_next_request: dict[str, float] = {}
_provider_cooldown: dict[str, float] = {}
_response_cache: dict[tuple[str, str], tuple[float, Any]] = {}
_cache_lock = threading.Lock()


def _wait_for_provider(provider: str) -> None:
    lock = _provider_locks.setdefault(provider, threading.Lock())
    with lock:
        now = time.monotonic()
        wait_until = max(_provider_next_request.get(provider, 0), _provider_cooldown.get(provider, 0))
        if wait_until > now:
            time.sleep(wait_until - now)
        _provider_next_request[provider] = time.monotonic() + PROVIDER_INTERVALS.get(provider, 0.0)


def _retry_delay(error: HTTPError, attempt: int) -> float:
    retry_after = error.headers.get("Retry-After")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = email.utils.parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass
    return min(30.0, 2**attempt + random.uniform(0, 0.5))


def _request(provider: str, url: str, *, headers: dict[str, str] | None = None, xml: bool = False) -> Any:
    cache_key = (provider, url)
    now = time.monotonic()
    with _cache_lock:
        cached = _response_cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]
        if cached:
            del _response_cache[cache_key]

    request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    for attempt in range(RETRY_LIMIT):
        _wait_for_provider(provider)
        try:
            request = urllib.request.Request(url, headers=request_headers)
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                body = response.read()
            payload = ET.fromstring(body) if xml else json.loads(body.decode("utf-8"))
            with _cache_lock:
                expired = [key for key, (expires, _) in _response_cache.items() if expires <= time.monotonic()]
                for key in expired:
                    del _response_cache[key]
                if len(_response_cache) >= CACHE_MAX_ENTRIES:
                    oldest = min(_response_cache, key=lambda key: _response_cache[key][0])
                    del _response_cache[oldest]
                _response_cache[cache_key] = (time.monotonic() + CACHE_TTL_SECONDS, payload)
            return payload
        except HTTPError as error:
            if error.code != 429 and not 500 <= error.code < 600:
                raise
            delay = _retry_delay(error, attempt)
            if error.code == 429:
                _provider_cooldown[provider] = max(_provider_cooldown.get(provider, 0), time.monotonic() + delay)
            else:
                time.sleep(delay)
            if attempt + 1 >= RETRY_LIMIT:
                raise
        except (TimeoutError, URLError):
            if attempt + 1 >= RETRY_LIMIT:
                raise
            time.sleep(min(30.0, 2**attempt + random.uniform(0, 0.5)))
    raise RuntimeError(f"request retries exhausted for {provider}")


def _get_json(url: str, *, headers: dict[str, str] | None = None) -> Any:
    provider = urllib.parse.urlparse(url).hostname or "unknown"
    provider = {"api.openalex.org": "openalex", "api.semanticscholar.org": "semanticscholar", "dblp.org": "dblp"}.get(provider, provider)
    return _request(provider, url, headers=headers)


def _get_xml(url: str) -> ET.Element:
    return _request("arxiv", url, xml=True)


def _abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str | None:
    if not index:
        return None
    words: list[str | None] = [None] * (max(pos for positions in index.values() for pos in positions) + 1)
    for word, positions in index.items():
        for position in positions:
            words[position] = word
    return " ".join(word for word in words if word)


def _normalize_openalex(item: dict[str, Any], query: str) -> dict[str, Any]:
    authorships = item.get("authorships") or []
    primary = item.get("primary_location") or {}
    source = primary.get("source") or {}
    ids = item.get("ids") or {}
    doi = item.get("doi")
    return {
        "title": item.get("title"),
        "authors": [a.get("author", {}).get("display_name") for a in authorships if a.get("author")],
        "year": item.get("publication_year"),
        "venue": source.get("display_name"),
        "publication_type": item.get("type"),
        "abstract": _abstract_from_inverted_index(item.get("abstract_inverted_index")),
        "doi": doi or ids.get("doi"),
        "arxiv_id": ids.get("arxiv"),
        "dblp_key": None,
        "provider_ids": {"openalex": item.get("id")},
        "url": item.get("primary_location", {}).get("landing_page_url") or item.get("id"),
        "citation_count": item.get("cited_by_count"),
        "query": query,
        "source": "openalex",
    }


def _search_openalex(query: str, limit: int) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"search": query, "per_page": limit})
    payload = _get_json(f"https://api.openalex.org/works?{params}")
    return [_normalize_openalex(item, query) for item in payload.get("results", [])]


def _normalize_semanticscholar(item: dict[str, Any], query: str) -> dict[str, Any]:
    external = item.get("externalIds") or {}
    paper_id = item.get("paperId")
    return {
        "title": item.get("title"),
        "authors": [a.get("name") for a in item.get("authors", []) if a.get("name")],
        "year": item.get("year"),
        "venue": item.get("venue"),
        "publication_type": ", ".join(item.get("publicationTypes") or []) or None,
        "abstract": item.get("abstract"),
        "doi": external.get("DOI"),
        "arxiv_id": external.get("ArXiv"),
        "dblp_key": external.get("DBLP"),
        "provider_ids": {"semanticscholar": paper_id},
        "url": item.get("url"),
        "citation_count": item.get("citationCount"),
        "query": query,
        "source": "semanticscholar",
    }


def _search_semanticscholar(query: str, limit: int) -> list[dict[str, Any]]:
    fields = "title,year,authors,venue,publicationTypes,abstract,externalIds,url,citationCount"
    params = urllib.parse.urlencode({"query": query, "limit": limit, "fields": fields})
    headers = {"x-api-key": os.environ["SEMANTIC_SCHOLAR_API_KEY"]} if os.environ.get("SEMANTIC_SCHOLAR_API_KEY") else None
    payload = _get_json(f"https://api.semanticscholar.org/graph/v1/paper/search?{params}", headers=headers)
    return [_normalize_semanticscholar(item, query) for item in payload.get("data", [])]


def _search_dblp(query: str, limit: int) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"q": query, "format": "json", "h": limit, "f": 0})
    payload = _get_json(f"https://dblp.org/search/publ/api?{params}")
    hits = payload.get("result", {}).get("hits", {}).get("hit", [])
    if isinstance(hits, dict):
        hits = [hits]
    records: list[dict[str, Any]] = []
    for hit in hits:
        info = hit.get("info") or {}
        authors = info.get("authors", {}).get("author", [])
        if isinstance(authors, str):
            authors = [authors]
        elif isinstance(authors, dict):
            authors = [authors]
        records.append({
            "title": info.get("title"),
            "authors": [a.get("text", "") if isinstance(a, dict) else a for a in authors],
            "year": int(info["year"]) if str(info.get("year", "")).isdigit() else None,
            "venue": info.get("venue"),
            "publication_type": info.get("type"),
            "abstract": None,
            "doi": info.get("doi"),
            "arxiv_id": None,
            "dblp_key": info.get("key"),
            "provider_ids": {"dblp": info.get("key")},
            "url": info.get("url"),
            "citation_count": None,
            "query": query,
            "source": "dblp",
        })
    return records


def _search_arxiv(query: str, limit: int) -> list[dict[str, Any]]:
    search_query = f"all:{query}"
    params = urllib.parse.urlencode({"search_query": search_query, "start": 0, "max_results": limit})
    root = _get_xml(f"https://export.arxiv.org/api/query?{params}")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    records: list[dict[str, Any]] = []
    for entry in root.findall("a:entry", ns):
        records.append(_normalize_arxiv_entry(entry, query, ns))
    return records


def _normalize_arxiv_entry(entry: ET.Element, query: str, ns: dict[str, str]) -> dict[str, Any]:
    link = entry.find("a:id", ns)
    url = link.text if link is not None else None
    arxiv_id = url.rsplit("/", 1)[-1] if url else None
    authors = [node.findtext("a:name", namespaces=ns) for node in entry.findall("a:author", ns)]
    categories = [node.get("term") for node in entry.findall("a:category", ns) if node.get("term")]
    published = entry.findtext("a:published", namespaces=ns)
    return {
        "title": " ".join((entry.findtext("a:title", namespaces=ns) or "").split()),
        "authors": authors,
        "year": int(published[:4]) if published and published[:4].isdigit() else None,
        "venue": None,
        "publication_type": "preprint",
        "abstract": " ".join((entry.findtext("a:summary", namespaces=ns) or "").split()),
        "doi": entry.findtext("a:doi", namespaces=ns),
        "arxiv_id": arxiv_id,
        "dblp_key": None,
        "provider_ids": {"arxiv": arxiv_id, "categories": categories},
        "url": url,
        "citation_count": None,
        "query": query,
        "source": "arxiv",
    }


SEARCHERS = {
    "openalex": _search_openalex,
    "semanticscholar": _search_semanticscholar,
    "dblp": _search_dblp,
    "arxiv": _search_arxiv,
}


def _parse_identifier(identifier: str) -> tuple[str, str]:
    value = identifier.strip()
    if not value:
        raise ValueError("identifier must not be empty")
    if re.fullmatch(r"10\.\d{4,9}/\S+", value, re.IGNORECASE):
        return "doi", value
    arxiv = re.search(r"(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:\.pdf)?$", value, re.IGNORECASE)
    if arxiv:
        return "arxiv", arxiv.group(1)
    return "provider", value


@SERVER.tool()
async def search_papers(
    query: str,
    sources: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    limit_per_source: int = 10,
) -> dict[str, Any]:
    """Search free scholarly APIs and return normalized records with provenance."""
    if not query.strip():
        raise ValueError("query must not be empty")
    selected = sources or DEFAULT_SOURCES
    unknown = sorted(set(selected) - set(SEARCHERS))
    if unknown:
        raise ValueError(f"unsupported sources: {', '.join(unknown)}")
    limit = max(1, min(int(limit_per_source), MAX_LIMIT))
    results = await asyncio.gather(*(
        asyncio.to_thread(SEARCHERS[source], query.strip(), limit) for source in selected
    ), return_exceptions=True)
    provider_results: dict[str, Any] = {}
    all_records: list[dict[str, Any]] = []
    for source, result in zip(selected, results):
        if isinstance(result, BaseException):
            provider_results[source] = {"error": f"{type(result).__name__}: {result}", "records": []}
            continue
        records = result
        if year_from is not None:
            records = [r for r in records if r.get("year") is None or r["year"] >= year_from]
        if year_to is not None:
            records = [r for r in records if r.get("year") is None or r["year"] <= year_to]
        provider_results[source] = {"records": records}
        all_records.extend(records)
    return {
        "query": query,
        "year_from": year_from,
        "year_to": year_to,
        "provider_results": provider_results,
        "records": all_records,
        "note": "Provider rankings are separate. Results are not deduplicated or globally ranked.",
    }


@SERVER.tool()
async def get_paper(identifier: str) -> dict[str, Any]:
    """Look up a paper by DOI or arXiv identifier."""
    kind, value = _parse_identifier(identifier)
    if kind == "doi":
        encoded = urllib.parse.quote(value, safe="")
        payload = await asyncio.to_thread(_get_json, f"https://api.openalex.org/works/https://doi.org/{encoded}")
        return _normalize_openalex(payload, f"DOI:{value}")
    if kind == "arxiv":
        query = urllib.parse.urlencode({"id_list": value, "max_results": 1})
        root = await asyncio.to_thread(_get_xml, f"https://export.arxiv.org/api/query?{query}")
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entry = root.find("a:entry", ns)
        if entry is None:
            return {"identifier": value, "error": "No arXiv record found"}
        return _normalize_arxiv_entry(entry, f"arXiv:{value}", ns)
    raise ValueError("Use a DOI or arXiv identifier. Other provider identifiers are not supported by get_paper yet.")


async def _semantic_scholar_graph(paper_id: str, relation: str, limit: int) -> dict[str, Any]:
    fields = "title,year,authors,venue,externalIds,url,citationCount"
    params = urllib.parse.urlencode({"fields": fields, "limit": max(1, min(limit, MAX_LIMIT))})
    url = f"https://api.semanticscholar.org/graph/v1/paper/{urllib.parse.quote(paper_id, safe='')}/{relation}?{params}"
    headers = {"x-api-key": os.environ["SEMANTIC_SCHOLAR_API_KEY"]} if os.environ.get("SEMANTIC_SCHOLAR_API_KEY") else None
    payload = await asyncio.to_thread(_get_json, url, headers=headers)
    papers = payload.get("data", [])
    return {
        "paper_id": paper_id,
        "relation": relation,
        "records": [_normalize_semanticscholar(row.get("citingPaper") or row.get("citedPaper") or {}, f"{relation}:{paper_id}") for row in papers],
        "source": "semanticscholar",
    }


@SERVER.tool()
async def get_citations(paper_id: str, limit: int = 20) -> dict[str, Any]:
    """Get papers that cite a Semantic Scholar paper ID or DOI."""
    return await _semantic_scholar_graph(paper_id, "citations", limit)


@SERVER.tool()
async def get_references(paper_id: str, limit: int = 20) -> dict[str, Any]:
    """Get references listed for a Semantic Scholar paper ID or DOI."""
    return await _semantic_scholar_graph(paper_id, "references", limit)


def main() -> None:
    SERVER.run(transport="stdio")


if __name__ == "__main__":
    main()
