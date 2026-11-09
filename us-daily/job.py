"""Dựng bản tin và một bài tiền, cắt hai Short, rồi hẹn giờ công khai.

Máy chủ Cursor chạy lúc 18:00 giờ Việt Nam, tức 6:00 sáng New York vào mùa đông.
Bốn video được hẹn: 8:00, 12:00, 16:00 và 20:00 giờ miền Đông.
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


def _field(text: str, name: str) -> str:
    marker = f"{name}\n"
    start = text.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    rest = text[start:]
    ends = [rest.find(f"\n{label}\n") for label in ("OPENING SHOT", "DESCRIPTION", "SPOKEN SCRIPT")]
    ends = [item for item in ends if item >= 0]
    if not ends:
        return rest.strip()
    return rest[: min(ends)].strip()


def _first_sentence(text: str) -> str:
    match = re.search(r".+?[.!?]", text.replace("\n", " ").strip())
    return match.group(0).strip() if match else text.strip()


def _title(sentence: str, when: datetime, total: int = 100) -> str:
    stamp = when.strftime("%b ") + str(when.day)
    suffix = f" | {stamp}"
    sentence = sentence.rstrip(".")
    limit = total - len(suffix)
    if len(sentence) > limit:
        cut = sentence[:limit].rsplit(" ", 1)[0].rstrip(" ,:;-")
        sentence = cut or sentence[:limit]
    return sentence + suffix


def _finance_post(path: Path, when: datetime) -> str:
    text = path.read_text(encoding="utf-8")
    raw_title = _field(text, "TITLE").splitlines()
    title = _title(raw_title[0] if raw_title else "U.S. money note", when)
    spoken = re.sub(r"\s+", " ", _field(text, "SPOKEN SCRIPT"))
    sentences = re.findall(r".+?[.!?]", spoken)
    lead = " ".join(part.strip() for part in sentences[:2])
    source = ""
    description = _field(text, "DESCRIPTION")
    if "Sources:" in description:
        source = description.split("Sources:", 1)[1].split("\n\n", 1)[0].strip()
    lines = [
        title,
        "",
        lead,
        "",
        f"Source: {source}" if source else "The dollar amounts in this video are an example.",
        "",
        "This is not personal financial advice.",
        "",
        _tags(title + " " + lead, "finance"),
    ]
    return "\n".join(lines).strip()


def _news_post(folder: Path, when: datetime) -> tuple[str, str]:
    text = (folder / "news.txt").read_text(encoding="utf-8")
    spoken = _field(text, "SPOKEN SCRIPT")
    sources = re.findall(r"^\d+\.\s+(PBS NewsHour|New York Times|NPR):\s+(.+)$", _field(text, "DESCRIPTION"), re.M)
    if sources:
        opening = sources[0][1].strip()
        stories = [f"{outlet}: {headline.strip()}" for outlet, headline in sources]
    else:
        paragraphs = [block.strip() for block in spoken.split("\n\n") if block.strip()]
        opening = _first_sentence(paragraphs[0] if paragraphs else "U.S. briefing")
        stories = []
        for paragraph in paragraphs[1:]:
            sentence = _first_sentence(paragraph)
            if sentence.lower().startswith("not advice"):
                continue
            stories.append(sentence)
    title = _title(opening, when, 70)
    video = folder / "vi-du-but.mp4"
    if not video.exists():
        video = folder / "vi-du-tin.mp4"
    body = [
        title,
        "",
        opening,
        "",
        "In this briefing:",
        *[f"{index}. {sentence}" for index, sentence in enumerate(stories, start=1)],
        "",
        "Pictures and headlines belong to the newsrooms named in the video.",
        "This is not advice about your vote or your money.",
        "",
        _tags(title + " " + " ".join(stories), "news"),
    ]
    return str(video), "\n".join(body).strip()


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


def _news_file(folder: Path) -> Path:
    video = folder / "vi-du-but.mp4"
    if video.exists():
        return video
    return folder / "vi-du-tin.mp4"


def _short_text(title: str, lead: str, kind: str) -> tuple[str, str]:
    suffix = " #Shorts"
    short_title = title if title.endswith(suffix) else f"{title}{suffix}"
    if len(short_title) > 100:
        room = 100 - len(suffix)
        cut = title[:room].rsplit(" ", 1)[0] or title[:room]
        short_title = cut + suffix
    description = "\n".join(
        [
            lead,
            "",
            "The full video is on the channel today.",
            "",
            "This is not personal financial advice." if kind == "finance" else "This is not advice about your vote or your money.",
            "",
            _tags(title + " " + lead, kind),
            "#Shorts",
        ]
    )
    return short_title, description


def _manifest(folder: Path, when: datetime, posts: list[dict]) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("lich", ROOT / "us-daily" / "lich.py")
    lich = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lich)
    times = lich.public_times(when)
    items = []
    for post in posts:
        stamp = times[post["slot"]]
        items.append(
            {
                "file": str(post["file"]),
                "title": post["title"],
                "description": post["description"],
                "publish_at": stamp.isoformat(),
                "category": post["category"],
            }
        )
    (folder / "lich.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def write_posts(folder: Path, when: datetime) -> Path:
    import importlib.util

    spec = importlib.util.spec_from_file_location("lich", ROOT / "us-daily" / "lich.py")
    lich = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lich)
    times = lich.public_times(when)
    clock = ", ".join(item.strftime("%H:%M") for item in times.values())
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        f"Giờ công khai, giờ miền Đông: {clock}.",
        "Thứ tự: bản tin 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00.",
        "Mùa đông các mốc đó là 20:00, 00:00, 04:00 và 08:00 giờ Việt Nam.",
        "",
    ]
    posts: list[dict] = []
    money_path = folder / "finance-1.txt"
    money_video = folder / "tai-chinh-1.mp4"
    blocks.append("===== BÀI TIỀN =====")
    blocks.append(f"File video: {money_video if money_video.exists() else 'chưa ghép'}")
    blocks.append(f"Giờ công khai: {times['tien'].strftime('%Y-%m-%d %H:%M %Z')}")
    blocks.append("")
    if money_path.exists():
        money_text = _finance_post(money_path, when)
        blocks.append(money_text)
        title = money_text.splitlines()[0]
        posts.append(
            {
                "slot": "tien",
                "file": money_video,
                "title": title,
                "description": money_text,
                "category": "27",
            }
        )
    else:
        blocks.append("Chưa có kịch bản tiền.")
    blocks.append("")
    blocks.append("===== BẢN TIN =====")
    news_video = _news_file(folder)
    if (folder / "news.txt").exists():
        _video, news = _news_post(folder, when)
        blocks.append(f"File video: {news_video if news_video.exists() else 'chưa ghép'}")
        blocks.append(f"Giờ công khai: {times['tin'].strftime('%Y-%m-%d %H:%M %Z')}")
        blocks.append("")
        blocks.append(news)
        posts.append(
            {
                "slot": "tin",
                "file": news_video,
                "title": news.splitlines()[0],
                "description": news,
                "category": "25",
            }
        )
    else:
        blocks.append("Hôm nay chưa có bản tin. Tin Mỹ vẫn là một video mỗi ngày.")
    blocks.append("")
    shorts = _cut_shorts(folder, posts, times)
    for short in shorts:
        blocks.append(f"===== SHORT {short['slot']} =====")
        blocks.append(f"File: {short['file']}")
        blocks.append(f"Giờ công khai: {times[short['slot']].strftime('%Y-%m-%d %H:%M %Z')}")
        blocks.append(short["title"])
        blocks.append("")
        posts.append(short)
    dest = folder / "youtube.txt"
    dest.write_text("\n".join(blocks), encoding="utf-8")
    _manifest(folder, when, posts)
    print(dest)
    _leave_for_download(folder, when, dest)
    return dest


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


def _cut_shorts(folder: Path, posts: list[dict], times: dict) -> list[dict]:
    spec_path = ROOT / "us-daily" / "cat_short.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("cat_short", spec_path)
    cutter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cutter)
    made = []
    pairing = {"tin": "short-tin", "tien": "short-tien"}
    for post in posts:
        slot = pairing.get(post["slot"])
        if slot is None or not Path(post["file"]).exists():
            continue
        dest = folder / f"{slot}.mp4"
        try:
            cutter.cut(Path(post["file"]), dest)
        except Exception as exc:
            print(f"Chưa cắt {slot}: {exc}")
            continue
        lead = post["description"].splitlines()[0]
        title, description = _short_text(post["title"].replace(" #Shorts", ""), lead, "news" if slot == "short-tin" else "finance")
        made.append(
            {
                "slot": slot,
                "file": dest,
                "title": title,
                "description": description,
                "category": post["category"],
            }
        )
    return made


def _leave_for_download(folder: Path, when: datetime, youtube: Path) -> None:
    """Máy chủ Cursor giữ file trong artifacts. Repo GitHub đang public nên không đẩy video lên đó."""
    day = when.strftime("%Y-%m-%d")
    video = folder / "vi-du-but.mp4"
    if not video.exists():
        video = folder / "vi-du-tin.mp4"
    server = Path("/opt/cursor/artifacts")
    if not server.is_dir():
        print(f"May nha. Video tin: {video}")
        return
    workspace = ROOT / "artifacts"
    workspace.mkdir(exist_ok=True)
    for dest_dir in (server, workspace):
        if video.exists():
            shutil.copy2(video, dest_dir / f"tin-{day}.mp4")
        money = folder / "tai-chinh-1.mp4"
        if money.exists():
            shutil.copy2(money, dest_dir / f"tien-{day}.mp4")
        for name in ("short-tin.mp4", "short-tien.mp4", "lich.json"):
            extra = folder / name
            if extra.exists():
                shutil.copy2(extra, dest_dir / f"{extra.stem}-{day}{extra.suffix}")
        shutil.copy2(youtube, dest_dir / f"youtube-{day}.txt")
        print(f"De tai: {dest_dir}")


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
    if not args.titles_only:
        news_code = _run("run.py", day)
        motion_code = _run("but_ve.py", day) if (folder / "news.txt").exists() else 1
        money_code = _run("tien.py", day)
        log.write_text(
            log.read_text(encoding="utf-8") + f"{started} run={news_code} but={motion_code} tien={money_code} day={day}\n"
            if log.exists()
            else f"{started} run={news_code} but={motion_code} tien={money_code} day={day}\n",
            encoding="utf-8",
        )
    if not (folder / "finance-1.txt").exists() and not (folder / "news.txt").exists():
        print(f"Chua co bai trong {folder}")
        if args.dang:
            _report(folder, when, False, "Không dựng được bản tin và bài tiền, nên chưa mở Studio.")
        return 1
    write_posts(folder, when)
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
    ok = code == 0 and len(posted) >= 4
    detail = "Đủ 4 video: bản tin 8:00, Short tin 12:00, bài tiền 16:00, Short tiền 20:00 giờ miền Đông." if ok else f"Chỉ đăng được {len(posted)} trên 4 video."
    _report(folder, when, ok, detail + "\n\n" + verdict)
    _clean_posted(folder)
    return code


def _clean_posted(folder: Path) -> None:
    """Xóa video đã qua kiểm định và đã đăng. Video chưa đăng được thì giữ lại."""
    done = folder / "da-dang.txt"
    posted = set(done.read_text(encoding="utf-8").splitlines()) if done.exists() else set()
    # Short được cắt từ video dài, nên video dài chỉ xóa khi Short của nó cũng đã đăng.
    needs = {"vi-du-but.mp4": "short-tin.mp4", "vi-du-tin.mp4": "short-tin.mp4", "tai-chinh-1.mp4": "short-tien.mp4"}
    removed = []
    for name in sorted(posted):
        path = folder / name
        if path.exists() and needs.get(name, name) in posted:
            path.unlink()
            removed.append(name)
    if {"short-tin.mp4", "short-tien.mp4"} <= posted and any(name in posted for name in ("vi-du-but.mp4", "vi-du-tin.mp4")) and "tai-chinh-1.mp4" in posted:
        for leftover in [*folder.glob("vi-du-tin.mp4"), *folder.glob("anh/*.mp4"), *folder.glob("anh/*.mp3"), *folder.glob("*.mp3")]:
            leftover.unlink()
            removed.append(leftover.name)
    if removed:
        print(f"Đã xóa {len(removed)} file video đã đăng trong {folder.name}.")


if __name__ == "__main__":
    sys.exit(main())
