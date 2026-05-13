#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
Discover source pages from free website sitemaps, no paid search API.

Purpose:
- Read places_for_image_pipeline.csv.
- Fetch sitemap URLs from known travel/news/tourism domains.
- Score sitemap page URLs against place names/province/area.
- Output source_pages_from_sitemaps.csv compatible with collect_images_from_pages.py.
- Does NOT use Brave/Bing/SerpAPI.
- Does NOT validate image URLs.
- Does NOT import/update database.

Why:
- Paid search API is too expensive for thousands of destinations.
- Wikidata/Wikipedia/Commons coverage is weak for many local Vietnam places.
- Many useful pages already exist on domains like vinwonders.com, mia.vn, ivivu.com,
  traveloka.com, vnexpress.net, dulichviet.com.vn, luhanhvietnam.com.vn, etc.
- Sitemaps are public and free to crawl politely.

Typical command:
python .\scripts\discover_source_pages_from_sitemaps.py ^
  --input .\data\image_pipeline\input\places_for_image_pipeline.csv ^
  --max-source-pages-per-place 5

Then:
python .\scripts\collect_images_from_pages.py ^
  --input .\data\image_pipeline\input\source_pages_from_sitemaps.csv ^
  --output .\data\image_pipeline\raw\sitemap_pages_raw.csv ^
  --timeout 8 ^
  --retries 0

Then validate/score/report/promote as usual.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import urljoin, urlparse

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
    "UnuTripSitemapDiscoverer/1.0"
)

DEFAULT_DOMAINS = [
    "vinwonders.com",
    "mia.vn",
    "ivivu.com",
    "traveloka.com",
    "vnexpress.net",
    "dulichviet.com.vn",
    "luhanhvietnam.com.vn",
    "vietravel.com",
    "dailytravelvietnam.com",
    "thamhiemmekong.com",
    "tcdulichtphcm.vn",
    "dantocmiennui.baotintuc.vn",
    "thanhnien.vn",
    "tuoitre.vn",
    "baotintuc.vn",
    "vietnamplus.vn",
    "vietnamtourism.gov.vn",
    "xanhsm.com",
]

SITEMAP_CANDIDATES = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
    "/post-sitemap.xml",
    "/page-sitemap.xml",
    "/news-sitemap.xml",
    "/sitemap-news.xml",
    "/vi/sitemap.xml",
    "/vn-vi/sitemap.xml",
]

GOOD_PATH_HINTS = (
    "du-lich",
    "dulich",
    "travel",
    "destination",
    "diem-den",
    "kham-pha",
    "explore",
    "wonderpedia",
    "news",
    "tin-tuc",
    "cam-nang",
    "blog",
    "dia-diem",
    "di-tich",
    "chua",
    "nui",
    "ho-",
    "thac",
    "rung",
    "lang",
    "cho-",
)

BAD_PATH_HINTS = (
    "tag/",
    "category/",
    "author/",
    "wp-content",
    "login",
    "register",
    "cart",
    "checkout",
    "search",
    "tim-kiem",
    "video",
    "podcast",
    "rss",
    "feed",
    "wp-json",
)

WEAK_TOKENS = {
    "khu",
    "du",
    "lich",
    "di",
    "tich",
    "van",
    "hoa",
    "nui",
    "chua",
    "ho",
    "song",
    "suoi",
    "thac",
    "lang",
    "cho",
    "cong",
    "vien",
    "trung",
    "tam",
    "an",
    "binh",
    "duong",
    "dong",
    "nai",
    "vung",
    "tau",
    "ha",
    "noi",
    "tp",
    "hcm",
}


@dataclass
class PageCandidate:
    url: str
    source: str
    score: int
    reasons: List[str]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def strip_accents(value: str) -> str:
    value = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in value if unicodedata.category(ch) != "Mn")


def normalize_for_match(value: str) -> str:
    value = strip_accents(clean_text(value)).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def slug_text(value: str) -> str:
    return normalize_for_match(value).replace(" ", "-")


def tokens(value: str) -> List[str]:
    return [token for token in normalize_for_match(value).split() if token]


def meaningful_tokens(value: str) -> List[str]:
    raw = tokens(value)
    strong = [token for token in raw if len(token) > 1 and token not in WEAK_TOKENS]
    return strong or raw


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


