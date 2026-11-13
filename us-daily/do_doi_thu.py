"""Đo Short mới nhất của kênh đối thủ: độ dài, khung, fps, độ to, ảnh mẫu.

Chạy tay khi cần cập nhật mốc so sánh. Kết quả ghi vào us-daily/doi_thu_short.json
để kiem_dinh.py so Short của kênh với cùng một mốc mỗi ngày.

    python us-daily/do_doi_thu.py [số Short mỗi kênh]
"""

from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "output" / "doi-thu-short"
DEST = Path(__file__).with_name("doi_thu_short.json")
RIVALS = {
    "tin": ("@NBCNews", "@PBSNewsHour", "@CBSNews"),
    "tien": ("@GrahamStephan", "@moneyguyshow", "@CNBCMakeIt"),
}


def _ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _lufs(path: Path) -> float | None:
    proc = subprocess.run(
        [_ffmpeg(), "-i", str(path), "-af", "ebur128", "-vn", "-f", "null", "-"],
        capture_output=True,
        text=True,
        errors="replace",
    )
    found = re.findall(r"I:\s+(-?\d+(?:\.\d+)?) LUFS", proc.stderr)
    return float(found[-1]) if found else None


def _stills(path: Path, stem: str, duration: float) -> list[str]:
    shots = []
    for share in (0.2, 0.5, 0.8):
        dest = WORK / f"{stem}-{int(share * 100)}.jpg"
        subprocess.run(
            [_ffmpeg(), "-y", "-ss", f"{duration * share:.2f}", "-i", str(path), "-frames:v", "1", "-q:v", "3", str(dest)],
            capture_output=True,
        )
        if dest.exists():
            shots.append(str(dest))
    return shots


def measure(per_channel: int = 3) -> dict:
    import yt_dlp

    WORK.mkdir(parents=True, exist_ok=True)
    deno = Path(sys.executable).with_name("Scripts") / "deno.exe"
    if not deno.exists():
        deno = Path(sys.executable).parent / "Scripts" / "deno.exe"
    runtimes = {"deno": {"path": str(deno)}} if deno.exists() else {}
    listing = {"quiet": True, "extract_flat": True, "playlistend": per_channel, "skip_download": True}
    fetch = {
        "quiet": True,
        "js_runtimes": runtimes,
        "format": "best[height<=1920][ext=mp4][acodec!=none]/best[ext=mp4]/best",
        "outtmpl": str(WORK / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "overwrites": False,
    }
    result: dict = {}
    for kind, handles in RIVALS.items():
        rows = []
        for handle in handles:
            try:
                with yt_dlp.YoutubeDL(listing) as ydl:
                    tab = ydl.extract_info(f"https://www.youtube.com/{handle}/shorts", download=False)
            except Exception as exc:
                print(f"{handle}: không đọc được tab Shorts ({exc.__class__.__name__})")
                continue
            for entry in (tab.get("entries") or [])[:per_channel]:
                url = f"https://www.youtube.com/shorts/{entry['id']}"
                try:
                    with yt_dlp.YoutubeDL(fetch) as ydl:
                        info = ydl.extract_info(url, download=True)
                        file = Path(ydl.prepare_filename(info))
                except Exception as exc:
                    print(f"{handle} {entry['id']}: bỏ qua ({exc.__class__.__name__})")
                    continue
                duration = float(info.get("duration") or 0)
                row = {
                    "channel": handle,
                    "id": entry["id"],
                    "title": info.get("title", ""),
                    "duration": duration,
                    "width": info.get("width"),
                    "height": info.get("height"),
                    "fps": info.get("fps"),
                    "lufs": _lufs(file) if file.exists() else None,
                    "stills": _stills(file, f"{kind}-{entry['id']}", duration) if file.exists() else [],
                }
                rows.append(row)
                print(f"{handle} {row['duration']:.0f}s {row['width']}x{row['height']} {row['fps']}fps {row['lufs']} LUFS  {row['title'][:60]}")
        durations = [row["duration"] for row in rows if row["duration"]]
        loud = [row["lufs"] for row in rows if row["lufs"] is not None]
        result[kind] = {
            "channels": sorted({row["channel"] for row in rows}),
            "count": len(rows),
            "duration_median": statistics.median(durations) if durations else None,
            "duration_low": min(durations) if durations else None,
            "duration_high": max(durations) if durations else None,
            "lufs_median": statistics.median(loud) if loud else None,
            "tall_share": sum(1 for row in rows if (row["height"] or 0) >= 1280) / len(rows) if rows else 0,
            "videos": rows,
        }
    DEST.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(DEST)
    return result


if __name__ == "__main__":
    measure(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
