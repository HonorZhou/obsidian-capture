"""obsidian-capture: Capture articles and save to Obsidian."""

from .config import load_config, create_default_config, validate_config
from .sources import get_source_for_url
from .sources.base import RawArticle, ExtractionError
from .renderer import render_article
from .obsidian_writer import (
    build_output_path,
    write_article,
    find_related_notes,
    sanitize_filename,
    validate_frontmatter,
)
from .dedup import find_existing

__version__ = "0.1.0"
__all__ = [
    "load_config",
    "create_default_config",
    "validate_config",
    "get_source_for_url",
    "RawArticle",
    "ExtractionError",
    "render_article",
    "build_output_path",
    "write_article",
    "find_related_notes",
    "sanitize_filename",
    "validate_frontmatter",
    "find_existing",
]
