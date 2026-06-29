# obsidian-capture

Capture articles from WeChat, Douyin, Zhihu, CSDN, etc. and save to Obsidian with structured frontmatter.

---

## Features

- **Multi-source support**:
  - WeChat Official Account (微信公众号)
  - Douyin/TikTok CN (抖音视频，通过本地 Whisper API 转写)
  - Zhihu, CSDN, Sspai (知乎、CSDN、少数派等)
  - Academic papers (arXiv PDF)
- **Structured output**: YAML frontmatter with title/author/date/type/tags/source
- **Deduplication**: Skip already captured articles by source URL
- **Related notes**: Auto‑discover related articles via tag matching
- **Customizable**: Jinja2 templates, configurable timeouts, proxy support
- **CLI + Marvis Skill**: Use as standalone tool or integrated with Marvis

---

## Quick Start

### 1. Install

```bash
pip install obsidian-capture
```

Or from GitHub:

```bash
pip install git+https://github.com/<user>/obsidian-capture.git
```

### 2. Configure

```bash
capture --init
```

This creates `~/.obsidian-capture/config.yaml`. Edit it to set your Obsidian vault path:

```yaml
obsidian:
  vault_dir: "D:\\WorkBuddy\\Claw\\Obsidian\\Obsidian"
```

### 3. Capture

```bash
capture "https://mp.weixin.qq.com/s/xxx"
```

Output: `OK 已入库: D:\...\01-文章\公众号\公众号名-标题-2026-06-29.md`

---

## Configuration

### Config File

`~/.obsidian-capture/config.yaml`:

```yaml
obsidian:
  vault_dir: "D:\\WorkBuddy\\Claw\\Obsidian\\Obsidian"
  article_dir: "01-文章"  # relative to vault_dir

sources:
  douyin:
    api_url: "http://localhost:5050"  # your local Douyin API
    timeout: 600                      # seconds for Whisper transcription
  paper:
    max_size_mb: 50                   # skip PDFs larger than this

templates:
  custom_dir: null                    # override default templates

network:
  proxy: null                         # e.g. "http://127.0.0.1:7890"
  timeout: 30                         # seconds for HTTP requests
```

### Environment Variables

- `OBSIDIAN_CAPTURE_VAULT_DIR`
- `OBSIDIAN_CAPTURE_DOUYIN_API`
- `OBSIDIAN_CAPTURE_PROXY`

### CLI Overrides

```bash
capture "https://..." \
  --obsidian-dir "/path/to/vault" \
  --douyin-api "http://localhost:5050" \
  --template-dir "~/my-templates" \
  --proxy "http://127.0.0.1:7890" \
  --force \
  --verbose
```

---

## Templates

Default templates are in `templates/` (installed with the package). You can override them by setting `templates.custom_dir` in config.

Template variables:

| Variable | Description |
|----------|-------------|
| `title` | Article title |
| `author` | Author name |
| `date` | Publication date (YYYY-MM-DD) |
| `type` | "公众号文章" / "抖音视频" / "文章" / "论文" |
| `tags` | List of auto‑generated tags |
| `source` | Original URL |
| `body` | Article body (Markdown) |
| `douyin_id` | Douyin video ID (only for Douyin) |
| `related_notes` | List of related note filenames |

---

## Marvis Skill

The Marvis Skill is a thin wrapper that calls the CLI. To use it:

1. Install `obsidian-capture` CLI (see above)
2. Configure `~/.obsidian-capture/config.yaml`
3. Add `marvis-skill/` to your Marvis skills directory

Skill file: `marvis-skill/skill.md` (included in the repo)

---

## Development

### Setup

```bash
git clone https://github.com/<user>/obsidian-capture.git
cd obsidian-capture
pip install -e ".[dev]"
```

### Testing

```bash
pytest tests/ -v
```

### Building

```bash
hatch build
```

### Releasing

1. Update version in `pyproject.toml`
2. `git tag vX.Y.Z`
3. `hatch publish`

---

## License

MIT License. See [LICENSE](LICENSE).

---

## Roadmap

- [x] Core engine + CLI
- [x] WeChat, Douyin, generic article sources
- [x] Paper PDF source
- [x] Deduplication + related notes
- [x] Marvis Skill wrapper
- [ ] Obsidian plugin (optional)
- [ ] More sources: Bilibili, Weibo, etc.
