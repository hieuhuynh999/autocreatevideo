"""Dựng bốn video trong ngày, rồi hẹn giờ nếu máy đã có token YouTube.

Bản tin ngang lúc 8:00, Short tin lúc 12:00, bài tiền lúc 16:00, Short tiền
lúc 20:00 giờ America/New_York. Cờ --dang gọi len_lich.py. Không mở Chrome,
không gõ mật khẩu. Thiếu YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET hoặc
YOUTUBE_REFRESH_TOKEN thì chép bốn file và phần chữ vào artifacts rồi dừng.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "us-daily"
ART = Path("/opt/cursor/artifacts")
NY = ZoneInfo("America/New_York")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
PYTHON = sys.executable
CHANNEL = "UCE056WfiFMV6k4N5irnIDnA"
ORDER = ("tin", "short-tin", "tien", "short-tien")
FILES = {
    "tin": "vi-du-tin.mp4",
    "short-tin": "short-tin.mp4",
    "tien": "tai-chinh-1.mp4",
    "short-tien": "short-tien.mp4",
}
TOKEN_NAMES = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")


def _wait_for_new_york_morning() -> None:
    now = datetime.now(NY)
    target = now.replace(hour=4, minute=0, second=0, microsecond=0)
    if now >= target:
        return
    delay = (target - now).total_seconds()
    if delay > 2 * 60 * 60:
        return
    print(f"Cho den 4:00 sang New York, con {int(delay)} giay.")
    time.sleep(delay)


def _title(sentence: str, when: datetime, total: int = 100) -> str:
    stamp = when.strftime("%b ") + str(when.day)
    suffix = f" | {stamp}"
    sentence = sentence.rstrip(".")
    limit = total - len(suffix)
    if len(sentence) > limit:
        cut = sentence[:limit].rsplit(" ", 1)[0].rstrip(" ,:;-")
        weak = {"a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "as", "at", "by", "with", "under", "over", "after", "from", "into", "its", "their", "his", "her"}
        words = cut.split()
        while len(words) > 3 and words[-1].lower() in weak:
            words.pop()
        cut = " ".join(words).rstrip(" ,:;-")
        sentence = cut or sentence[:limit]
    return sentence + suffix


def _tags(text: str, kind: str) -> str:
    words = text.lower()
    if kind == "finance":
        picked = ["#PersonalFinance", "#MoneyTips"]
        if any(item in words for item in ("card", "debt", "apr")):
            picked.append("#CreditCard")
        if "grocery" in words:
            picked.append("#Groceries")
        if any(item in words for item in ("paycheck", "budget", "split")):
            picked.append("#Budget")
        if any(item in words for item in ("emergency", "saving")):
            picked.append("#Savings")
        if any(item in words for item in ("fund", "invest")):
            picked.append("#Investing")
        if any(item in words for item in ("home", "mortgage", "down", "fha", "closing")):
            picked.append("#Housing")
        picked.append("#USFinance")
    else:
        picked = ["#USNews", "#NewsBriefing"]
        if any(item in words for item in ("congress", "chamber")):
            picked.append("#Congress")
        if "midterm" in words:
            picked.append("#Midterms")
        if "trump" in words:
            picked.append("#Trump")
        if "iran" in words:
            picked.append("#Iran")
        if "hong kong" in words:
            picked.append("#HongKong")
        if any(item in words for item in ("vatican", "pope", "dylan")):
            picked.append("#Vatican")
    chosen: list[str] = []
    for tag in picked:
        if tag not in chosen:
            chosen.append(tag)
    return " ".join(chosen[:8])


def _secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    path = ROOT / ".env"
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _tokens_ready() -> bool:
    return all(_secret(name) for name in TOKEN_NAMES)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _run(script: str, day: str) -> int:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["US_DAILY_DAY"] = day
    proc = subprocess.run([PYTHON, "-u", str(ROOT / "us-daily" / script)], cwd=ROOT, env=env)
    return proc.returncode


def _probe(path: Path) -> dict:
    import imageio_ffmpeg

    proc = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path)],
        capture_output=True,
        text=True,
        errors="replace",
    )
    text = proc.stderr
    info: dict = {"duration": 0.0, "size": None, "fps": None, "audio": "Audio:" in text}
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if match:
        hours, minutes, seconds = match.groups()
        info["duration"] = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    size = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", text)
    if size:
        info["size"] = (int(size.group(1)), int(size.group(2)))
    fps = re.search(r"(\d+(?:\.\d+)?) fps", text)
    if fps:
        info["fps"] = float(fps.group(1))
    return info


def _stories(folder: Path) -> list[dict]:
    path = folder / "bai.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _write_posts(folder: Path, when: datetime, finance: dict) -> None:
    lich = _load("lich")
    times = lich.public_times(when)
    stories = _stories(folder)
    lead = stories[0]["title"] if stories else "U.S. briefing"
    news_bits = [lead, "", "Stories in this briefing:"]
    for index, story in enumerate(stories, start=1):
        news_bits.append(f"{index}. {story['outlet']}: {story['title']}")
        news_bits.append(story["link"])
    news_bits += [
        "",
        "Pictures and headlines belong to PBS NewsHour, the New York Times, and NPR.",
        "The words are the headline and one sentence from the feed summary.",
        "This is not advice about your vote or your money.",
        "",
        _tags(" ".join(story["title"] for story in stories), "news"),
    ]
    news_description = "\n".join(news_bits)
    short_news = news_bits[:-1] + ["The Short is about the first 35 seconds of the briefing.", "", _tags(" ".join(story["title"] for story in stories), "news") + " #Shorts"]
    money_lines = [
        finance["title"],
        "",
        f"The number on screen: {finance['number']}",
        f"Source: {finance['source']}",
        "",
        "This is one example for a household in the United States.",
        "This is not personal financial advice.",
        "",
        _tags(finance["title"] + " " + finance["source"], "finance"),
    ]
    money_description = "\n".join(money_lines)
    short_money = money_lines[:-1] + ["The Short is about the first 35 seconds.", "", _tags(finance["title"], "finance") + " #Shorts"]
    titles = {
        "tin": _title(lead, when, 100),
        "short-tin": _title(lead, when, 91) + " #Shorts",
        "tien": _title(finance["title"], when, 100),
        "short-tien": _title(finance["title"], when, 91) + " #Shorts",
    }
    descriptions = {
        "tin": news_description,
        "short-tin": "\n".join(short_news),
        "tien": money_description,
        "short-tien": "\n".join(short_money),
    }
    categories = {"tin": "25", "short-tin": "25", "tien": "27", "short-tien": "27"}
    items = []
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        "Bốn video: bản tin 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00 giờ America/New_York.",
        f"Kênh: {CHANNEL}",
        "Không dành cho trẻ em.",
        "",
    ]
    for slot in ORDER:
        path = folder / FILES[slot]
        info = _probe(path) if path.exists() else {}
        items.append(
            {
                "file": str(path),
                "title": titles[slot][:100],
                "description": descriptions[slot],
                "publish_at": times[slot].isoformat(),
                "category": categories[slot],
                "made_for_kids": False,
            }
        )
        blocks += [
            f"===== {slot.upper()} =====",
            f"File: {path.name}",
            f"Giờ công khai: {times[slot].strftime('%Y-%m-%d %H:%M %Z')}",
            f"Khung: {info.get('size')}  dài {info.get('duration', 0):.1f}s  {info.get('fps')} fps",
            titles[slot][:100],
            "",
            descriptions[slot],
            "",
        ]
    (folder / "lich.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "youtube.txt").write_text("\n".join(blocks), encoding="utf-8")


def _check(folder: Path) -> list[str]:
    problems = []
    expect = {
        "vi-du-tin.mp4": (1280, 720),
        "tai-chinh-1.mp4": (1280, 720),
        "short-tin.mp4": (1080, 1920),
        "short-tien.mp4": (1080, 1920),
    }
    for name, shape in expect.items():
        path = folder / name
        if not path.exists():
            problems.append(f"thiếu {name}")
            continue
        info = _probe(path)
        if info["size"] != shape:
            problems.append(f"{name} khung {info['size']}, cần {shape[0]}x{shape[1]}")
        if not info["audio"]:
            problems.append(f"{name} không có tiếng")
        if name.startswith("short"):
            if not (30 <= info["duration"] <= 40):
                problems.append(f"{name} dài {info['duration']:.1f}s, cần khoảng 35 giây")
            if not info["fps"] or info["fps"] < 29:
                problems.append(f"{name} {info['fps']} fps, cần ít nhất 29")
        elif info["duration"] < 20:
            problems.append(f"{name} quá ngắn ({info['duration']:.1f}s)")
    stories = _stories(folder)
    outlets = {item.get("outlet") for item in stories}
    for name in ("PBS NewsHour", "New York Times", "NPR"):
        if name not in outlets:
            problems.append(f"bản tin thiếu bài có ảnh của {name}")
    if len(stories) < 4:
        problems.append(f"bản tin chỉ có {len(stories)} bài có ảnh")
    from PIL import Image

    photos = sorted((folder / "anh").glob("[0-9][0-9].img")) if (folder / "anh").exists() else []
    for path in photos:
        with Image.open(path) as image:
            if image.width < 240 or image.height < 160:
                problems.append(f"ảnh {path.name} quá nhỏ {image.size}")
    return problems


def _copy_artifacts(folder: Path, day: str) -> None:
    ART.mkdir(parents=True, exist_ok=True)
    names = {
        "vi-du-tin.mp4": f"tin-{day}.mp4",
        "short-tin.mp4": f"short-tin-{day}.mp4",
        "tai-chinh-1.mp4": f"tien-{day}.mp4",
        "short-tien.mp4": f"short-tien-{day}.mp4",
    }
    for source, dest in names.items():
        src = folder / source
        if src.exists():
            shutil.copy2(src, ART / dest)
            print(f"Đã chép {dest}")
    text = folder / "youtube.txt"
    if text.exists():
        shutil.copy2(text, ART / f"youtube-{day}.txt")
        print(f"Đã chép youtube-{day}.txt")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--titles-only", action="store_true")
    parser.add_argument("--now", action="store_true")
    parser.add_argument("--day", default="")
    parser.add_argument("--dang", action="store_true")
    args = parser.parse_args()
    if not args.now and not args.titles_only:
        _wait_for_new_york_morning()
    when = datetime.now(NY)
    if args.day:
        when = datetime.strptime(args.day, "%Y-%m-%d").replace(tzinfo=NY)
    day = when.strftime("%Y-%m-%d")
    folder = OUT / day
    folder.mkdir(parents=True, exist_ok=True)
    print(f"Ngày New York: {day}")
    run = _load("run")
    finance = run.finance_one(when)
    print(f"Bài tiền: {finance['title']} ({finance['number']})")
    if not args.titles_only:
        code = _run("run.py", day)
        if code != 0 or not (folder / "vi-du-tin.mp4").exists():
            print("Chưa dựng được bản tin. Không mở Chrome.")
            return 1
        code = _run("tien.py", day)
        if code != 0 or not (folder / "tai-chinh-1.mp4").exists():
            print("Chưa dựng được bài tiền. Không mở Chrome.")
            return 1
        cat = _load("cat_short")
        cat.cut(folder / "vi-du-tin.mp4", folder / "short-tin.mp4", 35)
        cat.cut(folder / "tai-chinh-1.mp4", folder / "short-tien.mp4", 35)
        print(f"Đã cắt Short: {folder / 'short-tin.mp4'} và {folder / 'short-tien.mp4'}")
    _write_posts(folder, when, finance)
    problems = _check(folder)
    if problems:
        print("Kiểm tra file:")
        for item in problems:
            print(f"- {item}")
    else:
        print("Bốn video đủ khung, tiếng và ảnh bài.")
    if not args.dang:
        print("Chưa hẹn giờ. Thêm --dang khi máy đã có token YouTube.")
        return 1 if problems else 0
    if not _tokens_ready():
        _copy_artifacts(folder, day)
        missing = [name for name in TOKEN_NAMES if not _secret(name)]
        print(
            "Thiếu "
            + ", ".join(missing)
            + ". Đã để bốn video và phần chữ trong artifacts. "
            "Không gõ mật khẩu, không mở Chrome, không hẹn giờ kênh "
            + CHANNEL
            + "."
        )
        return 0
    if problems:
        print("Chưa hẹn giờ vì file chưa đạt.")
        return 1
    uploader = _load("len_lich")
    return uploader.schedule(folder)


if __name__ == "__main__":
    sys.exit(main())
