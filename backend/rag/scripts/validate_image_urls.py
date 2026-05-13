#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
Validate direct image URLs for UnuTrip / SmartTravel image pipeline.

Purpose:
- Read a CSV of raw image candidates.
- Validate image_url/final_image_url/url is a real direct image URL.
- Reject HTML/search pages, dead links, too-small images, unsupported content types.
- Deduplicate by image URL unless --allow-duplicate is used.
- Split rows into valid and invalid CSV outputs.
- Add technical fields:
  technical_status,http_status,content_type,width,height,fail_reason,checked_at,final_image_url
- Does NOT import/update database.

Input examples:
python .\scripts\validate_image_urls.py ^
  --input .\data\image_pipeline\raw\source_pages_from_search_raw.csv

Recommended for large crawl batches:
python .\scripts\validate_image_urls.py ^
  --input .\data\image_pipeline\raw\source_pages_from_search_raw.csv ^
  --timeout 8 ^
  --retries 0

Default outputs:
data\image_pipeline\valid\<input_stem>_valid.csv
data\image_pipeline\invalid\<input_stem>_invalid.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import struct
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs, unquote, urlparse, urlunparse

try:
    import requests
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: requests\n"
        "Install it with:\n"
        "  pip install requests"
    ) from exc


TECHNICAL_FIELDS = [
    "technical_status",
    "http_status",
    "content_type",
    "width",
    "height",
    "fail_reason",
    "checked_at",
    "final_image_url",
]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 "
    "UnuTripImageValidator/1.1"
)

IMAGE_URL_COLUMNS = ["final_image_url", "image_url", "url", "src"]

DIRECT_IMAGE_EXTENSIONS = (
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

VALID_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/avif",
}

SEARCH_PAGE_HOSTS = {
    "google.com",
    "www.google.com",
    "images.google.com",
    "bing.com",
    "www.bing.com",
    "duckduckgo.com",
    "www.duckduckgo.com",
    "yahoo.com",
    "search.yahoo.com",
}

BAD_URL_KEYWORDS = (
    "/search?",
    "tbm=isch",
    "google.com/url?",
    "bing.com/ck/a",
    "facebook.com/sharer",
    "twitter.com/share",
    "mailto:",
    "javascript:",
    "data:image/",
    "base64,",
)

BAD_IMAGE_HINTS = (
    "logo",
    "icon",
    "favicon",
    "avatar",
    "placeholder",
    "loading",
    "transparent.gif",
    "blank.gif",
    "pixel.gif",
    "1x1",
    "sprite",
    "doubleclick",
    "googlesyndication",
    "analytics",
)


@dataclass
class ValidationResult:
    technical_status: str
    http_status: str = ""
    content_type: str = ""
    width: str = ""
    height: str = ""
    fail_reason: str = ""
    final_image_url: str = ""


