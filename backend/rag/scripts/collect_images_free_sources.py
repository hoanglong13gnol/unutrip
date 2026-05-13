#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
Collect image candidates from free public sources, no paid search API.

Purpose:
- Read places_for_image_pipeline.csv from export_places_for_image_pipeline.py.
- Query free/no-key sources:
  1. Wikidata search + P18 image property
  2. Vietnamese Wikipedia search + page images
  3. English Wikipedia search + page images
  4. Wikimedia Commons file search
- Write raw image candidates CSV compatible with validate_image_urls.py.
- Does NOT use Brave/Bing/SerpAPI.
- Does NOT import/update database.

Why:
- Paid search APIs are not cost-effective for 5,592 destinations.
- Wikidata/Wikipedia/Wikimedia Commons are free and often provide well-attributed direct image URLs.

Input expected:
data\image_pipeline\input\places_for_image_pipeline.csv

Command:
python .\scripts\collect_images_free_sources.py ^
  --input .\data\image_pipeline\input\places_for_image_pipeline.csv ^
  --max-images-per-place 8

Output default:
data\image_pipeline\raw\free_sources_raw.csv

Then run:
python .\scripts\validate_image_urls.py ^
  --input .\data\image_pipeline\raw\free_sources_raw.csv ^
  --timeout 8 ^
  --retries 0
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import quote, urlparse

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

USER_AGENT = "UnuTripFreeImageCollector/1.0 (graduation project; local data enrichment)"

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
VI_WIKI_API = "https://vi.wikipedia.org/w/api.php"
EN_WIKI_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_SPECIAL_FILE_PATH = "https://commons.wikimedia.org/wiki/Special:FilePath/"

BAD_FILE_HINTS = (
    "logo",
    "icon",
    "map",
    "locator",
    "flag",
    "seal",
    "symbol",
    "diagram",
    "svg",
    "audio",
    "video",
    "pdf",
)


