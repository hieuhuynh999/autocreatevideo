"""Dựng bốn video trong ngày, rồi hẹn giờ nếu máy đã có token YouTube.

Bản tin ngang 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00,
giờ America/New_York. Short cắt khoảng 35 giây đầu của video ngang.
Không mở Chrome. Không gõ mật khẩu. Không in token.
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
NY = ZoneInfo("America/New_York")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
PYTHON = sys.executable
ARTIFACTS = Path("/opt/cursor/artifacts")
CHANNEL = "UCE056WfiFMV6k4N5irnIDnA"
TOKEN_NAMES = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
PACK = (
    ("tin", "vi-du-tin.mp4"),
    ("short-tin", "short-tin.mp4"),
    ("tien", "tai-chinh-1.mp4"),
    ("short-tien", "short-tien.mp4"),
)


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
        if any(item in words for item in ("card", "debt", "apr", "percent")):
            picked.append("#CreditCard")
        if "mortgage" in words or "home" in words or "down" in words:
            picked.append("#Mortgage")
        if any(item in words for item in ("paycheck", "budget", "split")):
            picked.append("#Budget")
        if any(item in words for item in ("emergency", "saving")):
            picked.append("#Savings")
        if any(item in words for item in ("fund", "invest", "401", "ira")):
            picked.append("#Investing")
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


def _missing_tokens() -> list[str]:
    return [name for name in TOKEN_NAMES if not _secret(name)]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def _run(script: str, day: str) -> int:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["US_DAILY_DAY"] = day
    proc = subprocess.run([PYTHON, "-u", str(ROOT / "us-daily" / script)], cwd=ROOT, env=env)
    return proc.returncode


def _ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _loudness(path: Path) -> float | None:
    proc = subprocess.run(
        [_ffmpeg(), "-i", str(path), "-af", "ebur128", "-vn", "-f", "null", "-"],
        capture_output=True,
        text=True,
        errors="replace",
    )
    found = re.findall(r"I:\s+(-?\d+(?:\.\d+)?) LUFS", proc.stderr)
    return float(found[-1]) if found else None


def _normalize(path: Path) -> None:
    loud = _loudness(path)
    if loud is not None and -20.0 <= loud <= -9.0:
        print(f"{path.name}: {loud:.1f} LUFS")
        return
    tmp = path.with_suffix(".norm.mp4")
    proc = subprocess.run(
        [
            _ffmpeg(), "-y", "-i", str(path),
            "-c:v", "copy",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart",
            str(tmp),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0 and tmp.exists() and tmp.stat().st_size > 1000:
        tmp.replace(path)
        done = _loudness(path)
        shown = f"{done:.1f}" if done is not None else "?"
        print(f"Đã chỉnh độ to {path.name}: {shown} LUFS")
        return
    tmp.unlink(missing_ok=True)
    print(f"Giữ nguyên độ to {path.name}")


def _section(text: str, start: str, ends: tuple[str, ...]) -> str:
    if start not in text:
        return ""
    body = text.split(start, 1)[1]
    for end in ends:
        if end in body:
            body = body.split(end, 1)[0]
            break
    return body.strip()


def _news_bits(folder: Path) -> tuple[str, str]:
    text = (folder / "news.txt").read_text(encoding="utf-8")
    description = _section(text, "DESCRIPTION\n", ("\nSPOKEN SCRIPT\n",))
    sources = _section(description, "Sources:\n", ())
    kept: list[str] = []
    for line in sources.splitlines():
        if line.startswith("Each picture") or line.startswith("Not advice"):
            break
        kept.append(line)
    block = "\n".join(kept).strip()
    lead = ""
    for line in block.splitlines():
        if re.match(r"\d+\.\s", line):
            lead = line.split(": ", 1)[-1].strip()
            break
    return lead, block


def _money_bits(folder: Path) -> tuple[str, str, str]:
    text = (folder / "finance-1.txt").read_text(encoding="utf-8")
    title = _section(text, "TITLE\n", ("\n\n",))
    description = _section(text, "DESCRIPTION\n", ("\nSPOKEN SCRIPT\n",))
    spoken = _section(text, "SPOKEN SCRIPT\n", ())
    source = _section(description, "Sources:\n", ("\n\n",))
    first = spoken.splitlines()[0].strip() if spoken else title
    return title, source, first


def _write_schedule(folder: Path, when: datetime) -> None:
    lich = _load("lich")
    times = lich.public_times(when)
    lead, sources = _news_bits(folder)
    if not lead:
        lead = "U.S. briefing"
    money_title, source, opening = _money_bits(folder)
    if not money_title:
        money_title = "Today's household number"
    news_tags = _tags(lead + " " + sources, "news")
    money_tags = _tags(money_title + " " + opening, "finance")
    news_body = "\n".join(
        [
            lead,
            "",
            "Stories in this briefing, each with the newsroom photo from the feed:",
            sources,
            "",
            "Pictures and headlines belong to PBS NewsHour, the New York Times, and NPR.",
            "Not advice about your vote or your money.",
            "",
            news_tags,
        ]
    )
    money_body = "\n".join(
        [
            opening,
            "",
            f"Source: {source}",
            "",
            "This is not personal financial advice.",
            "",
            money_tags,
        ]
    )
    files = {
        "tin": folder / "vi-du-tin.mp4",
        "short-tin": folder / "short-tin.mp4",
        "tien": folder / "tai-chinh-1.mp4",
        "short-tien": folder / "short-tien.mp4",
    }
    posts = {
        "tin": (_title(lead, when, 100), news_body, "25"),
        "short-tin": (_title(lead, when, 70) + " #Shorts", "The first 35 seconds of today's U.S. briefing.\n\n" + news_body + " #Shorts", "25"),
        "tien": (_title(money_title, when, 100), money_body, "27"),
        "short-tien": (_title(money_title, when, 70) + " #Shorts", "The first 35 seconds of today's money briefing.\n\n" + money_body + " #Shorts", "27"),
    }
    items = []
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        "Bốn video: bản tin 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00 giờ miền Đông.",
        "Đánh dấu không dành cho trẻ em.",
        f"Kênh: https://www.youtube.com/channel/{CHANNEL}",
        "",
    ]
    labels = {
        "tin": "BẢN TIN",
        "short-tin": "SHORT TIN",
        "tien": "BÀI TIỀN",
        "short-tien": "SHORT TIỀN",
    }
    for slot, _hour, _minute in lich.SLOTS:
        title, description, category = posts[slot]
        path = files[slot]
        when_slot = times[slot]
        items.append(
            {
                "file": str(path),
                "title": title,
                "description": description,
                "publish_at": when_slot.isoformat(),
                "category": category,
                "madeForKids": False,
            }
        )
        blocks += [
            f"===== {labels[slot]} =====",
            f"File: {path.name}",
            f"Giờ công khai: {when_slot.strftime('%Y-%m-%d %H:%M %Z')}",
            "Không dành cho trẻ em.",
            title,
            "",
            description,
            "",
        ]
    (folder / "lich.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "youtube.txt").write_text("\n".join(blocks), encoding="utf-8")


def _copy_artifacts(folder: Path, day: str) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    names = {
        "vi-du-tin.mp4": f"tin-{day}.mp4",
        "short-tin.mp4": f"short-tin-{day}.mp4",
        "tai-chinh-1.mp4": f"tien-{day}.mp4",
        "short-tien.mp4": f"short-tien-{day}.mp4",
    }
    for src_name, dest_name in names.items():
        src = folder / src_name
        if not src.exists():
            print(f"Thiếu {src_name}, chưa chép artifact.")
            continue
        shutil.copy2(src, ARTIFACTS / dest_name)
        print(f"Artifact {dest_name}")
    text = folder / "youtube.txt"
    if text.exists():
        shutil.copy2(text, ARTIFACTS / f"youtube-{day}.txt")
        print(f"Artifact youtube-{day}.txt")


def _cut(folder: Path) -> None:
    cutter = _load("cat_short")
    cutter.cut(folder / "vi-du-tin.mp4", folder / "short-tin.mp4", 35)
    cutter.cut(folder / "tai-chinh-1.mp4", folder / "short-tien.mp4", 35)


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
    lich = _load("lich")
    row = lich.row_for(when)
    print(f"Ngày {day} giờ New York. Bài tiền: {row.get('title') or row.get('key')} {row.get('number', '')}")
    if not args.titles_only:
        news_code = _run("run.py", day)
        money_code = _run("tien.py", day)
        print(f"run.py={news_code} tien.py={money_code}")
        news = folder / "vi-du-tin.mp4"
        money = folder / "tai-chinh-1.mp4"
        if not news.exists() or not money.exists():
            print("Chưa dựng đủ bản tin và bài tiền.")
            return 1
        _cut(folder)
        for _slot, name in PACK:
            _normalize(folder / name)
    if not all((folder / name).exists() for _slot, name in PACK):
        print("Chưa đủ bốn video.")
        return 1
    _write_schedule(folder, when)
    checker = _load("kiem_dinh")
    passed, verdict = checker.check(folder)
    print(verdict)
    _copy_artifacts(folder, day)
    if not args.dang:
        print("Chưa hẹn giờ. Thêm --dang khi muốn hẹn bằng token YouTube.")
        return 0 if passed else 1
    missing = _missing_tokens()
    if missing:
        print(
            "Thiếu "
            + ", ".join(missing)
            + ". Đã để bốn file video và phần chữ trong artifacts. Dừng, không hẹn giờ, không gõ mật khẩu."
        )
        return 0 if passed else 1
    if not passed:
        print("Kiểm định chưa đạt. Không hẹn giờ.")
        return 1
    uploader = _load("len_lich")
    try:
        code = uploader.schedule(folder)
    except Exception as exc:
        print(f"Hẹn giờ lỗi: {exc.__class__.__name__}")
        return 1
    if code == 0:
        print(f"Đã hẹn bốn video trên kênh {CHANNEL}. Không dành cho trẻ em.")
    return code


if __name__ == "__main__":
    sys.exit(main())
