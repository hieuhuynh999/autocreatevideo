"""Cắt khoảng 35 giây đầu của video ngang thành Short dọc 1080x1920."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _duration(ffmpeg: str, path: Path) -> float:
    proc = subprocess.run(
        [ffmpeg, "-i", str(path)],
        capture_output=True,
        text=True,
    )
    for line in proc.stderr.splitlines():
        if "Duration:" not in line:
            continue
        clock = line.split("Duration:", 1)[1].split(",", 1)[0].strip()
        hours, minutes, seconds = clock.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise RuntimeError(f"Không đọc được độ dài của {path.name}")


def cut(source: Path, dest: Path, seconds: float = 35) -> Path:
    if not source.exists():
        raise RuntimeError(f"Không thấy {source}")
    ffmpeg = _ffmpeg()
    length = min(seconds, max(8, _duration(ffmpeg, source) - 0.2))
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Nền phóng to rồi làm mờ, khung 16:9 nằm giữa. Short cần hình dọc.
    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24:2[bg];"
        "[0:v]scale=1080:-2[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )
    proc = subprocess.run(
        [
            ffmpeg, "-y", "-i", str(source), "-t", f"{length:.2f}",
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "0:a:0?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart",
            str(dest),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not dest.exists():
        raise RuntimeError(proc.stderr[-400:])
    return dest
