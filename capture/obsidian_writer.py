"""Obsidian vault writer with frontmatter validation."""

import os
import re
from pathlib import Path
from typing import Optional


# Minimum required frontmatter fields for validation
REQUIRED_FRONTMATTER = ["title", "author", "date", "type", "tags", "source"]


def sanitize_filename(text: str, max_length: int = 80) -> str:
    """Sanitize text to a valid filename.

    Args:
        text: Raw text (article title + author).
        max_length: Maximum filename length.

    Returns:
        Safe filename without extension.
    """
    # Remove illegal Windows filename characters
    illegal = r'[<>:"/\\|?*\n\r\t]'
    name = re.sub(illegal, "-", text)

    # Replace multiple dashes/spaces with single dash
    name = re.sub(r"[- ]+", "-", name)
    name = re.sub(r"^-+|-+$", "", name)

    # Truncate
    if len(name) > max_length:
        name = name[:max_length].rstrip("-")

    return name


def build_output_path(
    vault_dir: str,
    article_dir: str,
    category: str,
    title: str,
    author: str,
    date: Optional[str] = None,
) -> str:
    """Build the full output path for an article.

    Args:
        vault_dir: Obsidian vault root directory.
        article_dir: Article subdirectory (e.g. "01-文章").
        category: Content category ("公众号", "抖音", "其他", "论文").
        title: Article title.
        author: Article author.
        date: Optional date string (YYYY-MM-DD).

    Returns:
        Full path to the .md file.
    """
    # Build directory
    dir_path = Path(vault_dir) / article_dir / category
    dir_path.mkdir(parents=True, exist_ok=True)

    # Build filename
    source_name = author if author and author != "未知作者" else "未知来源"
    source_name = sanitize_filename(source_name, max_length=30)
    title_part = sanitize_filename(title, max_length=50)

    if date:
        filename = f"{source_name}-{title_part}-{date}.md"
    else:
        filename = f"{source_name}-{title_part}.md"

    # Ensure uniqueness
    filepath = dir_path / filename
    counter = 1
    while filepath.exists():
        stem = filename.rsplit(".", 1)[0]
        filepath = dir_path / f"{stem}-{counter}.md"
        counter += 1

    return str(filepath)


def write_article(filepath: str, content: str) -> tuple[bool, list[str]]:
    """Write article to Obsidian and validate frontmatter.

    Args:
        filepath: Target file path.
        content: Rendered Markdown content with frontmatter.

    Returns:
        Tuple of (success, list of missing frontmatter fields).
    """
    # Write file
    filepath_obj = Path(filepath)
    filepath_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath_obj, "w", encoding="utf-8") as f:
        f.write(content)

    # Validate frontmatter
    missing = validate_frontmatter(content)

    return len(missing) == 0, missing


def validate_frontmatter(content: str) -> list[str]:
    """Validate that required frontmatter fields are present.

    Args:
        content: Full Markdown content with YAML frontmatter.

    Returns:
        List of missing required field names.
    """
    # Check if frontmatter exists
    if not content.startswith("---"):
        return REQUIRED_FRONTMATTER.copy()

    # Extract frontmatter
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return REQUIRED_FRONTMATTER.copy()

    frontmatter = m.group(1)
    missing = []

    for field in REQUIRED_FRONTMATTER:
        # Check for field: value pattern
        if not re.search(rf"^{field}\s*:", frontmatter, re.MULTILINE):
            missing.append(field)

    return missing


def find_related_notes(
    vault_dir: str,
    article_dir: str,
    tags: list[str],
    current_source_url: str,
) -> list[str]:
    """Find related notes based on tag overlap.

    Args:
        vault_dir: Obsidian vault root.
        article_dir: Article subdirectory.
        tags: Tags from current article.
        current_source_url: Source URL of current article (to avoid self-match).

    Returns:
        List of related note filenames (without .md extension) for [[linking]].
    """
    try:
        import yaml
    except ImportError:
        return []

    related = []
    articles_dir = Path(vault_dir) / article_dir

    if not articles_dir.exists():
        return related

    for md_file in articles_dir.rglob("*.md"):
        filepath = str(md_file)
        if filepath == current_source_url:
            continue

        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read(2048)  # Read first 2KB for frontmatter
        except Exception:
            continue

        # Extract tags from frontmatter
        m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not m:
            continue

        try:
            fm = yaml.safe_load(m.group(1))
        except Exception:
            continue

        file_tags = fm.get("tags", []) if fm else []
        if isinstance(file_tags, str):
            file_tags = [file_tags]

        # Check overlap
        overlap = set(tags) & set(file_tags)
        if overlap:
            related.append(md_file.stem)

        if len(related) >= 5:  # Max 5 related notes
            break

    return related