"""CLI entry point for obsidian-capture."""

import argparse
import sys
from typing import Any

from .config import (
    load_config,
    validate_config,
    create_default_config,
    ensure_config_dir,
)
from .dedup import find_existing
from .obsidian_writer import (
    build_output_path,
    write_article,
    find_related_notes,
)
from .renderer import render_article
from .sources import get_source_for_url
from .sources.base import ExtractionError


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    parser = argparse.ArgumentParser(
        prog="capture",
        description="Capture articles from WeChat, Douyin, Zhihu etc. and save to Obsidian.",
    )

    parser.add_argument(
        "url",
        help="URL of the article to capture",
    )

    parser.add_argument(
        "--obsidian-dir",
        help="Override Obsidian vault directory",
    )

    parser.add_argument(
        "--douyin-api",
        help="Override Douyin API URL",
    )

    parser.add_argument(
        "--template-dir",
        help="Override template directory",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite even if article already exists",
    )

    parser.add_argument(
        "--proxy",
        help="Network proxy (e.g. http://127.0.0.1:7890)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without writing to Obsidian",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    parser.add_argument(
        "--init",
        action="store_true",
        help="Create default config file and exit",
    )

    return parser


def main():
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Handle --init
    if args.init:
        path = create_default_config()
        print(f"OK 已创建默认配置: {path}")
        print("请编辑 vault_dir 为你的 Obsidian 库路径")
        sys.exit(0)

    # Build CLI overrides dict
    cli_overrides: dict[str, Any] = {}

    if args.obsidian_dir:
        cli_overrides.setdefault("obsidian", {})["vault_dir"] = args.obsidian_dir

    if args.douyin_api:
        cli_overrides.setdefault("sources", {}).setdefault("douyin", {})[
            "api_url"
        ] = args.douyin_api

    if args.template_dir:
        cli_overrides.setdefault("templates", {})["custom_dir"] = args.template_dir

    if args.proxy:
        cli_overrides.setdefault("network", {})["proxy"] = args.proxy

    # Load config
    config = load_config(cli_overrides)

    # Validate
    errors = validate_config(config)
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        print("\n运行 'capture --init' 创建配置文件", file=sys.stderr)
        sys.exit(7)

    url = args.url.strip()

    # Validate URL
    if not url.startswith(("http://", "https://")):
        print(f"ERROR 无效的 URL: {url}", file=sys.stderr)
        sys.exit(1)

    # Find source
    source = get_source_for_url(url)
    if source is None:
        print(f"ERROR 无法识别该 URL 类型: {url}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"INFO 来源类型: {source.name} ({source.category})")

    vault_dir = config["obsidian"]["vault_dir"]
    article_dir = config["obsidian"]["article_dir"]

    # Deduplication
    existing = find_existing(vault_dir, article_dir, url)
    if existing and not args.force:
        print(f"INFO 已入库: {existing}")
        sys.exit(0)

    # Extract
    try:
        article = source.extract(url, config)
    except ExtractionError as e:
        print(f"ERROR {e}", file=sys.stderr)
        sys.exit(e.exit_code)

    if args.verbose:
        print(f"INFO 标题: {article.title}")
        print(f"INFO 作者: {article.author}")
        print(f"INFO 日期: {article.date}")

    # Find related notes
    related = find_related_notes(vault_dir, article_dir, article.tags, url)
    if args.verbose and related:
        print(f"INFO 关联笔记: {', '.join(related)}")

    # Render
    custom_templates = config.get("templates", {}).get("custom_dir")
    content = render_article(article, custom_template_dir=custom_templates, related_notes=related)

    # Build output path
    output_path = build_output_path(
        vault_dir=vault_dir,
        article_dir=article_dir,
        category=article.category,
        title=article.title,
        author=article.author,
        date=article.date,
    )

    # Dry run
    if args.dry_run:
        print(f"DRY-RUN 将写入: {output_path}")
        print(f"DRY-RUN 内容长度: {len(content)} 字符")
        if args.verbose:
            print("\n" + content[:500] + "...")
        sys.exit(0)

    # Write
    success, missing_fields = write_article(output_path, content)
    if success:
        print(f"OK 已入库: {output_path}")
    else:
        print(f"WARN 已写入，但缺少 frontmatter 字段: {', '.join(missing_fields)}", file=sys.stderr)
        print(f"OK 已入库: {output_path}")


if __name__ == "__main__":
    main()
