import re
import unicodedata


def remove_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return text


def normalize_text(text: str | None) -> str:
    if text is None:
        return ""

    text = str(text).lower().strip()
    text = remove_accents(text)
    text = re.sub(r"[^a-z0-9\s_/-]+", " ", text)
    text = re.sub(r"[_/-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_vi(text: str | None) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    tokens = normalized.split()

    # bỏ token quá ngắn, nhưng giữ số
    tokens = [
        token for token in tokens
        if len(token) >= 2 or token.isdigit()
    ]

    return tokens