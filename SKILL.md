# obsidian-capture

当用户通过手机或桌面发送微信公众号、抖音、知乎、CSDN、少数派或 arXiv 论文链接时触发。负责提取全文内容及元数据，按 Obsidian 标准格式写入 Vault，含去重校验和关联笔记发现。

## 先读这个

`references/gotchas.md` —— 这些规则来自实践踩坑，违反将导致入库失败或数据污染。

## 入库路径映射

Vault 根目录：`D:\WorkBuddy\Claw\Obsidian\Obsidian`

| 来源 | 目录 | 文件名格式 |
|------|------|-----------|
| 微信公众号 `mp.weixin.qq.com` | `01-文章/公众号/` | `{作者}-{标题}-{日期}.md` |
| 抖音 `douyin.com` | `01-文章/抖音/{id}_{标题}/` | `{id}_{标题}.md`（子目录） |
| 知乎/CSDN/少数派 | `01-文章/` | `{来源}-{标题}-{日期}.md` |
| arXiv 论文 | `01-文章/论文/` | `{标题}.md` |

## 工作流概览

### 1. 抓取

- 微信公众号：`web_fetch(backend="playwright")`。不可用 auto/httpx。
- 抖音：派 `browser-agent` 打开链接，提取标题、作者、视频描述文本。
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

命中则跳过。

### 6. 关联分析

每篇笔记末尾附加「与你的关联分析」小节，结合具身智能/深度学习/嵌入式Linux三个方向分析关联价值。

## 模板文件

`assets/` 目录包含各来源的 Jinja2 模板。关键差异：

- 公众号：保留原始 Markdown 正文
- 抖音：子目录结构 + 视频信息表 + 核心内容提炼
- 全部来源：末尾加关联分析

## 验证脚本

`scripts/verify_note.ps1` 和 `scripts/check_dup.ps1` 提供独立的命令行验证和去重检查。
