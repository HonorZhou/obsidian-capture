# -*- coding: utf-8 -*-
"""浏览器兜底抓取：当 yt-dlp 对某条抖音报 Fresh cookies 但对照实验显示管线正常时使用。

原理：用 Playwright 真实浏览器打开视频页，捕获页面自身 JS 发出的 aweme/v1/web/aweme/detail
响应（status_code=0），从里面同时拿到 ①完整元数据（desc/author/create_time/statistics/时长）
②video.play_addr.url_list，再带 UA + Referer 用 curl 直接下载。

不使用任何账号凭据，等价于"用浏览器打开这个公开页面"。

用法：
    python browser_fetch.py <分享链接或视频ID> [-o OUT.mp4] [--meta-only] [--timeout 60]
产出：
    默认写 <out> 与同名 .meta.json；--meta-only 只打印元数据不下载。
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", r"D:\tools\ms-playwright")
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("[browser_fetch] 需要 playwright：pip install playwright && python -m playwright install chromium")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
REFERER = "https://www.douyin.com/"


def resolve(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("http"):
        return raw
    if raw.isdigit():
        return f"https://www.douyin.com/video/{raw}"
    raise ValueError(f"无法识别的输入: {raw}")


def capture_detail(url: str, profile: str, wait_ms: int = 7000) -> dict:
    """打开页面，返回第一条 status_code=0 且含 aweme_detail 的响应 JSON。"""
    holder = {}
    Path(profile).mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            profile, headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-first-run",
                  "--lang=zh-CN"],
            user_agent=UA, locale="zh-CN", timezone_id="Asia/Shanghai",
            viewport={"width": 1366, "height": 900})
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{},loadTimes:()=>{},csi:()=>{}};")
        page = ctx.new_page()

        def on_resp(resp):
            if holder.get("done") or "aweme/detail" not in (resp.url or ""):
                return
            try:
                body = resp.text()
            except Exception:  # noqa: BLE001
                return
            if '"aweme_detail"' in body and '"status_code":0' in body.replace(" ", ""):
                holder["detail"] = body
                holder["done"] = True

        page.on("response", on_resp)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(wait_ms)
            if not holder.get("done"):
                page.mouse.wheel(0, 500)
                page.wait_for_timeout(3500)
        except Exception as e:  # noqa: BLE001
            print(f"[browser_fetch] 页面加载异常: {type(e).__name__} {str(e)[:100]}")
        ctx.close()
    if "detail" not in holder:
        raise RuntimeError("未捕获到 aweme/detail（页面可能被登录墙/验证墙完全拦截）")
    return json.loads(holder["detail"])


def summarize(aw: dict) -> dict:
    au = aw.get("author") or {}
    st = aw.get("statistics") or {}
    v = aw.get("video") or {}
    ct = aw.get("create_time")
    return {
        "aweme_id": aw.get("aweme_id"),
        "title": aw.get("desc"),
        "channel": au.get("nickname"),
        "pubdate": (datetime.fromtimestamp(ct, timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
                    if ct else None),
        "duration_ms": v.get("duration"),
        "stats": {"digg": st.get("digg_count"), "share": st.get("share_count"),
                  "comment": st.get("comment_count"), "collect": st.get("collect_count")},
    }


def download(urls, dest: Path) -> bool:
    for u in urls:
        r = subprocess.run(["curl", "-sL", "-m", "300", "--fail", "-A", UA,
                            "-H", f"Referer: {REFERER}", "-o", str(dest), u],
                           capture_output=True, text=True)
        if r.returncode == 0 and dest.exists() and dest.stat().st_size > 200_000:
            print(f"[browser_fetch] ✅ 下载成功 {dest.stat().st_size} bytes")
            return True
        print(f"[browser_fetch] ✗ 该地址失败 (rc={r.returncode})")
    return False


def main():
    ap = argparse.ArgumentParser(description="抖音视频浏览器兜底抓取")
    ap.add_argument("url", help="分享链接或视频 ID")
    ap.add_argument("-o", "--out", default=None, help="输出 mp4 路径")
    ap.add_argument("--meta-only", action="store_true", help="只取元数据不下载")
    ap.add_argument("--profile", default=os.environ.get("DY_BROWSER_UDD", r"D:\tools\pw-browser-fetch"))
    args = ap.parse_args()

    page_url = resolve(args.url)
    try:
        d = capture_detail(page_url, args.profile)
    except Exception as e:  # noqa: BLE001
        print(f"[browser_fetch] ❌ {e}")
        sys.exit(2)

    aw = d.get("aweme_detail") or {}
    info = summarize(aw)
    print(json.dumps(info, ensure_ascii=False, indent=2))

    v = aw.get("video") or {}
    urls = (v.get("play_addr") or {}).get("url_list") or []
    if args.meta_only:
        sys.exit(0)
    if not urls:
        print("[browser_fetch] ❌ 响应里没有 play_addr（可能需登录才能播放）")
        sys.exit(3)

    dest = Path(args.out) if args.out else Path(f"D:/tools/temp/bf_{info['aweme_id']}.mp4")
    dest.parent.mkdir(parents=True, exist_ok=True)
    ok = download(urls, dest)
    dest.with_suffix(".meta.json").write_text(
        json.dumps({"info": info, "play_urls": urls}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[browser_fetch] 元数据已写 {dest.with_suffix('.meta.json')}")
    sys.exit(0 if ok else 4)


if __name__ == "__main__":
    main()
