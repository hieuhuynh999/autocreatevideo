"""Dựng bốn video trong ngày rồi hẹn giờ công khai.

Bản tin ngang 8:00, Short tin 12:00, bài tiền ngang 16:00, Short tiền 20:00
giờ America/New_York. Cờ --dang gọi len_lich.py. Không mở Chrome, không gõ mật khẩu.
Thiếu token YouTube thì để file trong artifacts rồi dừng.
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
ART = Path("/opt/cursor/artifacts")
NY = ZoneInfo("America/New_York")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
PYTHON = sys.executable
MAIL_TO = "huynhtronghieuiuh@gmail.com"
CHANNEL = "UCE056WfiFMV6k4N5irnIDnA"
PACK = ("vi-du-tin.mp4", "short-tin.mp4", "tai-chinh-1.mp4", "short-tien.mp4")
YOUTUBE_KEYS = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")


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
        if any(item in words for item in ("card", "debt", "apr", "percent")):
            picked.append("#CreditCard")
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


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _has_youtube() -> bool:
    return all(_secret(name) for name in YOUTUBE_KEYS)


def _missing_youtube() -> list[str]:
    return [name for name in YOUTUBE_KEYS if not _secret(name)]


def _probe(path: Path) -> str:
    proc = subprocess.run(
        ["ffmpeg", "-i", str(path)],
        capture_output=True,
        text=True,
        errors="replace",
    )
    text = proc.stderr
    size = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", text)
    duration = re.search(r"Duration: (\d+:\d+:\d+(?:\.\d+)?)", text)
    audio = "có tiếng" if "Audio:" in text else "không có tiếng"
    frame = f"{size.group(1)}x{size.group(2)}" if size else "không rõ khung"
    clock = duration.group(1) if duration else "?"
    return f"{path.name}: {frame}, {clock}, {audio}"


def _write_schedule(folder: Path, when: datetime, stories: list[dict], money: dict) -> None:
    lich = _load("lich")
    times = lich.public_times(when)
    lead = stories[0]["title"].rstrip(".") if stories else "U.S. briefing"
    news_bits = [lead, "", "Stories in this briefing:"]
    for index, story in enumerate(stories, start=1):
        news_bits.append(f"{index}. {story['outlet']}: {story['title']}")
        news_bits.append(story["link"])
    news_bits += [
        "",
        "Pictures and headlines belong to PBS NewsHour, the New York Times, and NPR, as named on screen.",
        "This is not advice about your vote or your money.",
        "",
        _tags(" ".join(story["title"] for story in stories), "news"),
    ]
    news_description = "\n".join(news_bits)
    short_news = news_description + "\n#Shorts"
    money_lines = [
        money["spoken"].strip().split("\n", 1)[0],
        "",
        f"Source: {money['source']}",
        "",
        "This is not personal financial advice.",
        "",
        _tags(money["title"] + " " + money["spoken"], "finance"),
    ]
    money_description = "\n".join(money_lines)
    short_money = money_description + "\n#Shorts"
    rows = [
        ("vi-du-tin.mp4", _title(lead, when, 100), news_description, times["tin"], "25", "BẢN TIN"),
        ("short-tin.mp4", _title(lead, when, 70) + " #Shorts", short_news, times["short-tin"], "25", "SHORT TIN"),
        ("tai-chinh-1.mp4", _title(money["title"], when, 100), money_description, times["tien"], "27", "BÀI TIỀN"),
        ("short-tien.mp4", _title(money["title"], when, 92) + " #Shorts", short_money, times["short-tien"], "27", "SHORT TIỀN"),
    ]
    items = []
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        "Bốn video: bản tin 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00 giờ America/New_York.",
        f"Kênh: {CHANNEL}",
        "Không dành cho trẻ em.",
        f"Bài tiền trong lịch 30 ngày (bắt đầu 2026-11-06): {money['title']}",
        "",
    ]
    for name, title, description, stamp, category, label in rows:
        path = folder / name
        items.append(
            {
                "file": str(path),
                "title": title[:100],
                "description": description,
                "publish_at": stamp.isoformat(),
                "category": category,
                "madeForKids": False,
            }
        )
        blocks += [
            f"===== {label} =====",
            f"File: {path}",
            f"Giờ công khai: {stamp.strftime('%Y-%m-%d %H:%M %Z')}",
            _probe(path),
            title[:100],
            "",
            description,
            "",
        ]
    (folder / "lich.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
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
        if not src.exists():
            print(f"Thiếu, không chép được: {source}")
            continue
        shutil.copy2(src, ART / dest)
        print(f"Artifact: {dest}")


def _build(day: str, folder: Path, when: datetime) -> int:
    news = folder / "vi-du-tin.mp4"
    money_file = folder / "tai-chinh-1.mp4"
    if not news.exists() or not (folder / "stories.json").exists():
        code = _run("run.py", day)
        print(f"run.py thoát {code}")
    if not money_file.exists():
        code = _run("tien.py", day)
        print(f"tien.py thoát {code}")
    if not news.exists() or not money_file.exists():
        print(f"Chưa đủ video ngang trong {folder}")
        return 1
    cutter = _load("cat_short")
    cutter.cut(news, folder / "short-tin.mp4", 35)
    cutter.cut(money_file, folder / "short-tien.mp4", 35)
    stories = json.loads((folder / "stories.json").read_text(encoding="utf-8"))
    money = _load("run").finance_one(when)
    _write_schedule(folder, when, stories, money)
    for name in PACK:
        print(_probe(folder / name))
    return 0


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
    log = OUT / "lich.log"
    started = datetime.now(VN).strftime("%Y-%m-%d %H:%M")
    done = folder / "da-dang.txt"
    posted_before = set(done.read_text(encoding="utf-8").splitlines()) if done.exists() else set()
    if set(PACK) <= posted_before:
        print(f"Ngày {day} đã hẹn đủ bốn video. Không dựng lại.")
        return 0
    code = _build(day, folder, when)
    with log.open("a", encoding="utf-8") as handle:
        handle.write(f"{started} pack={code} day={day}\n")
    if code != 0:
        return code
    _copy_artifacts(folder, day)
    if not args.dang:
        print("Đã dựng bốn video. Chưa hẹn giờ vì không có cờ --dang.")
        return 0
    missing = _missing_youtube()
    if missing:
        print(
            "Thiếu token YouTube: "
            + ", ".join(missing)
            + ". Đã để bốn video và phần chữ trong artifacts. Không gõ mật khẩu, không mở Chrome, không hẹn giờ kênh "
            + CHANNEL
            + "."
        )
        return 0
    uploader = _load("len_lich")
    code = uploader.schedule(folder)
    if code == 0:
        note = folder / "da-dang.txt"
        note.write_text("\n".join(PACK) + "\n", encoding="utf-8")
        _report(folder, when, True, "Đủ bốn video: 8:00, 12:00, 16:00 và 20:00 giờ miền Đông. Không dành cho trẻ em.")
    return code


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