class ImageUrlValidator:
    def __init__(
        self,
        session: requests.Session,
        timeout: float,
        min_width: int,
        min_height: int,
        user_agent: str,
        allow_duplicate: bool,
    ) -> None:
        self.session = session
        self.timeout = timeout
        self.min_width = min_width
        self.min_height = min_height
        self.user_agent = user_agent
        self.allow_duplicate = allow_duplicate
        self.seen_urls = set()

    def validate(self, raw_url: str) -> ValidationResult:
        url = normalize_url(raw_url)

        if not url:
            return invalid("missing_image_url", final_image_url=url)

        precheck_reason = precheck_url(url)
        if precheck_reason:
            return invalid(precheck_reason, final_image_url=url)

        dedupe_key = canonical_dedupe_key(url)
        if not self.allow_duplicate and dedupe_key in self.seen_urls:
            return invalid("duplicate_image_url", final_image_url=url)

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
            "Referer": referer_for_url(url),
            "Cache-Control": "no-cache",
        }

        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=self.timeout,
                stream=True,
                allow_redirects=True,
            )

            final_url = normalize_url(response.url or url)
            http_status = str(response.status_code)
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()

            if response.status_code != 200:
                close_response(response)
                return invalid(
                    f"http_status_{response.status_code}",
                    http_status=http_status,
                    content_type=content_type,
                    final_image_url=final_url,
                )

            if content_type.startswith("text/html") or content_type in {"text/html", "application/xhtml+xml"}:
                close_response(response)
                return invalid(
                    "content_type_html_not_direct_image",
                    http_status=http_status,
                    content_type=content_type,
                    final_image_url=final_url,
                )

            if content_type and content_type not in VALID_IMAGE_CONTENT_TYPES:
                # Some CDNs omit/lie about content-type. Allow octet-stream only if URL clearly looks image-like.
                if content_type not in {"application/octet-stream", "binary/octet-stream"} or not url_has_image_hint(final_url):
                    close_response(response)
                    return invalid(
                        "content_type_not_image",
                        http_status=http_status,
                        content_type=content_type,
                        final_image_url=final_url,
                    )

            sample = read_sample_bytes(response, max_bytes=128 * 1024)
            close_response(response)

            detected_type = detect_image_type(sample)
            if not detected_type:
                return invalid(
                    "image_signature_not_recognized",
                    http_status=http_status,
                    content_type=content_type,
                    final_image_url=final_url,
                )

            width, height = get_image_size(sample, detected_type)

            if width > 0 and height > 0:
                if width < self.min_width or height < self.min_height:
                    return invalid(
                        f"image_too_small_min_{self.min_width}x{self.min_height}",
                        http_status=http_status,
                        content_type=content_type or detected_type_to_content_type(detected_type),
                        width=str(width),
                        height=str(height),
                        final_image_url=final_url,
                    )

            self.seen_urls.add(dedupe_key)
            return ValidationResult(
                technical_status="valid",
                http_status=http_status,
                content_type=content_type or detected_type_to_content_type(detected_type),
                width=str(width) if width else "",
                height=str(height) if height else "",
                fail_reason="",
                final_image_url=final_url,
            )

        except requests.exceptions.Timeout:
            return invalid("timeout", final_image_url=url)
        except requests.exceptions.SSLError:
            return invalid("ssl_error", final_image_url=url)
        except requests.exceptions.TooManyRedirects:
            return invalid("too_many_redirects", final_image_url=url)
        except requests.exceptions.ConnectionError:
            return invalid("connection_error", final_image_url=url)
        except requests.exceptions.ChunkedEncodingError:
            return invalid("chunked_encoding_error", final_image_url=url)
        except requests.exceptions.ContentDecodingError:
            return invalid("content_decoding_error", final_image_url=url)
        except requests.exceptions.RequestException as exc:
            return invalid(exc.__class__.__name__.lower(), final_image_url=url)
        except Exception as exc:
            return invalid(f"unexpected_{exc.__class__.__name__.lower()}", final_image_url=url)


def invalid(
    reason: str,
    http_status: str = "",
    content_type: str = "",
    width: str = "",
    height: str = "",
    final_image_url: str = "",
) -> ValidationResult:
    return ValidationResult(
        technical_status="invalid",
        http_status=http_status,
        content_type=content_type,
        width=width,
        height=height,
        fail_reason=reason,
        final_image_url=final_image_url,
    )


def close_response(response: requests.Response) -> None:
    try:
        response.close()
    except Exception:
        pass


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def get_first_existing(row: Dict[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = clean_text(row.get(name, ""))
        if value:
            return value
    return ""


def normalize_url(raw_url: str) -> str:
    url = clean_text(raw_url)
    if not url:
        return ""

    url = url.strip().strip('"').strip("'")
    url = url.replace("&amp;", "&")
    url = url.replace("\\/", "/")

    if url.startswith("//"):
        url = "https:" + url

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return url

    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            "",
        )
    )


