# -*- coding: utf-8 -*-
"""
Download validated image candidates to local files.

Input CSV expected columns:
rag_place_id,place_name,image_url,source_page_url,source,credit,license_note,
image_order,is_primary,batch_code,provider,confidence,need_human_check,
candidate_status,ai_note,technical_status,http_status,content_type,width,height,...

Typical input:
data/image_pipeline/valid/priority_image_candidates_valid.csv

Output:
data/image_pipeline/downloaded/original/<rag_place_id>/<file>
data/image_pipeline/downloaded/optimized/<rag_place_id>/<rag_place_id>_NN.webp
data/image_pipeline/final/destination_images_ready.csv

This script does NOT write to database.
"""

import argparse
import csv
import hashlib
import io
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps, UnidentifiedImageError


ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT_DIR / "data" / "image_pipeline" / "valid" / "priority_image_candidates_valid.csv"
DEFAULT_OUT_BASE = ROOT_DIR / "data" / "image_pipeline"
DEFAULT_FINAL = ROOT_DIR / "data" / "image_pipeline" / "final" / "destination_images_ready.csv"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)

OUTPUT_HEADER = [
    "rag_place_id",
    "place_name",
    "original_image_url",
    "source_page_url",
    "source",
    "credit",
    "license_note",
    "image_order",
    "is_primary",
    "local_original_path",
    "local_optimized_path",
    "public_url",
    "download_status",
    "http_status",
    "content_type",
    "original_width",
    "original_height",
    "optimized_width",
    "optimized_height",
    "file_size_bytes",
    "fail_reason",
    "downloaded_at",
]


def clean(value):
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_slug(value):
    value = clean(value)
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def ext_from_content_type(content_type):
    ct = clean(content_type).lower().split(";")[0].strip()
    if ct == "image/jpeg":
        return ".jpg"
    if ct == "image/png":
        return ".png"
    if ct == "image/webp":
        return ".webp"
    if ct == "image/gif":
        return ".gif"
    if ct == "image/avif":
        return ".avif"
    return ""


def ext_from_url(url):
    path = urlparse(url).path.lower()
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"]:
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ""


def content_type_is_image(content_type):
    return clean(content_type).lower().split(";")[0].strip().startswith("image/")


def sha1_short(text):
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:12]


def fetch_bytes(url, timeout, max_bytes):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://www.google.com/",
    }

    result = {
        "ok": False,
        "status_code": "",
        "content_type": "",
        "data": b"",
        "fail_reason": "",
        "final_url": url,
    }

    try:
        with requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True) as resp:
            result["status_code"] = resp.status_code
            result["content_type"] = resp.headers.get("content-type", "")
            result["final_url"] = resp.url

            if resp.status_code != 200:
                result["fail_reason"] = f"http_status_{resp.status_code}"
                return result

            if not content_type_is_image(result["content_type"]):
                result["fail_reason"] = f"not_image_content_type:{result['content_type'] or 'missing'}"
                return result

            chunks = []
            total = 0

            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue

                chunks.append(chunk)
                total += len(chunk)

                if total > max_bytes:
                    result["fail_reason"] = f"file_too_large_over_{max_bytes}"
                    return result

            data = b"".join(chunks)

            if not data:
                result["fail_reason"] = "empty_response_body"
                return result

            result["ok"] = True
            result["data"] = data
            return result

    except requests.exceptions.Timeout:
        result["fail_reason"] = "timeout"
        return result
    except requests.exceptions.SSLError:
        result["fail_reason"] = "ssl_error"
        return result
    except requests.exceptions.ConnectionError:
        result["fail_reason"] = "connection_error"
        return result
    except requests.exceptions.RequestException as exc:
        result["fail_reason"] = f"request_error:{type(exc).__name__}"
        return result
    except Exception as exc:
        result["fail_reason"] = f"unexpected_error:{type(exc).__name__}"
        return result


def open_image(data):
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        return img
    except UnidentifiedImageError:
        return None
    except Exception:
        return None


def save_optimized_webp(img, out_path: Path, max_width: int, quality: int):
    img = img.convert("RGB")

    ow, oh = img.size

    if ow > max_width:
        ratio = max_width / float(ow)
        nh = int(oh * ratio)
        img = img.resize((max_width, nh), Image.Resampling.LANCZOS)

    ensure_dir(out_path.parent)
    img.save(out_path, "WEBP", quality=quality, method=6)

    return img.size


def relative_posix(path: Path):
    try:
        rel = path.relative_to(ROOT_DIR)
    except ValueError:
        rel = path
    return rel.as_posix()


def build_public_url(public_prefix, optimized_path: Path):
    # optimized path is under data/image_pipeline/downloaded/optimized/<id>/<file>.webp
    parts = optimized_path.parts
    try:
        idx = parts.index("optimized")
        sub = "/".join(parts[idx + 1:])
    except ValueError:
        sub = optimized_path.name

    prefix = public_prefix.rstrip("/")
    return f"{prefix}/{sub}"


