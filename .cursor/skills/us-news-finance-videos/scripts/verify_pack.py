"""Check one day's U.S. news and finance folder before it is shown.

Exit 0 only when every present piece passes. Prints THIEU for a missing piece.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

OUTLETS = ("PBS", "NPR", "New York Times")
FINANCE_FLOOR = 40.0
NEWS_FLOOR = 60.0


def _duration(path: Path) -> float | None:
    try:
        import imageio_ffmpeg
    except ImportError:
        return None
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True)
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _title_and_spoken(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    title = ""
    if "TITLE\n" in text:
        title = text.split("TITLE\n", 1)[1].split("\n", 1)[0].strip()
    spoken = text.split("SPOKEN SCRIPT\n", 1)[-1] if "SPOKEN SCRIPT\n" in text else text
    return title, spoken


def _check_finance(folder: Path, index: int, problems: list[str]) -> None:
    script = folder / f"finance-{index}.txt"
    video = folder / f"tai-chinh-{index}.mp4"
    if not script.exists():
        problems.append(f"THIEU finance-{index}.txt")
        return
    title, spoken = _title_and_spoken(script)
    if not re.search(r"\d", title):
        problems.append(f"FAIL finance-{index}: title has no digit")
    if "not personal financial advice" not in spoken.lower():
        problems.append(f"FAIL finance-{index}: missing the not-advice line")
    if not video.exists():
        problems.append(f"THIEU tai-chinh-{index}.mp4")
        return
    length = _duration(video)
    if length is None:
        problems.append(f"FAIL tai-chinh-{index}.mp4: could not read duration")
    elif length < FINANCE_FLOOR:
        problems.append(f"FAIL tai-chinh-{index}.mp4: {length:.1f}s is under {FINANCE_FLOOR:.0f}s")
    else:
        print(f"PASS tai-chinh-{index}.mp4 {length:.1f}s")


def _check_news(folder: Path, problems: list[str]) -> None:
    script = folder / "news.txt"
    if not script.exists():
        problems.append("THIEU news.txt")
        return
    _title, spoken = _title_and_spoken(script)
    if not any(name in spoken for name in OUTLETS):
        problems.append("FAIL news: spoken script names no PBS, NPR, or New York Times")
    video = folder / "vi-du-but.mp4"
    if not video.exists():
        video = folder / "vi-du-tin.mp4"
    if not video.exists():
        problems.append("THIEU news mp4")
        return
    length = _duration(video)
    if length is None:
        problems.append(f"FAIL {video.name}: could not read duration")
    elif length < NEWS_FLOOR:
        problems.append(f"FAIL {video.name}: {length:.1f}s is under {NEWS_FLOOR:.0f}s")
    else:
        print(f"PASS {video.name} {length:.1f}s")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python verify_pack.py output/us-daily/YYYY-MM-DD")
        return 2
    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print(f"FAIL missing folder {folder}")
        return 1
    problems: list[str] = []
    _check_finance(folder, 1, problems)
    _check_finance(folder, 2, problems)
    _check_news(folder, problems)
    for line in problems:
        print(line)
    failed = [line for line in problems if line.startswith("FAIL") or line.startswith("THIEU")]
    if failed:
        print("RESULT FAIL")
        return 1
    print("RESULT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
