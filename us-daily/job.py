"""Dựng bốn video trong ngày rồi hẹn giờ công khai.

Bản tin ngang 8:00, Short tin 12:00, bài tiền ngang 16:00, Short tiền 20:00
giờ America/New_York. Cờ --dang gọi len_lich.py bằng token. Không mở Chrome,
không gõ mật khẩu. Thiếu token thì chép bốn file và phần chữ vào artifacts rồi dừng.
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
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["US_DAILY_DAY"] = day
    proc = subprocess.run([PYTHON, "-u", str(ROOT / "us-daily" / script)], cwd=ROOT, env=env)
    return proc.returncode


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def _youtube_ready() -> bool:
    return all(_secret(name) for name in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"))


def _cut_shorts(folder: Path) -> None:
    cutter = _load("cat_short")
    cutter.cut(folder / "vi-du-tin.mp4", folder / "short-tin.mp4", 35)
    cutter.cut(folder / "tai-chinh-1.mp4", folder / "short-tien.mp4", 35)


def _write_schedule(folder: Path, when: datetime) -> None:
    news = json.loads((folder / "tin.json").read_text(encoding="utf-8"))
    money = json.loads((folder / "tien.json").read_text(encoding="utf-8"))
    times = _load("lich").public_times(when)
    lead = news[0]["title"].rstrip(".") if news else f"U.S. briefing {when.strftime('%B')} {when.day}"
    story_lines = []
    for index, item in enumerate(news, start=1):
        story_lines.append(f"{index}. {item['outlet']}: {item['title']}")
        story_lines.append(item["link"])
    news_body = "\n".join(
        [
            lead + ".",
            "",
            "In this briefing:",
            *story_lines,
            "",
            "Stories and pictures: PBS NewsHour, New York Times, and NPR.",
            "Each picture is the photo that newsroom attached to that article.",
            "Not advice about your vote or your money.",
            "",
            _tags(" ".join(item["title"] for item in news), "news"),
        ]
    )
    money_body = "\n".join(
        [
            money["title"] + ".",
            "",
            f"The number on screen: {money['number']}.",
            f"Source: {money['source']}",
            "",
            "This is not personal financial advice.",
            "",
            _tags(money["title"] + " " + money["source"], "finance"),
        ]
    )
    rows = [
        ("vi-du-tin.mp4", _title(lead, when, 100), news_body, "tin", "25"),
        ("short-tin.mp4", _title(lead, when, 90) + " #Shorts", news_body + "\n\n#Shorts", "short-tin", "25"),
        ("tai-chinh-1.mp4", _title(money["title"], when, 100), money_body, "tien", "27"),
        ("short-tien.mp4", _title(money["title"], when, 90) + " #Shorts", money_body + "\n\n#Shorts", "short-tien", "27"),
    ]
    items = []
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        "Kênh: UCE056WfiFMV6k4N5irnIDnA",
        "Không dành cho trẻ em.",
        "Giờ công khai America/New_York: 08:00 bản tin, 12:00 Short tin, 16:00 bài tiền, 20:00 Short tiền.",
        "",
    ]
    labels = {
        "tin": "BẢN TIN",
        "short-tin": "SHORT TIN",
        "tien": "BÀI TIỀN",
        "short-tien": "SHORT TIỀN",
    }
    for name, title, description, slot, category in rows:
        when_slot = times[slot]
        items.append(
            {
                "file": str((folder / name).resolve()),
                "title": title[:100],
                "description": description,
                "publish_at": when_slot.isoformat(),
                "category": category,
                "selfDeclaredMadeForKids": False,
            }
        )
        blocks += [
            f"===== {labels[slot]} =====",
            f"File: {name}",
            f"Giờ công khai: {when_slot.strftime('%Y-%m-%d %H:%M %Z')}",
            "Không dành cho trẻ em.",
            title,
            "",
            description,
            "",
        ]
    (folder / "lich.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "youtube.txt").write_text("\n".join(blocks), encoding="utf-8")


def _check_pack(folder: Path, when: datetime) -> tuple[bool, str]:
    lines = ["KIỂM TRA BỐN VIDEO"]
    bad = 0
    expected = {
        "vi-du-tin.mp4": ((1280, 720), 40, 20 * 60, 0),
        "tai-chinh-1.mp4": ((1280, 720), 20, 12 * 60, 0),
        "short-tin.mp4": ((1080, 1920), 30, 40, 29),
        "short-tien.mp4": ((1080, 1920), 30, 40, 29),
    }
    for name, (shape, low, high, min_fps) in expected.items():
        path = folder / name
        problems = []
        if not path.exists():
            problems.append("thiếu file")
        else:
            info = _probe(path)
            length = info["duration"] or 0
            if info["size"] != shape:
                problems.append(f"khung {info['size']}, cần {shape[0]}x{shape[1]}")
            if length < low or length > high:
                problems.append(f"dài {length:.1f}s, cần {low}–{high}s")
            if min_fps and (not info["fps"] or info["fps"] < min_fps):
                problems.append(f"{info['fps']} fps, cần ít nhất {min_fps}")
            if not info["audio"]:
                problems.append("không có tiếng")
        if problems:
            bad += 1
            lines.append(f"- {name} [CHẶN] {'; '.join(problems)}")
        else:
            info = _probe(path)
            lines.append(f"- {name} [ĐẠT] {info['size'][0]}x{info['size'][1]}, {info['duration']:.1f}s, {info['fps']} fps")
    news_path = folder / "tin.json"
    outlets = set()
    if news_path.exists():
        for item in json.loads(news_path.read_text(encoding="utf-8")):
            outlets.add(item.get("outlet", ""))
    for outlet in ("PBS NewsHour", "New York Times", "NPR"):
        if outlet not in outlets:
            bad += 1
            lines.append(f"- thiếu bài có ảnh của {outlet}")
    money_path = folder / "tien.json"
    if money_path.exists():
        money = json.loads(money_path.read_text(encoding="utf-8"))
        if not re.search(r"\d", money.get("title", "")):
            bad += 1
            lines.append("- tiêu đề bài tiền không có số")
        row = _load("lich").row_for(when)
        wanted = row.get("title") or row.get("key", "")
        if row.get("title") and money.get("title") != row["title"]:
            bad += 1
            lines.append(f"- bài tiền là «{money.get('title')}», lịch ngày này là «{wanted}»")
        if row.get("number") and money.get("number") != row["number"]:
            bad += 1
            lines.append(f"- số trên bài là {money.get('number')}, lịch là {row['number']}")
    else:
        bad += 1
        lines.append("- thiếu tien.json")
    scenes = folder / "tai-chinh-1.canh.txt"
    if scenes.exists():
        count = len([line for line in scenes.read_text(encoding="utf-8").splitlines() if line.strip()])
        if count < 4:
            bad += 1
            lines.append(f"- bài tiền chỉ {count} cảnh, cần đổi cảnh theo từng câu")
        else:
            lines.append(f"- bài tiền {count} cảnh")
    manifest = folder / "lich.json"
    if not manifest.exists():
        bad += 1
        lines.append("- thiếu lich.json")
    else:
        items = json.loads(manifest.read_text(encoding="utf-8"))
        hours = []
        for item in items:
            stamp = datetime.fromisoformat(item["publish_at"]).astimezone(NY)
            hours.append(stamp.strftime("%H:%M"))
            if item.get("selfDeclaredMadeForKids") is not False:
                bad += 1
                lines.append(f"- {Path(item['file']).name} chưa đánh dấu không dành cho trẻ em")
            if len(item.get("title", "")) > 100:
                bad += 1
                lines.append(f"- tiêu đề dài {len(item['title'])} ký tự")
        if hours != ["08:00", "12:00", "16:00", "20:00"]:
            bad += 1
            lines.append(f"- giờ công khai {hours}, cần 08:00, 12:00, 16:00, 20:00")
        else:
            lines.append("- giờ 08:00, 12:00, 16:00, 20:00 và không dành cho trẻ em")
    lines.append("")
    lines.append("KẾT LUẬN: ĐẠT." if bad == 0 else f"KẾT LUẬN: {bad} mục bị chặn.")
    report = "\n".join(lines)
    (folder / "kiem-dinh.txt").write_text(report + "\n", encoding="utf-8")
    return bad == 0, report


def _copy_artifacts(folder: Path, day: str) -> None:
    dest_root = Path("/opt/cursor/artifacts")
    dest_root.mkdir(parents=True, exist_ok=True)
    mapping = {
        "vi-du-tin.mp4": f"tin-{day}.mp4",
        "short-tin.mp4": f"short-tin-{day}.mp4",
        "tai-chinh-1.mp4": f"tien-{day}.mp4",
        "short-tien.mp4": f"short-tien-{day}.mp4",
        "youtube.txt": f"youtube-{day}.txt",
    }
    for source, name in mapping.items():
        src = folder / source
        if src.exists():
            shutil.copy2(src, dest_root / name)
            print(f"Đã để {name} trong artifacts.")


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
    names = ("vi-du-tin.mp4", "short-tin.mp4", "tai-chinh-1.mp4", "short-tien.mp4")
    passed = False
    verdict = ""
    for attempt in range(3):
        if attempt:
            print(f"Kiểm tra chưa đạt (lần {attempt}). Dựng lại...")
            time.sleep(15 * attempt)
            for name in names:
                (folder / name).unlink(missing_ok=True)
        news_code = _run("run.py", day)
        money_code = _run("tien.py", day)
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"{started} tin={news_code} tien={money_code} try={attempt + 1} day={day}\n")
        if (folder / "vi-du-tin.mp4").exists() and (folder / "tai-chinh-1.mp4").exists():
            try:
                _cut_shorts(folder)
            except Exception as exc:
                print(f"Chưa cắt được Short: {exc.__class__.__name__}")
        if (folder / "tin.json").exists() and (folder / "tien.json").exists():
            _write_schedule(folder, when)
        passed, verdict = _check_pack(folder, when)
        print(verdict)
        if passed:
            break
    if not passed:
        print("Chưa đủ bốn video. Không hẹn giờ, không mở Chrome.")
        return 1
    if not args.dang:
        print("Đã dựng bốn video. Chưa hẹn giờ vì không có cờ --dang.")
        return 0
    if not _youtube_ready():
        note = (
            "Chưa hẹn giờ: thiếu YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET hoặc YOUTUBE_REFRESH_TOKEN. "
            "Không gõ mật khẩu, không mở Chrome."
        )
        with (folder / "youtube.txt").open("a", encoding="utf-8") as handle:
            handle.write("\n" + note + "\n")
        _copy_artifacts(folder, day)
        print(note)
        return 0
    proc = subprocess.run([PYTHON, "-u", str(ROOT / "us-daily" / "len_lich.py"), str(folder)], cwd=ROOT)
    if proc.returncode != 0:
        print("YouTube không nhận lịch. Không in token, không mở Chrome.")
        return proc.returncode
    (folder / "da-dang.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    print(f"Đã hẹn bốn video ngày {day} trên kênh UCE056WfiFMV6k4N5irnIDnA.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
