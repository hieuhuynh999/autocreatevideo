"""Dựng bốn video trong ngày rồi hẹn giờ công khai trên YouTube.

Bản tin ngang lúc 8:00, Short tin lúc 12:00, bài tiền lúc 16:00, Short tiền
lúc 20:00 giờ miền Đông. Cờ --dang gọi len_lich.py. Không mở Chrome, không
gõ mật khẩu, không in token. Thiếu token thì giữ file và phần chữ rồi dừng.
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


PACK = ("vi-du-tin.mp4", "short-tin.mp4", "tai-chinh-1.mp4", "short-tien.mp4")
ART = Path("/opt/cursor/artifacts")
NEED = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _section(path: Path, label: str) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    marker = f"{label}\n"
    if marker not in text:
        return ""
    body = text.split(marker, 1)[1]
    for later in ("OPENING SHOT", "DESCRIPTION", "SPOKEN SCRIPT"):
        if later == label:
            continue
        if f"\n{later}\n" in body:
            body = body.split(f"\n{later}\n", 1)[0]
    return body.strip()


def _probe(path: Path) -> dict:
    import imageio_ffmpeg

    proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True, errors="replace")
    text = proc.stderr
    info: dict = {"duration": None, "size": None, "audio": "Audio:" in text}
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if match:
        hours, minutes, seconds = match.groups()
        info["duration"] = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    size = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", text)
    if size:
        info["size"] = (int(size.group(1)), int(size.group(2)))
    return info


def _build_pack(folder: Path, day: str) -> tuple[bool, str]:
    news_code = _run("run.py", day)
    money_code = _run("tien.py", day)
    news = folder / "vi-du-tin.mp4"
    money = folder / "tai-chinh-1.mp4"
    if not news.exists() or not money.exists():
        return False, f"Chưa có video ngang (tin={news_code}, tiền={money_code})."
    cutter = _load("cat_short")
    cutter.cut(news, folder / "short-tin.mp4", 35)
    cutter.cut(money, folder / "short-tien.mp4", 35)
    return True, "Đã dựng bốn file."


def _check_pack(folder: Path, when: datetime) -> tuple[bool, str]:
    lines = ["KIỂM TRA BỐN VIDEO"]
    bad = 0
    expect = {
        "vi-du-tin.mp4": (1280, 720),
        "tai-chinh-1.mp4": (1280, 720),
        "short-tin.mp4": (1080, 1920),
        "short-tien.mp4": (1080, 1920),
    }
    for name, shape in expect.items():
        path = folder / name
        if not path.exists():
            lines.append(f"- {name}: thiếu file")
            bad += 1
            continue
        info = _probe(path)
        notes = []
        if info["size"] != shape:
            notes.append(f"khung {info['size']}, cần {shape[0]}x{shape[1]}")
        length = info["duration"] or 0
        if name.startswith("short-"):
            if length < 30 or length > 36:
                notes.append(f"dài {length:.1f}s, cần khoảng 35 giây")
        elif length < 20:
            notes.append(f"dài {length:.1f}s, bản ngang quá ngắn")
        if not info["audio"]:
            notes.append("không có tiếng")
        if notes:
            bad += 1
            lines.append(f"- {name}: " + "; ".join(notes))
        else:
            lines.append(f"- {name}: đạt, {info['size'][0]}x{info['size'][1]}, {length:.1f}s")
    review = (folder / "review.md").read_text(encoding="utf-8") if (folder / "review.md").exists() else ""
    stories = [line[4:] for line in review.splitlines() if line.startswith("  - ") and ": " in line]
    for outlet in ("PBS", "New York Times", "NPR"):
        if not any(line.startswith(outlet) for line in stories):
            bad += 1
            lines.append(f"- bản tin thiếu bài có ảnh của {outlet}")
    if len(stories) < 4:
        bad += 1
        lines.append(f"- bản tin chỉ có {len(stories)} bài có ảnh, cần ít nhất 4")
    row = _load("lich").row_for(when)
    number = str(row.get("number", ""))
    spoken = _section(folder / "finance-1.txt", "SPOKEN SCRIPT").lower()
    digits = re.sub(r"[^\d]", "", number)
    if digits and digits not in re.sub(r"[^\d]", "", spoken):
        bad += 1
        lines.append(f"- bài tiền không chứa số của ngày {row.get('date')}")
    else:
        lines.append(f"- bài tiền ngày {row.get('date')}: {row.get('title', row.get('key', ''))} {number}")
    lines.append("ĐẠT" if bad == 0 else f"{bad} lỗi")
    report = "\n".join(lines)
    (folder / "kiem-dinh.txt").write_text(report + "\n", encoding="utf-8")
    return bad == 0, report


def _write_schedule(folder: Path, when: datetime) -> None:
    lich = _load("lich")
    times = lich.public_times(when)
    row = lich.row_for(when)
    review = (folder / "review.md").read_text(encoding="utf-8") if (folder / "review.md").exists() else ""
    stories = [line[4:] for line in review.splitlines() if line.startswith("  - ") and ": " in line]
    news_title = ""
    if stories:
        news_title = re.sub(r"\s+\([^)]*\)\s*$", "", stories[0].split(": ", 1)[1]).strip()
    if not news_title:
        news_title = _section(folder / "news.txt", "TITLE").splitlines()[0].strip()
    news_description = _section(folder / "news.txt", "DESCRIPTION")
    money_raw = _section(folder / "finance-1.txt", "TITLE")
    money_title = money_raw.splitlines()[0].strip() if money_raw else ""
    money_description = _section(folder / "finance-1.txt", "DESCRIPTION")
    news_tags = _tags(news_title + " " + news_description, "news")
    money_tags = _tags(money_title + " " + money_description, "finance")
    slots = (
        ("tin", "vi-du-tin.mp4", _title(news_title, when, 100), news_description + "\n\n" + news_tags, "25"),
        ("short-tin", "short-tin.mp4", _title(news_title, when, 70) + " #Shorts", "Opening of today's U.S. briefing.\n\n" + news_description + "\n\n" + news_tags + " #Shorts", "25"),
        ("tien", "tai-chinh-1.mp4", _title(money_title, when, 100), money_description + "\n\n" + money_tags, "27"),
        ("short-tien", "short-tien.mp4", _title(money_title, when, 70) + " #Shorts", "Opening of today's money video.\n\n" + money_description + "\n\n" + money_tags + " #Shorts", "27"),
    )
    items = []
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        "Kênh: UCE056WfiFMV6k4N5irnIDnA",
        "Không dành cho trẻ em.",
        "Thứ tự: bản tin 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00 giờ America/New_York.",
        f"Bài tiền: {row.get('title', row.get('key', ''))} {row.get('number', '')}",
        "",
    ]
    for key, filename, title, description, category in slots:
        publish = times[key]
        items.append(
            {
                "file": str(folder / filename),
                "title": title[:100],
                "description": description.strip(),
                "publish_at": publish.isoformat(),
                "category": category,
                "madeForKids": False,
            }
        )
        blocks += [
            f"===== {key} =====",
            f"File: {filename}",
            f"Giờ công khai: {publish.strftime('%Y-%m-%d %H:%M %Z')}",
            "Không dành cho trẻ em.",
            title,
            "",
            description.strip(),
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
        if src.exists():
            shutil.copy2(src, ART / dest)
            print(f"Artifact: {dest}")


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
    passed = False
    verdict = ""
    for attempt in range(3):
        if attempt > 0:
            print(f"Chưa đạt (lần {attempt}). Dựng lại bốn video...")
            time.sleep(20 * attempt)
        if not args.titles_only or attempt > 0:
            built, note = _build_pack(folder, day)
            with log.open("a", encoding="utf-8") as handle:
                handle.write(f"{started} pack={int(built)} try={attempt + 1} day={day} {note}\n")
            if not built:
                verdict = note
                continue
        if not all((folder / name).exists() for name in PACK):
            verdict = "Thiếu một trong bốn video."
            continue
        _write_schedule(folder, when)
        passed, verdict = _check_pack(folder, when)
        print(verdict)
        if passed:
            break
    _copy_artifacts(folder, day)
    if not passed:
        print(verdict)
        print("Chưa hẹn giờ vì bốn video chưa đạt. Không mở Chrome.")
        return 1
    if not args.dang:
        print("Đã dựng bốn video. Thêm --dang để hẹn giờ bằng token, không mở Chrome.")
        return 0
    missing = [name for name in NEED if not _secret(name)]
    if missing:
        print(
            "Chưa hẹn giờ: thiếu "
            + ", ".join(missing)
            + ". Không gõ mật khẩu. Bốn video và phần chữ nằm trong artifacts."
        )
        return 0
    scheduler = _load("len_lich")
    code = scheduler.schedule(folder)
    if code == 0:
        with done.open("a", encoding="utf-8") as handle:
            for name in PACK:
                if name not in posted_before:
                    handle.write(name + "\n")
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
