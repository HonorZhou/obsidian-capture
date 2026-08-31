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

~~需要创建 `{douyin_id}_{标题}/` 子目录~~ —— **此条已作废**。2026-08 起纯文字入库惯例改为 `01-文章/抖音/` **根目录单文件** `{作者}-{标题}-{日期}.md`，逐字稿证据件按 `<笔记名>_transcript.json` / `.txt` 同名并存。详见文末「抖音笔记目录结构已变」。旧条文若被照用，会让笔记脱离索引与 `01-文章/抖音/` 的扁平检索路径。

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

## 2026-08-30 新增坑点（第二台设备实机跑通：i7-11800H + RTX 3050 Ti 4GB + 16GB 内存）

以下每一条都在这一天的连续 5 条视频入库中真实踩过。

### 5050 后端彻底失效，别再试

`douyin-capture` 后端（`127.0.0.1:5050`，靠解析 `_ROUTER_DATA`）已被抖音改版**全网击穿**：分享页只返回 JS 壳，`_ROUTER_DATA` 里只有 `loaderData` 的页面上下文字段，**没有 item_list / desc / author / statistics**。旧版 `iteminfo` 接口也返回空。唯一正解是 yt-dlp。

### msToken 走响应头，必须拦截后手动提升为 cookie

yt-dlp 的 Douyin 提取器要求 `Fresh cookies`，实测它真正需要的是 **`msToken`**：

- `msToken` **不再通过 Set-Cookie 下发**，而是出现在响应的 **`x-ms-token` 头**里；`webid` 藏在 passport 接口 JSON 中。所以轮询 cookie 永远等不到它们。
- 解法：Playwright 里 `page.on("response", ...)` 捕获 `x-ms-token`，再用 `ctx.add_cookies()` 以 `.douyin.com` 域写回，最后导出 Netscape `cookies.txt`。
- **只要 `msToken` 就够，`webid` 缺失不影响抓取。**
- 只自助注册匿名 `ttwid`（POST `ttwid.bytedance.com/ttwid/union/register/`，返回 `union register success`）**不够**，yt-dlp 仍判 cookie 不新鲜。
- 无头 Chromium 需带反自动化参数（`--disable-blink-features=AutomationControlled`、`navigator.webdriver` 打码）**加持久化 profile**，否则只采到 9 个基础 cookie、拿不到签名项；配好后能采到 38 项含 `bd_ticket_guard_client_data` / `odin_tt` / `bit_env`。

### 绝不读用户正在使用的浏览器

`--cookies-from-browser edge` 在 Edge 运行时会 **`PermissionError: [Errno 13] Permission denied: ...\Edge\User Data\Default\Network\Cookies`**（yt-dlp issue #7271）——浏览器独占锁定 cookie 库，连复制都不行。而且要求用户退出浏览器本身就是扰民。正确做法：**用 Playwright 自带 Chromium + 独立 profile 自己采 cookie**，写进 `cookies.txt` 后用 `--cookies`。

### cookie 与下载必须在同一命令里背靠背

`msToken` 时效只有几分钟。实测：刷完 cookie → 抓元数据（成功）→ 查格式列表 → 再下载，**就报 `Fresh cookies are needed` 了**。把「刷 cookie + 下载」写进同一个 shell 调用连续执行；中间不要插入耗时请求。

### `-S size` 会选到 4 倍大的文件

想挑最小文件而用 `-S size`，结果选中的是 `download_addr-*`（带水印的下载源，实测 44.5MB），而不是真正的最小档 `bytevc1_540p_*`（h265，同片仅 8–30MB）。**正确做法：自己解析 `-J` 输出的 `formats[].filesize` 排序**，取 `bytevc1_540p*`。

### 同一格式有多个 CDN 镜像 host，部分不可达

每个 format_id 都有 `-0/-1/-2/-3` 四个变体，分别指向 `api-play-hl.amemv.com` / `api.amemv.com` / `v6-default.365yg.com` / `v95-ynkmtc-default.365yg.com` 等。实测 **`v95-ynkmtc-*` 完全连不通**（connect timeout），而 `v6-default`、`v11-default`、amemv API 可达。

- 用 `-f "id-3/id-2/id-0"` 写**降级链**，不要只给一个格式号。
- 探活技巧：`curl -m 8 https://<host>/` 返回 **403/404 即为可达**（根路径无资源正常），返回 `000` 才是真不可达。

