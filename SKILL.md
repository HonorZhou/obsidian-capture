# obsidian-capture

当用户通过手机或桌面发送微信公众号、抖音、知乎、CSDN、少数派或 arXiv 论文链接时触发。负责提取全文内容及元数据，按 Obsidian 标准格式写入 Vault，含去重校验和关联笔记发现。

## 先读这个

`references/gotchas.md` —— 这些规则来自实践踩坑，违反将导致入库失败或数据污染。

## 入库路径映射

Vault 根目录：`D:\WorkBuddy\Claw\Obsidian\Obsidian`

| 来源 | 目录 | 文件名格式 |
|------|------|-----------|
| 微信公众号 `mp.weixin.qq.com` | `01-文章/公众号/` | `{作者}-{标题}-{日期}.md` |
| 抖音 `douyin.com` | `01-文章/抖音/` | `{作者}-{标题}-{日期}.md`（根目录单文件，纯文字入库惯例；早期版本用过 `{id}_{标题}/` 子目录，已废弃） |
| 知乎/CSDN/少数派 | `01-文章/` | `{来源}-{标题}-{日期}.md` |
| arXiv 论文 | `01-文章/论文/` | `{标题}.md` |

## 工作流概览

### 1. 抓取

- 微信公众号：`scripts/wechat_fetch.py`（requests 直抓 raw HTML，最稳）。`web_fetch` 只能拿到 JS shell，禁止用于微信。微信对 httpx 反爬，勿用 httpx 后端。
- 抖音：`scripts/douyin_fetch.py`（yt-dlp + cft cookie）拿元数据 → `--mode audio-only` 下载音频 → `scripts/transcribe_dy.py`（faster-whisper medium + CUDA）转写全文。browser-agent 方案仅作兜底。
- 知乎/CSDN/少数派/arXiv：`web_fetch(backend="auto")`，失败升 playwright。

### 2. 提取元数据

| 字段 | 说明 |
|------|------|
| `title` | 清理 `/ \ : * ? " < > |` 字符 |
| `author` | 公众号名或作者昵称，须从原文核实 |
| `date` | **必须从原文核实发布日期**，禁止用处理当天 |
| `type` | `公众号` / `抖音` / `文章` / `论文` |
| `tags` | 3-5 个技术关键词 |
| `source` | 原始 URL |
| `douyin_id` | 仅抖音，从链接提取 |

### 3. 写入

**必须用 PowerShell WriteAllText**，严禁 `write_file`：

```powershell
[System.IO.File]::WriteAllText('<路径>', $content, [System.Text.UTF8Encoding]::new($false))
```

原因：`write_file` 触发 Obsidian 文件监控钩子，douyin-capture 插件会向 frontmatter 注入 AIGC 元数据字段。

### 4. 验证

写入后读取前 15 行验证 frontmatter 未被注入：

```powershell
Get-Content '<文件路径>' -Head 15
```

### 5. 去重

```powershell
Select-String -Path 'D:\WorkBuddy\Claw\Obsidian\Obsidian\01-文章\**\*.md' -Pattern '<source_url>' -SimpleMatch
```

命中则跳过。**抖音必须先按 `douyin_id` 精确查重**（同一视频可能换标题重复出现，只查标题会漏——2026-08-25 实测踩坑：赛文乔伊视频重复入库浪费一次下载+CUDA 转写）：

```bash
grep -rn "douyin_id: 7677xxxx" "01-文章/抖音/抖音内容索引.md"   # 或 Grep 工具搜 douyin_id
```

### 6. 关联分析

每篇笔记末尾附加「与你的关联分析」小节，结合具身智能/深度学习/嵌入式Linux三个方向分析关联价值。

## 模板文件

`assets/` 目录包含各来源的 Jinja2 模板。关键差异：

- 公众号：保留原始 Markdown 正文
- 抖音：根目录单文件 + 转写信息表 + 核心观点提炼（含 ASR 专名校正，见 gotchas）
- 全部来源：末尾加关联分析

## 验证脚本

`scripts/verify_note.ps1` 和 `scripts/check_dup.ps1` 提供独立的命令行验证和去重检查。

## 抓取脚本（2026-08 新增）

| 脚本 | 用途 | 依赖 |
|---|---|---|
| `scripts/wechat_fetch.py` | 公众号直抓：requests → 元数据 → 正文转 Markdown | requests（default venv） |
| `scripts/douyin_fetch.py` | 抖音：yt-dlp + cft cookie 元数据/下载（`--mode audio-only`） | yt-dlp、ffmpeg、cft profile |
| `scripts/transcribe_dy.py` | 音频 → transcript.json（faster-whisper medium + CUDA） | Anaconda python + faster-whisper |

> 三个脚本与 GitHub `HonorZhou/honorzhou-skills`（douyin-to-obsidian / wechat-to-obsidian skill）共用，修改后两端同步。
