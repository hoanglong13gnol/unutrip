#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
Score validated image candidates for UnuTrip / SmartTravel image pipeline.

Version: v2 stricter scoring

Purpose:
- Read valid image CSV produced by validate_image_urls.py.
- Score how well each image candidate matches its destination/place.
- Penalize suspicious/unrelated images and weak matches.
- Require image-level evidence for APPROVED_AUTO.
- Detect duplicated image URLs reused across multiple rag_place_id values.
- Export:
  - scored CSV with match_score and match_status
  - approved_auto CSV, limited to top N images per place
  - needs_review CSV
  - rejected CSV
- Do NOT import or update database.

Why v2:
- v1 could approve rows where page_title matched the place, but image_url/alt_text was unrelated.
- v2 requires image_url or alt_text to also contain meaningful place tokens before auto-approval.

Typical command:
python .\scripts\score_image_candidates.py ^
  --input .\data\image_pipeline\valid\source_pages_from_search_raw_valid.csv ^
  --max-approved-per-place 5 ^
  --min-approved-score 10

Outputs default:
data\image_pipeline\scored\<input>_scored.csv
data\image_pipeline\final\<input>_approved_auto.csv
data\image_pipeline\review\<input>_needs_review.csv
data\image_pipeline\review\<input>_rejected.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse


APPROVED_STATUS = "APPROVED_AUTO"
REVIEW_STATUS = "NEEDS_REVIEW"
REJECTED_STATUS = "REJECTED"

ADDED_FIELDS = [
    "match_score",
    "match_status",
    "score_reasons",
    "image_level_match",
    "page_level_match",
    "duplicate_place_count",
    "selected_for_final",
    "final_rank",
]

GOOD_DOMAIN_HINTS = (
    "wikipedia.org",
    "wikimedia.org",
    "vnexpress.net",
    "vinwonders.com",
    "mia.vn",
    "ivivu.com",
    "traveloka.com",
    "vietnamplus.vn",
    "vietnamtourism.gov.vn",
    "dsvh.gov.vn",
    "gov.vn",
    "angiang.gov.vn",
    "thamhiemmekong.com",
    "dulichviet.com.vn",
    "luhanhvietnam.com.vn",
    "haidangtravel.com",
    "dailytravelvietnam.com",
)

BAD_DOMAIN_HINTS = (
    "shopee",
    "shopeeusercontent",
    "lazada",
    "tiki.vn",
    "booking-static",
    "booking.com",
    "agoda",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "foody.vn",
)

BAD_URL_HINTS = (
    "logo",
    "icon",
    "avatar",
    "banner",
    "ads",
    "placeholder",
    "loading",
    "combo",
    "tour-combo",
    "vip-tour",
    "hotel",
    "lodging",
    "apr-asset",
    "booking-static",
    "aquafield",
    "times-city",
    "phu-quoc",
    "nha-trang",
    "vinpearl-aquarium",
    "tuyen-dung",
    "tuyen_dung",
    "nhan-vien",
    "nhan_vien",
    "kinh-doanh",
    "kinh_doanh",
    "viec-lam",
    "viec_lam",
    "banner-qc",
    "weblink",
    "facebook-messenger",
    "messenger",
    "email",
    "congkhaibochiso",
    "dich-vu-cong",
    "phan-anh-kien-nghi",
    "ocop",
    "thanh-co-hn",
    "thanh_cổ_hn",
    "thanh-co-ha-noi",
)

# If these phrases appear in image_url or alt_text while the place name does not contain them,
# auto-approval should be blocked. This catches page-context contamination.
CONFLICT_TERMS = (
    "cap treo",
    "cáp treo",
    "chua van linh",
    "chùa vạn linh",
    "thanh co hn",
    "thành cổ hn",
    "thanh co ha noi",
    "thành cổ hà nội",
    "nha trang",
    "phu quoc",
    "phú quốc",
    "times city",
    "aquafield",
    "hotel",
    "khach san",
    "khách sạn",
    "tuyen dung",
    "tuyển dụng",
    "nhan vien",
    "nhân viên",
    "kinh doanh",
    "booking",
    "combo",
)

WEAK_GENERIC_PLACE_WORDS = {
    "khu",
    "du",
    "lich",
    "di",
    "tich",
    "van",
    "hoa",
    "chua",
    "nui",
    "sam",
    "cam",
    "an",
    "giang",
    "ho",
    "nuoc",
    "troi",
    "cap",
    "treo",
    "rung",
    "tram",
    "diem",
    "tham",
    "quan",
    "mien",
    "tay",
    "khuon",
    "vien",
}

