"""Academic paper source (PDF from arXiv or direct links)."""

import os
import re
import tempfile

from .base import SourceBase, RawArticle, ExtractionError


class PaperSource(SourceBase):
    category = "论文"
    name = "paper"

    def matches(self, url: str) -> bool:
        return "arxiv.org" in url.lower() or url.lower().endswith(".pdf")

    def extract(self, url: str, config: dict) -> RawArticle:
        """Download PDF and extract text."""
        try:
            from urllib.request import Request, urlopen
        except ImportError:
            raise ExtractionError("Python urllib not available", exit_code=2)

        # Convert arxiv.org/abs/ URL to PDF
        pdf_url = url
        if "arxiv.org/abs/" in url:
            arxiv_id = url.split("/abs/")[-1].rstrip("/")
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        # Download PDF
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        try:
            req = Request(pdf_url, headers=headers)
            with urlopen(req, timeout=60) as resp:
                content_length = resp.headers.get("Content-Length")
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    max_size = config.get("sources", {}).get("paper", {}).get("max_size_mb", 50)
                    if size_mb > max_size:
                        raise ExtractionError(
                            f"PDF 过大（{size_mb:.1f}MB），超过限制 {max_size}MB", exit_code=6
                        )
                pdf_data = resp.read()
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"无法下载 PDF: {e}", exit_code=2)

        # Save to temp file
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(pdf_data)
                tmp_path = f.name

            # Extract text
            body = self._extract_pdf_text(tmp_path)
            if not body or len(body.strip()) < 100:
                raise ExtractionError("PDF 文本提取失败，可能为扫描件或加密文档", exit_code=2)

            # Extract metadata
            title = self._extract_title(body) or "未知标题"
            author = self._extract_author(body) or "未知作者"
            date_str = self._extract_date(url, body)

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

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF using pdfplumber."""
        try:
            import pdfplumber
        except ImportError:
            raise ExtractionError(
                "pdfplumber 未安装。请运行: pip install pdfplumber", exit_code=2
            )

        with pdfplumber.open(pdf_path) as pdf:
            texts = []
            for page in pdf.pages[:50]:  # First 50 pages max
                text = page.extract_text()
                if text:
                    texts.append(text)

        return "\n\n".join(texts)

    def _extract_title(self, text: str) -> str | None:
        """Extract title from first lines of PDF text."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        # Title is usually the first substantive line(s)
        for i in range(min(5, len(lines))):
            if len(lines[i]) > 20 and not lines[i].startswith("arXiv:"):
                return lines[i]
        return None

    def _extract_author(self, text: str) -> str | None:
        """Extract authors from text."""
        # Look for author line after title
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines[:10]:
            if "," in line and not any(
                kw in line.lower()
                for kw in ["abstract", "university", "department", "arxiv"]
            ):
                # Likely an author line
                authors = [a.strip() for a in line.split(",")]
                if len(authors) >= 2:
                    # Return first 3 authors max
                    return ", ".join(authors[:3]) + (
                        " et al." if len(authors) > 3 else ""
                    )
        return None

    def _extract_date(self, url: str, body: str) -> str | None:
        """Extract date from arXiv ID or body."""
        # arXiv ID encodes date: arXiv:YYMM.NNNNN
        m = re.search(r"arxiv\.org/abs/(\d+)", url)
        if m:
            arxiv_id = m.group(1)
            if len(arxiv_id) >= 4:
                yy = int(arxiv_id[:2])
                mm = int(arxiv_id[2:4])
                year = 2000 + yy
                return f"{year}-{mm:02d}"

        # Look for date in text
        m = re.search(r"(\d{4}-\d{2}-\d{2})", body[:500])
        if m:
            return m.group(1)

        return None

    def _extract_tags(self, title: str, body: str) -> list[str]:
        """Extract research area tags."""
        tags = []
        keyword_map = {
            "reinforcement learning": "强化学习",
            "deep learning": "深度学习",
            "neural network": "深度学习",
            "transformer": "Transformer",
            "robot": "机器人",
            "robotics": "机器人",
            "embodiment": "具身智能",
            "manipulation": "灵巧操作",
            "vision-language": "VLA",
            "diffusion": "扩散模型",
            "llm": "LLM",
            "large language model": "LLM",
            "policy": "策略学习",
            "imitation": "模仿学习",
            "sim-to-real": "Sim2Real",
        }
        combined = f"{title}\n{body[:2000]}".lower()
        for key, tag in keyword_map.items():
            if key in combined:
                tags.append(tag)
        if not tags:
            tags.append("论文")
        return list(dict.fromkeys(tags))
