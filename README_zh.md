# obsidian-capture

从微信、抖音、知乎、CSDN 等平台抓取文章，自动整理为带结构化 frontmatter 的 Obsidian 笔记。

---

## 功能特性

- **多平台支持**：
  - 微信公众号（mp.weixin.qq.com）
  - 抖音视频（v.douyin.com，通过本地 Whisper API 转写）
  - 知乎、CSDN、少数派等图文文章
  - 学术论文（arXiv PDF）
- **结构化输出**：YAML frontmatter 含标题、作者、日期、类型、标签、来源
- **去重检查**：通过来源 URL 自动跳过已入库文章
- **关联笔记**：基于标签匹配自动发现相关笔记并添加双向链接
- **高度可配置**：Jinja2 模板、超时时间、网络代理
- **双重交付**：CLI 工具 + Marvis Skill，可独立使用或集成到 AI 助手

---

## 快速开始

### 1. 安装

```bash
pip install obsidian-capture
```

或从 GitHub 安装：

```bash
pip install git+https://github.com/HonorZhou/obsidian-capture.git
```

### 2. 配置

```bash
capture --init
```

这会创建配置文件 `~/.obsidian-capture/config.yaml`。编辑它，设置你的 Obsidian 库路径：

```yaml
obsidian:
  vault_dir: "D:\\WorkBuddy\\Claw\\Obsidian\\Obsidian"  # 你的 Obsidian 库路径
```

### 3. 抓取

```bash
capture "https://mp.weixin.qq.com/s/xxx"
```

输出示例：`OK 已入库: D:\...\01-文章\公众号\闲搞机-末代双系统MacBookPro无头骑士-20260629.md`

---

## 配置说明

### 配置文件

`~/.obsidian-capture/config.yaml`：

```yaml
obsidian:
  vault_dir: "D:\\WorkBuddy\\Claw\\Obsidian\\Obsidian"  # Obsidian 库根目录
  article_dir: "01-文章"  # 文章子目录（相对于 vault_dir）

sources:
  douyin:
    api_url: "http://localhost:5050"  # 你的本地抖音转写 API 地址
    timeout: 600                      # Whisper 转写超时（秒）
  paper:
    max_size_mb: 50                   # 跳过超过此大小的 PDF 文件

templates:
  custom_dir: null                    # 自定义模板目录（覆盖默认）

network:
  proxy: null                         # 网络代理，如 "http://127.0.0.1:7890"
  timeout: 30                         # HTTP 请求超时（秒）
```

### 环境变量

- `OBSIDIAN_CAPTURE_VAULT_DIR`
- `OBSIDIAN_CAPTURE_DOUYIN_API`
- `OBSIDIAN_CAPTURE_PROXY`

### CLI 参数覆盖

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

## 模板系统

默认模板位于 `templates/` 目录（随包安装）。可通过 `templates.custom_dir` 配置自定义模板。

模板变量：

| 变量 | 说明 |
|------|------|
| `title` | 文章标题 |
| `author` | 作者 |
| `date` | 发布日期（YYYY-MM-DD） |
| `type` | 类型（"公众号文章" / "抖音视频" / "文章" / "论文"） |
| `tags` | 自动生成的标签列表 |
| `source` | 原始 URL |
| `body` | 文章正文（Markdown） |
| `douyin_id` | 抖音视频 ID（仅抖音源） |
| `related_notes` | 相关笔记文件名列表 |

---

## Marvis Skill

Marvis Skill 是一个薄封装，直接调用 CLI 工具。使用方法：

1. 安装 `obsidian-capture` CLI（见上文）
2. 配置 `~/.obsidian-capture/config.yaml`
3. 将 `marvis-skill/` 目录添加到 Marvis 技能目录

技能文件：`marvis-skill/skill.md`（已包含在仓库中）

---

## 开发

### 环境搭建

```bash
git clone https://github.com/HonorZhou/obsidian-capture.git
cd obsidian-capture
pip install -e ".[dev]"
```

### 测试

```bash
pytest tests/ -v
```

### 构建

```bash
hatch build
```

### 发布

1. 更新 `pyproject.toml` 中的版本号
2. `git tag vX.Y.Z`
3. `hatch publish`

---

## 许可证

MIT 许可证。详见 [LICENSE](LICENSE)。

---

## 路线图

- [x] 核心引擎 + CLI
- [x] 微信公众号、抖音、通用图文来源
- [x] 论文 PDF 来源
- [x] 去重 + 关联笔记
- [x] Marvis Skill 封装
- [ ] Obsidian 插件（可选）
- [ ] 更多来源：B站、微博等
