"""Dựng bốn video trong ngày rồi hẹn giờ công khai.

Bản tin ngang 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00
giờ America/New_York. Cờ --dang gọi len_lich.py bằng token.
Không mở Chrome. Không gõ mật khẩu. Không in token.
Thiếu YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET hoặc YOUTUBE_REFRESH_TOKEN
thì chép bốn file và phần chữ vào artifacts rồi dừng.
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
        if any(item in words for item in ("card", "debt", "apr", "credit")):
            picked.append("#CreditCard")
        if "grocery" in words:
            picked.append("#Groceries")
        if any(item in words for item in ("paycheck", "budget", "split")):
            picked.append("#Budget")
        if any(item in words for item in ("emergency", "saving")):
            picked.append("#Savings")
        if any(item in words for item in ("fund", "invest")):
            picked.append("#Investing")
        if any(item in words for item in ("home", "mortgage", "down payment", "closing", "housing")):
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


def _probe(path: Path) -> dict:
    import imageio_ffmpeg

    proc = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path)],
        capture_output=True,
        text=True,
        errors="replace",
    )
    text = proc.stderr
    info: dict = {"duration": None, "size": None, "audio": "Audio:" in text, "fps": None}
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


def _calendar(when: datetime):
    spec = importlib.util.spec_from_file_location("lich", ROOT / "us-daily" / "lich.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.row_for(when), module.public_times(when)


def _stories(folder: Path) -> list[dict]:
    path = folder / "tin.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _finance_title(folder: Path, row: dict) -> str:
    if row.get("title"):
        return row["title"]
    script = folder / "finance-1.txt"
    if script.exists():
        text = script.read_text(encoding="utf-8")
        if "TITLE\n" in text:
            return text.split("TITLE\n", 1)[1].split("\n", 1)[0].strip()
    return row.get("hook") or "A household money number"


def _cut_shorts(folder: Path) -> None:
    spec = importlib.util.spec_from_file_location("cat_short", ROOT / "us-daily" / "cat_short.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.cut(folder / "vi-du-tin.mp4", folder / "short-tin.mp4", 35)
    module.cut(folder / "tai-chinh-1.mp4", folder / "short-tien.mp4", 35)


def _news_copy(stories: list[dict], when: datetime, short: bool) -> tuple[str, str]:
    lead = stories[0]["title"].rstrip(".") if stories else "U.S. briefing"
    title = _title(lead, when, 92 if short else 100)
    if short:
        title += " #Shorts"
    lines = [lead, ""]
    if short:
        lines += ["The opening of today's U.S. briefing.", ""]
    lines += ["Stories with pictures from PBS NewsHour, the New York Times, and NPR.", ""]
    for index, story in enumerate(stories, start=1):
        lines.append(f"{index}. {story['outlet']}: {story['title']}")
        lines.append(story["link"])
    lines += [
        "",
        "Pictures and headlines belong to the newsrooms named on screen.",
        "This is not advice about your vote or your money.",
        "This video is not made for kids.",
        "",
        _tags(" ".join(story["title"] for story in stories), "news") + (" #Shorts" if short else ""),
    ]
    return title, "\n".join(lines)


def _money_copy(folder: Path, row: dict, when: datetime, short: bool) -> tuple[str, str]:
    headline = _finance_title(folder, row)
    title = _title(headline, when, 92 if short else 100)
    if short:
        title += " #Shorts"
    lines = [
        row.get("hook") or headline,
        "",
        f"Number on screen: {row.get('number', '')}".rstrip(),
        f"Source: {row.get('source', '')}".rstrip(),
        "",
        "This is not personal financial advice.",
        "This video is not made for kids.",
        "",
        _tags(f"{headline} {row.get('source', '')}", "finance") + (" #Shorts" if short else ""),
    ]
    return title, "\n".join(lines)


def _write_schedule(folder: Path, when: datetime, stories: list[dict], row: dict, times: dict) -> None:
    news_title, news_desc = _news_copy(stories, when, False)
    short_news_title, short_news_desc = _news_copy(stories, when, True)
    money_title, money_desc = _money_copy(folder, row, when, False)
    short_money_title, short_money_desc = _money_copy(folder, row, when, True)
    items = [
        {
            "file": str((folder / "vi-du-tin.mp4").resolve()),
            "title": news_title,
            "description": news_desc,
            "publish_at": times["tin"].isoformat(),
            "category": "25",
            "madeForKids": False,
        },
        {
            "file": str((folder / "short-tin.mp4").resolve()),
            "title": short_news_title,
            "description": short_news_desc,
            "publish_at": times["short-tin"].isoformat(),
            "category": "25",
            "madeForKids": False,
        },
        {
            "file": str((folder / "tai-chinh-1.mp4").resolve()),
            "title": money_title,
            "description": money_desc,
            "publish_at": times["tien"].isoformat(),
            "category": "27",
            "madeForKids": False,
        },
        {
            "file": str((folder / "short-tien.mp4").resolve()),
            "title": short_money_title,
            "description": short_money_desc,
            "publish_at": times["short-tien"].isoformat(),
            "category": "27",
            "madeForKids": False,
        },
    ]
    (folder / "lich.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        "Kênh: UCE056WfiFMV6k4N5irnIDnA",
        "Không dành cho trẻ em (selfDeclaredMadeForKids: false).",
        "Thứ tự: bản tin 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00 giờ America/New_York.",
        "",
    ]
    labels = ("BẢN TIN", "SHORT TIN", "BÀI TIỀN", "SHORT TIỀN")
    for label, item in zip(labels, items):
        blocks += [
            f"===== {label} =====",
            f"File: {Path(item['file']).name}",
            f"Giờ công khai: {item['publish_at']}",
            "madeForKids: false",
            item["title"],
            "",
            item["description"],
            "",
        ]
    (folder / "youtube.txt").write_text("\n".join(blocks), encoding="utf-8")


def _acceptable(folder: Path) -> tuple[bool, str]:
    expect = {
        "vi-du-tin.mp4": {"shape": (1280, 720), "min": 45, "max": 700, "fps": 20},
        "tai-chinh-1.mp4": {"shape": (1280, 720), "min": 30, "max": 700, "fps": 20},
        "short-tin.mp4": {"shape": (1080, 1920), "min": 30, "max": 40, "fps": 29},
        "short-tien.mp4": {"shape": (1080, 1920), "min": 30, "max": 40, "fps": 29},
    }
    lines: list[str] = []
    ok = True
    for name, rule in expect.items():
        path = folder / name
        if not path.exists():
            ok = False
            lines.append(f"{name}: thiếu file")
            continue
        info = _probe(path)
        problems = []
        if info["size"] != rule["shape"]:
            problems.append(f"khung {info['size']}")
        length = info["duration"] or 0
        if not (rule["min"] <= length <= rule["max"]):
            problems.append(f"dài {length:.1f}s")
        if not info["fps"] or info["fps"] < rule["fps"]:
            problems.append(f"{info['fps']} fps")
        if not info["audio"]:
            problems.append("không có tiếng")
        if problems:
            ok = False
            lines.append(f"{name}: " + "; ".join(problems))
        else:
            lines.append(f"{name}: {info['size'][0]}x{info['size'][1]}, {length:.1f}s, {info['fps']:.0f} fps")
    stories = _stories(folder)
    outlets = {item.get("outlet") for item in stories}
    allowed = {"PBS NewsHour", "New York Times", "NPR"}
    if len(stories) < 4:
        ok = False
        lines.append(f"bản tin chỉ có {len(stories)} bài có ảnh")
    elif not outlets <= allowed:
        ok = False
        lines.append("bản tin có nguồn ngoài PBS NewsHour, New York Times và NPR")
    else:
        lines.append("bài có ảnh: " + "; ".join(f"{item['outlet']}: {item['title']}" for item in stories))
    missing = [name for name in ("PBS NewsHour", "New York Times", "NPR") if name not in outlets]
    if missing:
        lines.append("nguồn không có bài có ảnh: " + ", ".join(missing))
    return ok, "\n".join(lines)


def _artifacts(folder: Path, day: str) -> None:
    dest_root = Path("/opt/cursor/artifacts")
    dest_root.mkdir(parents=True, exist_ok=True)
    names = {
        "vi-du-tin.mp4": f"tin-{day}.mp4",
        "short-tin.mp4": f"short-tin-{day}.mp4",
        "tai-chinh-1.mp4": f"tien-{day}.mp4",
        "short-tien.mp4": f"short-tien-{day}.mp4",
    }
    for src, dest in names.items():
        shutil.copy2(folder / src, dest_root / dest)
        print(f"Artifact: {dest_root / dest}")
    target = dest_root / f"youtube-{day}.txt"
    shutil.copy2(folder / "youtube.txt", target)
    print(f"Artifact: {target}")


def _tokens_missing() -> list[str]:
    return [
        name
        for name in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
        if not _secret(name)
    ]


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
    row, times = _calendar(when)
    print(f"Ngày New York: {day} {when.strftime('%H:%M %Z')}")
    print(f"Bài tiền: {row.get('number', '')} { _finance_title(folder, row) }".strip())
    for name, stamp in times.items():
        print(f"Giờ {name}: {stamp.strftime('%Y-%m-%d %H:%M %Z')}")
    passed = False
    verdict = ""
    for attempt in range(3):
        if attempt:
            print(f"Chưa đạt (lần {attempt}). Dựng lại...")
            time.sleep(15 * attempt)
        news_code = _run("run.py", day)
        money_code = _run("tien.py", day)
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"{started} news={news_code} money={money_code} try={attempt + 1} day={day}\n")
        if (folder / "vi-du-tin.mp4").exists() and (folder / "tai-chinh-1.mp4").exists():
            try:
                _cut_shorts(folder)
            except Exception as exc:
                print(f"Không cắt được Short: {exc.__class__.__name__}")
        stories = _stories(folder)
        if stories and all((folder / name).exists() for name in ("vi-du-tin.mp4", "short-tin.mp4", "tai-chinh-1.mp4", "short-tien.mp4")):
            _write_schedule(folder, when, stories, row, times)
        passed, verdict = _acceptable(folder)
        print(verdict)
        if passed:
            break
    if not passed:
        print("Không đủ bốn video. Không hẹn giờ, không mở Chrome.")
        return 1
    if not args.dang:
        print("Chưa hẹn giờ. Thêm --dang để hẹn bằng token YouTube.")
        return 0
    missing = _tokens_missing()
    if missing:
        _artifacts(folder, day)
        print(
            "Thiếu token YouTube: "
            + ", ".join(missing)
            + ". Đã để bốn video và phần chữ trong /opt/cursor/artifacts. "
            "Không gõ mật khẩu. Không hẹn giờ kênh UCE056WfiFMV6k4N5irnIDnA."
        )
        return 0
    spec = importlib.util.spec_from_file_location("len_lich", ROOT / "us-daily" / "len_lich.py")
    uploader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(uploader)
    return uploader.schedule(folder)


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
