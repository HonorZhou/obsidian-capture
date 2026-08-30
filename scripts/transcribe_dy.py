#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抖音音频转写：faster-whisper medium + CUDA，输出 transcript.json。

用法:
    python transcribe_dy.py <input.m4a> [output.json]
"""
import sys
import json
import os
from faster_whisper import WhisperModel


def load_model():
    """优先按环境变量/CUDA 加载；CUDA 不可用时自动降级 CPU int8。"""
    name = os.environ.get("WHISPER_MODEL", "medium")
    want_dev = os.environ.get("WHISPER_DEVICE")          # 可强制 cuda / cpu
    want_ct = os.environ.get("WHISPER_COMPUTE_TYPE")     # 可强制 float16 / int8 / int8_float16
    attempts = []
    if want_dev:
        attempts.append((name, want_dev, want_ct or ("float16" if want_dev == "cuda" else "int8")))
    else:
        attempts += [
            (name, "cuda", want_ct or "float16"),
            (name, "cuda", "int8_float16"),
            (name, "cpu", want_ct or "int8"),
        ]
    last = None
    for mdl, dev, ct in attempts:
        try:
            m = WhisperModel(mdl, device=dev, compute_type=ct)
            print(f"[model] loaded {mdl} device={dev} compute_type={ct}")
            return m
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"[model] {dev}/{ct} 失败: {e}")
    raise last


def main():
    if len(sys.argv) < 2:
        print("usage: transcribe_dy.py <input.m4a> [output.json]")
        sys.exit(1)
    m4a = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else m4a.rsplit(".", 1)[0] + ".transcript.json"

    model = load_model()
    segments_iter, info = model.transcribe(
        m4a, beam_size=5, language="zh", vad_filter=True
    )

    segments = []
    texts = []
    for s in segments_iter:
        segments.append({
            "start": round(s.start, 1),
            "end": round(s.end, 1),
            "text": s.text.strip(),
        })
        texts.append(s.text.strip())

    data = {
        "text": "".join(texts),
        "segments": segments,
        "language": info.language,
        "duration": round(info.duration, 1),
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"segments={len(segments)} chars={len(data['text'])} -> {out}")


if __name__ == "__main__":
    main()
