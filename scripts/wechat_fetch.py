# -*- coding: utf-8 -*-
"""微信公众号文章抓取工具（可复用）

对标 scripts/douyin_fetch.py 的抖音抓取，本脚本负责微信公众号文章：
抓取 raw HTML → 解析元数据 → 提取正文 → HTML→Markdown 转换。

用法:
    # 打印元数据 + 保存正文 markdown
    python wechat_fetch.py https://mp.weixin.qq.com/s/XXXX -o body.md

    # 只打印元数据（JSON，便于脚本化）
    python wechat_fetch.py https://mp.weixin.qq.com/s/XXXX --meta-only

    # 从已保存的 HTML 解析（避免重复抓取）
    python wechat_fetch.py --file page.html -o body.md

依赖: requests（venv: C:/Users/Administrator/.workbuddy/binaries/python/envs/default）
踩坑备忘（2026-08-20 实测）:
    1. 正文 div 正则必须 <div[^>]*id="js_content"[^>]*> —— 真实 HTML 中
       id 前有 class 等属性，严格 <div id="js_content" 匹配不到。
    2. var msg_title = 'xxx'.html(false); 带 .html(false) 后缀，
       须匹配单引号包裹的标题 + 转义的 .html(false) 结尾（见 parse_meta），
       失败再回退 og:title。
    3. web_fetch 工具只能拿到 JS shell，必须 requests 直抓 raw HTML。
"""
import argparse
import html as ihtml
import json
import re
import sys
from datetime import datetime, timezone, timedelta

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
TZ_CN = timezone(timedelta(hours=8))


# ---------------------------------------------------------------- 抓取
def fetch(url: str, timeout: int = 30) -> str:
    r = requests.get(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return r.text


# ---------------------------------------------------------------- 解析
def _grab(raw: str, pat: str) -> str:
    m = re.search(pat, raw, re.S)
    return m.group(1).strip() if m else ""


def parse_meta(raw: str) -> dict:
    """解析公众号文章元数据。"""
    title = _grab(raw, r"var msg_title = '(.*?)'\.html\(false\)")
    if not title:
        title = _grab(raw, r'<meta property="og:title" content="(.*?)"')
    author = _grab(raw, r'var nickname = htmlDecode\("(.*?)"\);')
    if not author:
        author = _grab(raw, r'<meta property="og:article:author" content="(.*?)"')
    user_name = _grab(raw, r'var user_name = "(.*?)";')
    desc = _grab(raw, r'var msg_desc = htmlDecode\("(.*?)"\);')
    ct_s = _grab(raw, r'var ct = "(\d+)"')

    pubdate = ""
    ct = 0
    if ct_s.isdigit():
        ct = int(ct_s)
        pubdate = datetime.fromtimestamp(ct, tz=TZ_CN).strftime("%Y-%m-%d")

    return {
        "title": title,
        "author": author,
        "user_name": user_name,
        "desc": desc,
        "ct": ct,
        "pubdate": pubdate,
    }


def extract_body(raw: str) -> str:
    """提取 js_content 内部 HTML。"""
    m = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)<script', raw, re.S)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- 转换
def html_to_markdown(body: str) -> str:
    """HTML 正文 → Markdown（保留标题/加粗/引用/图片/段落）。"""
    b = body
    # 图片：优先 data-src（懒加载），回退 src
    b = re.sub(r'<img[^>]*?data-src="([^"]+)"[^>]*>', r'![image](\1)', b)
    b = re.sub(r'<img[^>]*?src="([^"]+)"[^>]*>', r'![image](\1)', b)
    # 标题
    b = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n', b, flags=re.S)
    b = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', b, flags=re.S)
    b = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', b, flags=re.S)
    # 引用 / 加粗 / 斜体
    b = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'> \1\n', b, flags=re.S)
    b = re.sub(r'<(strong|b)[^>]*>(.*?)</\1>', r'**\2**', b, flags=re.S)
    b = re.sub(r'<(em|i)[^>]*>(.*?)</\1>', r'*\2*', b, flags=re.S)
    # 段落与换行
    b = re.sub(r'</p>', '\n', b)
    b = re.sub(r'<br\s*/?>', '\n', b)
    b = re.sub(r'</section>', '\n', b)
    b = re.sub(r'</div>', '\n', b)
    # 清理残留标签 + 反转义
    b = re.sub(r'<[^>]+>', '', b)
    b = ihtml.unescape(b)
    # 空白规整
    b = re.sub(r'\n{3,}', '\n\n', b)
    b = re.sub(r'[ \t]+\n', '\n', b)
    b = re.sub(r'!\[image\]\(\s*\)', '', b)
    return b.strip()


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser(description="微信公众号文章抓取工具")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("url", nargs="?", help="mp.weixin.qq.com 文章链接")
    src.add_argument("--file", help="从本地 HTML 文件读取（跳过网络抓取）")
    ap.add_argument("-o", "--output", help="正文 Markdown 输出路径（不指定则不落盘）")
    ap.add_argument("--meta-only", action="store_true", help="仅打印元数据 JSON")
    ap.add_argument("--timeout", type=int, default=30, help="抓取超时秒数（默认 30）")
    args = ap.parse_args()

    # 1. 取 raw HTML
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            raw = f.read()
    else:
        try:
            raw = fetch(args.url, timeout=args.timeout)
        except Exception as e:  # noqa: BLE001
            print(f"FETCH_ERR: {e}", file=sys.stderr)
            return 1

    # 2. 元数据
    meta = parse_meta(raw)
    body = extract_body(raw)
    md = html_to_markdown(body) if body else ""
    meta["body_len"] = len(body)
    meta["md_len"] = len(md)

    if args.meta_only:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0

    # 3. 默认输出：人类可读摘要
    print("TITLE   :", meta["title"] or "(未提取到)")
    print("AUTHOR  :", meta["author"] or "(未提取到)")
    print("WXID    :", meta["user_name"])
    print("PUBDATE :", meta["pubdate"])
    print("DESC    :", meta["desc"][:120] if meta["desc"] else "")
    print("BODY_LEN:", meta["body_len"], "| MD_LEN:", meta["md_len"])

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"BODY_SAVED: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
