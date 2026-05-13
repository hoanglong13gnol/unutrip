#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
Collect image candidates from source web pages for UnuTrip / SmartTravel.

Purpose:
- Read an input CSV containing place info and source_page_url or source_url.
- Fetch each source page.
- Extract image URLs from:
  - og:image
  - twitter:image
  - link rel="image_src"
  - img[src]
  - img[data-src], data-original, data-lazy-src, data-url
  - picture/source[srcset]
  - img[srcset]
  - JSON-LD image fields
- Normalize relative image URLs into absolute URLs.
- Write raw image candidates CSV.
- Do NOT validate image bytes here.
- Do NOT import or update database.

Example input columns:
rag_place_id,place_name,source_page_url,source

Also accepted aliases:
id,name,source_url

Example:
python .\scripts\collect_images_from_pages.py ^
  --input .\data\image_pipeline\input\source_pages_from_search.csv ^
  --output .\data\image_pipeline\raw\source_pages_from_search_raw.csv ^
  --timeout 8 ^
  --retries 0

Then validate output:
python .\scripts\validate_image_urls.py ^
  --input .\data\image_pipeline\raw\source_pages_from_search_raw.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote, unquote, urljoin, urlparse, urlunparse

try:
    import requests
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: requests\n"
        "Install it with:\n"
        "  pip install requests"
    ) from exc

try:
    from bs4 import BeautifulSoup
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: beautifulsoup4\n"
        "Install it with:\n"
        "  pip install beautifulsoup4"
    ) from exc


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 "
    "UnuTripImageCollector/1.1"
)

OUTPUT_FIELDS = [
    "rag_place_id",
    "place_name",
    "image_url",
    "source_page_url",
    "source",
    "credit",
    "license_note",
    "image_order",
    "is_primary",
    "batch_code",
    "provider",
    "confidence",
    "need_human_check",
    "candidate_status",
    "ai_note",
    "extract_method",
    "page_title",
    "alt_text",
    "collected_at",
]

IMAGE_ATTRS = [
    "src",
    "data-src",
    "data-original",
    "data-lazy-src",
    "data-url",
    "data-image",
    "data-img",
    "data-thumb",
]

COMMON_IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".avif",
)

BAD_IMAGE_SUBSTRINGS = (
    "base64,",
    "data:image/",
    "sprite",
    "logo",
    "icon",
    "favicon",
    "avatar",
    "placeholder",
    "loading",
    "wordmark",
    "commonswiki-wordmark",
    "wikimedia-button",
    "poweredby_mediawiki",
    "maps.wikimedia.org",
    "osm-intl",
    "blank.gif",
    "transparent.gif",
    "pixel.gif",
    "1x1",
    "ads/",
    "/ads",
    "doubleclick",
    "googlesyndication",
    "analytics",
    ".svg",
)

SEARCH_PAGE_HOSTS = {
    "google.com",
    "www.google.com",
    "images.google.com",
    "bing.com",
    "www.bing.com",
    "duckduckgo.com",
    "www.duckduckgo.com",
}


@dataclass
class PageFetchResult:
    ok: bool
    url: str
    status_code: str = ""
    content_type: str = ""
    html: str = ""
    fail_reason: str = ""


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_url(raw_url: str, base_url: str = "") -> str:
    if raw_url is None:
        return ""

    url = unescape(str(raw_url).strip())
    if not url:
        return ""

    url = url.replace("&amp;", "&")
    url = url.replace("\\/", "/")
    url = url.strip().strip('"').strip("'")

    if url.startswith("data:"):
        return url

    if base_url:
        url = urljoin(base_url, url)
    elif url.startswith("//"):
        url = "https:" + url

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return url

    safe_path = quote(unquote(parsed.path), safe="/%:@")
    safe_query = quote(unquote(parsed.query), safe="=&?/:,%+@;[]()!$'*")

    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            safe_path,
            parsed.params,
            safe_query,
            "",
        )
    )


def host_matches(host: str, domain: str) -> bool:
    host = host.lower().strip(".")
    domain = domain.lower().strip(".")
    return host == domain or host.endswith("." + domain)


