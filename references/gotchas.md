# 坑点清单

以下规则来自 2026-07-03 ~ 2026-07-15 期间数十次入库操作的实践总结。每一条都对应至少一次失败案例。

## 写入方式：write_file 会触发污染

- write_file 创建新文件时，Obsidian 的 douyin-capture 插件监控到文件系统事件，自动向 frontmatter 注入 AIGC 元数据块（ContentProducer / ProduceID / Label 等字段）
- edit_file 修改已有文件时，插件二次扫描文件变更，**再次注入**
- 实测同一文件被注入后，edit_file 修复 → 插件二次注入 → 再修复 → 可能再次注入。无法通过"写入后修复"解决
- **唯一可靠方案**：PowerShell `[System.IO.File]::WriteAllText`，绕过 Obsidian 全部文件监控钩子

## 日期：不能默认当天

- web_fetch 返回的 Markdown 正文不一定包含发布日期
- 若未提取到日期，**必须**派 browser-agent 打开原文页面确认
- 禁止以处理当天日期填入 frontmatter
- 多个入库案例因日期字段错误需要后续修正

## 微信公众号：httpx 后端必返回空

- 微信 mp.weixin.qq.com 对 httpx 请求有严格反爬
- web_fetch 默认 auto 后端在微信场景大概率回退到 httpx → 返回空正文
- **必须显式指定 `backend="playwright"`**

## AIGC 注入字段黑名单

以下字段**绝对不能**出现在 frontmatter 中：

- ContentProducer
- ProduceID
- Label
- douyin_author
- douyin_description
- douyin_create_time
- douyin_modify_time
- AIGC
- ai_generated

## 文末 AI 尾注

douyin-capture 注入 AIGC 元数据块时，可能在文末追加"内容由AI生成，仅供参考"等尾注。写入后验证时一并检查文末。

## frontmatter 字段：不超过 7 个

标准字段：title / author / date / type / tags / source / douyin_id

douyin_id 仅抖音需要。其他来源不出现此字段。

## 抖音笔记目录结构

抖音笔记需要创建 `{douyin_id}_{标题}/` 子目录，笔记文件和封面图放在该目录内。直接放在 `01-文章/抖音/` 根目录会导致封面图无处存放。

## 微信公众号 author 字段

公众号名称必须从原文页面提取，不可凭同一会话中其他文章推测。不同公众号作者名不可混淆。

## 写入后验证是强制的

无论用什么方式写入，写入后必须读取前 15 行确认 frontmatter 干净。跳过验证的案例中约 30% 事后发现 AIGC 注入。

## 去重用 source URL 精确匹配

去重依据是 frontmatter 的 source 字段（原始 URL），不是标题。同一篇文章可能在不同时间被不同标题转发，但 source URL 唯一。

## 2026-08 新增坑点（wechat_fetch / douyin_fetch 时代）

### 微信正文 div 正则必须宽松匹配

真实 HTML 中 `js_content` 的 id 前有 class 等属性，严格写 `<div id="js_content"` 匹配不到：

```python
re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)<script', raw, re.S)
```

### 微信标题正则带 .html(false) 后缀

`var msg_title = 'xxx'.html(false);` 带 `.html(false)` 结尾，须匹配：

```python
r"var msg_title = '(.*?)'\.html\(false\)"
```

失败再回退 `og:title`。作者同理：`var nickname = htmlDecode\("(.*?)"\);`，失败回退 `og:article:author`。

### web_fetch 只能拿 JS shell，微信必须 requests 直抓

网页抓取工具拿到的公众号页面是 JS 壳，正文/元数据全在服务端渲染。必须用 `wechat_fetch.py` 的 requests 直抓 raw HTML。微信对 httpx 反爬（返回空），勿用 httpx 后端。

### douyin_fetch.py 参数是 --mode audio-only

不是 `--audio-only`（会报 unrecognized arguments）。完整：`python douyin_fetch.py <链接> --mode audio-only --out temp/dy_<name>`。

### 抖音入库前必须按 douyin_id 查重

2026-08-25 实测：赛文乔伊"网球人机对打"视频，08-22 已按旧标题入库，08-25 用新标题重复下载+转写+建笔记才发现——浪费一次下载+CUDA 转写。**元数据拿到后先 Grep `douyin_id` 再动手**。

### yt-dlp --json 偶发抖动

`douyin_fetch.py --json` 偶发 `'NoneType' object has no attribute 'get'` → 直接重试即可（网络抖动）。

### 后台任务 ID 可能丢失

长任务（下载/转写）后台运行时 task_id 可能查不到——用文件系统核查产物（`temp/dy_xxx/*.m4a`、`transcript.json`），别依赖 task_id 轮询。

### 抖音转写 ASR 专名必须人工校正

faster-whisper medium 中文口播常见同音错字，入库笔记前必须订正：

- 行业术语：巨深智能→具身智能、清言/清严/轻言精准→（按上下文还原公司名，不确定问用户）
- 同音字：中式→中试、弊常→臂长、重应设→重定向、一场→异常、导班→倒班、常委→常态
- 人名/公司名拿不准 → 笔记尾部标注"待核实"，或问用户确认（2026-08-25 用户确认"清研精准"纠正了 ASR 推断的"清岩智能"）

### 转写产物保留 transcript.json，删大文件

入库完成后删除 m4a/mp4 大文件，保留 `transcript.json`（笔记引用来源指向它，留作证据）。

### 抖音笔记目录结构已变

早期版本用 `{douyin_id}_{标题}/` 子目录（封面图无处存放），2026-08 纯文字入库惯例已改为 `01-文章/抖音/` 根目录单文件 `{作者}-{标题}-{日期}.md`。新笔记一律根目录单文件。
