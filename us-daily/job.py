"""Dựng bốn video trong ngày rồi hẹn giờ nếu đã có token YouTube.

Bản tin ngang, bài tiền ngang, và hai Short cắt khoảng 35 giây đầu.
Giờ công khai miền Đông: 8:00, 12:00, 16:00, 20:00.
Cờ --dang gọi len_lich.py. Không mở Chrome, không gõ mật khẩu.
Thiếu token thì giữ bốn file và phần chữ, không hẹn giờ.
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


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sources(text: str) -> list[str]:
    if "Sources:" not in text:
        return []
    lines = []
    for line in text.split("Sources:", 1)[1].splitlines():
        if line.startswith("SPOKEN SCRIPT"):
            break
        if line.strip() in {
            "Not personal financial advice.",
            "Each picture belongs to the newsroom named with it. The words are that article's headline and feed summary. Not advice.",
        }:
            break
        lines.append(line)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _lead_title(folder: Path) -> str:
    news = folder / "news.txt"
    if not news.exists():
        return f"U.S. briefing {folder.name}"
    match = re.search(r"^1\. [^:]+: (.+)$", news.read_text(encoding="utf-8"), re.M)
    if not match:
        return f"U.S. briefing {folder.name}"
    return match.group(1).strip().rstrip(".")


def _write_posts(folder: Path, when: datetime) -> None:
    lich = _load_module("lich")
    run = _load_module("run")
    times = lich.public_times(when)
    row = lich.row_for(when)
    item = run.finance_one(when)
    news_file = folder / "news.txt"
    news_text = news_file.read_text(encoding="utf-8") if news_file.exists() else ""
    lead = _lead_title(folder)
    news_sources = _sources(news_text)
    money_title = item["title"]
    news_tags = _tags(lead + " " + news_text, "news")
    money_tags = _tags(money_title + " " + item["spoken"], "finance")
    news_desc = "\n".join(
        [
            lead + ".",
            "",
            "A U.S. briefing from articles with pictures at PBS NewsHour, the New York Times, and NPR.",
            "",
            "In this briefing:",
            *news_sources,
            "",
            "Pictures and headlines belong to the newsrooms named on screen.",
            "This is not advice about your vote or your money.",
            "Not made for kids.",
            "",
            news_tags,
        ]
    )
    number = item.get("number") or row.get("number") or ""
    money_lines = [
        row.get("hook") or money_title,
        "",
        money_title + ".",
        "",
    ]
    if number:
        money_lines += [f"On screen: {number}", ""]
    money_lines += [
        "Sources:",
        item["source"],
        "",
        "This is not personal financial advice.",
        "Not made for kids.",
        "",
        money_tags,
    ]
    money_desc = "\n".join(money_lines)
    specs = [
        ("tin", folder / "vi-du-tin.mp4", _title(lead, when, 100), news_desc, "25", "BẢN TIN"),
        ("short-tin", folder / "short-tin.mp4", _title(lead, when, 92) + " #Shorts", news_desc + "\n\n#Shorts", "25", "SHORT TIN"),
        ("tien", folder / "tai-chinh-1.mp4", _title(money_title, when, 100), money_desc, "27", "BÀI TIỀN"),
        ("short-tien", folder / "short-tien.mp4", _title(money_title, when, 92) + " #Shorts", money_desc + "\n\n#Shorts", "27", "SHORT TIỀN"),
    ]
    manifest = []
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        "Bốn video, giờ America/New_York: bản tin 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00.",
        "Thứ tự: bản tin, Short tin, bài tiền, Short tiền.",
        "Kênh: UCE056WfiFMV6k4N5irnIDnA",
        "Không dành cho trẻ em.",
        f"Bài tiền: {money_title}",
        f"Số trên hình: {number}",
        "",
    ]
    for slot, path, title, description, category, label in specs:
        stamp = times[slot]
        manifest.append(
            {
                "file": str(path),
                "title": title,
                "description": description,
                "publish_at": stamp.isoformat(),
                "category": category,
                "madeForKids": False,
            }
        )
        blocks += [
            f"===== {label} =====",
            f"File: {path.name}",
            f"Giờ công khai: {stamp.strftime('%Y-%m-%d %H:%M %Z')}",
            title,
            "",
            description,
            "",
        ]
    (folder / "lich.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "youtube.txt").write_text("\n".join(blocks), encoding="utf-8")
    for entry in manifest:
        print(f"{Path(entry['file']).name} | {entry['publish_at']} | kids={entry['madeForKids']} | {entry['title']}")


def _normalize(path: Path) -> None:
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    temp = path.with_suffix(".norm.mp4")
    proc = subprocess.run(
        [
            ffmpeg, "-y", "-i", str(path),
            "-c:v", "copy",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
            str(temp),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0 and temp.exists():
        temp.replace(path)
    else:
        temp.unlink(missing_ok=True)
        print(f"Chưa chỉnh được độ to của {path.name}.")


def _cut_shorts(folder: Path) -> None:
    cutter = _load_module("cat_short")
    cutter.cut(folder / "vi-du-tin.mp4", folder / "short-tin.mp4", 35)
    cutter.cut(folder / "tai-chinh-1.mp4", folder / "short-tien.mp4", 35)


def _build(day: str, folder: Path) -> bool:
    if _run("run.py", day) != 0 or not (folder / "vi-du-tin.mp4").exists():
        print("Chưa có bản tin.")
        return False
    if _run("tien.py", day) != 0 or not (folder / "tai-chinh-1.mp4").exists():
        print("Chưa có bài tiền.")
        return False
    _cut_shorts(folder)
    needed = ("vi-du-tin.mp4", "short-tin.mp4", "tai-chinh-1.mp4", "short-tien.mp4")
    return all((folder / name).exists() for name in needed)


def _artifacts(folder: Path, day: str) -> None:
    root = Path("/opt/cursor/artifacts")
    root.mkdir(parents=True, exist_ok=True)
    mapping = {
        "vi-du-tin.mp4": f"tin-{day}.mp4",
        "short-tin.mp4": f"short-tin-{day}.mp4",
        "tai-chinh-1.mp4": f"tien-{day}.mp4",
        "short-tien.mp4": f"short-tien-{day}.mp4",
    }
    for src_name, dest_name in mapping.items():
        src = folder / src_name
        if not src.exists():
            print(f"Thiếu {src_name}, chưa chép artifact.")
            continue
        shutil.copy2(src, root / dest_name)
        print(f"Đã để {dest_name}")
    text = folder / "youtube.txt"
    if text.exists():
        shutil.copy2(text, root / f"youtube-{day}.txt")
        print(f"Đã để youtube-{day}.txt")


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
    lich = _load_module("lich")
    index = (when.astimezone(NY).date() - lich.START.date()).days
    item = _load_module("run").finance_one(when)
    print(f"Ngày {day} giờ New York. Chỉ số lịch {index}. Bài tiền: {item['title']}. Số trên hình: {item['number']}.")
    if not args.titles_only:
        built = False
        for attempt in range(2):
            if attempt:
                print("Dựng lại bốn video.")
                time.sleep(15)
            if _build(day, folder):
                built = True
                break
        if not built:
            print(f"Không dựng đủ bốn video cho {day}.")
            return 1
    needed = ("vi-du-tin.mp4", "short-tin.mp4", "tai-chinh-1.mp4", "short-tien.mp4")
    if not all((folder / name).exists() for name in needed):
        print("Thiếu một trong bốn file.")
        return 1
    _write_posts(folder, when)
    checker = _load_module("kiem_dinh")
    try:
        passed, verdict = checker.check(folder)
    except Exception as exc:
        passed, verdict = False, f"KIỂM ĐỊNH bị lỗi: {exc.__class__.__name__}."
    print(verdict)
    if not passed and "LUFS" in verdict:
        for name in ("vi-du-tin.mp4", "tai-chinh-1.mp4"):
            _normalize(folder / name)
        _cut_shorts(folder)
        _write_posts(folder, when)
        try:
            passed, verdict = checker.check(folder)
        except Exception as exc:
            passed, verdict = False, f"KIỂM ĐỊNH bị lỗi: {exc.__class__.__name__}."
        print(verdict)
    _artifacts(folder, day)
    if not passed:
        print("Kiểm định chưa đạt. Chưa hẹn giờ. Không mở Chrome.")
        return 1
    if not args.dang:
        print("Chưa hẹn giờ. Không mở Chrome.")
        return 0
    names = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [name for name in names if not _secret(name)]
    if missing:
        print(
            "Thiếu token YouTube: "
            + ", ".join(missing)
            + ". Đã để bốn video và phần chữ trong artifacts. Không gõ mật khẩu. Không hẹn giờ."
        )
        return 0
    return _load_module("len_lich").schedule(folder)


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
