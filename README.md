# obsidian-capture

AI Skill for capturing articles from WeChat Official Account, Douyin, Zhihu, CSDN, Sspai, and arXiv into Obsidian with structured frontmatter.

## Design Philosophy

Built following Claude Code Skills best practices:

- **Folder, not file** — SKILL.md + references/ + scripts/ + assets/
- **Progressive disclosure** — description → SKILL.md → sub-files on demand
- **Gotchas first** — the most valuable content is what only practice can teach
- **Don't state the obvious** — Claude already knows how to web_fetch and write files

## Structure

```
obsidian-capture/
├── SKILL.md                    # Main entry — loaded when description matches
├── references/
│   ├── gotchas.md              # Pitfalls from real-world use (most valuable)
│   ├── frontmatter.md          # Frontmatter field specification
│   ├── vault-structure.md      # Obsidian vault directory layout
│   └── templates.md            # Output templates per source
├── scripts/
│   ├── verify_note.ps1         # Post-write frontmatter validation
│   └── check_dup.ps1           # Deduplication check
├── assets/
│   ├── wechat.md.j2
│   ├── douyin.md.j2
│   ├── web_article.md.j2
│   └── paper.md.j2
└── README.md
```

## Supported Sources

| Source | URL Pattern | Method |
|--------|-------------|--------|
| 微信公众号 | `mp.weixin.qq.com/s/...` | playwright backend |
| 抖音 | `v.douyin.com/...` or `douyin.com/video/...` | browser-agent |
| 知乎 / CSDN / 少数派 | respective domains | auto → playwright fallback |
| arXiv | `arxiv.org/abs/...` | auto |

## Key Gotchas

1. Never use `write_file` — triggers douyin-capture AIGC injection. Use PowerShell WriteAllText.
2. Always verify publication date from source — never default to today.
3. WeChat articles must use `web_fetch(backend="playwright")`.
4. AIGC fields (ContentProducer, ProduceID, Label, etc.) are blacklisted.
5. Post-write verification is mandatory — read first 15 lines to confirm clean.

See `references/gotchas.md` for the full list.

## License

MIT
