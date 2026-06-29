"""WeChat Official Account article source."""

import re

from .base import SourceBase, RawArticle, ExtractionError


class WechatSource(SourceBase):
    category = "公众号"
    name = "wechat"

    def matches(self, url: str) -> bool:
        return "mp.weixin.qq.com" in url

    def extract(self, url: str, config: dict) -> RawArticle:
        """Extract WeChat article using HTTP + browser rendering."""
        try:
            from urllib.request import Request, urlopen
            import json
        except ImportError:
            raise ExtractionError("Python urllib not available", exit_code=2)

        try:
            # Attempt to fetch article content via WeChat API-like endpoint
            req = Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })
            with urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            raise ExtractionError(f"无法抓取微信文章: {e}", exit_code=2)

        # Extract meta info
        title = self._extract_meta(html, "og:title") or self._extract_title(html) or "未知标题"
        author = self._extract_meta(html, "og:article:author") or "未知作者"
        date_str = self._extract_date(html)

        # Extract body
        body = self._extract_body(html)

        if not body or len(body.strip()) < 50:
            raise ExtractionError("微信文章正文提取失败，可能已被删除或需要登录", exit_code=3)

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
        m = re.search(r"<title>([^<]*)</title>", html, re.IGNORECASE)
        if m:
            title = m.group(1).strip()
            # Remove trailing " - WeChat" or similar
            title = re.sub(r"\s*[-–|]\s*.*$", "", title)
            return title
        return None

    def _extract_date(self, html: str) -> str | None:
        # Try meta first
        date = self._extract_meta(html, "og:article:published_time")
        if date:
            return date[:10]  # YYYY-MM-DD

        # Try to find date in content
        m = re.search(r'publish_time[=:]\s*"?(\d{4}-\d{2}-\d{2})', html, re.IGNORECASE)
        if m:
            return m.group(1)

        m = re.search(r'(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}', html)
        if m:
            return m.group(1)

        return None

    def _extract_body(self, html: str) -> str:
        """Extract article body from WeChat page HTML."""
        # Try to find js_content div
        m = re.search(r'id="js_content"\s*[^>]*>(.*?)</div>', html, re.DOTALL)
        if m:
            content = m.group(1)
        else:
            # Try rich_media_content
            m = re.search(
                r'class="rich_media_content[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL
            )
            if m:
                content = m.group(1)
            else:
                # Fallback: try to get body text
                m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL)
                if m:
                    content = m.group(1)
                else:
                    return ""

        # Clean HTML to Markdown-like plain text
        content = self._html_to_text(content)
        return content.strip()

    def _html_to_text(self, html: str) -> str:
        """Convert simple HTML to plain text with basic formatting."""
        # Remove scripts and styles
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL)
        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)

        # Replace block elements with line breaks
        for tag in ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "br", "tr"]:
            html = re.sub(rf"</?{tag}[^>]*>", "\n", html, flags=re.IGNORECASE)

        # Bold/em to Markdown
        html = re.sub(r"<(strong|b)[^>]*>", "**", html, flags=re.IGNORECASE)
        html = re.sub(r"</(strong|b)>", "**", html, flags=re.IGNORECASE)
        html = re.sub(r"<(em|i)[^>]*>", "*", html, flags=re.IGNORECASE)
        html = re.sub(r"</(em|i)>", "*", html, flags=re.IGNORECASE)

        # Handle images: keep alt text or mark as [图片]
        html = re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>', r"[图: \1]", html)
        html = re.sub(r"<img[^>]*>", "[图片]", html)

        # Remove remaining tags
        html = re.sub(r"<[^>]*>", "", html)

        # Decode HTML entities
        import html as html_mod

        text = html_mod.unescape(html)

        # Collapse multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        # Remove leading/trailing whitespace per line
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(lines)

    def _extract_tags(self, title: str, body: str) -> list[str]:
        """Extract basic tags from title and body."""
        tags = []
        # Use common tech/domain keywords
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
            "MacBook": "MacBook",
            "苹果": "Apple",
            "Python": "Python",
            "Linux": "Linux",
            "GPU": "GPU",
            "CUDA": "CUDA",
            "Transformer": "Transformer",
        }
        combined = f"{title}\n{body[:1000]}".lower()
        for key, tag in keyword_map.items():
            if key.lower() in combined:
                tags.append(tag)

        if not tags:
            tags.append("未分类")

        return list(dict.fromkeys(tags))  # dedup preserve order