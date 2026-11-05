"""Chạy bộ bài hằng ngày lúc 4:00 sáng New York.

Task Windows gọi file này lúc 15:00 giờ Việt Nam.
Mùa đông máy chờ tới 16:00. Mùa hè 15:00 đã là 4:00 sáng New York.
Job không tự đăng video.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "us-daily"
NY = ZoneInfo("America/New_York")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
PYTHON = sys.executable


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


def _title(sentence: str, when: datetime) -> str:
    stamp = when.strftime("%b ") + str(when.day)
    suffix = f" | {stamp}"
    sentence = sentence.rstrip(".")
    limit = 100 - len(suffix)
    if len(sentence) > limit:
        cut = sentence[:limit].rsplit(" ", 1)[0]
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
    ]
    return "\n".join(lines).strip()


def _news_post(folder: Path, when: datetime) -> tuple[str, str]:
    text = (folder / "news.txt").read_text(encoding="utf-8")
    spoken = _field(text, "SPOKEN SCRIPT")
    paragraphs = [block.strip() for block in spoken.split("\n\n") if block.strip()]
    opening = _first_sentence(paragraphs[0] if paragraphs else "U.S. briefing")
    title = _title(opening, when)
    stories = []
    for paragraph in paragraphs[1:]:
        sentence = _first_sentence(paragraph)
        if sentence.lower().startswith("not advice"):
            continue
        stories.append(sentence)
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
    ]
    return str(video), "\n".join(body).strip()


def write_posts(folder: Path, when: datetime) -> Path:
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        "Đăng từ 17:30 đến 18:00 giờ Việt Nam nếu đang giờ mùa đông của Mỹ.",
        "Đăng từ 16:30 đến 17:00 giờ Việt Nam nếu Mỹ đang giờ mùa hè.",
        "Cả hai mốc đều là 5:30–6:00 sáng New York. Job không tự đăng.",
        "",
    ]
    for index, name in enumerate(("finance-1.txt", "finance-2.txt"), start=1):
        path = folder / name
        blocks.append(f"===== VIDEO {index} — TÀI CHÍNH =====")
        blocks.append(f"Kịch bản: {path.name}")
        blocks.append("File video: job này chưa ghép video tài chính. Dùng title và description dưới khi có file hình.")
        blocks.append("")
        if path.exists():
            blocks.append(_finance_post(path, when))
        else:
            blocks.append("Chưa có kịch bản.")
        blocks.append("")
    video, news = _news_post(folder, when)
    blocks.append("===== VIDEO 3 — TIN TỨC =====")
    blocks.append(f"File video: {video}")
    blocks.append("")
    blocks.append(news)
    blocks.append("")
    dest = folder / "youtube.txt"
    dest.write_text("\n".join(blocks), encoding="utf-8")
    print(dest)
    return dest


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
        motion_code = _run("but_ve.py", day)
        log.write_text(
            log.read_text(encoding="utf-8") + f"{started} run={news_code} but={motion_code} day={day}\n"
            if log.exists()
            else f"{started} run={news_code} but={motion_code} day={day}\n",
            encoding="utf-8",
        )
    if not (folder / "news.txt").exists():
        print(f"Chua co bai trong {folder}")
        return 1
    write_posts(folder, when)
    return 0


if __name__ == "__main__":
    sys.exit(main())
