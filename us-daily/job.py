"""Dựng bốn video trong ngày rồi hẹn giờ công khai.

Bản tin Mỹ 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00 giờ miền Đông.
Short cắt khoảng 35 giây đầu của video ngang. Cờ --dang gọi YouTube bằng token.
Thiếu token thì để file trong artifacts và dừng. Không mở Chrome, không gõ mật khẩu.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import smtplib
import ssl
import subprocess
import sys
import time
from email.message import EmailMessage
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "us-daily"
NY = ZoneInfo("America/New_York")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
PYTHON = sys.executable
MAIL_TO = "huynhtronghieuiuh@gmail.com"


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
        weak = {"a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "as", "at", "by", "with", "under", "over", "after", "from", "into", "its", "their", "his", "her", "are", "is", "be", "was", "were", "but", "few", "has", "have", "been"}
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
        if any(item in words for item in ("home", "mortgage", "closing")):
            picked.append("#Housing")
        if "grocery" in words:
            picked.append("#Groceries")
        if any(item in words for item in ("paycheck", "budget", "split")):
            picked.append("#Budget")
        if any(item in words for item in ("emergency", "saving")):
            picked.append("#Savings")
        if any(item in words for item in ("fund", "invest")):
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


def send_mail(when: datetime, body: str, subject: str = "", attach: Path | None = None) -> str:
    password = _secret("MAIL_APP_PASSWORD").replace(" ", "")
    sender = _secret("MAIL_FROM") or MAIL_TO
    if not password:
        return "Chua gui mail: file .env chua co MAIL_APP_PASSWORD."
    message = EmailMessage()
    message["Subject"] = subject or f"Đăng bài {when.strftime('%Y-%m-%d')}: title, description, hashtag"
    message["From"] = sender
    message["To"] = MAIL_TO
    message.set_content(body)
    if attach is not None and attach.exists():
        message.add_attachment(attach.read_bytes(), maintype="image", subtype="jpeg", filename=attach.name)
    context = ssl.create_default_context()
    last = None
    for attempt in range(4):
        try:
            if attempt % 2 == 0:
                smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=60)
            else:
                smtp = smtplib.SMTP("smtp.gmail.com", 587, timeout=60)
                smtp.starttls(context=context)
            with smtp:
                smtp.login(sender, password)
                smtp.send_message(message)
            return f"Da gui mail toi {MAIL_TO}"
        except (smtplib.SMTPException, OSError) as exc:
            last = exc
            time.sleep(20 * (attempt + 1))
    raise last


def _report(folder: Path, when: datetime, ok: bool, detail: str) -> None:
    day = when.strftime("%Y-%m-%d")
    done = folder / "da-dang.txt"
    posted = done.read_text(encoding="utf-8").splitlines() if done.exists() else []
    lines = [
        f"Ngày New York: {day}",
        f"Kết quả: {'ĐĂNG THÀNH CÔNG' if ok else 'ĐĂNG KHÔNG ĐƯỢC'}",
        "",
        "Video đã hẹn giờ trên kênh AMERICAN DATA DAILY:",
        *([f"- {name}" for name in posted] or ["- chưa có video nào"]),
        "",
        detail,
        "",
        "Studio: https://studio.youtube.com/channel/UCE056WfiFMV6k4N5irnIDnA/videos",
    ]
    youtube = folder / "youtube.txt"
    if youtube.exists():
        lines += ["", "----- Tiêu đề, mô tả, hashtag -----", youtube.read_text(encoding="utf-8")]
    subject = f"[{'OK' if ok else 'LỖI'}] Đăng YouTube ngày {day}"
    shot = None if ok else folder / "studio-dang.jpg"
    try:
        print(send_mail(when, "\n".join(lines), subject, shot))
    except Exception as exc:
        print(f"Chua gui mail: {exc.__class__.__name__}")


def _run(script: str, day: str) -> int:
    env = dict(**{key: value for key, value in __import__("os").environ.items()})
    env["PYTHONUTF8"] = "1"
    env["US_DAILY_DAY"] = day
    proc = subprocess.run([PYTHON, "-u", str(ROOT / "us-daily" / script)], cwd=ROOT, env=env)
    return proc.returncode


ART = Path("/opt/cursor/artifacts")
PACK = (
    ("vi-du-tin.mp4", "tin", "news"),
    ("short-tin.mp4", "short-tin", "news"),
    ("tai-chinh-1.mp4", "tien", "finance"),
    ("short-tien.mp4", "short-tien", "finance"),
)
TOKEN_NAMES = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _media(path: Path) -> dict:
    import imageio_ffmpeg

    proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True, errors="replace")
    text = proc.stderr
    info = {"duration": 0.0, "size": None, "audio": "Audio:" in text, "fps": 0.0}
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
    path = folder / "tin.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _money(folder: Path) -> dict:
    path = folder / "tien.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _news_description(stories: list[dict], short: bool) -> str:
    lines = [
        "Opening 35 seconds of today's U.S. briefing." if short else "Today's U.S. briefing.",
        "",
        "Stories with pictures from PBS NewsHour, the New York Times, and NPR:",
        "",
    ]
    for index, story in enumerate(stories, start=1):
        lines.append(f"{index}. {story['outlet']}: {story['title']}")
        lines.append(story["link"])
    lines += [
        "",
        "Pictures and headlines belong to the newsrooms named in the video.",
        "This is not advice about your vote or your money.",
        "",
        _tags(" ".join(story["title"] for story in stories), "news"),
    ]
    if short:
        lines[-1] += " #Shorts"
    return "\n".join(lines)


def _money_description(item: dict, short: bool) -> str:
    spoken = item.get("spoken", "").strip().splitlines()
    lead = spoken[0] if spoken else item.get("title", "")
    tags = _tags(item.get("title", "") + " " + item.get("spoken", ""), "finance")
    if short:
        tags += " #Shorts"
    lines = [
        lead,
        "",
        f"Source: {item.get('source', '')}",
        "",
        "This is not personal financial advice.",
        "",
        tags,
    ]
    return "\n".join(lines)


def _write_schedule(folder: Path, when: datetime) -> None:
    lich = _load("lich")
    times = lich.public_times(when)
    stories = _stories(folder)
    money = _money(folder)
    lead = stories[0]["title"] if stories else f"U.S. briefing {when.strftime('%b')} {when.day}"
    money_title = money.get("title") or "Household money"
    labels = {
        "vi-du-tin.mp4": ("tin", _title(lead, when, 100), _news_description(stories, False), "25"),
        "short-tin.mp4": ("short-tin", _title(lead, when, 90) + " #Shorts", _news_description(stories, True), "25"),
        "tai-chinh-1.mp4": ("tien", _title(money_title, when, 100), _money_description(money, False), "27"),
        "short-tien.mp4": ("short-tien", _title(money_title, when, 90) + " #Shorts", _money_description(money, True), "27"),
    }
    items = []
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        "Kênh: UCE056WfiFMV6k4N5irnIDnA",
        "Không dành cho trẻ em: có (madeForKids false).",
        "Thứ tự: bản tin 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00 giờ America/New_York.",
        "",
    ]
    for filename, _slot, _kind in PACK:
        slot, title, description, category = labels[filename]
        path = folder / filename
        info = _media(path) if path.exists() else {"duration": 0}
        items.append(
            {
                "file": str(path),
                "title": title,
                "description": description,
                "publish_at": times[slot].isoformat(),
                "category": category,
                "madeForKids": False,
            }
        )
        blocks += [
            f"===== {slot.upper()} =====",
            f"File: {path}",
            f"Giờ công khai: {times[slot].strftime('%Y-%m-%d %H:%M %Z')}",
            f"Dài {info['duration']:.1f}s",
            "Không dành cho trẻ em.",
            title,
            "",
            description,
            "",
        ]
    (folder / "lich.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "youtube.txt").write_text("\n".join(blocks), encoding="utf-8")


def _check_pack(folder: Path) -> list[str]:
    problems = []
    stories = _stories(folder)
    outlets = {item.get("outlet") for item in stories}
    for name in ("PBS NewsHour", "New York Times", "NPR"):
        if name not in outlets:
            problems.append(f"bản tin thiếu ảnh từ {name}")
    if len(stories) < 4:
        problems.append(f"chỉ có {len(stories)} bài có ảnh")
    money = _money(folder)
    if not re.search(r"\d", money.get("title", "")):
        problems.append("bài tiền không có số trong tiêu đề")
    if "not personal financial advice" not in money.get("spoken", "").lower():
        problems.append("bài tiền thiếu câu not personal financial advice")
    expect = {
        "vi-du-tin.mp4": ((1280, 720), 40, None),
        "tai-chinh-1.mp4": ((1280, 720), 30, None),
        "short-tin.mp4": ((1080, 1920), 30, 36),
        "short-tien.mp4": ((1080, 1920), 30, 36),
    }
    for name, (shape, low, high) in expect.items():
        path = folder / name
        if not path.exists():
            problems.append(f"thiếu {name}")
            continue
        info = _media(path)
        if info["size"] != shape:
            problems.append(f"{name} khung {info['size']}, cần {shape[0]}x{shape[1]}")
        if info["duration"] < low or (high is not None and info["duration"] > high):
            problems.append(f"{name} dài {info['duration']:.1f}s")
        if not info["audio"]:
            problems.append(f"{name} không có tiếng")
        if name.startswith("short") and info["fps"] < 29:
            problems.append(f"{name} {info['fps']} fps")
    return problems


def _artifacts(folder: Path, day: str) -> None:
    ART.mkdir(parents=True, exist_ok=True)
    names = {
        "vi-du-tin.mp4": f"tin-{day}.mp4",
        "short-tin.mp4": f"short-tin-{day}.mp4",
        "tai-chinh-1.mp4": f"tien-{day}.mp4",
        "short-tien.mp4": f"short-tien-{day}.mp4",
    }
    for source, dest in names.items():
        shutil.copy2(folder / source, ART / dest)
        print(f"Artifact {dest}")
    shutil.copy2(folder / "youtube.txt", ART / f"youtube-{day}.txt")
    print(f"Artifact youtube-{day}.txt")


def _build_long(day: str, folder: Path) -> bool:
    news = folder / "vi-du-tin.mp4"
    money = folder / "tai-chinh-1.mp4"
    for attempt in range(2):
        if news.exists() and _stories(folder) and len({item.get("outlet") for item in _stories(folder)} & {"PBS NewsHour", "New York Times", "NPR"}) == 3:
            break
        if attempt:
            print("Bản tin chưa đủ ba báo có ảnh. Dựng lại.")
            time.sleep(15)
        code = _run("run.py", day)
        print(f"run.py mã {code}")
    for attempt in range(2):
        if money.exists() and _money(folder).get("number"):
            break
        if attempt:
            print("Bài tiền chưa có file. Dựng lại.")
            time.sleep(15)
        code = _run("tien.py", day)
        print(f"tien.py mã {code}")
    if not news.exists() or not money.exists():
        return False
    cutter = _load("cat_short")
    cutter.cut(news, folder / "short-tin.mp4", 35)
    cutter.cut(money, folder / "short-tien.mp4", 35)
    return True


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
    done = folder / "da-dang.txt"
    posted_before = set(done.read_text(encoding="utf-8").splitlines()) if done.exists() else set()
    if {name for name, _slot, _kind in PACK} <= posted_before:
        print(f"Ngày {day} đã đăng đủ bốn video. Không dựng lại.")
        return 0
    if not args.titles_only and not _build_long(day, folder):
        print("Chưa dựng đủ bản tin và bài tiền.")
        return 1
    if not (folder / "tin.json").exists() or not (folder / "tien.json").exists():
        print("Thiếu tin.json hoặc tien.json.")
        return 1
    _write_schedule(folder, when)
    problems = _check_pack(folder)
    if problems:
        print("Chưa đạt:")
        for item in problems:
            print(f"- {item}")
        return 1
    print("Đủ bốn video.")
    _artifacts(folder, day)
    if not args.dang:
        print("Chưa hẹn giờ. Thêm --dang khi có token YouTube.")
        return 0
    missing = [name for name in TOKEN_NAMES if not _secret(name)]
    if missing:
        print(
            "Thiếu "
            + ", ".join(missing)
            + ". Đã để bốn video và phần chữ trong artifacts. Không hẹn giờ. Không gõ mật khẩu."
        )
        return 0
    scheduler = _load("len_lich")
    return scheduler.schedule(folder)


def _clean_posted(folder: Path) -> None:
    """Xóa video đã qua kiểm định và đã đăng. Video chưa đăng được thì giữ lại."""
    done = folder / "da-dang.txt"
    posted = set(done.read_text(encoding="utf-8").splitlines()) if done.exists() else set()
    removed = []
    for name in sorted(posted):
        path = folder / name
        if path.exists():
            path.unlink()
            removed.append(name)
    if {"short-tin.mp4", "short-tien.mp4"} <= posted:
        for leftover in [*folder.glob("*.mp4"), *folder.glob("*.mp3"), *folder.glob("*.wav"), *folder.glob("*.jpg")]:
            leftover.unlink()
            removed.append(leftover.name)
        if (folder / "anh").exists():
            shutil.rmtree(folder / "anh", ignore_errors=True)
            removed.append("anh")
    if removed:
        print(f"Đã xóa {len(removed)} file đã đăng trong {folder.name}.")


if __name__ == "__main__":
    sys.exit(main())