def read_input(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def download_images(args):
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    out_base = Path(args.output_base)
    original_dir = out_base / "downloaded" / "original"
    optimized_dir = out_base / "downloaded" / "optimized"
    final_path = Path(args.final_output)

    ensure_dir(original_dir)
    ensure_dir(optimized_dir)
    ensure_dir(final_path.parent)

    rows = read_input(input_path)

    if args.limit > 0:
        rows = rows[:args.limit]

    output_rows = []
    seen_url = set()
    per_place_count = {}

    total = len(rows)
    downloaded = 0
    failed = 0
    skipped = 0

    print(f"Input: {input_path}")
    print(f"Rows: {total}")
    print(f"Original dir: {original_dir}")
    print(f"Optimized dir: {optimized_dir}")
    print(f"Final output: {final_path}")
    print("Starting download...")

    for idx, row in enumerate(rows, start=1):
        rid = clean(row.get("rag_place_id"))
        name = clean(row.get("place_name"))
        url = clean(row.get("image_url"))

        if not rid or not url:
            skipped += 1
            continue

        url_key = url.lower()
        if url_key in seen_url and not args.allow_duplicate_urls:
            skipped += 1
            continue
        seen_url.add(url_key)

        per_place_count[rid] = per_place_count.get(rid, 0) + 1
        order = per_place_count[rid]

        source = clean(row.get("source"))
        ext = ext_from_url(url) or ext_from_content_type(row.get("content_type")) or ".img"

        place_dir_original = original_dir / safe_slug(rid)
        place_dir_optimized = optimized_dir / safe_slug(rid)

        hash_part = sha1_short(url)
        original_name = f"{safe_slug(rid)}_{order:02d}_{hash_part}{ext}"
        optimized_name = f"{safe_slug(rid)}_{order:02d}.webp"

        original_path = place_dir_original / original_name
        optimized_path = place_dir_optimized / optimized_name

        out = {
            "rag_place_id": rid,
            "place_name": name,
            "original_image_url": url,
            "source_page_url": clean(row.get("source_page_url")),
            "source": source,
            "credit": clean(row.get("credit")),
            "license_note": clean(row.get("license_note")) or "Cần kiểm tra quyền sử dụng",
            "image_order": order,
            "is_primary": 1 if order == 1 else 0,
            "local_original_path": "",
            "local_optimized_path": "",
            "public_url": "",
            "download_status": "failed",
            "http_status": "",
            "content_type": "",
            "original_width": "",
            "original_height": "",
            "optimized_width": "",
            "optimized_height": "",
            "file_size_bytes": "",
            "fail_reason": "",
            "downloaded_at": now_iso(),
        }

        if optimized_path.exists() and not args.overwrite:
            try:
                img = Image.open(optimized_path)
                ow, oh = img.size
                out["download_status"] = "exists"
                out["local_optimized_path"] = relative_posix(optimized_path)
                out["public_url"] = build_public_url(args.public_prefix, optimized_path)
                out["optimized_width"] = ow
                out["optimized_height"] = oh
                out["file_size_bytes"] = optimized_path.stat().st_size
                downloaded += 1
                output_rows.append(out)
                continue
            except Exception:
                pass

        fetch = fetch_bytes(url, timeout=args.timeout, max_bytes=args.max_bytes)
        out["http_status"] = fetch.get("status_code", "")
        out["content_type"] = fetch.get("content_type", "")

        if not fetch.get("ok"):
            out["fail_reason"] = fetch.get("fail_reason", "fetch_failed")
            failed += 1
            output_rows.append(out)
        else:
            data = fetch["data"]
            img = open_image(data)

            if img is None:
                out["fail_reason"] = "cannot_open_image"
                failed += 1
                output_rows.append(out)
            else:
                original_width, original_height = img.size
                ensure_dir(original_path.parent)
                original_path.write_bytes(data)

                try:
                    optimized_width, optimized_height = save_optimized_webp(
                        img=img,
                        out_path=optimized_path,
                        max_width=args.max_width,
                        quality=args.quality,
                    )

                    out["download_status"] = "downloaded"
                    out["local_original_path"] = relative_posix(original_path)
                    out["local_optimized_path"] = relative_posix(optimized_path)
                    out["public_url"] = build_public_url(args.public_prefix, optimized_path)
                    out["original_width"] = original_width
                    out["original_height"] = original_height
                    out["optimized_width"] = optimized_width
                    out["optimized_height"] = optimized_height
                    out["file_size_bytes"] = optimized_path.stat().st_size

                    downloaded += 1
                    output_rows.append(out)

                except Exception as exc:
                    out["fail_reason"] = f"optimize_error:{type(exc).__name__}"
                    failed += 1
                    output_rows.append(out)

        if args.sleep > 0:
            time.sleep(args.sleep)

        if idx % args.progress_every == 0 or idx == total:
            print(f"Processed {idx}/{total} | downloaded={downloaded} failed={failed} skipped={skipped}")

    with final_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADER)
        writer.writeheader()
        writer.writerows(output_rows)

    print("")
    print("Download finished.")
    print(f"Total rows : {total}")
    print(f"Downloaded : {downloaded}")
    print(f"Failed     : {failed}")
    print(f"Skipped    : {skipped}")
    print(f"Output     : {final_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Download validated image candidates to local optimized files.")

    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input CSV")
    parser.add_argument("--output-base", default=str(DEFAULT_OUT_BASE), help="Base output directory")
    parser.add_argument("--final-output", default=str(DEFAULT_FINAL), help="Output DB-ready CSV")

    parser.add_argument("--public-prefix", default="/images/destinations", help="Public URL prefix for optimized images")
    parser.add_argument("--max-width", type=int, default=1280, help="Resize images wider than this")
    parser.add_argument("--quality", type=int, default=82, help="WEBP quality")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    parser.add_argument("--max-bytes", type=int, default=15 * 1024 * 1024, help="Max download bytes per image")
    parser.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between downloads")
    parser.add_argument("--progress-every", type=int, default=25, help="Print progress every N rows")
    parser.add_argument("--limit", type=int, default=0, help="Limit rows for testing")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing downloaded files")
    parser.add_argument("--allow-duplicate-urls", action="store_true", help="Allow same image URL multiple times")

    return parser.parse_args()


if __name__ == "__main__":
    try:
        download_images(parse_args())
    except KeyboardInterrupt:
        print("Interrupted.")
        sys.exit(130)
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