def host_matches(host: str, domain: str) -> bool:
    host = host.lower().strip(".")
    domain = domain.lower().strip(".")
    return host == domain or host.endswith("." + domain)


def precheck_url(url: str) -> str:
    lower = url.lower()

    if any(keyword in lower for keyword in BAD_URL_KEYWORDS):
        return "search_result_url_not_direct_image"

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "invalid_url_scheme"
    if not parsed.netloc:
        return "missing_url_host"

    if any(host_matches(parsed.netloc, host) for host in SEARCH_PAGE_HOSTS):
        if parsed.path.startswith("/search") or "tbm=isch" in parsed.query.lower():
            return "search_result_url_not_direct_image"

    if any(hint in lower for hint in BAD_IMAGE_HINTS):
        # Some real URLs may contain logo text as article slug, but these are usually bad for destination gallery.
        return "bad_image_url_hint"

    return ""


def url_has_image_hint(url: str) -> bool:
    lower = url.lower()
    path = urlparse(lower).path
    if path.endswith(DIRECT_IMAGE_EXTENSIONS):
        return True
    query = urlparse(lower).query
    hints = ("format=jpg", "format=jpeg", "format=png", "format=webp", "w=", "width=", "h=", "height=")
    if any(hint in query for hint in hints):
        return True
    return any(hint in lower for hint in ("image", "img", "photo", "cdn", "upload", "media", "vcdn"))


def canonical_dedupe_key(url: str) -> str:
    parsed = urlparse(url.lower())
    query = parse_qs(parsed.query, keep_blank_values=True)

    # Keep transformation query params because they may represent real dimensions.
    drop_prefixes = ("utm_",)
    drop_keys = {"fbclid", "gclid", "yclid", "mc_cid", "mc_eid"}
    filtered_items = []
    for key, values in sorted(query.items()):
        if key in drop_keys or any(key.startswith(prefix) for prefix in drop_prefixes):
            continue
        for value in values:
            filtered_items.append((key, value))

    query_text = "&".join(f"{k}={v}" for k, v in filtered_items)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query_text, ""))


def referer_for_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/"
    return "https://www.google.com/"


def read_sample_bytes(response: requests.Response, max_bytes: int) -> bytes:
    chunks: List[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=8192):
        if not chunk:
            continue
        chunks.append(chunk)
        total += len(chunk)
        if total >= max_bytes:
            break
    return b"".join(chunks)[:max_bytes]


def detect_image_type(data: bytes) -> str:
    if len(data) < 12:
        return ""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith(b"BM"):
        return "bmp"
    if data[4:8] == b"ftyp" and b"avif" in data[8:32]:
        return "avif"
    if data.startswith(b"II*\x00") or data.startswith(b"MM\x00*"):
        return "tiff"
    return ""


def detected_type_to_content_type(image_type: str) -> str:
    return {
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "avif": "image/avif",
    }.get(image_type, "")


def get_image_size(data: bytes, image_type: str) -> Tuple[int, int]:
    try:
        if image_type == "png":
            return parse_png_size(data)
        if image_type == "gif":
            return parse_gif_size(data)
        if image_type == "jpeg":
            return parse_jpeg_size(data)
        if image_type == "webp":
            return parse_webp_size(data)
        if image_type == "bmp":
            return parse_bmp_size(data)
    except Exception:
        return 0, 0
    return 0, 0


def parse_png_size(data: bytes) -> Tuple[int, int]:
    if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
        width, height = struct.unpack(">II", data[16:24])
        return int(width), int(height)
    return 0, 0


