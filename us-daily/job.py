"""Dựng bốn video trong ngày và hẹn giờ công khai nếu đã có token YouTube.

Thứ tự: bản tin ngang, Short tin, bài tiền ngang, Short tiền.
Giờ miền Đông: 8:00, 12:00, 16:00, 20:00. Không dành cho trẻ em.
Không gõ mật khẩu Google. Không in token. Không mở Chrome.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "us-daily"
NY = ZoneInfo("America/New_York")
PYTHON = sys.executable
ART = Path("/opt/cursor/artifacts")
CHANNEL = "UCE056WfiFMV6k4N5irnIDnA"
TOKEN_NAMES = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
PACK = (
    ("tin", "vi-du-tin.mp4", "25"),
    ("short-tin", "short-tin.mp4", "25"),
    ("tien", "tai-chinh-1.mp4", "27"),
    ("short-tien", "short-tien.mp4", "27"),
)


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


def _missing_tokens() -> list[str]:
    return [name for name in TOKEN_NAMES if not _secret(name)]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(script: str, day: str) -> int:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["US_DAILY_DAY"] = day
    proc = subprocess.run([PYTHON, "-u", str(ROOT / "us-daily" / script)], cwd=ROOT, env=env)
    return proc.returncode


def _title(sentence: str, when: datetime, total: int = 100) -> str:
    stamp = when.strftime("%b ") + str(when.day)
    suffix = f" | {stamp}"
    sentence = sentence.rstrip(".")
    limit = total - len(suffix)
    if len(sentence) > limit:
        cut = sentence[:limit].rsplit(" ", 1)[0].rstrip(" ,:;-")
        weak = {"a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "as", "at", "by", "with", "from"}
        words = cut.split()
        while len(words) > 3 and words[-1].lower() in weak:
            words.pop()
        cut = " ".join(words).rstrip(" ,:;-")
        sentence = cut or sentence[:limit]
    return sentence + suffix


def _block(path: Path, label: str) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    headers = ("TITLE\n", "OPENING SHOT", "DESCRIPTION\n", "SPOKEN SCRIPT\n")
    marker = label + "\n"
    start = text.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    ends = [text.find(header, start) for header in headers if text.find(header, start) >= 0]
    end = min(ends) if ends else len(text)
    return text[start:end].strip()


def _first_sentence(text: str) -> str:
    clean = " ".join(text.split())
    match = re.search(r"(.+?[.!?])(?:\s|$)", clean)
    return (match.group(1) if match else clean).strip()


def _probe(path: Path) -> dict:
    import imageio_ffmpeg

    proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True, errors="replace")
    info = {"duration": 0.0, "size": None, "audio": "Audio:" in proc.stderr, "fps": None}
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
    if match:
        hours, minutes, seconds = match.groups()
        info["duration"] = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    size = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", proc.stderr)
    if size:
        info["size"] = (int(size.group(1)), int(size.group(2)))
    fps = re.search(r"(\d+(?:\.\d+)?) fps", proc.stderr)
    if fps:
        info["fps"] = float(fps.group(1))
    return info


def _check(folder: Path, when: datetime) -> tuple[bool, str]:
    lines = ["KIỂM TRA BỐN VIDEO"]
    bad = 0
    expect = {
        "vi-du-tin.mp4": ((1280, 720), 45, 900),
        "tai-chinh-1.mp4": ((1280, 720), 30, 900),
        "short-tin.mp4": ((1080, 1920), 30, 40),
        "short-tien.mp4": ((1080, 1920), 30, 40),
    }
    for name, (shape, low, high) in expect.items():
        path = folder / name
        if not path.exists():
            lines.append(f"- {name}: thiếu file")
            bad += 1
            continue
        info = _probe(path)
        problems = []
        if info["size"] != shape:
            problems.append(f"khung {info['size']}, cần {shape[0]}x{shape[1]}")
        if not (low <= info["duration"] <= high):
            problems.append(f"dài {info['duration']:.1f}s, cần {low}–{high}s")
        if not info["audio"]:
            problems.append("không có tiếng")
        if problems:
            bad += 1
            lines.append(f"- {name}: " + "; ".join(problems))
        else:
            lines.append(f"- {name}: {info['size'][0]}x{info['size'][1]}, {info['duration']:.1f}s, {info['fps']} fps")
    review = folder / "review.md"
    if review.exists():
        text = review.read_text(encoding="utf-8")
        if "tin và một bài tiền đủ để thu" not in text:
            lines.append("- bản tin hoặc bài tiền chưa đủ để thu")
            bad += 1
        for outlet in ("PBS NewsHour", "New York Times", "NPR"):
            if f"  - {outlet}:" not in text:
                lines.append(f"- bản tin chưa có bài của {outlet}")
                bad += 1
    else:
        lines.append("- thiếu review.md")
        bad += 1
    finance_path = folder / "finance-1.txt"
    finance = finance_path.read_text(encoding="utf-8") if finance_path.exists() else ""
    if "not personal financial advice" not in finance.lower():
        lines.append("- bài tiền thiếu câu không phải lời khuyên")
        bad += 1
    row = _load("lich").row_for(when)
    groups = re.findall(r"\d[\d,]*", row.get("number", ""))
    for group in groups:
        plain = group.replace(",", "")
        spoken_digits = re.sub(r"\D", "", finance)
        if group not in finance and plain not in finance and plain not in spoken_digits:
            lines.append(f"- bài tiền chưa thấy số {group}")
            bad += 1
    scenes = folder / "tai-chinh-1.canh.txt"
    if scenes.exists():
        count = len([line for line in scenes.read_text(encoding="utf-8").splitlines() if line.strip()])
        lines.append(f"- bài tiền {count} cảnh")
        if count < 4:
            lines.append("- bài tiền quá ít cảnh")
            bad += 1
    lines.append("ĐẠT" if bad == 0 else f"CHƯA ĐẠT ({bad})")
    report = "\n".join(lines)
    (folder / "kiem-dinh.txt").write_text(report + "\n", encoding="utf-8")
    return bad == 0, report


def _write_schedule(folder: Path, when: datetime, news_title: str, money_title: str, news_body: str, money_body: str) -> None:
    lich = _load("lich")
    times = lich.public_times(when)
    short_news = _title(news_title, when, 90)
    if len(short_news) + len(" #Shorts") <= 100:
        short_news += " #Shorts"
    short_money = _title(money_title, when, 90)
    if len(short_money) + len(" #Shorts") <= 100:
        short_money += " #Shorts"
    news_description = (
        news_body
        + "\n\nPictures come from the PBS NewsHour, New York Times, and NPR articles named above.\n"
        + "Not made for kids.\n"
    )
    money_description = (
        money_body
        + "\n\nThis is not personal financial advice.\nNot made for kids.\n"
    )
    short_news_description = (
        "The first 35 seconds of today's U.S. briefing.\n\n"
        + news_body
        + "\n\n#Shorts #USNews #NewsBriefing\nNot made for kids.\n"
    )
    short_money_description = (
        "The first 35 seconds of today's household money video.\n\n"
        + money_body
        + "\n\nThis is not personal financial advice.\n#Shorts #PersonalFinance #MoneyTips\nNot made for kids.\n"
    )
    titles = {
        "tin": _title(news_title, when, 100),
        "short-tin": short_news,
        "tien": _title(money_title, when, 100),
        "short-tien": short_money,
    }
    descriptions = {
        "tin": news_description.strip() + "\n",
        "short-tin": short_news_description.strip() + "\n",
        "tien": money_description.strip() + "\n",
        "short-tien": short_money_description.strip() + "\n",
    }
    items = []
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        f"Kênh: {CHANNEL}",
        "Không dành cho trẻ em.",
        "Thứ tự: bản tin 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00 giờ America/New_York.",
        "",
    ]
    labels = {
        "tin": "BẢN TIN",
        "short-tin": "SHORT TIN",
        "tien": "BÀI TIỀN",
        "short-tien": "SHORT TIỀN",
    }
    for key, filename, category in PACK:
        path = folder / filename
        info = _probe(path) if path.exists() else {"duration": 0}
        item = {
            "file": str(path),
            "title": titles[key],
            "description": descriptions[key],
            "publish_at": times[key].isoformat(),
            "category": category,
            "made_for_kids": False,
        }
        items.append(item)
        blocks += [
            f"===== {labels[key]} {times[key].strftime('%H:%M')} =====",
            f"File: {filename}",
            f"Giờ công khai: {times[key].strftime('%Y-%m-%d %H:%M %Z')}",
            f"Dài {info['duration']:.1f}s",
            "Không dành cho trẻ em.",
            titles[key],
            "",
            descriptions[key].strip(),
            "",
        ]
    (folder / "lich.json").write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (folder / "youtube.txt").write_text("\n".join(blocks), encoding="utf-8")


def _copy_artifacts(folder: Path, day: str) -> None:
    ART.mkdir(parents=True, exist_ok=True)
    names = {
        "vi-du-tin.mp4": f"tin-{day}.mp4",
        "short-tin.mp4": f"short-tin-{day}.mp4",
        "tai-chinh-1.mp4": f"tien-{day}.mp4",
        "short-tien.mp4": f"short-tien-{day}.mp4",
        "youtube.txt": f"youtube-{day}.txt",
    }
    for source, dest in names.items():
        src = folder / source
        if src.exists():
            shutil.copy2(src, ART / dest)
            print(f"Artifacts: {dest}")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true")
    parser.add_argument("--day", default="")
    parser.add_argument("--dang", action="store_true")
    args = parser.parse_args()
    when = datetime.now(NY)
    if args.day:
        when = datetime.strptime(args.day, "%Y-%m-%d").replace(tzinfo=NY)
    day = when.strftime("%Y-%m-%d")
    folder = OUT / day
    folder.mkdir(parents=True, exist_ok=True)
    print(f"Ngày New York: {day}")
    news_code = _run("run.py", day)
    money_code = _run("tien.py", day)
    if news_code != 0 or not (folder / "vi-du-tin.mp4").exists():
        print("Chưa dựng được bản tin có ảnh.")
        return 1
    if money_code != 0 or not (folder / "tai-chinh-1.mp4").exists():
        print("Chưa dựng được bài tiền đúng ngày.")
        return 1
    cutter = _load("cat_short")
    cutter.cut(folder / "vi-du-tin.mp4", folder / "short-tin.mp4", 35)
    cutter.cut(folder / "tai-chinh-1.mp4", folder / "short-tien.mp4", 35)
    spoken = _block(folder / "news.txt", "SPOKEN SCRIPT")
    finance_title = _block(folder / "finance-1.txt", "TITLE").splitlines()[0]
    finance_body = _block(folder / "finance-1.txt", "DESCRIPTION")
    news_title = _first_sentence(spoken) or _block(folder / "news.txt", "TITLE")
    news_body = _block(folder / "news.txt", "DESCRIPTION")
    _write_schedule(folder, when, news_title, finance_title, news_body, finance_body)
    passed, report = _check(folder, when)
    print(report)
    if not passed:
        print("Bốn video chưa đủ điều kiện. Không hẹn giờ.")
        return 1
    missing = _missing_tokens()
    note = ""
    if missing:
        note = (
            "Chưa hẹn giờ vì máy chưa có "
            + ", ".join(missing)
            + ". Không gõ mật khẩu Google. Không in token."
        )
        text = (folder / "youtube.txt").read_text(encoding="utf-8")
        (folder / "youtube.txt").write_text(text.rstrip() + "\n\n" + note + "\n", encoding="utf-8")
    _copy_artifacts(folder, day)
    if not args.dang:
        print("Chưa hẹn giờ. Thêm --dang khi đủ token YouTube.")
        return 0
    if missing:
        print(note)
        return 0
    code = _run_schedule(folder)
    return code


def _run_schedule(folder: Path) -> int:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run([PYTHON, "-u", str(ROOT / "us-daily" / "len_lich.py"), str(folder)], cwd=ROOT, env=env)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
