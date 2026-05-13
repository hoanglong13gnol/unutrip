#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
Search or prepare source pages for UnuTrip / SmartTravel image pipeline.

Purpose:
- Read places exported by export_places_for_image_pipeline.py.
- Produce a source-pages CSV that collect_images_from_pages.py can crawl.
- Supports safe offline/source-url mode first.
- Supports optional Brave Search API, Bing Web Search API, and SerpAPI if API keys are available.
- Does NOT validate image URLs.
- Does NOT import or update database.

Why this script exists:
- validate_image_urls.py checks direct image URLs.
- collect_images_from_pages.py extracts images from known source_page_url.
- This script prepares/discovers those source_page_url rows.

Input columns expected:
rag_place_id,name,province,area,short_description,category,source_url,aliases,image_query_1,image_query_2,image_query_3,avoid_note,existing_image_count,images_json

Output columns:
rag_place_id,place_name,province,area,source_page_url,source,search_query,search_rank,search_provider,search_title,search_snippet,candidate_status,need_human_check,note

Mode 1: source-url only, no API key needed
python .\scripts\search_collect_images.py ^
  --input .\data\image_pipeline\input\places_for_image_pipeline.csv ^
  --provider source_url

Mode 2: Brave Search API
set BRAVE_SEARCH_API_KEY=your_key_here
python .\scripts\search_collect_images.py ^
  --input .\data\image_pipeline\input\places_for_image_pipeline.csv ^
  --provider brave ^
  --max-results-per-query 5

Mode 3: Bing Web Search API
set BING_SEARCH_API_KEY=your_key_here
python .\scripts\search_collect_images.py ^
  --input .\data\image_pipeline\input\places_for_image_pipeline.csv ^
  --provider bing ^
  --max-results-per-query 5

Mode 4: SerpAPI Google Search
set SERPAPI_API_KEY=your_key_here
python .\scripts\search_collect_images.py ^
  --input .\data\image_pipeline\input\places_for_image_pipeline.csv ^
  --provider serpapi ^
  --max-results-per-query 5

Default output:
data\image_pipeline\input\source_pages_from_search.csv

Then run:
python .\scripts\collect_images_from_pages.py ^
  --input .\data\image_pipeline\input\source_pages_from_search.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import quote_plus, urlparse

try:
    import requests
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: requests\n"
        "Install it with:\n"
        "  pip install requests"
    ) from exc


OUTPUT_FIELDS = [
    "rag_place_id",
    "place_name",
    "province",
    "area",
    "source_page_url",
    "source",
    "search_query",
    "search_rank",
    "search_provider",
    "search_title",
    "search_snippet",
    "candidate_status",
    "need_human_check",
    "note",
]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 "
    "UnuTripSearchCollector/1.0"
)

BLOCKED_PAGE_HOSTS = {
    "google.com",
    "www.google.com",
    "images.google.com",
    "bing.com",
    "www.bing.com",
    "duckduckgo.com",
    "www.duckduckgo.com",
    "yahoo.com",
    "search.yahoo.com",
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "tiktok.com",
    "www.tiktok.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
}

BLOCKED_URL_KEYWORDS = (
    "/search?",
    "tbm=isch",
    "google.com/url?",
    "bing.com/ck/a",
    "login",
    "signin",
    "register",
)

PREFERRED_DOMAIN_KEYWORDS = (
    "vietnamtourism.gov.vn",
    "wikimedia.org",
    "wikipedia.org",
    "vnexpress.net",
    "mia.vn",
    "vinwonders.com",
    "traveloka.com",
    "ivivu.com",
    "dulich",
    "tourism",
    "baotang",
    "baovanhoa",
    "baoangiang",
    "angiang",
    "gov.vn",
)

QUERY_COLUMNS = ["image_query_1", "image_query_2", "image_query_3"]


@dataclass
class SearchResult:
    url: str
    title: str = ""
    snippet: str = ""
    rank: int = 0


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_csv_rows(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Input CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def write_csv(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, str]]) -> int:
    ensure_parent_dir(path)
    count = 0

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1

    return count