def place_name(row: Dict[str, str]) -> str:
    return get_first_existing(row, ["name", "place_name", "title"])


def rag_place_id(row: Dict[str, str]) -> str:
    return get_first_existing(row, ["rag_place_id", "id", "place_id"])


def province(row: Dict[str, str]) -> str:
    return clean_text(row.get("province", ""))


def area(row: Dict[str, str]) -> str:
    return clean_text(row.get("area", ""))


def normalize_url(url: str) -> str:
    url = clean_text(url)
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    return url.split("#", 1)[0]


def source_name(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def allowed_page_url(url: str) -> bool:
    url = normalize_url(url)
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    lower = url.lower()
    if any(hint in lower for hint in BAD_PATH_HINTS):
        return False
    if re.search(r"\.(jpg|jpeg|png|webp|gif|svg|pdf|zip|mp4|mp3)(\?|$)", lower):
        return False
    return True


def fetch_text(session: requests.Session, url: str, timeout: float) -> Tuple[str, str]:
    headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/xml,text/xml,text/plain,text/html,*/*"}
    response = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}")
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
    raw = response.content
    if url.lower().endswith(".gz") or content_type in {"application/x-gzip", "application/gzip"}:
        raw = gzip.decompress(raw)
    text = raw.decode(response.encoding or "utf-8", errors="replace")
    return text, response.url


def parse_sitemap_xml(xml_text: str) -> Tuple[List[str], List[str]]:
    sitemap_urls: List[str] = []
    page_urls: List[str] = []

    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except Exception:
        # Fallback regex for malformed XML.
        locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", xml_text, flags=re.I | re.S)
        for loc in locs:
            loc = clean_text(loc)
            if loc.lower().endswith(".xml") or loc.lower().endswith(".xml.gz") or "sitemap" in loc.lower():
                sitemap_urls.append(loc)
            else:
                page_urls.append(loc)
        return sitemap_urls, page_urls

    for elem in root.iter():
        tag = elem.tag.split("}", 1)[-1].lower()
        if tag != "loc":
            continue
        loc = clean_text(elem.text or "")
        if not loc:
            continue
        lower = loc.lower()
        if lower.endswith(".xml") or lower.endswith(".xml.gz") or "sitemap" in lower:
            sitemap_urls.append(loc)
        else:
            page_urls.append(loc)

    return sitemap_urls, page_urls


def discover_sitemap_roots(domain: str) -> List[str]:
    domain = domain.strip().replace("https://", "").replace("http://", "").strip("/")
    roots = []
    for scheme in ["https", "http"]:
        base = f"{scheme}://{domain}"
        for path in SITEMAP_CANDIDATES:
            roots.append(base + path)
    return roots


def crawl_sitemaps_for_domain(
    session: requests.Session,
    domain: str,
    timeout: float,
    max_sitemaps: int,
    max_urls: int,
    sleep: float,
) -> List[str]:
    queue = discover_sitemap_roots(domain)
    seen_sitemaps: Set[str] = set()
    page_urls: List[str] = []
    seen_pages: Set[str] = set()

    while queue and len(seen_sitemaps) < max_sitemaps and len(page_urls) < max_urls:
        sitemap_url = queue.pop(0)
        sitemap_url = normalize_url(sitemap_url)
        if sitemap_url in seen_sitemaps:
            continue
        seen_sitemaps.add(sitemap_url)

        try:
            xml_text, final_url = fetch_text(session, sitemap_url, timeout)
        except Exception:
            continue

        child_sitemaps, child_pages = parse_sitemap_xml(xml_text)

        for child in child_sitemaps:
            child = normalize_url(child)
            if child and child not in seen_sitemaps and len(queue) < max_sitemaps * 2:
                queue.append(child)

        for page in child_pages:
            page = normalize_url(page)
            if not allowed_page_url(page):
                continue
            if domain.replace("www.", "") not in source_name(page):
                continue
            if page.lower() in seen_pages:
                continue
            seen_pages.add(page.lower())
            page_urls.append(page)
            if len(page_urls) >= max_urls:
                break

        if sleep > 0:
            time.sleep(sleep)

    return page_urls


def score_url_for_place(row: Dict[str, str], url: str) -> PageCandidate:
    name = place_name(row)
    prov = province(row)
    ar = area(row)
    url_norm = normalize_for_match(url)
    path_norm = normalize_for_match(urlparse(url).path)
    name_slug = slug_text(name)
    area_slug = slug_text(ar)
    province_slug = slug_text(prov)
    strong_tokens = meaningful_tokens(name)

    score = 0
    reasons: List[str] = []

    if name_slug and name_slug in url.lower():
        score += 12
        reasons.append("name_slug_match")

    hits = sum(1 for token in strong_tokens if token in path_norm)
    total = len(strong_tokens)
    if total:
        ratio = hits / total
        if ratio >= 0.8:
            score += 10
            reasons.append(f"strong_token_match:{hits}/{total}")
        elif ratio >= 0.6:
            score += 7
            reasons.append(f"partial_token_match:{hits}/{total}")
        elif hits > 0:
            score += 2
            reasons.append(f"weak_token_match:{hits}/{total}")

    if province_slug and province_slug in url.lower():
        score += 3
        reasons.append("province_slug_match")
    if area_slug and area_slug in url.lower():
        score += 3
        reasons.append("area_slug_match")

    lower = url.lower()
    if any(hint in lower for hint in GOOD_PATH_HINTS):
        score += 2
        reasons.append("good_path_hint")

    if any(hint in lower for hint in BAD_PATH_HINTS):
        score -= 5
        reasons.append("bad_path_hint")

    # Penalize overly generic province pages if no meaningful place tokens hit.
    if hits == 0 and province_slug and province_slug in lower:
        score -= 3
        reasons.append("province_only_penalty")

    return PageCandidate(url=url, source=source_name(url), score=score, reasons=reasons)


def build_domain_url_index(
    domains: List[str],
    timeout: float,
    max_sitemaps_per_domain: int,
    max_urls_per_domain: int,
    sleep: float,
) -> List[str]:
    session = requests.Session()
    all_urls: List[str] = []
    seen = set()

    for index, domain in enumerate(domains, start=1):
        print(f"[{index}/{len(domains)}] crawl sitemap domain={domain}")
        urls = crawl_sitemaps_for_domain(
            session=session,
            domain=domain,
            timeout=timeout,
            max_sitemaps=max_sitemaps_per_domain,
            max_urls=max_urls_per_domain,
            sleep=sleep,
        )
        kept = 0
        for url in urls:
            key = url.lower()
            if key in seen:
                continue
            seen.add(key)
            all_urls.append(url)
            kept += 1
        print(f"  urls={len(urls)} new={kept} total={len(all_urls)}")

    return all_urls


def output_row(place_row: Dict[str, str], candidate: PageCandidate, rank: int) -> Dict[str, str]:
    return {
        "rag_place_id": rag_place_id(place_row),
        "place_name": place_name(place_row),
        "province": province(place_row),
        "area": area(place_row),
        "source_page_url": candidate.url,
        "source": candidate.source,
        "search_query": "sitemap_url_match",
        "search_rank": str(rank),
        "search_provider": "free_sitemap",
        "search_title": "",
        "search_snippet": "",
        "candidate_status": "raw",
        "need_human_check": "1",
        "note": f"score={candidate.score}; reasons={';'.join(candidate.reasons)}",
    }


def match_places_to_urls(
    rows: List[Dict[str, str]],
    urls: List[str],
    max_source_pages_per_place: int,
    min_score: int,
) -> List[Dict[str, str]]:
    output_rows: List[Dict[str, str]] = []

    for index, row in enumerate(rows, start=1):
        scored: List[PageCandidate] = []
        for url in urls:
            candidate = score_url_for_place(row, url)
            if candidate.score >= min_score:
                scored.append(candidate)

        scored.sort(key=lambda c: (-c.score, c.source, c.url))
        kept = scored[:max_source_pages_per_place]

        print(f"[{index}/{len(rows)}] match {rag_place_id(row)} {place_name(row)} | kept={len(kept)}")
        for rank, candidate in enumerate(kept, start=1):
            output_rows.append(output_row(row, candidate, rank))

    return output_rows


def default_output_path(project_root: Path) -> Path:
    return project_root / "data" / "image_pipeline" / "input" / "source_pages_from_sitemaps.csv"


def default_cache_path(project_root: Path) -> Path:
    return project_root / "data" / "image_pipeline" / "cache" / "sitemap_url_index.csv"


def parse_domains(text: str) -> List[str]:
    if not text.strip():
        return list(DEFAULT_DOMAINS)
    domains = []
    for part in re.split(r"[,\n]+", text):
        part = part.strip()
        if part:
            domains.append(part)
    return domains


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover source pages from free public sitemaps.")

    parser.add_argument("--input", required=True, help="Input places CSV from export_places_for_image_pipeline.py.")
    parser.add_argument("--output", default="", help="Output source pages CSV. Default: data/image_pipeline/input/source_pages_from_sitemaps.csv")
    parser.add_argument("--project-root", default=".", help="Project root. Default: current directory.")
    parser.add_argument("--domains", default="", help="Comma-separated domains. Default: built-in travel/news domains.")
    parser.add_argument("--cache", default="", help="Sitemap URL cache CSV. Default: data/image_pipeline/cache/sitemap_url_index.csv")
    parser.add_argument("--use-cache", action="store_true", help="Use existing sitemap URL cache instead of crawling domains.")
    parser.add_argument("--timeout", type=float, default=12.0, help="HTTP timeout seconds. Default: 12")
    parser.add_argument("--sleep", type=float, default=0.05, help="Sleep between sitemap requests. Default: 0.05")
    parser.add_argument("--max-sitemaps-per-domain", type=int, default=60, help="Max sitemaps per domain. Default: 60")
    parser.add_argument("--max-urls-per-domain", type=int, default=20000, help="Max page URLs per domain. Default: 20000")
    parser.add_argument("--max-source-pages-per-place", type=int, default=5, help="Max source pages per place. Default: 5")
    parser.add_argument("--min-score", type=int, default=8, help="Min URL match score. Default: 8")

    return parser.parse_args(argv)


def resolve_path(path_text: str, project_root: Path) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return path


def read_url_cache(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Cache file not found: {path}")
    _, rows = read_csv_rows(path)
    urls = []
    for row in rows:
        url = clean_text(row.get("url", ""))
        if url:
            urls.append(url)
    return urls


def write_url_cache(path: Path, urls: List[str]) -> int:
    rows = [{"url": url, "source": source_name(url)} for url in urls]
    return write_csv(path, ["url", "source"], rows)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    project_root = Path(args.project_root).resolve()
    input_path = resolve_path(args.input, project_root)
    output_path = resolve_path(args.output, project_root) if args.output else default_output_path(project_root)
    cache_path = resolve_path(args.cache, project_root) if args.cache else default_cache_path(project_root)

    _, place_rows = read_csv_rows(input_path)
    domains = parse_domains(args.domains)

    print(f"Input: {input_path}")
    print(f"Rows: {len(place_rows)}")
    print(f"Output: {output_path}")
    print(f"Cache: {cache_path}")

    if args.use_cache:
        urls = read_url_cache(cache_path)
        print(f"Loaded URL cache: {len(urls)}")
    else:
        urls = build_domain_url_index(
            domains=domains,
            timeout=args.timeout,
            max_sitemaps_per_domain=args.max_sitemaps_per_domain,
            max_urls_per_domain=args.max_urls_per_domain,
            sleep=args.sleep,
        )
        write_url_cache(cache_path, urls)
        print(f"Wrote URL cache: {len(urls)} -> {cache_path}")

    output_rows = match_places_to_urls(
        rows=place_rows,
        urls=urls,
        max_source_pages_per_place=args.max_source_pages_per_place,
        min_score=args.min_score,
    )

    written = write_csv(output_path, OUTPUT_FIELDS, output_rows)

    print()
    print("Done.")
    print(f"Source page rows written: {written}")
    print(f"Output file: {output_path}")
    print()
    print("Next:")
    print(f"python .\\scripts\\collect_images_from_pages.py --input {output_path} --output .\\data\\image_pipeline\\raw\\sitemap_pages_raw.csv --timeout 8 --retries 0")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        print("Cancelled by user.", file=sys.stderr)
        raise SystemExit(130)
