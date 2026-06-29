"""Generic web article source (Zhihu, CSDN, Sspai, etc.)."""

import re

from .base import SourceBase, RawArticle, ExtractionError


class WebArticleSource(SourceBase):
    category = "其他"
    name = "web_article"

    def matches(self, url: str) -> bool:
        # This is the fallback source, always matches
        return True

    def extract(self, url: str, config: dict) -> RawArticle:
        """Extract generic web article via HTTP fetch."""
        try:
            from urllib.request import Request, urlopen
        except ImportError:
            raise ExtractionError("Python urllib not available", exit_code=2)

        timeout = config.get("network", {}).get("timeout", 30)
        proxy = config.get("network", {}).get("proxy", None)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            raise ExtractionError(f"无法抓取文章: {e}", exit_code=2)

        # Extract meta info
        title = self._extract_meta(html, "og:title") or self._extract_title(html) or "未知标题"
        author = self._extract_meta(html, "og:article:author") or self._extract_author(html, url) or "未知作者"
        date_str = self._extract_date(html)

        # Extract body
        body = self._extract_body(html, url)

        if not body or len(body.strip()) < 50:
            raise ExtractionError("文章内容提取失败，可能被反爬保护", exit_code=2)

        tags = self._extract_tags(title, body)

        return RawArticle(
            title=title,
            author=author,
            date=date_str,
            body=body,
            source_url=url,
            category=self.category,
            tags=tags,
        )

    def _extract_meta(self, html: str, prop: str) -> str | None:
        patterns = [
            rf'<meta[^>]*property="{prop}"[^>]*content="([^"]*)"',
            rf'<meta[^>]*content="([^"]*)"[^>]*property="{prop}"',
            rf'<meta[^>]*name="{prop}"[^>]*content="([^"]*)"',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _extract_title(self, html: str) -> str | None:
        # Try h1 or article title first
        for tag in ["h1", "h2"]:
            m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.DOTALL | re.IGNORECASE)
            if m:
                text = re.sub(r"<[^>]*>", "", m.group(1)).strip()
                if len(text) > 3:
                    return text

        # Fallback to page title
        m = re.search(r"<title>([^<]*)</title>", html, re.IGNORECASE)
        if m:
            return m.group(1).strip().split(" - ")[0].split(" | ")[0]
        return None

    def _extract_author(self, html: str, url: str) -> str | None:
        # Zhihu-specific
        m = re.search(r'"author"[^}]*"name"\s*:\s*"([^"]*)"', html)
        if m:
            return m.group(1)

        # CSDN-specific
        m = re.search(r'class="follow-nickName[^"]*"[^>]*>([^<]*)<', html)
        if m:
            return m.group(1).strip()

        # Generic: look for author class
        for cls in ["author", "byline", "writer"]:
            m = re.search(rf'class="[^"]*{cls}[^"]*"[^>]*>([^<]*)<', html, re.IGNORECASE)
            if m:
                return m.group(1).strip()

        return None

    def _extract_date(self, html: str) -> str | None:
        # Try meta first
        date = self._extract_meta(html, "og:article:published_time")
        if date:
            return date[:10]

        # Zhihu: JSON-LD datePublished
        m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"', html)
        if m:
            return m.group(1)

        # Common date patterns
        m = re.search(r'(\d{4}-\d{2}-\d{2})', html)
        if m:
            return m.group(1)
        return None

    def _extract_body(self, html: str, url: str) -> str:
        """Extract article body content."""
        # Common article containers (ordered by specificity)
        selectors = [
            # Zhihu
            r'class="RichText[^"]*"[^>]*>(.*?)<(?:div class="ContentItem-actions|div class="Post-Author)',
            # CSDN
            r'<article[^>]*>(.*?)</article>',
            r'class="article_content[^"]*"[^>]*>(.*?)</div>',
            # Generic
            r'<article[^>]*>(.*?)</article>',
            r'itemprop="articleBody"[^>]*>(.*?)</div>',
            r'class="(?:post-content|article-content|entry-content|content)[^"]*"[^>]*>(.*?)(?:</div>\s*<(?:div|section|footer))',
            # Last resort
            r"<body[^>]*>(.*?)</body>",
        ]

        for pattern in selectors:
            m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if m:
                content = m.group(1)
                if len(content) > 200:
                    return self._html_to_text(content)

        return ""

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        # Remove scripts, styles, nav, header, footer
        for tag in ["script", "style", "nav", "header", "footer", "aside"]:
            html = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML comments
        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)

        # Block elements to newlines
        for tag in ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "br", "tr", "section"]:
            html = re.sub(rf"</?{tag}[^>]*>", "\n", html, flags=re.IGNORECASE)

        # Bold/italic to Markdown
        html = re.sub(r"<(strong|b)[^>]*>", "**", html, flags=re.IGNORECASE)
        html = re.sub(r"</(strong|b)>", "**", html, flags=re.IGNORECASE)
        html = re.sub(r"<(em|i)[^>]*>", "*", html, flags=re.IGNORECASE)
        html = re.sub(r"</(em|i)>", "*", html, flags=re.IGNORECASE)

        # Links to Markdown
        html = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', r"[\2](\1)", html)

        # Images
        html = re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>', r'[图: \1]', html)
        html = re.sub(r"<img[^>]*>", "[图片]", html)

        # Remove remaining tags
        html = re.sub(r"<[^>]*>", "")

        # Decode entities
        import html as html_mod

        text = html_mod.unescape(html)

        # Clean whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(line for line in lines if line)

    def _extract_tags(self, title: str, body: str) -> list[str]:
        """Extract basic tags."""
        tags = []
        keyword_map = {
            "AI": "AI",
            "人工智能": "AI",
            "大模型": "大模型",
            "LLM": "LLM",
            "机器人": "机器人",
            "具身智能": "具身智能",
            "强化学习": "强化学习",
            "深度学习": "深度学习",
            "VLA": "VLA",
            "NVIDIA": "NVIDIA",
            "Python": "Python",
            "Linux": "Linux",
            "GPU": "GPU",
        }
        combined = f"{title}\n{body[:1000]}".lower()
        for key, tag in keyword_map.items():
            if key.lower() in combined:
                tags.append(tag)
        if not tags:
            tags.append("未分类")
        return list(dict.fromkeys(tags))
