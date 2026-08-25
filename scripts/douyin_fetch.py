#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频/图文获取脚本（替代方案 v1）
====================================
背景：douyin-capture 后端（5050，HTML 解析 _ROUTER_DATA）已被抖音改版击穿，
      抖音网页版不再向页面注入视频数据。本脚本改用 yt-dlp + agent-browser
      cft profile cookie 方案，走 aweme/v1/web/aweme/detail API，抗改版。

用法：
    python douyin_fetch.py <分享链接或视频ID> [--out DIR] [--video-only|--audio-only] [--json]

    依赖：
    yt-dlp（隔离 venv：C:/Users/Administrator/.workbuddy/binaries/python/envs/default）
    cft profile（agent-browser 曾访问过 douyin.com 即有 cookie；未登录也够用）
    ffmpeg（系统 PATH，抽音频用）

    示例：
    python douyin_fetch.py "https://v.douyin.com/WTIR26uvcKY/"
    python douyin_fetch.py 7658845517123816746 --audio-only --out C:/Users/Administrator/WorkBuddy/Claw/temp/dy_test
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

# ---- 常量（按本机环境配置，其他机器需改）----
YTDLP = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
CFT_PROFILE = "chrome:C:/Users/Administrator/.qclaw/tools/xbrowser/profiles/cft/Default"
FFMPEG = "ffmpeg"
# yt-dlp 网络 socket 超时（秒）。弱网/长视频默认 20s 易超时，固定放宽到 60s。
SOCKET_TIMEOUT = 60


def run_ytdlp(url: str, out_dir: Path, mode: str) -> dict:
    """调用 yt-dlp 解析并下载，返回元数据。"""
    cmd = [YTDLP, "-m", "yt_dlp", "--no-warnings",
           "--socket-timeout", str(SOCKET_TIMEOUT),
           "--cookies-from-browser", CFT_PROFILE]
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
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    url = resolve_input(args.url)

    try:
        if args.json:
            cmd = [YTDLP, "-m", "yt_dlp", "--no-warnings", "-J",
                   "--socket-timeout", str(SOCKET_TIMEOUT),
                   "--cookies-from-browser", CFT_PROFILE, url]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            meta = json.loads(proc.stdout or "{}")
            print(json.dumps({
                "id": meta.get("id"),
                "title": meta.get("title"),
                "uploader": meta.get("uploader"),
                "upload_date": meta.get("upload_date"),
                "duration": meta.get("duration"),
                "formats": len(meta.get("formats", [])),
            }, ensure_ascii=False, indent=2))
            return

        result = run_ytdlp(url, out_dir, args.mode)
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
