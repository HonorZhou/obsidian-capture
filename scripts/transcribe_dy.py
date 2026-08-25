#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抖音音频转写：faster-whisper medium + CUDA，输出 transcript.json。

用法:
    python transcribe_dy.py <input.m4a> [output.json]
"""
import sys
import json
from faster_whisper import WhisperModel


def main():
    if len(sys.argv) < 2:
        print("usage: transcribe_dy.py <input.m4a> [output.json]")
        sys.exit(1)
    m4a = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else m4a.rsplit(".", 1)[0] + ".transcript.json"

    model = WhisperModel("medium", device="cuda", compute_type="float16")
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
