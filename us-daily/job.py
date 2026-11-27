"""Dựng bốn video trong ngày, kiểm định, rồi hẹn giờ nếu đã có token YouTube.

Bản tin 1280x720 lúc 8:00, Short tin cắt khoảng 35 giây lúc 12:00,
bài tiền 1280x720 lúc 16:00, Short tiền lúc 20:00 giờ miền Đông.
Cờ --dang gọi len_lich.py. Không mở Chrome và không gõ mật khẩu.
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
TOKEN_NAMES = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
ARTIFACTS = Path("/opt/cursor/artifacts")
PACK = (
    ("tin", "vi-du-tin.mp4"),
    ("short-tin", "short-tin.mp4"),
    ("tien", "tai-chinh-1.mp4"),
    ("short-tien", "short-tien.mp4"),
)


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
        if any(item in words for item in ("credit card", "card balance", "apr", "debt")):
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


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tokens_ready() -> bool:
    return all(_secret(name) for name in TOKEN_NAMES)


def _normalize(path: Path) -> None:
    checker = _module("kiem_dinh")
    loud = checker._loudness(path)
    print(f"{path.name}: {loud} LUFS")
    if loud is not None and checker.LUFS_RANGE[0] <= loud <= checker.LUFS_RANGE[1]:
        return
    import imageio_ffmpeg

    tmp = path.with_name(path.stem + "-norm.mp4")
    proc = subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(path),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart",
            str(tmp),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        print(f"Không chỉnh được độ to của {path.name}")
        return
    after = checker._loudness(tmp)
    print(f"{path.name} sau chỉnh: {after} LUFS")
    if after is not None and checker.LUFS_RANGE[0] <= after <= checker.LUFS_RANGE[1]:
        tmp.replace(path)
    else:
        tmp.unlink(missing_ok=True)


def _build(day: str) -> None:
    folder = OUT / day
    news_code = _run("run.py", day)
    if not (folder / "vi-du-tin.mp4").exists():
        raise RuntimeError(f"Chưa có bản tin, run.py trả {news_code}")
    stories = json.loads((folder / "tin.json").read_text(encoding="utf-8"))
    families = {item["outlet"] for item in stories}
    missing = {"PBS NewsHour", "New York Times", "NPR"} - families
    if missing or len(stories) < 4:
        raise RuntimeError(f"Bản tin có {len(stories)} bài, thiếu nguồn {sorted(missing)}")
    for item in stories:
        print(f"Tin: {item['outlet']}: {item['title']}")
    money_code = _run("tien.py", day)
    if not (folder / "tai-chinh-1.mp4").exists():
        raise RuntimeError(f"Chưa có bài tiền, tien.py trả {money_code}")
    for name in ("vi-du-tin.mp4", "tai-chinh-1.mp4"):
        _normalize(folder / name)
    cutter = _module("cat_short")
    cutter.cut(folder / "vi-du-tin.mp4", folder / "short-tin.mp4", 35)
    cutter.cut(folder / "tai-chinh-1.mp4", folder / "short-tien.mp4", 35)
    for name in ("short-tin.mp4", "short-tien.mp4"):
        _normalize(folder / name)


def _package_fields(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    title = text.split("TITLE\n", 1)[1].split("\n", 1)[0].strip() if "TITLE\n" in text else ""
    spoken = text.split("SPOKEN SCRIPT\n", 1)[1].strip() if "SPOKEN SCRIPT\n" in text else ""
    description = ""
    if "DESCRIPTION\n" in text:
        description = text.split("DESCRIPTION\n", 1)[1].split("\nSPOKEN SCRIPT\n", 1)[0].strip()
    source = description.split("Sources:", 1)[1].strip() if "Sources:" in description else ""
    return {"title": title, "spoken": spoken, "source": source}


def _write_posts(folder: Path, when: datetime) -> None:
    lich = _module("lich")
    times = lich.public_times(when)
    stories = json.loads((folder / "tin.json").read_text(encoding="utf-8"))
    money = _package_fields(folder / "finance-1.txt")
    lead = stories[0]["title"].rstrip(".") if stories else "U.S. briefing"
    news_lines = [
        lead,
        "",
        "Stories with pictures from PBS NewsHour, the New York Times, and NPR.",
        "",
    ]
    for index, story in enumerate(stories, start=1):
        news_lines.append(f"{index}. {story['outlet']}: {story['title']}")
        news_lines.append(story["link"])
        for other in story.get("others") or []:
            news_lines.append(f"Related: {other['outlet']}: {other['title']}")
            news_lines.append(other["link"])
    news_lines += [
        "",
        "Pictures and headlines belong to the newsrooms named in the video.",
        "This is not advice about your vote or your money.",
        "",
        _tags(" ".join(story["title"] for story in stories), "news"),
    ]
    news_description = "\n".join(news_lines)
    opener = next((line.strip() for line in money["spoken"].splitlines() if line.strip()), money["title"])
    money_lines = [
        opener,
        "",
        "Source:",
        money["source"],
        "",
        "This is not personal financial advice.",
        "",
        _tags(money["title"] + " " + money["spoken"], "finance"),
    ]
    money_description = "\n".join(money_lines)
    titles = {
        "tin": _title(lead, when, 100),
        "short-tin": _title(lead, when, 91) + " #Shorts",
        "tien": _title(money["title"], when, 100),
        "short-tien": _title(money["title"], when, 91) + " #Shorts",
    }
    descriptions = {
        "tin": news_description,
        "short-tin": news_description + "\n\n#Shorts",
        "tien": money_description,
        "short-tien": money_description + "\n\n#Shorts",
    }
    categories = {"tin": "25", "short-tin": "25", "tien": "27", "short-tien": "27"}
    labels = {
        "tin": "BẢN TIN",
        "short-tin": "SHORT TIN",
        "tien": "BÀI TIỀN",
        "short-tien": "SHORT TIỀN",
    }
    items = []
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        "Bốn video, giờ công khai America/New_York: 08:00 bản tin, 12:00 Short tin, 16:00 bài tiền, 20:00 Short tiền.",
        "Không dành cho trẻ em (selfDeclaredMadeForKids: false).",
        "Kênh: UCE056WfiFMV6k4N5irnIDnA",
        "",
    ]
    for key, filename in PACK:
        path = folder / filename
        items.append(
            {
                "file": str(path.resolve()),
                "title": titles[key],
                "description": descriptions[key],
                "publish_at": times[key].isoformat(),
                "category": categories[key],
                "selfDeclaredMadeForKids": False,
            }
        )
        blocks += [
            f"===== {labels[key]} =====",
            f"File: {filename}",
            f"Giờ công khai: {times[key].strftime('%Y-%m-%d %H:%M %Z')}",
            titles[key],
            "",
            descriptions[key],
            "",
        ]
    (folder / "lich.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "youtube.txt").write_text("\n".join(blocks), encoding="utf-8")


def _artifacts(folder: Path, day: str) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    names = {
        "vi-du-tin.mp4": f"tin-{day}.mp4",
        "short-tin.mp4": f"short-tin-{day}.mp4",
        "tai-chinh-1.mp4": f"tien-{day}.mp4",
        "short-tien.mp4": f"short-tien-{day}.mp4",
    }
    for src, dest in names.items():
        shutil.copy2(folder / src, ARTIFACTS / dest)
        print(f"Artifact {dest}")
    text = (folder / "youtube.txt").read_text(encoding="utf-8")
    (ARTIFACTS / f"youtube-{day}.txt").write_text(text, encoding="utf-8")
    print(f"Artifact youtube-{day}.txt")


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
    if not args.titles_only:
        try:
            _build(day)
        except Exception as exc:
            print(f"Chưa dựng xong bốn video: {exc}")
            return 1
    if not all((folder / name).exists() for _key, name in PACK):
        print(f"Thiếu một trong bốn video trong {folder}")
        return 1
    _write_posts(folder, when)
    checker = _module("kiem_dinh")
    try:
        passed, verdict = checker.check(folder)
    except Exception as exc:
        print(f"KIỂM ĐỊNH bị lỗi: {exc.__class__.__name__}. Không hẹn giờ.")
        return 1
    print(verdict)
    if not passed:
        print("Kiểm định chưa đạt. Không hẹn giờ.")
        return 1
    _artifacts(folder, day)
    if not args.dang:
        print("Chưa hẹn giờ. Thêm --dang khi máy đã có token YouTube.")
        return 0
    if not _tokens_ready():
        print(
            "Thiếu YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET hoặc YOUTUBE_REFRESH_TOKEN. "
            "Đã để bốn video và phần chữ trong artifacts. Không hẹn giờ. Không gõ mật khẩu."
        )
        return 0
    scheduler = _module("len_lich")
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