### GPU 缺库时：cuDNN 已在包里，通常只缺 cuBLAS

`ctranslate2` 报 `Library cublas64_12.dll is not found` 时，**不要急着下 1GB 的 cuBLAS+cuDNN**：

- **`cudnn64_9.dll` 本来就打包在 `site-packages/ctranslate2/` 里**（和 `ctranslate2.dll`、`libiomp5md.dll` 同目录）。
- 唯一缺的就是 `cublas64_12.dll`。机器上任意一个装了 `nvidia-cublas-cu12` 的 venv（`site-packages/nvidia/cublas/bin/`）里现成有，**把 `cublas64_12.dll` + `cublasLt64_12.dll` 拷进 ctranslate2 目录即可点亮 CUDA**，零下载。
- 验证方式：`ctranslate2.get_cuda_device_count()` 返回 1 只说明能**枚举**设备，`WhisperModel(..., device="cuda")` 能加载也只说明权重进得去显存——**必须真跑一次 transcribe 才会暴露 cuBLAS 缺失**。
- 效果：medium float16 在 RTX 3050 Ti 上 **4.6 倍速**（125s→27s，515s→约 1.5min）。走 GPU 几乎不占内存，反而是内存紧张时的首选路径。

### 国内网络：pip 与 HF 都必须走镜像

- PyPI 直连在这条网路上会**大文件反复断流零进度重连**（`resume incomplete download (0 bytes/...)`），严重时索引查询直接返回空、报 `from versions: none`。换 `-i https://pypi.tuna.tsinghua.edu.cn/simple/` 后立刻正常（`mirrors.aliyun.com` 亦可）。
- HuggingFace 下载缺 `model.bin` 且报 `cas-server.xethub.hf.co ... 401`：这是 **xet 加速协议绕过镜像直连官方 CAS**。设 `HF_HUB_DISABLE_XET=1` + `HF_ENDPOINT=https://hf-mirror.com` 走普通 HTTP 才能拿到完整快照。

### 脚本会吞掉 yt-dlp 的真实报错

`douyin_fetch.py --json` 在 yt-dlp 失败时，因为 yt-dlp 输出字符串 `null`、`json.loads("null")` 得 None，最终抛出的是**误导性的 `'NoneType' object has no attribute 'get'`**，且 `stderr` 被丢弃。排查时**务必跑原生 `python -m yt_dlp -J <url>` 看 stderr**，否则会误判成"网络抖动，重试即可"。（本条已修：脚本改抛真实错误。）

### ASR 中文输出偶发繁体，入库前要过 zhconv

faster-whisper 对同一台机器、同一 model 的多条视频，输出可能是**繁体**（实测《滚雪球》30 番外 5309 字全篇繁体）。入库前统一：

```python
from zhconv import convert
convert(text, "zh-cn")   # text 与每个 segment.text 都要转
```

`zhconv` 本来就在抖音入库 SOP 的依赖清单里，但 `transcribe_dy.py` 此前没有调用——**属于依赖列了却没用的漏点**。

### Windows 控制台与 PowerShell 的编码陷阱

- git-bash 终端是 GBK：中文 stdout 显示乱码（文件本身没问题）、打印 `⚠️/✅` 会 `UnicodeEncodeError: 'gbk' codec`。脚本里日志用 ASCII 前缀（`!!` / `>>`），或设 `PYTHONIOENCODING=utf-8`。
- **无 BOM 的 `.ps1` 会被 Windows PowerShell 按 GBK 解析**，脚本里的中文路径字面量直接变乱码并报"路径中有非法字符"。对策：**`.ps1` 保持纯 ASCII，中文路径通过环境变量或 UTF-8 清单文件传入**，脚本内用 `[System.IO.File]::ReadAllLines($m, UTF8)` 读。
- 校验落盘是否无 BOM，看首三字节即可（`efbbbf` = 有 BOM）；写 vault 笔记仍必须 `[System.IO.File]::WriteAllText($p,$t,[System.Text.UTF8Encoding]::new($false))`。

### 本机环境陷阱：别信文档里的解释器路径

