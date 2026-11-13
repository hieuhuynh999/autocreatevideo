"""Dựng hai Short dọc (tin Mỹ và tiền bạc), kiểm định, rồi hẹn giờ công khai.

Máy nhà chạy lúc 18:00 giờ Việt Nam, tức 6:00 sáng New York vào mùa đông.
Hai Short được hẹn: 8:00 và 16:00 giờ miền Đông.
Cờ --dang mới gọi YouTube. Không có cờ thì chỉ dựng file.
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
    if {"short-tin.mp4", "short-tien.mp4"} <= posted_before:
        print(f"Ngày {day} đã đăng đủ 2 Short. Không dựng lại.")
        return 0
    if not args.titles_only:
        code = _run("lam_short.py", day)
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"{started} short={code} day={day}\n")
    if not (folder / "lich.json").exists() or not json.loads((folder / "lich.json").read_text(encoding="utf-8")):
        print(f"Chua co Short trong {folder}")
        if args.dang:
            _report(folder, when, False, "Không dựng được Short tin lẫn Short tiền, nên chưa mở Studio.")
        return 1
    if not args.dang:
        print("Chưa mở YouTube Studio. Thêm --dang để đăng bằng Chrome trên máy này.")
        return 0
    spec = importlib.util.spec_from_file_location("kiem_dinh", ROOT / "us-daily" / "kiem_dinh.py")
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    try:
        passed, verdict = checker.check(folder)
    except Exception as exc:
        passed, verdict = False, f"KIỂM ĐỊNH bị lỗi: {exc.__class__.__name__}. Không đăng để an toàn."
    print(verdict)
    if not passed:
        _report(folder, when, False, verdict + "\n\nChưa mở Studio. Không có video nào được đăng.")
        return 1
    spec = importlib.util.spec_from_file_location("dang_studio", ROOT / "us-daily" / "dang_studio.py")
    uploader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(uploader)
    failure = None
    for attempt in range(3):
        try:
            code = uploader.upload_day(folder)
            failure = None
            break
        except Exception as exc:
            failure = exc
            print(f"Lượt đăng {attempt + 1} lỗi: {str(exc).splitlines()[0][:200] if str(exc) else exc.__class__.__name__}")
            time.sleep(120)
    if failure is not None:
        exc = failure
        reason = str(exc).splitlines()[0][:300] if str(exc) else exc.__class__.__name__
        _report(folder, when, False, f"Lỗi khi bấm trong Studio: {reason}\nẢnh màn hình lúc lỗi đính kèm nếu có.\n\n{verdict}")
        _clean_posted(folder)
        return 1
    posted = (folder / "da-dang.txt").read_text(encoding="utf-8").splitlines() if (folder / "da-dang.txt").exists() else []
    ok = code == 0 and {"short-tin.mp4", "short-tien.mp4"} <= set(posted)
    detail = "Đủ 2 Short: tin 8:00 và tiền 16:00 giờ miền Đông." if ok else f"Chỉ đăng được {len(posted)} trên 2 Short."
    _report(folder, when, ok, detail + "\n\n" + verdict)
    _clean_posted(folder)
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
