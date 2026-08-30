#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频/图文获取脚本（替代方案 v1）
====================================
背景：douyin-capture 后端（5050，HTML 解析 _ROUTER_DATA）已被抖音改版击穿，
      抖音网页版不再向页面注入视频数据。本脚本改用 yt-dlp 走
      aweme/v1/web/aweme/detail API，抗改版；cookie 由 dy_cookie.py 用 Playwright
      独立 Chromium 采集（关键项是藏在 x-ms-token 响应头里的 msToken），导出为
      cookies.txt 后由 --cookies 提供——不读用户正在使用的浏览器。

用法：
    python douyin_fetch.py <分享链接或视频ID> [--out DIR] [--mode both|video-only|audio-only] [--json] [--cookie-mode auto|file|browser|none]

    依赖：
    yt-dlp / requests（装在本脚本所用的 venv 内即可，无需硬编码解释器路径）
    cookies.txt（由 dy_cookie.py 用 Playwright 独立 Chromium 采集，含 msToken）
    ffmpeg（抽音频用；设 DY_FFMPEG 或放 PATH）

    跨设备配置走环境变量：DY_YTDLP_PYTHON / DY_COOKIES_FILE / DY_COOKIES_FROM_BROWSER /
    DY_FFMPEG / DY_SOCKET_TIMEOUT。

    示例：
    python douyin_fetch.py "https://v.douyin.com/WTIR26uvcKY/" --json --cookie-mode file
    python douyin_fetch.py 7658845517123816746 --mode audio-only --out temp/dy_test
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# ---- 常量（跨设备：优先读环境变量，未设置则用可移植默认值）----
# 运行 yt-dlp 的 Python。默认「当前解释器自身」，只要在本脚本所在 venv 里装好 yt-dlp 即可。
YTDLP = os.environ.get("DY_YTDLP_PYTHON") or sys.executable
# cookie 来源，yt-dlp --cookies-from-browser 语法：BROWSER[:PROFILE]。
# 原设备用 cft profile；本机无 Chrome/cft，默认走 Edge。可用 DY_COOKIES_FROM_BROWSER 覆盖。
CFT_PROFILE = os.environ.get("DY_COOKIES_FROM_BROWSER", "edge")
# 可选：导出的 cookies.txt（Netscape 格式）。设置后优先于 --cookies-from-browser，
# 好处是完全不读浏览器正在占用的 cookie 库，浏览器不用退出。
COOKIES_FILE = os.environ.get("DY_COOKIES_FILE", "")
FFMPEG = os.environ.get("DY_FFMPEG", "ffmpeg")
# yt-dlp 网络 socket 超时（秒）。弱网/长视频默认 20s 易超时，固定放宽到 60s。
SOCKET_TIMEOUT = int(os.environ.get("DY_SOCKET_TIMEOUT", "60"))


def build_cookie_args(mode: str = "auto") -> list:
    """构造 yt-dlp 的 cookie 参数，支持三级降级。

    mode:
      file    -> 只用 DY_COOKIES_FILE
      browser -> 只用 --cookies-from-browser
      none    -> 不带 cookie（靠 yt-dlp 自行引导匿名 cookie）
      auto    -> 有 cookies.txt 用文件，否则用浏览器，都没有则不带
    """
    if mode == "none":
        return []
    if mode in ("file", "auto") and COOKIES_FILE and Path(COOKIES_FILE).exists():
        return ["--cookies", COOKIES_FILE]
    if mode == "file":
        raise SystemExit(f"[cookie] 指定了 file 模式但 DY_COOKIES_FILE 不存在: {COOKIES_FILE}")
    if mode == "browser" or (mode == "auto" and CFT_PROFILE):
        return ["--cookies-from-browser", CFT_PROFILE]
    return []


