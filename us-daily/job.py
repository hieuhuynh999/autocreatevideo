"""Dựng bốn video trong ngày rồi hẹn giờ công khai.

Bản tin Mỹ 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00,
giờ America/New_York. Short cắt khoảng 35 giây đầu của video ngang.
Cờ --dang gọi len_lich.py. Không mở Chrome, không gõ mật khẩu.
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
        if any(item in words for item in ("credit card", "card balance", "apr")):
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


ART = Path("/opt/cursor/artifacts")
PACK = ("vi-du-tin.mp4", "short-tin.mp4", "tai-chinh-1.mp4", "short-tien.mp4")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _missing_youtube() -> list[str]:
    return [
        name
        for name in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
        if not _secret(name)
    ]


def _read_title(folder: Path) -> str:
    path = folder / "finance-1.txt"
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    if lines[:1] == ["TITLE"] and len(lines) > 1:
        return lines[1].strip()
    return ""


def _read_source(folder: Path) -> str:
    path = folder / "finance-1.txt"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if "Sources:" not in text:
        return ""
    chunk = text.split("Sources:", 1)[1].split("\n\n", 1)[0]
    return " ".join(line.strip() for line in chunk.splitlines() if line.strip())


def _stories(folder: Path) -> list[dict]:
    path = folder / "nguon.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _write_schedule(folder: Path, when: datetime) -> None:
    lich = _load("lich")
    times = lich.public_times(when)
    row = lich.row_for(when)
    stories = _stories(folder)
    lead = stories[0]["title"] if stories else f"U.S. briefing {when.strftime('%B')} {when.day}"
    money_raw = str(row.get("title") or _read_title(folder) or row.get("hook") or "One U.S. household money number")
    money_source = str(row.get("source") or _read_source(folder))
    news_title = _title(lead.rstrip("."), when)
    news_short = _title(lead.rstrip("."), when, 92) + " #Shorts"
    money_title = _title(money_raw.rstrip("."), when)
    money_short = _title(money_raw.rstrip("."), when, 92) + " #Shorts"
    news_lines = [
        f"U.S. briefing for {when.strftime('%A, %B')} {when.day}.",
        "",
        "Stories with pictures from PBS NewsHour, the New York Times, and NPR:",
    ]
    for index, story in enumerate(stories, start=1):
        news_lines.append(f"{index}. {story.get('outlet', '')}: {story.get('title', '')}")
        news_lines.append(str(story.get("link", "")))
    news_lines += [
        "",
        "Pictures and headlines belong to the newsrooms named in the video.",
        "Not advice about your vote or your money.",
        "",
        _tags(" ".join(str(story.get("title", "")) for story in stories), "news"),
    ]
    news_description = "\n".join(news_lines)
    money_lines = [
        money_raw,
        "",
        f"Source: {money_source}" if money_source else "Source: see the on-screen citation.",
        "",
        "This is not personal financial advice.",
        "",
        _tags(money_raw + " " + money_source, "finance"),
    ]
    money_description = "\n".join(money_lines)
    files = {
        "tin": folder / "vi-du-tin.mp4",
        "short-tin": folder / "short-tin.mp4",
        "tien": folder / "tai-chinh-1.mp4",
        "short-tien": folder / "short-tien.mp4",
    }
    copy = {
        "tin": (news_title, news_description, "25"),
        "short-tin": (news_short, news_description + "\n\n#Shorts", "25"),
        "tien": (money_title, money_description, "27"),
        "short-tien": (money_short, money_description + "\n\n#Shorts", "27"),
    }
    items = []
    for name in ("tin", "short-tin", "tien", "short-tien"):
        title, description, category = copy[name]
        items.append(
            {
                "file": str(files[name]),
                "title": title,
                "description": description,
                "publish_at": times[name].isoformat(),
                "category": category,
                "madeForKids": False,
            }
        )
    (folder / "lich.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    labels = {"tin": "BẢN TIN", "short-tin": "SHORT TIN", "tien": "BÀI TIỀN", "short-tien": "SHORT TIỀN"}
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        "Bốn video, giờ America/New_York: bản tin 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00.",
        "Kênh: UCE056WfiFMV6k4N5irnIDnA",
        "Không dành cho trẻ em.",
        f"Bài tiền: {money_raw}",
        "",
    ]
    for name, item in zip(("tin", "short-tin", "tien", "short-tien"), items):
        blocks += [
            f"===== {labels[name]} =====",
            f"File: {files[name].name}",
            f"Giờ công khai: {times[name].strftime('%Y-%m-%d %H:%M %Z')}",
            "Không dành cho trẻ em.",
            item["title"],
            "",
            item["description"],
            "",
        ]
    (folder / "youtube.txt").write_text("\n".join(blocks), encoding="utf-8")


def _probe_line(path: Path) -> str:
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True, errors="replace")
    text = proc.stderr
    duration = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", text)
    size = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", text)
    fps = re.search(r"(\d+(?:\.\d+)?) fps", text)
    clock = "?"
    if duration:
        hours, minutes, seconds = duration.groups()
        clock = f"{int(hours) * 3600 + int(minutes) * 60 + float(seconds):.1f}s"
    frame = f"{size.group(1)}x{size.group(2)}" if size else "?"
    rate = f"{fps.group(1)} fps" if fps else "?"
    audio = "có tiếng" if "Audio:" in text else "không tiếng"
    return f"{path.name}: {frame}, {clock}, {rate}, {audio}"


def _artifacts(folder: Path, day: str) -> None:
    ART.mkdir(parents=True, exist_ok=True)
    mapping = {
        "vi-du-tin.mp4": f"tin-{day}.mp4",
        "short-tin.mp4": f"short-tin-{day}.mp4",
        "tai-chinh-1.mp4": f"tien-{day}.mp4",
        "short-tien.mp4": f"short-tien-{day}.mp4",
    }
    for source, dest in mapping.items():
        shutil.copy2(folder / source, ART / dest)
        print(f"Artifacts: {dest}")
    shutil.copy2(folder / "youtube.txt", ART / f"youtube-{day}.txt")
    print(f"Artifacts: youtube-{day}.txt")


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
    if set(PACK) <= posted_before and not args.titles_only:
        print(f"Ngày {day} đã hẹn đủ bốn video. Không dựng lại.")
        return 0
    news_code = 1
    for attempt in range(2):
        if not args.titles_only:
            news_code = _run("run.py", day)
            with log.open("a", encoding="utf-8") as handle:
                handle.write(f"{started} tin={news_code} try={attempt + 1} day={day}\n")
        if (folder / "vi-du-tin.mp4").exists() and (folder / "nguon.json").exists():
            break
        print(f"Chưa có bản tin (lần {attempt + 1}).")
        time.sleep(15)
    if not (folder / "vi-du-tin.mp4").exists():
        print(f"Không dựng được bản tin trong {folder}.")
        return 1
    money_code = 1
    for attempt in range(2):
        if args.titles_only and (folder / "tai-chinh-1.mp4").exists():
            money_code = 0
            break
        money_code = _run("tien.py", day)
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"{started} tien={money_code} try={attempt + 1} day={day}\n")
        if (folder / "tai-chinh-1.mp4").exists():
            break
        print(f"Chưa có bài tiền (lần {attempt + 1}).")
        time.sleep(15)
    if not (folder / "tai-chinh-1.mp4").exists():
        print(f"Không dựng được bài tiền trong {folder}.")
        return 1
    if not args.titles_only:
        cutter = _load("cat_short")
        cutter.cut(folder / "vi-du-tin.mp4", folder / "short-tin.mp4", 35)
        cutter.cut(folder / "tai-chinh-1.mp4", folder / "short-tien.mp4", 35)
    missing_files = [name for name in PACK if not (folder / name).exists()]
    if missing_files:
        print("Thiếu file: " + ", ".join(missing_files))
        return 1
    _write_schedule(folder, when)
    for name in PACK:
        print(_probe_line(folder / name))
    outlets = {str(item.get("outlet", "")) for item in _stories(folder)}
    print("Báo trong bản tin: " + ", ".join(sorted(outlets)))
    if not args.dang:
        print("Đã dựng bốn video. Chưa hẹn giờ vì không có --dang.")
        return 0
    missing_secrets = _missing_youtube()
    if missing_secrets:
        _artifacts(folder, day)
        print(
            "Thiếu "
            + ", ".join(missing_secrets)
            + ". Đã để bốn video và phần chữ trong artifacts. "
            "Không gõ mật khẩu. Không hẹn giờ kênh UCE056WfiFMV6k4N5irnIDnA."
        )
        return 0
    code = _load("len_lich").schedule(folder)
    if code != 0:
        _artifacts(folder, day)
        print("Hẹn giờ chưa xong. Bốn video và phần chữ nằm trong artifacts. Không in token.")
        return code
    print("Đã hẹn bốn video lúc 8:00, 12:00, 16:00 và 20:00 giờ miền Đông. Không dành cho trẻ em.")
    return 0


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
