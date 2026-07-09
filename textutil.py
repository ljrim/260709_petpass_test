"""자유 텍스트 유틸 (HTML 제거·체크리스트 분해·날짜 포맷)."""
from __future__ import annotations

import re

_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://[^\s\"'<>)]+")


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = _TAG_RE.sub("", text)
    return (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .strip()
    )


def extract_url(text: str | None) -> str | None:
    if not text:
        return None
    m = _URL_RE.search(text)
    return m.group(0) if m else None


def split_free(text: str | None, comma: bool = False) -> list[str]:
    """줄바꿈과 '- ' 불릿에서 나눔. comma=True 면 쉼표에서도 나눔(필요사항 목록용)."""
    if not text:
        return []
    # '- ' 불릿 경계 앞에 줄바꿈을 넣어 분리 지점을 만든다
    normalized = re.sub(r"(?<!^)- ", "\n- ", text)
    parts = re.split(r"[\n,]" if comma else r"\n", normalized)
    seen: list[str] = []
    for p in parts:
        p = p.lstrip("-").strip()
        if p and p not in seen:
            seen.append(p)
    return seen


def format_modified(raw: str | None) -> str:
    if not raw or len(raw) < 8:
        return ""
    return f"{raw[0:4]}.{raw[4:6]}.{raw[6:8]}"
