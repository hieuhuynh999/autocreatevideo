"""Hai video giải thích tiền và đời sống mỗi ngày.

Một con số có phép tính, lời nói, và bàn tay vẽ đô la hoặc biểu đồ đúng từ.
Không bịa số thị trường. Không tự đăng.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
NY = ZoneInfo("America/New_York")
W, H = 1280, 720
FPS = 24


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _token_at(words, second: float) -> str:
    current = ""
    for start, end, token in words:
        if start <= second:
            current = token
        if start <= second < end + 0.06:
            return token
    return current


def _money_kind(token: str) -> str | None:
    word = token.strip(" .,!?;:").lower()
    if word in {"percent", "apr", "interest", "rate", "rates"}:
        return "chart"
    if word in {"account", "bank", "house", "rent"}:
        return "building"
    if any(piece in word for piece in ("dollar", "pay", "save", "card", "bill", "fund", "money", "cost")):
        return "dollar"
    return None


def _kind_start(words, second: float) -> tuple[str | None, float | None]:
    kind = None
    started = None
    for start, _end, token in words:
        if start > second:
            break
        found = _money_kind(token)
        if found and found != kind:
            kind = found
            started = start
    return kind, started


def _title_lines(title: str, width: int = 48) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in title.split():
        trial = word if not current else f"{current} {word}"
        if len(trial) > width and current:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines[:3]


def _frame(draw_mod, title: str, number: str, token: str, kind: str | None, started: float | None, second: float) -> Image.Image:
    image = Image.new("RGB", (W, H), (10, 32, 28))
    draw = ImageDraw.Draw(image)
    title_font = draw_mod.ImageFont.truetype(draw_mod.FONT_DISPLAY, 34)
    number_size = 64 if len(number) > 10 else 92
    number_font = draw_mod.ImageFont.truetype(draw_mod.FONT_DISPLAY, number_size)
    word_font = draw_mod.FONT_MID
    for row, line in enumerate(_title_lines(title)):
        draw.text((36, 22 + row * 40), line, font=title_font, fill=(255, 255, 255))
    draw.text((700, 160), number, font=number_font, fill=(255, 214, 40))
    if kind and started is not None and second >= started:
        draw.rounded_rectangle((78, 392, 390, 628), radius=16, fill=(8, 12, 22))
        tip, direction, done = draw_mod._trace(draw, draw_mod.MODELS[kind], (second - started) * draw_mod.DRAW_SPEED)
        draw_mod._hand(draw, tip, direction, done)
    draw.rectangle((0, 640, W, H), fill=(0, 0, 0))
    if token:
        draw.text((36, 656), token, font=word_font, fill=(255, 214, 40))
    return image


def _render(draw_mod, words, audio: Path, dest: Path, title: str, number: str) -> None:
    ffmpeg = draw_mod._ffmpeg_bin()
    duration = draw_mod._duration(audio)
    frames = max(1, int(duration * FPS))
    proc = subprocess.Popen(
        [
            ffmpeg, "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
            "-i", "-",
            "-i", str(audio),
            "-shortest",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k", "-ar", "24000", "-ac", "1",
            "-movflags", "+faststart",
            str(dest),
        ],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None
    for frame in range(frames):
        second = frame / FPS
        token = _token_at(words, second)
        kind, started = _kind_start(words, second)
        image = _frame(draw_mod, title, number, token, kind, started, second)
        proc.stdin.write(image.tobytes())
    proc.stdin.close()
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg {dest.name} {code}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", default="")
    parser.add_argument("--index", type=int, default=0)
    args = parser.parse_args()
    when = datetime.now(NY)
    if args.day:
        when = datetime.strptime(args.day, "%Y-%m-%d").replace(tzinfo=NY)
    run = _load("run")
    draw_mod = _load("but_ve")
    folder = run.OUT / when.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    shot = "One number, a hand drawing a dollar sign or a falling chart as the word is spoken. No face, no readable fine print."
    for index, item in enumerate(run.finance_pair(when), start=1):
        if args.index and index != args.index:
            continue
        print(item["title"], item["words"])
        text = run._package("finance", item["spoken"], item["title"], [item["source"]], shot)
        (folder / f"finance-{index}.txt").write_text(text, encoding="utf-8")
        audio = folder / f"tai-chinh-{index}.mp3"
        words = asyncio.run(run._speak_timed(item["spoken"], audio))
        dest = folder / f"tai-chinh-{index}.mp4"
        _render(draw_mod, words, audio, dest, item["title"], item["number"])
        print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