def run_ytdlp(url: str, out_dir: Path, mode: str, cookie_mode: str = "auto") -> dict:
    """调用 yt-dlp 解析并下载，返回元数据。"""
    cmd = [YTDLP, "-m", "yt_dlp", "--no-warnings",
           "--socket-timeout", str(SOCKET_TIMEOUT)] + build_cookie_args(cookie_mode)
    if mode == "audio-only":
        cmd += ["-f", "ba/b"]
    elif mode == "video-only":
        cmd += ["-f", "bv*/b"]
    # 默认下载视频+音频最佳合并
    cmd += ["-o", str(out_dir / "%(id)s.%(ext)s"),
            "--print", "after_move:%(id)s|%(title).60s|%(uploader)s|%(duration)s|%(ext)s",
            url]
    print(">> yt-dlp 命令:", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp 失败 (rc={proc.returncode}): {stderr[-500:]}")
    return {"stdout": stdout, "stderr": stderr}


def extract_audio(video_path: Path) -> Path:
    """用 ffmpeg 抽音频为 m4a（供 faster-whisper 转写）。"""
    audio_path = video_path.with_suffix(".m4a")
    subprocess.run([FFMPEG, "-y", "-i", str(video_path),
                    "-vn", "-acodec", "aac", "-b:a", "128k",
                    str(audio_path)],
                   capture_output=True, timeout=180)
    return audio_path if audio_path.exists() else None


def resolve_input(raw: str) -> str:
    """输入可能是分享链接或纯视频 ID，统一成 yt-dlp 可用的 URL。"""
    raw = raw.strip()
    if raw.startswith("http"):
        return raw
    if raw.isdigit():
        return f"https://www.douyin.com/video/{raw}"
    raise ValueError(f"无法识别的输入: {raw}")


def main():
    ap = argparse.ArgumentParser(description="抖音视频获取（yt-dlp + cft cookie 替代方案）")
    ap.add_argument("url", help="抖音分享链接（v.douyin.com/...）或视频 ID")
    ap.add_argument("--out", default="temp/dy_download", help="输出目录")
    ap.add_argument("--mode", choices=["both", "video-only", "audio-only"], default="both",
                    help="下载模式：both=视频+音频合并(默认) / video-only / audio-only")
    ap.add_argument("--json", action="store_true", help="仅打印元数据 JSON，不下载")
    ap.add_argument("--cookie-mode", choices=["auto", "file", "browser", "none"], default="auto",
                    help="cookie 来源：auto=cookies.txt>浏览器>不带 / file / browser / none(不读浏览器,无需退出Edge)")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    url = resolve_input(args.url)

    try:
        if args.json:
            cmd = [YTDLP, "-m", "yt_dlp", "--no-warnings", "-J",
                   "--socket-timeout", str(SOCKET_TIMEOUT)] \
                + build_cookie_args(args.cookie_mode) + [url]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            err = (proc.stderr or "").strip()
            if proc.returncode != 0:
                # yt-dlp 失败时 -J 会输出 "null"，绝不能当成空 meta 继续往下走
                raise RuntimeError(
                    f"yt-dlp 解析失败 (rc={proc.returncode}): {err[-600:] or '(无 stderr)'}")
            out = (proc.stdout or "").strip()
            if not out or out == "null":
                raise RuntimeError(
                    f"yt-dlp 未返回元数据 (stdout={'空' if not out else 'null'}): "
                    f"{err[-600:] or '(无 stderr)'}")
            meta = json.loads(out)
            if not isinstance(meta, dict) or not meta.get("id"):
                raise RuntimeError(f"yt-dlp 返回内容异常，缺少 id 字段：{out[:200]}")
            print(json.dumps({
                "id": meta.get("id"),
                "title": meta.get("title"),
                "uploader": meta.get("uploader"),
                "upload_date": meta.get("upload_date"),
                "duration": meta.get("duration"),
                "formats": len(meta.get("formats", [])),
            }, ensure_ascii=False, indent=2))
            return

        result = run_ytdlp(url, out_dir, args.mode, args.cookie_mode)
        print(">> yt-dlp 输出:")
        print(result["stdout"] or "(无)")
        if result["stderr"]:
            print("(stderr):", result["stderr"][-300:])

        # 列出现有文件
        files = list(out_dir.glob("*"))
        print("\n>> 输出文件:")
        for f in files:
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  {f.name}  ({size_mb:.1f} MiB)")

        # audio-only 模式下 yt-dlp 下载的其实是 mp4 容器音频，补一步标准化 m4a
        if args.mode == "audio-only":
            for f in files:
                if f.suffix.lower() == ".mp4":
                    m4a = extract_audio(f)
                    if m4a:
                        print(f">> 已抽音频: {m4a.name}")
        print("\n✅ 完成。可直接用 faster-whisper 转写：")
        for f in files:
            if f.suffix.lower() in (".mp4", ".m4a", ".wav"):
                print(f"   whisper medium {f}")

    except Exception as e:
        print(f"❌ 失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
