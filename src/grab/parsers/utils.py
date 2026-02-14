from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", flags=re.IGNORECASE)


def extract_links(text: str | None, html: str | None) -> list[str]:
    links: list[str] = []

    if text:
        links.extend(URL_PATTERN.findall(text))

    if html:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["a", "img", "source", "video"]):
            attr = "href" if tag.name == "a" else "src"
            value = tag.get(attr)
            if value and value.startswith("http"):
                links.append(value)

    deduped = []
    seen = set()
    for link in links:
        normalized = link.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped


def filter_media_links(links: list[str]) -> list[str]:
    media_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".mov"}
    result = []
    for link in links:
        path = urlparse(link).path.lower()
        if any(path.endswith(ext) for ext in media_ext):
            result.append(link)
    return result

