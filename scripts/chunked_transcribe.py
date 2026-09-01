# -*- coding: utf-8 -*-
"""分块可续跑的 faster-whisper 转写：把长音频切成若干段，逐段落盘，最后合并。

用法: python chunked_transcribe.py <audio.wav> <out_dir> [--chunk-min 15]
每段产出 segNN.json（幂等：已存在则跳过），最后写 transcript.json。
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("WHISPER_MODEL", "medium")
os.environ.setdefault("WHISPER_DEVICE", "cuda")
os.environ.setdefault("WHISPER_COMPUTE_TYPE", "float16")

FFMPEG = os.environ.get("DY_FFMPEG", "ffmpeg")


def load_model():
    from faster_whisper import WhisperModel
    name = os.environ.get("WHISPER_MODEL", "medium")
    dev = os.environ.get("WHISPER_DEVICE")
    ct = os.environ.get("WHISPER_COMPUTE_TYPE")
    attempts = ([(name, dev, ct or ("float16" if dev == "cuda" else "int8"))] if dev
                else [(name, "cuda", "float16"), (name, "cuda", "int8_float16"), (name, "cpu", "int8")])
    last = None
    for mdl, d, c in attempts:
        try:
            m = WhisperModel(mdl, device=d, compute_type=c)
            print(f"[model] {mdl} device={d} compute_type={c}", flush=True)
            return m
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"[model] {d}/{c} 失败: {e}", flush=True)
    raise last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("outdir")
    ap.add_argument("--chunk-min", type=int, default=15)
    args = ap.parse_args()

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    chunk_dir = out / "chunks"
    chunk_dir.mkdir(exist_ok=True)

    # 1) 切块（若已切过则复用）
    existing = sorted(chunk_dir.glob("chunk*.wav"))
    if not existing:
        cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", args.audio,
               "-f", "segment", "-segment_time", str(args.chunk_min * 60),
               "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1",
               str(chunk_dir / "chunk%03d.wav")]
        subprocess.run(cmd, check=True)
        existing = sorted(chunk_dir.glob("chunk*.wav"))
    print(f"[split] {len(existing)} chunks", flush=True)

    # 2) 逐段转写（可续跑）
    model = None
    durations = []
    for i, wav in enumerate(existing):
        meta = wav.with_suffix(".json")
        if meta.exists():
            print(f"[skip] {wav.name} 已完成", flush=True)
            continue
        if model is None:
            model = load_model()
        segs, info = model.transcribe(str(wav), language="zh", beam_size=5, vad_filter=True)
        items = [{"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip()}
                 for s in segs]
        meta.write_text(json.dumps({"items": items, "dur": round(info.duration, 1)},
                                   ensure_ascii=False), encoding="utf-8")
        print(f"[done] {wav.name} segs={len(items)} dur={info.duration:.0f}s", flush=True)

    # 3) 合并，按块时长做时间偏移
    all_segs, texts, offset = [], [], 0.0
    for wav in sorted(chunk_dir.glob("chunk*.wav")):
        meta = wav.with_suffix(".json")
        if not meta.exists():
            print(f"[warn] 缺 {meta.name}，跳过", flush=True)
            continue
        d = json.loads(meta.read_text(encoding="utf-8"))
        for s in d["items"]:
            all_segs.append({"start": round(s["start"] + offset, 1),
                             "end": round(s["end"] + offset, 1), "text": s["text"]})
            texts.append(s["text"])
        offset += float(d.get("dur") or 0.0)

    final = {"text": "".join(texts), "segments": all_segs,
             "language": "zh", "duration": round(offset, 1)}
    (out / "transcript.json").write_text(json.dumps(final, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    print(f"[merge] segments={len(all_segs)} chars={len(final['text'])} "
          f"dur={final['duration']} -> {out/'transcript.json'}", flush=True)


if __name__ == "__main__":
    main()