# Some short names need extra context to avoid false positives.
AMBIGUOUS_PLACE_NAMES = {
    "nui sam",
    "nui cam",
    "nui ba the",
    "oc eo",
}


def clean_text(value: object) -> str:
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


def tokenize(value: str) -> List[str]:
    text = normalize_for_match(value)
    if not text:
        return []
    return [token for token in text.split() if token]


def meaningful_tokens(value: str) -> List[str]:
    tokens = tokenize(value)
    result = []
    for token in tokens:
        if len(token) <= 1:
            continue
        if token in WEAK_GENERIC_PLACE_WORDS and len(tokens) > 2:
            continue
        result.append(token)
    return result or tokens


def phrase_in_text(phrase: str, text: str) -> bool:
    phrase_norm = normalize_for_match(phrase)
    text_norm = normalize_for_match(text)
    return bool(phrase_norm and phrase_norm in text_norm)


def token_overlap(tokens: Sequence[str], text: str) -> Tuple[int, int, float]:
    text_norm = normalize_for_match(text)
    if not tokens or not text_norm:
        return 0, len(tokens), 0.0
    hits = sum(1 for token in tokens if token in text_norm)
    total = len(tokens)
    return hits, total, hits / total if total else 0.0


def read_csv_rows(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Input CSV has no header: {path}")
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


def build_output_fieldnames(input_fieldnames: List[str]) -> List[str]:
    output = list(input_fieldnames)
    for field in ADDED_FIELDS:
        if field not in output:
            output.append(field)
    return output


def get_first_existing(row: Dict[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = clean_text(row.get(name, ""))
        if value:
            return value
    return ""


def get_image_url(row: Dict[str, str]) -> str:
    return get_first_existing(row, ["final_image_url", "image_url", "url"])


def get_host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def parse_int(value: object, default: int = 0) -> int:
    try:
        return int(float(clean_text(value)))
    except Exception:
        return default


def page_haystack(row: Dict[str, str]) -> str:
    parts = [
        row.get("source_page_url", ""),
        row.get("source", ""),
        row.get("page_title", ""),
        row.get("search_title", ""),
        row.get("search_snippet", ""),
        row.get("ai_note", ""),
    ]
    return " ".join(clean_text(part) for part in parts if clean_text(part))


def image_haystack(row: Dict[str, str]) -> str:
    parts = [
        get_image_url(row),
        row.get("alt_text", ""),
        row.get("extract_method", ""),
    ]
    return " ".join(clean_text(part) for part in parts if clean_text(part))


def full_haystack(row: Dict[str, str]) -> str:
    return f"{page_haystack(row)} {image_haystack(row)}"


def image_dimensions_score(row: Dict[str, str]) -> Tuple[int, List[str]]:
    score = 0
    reasons = []
    width = parse_int(row.get("width", ""), 0)
    height = parse_int(row.get("height", ""), 0)

    if width <= 0 or height <= 0:
        reasons.append("no_dimensions")
        return 0, reasons

    if width >= 1000 and height >= 600:
        score += 4
        reasons.append("very_large_image")
    elif width >= 800 and height >= 450:
        score += 3
        reasons.append("large_image")
    elif width >= 500 and height >= 300:
        score += 2
        reasons.append("medium_image")
    elif width >= 300 and height >= 200:
        score += 1
        reasons.append("small_but_usable")
    else:
        score -= 5
        reasons.append("too_small_for_gallery")

    ratio = width / max(height, 1)
    if ratio > 3.5 or ratio < 0.3:
        score -= 3
        reasons.append("extreme_aspect_ratio")

    return score, reasons


def domain_score(image_url: str, source_page_url: str) -> Tuple[int, List[str]]:
    score = 0
    reasons = []
    combined = f"{image_url} {source_page_url}".lower()
    host = get_host(source_page_url or image_url)

    if any(good in combined for good in GOOD_DOMAIN_HINTS):
        score += 2
        reasons.append("trusted_or_travel_domain")

    if any(bad in combined for bad in BAD_DOMAIN_HINTS):
        score -= 6
        reasons.append("suspicious_domain")

    if "wikipedia.org" in host or "wikimedia.org" in combined:
        score += 1
        reasons.append("wikimedia_source")

    return score, reasons


def url_penalty(image_url: str, source_page_url: str, alt_text: str) -> Tuple[int, List[str]]:
    combined = f"{image_url} {source_page_url} {alt_text}".lower()
    score = 0
    reasons = []

    for hint in BAD_URL_HINTS:
        if hint in combined:
            score -= 5
            reasons.append(f"bad_url_hint:{hint}")

    if image_url.lower().endswith(".svg"):
        score -= 10
        reasons.append("svg_asset")

    return score, reasons


def evaluate_place_match(row: Dict[str, str]) -> Tuple[int, bool, bool, List[str]]:
    place_name = get_first_existing(row, ["place_name", "name", "title"])
    province = clean_text(row.get("province", ""))
    area = clean_text(row.get("area", ""))

    page_text = page_haystack(row)
    image_text = image_haystack(row)
    all_text = f"{page_text} {image_text}"
    tokens = meaningful_tokens(place_name)

    score = 0
    reasons: List[str] = []

    image_exact = bool(place_name and phrase_in_text(place_name, image_text))
    page_exact = bool(place_name and phrase_in_text(place_name, page_text))

    image_hits, image_total, image_ratio = token_overlap(tokens, image_text)
    page_hits, page_total, page_ratio = token_overlap(tokens, page_text)

    image_level_match = image_exact or image_ratio >= 0.60
    page_level_match = page_exact or page_ratio >= 0.60

    if image_exact:
        score += 9
        reasons.append("image_exact_place_name_match")
    elif image_ratio >= 0.80:
        score += 7
        reasons.append(f"image_strong_place_token_match:{image_hits}/{image_total}")
    elif image_ratio >= 0.60:
        score += 5
        reasons.append(f"image_partial_place_token_match:{image_hits}/{image_total}")
    elif image_hits > 0:
        score += 1
        reasons.append(f"image_weak_place_token_match:{image_hits}/{image_total}")
    else:
        reasons.append("no_image_level_place_match")

    if page_exact:
        score += 5
        reasons.append("page_exact_place_name_match")
    elif page_ratio >= 0.80:
        score += 4
        reasons.append(f"page_strong_place_token_match:{page_hits}/{page_total}")
    elif page_ratio >= 0.60:
        score += 2
        reasons.append(f"page_partial_place_token_match:{page_hits}/{page_total}")
    elif page_hits > 0:
        score += 1
        reasons.append(f"page_weak_place_token_match:{page_hits}/{page_total}")
    else:
        score -= 5
        reasons.append("no_page_level_place_match")

    if province and phrase_in_text(province, all_text):
        score += 2
        reasons.append("province_match")

    if area and phrase_in_text(area, all_text):
        score += 2
        reasons.append("area_match")

    normalized_place = normalize_for_match(place_name)
    if normalized_place in AMBIGUOUS_PLACE_NAMES and not phrase_in_text(province, all_text):
        score -= 2
        reasons.append("ambiguous_place_without_province_penalty")

    if page_level_match and not image_level_match:
        score -= 4
        reasons.append("page_match_without_image_match_penalty")

    return score, image_level_match, page_level_match, reasons


def conflict_penalty(row: Dict[str, str]) -> Tuple[int, List[str], bool]:
    place_name = get_first_existing(row, ["place_name", "name", "title"])
    place_norm = normalize_for_match(place_name)
    image_norm = normalize_for_match(image_haystack(row))
    reasons = []
    score = 0
    has_conflict = False

    for term in CONFLICT_TERMS:
        term_norm = normalize_for_match(term)
        if term_norm and term_norm in image_norm and term_norm not in place_norm:
            has_conflict = True
            score -= 8
            reasons.append(f"conflict_term_in_image:{term_norm}")

    return score, reasons, has_conflict


def match_score(row: Dict[str, str], duplicate_place_count: int) -> Tuple[int, str, List[str], bool, bool]:
    image_url = get_image_url(row)
    source_page_url = clean_text(row.get("source_page_url", ""))
    alt_text = clean_text(row.get("alt_text", ""))

    if not image_url:
        return -999, REJECTED_STATUS, ["missing_image_url"], False, False

    technical_status = clean_text(row.get("technical_status", "")).lower()
    if technical_status and technical_status != "valid":
        return -999, REJECTED_STATUS, ["technical_status_not_valid"], False, False

    score = 0
    reasons: List[str] = []

    m_score, image_level_match, page_level_match, m_reasons = evaluate_place_match(row)
    score += m_score
    reasons.extend(m_reasons)

    dim_score, dim_reasons = image_dimensions_score(row)
    score += dim_score
    reasons.extend(dim_reasons)

    d_score, d_reasons = domain_score(image_url, source_page_url)
    score += d_score
    reasons.extend(d_reasons)

    u_score, u_reasons = url_penalty(image_url, source_page_url, alt_text)
    score += u_score
    reasons.extend(u_reasons)

    c_score, c_reasons, has_conflict = conflict_penalty(row)
    score += c_score
    reasons.extend(c_reasons)

    extract_method = clean_text(row.get("extract_method", "")).lower()
    if "og:image" in extract_method or "twitter:image" in extract_method or "jsonld" in extract_method:
        score += 2
        reasons.append("high_signal_extract_method")

    if duplicate_place_count > 1:
        score -= min(8, duplicate_place_count + 1)
        reasons.append(f"same_image_used_by_{duplicate_place_count}_places")

    has_bad_hint = any(reason.startswith("bad_url_hint") for reason in reasons)
    has_suspicious_domain = "suspicious_domain" in reasons
    too_small = "too_small_for_gallery" in reasons

    # Conservative status logic:
    # APPROVED_AUTO requires both page-level and image-level evidence.
    # If page matches but image URL/alt is unrelated, keep it for review or reject.
    if (
        score >= 10
        and image_level_match
        and page_level_match
        and not has_conflict
        and not has_bad_hint
        and not has_suspicious_domain
        and not too_small
    ):
        status = APPROVED_STATUS
    elif score >= 5 and page_level_match and not has_conflict and not has_suspicious_domain:
        status = REVIEW_STATUS
    else:
        status = REJECTED_STATUS

    return score, status, reasons, image_level_match, page_level_match


def default_output_paths(input_path: Path, project_root: Path) -> Tuple[Path, Path, Path, Path]:
    stem = input_path.stem
    if stem.endswith("_valid"):
        stem = stem[:-6]

    scored = project_root / "data" / "image_pipeline" / "scored" / f"{stem}_scored.csv"
    approved = project_root / "data" / "image_pipeline" / "final" / f"{stem}_approved_auto.csv"
    review = project_root / "data" / "image_pipeline" / "review" / f"{stem}_needs_review.csv"
    rejected = project_root / "data" / "image_pipeline" / "review" / f"{stem}_rejected.csv"
    return scored, approved, review, rejected


def select_approved_top_n(
    scored_rows: List[Dict[str, str]],
    max_approved_per_place: int,
    min_score: int,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    approved_by_place: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    review_rows: List[Dict[str, str]] = []

    for row in scored_rows:
        score = parse_int(row.get("match_score"), -999)
        if row.get("match_status") == APPROVED_STATUS and score >= min_score:
            place_id = get_first_existing(row, ["rag_place_id", "id", "place_id"])
            approved_by_place[place_id].append(row)
        elif row.get("match_status") == REVIEW_STATUS:
            review_rows.append(row)

    final_rows: List[Dict[str, str]] = []

    for place_id in sorted(approved_by_place.keys()):
        rows = approved_by_place[place_id]
        rows.sort(
            key=lambda r: (
                -parse_int(r.get("match_score"), 0),
                -parse_int(r.get("is_primary"), 0),
                -parse_int(r.get("width"), 0),
                get_image_url(r),
            )
        )

        seen_base_urls = set()
        rank = 0

        for row in rows:
            # Avoid selecting the same Wikimedia/base image at several sizes when possible.
            image_url = get_image_url(row)
            base_key = re.sub(r"/\d+px-[^/]+$", "", image_url)
            base_key = re.sub(r"\?.*$", "", base_key)
            if base_key in seen_base_urls and len(rows) > max_approved_per_place:
                continue
            seen_base_urls.add(base_key)

            rank += 1
            out = dict(row)
            out["selected_for_final"] = "1"
            out["final_rank"] = str(rank)
            out["image_order"] = str(rank)
            out["is_primary"] = "1" if rank == 1 else "0"
            final_rows.append(out)

            if rank >= max_approved_per_place:
                break

        selected_urls = {get_image_url(row) for row in final_rows if get_first_existing(row, ["rag_place_id"]) == place_id}
        for row in rows:
            if get_image_url(row) in selected_urls:
                continue
            out = dict(row)
            out["selected_for_final"] = "0"
            out["final_rank"] = ""
            out["match_status"] = REVIEW_STATUS
            out["score_reasons"] = clean_text(out.get("score_reasons", "")) + "; approved_overflow_or_duplicate_needs_review"
            review_rows.append(out)

    return final_rows, review_rows


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score valid image candidates for place/image match quality.")

    parser.add_argument("--input", required=True, help="Valid image CSV from validate_image_urls.py.")
    parser.add_argument("--scored-output", default="", help="Output scored CSV path.")
    parser.add_argument("--approved-output", default="", help="Output approved_auto CSV path.")
    parser.add_argument("--review-output", default="", help="Output needs_review CSV path.")
    parser.add_argument("--rejected-output", default="", help="Output rejected CSV path.")
    parser.add_argument("--project-root", default=".", help="Project root. Default: current directory.")
    parser.add_argument("--max-approved-per-place", type=int, default=5, help="Max approved images per place. Default: 5")
    parser.add_argument("--min-approved-score", type=int, default=10, help="Minimum score for approved final selection. Default: 10")

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

    default_scored, default_approved, default_review, default_rejected = default_output_paths(input_path, project_root)

    scored_output = resolve_path(args.scored_output, project_root) if args.scored_output else default_scored
    approved_output = resolve_path(args.approved_output, project_root) if args.approved_output else default_approved
    review_output = resolve_path(args.review_output, project_root) if args.review_output else default_review
    rejected_output = resolve_path(args.rejected_output, project_root) if args.rejected_output else default_rejected

    fieldnames, rows = read_csv_rows(input_path)
    output_fieldnames = build_output_fieldnames(fieldnames)

    image_to_places: Dict[str, set] = defaultdict(set)
    for row in rows:
        image_url = get_image_url(row).lower()
        place_id = get_first_existing(row, ["rag_place_id", "id", "place_id"])
        if image_url and place_id:
            image_to_places[image_url].add(place_id)

    scored_rows: List[Dict[str, str]] = []
    rejected_rows: List[Dict[str, str]] = []
    status_counter = Counter()

    for row in rows:
        out = dict(row)
        image_url = get_image_url(out).lower()
        duplicate_place_count = len(image_to_places.get(image_url, set())) if image_url else 0

        score, status, reasons, image_level_match, page_level_match = match_score(out, duplicate_place_count)

        out["match_score"] = str(score)
        out["match_status"] = status
        out["score_reasons"] = "; ".join(reasons)
        out["image_level_match"] = "1" if image_level_match else "0"
        out["page_level_match"] = "1" if page_level_match else "0"
        out["duplicate_place_count"] = str(duplicate_place_count)
        out["selected_for_final"] = "0"
        out["final_rank"] = ""

        scored_rows.append(out)
        status_counter[status] += 1

        if status == REJECTED_STATUS:
            rejected_rows.append(out)

    final_rows, review_rows = select_approved_top_n(
        scored_rows=scored_rows,
        max_approved_per_place=args.max_approved_per_place,
        min_score=args.min_approved_score,
    )

    scored_count = write_csv(scored_output, output_fieldnames, scored_rows)
    approved_count = write_csv(approved_output, output_fieldnames, final_rows)
    review_count = write_csv(review_output, output_fieldnames, review_rows)
    rejected_count = write_csv(rejected_output, output_fieldnames, rejected_rows)

    final_places = {get_first_existing(row, ["rag_place_id", "id", "place_id"]) for row in final_rows}

    print(f"Input: {input_path}")
    print(f"Rows scored: {scored_count}")
    print()
    print("Score status counts before top-N final selection")
    for status, count in status_counter.most_common():
        print(f"{status}: {count}")
    print()
    print(f"Approved final rows: {approved_count}")
    print(f"Approved final places: {len([p for p in final_places if p])}")
    print(f"Needs review rows: {review_count}")
    print(f"Rejected rows: {rejected_count}")
    print()
    print("Files written")
    print(f"Scored: {scored_output}")
    print(f"Approved auto: {approved_output}")
    print(f"Needs review: {review_output}")
    print(f"Rejected: {rejected_output}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        print("Cancelled by user.", file=sys.stderr)
        raise SystemExit(130)
