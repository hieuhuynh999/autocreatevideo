"""Tải Short đối thủ theo lượt xem, trích khung đầu và ghi phân tích.

    python us-daily/phan_tich_doi_thu.py [số Short mỗi kênh]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "output" / "doi-thu-phan-tich"
DEST = Path(__file__).with_name("doi_thu_phan_tich.json")
RIVALS = {
    "tin": ("@NBCNews", "@CBSNews", "@PBSNewsHour", "@ABCNews", "@CNN"),
    "tien": ("@GrahamStephan", "@moneyguyshow", "@CNBCMakeIt", "@TheFinancialDiet", "@RamseySolutions"),
}


def _ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _still(path: Path, stem: str, at: float) -> str | None:
    dest = WORK / f"{stem}-{int(at * 10)}.jpg"
    subprocess.run(
        [_ffmpeg(), "-y", "-ss", f"{at:.2f}", "-i", str(path), "-frames:v", "1", "-q:v", "3", str(dest)],
        capture_output=True,
    )
    return str(dest) if dest.exists() else None


def measure(per_channel: int = 8) -> dict:
    import yt_dlp

    WORK.mkdir(parents=True, exist_ok=True)
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    deno = Path(sys.executable).parent / "Scripts" / "deno.exe"
    runtimes = {"deno": {"path": str(deno)}} if deno.exists() else {}
    listing = {
        "quiet": True,
        "extract_flat": False,
        "playlistend": per_channel,
        "skip_download": True,
        "js_runtimes": runtimes,
    }
    fetch = {
        "quiet": True,
        "js_runtimes": runtimes,
        "ffmpeg_location": ffmpeg,
        "format": "best[height<=720][ext=mp4]/best[ext=mp4]/best",
        "outtmpl": str(WORK / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "overwrites": False,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "vtt",
        "ignoreerrors": "only_download",
        "skip_unavailable_fragments": True,
    }
    result: dict = {}
    for kind, handles in RIVALS.items():
        rows = []
        for handle in handles:
            try:
                with yt_dlp.YoutubeDL(listing) as ydl:
                    tab = ydl.extract_info(f"https://www.youtube.com/{handle}/shorts", download=False)
            except Exception as exc:
                print(f"{handle}: bỏ kênh ({exc.__class__.__name__})")
                continue
            entries = sorted(
                [e for e in (tab.get("entries") or []) if e],
                key=lambda e: e.get("view_count") or 0,
                reverse=True,
            )[:3]
            for entry in entries:
                url = f"https://www.youtube.com/shorts/{entry['id']}"
                try:
                    with yt_dlp.YoutubeDL(fetch) as ydl:
                        info = ydl.extract_info(url, download=True)
                        file = Path(ydl.prepare_filename(info))
                except Exception as exc:
                    print(f"{handle} {entry['id']}: bỏ ({exc.__class__.__name__}: {str(exc)[:80]})")
                    continue
                duration = float(info.get("duration") or 0)
                subs = ""
                for candidate in WORK.glob(f"{entry['id']}*.vtt"):
                    text = candidate.read_text(encoding="utf-8", errors="replace")
                    lines = []
                    for line in text.splitlines():
                        if not line or line.startswith("WEBVTT") or "-->" in line or line.isdigit():
                            continue
                        clean = re.sub(r"<[^>]+>", "", line).strip()
                        if clean and clean not in lines:
                            lines.append(clean)
                    if lines:
                        subs = " ".join(lines[:40])
                        break
                row = {
                    "channel": handle,
                    "id": entry["id"],
                    "title": info.get("title", ""),
                    "views": info.get("view_count") or entry.get("view_count") or 0,
                    "likes": info.get("like_count"),
                    "duration": duration,
                    "description": (info.get("description") or "")[:280],
                    "opening_words": " ".join(subs.split()[:28]),
                    "subtitle_excerpt": subs[:500],
                    "stills": [
                        s
                        for s in (
                            _still(file, f"{kind}-{entry['id']}", 0.4),
                            _still(file, f"{kind}-{entry['id']}", min(3.0, duration * 0.2)),
                            _still(file, f"{kind}-{entry['id']}", min(duration * 0.5, duration - 0.5)),
                        )
                        if s
                    ],
                }
                rows.append(row)
                print(f"{handle} {row['views']:,} views {duration:.0f}s  {row['title'][:70]}")
                print(f"  mở đầu: {row['opening_words'][:120]}")
        rows.sort(key=lambda r: r["views"], reverse=True)
        result[kind] = {"count": len(rows), "videos": rows}
    DEST.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(DEST)
    return result


if __name__ == "__main__":
    measure(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
