"""Jinja2 template renderer for Obsidian notes."""

import os
from pathlib import Path
from typing import Optional

import jinja2

from .sources.base import RawArticle

# Default templates directory (relative to this file)
_DEFAULT_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _get_template_path(category: str) -> str:
    """Map article category to template filename."""
    template_map = {
        "公众号": "wechat.md.j2",
        "抖音": "douyin.md.j2",
        "其他": "web_article.md.j2",
        "论文": "paper.md.j2",
    }
    return template_map.get(category, "web_article.md.j2")


def render_article(
    article: RawArticle,
    custom_template_dir: Optional[str] = None,
    related_notes: Optional[list[str]] = None,
) -> str:
    """Render a RawArticle into Markdown using Jinja2 template.

    Args:
        article: Standardized article data.
        custom_template_dir: Optional path to user's custom templates.
        related_notes: Optional list of related note filenames for backlinks.

    Returns:
        Rendered Markdown string with YAML frontmatter.
    """
    # Choose template directory
    if custom_template_dir and Path(custom_template_dir).exists():
        template_dir = custom_template_dir
    else:
        template_dir = str(_DEFAULT_TEMPLATE_DIR)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template_name = _get_template_path(article.category)
    try:
        template = env.get_template(template_name)
    except jinja2.TemplateNotFound:
        # Fallback to web_article template
        template = env.get_template("web_article.md.j2")

    # Build template context
    context = {
        "title": article.title,
        "author": article.author,
        "date": article.date or "",
        "type": _get_type_label(article.category),
        "tags": article.tags,
        "source": article.source_url,
        "body": article.body,
        "douyin_id": article.douyin_id if article.category == "抖音" else None,
        "related_notes": related_notes or [],
    }

    return template.render(**context)


def _get_type_label(category: str) -> str:
    """Map category to frontmatter type label."""
    type_map = {
        "公众号": "公众号文章",
        "抖音": "抖音视频",
        "其他": "文章",
        "论文": "论文",
    }
    return type_map.get(category, "文章")