@dataclass
class CandidateImage:
    image_url: str
    source_page_url: str
    source: str
    credit: str
    license_note: str
    provider: str
    confidence: float
    extract_method: str
    page_title: str
    alt_text: str
    note: str


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def request_json(session: requests.Session, url: str, params: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    response = session.get(url, params=params, headers=headers, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
    return response.json()


def commons_file_url(filename: str, width: int = 1600) -> str:
    filename = clean_text(filename)
    if filename.lower().startswith("file:"):
        filename = filename[5:].strip()
    return f"{COMMONS_SPECIAL_FILE_PATH}{quote(filename.replace(' ', '_'))}?width={width}"


def commons_file_page(filename: str) -> str:
    filename = clean_text(filename)
    if filename.lower().startswith("file:"):
        filename = filename[5:].strip()
    return f"https://commons.wikimedia.org/wiki/File:{quote(filename.replace(' ', '_'))}"


def bad_file_name(filename: str) -> bool:
    lower = clean_text(filename).lower()
    return any(hint in lower for hint in BAD_FILE_HINTS)


def wikidata_search(session: requests.Session, query: str, timeout: float, limit: int = 3) -> List[Dict[str, Any]]:
    data = request_json(
        session,
        WIKIDATA_API,
        {
            "action": "wbsearchentities",
            "format": "json",
            "language": "vi",
            "uselang": "vi",
            "type": "item",
            "limit": limit,
            "search": query,
        },
        timeout,
    )
    return data.get("search", []) or []


def wikidata_entity_images(session: requests.Session, qid: str, timeout: float) -> List[Tuple[str, str]]:
    data = request_json(
        session,
        WIKIDATA_API,
        {
            "action": "wbgetentities",
            "format": "json",
            "ids": qid,
            "props": "claims|sitelinks|labels|descriptions",
            "languages": "vi|en",
            "sitefilter": "viwiki|enwiki|commonswiki",
        },
        timeout,
    )

    entity = (data.get("entities", {}) or {}).get(qid, {}) or {}
    claims = entity.get("claims", {}) or {}
    p18_claims = claims.get("P18", []) or []

    images: List[Tuple[str, str]] = []
    for claim in p18_claims:
        value = (
            claim.get("mainsnak", {})
            .get("datavalue", {})
            .get("value", "")
        )
        filename = clean_text(value)
        if filename and not bad_file_name(filename):
            images.append((filename, "wikidata:P18"))

    return images


def wikidata_candidates(session: requests.Session, row: Dict[str, str], timeout: float, max_qids: int = 3) -> List[CandidateImage]:
    name = place_name(row)
    prov = province(row)
    queries = []
    for q in [f"{name} {prov}", name]:
        q = clean_text(q)
        if q and q not in queries:
            queries.append(q)

    candidates: List[CandidateImage] = []
    seen_files = set()

    for query in queries:
        try:
            hits = wikidata_search(session, query, timeout, limit=max_qids)
        except Exception as exc:
            continue

        for hit in hits:
            qid = clean_text(hit.get("id", ""))
            label = clean_text(hit.get("label", ""))
            desc = clean_text(hit.get("description", ""))
            if not qid:
                continue

            try:
                images = wikidata_entity_images(session, qid, timeout)
            except Exception:
                continue

            for filename, method in images:
                if filename.lower() in seen_files:
                    continue
                seen_files.add(filename.lower())
                candidates.append(
                    CandidateImage(
                        image_url=commons_file_url(filename),
                        source_page_url=f"https://www.wikidata.org/wiki/{qid}",
                        source="Wikidata/Wikimedia Commons",
                        credit="Wikimedia Commons contributor",
                        license_note="Check Commons file page before commercial use",
                        provider="free_wikidata",
                        confidence=0.80,
                        extract_method=method,
                        page_title=f"{label} {desc}".strip(),
                        alt_text=filename,
                        note=f"query={query}; qid={qid}",
                    )
                )

    return candidates


def wiki_search_pages(session: requests.Session, api_url: str, query: str, timeout: float, limit: int = 3) -> List[Tuple[int, str]]:
    data = request_json(
        session,
        api_url,
        {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "srnamespace": 0,
        },
        timeout,
    )
    rows = data.get("query", {}).get("search", []) or []
    return [(int(item.get("pageid", 0)), clean_text(item.get("title", ""))) for item in rows if item.get("pageid")]


def wiki_page_images(session: requests.Session, api_url: str, pageid: int, timeout: float, limit: int = 10) -> List[str]:
    data = request_json(
        session,
        api_url,
        {
            "action": "query",
            "format": "json",
            "prop": "images",
            "pageids": pageid,
            "imlimit": limit,
        },
        timeout,
    )
    pages = data.get("query", {}).get("pages", {}) or {}
    page = pages.get(str(pageid), {}) or {}
    images = page.get("images", []) or []
    files = []
    for item in images:
        title = clean_text(item.get("title", ""))
        if title.lower().startswith("file:") and not bad_file_name(title):
            files.append(title[5:].strip())
    return files


def wiki_page_url(lang: str, title: str) -> str:
    host = "vi.wikipedia.org" if lang == "vi" else "en.wikipedia.org"
    return f"https://{host}/wiki/{quote(title.replace(' ', '_'))}"


def wikipedia_candidates(session: requests.Session, row: Dict[str, str], api_url: str, lang: str, timeout: float) -> List[CandidateImage]:
    name = place_name(row)
    prov = province(row)
    queries = []
    for q in [f"{name} {prov}", name]:
        q = clean_text(q)
        if q and q not in queries:
            queries.append(q)

    candidates: List[CandidateImage] = []
    seen_files = set()

    for query in queries:
        try:
            pages = wiki_search_pages(session, api_url, query, timeout, limit=3)
        except Exception:
            continue

        for pageid, title in pages:
            try:
                files = wiki_page_images(session, api_url, pageid, timeout, limit=12)
            except Exception:
                continue

            for filename in files:
                if filename.lower() in seen_files:
                    continue
                seen_files.add(filename.lower())
                candidates.append(
                    CandidateImage(
                        image_url=commons_file_url(filename),
                        source_page_url=wiki_page_url(lang, title),
                        source=f"{lang}.wikipedia.org/Wikimedia Commons",
                        credit="Wikimedia Commons contributor",
                        license_note="Check Commons file page before commercial use",
                        provider=f"free_{lang}wiki",
                        confidence=0.65,
                        extract_method=f"{lang}wiki:page_images",
                        page_title=title,
                        alt_text=filename,
                        note=f"query={query}; pageid={pageid}",
                    )
                )

    return candidates


def commons_search_files(session: requests.Session, query: str, timeout: float, limit: int = 8) -> List[Tuple[str, str]]:
    data = request_json(
        session,
        COMMONS_API,
        {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srnamespace": 6,
            "srlimit": limit,
        },
        timeout,
    )
    rows = data.get("query", {}).get("search", []) or []
    files: List[Tuple[str, str]] = []
    for item in rows:
        title = clean_text(item.get("title", ""))
        snippet = clean_text(re.sub(r"<[^>]+>", " ", item.get("snippet", "")))
        if title.lower().startswith("file:"):
            filename = title[5:].strip()
            if filename and not bad_file_name(filename):
                files.append((filename, snippet))
    return files


def commons_candidates(session: requests.Session, row: Dict[str, str], timeout: float, limit: int) -> List[CandidateImage]:
    name = place_name(row)
    prov = province(row)
    ar = area(row)
    queries = []
    for q in [f"{name} {prov}", f"{name} {ar}", name]:
        q = clean_text(q)
        if q and q not in queries:
            queries.append(q)

    candidates: List[CandidateImage] = []
    seen_files = set()

    for query in queries:
        try:
            files = commons_search_files(session, query, timeout, limit=limit)
        except Exception:
            continue

        for filename, snippet in files:
            if filename.lower() in seen_files:
                continue
            seen_files.add(filename.lower())
            candidates.append(
                CandidateImage(
                    image_url=commons_file_url(filename),
                    source_page_url=commons_file_page(filename),
                    source="Wikimedia Commons",
                    credit="Wikimedia Commons contributor",
                    license_note="Check Commons file page before commercial use",
                    provider="free_commons_search",
                    confidence=0.55,
                    extract_method="commons:file_search",
                    page_title=filename,
                    alt_text=filename,
                    note=f"query={query}; snippet={snippet[:120]}",
                )
            )

    return candidates


def dedupe_candidates(candidates: List[CandidateImage]) -> List[CandidateImage]:
    seen = set()
    out: List[CandidateImage] = []
    for candidate in sorted(candidates, key=lambda c: (-c.confidence, c.provider, c.image_url)):
        key = candidate.image_url.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)
    return out


def candidate_to_row(place_row: Dict[str, str], candidate: CandidateImage, order: int, batch_code: str, collected_at: str) -> Dict[str, str]:
    return {
        "rag_place_id": rag_place_id(place_row),
        "place_name": place_name(place_row),
        "image_url": candidate.image_url,
        "source_page_url": candidate.source_page_url,
        "source": candidate.source,
        "credit": candidate.credit,
        "license_note": candidate.license_note,
        "image_order": str(order),
        "is_primary": "1" if order == 1 else "0",
        "batch_code": batch_code,
        "provider": candidate.provider,
        "confidence": f"{candidate.confidence:.2f}",
        "need_human_check": "1",
        "candidate_status": "raw",
        "ai_note": candidate.note,
        "extract_method": candidate.extract_method,
        "page_title": candidate.page_title,
        "alt_text": candidate.alt_text,
        "collected_at": collected_at,
    }


def collect_for_rows(
    rows: List[Dict[str, str]],
    timeout: float,
    sleep: float,
    max_images_per_place: int,
    commons_limit: int,
    batch_code: str,
    use_wikidata: bool,
    use_viwiki: bool,
    use_enwiki: bool,
    use_commons: bool,
) -> List[Dict[str, str]]:
    session = requests.Session()
    collected_at = now_utc_iso()
    output_rows: List[Dict[str, str]] = []

    for index, row in enumerate(rows, start=1):
        name = place_name(row)
        pid = rag_place_id(row)
        candidates: List[CandidateImage] = []

        print(f"[{index}/{len(rows)}] Free sources {pid} {name}")

        if use_wikidata:
            cands = wikidata_candidates(session, row, timeout)
            candidates.extend(cands)
            print(f"  wikidata: {len(cands)}")

        if use_viwiki:
            cands = wikipedia_candidates(session, row, VI_WIKI_API, "vi", timeout)
            candidates.extend(cands)
            print(f"  viwiki: {len(cands)}")

        if use_enwiki:
            cands = wikipedia_candidates(session, row, EN_WIKI_API, "en", timeout)
            candidates.extend(cands)
            print(f"  enwiki: {len(cands)}")

        if use_commons:
            cands = commons_candidates(session, row, timeout, limit=commons_limit)
            candidates.extend(cands)
            print(f"  commons: {len(cands)}")

        candidates = dedupe_candidates(candidates)[:max_images_per_place]

        for order, candidate in enumerate(candidates, start=1):
            output_rows.append(candidate_to_row(row, candidate, order, batch_code, collected_at))

        print(f"  kept: {len(candidates)}")

        if sleep > 0:
            time.sleep(sleep)

    return output_rows


def default_output_path(project_root: Path) -> Path:
    return project_root / "data" / "image_pipeline" / "raw" / "free_sources_raw.csv"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect image candidates from free Wikidata/Wikipedia/Commons sources.")

    parser.add_argument("--input", required=True, help="Input places CSV from export_places_for_image_pipeline.py.")
    parser.add_argument("--output", default="", help="Output raw image candidates CSV. Default: data/image_pipeline/raw/free_sources_raw.csv")
    parser.add_argument("--project-root", default=".", help="Project root. Default: current directory.")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds. Default: 15")
    parser.add_argument("--sleep", type=float, default=0.1, help="Sleep between places. Default: 0.1")
    parser.add_argument("--max-images-per-place", type=int, default=8, help="Max candidates kept per place. Default: 8")
    parser.add_argument("--commons-limit", type=int, default=8, help="Commons file search limit per query. Default: 8")
    parser.add_argument("--batch-code", default="free_sources", help="batch_code value. Default: free_sources")

    parser.add_argument("--no-wikidata", action="store_true", help="Disable Wikidata P18 collection.")
    parser.add_argument("--no-viwiki", action="store_true", help="Disable Vietnamese Wikipedia page images.")
    parser.add_argument("--no-enwiki", action="store_true", help="Disable English Wikipedia page images.")
    parser.add_argument("--no-commons", action="store_true", help="Disable Wikimedia Commons file search.")

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
    print(f"Output: {output_path}")
    print("Starting free-source collection...")

    output_rows = collect_for_rows(
        rows=rows,
        timeout=args.timeout,
        sleep=args.sleep,
        max_images_per_place=args.max_images_per_place,
        commons_limit=args.commons_limit,
        batch_code=args.batch_code,
        use_wikidata=not args.no_wikidata,
        use_viwiki=not args.no_viwiki,
        use_enwiki=not args.no_enwiki,
        use_commons=not args.no_commons,
    )

    written = write_csv(output_path, OUTPUT_FIELDS, output_rows)

    print()
    print("Done.")
    print(f"Rows written: {written}")
    print(f"Output file: {output_path}")
    print()
    print("Next:")
    print(f"python .\\scripts\\validate_image_urls.py --input {output_path} --timeout 8 --retries 0")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        print("Cancelled by user.", file=sys.stderr)
        raise SystemExit(130)