def is_probably_bad_page_url(url: str) -> bool:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return True

    if not parsed.netloc:
        return True

    host = parsed.netloc.lower()
    path = parsed.path.lower()
    query = parsed.query.lower()

    if any(host_matches(host, domain) for domain in SEARCH_PAGE_HOSTS):
        if path.startswith("/search") or path.startswith("/images/search"):
            return True
        if "tbm=isch" in query:
            return True

    return False


def image_url_looks_useful(url: str) -> bool:
    if not url:
        return False

    lower = url.lower()

    if lower.startswith("data:"):
        return False

    if any(bad in lower for bad in BAD_IMAGE_SUBSTRINGS):
        return False

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return False

    if not parsed.netloc:
        return False

    path = parsed.path.lower()
    query = parsed.query.lower()

    if path.endswith(COMMON_IMAGE_EXTENSIONS):
        return True

    image_query_hints = (
        "format=jpg",
        "format=jpeg",
        "format=png",
        "format=webp",
        "type=jpg",
        "type=jpeg",
        "type=png",
        "type=webp",
        "w=",
        "width=",
        "h=",
        "height=",
        "fit=",
        "crop=",
    )

    if any(hint in query for hint in image_query_hints):
        return True

    cdn_hints = (
        "photo",
        "image",
        "img",
        "media",
        "cdn",
        "upload",
        "static",
        "vcdn",
    )

    if any(hint in lower for hint in cdn_hints):
        return True

    return False


def parse_srcset(srcset: str, base_url: str) -> List[str]:
    if not srcset:
        return []

    urls: List[str] = []

    for part in srcset.split(","):
        candidate = part.strip()
        if not candidate:
            continue

        url_part = candidate.split()[0].strip()

        if not (
            url_part.startswith("http://")
            or url_part.startswith("https://")
            or url_part.startswith("//")
            or url_part.startswith("/")
        ):
            continue

        normalized = normalize_url(url_part, base_url)
        if normalized and image_url_looks_useful(normalized):
            urls.append(normalized)

    return urls


