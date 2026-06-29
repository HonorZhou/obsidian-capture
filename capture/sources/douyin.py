"""Douyin (TikTok CN) video source via local API."""

import json
import re

from .base import SourceBase, RawArticle, ExtractionError


class DouyinSource(SourceBase):
    category = "抖音"
    name = "douyin"

    def matches(self, url: str) -> bool:
        return bool(re.search(r"douyin\.com|v\.douyin\.com", url))

    def extract(self, url: str, config: dict) -> RawArticle:
        """Extract Douyin video via user-provided local API."""
        douyin_config = config.get("sources", {}).get("douyin", {})
        api_url = douyin_config.get("api_url", "")
        timeout = douyin_config.get("timeout", 600)

        if not api_url:
            raise ExtractionError(
                "抖音链接需要配置 douyin_api_url。\n"
                "请在 ~/.obsidian-capture/config.yaml 中设置:\n"
                "  sources:\n"
                "    douyin:\n"
                "      api_url: 'http://localhost:5050'",
                exit_code=4,
            )

        # Extract video ID from URL
        douyin_id = self._extract_id(url)

        try:
            from urllib.request import Request, urlopen
        except ImportError:
            raise ExtractionError("Python urllib not available", exit_code=2)

        # Step 1: Get video metadata
        try:
            req = Request(
                f"{api_url.rstrip('/')}/api/video/info",
                method="POST",
                data=json.dumps({"url": url}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urlopen(req, timeout=30) as resp:
                meta = json.loads(resp.read().decode())
        except Exception as e:
            raise ExtractionError(f"抖音 API 不可达: {api_url}\n错误: {e}", exit_code=5)

        # Step 2: Get transcription
        try:
            req = Request(
                f"{api_url.rstrip('/')}/api/video/extract",
                method="POST",
                data=json.dumps({"url": url, "model": "small"}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urlopen(req, timeout=timeout) as resp:
                transcript = json.loads(resp.read().decode())
        except Exception as e:
            transcript = {"text": "", "error": str(e)}

        # Build article
        title = meta.get("title", "无标题")
        author = meta.get("author", "未知作者")
        date_str = meta.get("date", None)
        text_body = transcript.get("text", "")
        if not text_body:
            text_body = meta.get("description", "无文案内容")

        tags = self._extract_tags(title, text_body)

        return RawArticle(
            title=f"{author} - {title}",
            author=author,
            date=date_str,
            body=text_body,
            source_url=url,
            category=self.category,
            douyin_id=douyin_id,
            tags=tags,
            original_meta=meta,
        )

    def _extract_id(self, url: str) -> str:
        """Extract douyin video ID from URL."""
        # Try to find video ID patterns
        m = re.search(r"/video/(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"video/(\d+)", url)
        if m:
            return m.group(1)
        # For short URLs, the redirect path contains the ID
        m = re.search(r"/(\d{10,})/?", url)
        if m:
            return m.group(1)
        return "unknown"

    def _extract_tags(self, title: str, body: str) -> list[str]:
        """Extract basic tags."""
        tags = []
        keyword_map = {
            "AI": "AI",
            "人工智能": "AI",
            "机器人": "机器人",
            "科技": "科技",
            "财经": "财经",
            "股票": "财经",
            "区块链": "区块链",
            "macbook": "MacBook",
            "编程": "编程",
            "python": "Python",
            "面试": "面试",
            "深度学习": "深度学习",
            "具身智能": "具身智能",
        }
        combined = f"{title}\n{body[:2000]}".lower()
        for key, tag in keyword_map.items():
            if key.lower() in combined:
                tags.append(tag)
        if not tags:
            tags.append("未分类")
        return list(dict.fromkeys(tags))
