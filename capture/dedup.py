"""Deduplication by source URL."""

import re
from pathlib import Path
from typing import Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def find_existing(
    vault_dir: str,
    article_dir: str,
    source_url: str,
) -> Optional[str]:
    """Check if an article with the same source URL already exists.

    Args:
        vault_dir: Obsidian vault root.
        article_dir: Article subdirectory.
        source_url: Source URL to look for.

    Returns:
        Path of existing note if found, None otherwise.
    """
    if not HAS_YAML:
        return None

    articles_dir = Path(vault_dir) / article_dir
    if not articles_dir.exists():
        return None

    for md_file in articles_dir.rglob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read(4096)
        except Exception:
            continue

        # Extract source from frontmatter
        m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not m:
            continue

        try:
            fm = yaml.safe_load(m.group(1))
        except Exception:
            continue

        if fm and isinstance(fm, dict) and fm.get("source") == source_url:
            return str(md_file)

    return None