skill 文档写的 `D:/ANACONDA/python.exe（torch 2.7 cu128 + faster-whisper）` 在这台机器上**是 `torch 2.12.0+cpu` 且根本没装 faster-whisper/ctranslate2**——路径存在但完全不可用。教训：**跨设备复用 skill 前先实测版本与 CUDA 可用性，不要因路径存在就直接采信文档**。同理 `python` 可能只解析到微软商店的占位 stub（`WindowsApps\python.exe`），它静默失败、不报错。

### 内存与磁盘

- 16GB 机器实测可用仅 0.6–1.6GB，主因是**向日葵（AweSun）的 `OrayVGC.sys` / `OrayUSBVHCI.sys` 驱动占用非分页池约 3.07GB**（正常应 <1GB）——**关普通程序腾不出来，只有停用该驱动或重启才能回收**。判断依据：`Get-Counter '\Memory\Pool Nonpaged Bytes'`。
- 系统盘紧张（剩 12GB、93% 满）时，venv 和 Playwright 浏览器一律装到别的盘：`python -m venv D:\tools\dy-venv`、`PLAYWRIGHT_BROWSERS_PATH=D:\tools\ms-playwright`（否则 Chromium 默认吃掉 C 盘 700MB）。

## 2026-08-31 新增：把脚本改动推回 GitHub 的认证坑

### 症状识别：push 无输出、远端不动，但 ls-remote 正常

HTTPS push 在这台机器上**卡在凭据，不是网络**。特征组合非常好认：

- `git push` **一个字都不输出**就结束了（或挂到被 timeout 杀掉），远端 SHA 不变；
- 同一时刻 `git ls-remote` **秒级正常返回**。

因为公开仓库的**读是匿名的，只有写要认证**。看到"读得通、写不通"就直接按认证问题查，别去怀疑网络或代理——本次先入为主当成网络故障，白跑了一轮 HTTP/1.1 + 五次退避重试。

快速确认手段（让它立即失败而不是挂死）：

```bash
GIT_TERMINAL_PROMPT=0 git -c credential.interactive=false push origin master
# fatal: Cannot prompt because user interactivity has been disabled.
```

`cmdkey /list | grep -i github` 返回空 = Windows 凭据管理器里从来没存过 GitHub 凭据；GCM（`credential.helper = manager`，来自 Git 的 **system 级**配置，global 里查不到）在无终端环境弹不出授权窗，于是静默阻塞。

### 正解：走 SSH

本机 `~/.ssh/id_ed25519` 已绑定 GitHub 账号，22 端口与 `ssh.github.com:443` 都能过：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=15 -T git@github.com
# Hi <用户>! You've successfully authenticated, but GitHub does not provide shell access.
```

443 那个是**备用通道**，专治 22 端口被封：`ssh -p 443 -T git@ssh.github.com`。

一次性用显式 SSH 地址推送，**不改任何 git 配置**：

```bash
git push git@github.com:<用户>/<repo>.git master
```

只有想让以后裸 `git push` 也走 SSH，才需要 `git remote set-url origin git@github.com:...` —— 那会写 `.git/config`，属配置变更，须先征求用户同意。

### 浅克隆的仓库不能直接 push

`--depth 1` clone 出来的仓库 push 会被 GitHub 拒绝（`shallow update not allowed`）。推送前先补历史：

```bash
git fetch --unshallow
test -f "$(git rev-parse --git-dir)/shallow" && echo "仍是浅仓库"
```

`fetch` 是匿名读，不需要凭据，但网络不稳时可能失败，要重试确认成功再推。

### 用显式 URL push 之后要 fetch 校准

`git push <显式URL> master` **不会更新 remote-tracking 引用**，于是 `git status` 会长期误显示"领先 origin 1 个提交"。补一次即可：

```bash
git fetch origin   # 之后 git rev-list --count origin/<branch>..HEAD 应为 0
```

### 提交身份缺失时别改全局配置

新装 Git 常没有 `user.name/email`，直接 commit 报 `Author identity unknown`。**不要为省事去写全局 config**，用一次性参数、并沿用该仓库既有提交的作者身份（不同仓库的 GitHub noreply 邮箱可能不一致，本项目两个仓库就分别是 `96284073+HonorZhou@…` 与 `honorzhou@…`）：

```bash
git log -1 --format="%an <%ae>"
git -c user.name="X" -c user.email="Y@users.noreply.github.com" commit -m "..."
```