def get_first_existing(row: Dict[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = clean_text(row.get(name, ""))
        if value:
            return value
    return ""


def normalize_url(url: str) -> str:
    url = clean_text(url)
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    return url.split("#", 1)[0].strip()


def host_matches(host: str, domain: str) -> bool:
    host = host.lower().strip(".")
    domain = domain.lower().strip(".")
    return host == domain or host.endswith("." + domain)


def url_is_allowed_source_page(url: str) -> bool:
    url = normalize_url(url)
    if not url:
        return False

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False

    host = parsed.netloc.lower()
    lower = url.lower()

    if any(host_matches(host, blocked) for blocked in BLOCKED_PAGE_HOSTS):
        return False

    if any(keyword in lower for keyword in BLOCKED_URL_KEYWORDS):
        return False

    return True


def infer_source_name(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def build_queries(row: Dict[str, str], include_site_queries: bool) -> List[str]:
    queries: List[str] = []

    for col in QUERY_COLUMNS:
        value = clean_text(row.get(col, ""))
        if value and value not in queries:
            queries.append(value)

    name = get_first_existing(row, ["name", "place_name", "title"])
    province = clean_text(row.get("province", ""))
    area = clean_text(row.get("area", ""))

    if name:
        fallback_queries = [
            f"{name} {area} {province} ảnh",
            f"{name} {area} {province} hình ảnh",
            f"{name} {province} du lịch",
        ]
        for query in fallback_queries:
            query = re.sub(r"\s+", " ", query).strip()
            if query and query not in queries:
                queries.append(query)

    if include_site_queries and name:
        domains = [
            "vietnamtourism.gov.vn",
            "wikimedia.org",
            "vnexpress.net",
            "mia.vn",
            "vinwonders.com",
        ]
        for domain in domains:
            query = f"{name} {province} site:{domain}"
            query = re.sub(r"\s+", " ", query).strip()
            if query and query not in queries:
                queries.append(query)

    return queries


def score_source_result(row: Dict[str, str], result: SearchResult) -> int:
    name = get_first_existing(row, ["name", "place_name", "title"]).lower()
    province = clean_text(row.get("province", "")).lower()
    area = clean_text(row.get("area", "")).lower()

    haystack = f"{result.url} {result.title} {result.snippet}".lower()
    host = urlparse(result.url).netloc.lower()

    score = 0

    if name and name in haystack:
        score += 5
    if province and province in haystack:
        score += 2
    if area and area in haystack:
        score += 2

    if any(keyword in host or keyword in result.url.lower() for keyword in PREFERRED_DOMAIN_KEYWORDS):
        score += 2

    # Prefer article/detail pages over generic home/category/search pages.
    path = urlparse(result.url).path.lower()
    if len(path.strip("/").split("/")) >= 2:
        score += 1
    if "category" in path or "tag" in path:
        score -= 1

    return score


def create_output_row(
    place_row: Dict[str, str],
    source_page_url: str,
    source: str,
    search_query: str,
    search_rank: int,
    provider: str,
    title: str,
    snippet: str,
    note: str,
) -> Dict[str, str]:
    return {
        "rag_place_id": get_first_existing(place_row, ["rag_place_id", "id", "place_id"]),
        "place_name": get_first_existing(place_row, ["name", "place_name", "title"]),
        "province": clean_text(place_row.get("province", "")),
        "area": clean_text(place_row.get("area", "")),
        "source_page_url": normalize_url(source_page_url),
        "source": source or infer_source_name(source_page_url),
        "search_query": search_query,
        "search_rank": str(search_rank),
        "search_provider": provider,
        "search_title": title,
        "search_snippet": snippet,
        "candidate_status": "raw",
        "need_human_check": "1",
        "note": note,
    }


def source_url_mode(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    output_rows: List[Dict[str, str]] = []
    seen = set()

    for row in rows:
        source_url = get_first_existing(row, ["source_page_url", "source_url", "url", "page_url"])
        source_url = normalize_url(source_url)

        if not url_is_allowed_source_page(source_url):
            continue

        key = (
            get_first_existing(row, ["rag_place_id", "id", "place_id"]),
            source_url.lower(),
        )
        if key in seen:
            continue
        seen.add(key)

        output_rows.append(
            create_output_row(
                place_row=row,
                source_page_url=source_url,
                source=infer_source_name(source_url),
                search_query="source_url_from_db",
                search_rank=1,
                provider="source_url",
                title="",
                snippet="",
                note="source_url exported from database; may be generic and should be scored later",
            )
        )

    return output_rows


def request_json(
    session: requests.Session,
    url: str,
    headers: Dict[str, str],
    params: Dict[str, Any],
    timeout: float,
) -> Dict[str, Any]:
    response = session.get(url, headers=headers, params=params, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
    return response.json()


def brave_search(
    session: requests.Session,
    query: str,
    api_key: str,
    max_results: int,
    timeout: float,
) -> List[SearchResult]:
    # Do not send country="VN" here. Brave Search API only accepts a fixed enum
    # of country codes and may reject unsupported values with HTTP 422.
    # Vietnamese queries still work without country, using search_lang="vi".
    data = request_json(
        session=session,
        url="https://api.search.brave.com/res/v1/web/search",
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
            "User-Agent": DEFAULT_USER_AGENT,
        },
        params={
            "q": query,
            "count": max_results,
            "search_lang": "vi",
            "safesearch": "moderate",
        },
        timeout=timeout,
    )

    results: List[SearchResult] = []
    web_results = data.get("web", {}).get("results", []) or []

    for index, item in enumerate(web_results[:max_results], start=1):
        url = normalize_url(item.get("url", ""))
        if not url_is_allowed_source_page(url):
            continue
        results.append(
            SearchResult(
                url=url,
                title=clean_text(item.get("title", "")),
                snippet=clean_text(item.get("description", "")),
                rank=index,
            )
        )

    return results


def bing_search(
    session: requests.Session,
    query: str,
    api_key: str,
    max_results: int,
    timeout: float,
) -> List[SearchResult]:
    data = request_json(
        session=session,
        url="https://api.bing.microsoft.com/v7.0/search",
        headers={
            "Ocp-Apim-Subscription-Key": api_key,
            "User-Agent": DEFAULT_USER_AGENT,
        },
        params={
            "q": query,
            "count": max_results,
            "mkt": "vi-VN",
            "safeSearch": "Moderate",
            "responseFilter": "Webpages",
        },
        timeout=timeout,
    )

    results: List[SearchResult] = []
    web_results = data.get("webPages", {}).get("value", []) or []

    for index, item in enumerate(web_results[:max_results], start=1):
        url = normalize_url(item.get("url", ""))
        if not url_is_allowed_source_page(url):
            continue
        results.append(
            SearchResult(
                url=url,
                title=clean_text(item.get("name", "")),
                snippet=clean_text(item.get("snippet", "")),
                rank=index,
            )
        )

    return results


def serpapi_search(
    session: requests.Session,
    query: str,
    api_key: str,
    max_results: int,
    timeout: float,
) -> List[SearchResult]:
    data = request_json(
        session=session,
        url="https://serpapi.com/search.json",
        headers={"User-Agent": DEFAULT_USER_AGENT},
        params={
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "google_domain": "google.com.vn",
            "gl": "vn",
            "hl": "vi",
            "num": max_results,
            "safe": "active",
        },
        timeout=timeout,
    )

    results: List[SearchResult] = []
    organic_results = data.get("organic_results", []) or []

    for index, item in enumerate(organic_results[:max_results], start=1):
        url = normalize_url(item.get("link", ""))
        if not url_is_allowed_source_page(url):
            continue
        results.append(
            SearchResult(
                url=url,
                title=clean_text(item.get("title", "")),
                snippet=clean_text(item.get("snippet", "")),
                rank=index,
            )
        )

    return results


def search_provider_results(
    session: requests.Session,
    provider: str,
    query: str,
    api_key: str,
    max_results: int,
    timeout: float,
) -> List[SearchResult]:
    if provider == "brave":
        return brave_search(session, query, api_key, max_results, timeout)
    if provider == "bing":
        return bing_search(session, query, api_key, max_results, timeout)
    if provider == "serpapi":
        return serpapi_search(session, query, api_key, max_results, timeout)
    raise ValueError(f"Unsupported search provider: {provider}")


def get_api_key(provider: str, explicit_key: str) -> str:
    if explicit_key:
        return explicit_key
    if provider == "brave":
        return os.environ.get("BRAVE_SEARCH_API_KEY", "")
    if provider == "bing":
        return os.environ.get("BING_SEARCH_API_KEY", "")
    if provider == "serpapi":
        return os.environ.get("SERPAPI_API_KEY", "")
    return ""


def api_search_mode(
    rows: List[Dict[str, str]],
    provider: str,
    api_key: str,
    max_queries_per_place: int,
    max_results_per_query: int,
    max_source_pages_per_place: int,
    timeout: float,
    sleep: float,
    include_site_queries: bool,
) -> List[Dict[str, str]]:
    if not api_key:
        raise RuntimeError(
            f"Missing API key for provider={provider}. "
            f"Use --api-key or set the corresponding environment variable."
        )

    session = requests.Session()
    output_rows: List[Dict[str, str]] = []
    global_seen: Set[Tuple[str, str]] = set()

    for place_index, row in enumerate(rows, start=1):
        rag_place_id = get_first_existing(row, ["rag_place_id", "id", "place_id"])
        place_name = get_first_existing(row, ["name", "place_name", "title"])
        queries = build_queries(row, include_site_queries=include_site_queries)[:max_queries_per_place]

        place_candidates: List[Tuple[int, str, SearchResult]] = []

        print(f"[{place_index}/{len(rows)}] Searching {rag_place_id} {place_name} | queries={len(queries)}")

        for query_index, query in enumerate(queries, start=1):
            try:
                results = search_provider_results(
                    session=session,
                    provider=provider,
                    query=query,
                    api_key=api_key,
                    max_results=max_results_per_query,
                    timeout=timeout,
                )
            except Exception as exc:
                print(f"  query failed: {query} | {exc}")
                if sleep > 0:
                    time.sleep(sleep)
                continue

            print(f"  query {query_index}: results={len(results)} | {query}")

            for result in results:
                score = score_source_result(row, result)
                place_candidates.append((score, query, result))

            if sleep > 0:
                time.sleep(sleep)

        place_candidates.sort(key=lambda item: (-item[0], item[2].rank, item[2].url))

        kept = 0
        for score, query, result in place_candidates:
            key = (rag_place_id, result.url.lower())
            if key in global_seen:
                continue
            global_seen.add(key)

            kept += 1
            output_rows.append(
                create_output_row(
                    place_row=row,
                    source_page_url=result.url,
                    source=infer_source_name(result.url),
                    search_query=query,
                    search_rank=result.rank,
                    provider=provider,
                    title=result.title,
                    snippet=result.snippet,
                    note=f"search_score={score}",
                )
            )

            if kept >= max_source_pages_per_place:
                break

        print(f"  kept source pages: {kept}")

    return output_rows


def default_output_path(project_root: Path) -> Path:
    return project_root / "data" / "image_pipeline" / "input" / "source_pages_from_search.csv"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare/search source pages for image collection pipeline."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Input places CSV from export_places_for_image_pipeline.py.",
    )

    parser.add_argument(
        "--output",
        default="",
        help="Output source pages CSV. Default: data/image_pipeline/input/source_pages_from_search.csv",
    )

    parser.add_argument(
        "--provider",
        choices=["source_url", "brave", "bing", "serpapi"],
        default="source_url",
        help="Source page provider. Default: source_url, no API key needed.",
    )

    parser.add_argument(
        "--api-key",
        default="",
        help="Search API key. If omitted, uses provider-specific environment variable.",
    )

    parser.add_argument(
        "--max-queries-per-place",
        type=int,
        default=3,
        help="Max queries per place for API search. Default: 3",
    )

    parser.add_argument(
        "--max-results-per-query",
        type=int,
        default=5,
        help="Max raw search results per query. Default: 5",
    )

    parser.add_argument(
        "--max-source-pages-per-place",
        type=int,
        default=5,
        help="Max source pages kept per place. Default: 5",
    )

    parser.add_argument(
        "--include-site-queries",
        action="store_true",
        help="Add site: queries for preferred domains. Useful with real search APIs.",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout seconds for API calls. Default: 20",
    )

    parser.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        help="Sleep seconds between API calls. Default: 0.5",
    )

    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root. Default: current directory.",
    )

    return parser.parse_args(argv)


def resolve_path(path_text: str, project_root: Path) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return path


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    project_root = Path(args.project_root).resolve()
    input_path = resolve_path(args.input, project_root)
    output_path = resolve_path(args.output, project_root) if args.output else default_output_path(project_root)

    _, rows = read_csv_rows(input_path)

    print(f"Input: {input_path}")
    print(f"Rows: {len(rows)}")
    print(f"Provider: {args.provider}")
    print(f"Output: {output_path}")

    if args.provider == "source_url":
        output_rows = source_url_mode(rows)
    else:
        api_key = get_api_key(args.provider, args.api_key)
        output_rows = api_search_mode(
            rows=rows,
            provider=args.provider,
            api_key=api_key,
            max_queries_per_place=args.max_queries_per_place,
            max_results_per_query=args.max_results_per_query,
            max_source_pages_per_place=args.max_source_pages_per_place,
            timeout=args.timeout,
            sleep=args.sleep,
            include_site_queries=args.include_site_queries,
        )

    written = write_csv(output_path, OUTPUT_FIELDS, output_rows)

    print()
    print("Done.")
    print(f"Source page rows written: {written}")
    print(f"Output file: {output_path}")

    if args.provider == "source_url":
        print()
        print("Note: provider=source_url only reuses source_url from DB. Some URLs may be generic province/source pages.")
        print("For better coverage, use provider=brave, bing, or serpapi with an API key later.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        print("Cancelled by user.", file=sys.stderr)
        raise SystemExit(130)
