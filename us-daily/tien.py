"""Hai video giải thích tiền mỗi ngày, cắt cảnh theo từng câu.

Mỗi câu là một tranh hoạt hình mới: nhân vật, đồ vật đúng ý câu nói, và dòng chữ lớn.
Nhân vật là hình vẽ riêng. Không chép tranh, mặt, hay logo của kênh khác.
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
INK = (28, 28, 32)
SKIN = (244, 206, 170)
NAVY = (24, 58, 122)
GOLD = (242, 184, 32)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _beats(words, span: float = 6.5) -> list[list[tuple[float, float, str]]]:
    beats: list[list[tuple[float, float, str]]] = []
    current: list[tuple[float, float, str]] = []
    for item in words:
        if current and (item[0] - current[0][0] >= span or current[-1][2].endswith((".", "!", "?"))):
            beats.append(current)
            current = []
        current.append(item)
    if current:
        beats.append(current)
    return beats


def _beat_at(beats, second: float):
    chosen = beats[0]
    for beat in beats:
        if beat[0][0] <= second:
            chosen = beat
        else:
            break
    return chosen


def _scene_name(text: str, index: int, previous: str) -> str:
    low = text.lower()
    order = ("board", "card", "scale", "jars", "calendar", "city", "list", "clock")
    if "minimum" in low or "payment" in low:
        name = "scale"
    elif "card" in low or "apr" in low or "interest" in low or "percent" in low:
        name = "card"
    elif "month" in low:
        name = "calendar"
    elif "year" in low or "years" in low or "ten" in low:
        name = "jars"
    elif "fund" in low or "stock" in low or "index" in low or "company" in low or "market" in low:
        name = "city"
    elif "week" in low or "autopay" in low or "write" in low:
        name = "list"
    elif "promise" in low or "forecast" in low or "advice" in low:
        name = "clock"
    else:
        name = order[index % len(order)]
    if name == previous:
        name = order[(order.index(name) + 1) % len(order)]
    return name


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill) -> None:
    draw.text(xy, text, font=font, fill=fill, anchor="lt")


def _badge(draw: ImageDraw.ImageDraw, font, number: str) -> None:
    width = int(font.getlength(number)) + 48
    x = max(24, (W - width) // 2)
    draw.rounded_rectangle((x, 18, x + width, 92), radius=16, fill=GOLD, outline=INK, width=4)
    _text(draw, (x + 24, 28), number, font, INK)


def _coin(draw: ImageDraw.ImageDraw, x: int, y: int, radius: int = 22) -> None:
    draw.ellipse((x, y, x + radius * 2, y + radius * 2), fill=GOLD, outline=(120, 78, 0), width=4)
    draw.ellipse((x + 7, y + 7, x + radius * 2 - 7, y + radius * 2 - 7), outline=(150, 100, 10), width=3)


def _host(draw: ImageDraw.ImageDraw, x: int, y: int, arm: str) -> None:
    draw.rounded_rectangle((x + 30, y + 168, x + 62, y + 248), radius=8, fill=(32, 40, 72))
    draw.rounded_rectangle((x + 72, y + 168, x + 104, y + 248), radius=8, fill=(32, 40, 72))
    draw.ellipse((x + 22, y + 232, x + 70, y + 258), fill=INK)
    draw.ellipse((x + 66, y + 232, x + 114, y + 258), fill=INK)
    draw.rounded_rectangle((x + 18, y + 78, x + 116, y + 186), radius=18, fill=NAVY, outline=INK, width=4)
    draw.polygon([(x + 60, y + 86), (x + 78, y + 86), (x + 69, y + 138)], fill=(196, 42, 48))
    draw.ellipse((x + 30, y + 6, x + 104, y + 88), fill=SKIN, outline=INK, width=4)
    draw.pieslice((x + 30, y + 2, x + 104, y + 58), 200, 340, fill=INK)
    draw.ellipse((x + 48, y + 38, x + 60, y + 50), fill=INK)
    draw.ellipse((x + 74, y + 38, x + 86, y + 50), fill=INK)
    draw.arc((x + 52, y + 52, x + 84, y + 74), 15, 165, fill=(150, 70, 60), width=3)
    if arm == "point":
        draw.line((x + 112, y + 112, x + 176, y + 86), fill=SKIN, width=12)
        draw.ellipse((x + 164, y + 70, x + 190, y + 98), fill=SKIN, outline=INK, width=3)
    elif arm == "think":
        draw.line((x + 24, y + 112, x + 4, y + 78), fill=SKIN, width=12)
        draw.ellipse((x - 8, y + 58, x + 20, y + 90), fill=SKIN, outline=INK, width=3)
    else:
        draw.line((x + 112, y + 124, x + 158, y + 156), fill=SKIN, width=12)
        draw.ellipse((x + 146, y + 142, x + 174, y + 170), fill=SKIN, outline=INK, width=3)


def _skyline(draw: ImageDraw.ImageDraw, top: int) -> None:
    colors = ((186, 214, 168), (232, 168, 92), (120, 168, 196), (214, 120, 110))
    cursor = 40
    for number, color in enumerate(colors * 4):
        height = 70 + (number * 37) % 150
        width = 54 + (number * 13) % 30
        draw.rectangle((cursor, top + 180 - height, cursor + width, top + 180), fill=color, outline=INK, width=3)
        draw.rectangle((cursor + 10, top + 150 - height, cursor + 24, top + 168 - height), fill=(255, 236, 160))
        cursor += width + 8
        if cursor > 1180:
            break


def _caption(draw: ImageDraw.ImageDraw, font, text: str) -> None:
    draw.rounded_rectangle((70, 560, 1210, 690), radius=16, fill=(16, 16, 18))
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if font.getlength(trial) > 1060 and current:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    lines = lines[:2]
    for row, line in enumerate(lines):
        _text(draw, (96, 578 + row * 48), line, font, (255, 255, 255))


def _scene_board(draw, fonts, number: str) -> None:
    draw.rectangle((0, 0, W, 430), fill=(176, 214, 242))
    draw.rectangle((0, 430, W, H), fill=(214, 196, 160))
    draw.rounded_rectangle((430, 70, 1180, 430), radius=18, fill=(248, 248, 244), outline=INK, width=6)
    draw.rectangle((500, 40, 560, 78), fill=(180, 70, 60))
    _text(draw, (500, 150), number, fonts["number"], (186, 48, 36))
    _host(draw, 80, 150, "point")
    for index in range(5):
        _coin(draw, 470 + index * 70, 360, 18)


def _scene_card(draw, fonts, number: str) -> None:
    draw.rectangle((0, 0, W, 470), fill=(255, 228, 196))
    draw.rectangle((0, 470, W, H), fill=(232, 196, 150))
    draw.rounded_rectangle((430, 80, 980, 390), radius=28, fill=(36, 92, 176), outline=INK, width=6)
    draw.rounded_rectangle((470, 120, 560, 180), radius=10, fill=GOLD)
    draw.rectangle((430, 230, 980, 280), fill=INK)
    _text(draw, (470, 300), number, fonts["mid"], (255, 255, 255))
    _badge(draw, fonts["mid"], number)
    for index in range(4):
        _coin(draw, 1000, 160 + index * 70, 20)
    _host(draw, 70, 160, "point")


def _scene_scale(draw, fonts, number: str) -> None:
    draw.rectangle((0, 0, W, H), fill=(232, 236, 214))
    draw.rectangle((620, 120, 660, 250), fill=(70, 70, 76))
    draw.polygon([(300, 250), (980, 250), (940, 290), (340, 290)], fill=(90, 90, 96))
    draw.rounded_rectangle((300, 300, 520, 470), radius=18, fill=(196, 52, 48), outline=INK, width=4)
    draw.rounded_rectangle((820, 360, 1040, 470), radius=18, fill=(48, 150, 86), outline=INK, width=4)
    _text(draw, (340, 360), "interest", fonts["small"], (255, 255, 255))
    _text(draw, (860, 390), "paid down", fonts["small"], (255, 255, 255))
    _badge(draw, fonts["mid"], number)
    _host(draw, 140, 180, "think")


def _scene_jars(draw, fonts, number: str, index: int) -> None:
    draw.rectangle((0, 0, W, 400), fill=(255, 236, 186))
    draw.rectangle((0, 400, W, H), fill=(120, 170, 96))
    active = index % 6
    for jar in range(6):
        x = 360 + jar * 140
        draw.rounded_rectangle((x, 250, x + 90, 470), radius=16, fill=(186, 220, 236), outline=INK, width=4)
        fill_top = 430 - (jar + 1) * 22
        draw.rectangle((x + 8, fill_top, x + 82, 462), fill=GOLD)
        if jar == active:
            _coin(draw, x + 20, 180, 22)
    _badge(draw, fonts["mid"], number)
    _host(draw, 40, 170, "hold")


def _scene_calendar(draw, fonts, number: str, index: int) -> None:
    draw.rectangle((0, 0, W, H), fill=(255, 248, 236))
    marked = index % 12
    for month in range(12):
        column, row = month % 6, month // 6
        x, y = 360 + column * 140, 80 + row * 180
        fill = (255, 214, 64) if month == marked else (255, 255, 255)
        draw.rounded_rectangle((x, y, x + 120, y + 150), radius=12, fill=fill, outline=INK, width=4)
        draw.rectangle((x, y, x + 120, y + 36), fill=(180, 60, 54))
        _text(draw, (x + 36, y + 70), str(month + 1), fonts["small"], INK)
    _host(draw, 40, 180, "point")
    _badge(draw, fonts["mid"], number)


def _scene_city(draw, fonts, number: str) -> None:
    draw.rectangle((0, 0, W, 250), fill=(150, 206, 236))
    draw.rectangle((0, 250, W, H), fill=(210, 206, 190))
    _skyline(draw, 80)
    draw.rectangle((860, 80, 1120, 430), fill=(70, 110, 160), outline=INK, width=5)
    for window in range(8):
        draw.rectangle((900 + (window % 4) * 48, 120 + (window // 4) * 70, 930 + (window % 4) * 48, 160 + (window // 4) * 70), fill=(255, 230, 140))
    _badge(draw, fonts["mid"], number)
    _host(draw, 80, 180, "think")


def _scene_list(draw, fonts, number: str) -> None:
    draw.rectangle((0, 0, W, H), fill=(236, 228, 210))
    draw.rounded_rectangle((420, 60, 1140, 520), radius=12, fill=(255, 252, 242), outline=INK, width=5)
    for row, done in enumerate((True, True, False)):
        y = 120 + row * 110
        draw.rounded_rectangle((470, y, 540, y + 70), radius=8, outline=INK, width=4, fill=(255, 255, 255))
        if done:
            draw.line((482, y + 36, 504, y + 58), fill=(36, 140, 72), width=8)
            draw.line((504, y + 58, 534, y + 16), fill=(36, 140, 72), width=8)
        draw.rectangle((570, y + 24, 1060, y + 44), fill=(210, 206, 196))
    _badge(draw, fonts["mid"], number)
    _host(draw, 60, 180, "point")


def _scene_clock(draw, fonts, number: str) -> None:
    draw.rectangle((0, 0, W, 430), fill=(126, 186, 224))
    draw.rectangle((0, 430, W, H), fill=(186, 196, 176))
    draw.ellipse((700, 40, 1180, 520), fill=(236, 228, 206), outline=INK, width=8)
    draw.line((940, 280, 940, 120), fill=INK, width=8)
    draw.line((940, 280, 1080, 320), fill=(180, 40, 40), width=8)
    for index in range(5):
        _coin(draw, 760 + index * 40, 80 + (index % 2) * 30, 16)
    _badge(draw, fonts["mid"], number)
    _host(draw, 80, 160, "hold")


def _paint(draw, fonts, scene: str, number: str, index: int) -> None:
    if scene == "card":
        _scene_card(draw, fonts, number)
    elif scene == "scale":
        _scene_scale(draw, fonts, number)
    elif scene == "jars":
        _scene_jars(draw, fonts, number, index)
    elif scene == "calendar":
        _scene_calendar(draw, fonts, number, index)
    elif scene == "city":
        _scene_city(draw, fonts, number)
    elif scene == "list":
        _scene_list(draw, fonts, number)
    elif scene == "clock":
        _scene_clock(draw, fonts, number)
    else:
        _scene_board(draw, fonts, number)


def _frame(draw_mod, beats, scenes, number: str, second: float) -> Image.Image:
    image = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    fonts = {
        "number": draw_mod.ImageFont.truetype(draw_mod.FONT_DISPLAY, 92 if len(number) < 8 else 54),
        "mid": draw_mod.ImageFont.truetype(draw_mod.FONT_DISPLAY, 48),
        "small": draw_mod.ImageFont.truetype(draw_mod.FONT_DISPLAY, 32),
        "caption": draw_mod.ImageFont.truetype(draw_mod.FONT_BOLD, 36),
    }
    beat = _beat_at(beats, second)
    index = beats.index(beat)
    _paint(draw, fonts, scenes[index], number, index)
    spoken = " ".join(token for _start, _end, token in beat)
    _caption(draw, fonts["caption"], spoken)
    return image


def _render(draw_mod, words, audio: Path, dest: Path, number: str) -> None:
    beats = _beats(words)
    scenes: list[str] = []
    previous = ""
    for index, beat in enumerate(beats):
        text = " ".join(token for _start, _end, token in beat)
        previous = _scene_name(text, index, previous)
        scenes.append(previous)
    print(f"{len(beats)} canh")
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
        stderr=subprocess.DEVNULL,
    )
    assert proc.stdin is not None
    for frame in range(frames):
        image = _frame(draw_mod, beats, scenes, number, frame / FPS)
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
    shot = "A new cartoon scene every sentence: a host, the object in that sentence, and a large caption. Original drawings only."
    for index, item in enumerate(run.finance_pair(when), start=1):
        if args.index and index != args.index:
            continue
        print(item["title"], item["words"])
        text = run._package("finance", item["spoken"], item["title"], [item["source"]], shot)
        (folder / f"finance-{index}.txt").write_text(text, encoding="utf-8")
        audio = folder / f"tai-chinh-{index}.mp3"
        words = asyncio.run(run._speak_timed(item["spoken"], audio))
        dest = folder / f"tai-chinh-{index}.mp4"
        _render(draw_mod, words, audio, dest, item["number"])
        print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
