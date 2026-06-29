"""Base classes for content sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawArticle:
    """Standardized article data returned by all sources."""

    title: str
    author: str
    body: str  # Markdown content
    source_url: str
    category: str  # "公众号" | "抖音" | "其他" | "论文"
    date: Optional[str] = None
    douyin_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    original_meta: dict = field(default_factory=dict)


class SourceBase(ABC):
    """Abstract base for all content sources."""

    category: str = "其他"
    name: str = "base"

    @abstractmethod
    def extract(self, url: str, config: dict) -> RawArticle:
        """Extract content from URL. Returns RawArticle on success, raises on failure."""
        ...

    def matches(self, url: str) -> bool:
        """Check if this source can handle the given URL."""
        raise NotImplementedError


class ExtractionError(Exception):
    """Base exception for extraction failures."""

    def __init__(self, message: str, exit_code: int = 2):
        super().__init__(message)
        self.exit_code = exit_code
