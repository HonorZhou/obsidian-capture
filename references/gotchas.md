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