def get_first_existing(row: Dict[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = clean_text(row.get(name, ""))
        if value:
            return value
    return ""


def read_csv_rows(input_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("Input CSV has no header")
        return list(reader.fieldnames), list(reader)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


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


def default_output_path(input_path: Path, project_root: Path) -> Path:
    stem = input_path.stem
    return project_root / "data" / "image_pipeline" / "raw" / f"{stem}_page_images_raw.csv"


def session_with_retries(max_retries: int) -> requests.Session:
    session = requests.Session()

    if max_retries <= 0:
        return session

    try:
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry = Retry(
            total=max_retries,
            connect=max_retries,
            read=max_retries,
            status=max_retries,
            backoff_factor=0.4,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

    except Exception:
        pass

    return session


def fetch_page(
    session: requests.Session,
    url: str,
    timeout: float,
    user_agent: str,
) -> PageFetchResult:
    normalized_url = normalize_url(url)

    if is_probably_bad_page_url(normalized_url):
        return PageFetchResult(
            ok=False,
            url=normalized_url,
            fail_reason="bad_or_search_page_url",
        )

    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }

    try:
        response = session.get(
            normalized_url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
        )

        status_code = str(response.status_code)
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        final_url = normalize_url(response.url or normalized_url)

        if response.status_code != 200:
            return PageFetchResult(
                ok=False,
                url=final_url,
                status_code=status_code,
                content_type=content_type,
                fail_reason=f"http_status_{response.status_code}",
            )

        if "html" not in content_type and content_type not in {"", "text/plain"}:
            return PageFetchResult(
                ok=False,
                url=final_url,
                status_code=status_code,
                content_type=content_type,
                fail_reason="content_type_not_html",
            )

        if not response.encoding:
            response.encoding = response.apparent_encoding or "utf-8"

        return PageFetchResult(
            ok=True,
            url=final_url,
            status_code=status_code,
            content_type=content_type,
            html=response.text,
        )

    except requests.exceptions.Timeout:
        return PageFetchResult(ok=False, url=normalized_url, fail_reason="timeout")

    except requests.exceptions.SSLError:
        return PageFetchResult(ok=False, url=normalized_url, fail_reason="ssl_error")

    except requests.exceptions.TooManyRedirects:
        return PageFetchResult(ok=False, url=normalized_url, fail_reason="too_many_redirects")

    except requests.exceptions.ConnectionError:
        return PageFetchResult(ok=False, url=normalized_url, fail_reason="connection_error")

    except requests.exceptions.RequestException as exc:
        return PageFetchResult(
            ok=False,
            url=normalized_url,
            fail_reason=exc.__class__.__name__.lower(),
        )

    except Exception as exc:
        return PageFetchResult(
            ok=False,
            url=normalized_url,
            fail_reason=f"unexpected_{exc.__class__.__name__.lower()}",
        )


def extract_jsonld_images_from_value(value: Any) -> List[str]:
    images: List[str] = []

    if value is None:
        return images

    if isinstance(value, str):
        if value.strip():
            images.append(value.strip())
        return images

    if isinstance(value, list):
        for item in value:
            images.extend(extract_jsonld_images_from_value(item))
        return images

    if isinstance(value, dict):
        for key in ("url", "contentUrl", "thumbnailUrl"):
            if key in value:
                images.extend(extract_jsonld_images_from_value(value.get(key)))

        if "image" in value:
            images.extend(extract_jsonld_images_from_value(value.get("image")))

        return images

    return images


def extract_jsonld_images(soup: BeautifulSoup, base_url: str) -> List[Tuple[str, str, str]]:
    results: List[Tuple[str, str, str]] = []
    scripts = soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)})

    for script in scripts:
        raw = script.string or script.get_text(" ", strip=True)

        if not raw:
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        values: List[Any]
        if isinstance(data, list):
            values = list(data)
        else:
            values = [data]

        index = 0
        while index < len(values):
            item = values[index]
            index += 1

            if isinstance(item, dict) and "@graph" in item and isinstance(item["@graph"], list):
                values.extend(item["@graph"])

            for img in extract_jsonld_images_from_value(item):
                normalized = normalize_url(img, base_url)
                if image_url_looks_useful(normalized):
                    results.append((normalized, "jsonld:image", ""))

    return results


def extract_images_from_html(html: str, page_url: str) -> Tuple[str, List[Tuple[str, str, str]]]:
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = clean_text(soup.title.string)

    results: List[Tuple[str, str, str]] = []

    meta_selectors = [
        ("property", "og:image", "meta:og:image"),
        ("property", "og:image:url", "meta:og:image:url"),
        ("property", "og:image:secure_url", "meta:og:image:secure_url"),
        ("name", "twitter:image", "meta:twitter:image"),
        ("name", "twitter:image:src", "meta:twitter:image:src"),
    ]

    for attr_name, attr_value, method in meta_selectors:
        for tag in soup.find_all("meta", attrs={attr_name: re.compile(f"^{re.escape(attr_value)}$", re.I)}):
            content = tag.get("content", "")
            normalized = normalize_url(content, page_url)
            if image_url_looks_useful(normalized):
                results.append((normalized, method, ""))

    for tag in soup.find_all("link"):
        rel_value = tag.get("rel", "")
        if isinstance(rel_value, list):
            rel = " ".join(rel_value)
        else:
            rel = clean_text(rel_value)

        if "image_src" in rel.lower():
            href = tag.get("href", "")
            normalized = normalize_url(href, page_url)
            if image_url_looks_useful(normalized):
                results.append((normalized, "link:image_src", ""))

    results.extend(extract_jsonld_images(soup, page_url))

    for img in soup.find_all("img"):
        alt_text = clean_text(img.get("alt", ""))

        for attr in IMAGE_ATTRS:
            value = img.get(attr, "")
            normalized = normalize_url(value, page_url)
            if image_url_looks_useful(normalized):
                results.append((normalized, f"img:{attr}", alt_text))

        srcset = img.get("srcset", "")
        for srcset_url in parse_srcset(srcset, page_url):
            results.append((srcset_url, "img:srcset", alt_text))

    for source in soup.find_all("source"):
        srcset = source.get("srcset", "")
        for srcset_url in parse_srcset(srcset, page_url):
            results.append((srcset_url, "source:srcset", ""))

    return title, results


