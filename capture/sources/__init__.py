"""Source registry and URL matching."""

import re
from typing import Optional
from urllib.parse import urlparse

from .base import SourceBase
from .wechat import WechatSource
from .douyin import DouyinSource
from .web_article import WebArticleSource
from .paper import PaperSource

_SOURCES: list[SourceBase] = [
    WechatSource(),
    DouyinSource(),
    PaperSource(),
    WebArticleSource(),  # fallback
]

# Domain patterns for quick matching
_SOURCE_PATTERNS = [
    (r"mp\.weixin\.qq\.com", "wechat"),
    (r"douyin\.com|v\.douyin\.com", "douyin"),
    (r"arxiv\.org", "paper"),
    (r"zhihu\.com", "web_article"),
    (r"csdn\.net", "web_article"),
    (r"sspai\.com", "web_article"),
]


def get_source_for_url(url: str) -> Optional[SourceBase]:
    """Find the appropriate source for a URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # Check domain patterns
    for pattern, source_name in _SOURCE_PATTERNS:
        if re.search(pattern, domain):
            for source in _SOURCES:
                if source.name == source_name:
                    return source

    # Check file extension for PDF
    if url.lower().endswith(".pdf"):
        for source in _SOURCES:
            if source.name == "paper":
                return source

    # Fallback to web_article
    for source in _SOURCES:
        if source.name == "web_article":
            return source

    return None
