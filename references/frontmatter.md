# Frontmatter 规范

## 标准字段（7 个）

```yaml
---
title: 文章标题
author: 作者名
date: YYYY-MM-DD
type: 公众号 | 抖音 | 文章 | 论文
tags: [标签1, 标签2, 标签3]
source: https://...
douyin_id: video_id  # 仅抖音
---
```

## 字段约束

| 字段 | 必填 | 约束 |
|------|------|------|
| title | 是 | 原文标题，清理 `/ \ : * ? " < > |` 字符。不超过 200 字符 |
| author | 是 | 从原文核实，不可凭猜测。同一会话中不同来源不可混淆 |
| date | 是 | YYYY-MM-DD，须从原文核实，禁止默认处理当天 |
| type | 是 | 枚举值：`公众号` / `抖音` / `文章` / `论文` |
| tags | 是 | YAML 列表格式，3-5 个技术关键词，中英文均可 |
| source | 条件 | 公众号和抖音必填，填原文 URL。其他来源可选 |
| douyin_id | 条件 | 仅抖音需要，从链接中提取数字 ID |

## 黑名单（必须排除）

以下字段绝对不能出现，如检测到立即清理：

- ContentProducer
- ProduceID
- Label
- douyin_author
- douyin_description
- douyin_create_time
- douyin_modify_time
- AIGC
- ai_generated
- any other field beyond the 7 standard fields

## 示例

### 微信公众号

```yaml
---
title: 行业杂谈 | Claude Code Skills 机制解析以及自主学习进化
author: 敢敢AUTOHUB
date: 2026-07-15
type: 公众号
tags: [Claude Code, Skills, AI工程, Agent]
source: https://mp.weixin.qq.com/s/xS2-MW129USsWn9VnEjgqA
---
```

### 抖音

```yaml
---
title: 美联储降息对A股的影响
author: 小A学财经
date: 2026-06-30
type: 抖音
tags: [宏观经济, 美联储, A股, 降息]
source: https://v.douyin.com/xxx
douyin_id: 1234567890123456789
---
```

### arXiv 论文

```yaml
---
title: NanoWorld: A 3D World Model for Robot Manipulation
author: NanoWorld Team
date: 2026-07-09
type: 论文
tags: [world model, manipulation, sim-to-real]
source: https://arxiv.org/abs/2607.xxxxx
---
```