def infer_source_name(source_page_url: str, explicit_source: str = "") -> str:
    if explicit_source:
        return explicit_source

    host = urlparse(source_page_url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def build_candidate_row(
    source_row: Dict[str, str],
    image_url: str,
    source_page_url: str,
    source: str,
    image_order: int,
    is_primary: int,
    batch_code: str,
    extract_method: str,
    page_title: str,
    alt_text: str,
    collected_at: str,
) -> Dict[str, str]:
    rag_place_id = get_first_existing(source_row, ["rag_place_id", "id", "place_id"])
    place_name = get_first_existing(source_row, ["place_name", "name", "title"])

    return {
        "rag_place_id": rag_place_id,
        "place_name": place_name,
        "image_url": image_url,
        "source_page_url": source_page_url,
        "source": source,
        "credit": "",
        "license_note": "",
        "image_order": str(image_order),
        "is_primary": str(is_primary),
        "batch_code": batch_code,
        "provider": "page_crawler",
        "confidence": "0.50",
        "need_human_check": "1",
        "candidate_status": "raw",
        "ai_note": "",
        "extract_method": extract_method,
        "page_title": page_title,
        "alt_text": alt_text,
        "collected_at": collected_at,
    }


def collect_from_rows(
    rows: List[Dict[str, str]],
    session: requests.Session,
    source_url_columns: Sequence[str],
    timeout: float,
    sleep: float,
    user_agent: str,
    max_images_per_page: int,
    batch_code: str,
    start_row: int,
    limit_rows: int,
) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    output_rows: List[Dict[str, str]] = []

    if start_row < 1:
        start_row = 1

    end_row = len(rows)
    if limit_rows > 0:
        end_row = min(len(rows), start_row + limit_rows - 1)

    selected_rows = rows[start_row - 1 : end_row]

    stats: Dict[str, int] = {
        "input_rows": len(rows),
        "selected_rows": len(selected_rows),
        "pages_ok": 0,
        "pages_failed": 0,
        "rows_missing_source_url": 0,
        "images_collected": 0,
        "duplicates_skipped": 0,
        "pages_with_0_images": 0,
        "page_parse_errors": 0,
    }

    collected_at = now_utc_iso()
    global_seen = set()

    for local_index, row in enumerate(selected_rows, start=1):
        absolute_index = start_row + local_index - 1
        source_page_url = get_first_existing(row, source_url_columns)

        if not source_page_url:
            stats["rows_missing_source_url"] += 1
            print(f"[{absolute_index}/{len(rows)}] missing source URL")
            continue

        fetch_result = fetch_page(
            session=session,
            url=source_page_url,
            timeout=timeout,
            user_agent=user_agent,
        )

        if not fetch_result.ok:
            stats["pages_failed"] += 1
            print(
                f"[{absolute_index}/{len(rows)}] FAILED {source_page_url} | "
                f"reason={fetch_result.fail_reason} status={fetch_result.status_code}"
            )

            if sleep > 0:
                time.sleep(sleep)

            continue

        try:
            page_title, images = extract_images_from_html(fetch_result.html, fetch_result.url)
        except Exception as exc:
            stats["page_parse_errors"] += 1
            stats["pages_failed"] += 1
            print(
                f"[{absolute_index}/{len(rows)}] FAILED {fetch_result.url} | "
                f"reason=parse_error_{exc.__class__.__name__.lower()}"
            )

            if sleep > 0:
                time.sleep(sleep)

            continue

        stats["pages_ok"] += 1

        source_name = infer_source_name(fetch_result.url, get_first_existing(row, ["source"]))
        local_seen = set()
        image_order = 0

        for image_url, extract_method, alt_text in images:
            key = image_url.lower()

            if key in local_seen or key in global_seen:
                stats["duplicates_skipped"] += 1
                continue

            local_seen.add(key)
            global_seen.add(key)
            image_order += 1

            candidate = build_candidate_row(
                source_row=row,
                image_url=image_url,
                source_page_url=fetch_result.url,
                source=source_name,
                image_order=image_order,
                is_primary=1 if image_order == 1 else 0,
                batch_code=batch_code,
                extract_method=extract_method,
                page_title=page_title,
                alt_text=alt_text,
                collected_at=collected_at,
            )

            output_rows.append(candidate)
            stats["images_collected"] += 1

            if image_order >= max_images_per_page:
                break

        if image_order == 0:
            stats["pages_with_0_images"] += 1

        print(
            f"[{absolute_index}/{len(rows)}] OK {fetch_result.url} | "
            f"found={len(images)} kept={image_order} title={page_title[:80]}"
        )

        if sleep > 0:
            time.sleep(sleep)

    return output_rows, stats


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect raw image candidates from source pages."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Input CSV containing source_page_url/source_url and place columns.",
    )

    parser.add_argument(
        "--output",
        default="",
        help="Output raw candidates CSV. Default: data/image_pipeline/raw/<input>_page_images_raw.csv",
    )

    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root. Default: current directory.",
    )

    parser.add_argument(
        "--source-url-columns",
        default="source_page_url,source_url,url,page_url",
        help="Comma-separated source URL column names, checked in order.",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=8.0,
        help="HTTP timeout in seconds. Default: 8",
    )

    parser.add_argument(
        "--retries",
        type=int,
        default=0,
        help="HTTP retry count. Default: 0",
    )

    parser.add_argument(
        "--sleep",
        type=float,
        default=0.1,
        help="Sleep seconds between pages. Default: 0.1",
    )

    parser.add_argument(
        "--max-images-per-page",
        type=int,
        default=30,
        help="Maximum image candidates kept per source page. Default: 30",
    )

    parser.add_argument(
        "--batch-code",
        default="page_collect",
        help="batch_code value for output rows. Default: page_collect",
    )

    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="HTTP User-Agent string.",
    )

    parser.add_argument(
        "--start-row",
        type=int,
        default=1,
        help="1-based input row to start from. Useful for retrying large batches. Default: 1",
    )

    parser.add_argument(
        "--limit-rows",
        type=int,
        default=0,
        help="Limit number of input rows to process. 0 means no limit. Default: 0",
    )

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    project_root = Path(args.project_root).resolve()

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = (project_root / input_path).resolve()

    output_path = Path(args.output) if args.output else default_output_path(input_path, project_root)
    if not output_path.is_absolute():
        output_path = (project_root / output_path).resolve()

    _, rows = read_csv_rows(input_path)

    source_url_columns = [
        col.strip()
        for col in args.source_url_columns.split(",")
        if col.strip()
    ]

    session = session_with_retries(args.retries)

    print(f"Input: {input_path}")
    print(f"Rows: {len(rows)}")
    print(f"Output: {output_path}")
    print(f"Start row: {args.start_row}")
    print(f"Limit rows: {args.limit_rows if args.limit_rows > 0 else 'all'}")
    print("Starting page image collection...")

    output_rows, stats = collect_from_rows(
        rows=rows,
        session=session,
        source_url_columns=source_url_columns,
        timeout=args.timeout,
        sleep=args.sleep,
        user_agent=args.user_agent,
        max_images_per_page=args.max_images_per_page,
        batch_code=args.batch_code,
        start_row=args.start_row,
        limit_rows=args.limit_rows,
    )

    written = write_csv(output_path, OUTPUT_FIELDS, output_rows)

    print()
    print("Done.")
    print(f"Input rows: {stats['input_rows']}")
    print(f"Selected rows: {stats['selected_rows']}")
    print(f"Pages OK: {stats['pages_ok']}")
    print(f"Pages failed: {stats['pages_failed']}")
    print(f"Rows missing source URL: {stats['rows_missing_source_url']}")
    print(f"Pages with 0 images: {stats['pages_with_0_images']}")
    print(f"Page parse errors: {stats['page_parse_errors']}")
    print(f"Images collected: {stats['images_collected']}")
    print(f"Duplicates skipped: {stats['duplicates_skipped']}")
    print(f"Output rows written: {written}")
    print(f"Output file: {output_path}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        print("Cancelled by user.", file=sys.stderr)
        raise SystemExit(130)