def parse_gif_size(data: bytes) -> Tuple[int, int]:
    if len(data) >= 10 and (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
        width, height = struct.unpack("<HH", data[6:10])
        return int(width), int(height)
    return 0, 0


def parse_bmp_size(data: bytes) -> Tuple[int, int]:
    if len(data) >= 26 and data.startswith(b"BM"):
        width = struct.unpack("<I", data[18:22])[0]
        height = struct.unpack("<I", data[22:26])[0]
        return int(width), abs(int(height))
    return 0, 0


def parse_jpeg_size(data: bytes) -> Tuple[int, int]:
    if not data.startswith(b"\xff\xd8"):
        return 0, 0

    index = 2
    data_len = len(data)

    while index < data_len - 1:
        if data[index] != 0xFF:
            index += 1
            continue

        while index < data_len and data[index] == 0xFF:
            index += 1
        if index >= data_len:
            break

        marker = data[index]
        index += 1

        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > data_len:
            break

        segment_length = struct.unpack(">H", data[index:index + 2])[0]
        if segment_length < 2:
            break

        # SOF markers that contain dimensions.
        if marker in {
            0xC0, 0xC1, 0xC2, 0xC3,
            0xC5, 0xC6, 0xC7,
            0xC9, 0xCA, 0xCB,
            0xCD, 0xCE, 0xCF,
        }:
            if index + 7 <= data_len:
                height = struct.unpack(">H", data[index + 3:index + 5])[0]
                width = struct.unpack(">H", data[index + 5:index + 7])[0]
                return int(width), int(height)
            break

        index += segment_length

    return 0, 0


def parse_webp_size(data: bytes) -> Tuple[int, int]:
    if len(data) < 30 or not (data.startswith(b"RIFF") and data[8:12] == b"WEBP"):
        return 0, 0

    chunk = data[12:16]

    if chunk == b"VP8 ":
        # Lossy bitstream. Size is after start code 9d 01 2a.
        start = data.find(b"\x9d\x01\x2a", 20)
        if start != -1 and start + 7 <= len(data):
            width_raw, height_raw = struct.unpack("<HH", data[start + 3:start + 7])
            return int(width_raw & 0x3FFF), int(height_raw & 0x3FFF)

    if chunk == b"VP8L":
        if len(data) >= 25:
            b0, b1, b2, b3 = data[21], data[22], data[23], data[24]
            width = 1 + (((b1 & 0x3F) << 8) | b0)
            height = 1 + (((b3 & 0x0F) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
            return int(width), int(height)

    if chunk == b"VP8X":
        if len(data) >= 30:
            width = 1 + int.from_bytes(data[24:27], "little")
            height = 1 + int.from_bytes(data[27:30], "little")
            return int(width), int(height)

    return 0, 0


def build_output_fieldnames(input_fieldnames: List[str]) -> List[str]:
    output = list(input_fieldnames)
    for field in TECHNICAL_FIELDS:
        if field not in output:
            output.append(field)
    return output


def apply_result_to_row(row: Dict[str, str], result: ValidationResult, checked_at: str) -> Dict[str, str]:
    out = dict(row)
    out["technical_status"] = result.technical_status
    out["http_status"] = result.http_status
    out["content_type"] = result.content_type
    out["width"] = result.width
    out["height"] = result.height
    out["fail_reason"] = result.fail_reason
    out["checked_at"] = checked_at
    out["final_image_url"] = result.final_image_url or get_first_existing(row, IMAGE_URL_COLUMNS)
    return out


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


def default_output_paths(input_path: Path, project_root: Path) -> Tuple[Path, Path]:
    stem = input_path.stem
    valid = project_root / "data" / "image_pipeline" / "valid" / f"{stem}_valid.csv"
    invalid_path = project_root / "data" / "image_pipeline" / "invalid" / f"{stem}_invalid.csv"
    return valid, invalid_path


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
            backoff_factor=0.3,
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


def count_reasons(rows: List[Dict[str, str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        reason = clean_text(row.get("fail_reason", "")) or "unknown"
        counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate direct image URLs and split valid/invalid CSVs.")

    parser.add_argument("--input", required=True, help="Input raw image candidates CSV.")
    parser.add_argument("--valid-output", default="", help="Valid output CSV path.")
    parser.add_argument("--invalid-output", default="", help="Invalid output CSV path.")
    parser.add_argument("--project-root", default=".", help="Project root. Default: current directory.")
    parser.add_argument("--image-url-columns", default=",".join(IMAGE_URL_COLUMNS), help="Comma-separated image URL columns to check in order.")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout seconds. Default: 10")
    parser.add_argument("--retries", type=int, default=0, help="HTTP retry count. Default: 0")
    parser.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between checks. Default: 0")
    parser.add_argument("--min-width", type=int, default=120, help="Minimum image width. Default: 120")
    parser.add_argument("--min-height", type=int, default=90, help="Minimum image height. Default: 90")
    parser.add_argument("--progress-every", type=int, default=25, help="Print progress every N rows. Default: 25")
    parser.add_argument("--allow-duplicate", action="store_true", help="Do not reject duplicate image URLs.")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="HTTP User-Agent.")
    parser.add_argument("--start-row", type=int, default=1, help="1-based start row. Default: 1")
    parser.add_argument("--limit-rows", type=int, default=0, help="Limit number of rows. 0 means all. Default: 0")

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
    default_valid_output, default_invalid_output = default_output_paths(input_path, project_root)
    valid_output = resolve_path(args.valid_output, project_root) if args.valid_output else default_valid_output
    invalid_output = resolve_path(args.invalid_output, project_root) if args.invalid_output else default_invalid_output

    fieldnames, all_rows = read_csv_rows(input_path)
    output_fieldnames = build_output_fieldnames(fieldnames)

    image_url_columns = [col.strip() for col in args.image_url_columns.split(",") if col.strip()]

    start_row = max(1, args.start_row)
    end_row = len(all_rows)
    if args.limit_rows > 0:
        end_row = min(len(all_rows), start_row + args.limit_rows - 1)
    rows = all_rows[start_row - 1:end_row]

    session = session_with_retries(args.retries)
    validator = ImageUrlValidator(
        session=session,
        timeout=args.timeout,
        min_width=args.min_width,
        min_height=args.min_height,
        user_agent=args.user_agent,
        allow_duplicate=args.allow_duplicate,
    )

    valid_rows: List[Dict[str, str]] = []
    invalid_rows: List[Dict[str, str]] = []
    checked_at = now_utc_iso()

    print(f"Input: {input_path}")
    print(f"Rows: {len(all_rows)}")
    print(f"Selected rows: {len(rows)}")
    print(f"Valid output: {valid_output}")
    print(f"Invalid output: {invalid_output}")
    print("Starting validation...")

    for local_index, row in enumerate(rows, start=1):
        absolute_index = start_row + local_index - 1
        raw_url = get_first_existing(row, image_url_columns)
        result = validator.validate(raw_url)
        out = apply_result_to_row(row, result, checked_at)

        if result.technical_status == "valid":
            valid_rows.append(out)
        else:
            invalid_rows.append(out)

        if args.progress_every > 0 and (local_index % args.progress_every == 0 or local_index == len(rows)):
            print(f"Checked {local_index}/{len(rows)} | valid={len(valid_rows)} invalid={len(invalid_rows)}")

        if args.sleep > 0:
            time.sleep(args.sleep)

    write_csv(valid_output, output_fieldnames, valid_rows)
    write_csv(invalid_output, output_fieldnames, invalid_rows)

    print()
    print("Done.")
    print(f"Total rows: {len(rows)}")
    print(f"Valid rows: {len(valid_rows)}")
    print(f"Invalid rows: {len(invalid_rows)}")

    if invalid_rows:
        print()
        print("Invalid reasons:")
        for reason, count in count_reasons(invalid_rows).items():
            print(f"  {reason}: {count}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        print("Cancelled by user.", file=sys.stderr)
        raise SystemExit(130)
