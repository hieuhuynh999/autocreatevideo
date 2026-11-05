"""Vẽ lại bản tin: ảnh đúng bài, bàn tay cầm bút vẽ mô hình đúng từ đang nói.

Chạy từ thư mục project, sau khi us-daily/run.py đã có file trong output/us-daily/ngày.
"""

from __future__ import annotations

import os
import re
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DAY = ROOT / "output" / "us-daily"
STATIC = ROOT / "us-daily" / "static"
PORTRAIT_URLS = {
    "trump.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/Official_Presidential_Portrait_of_President_Donald_J._Trump_%282025%29.jpg/960px-Official_Presidential_Portrait_of_President_Donald_J._Trump_%282025%29.jpg",
    "capitol.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/United_States_Capitol_west_front_edit2.jpg/960px-United_States_Capitol_west_front_edit2.jpg",
}
FFMPEG = Path(
    r"C:\Users\henry.hieu\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
)
W, H = 1280, 720
FPS = 24
PAPER = (244, 241, 234)
INK = (28, 28, 28)
PEN = (180, 55, 28)
BIG = (176, 32, 24)
SMALL = (40, 40, 40)
BAR = (22, 22, 22)
FONT_BIG = ImageFont.truetype(r"C:\Windows\Fonts\impact.ttf", 92)
FONT_MID = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 34)
FONT_SMALL = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 28)
FONT_BUG = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 26)

# Biểu tượng gốc, không vẽ mặt người.
SCENES: dict[str, list[list[tuple[int, int]]]] = {
    "intro": [
        [(180, 360), (1100, 360)],
        [(240, 250), (240, 470)],
        [(430, 220), (430, 500)],
        [(620, 280), (620, 440)],
        [(810, 200), (810, 520)],
        [(1000, 260), (1000, 460)],
    ],
    "00": [
        [(200, 470), (200, 250), (340, 250), (340, 470)],
        [(390, 470), (390, 190), (560, 190), (560, 470)],
        [(390, 190), (430, 140), (475, 115), (520, 140), (560, 190)],
        [(610, 470), (610, 250), (750, 250), (750, 470)],
        [(170, 470), (790, 470)],
    ],
    "01": [
        [(220, 180), (220, 480), (860, 480)],
        [(260, 210), (380, 250), (500, 230), (640, 360), (820, 450)],
    ],
    "02": [
        [(260, 300), (260, 470), (620, 470), (620, 300)],
        [(260, 300), (300, 250), (440, 210), (580, 250), (620, 300)],
        [(700, 420), (760, 300), (820, 420), (880, 280), (940, 420)],
    ],
    "03": [
        [(180, 420), (280, 300), (400, 390), (540, 230), (700, 360), (860, 200), (1040, 340)],
        [(300, 470), (300, 390)],
        [(560, 470), (560, 300)],
        [(820, 470), (820, 250)],
    ],
    "04": [
        [(240, 180), (240, 470)],
        [(250, 330), (520, 330)],
        [(530, 180), (700, 470)],
        [(760, 180), (760, 470)],
        [(770, 330), (1040, 330)],
    ],
    "05": [
        [(300, 160), (300, 470), (430, 470), (430, 160)],
        [(560, 160), (560, 470), (820, 470), (820, 160)],
    ],
    "end": [
        [(640, 180), (640, 300)],
        [(560, 260), (640, 180), (720, 260)],
        [(360, 420), (920, 420)],
    ],
}
LABELS = {
    "intro": "SIX STORIES",
    "00": "BOTH CHAMBERS",
    "01": "THE COLLAPSE",
    "02": "THE VATICAN",
    "03": "BLUE WAVE",
    "04": "IRAN WAR",
    "05": "10 YEARS",
    "end": "ONE SENTENCE",
}
HOT = {
    "democrats", "congress", "chambers", "trump", "collapse", "iran",
    "war", "years", "vatican", "dylan", "majorities", "wave", "washington",
    "rebuke", "sentence",
}


def _clock(text: str) -> float:
    hours, minutes, seconds = text.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _cues(path: Path) -> list[tuple[float, float, list[tuple[float, float, str]]]]:
    cues = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(",", 9)
        style = parts[3]
        if style not in {"Hook", "Caption"}:
            continue
        start = _clock(parts[1])
        found = re.findall(r"\\kf(\d+)\}([^{]+)", parts[9])
        words = []
        cursor = start
        for centiseconds, token in found:
            token = token.strip()
            if not token:
                continue
            duration = int(centiseconds) / 100
            words.append((cursor, cursor + duration, token))
            cursor += duration
        if words:
            cues.append((words[0][0], words[-1][1], words))
    return cues


def _length(lines: list[list[tuple[int, int]]]) -> float:
    total = 0.0
    for line in lines:
        for start, end in zip(line, line[1:]):
            total += ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
    return max(total, 1.0)


def _draw_ink(draw: ImageDraw.ImageDraw, lines: list[list[tuple[int, int]]], budget: float) -> tuple[int, int] | None:
    pen = None
    left = budget
    for line in lines:
        for start, end in zip(line, line[1:]):
            span = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
            if left <= 0:
                return pen
            if left >= span:
                draw.line([start, end], fill=INK, width=7)
                left -= span
                pen = end
            else:
                ratio = left / span
                point = (start[0] + (end[0] - start[0]) * ratio, start[1] + (end[1] - start[1]) * ratio)
                draw.line([start, point], fill=INK, width=7)
                return (int(point[0]), int(point[1]))
    return pen


def _active(cues, second: float) -> tuple[list[tuple[float, float, str]], int]:
    for _start, _end, words in cues:
        if words[0][0] - 0.05 <= second <= words[-1][1] + 0.2:
            index = 0
            for number, (start, end, _word) in enumerate(words):
                if start <= second < end + 0.04:
                    index = number
            return words, index
    return [], 0


POSTERS = {
    "intro": ((92, 26, 168), "THURSDAY", "ONE LINE", "MATTERS", (255, 214, 40)),
    "00": ((16, 58, 150), "DEMOCRATS", "TOOK", "BOTH", (255, 214, 40)),
    "01": ((150, 22, 28), "TRUMP'S", "TEAM", "COLLAPSED", (255, 255, 255)),
    "02": ((18, 18, 22), "DYLAN", "MEETS", "THE POPE", (255, 196, 40)),
    "03": ((12, 86, 176), "AFTER THE", "BLUE", "WAVE", (120, 230, 255)),
    "04": ((120, 36, 18), "VANCE", "BLAMES", "IRAN", (255, 214, 40)),
    "05": ((24, 24, 28), "HONG KONG", "SENTENCE", "10 YEARS", (255, 214, 40)),
    "end": ((92, 26, 168), "REMEMBER", "ONE", "SENTENCE", (255, 214, 40)),
}
OUTLET = {
    "intro": "U.S. BRIEFING",
    "00": "PBS NEWSHOUR",
    "01": "NEW YORK TIMES",
    "02": "NPR",
    "03": "PBS NEWSHOUR",
    "04": "NEW YORK TIMES",
    "05": "NPR",
    "end": "U.S. BRIEFING",
}
INK_COLOR = (255, 214, 40)
SKIN = (235, 201, 170)
OX, OY = 128, 408
DRAW_SPEED = 210.0
# Mỗi mô hình là các nét bút liên tiếp. Ô cửa sổ là nét khép, không phải khối hiện sẵn.
MODELS: dict[str, list[list[tuple[int, int]]]] = {
    "building": [
        [(24, 86), (24, 196), (196, 196), (196, 86), (24, 86)],
        [(10, 86), (110, 22), (210, 86)],
        [(46, 108), (46, 142), (78, 142), (78, 108), (46, 108)],
        [(96, 108), (96, 142), (128, 142), (128, 108), (96, 108)],
        [(146, 108), (146, 142), (178, 142), (178, 108), (146, 108)],
        [(96, 156), (96, 196), (132, 196), (132, 156)],
    ],
    "dollar": [
        [(118, 18), (118, 198)],
        [(156, 42), (124, 36), (78, 58), (68, 96), (96, 118), (148, 142), (160, 172), (132, 196), (78, 188)],
    ],
    "chart": [
        [(18, 24), (18, 196), (230, 196)],
        [(36, 36), (214, 176)],
    ],
    "door": [
        [(48, 24), (48, 200), (176, 200), (176, 24), (48, 24)],
        [(148, 108), (160, 108), (160, 122), (148, 122), (148, 108)],
    ],
    "ten": [
        [(36, 28), (36, 188)],
        [(36, 28), (92, 28)],
        [(124, 28), (210, 28), (210, 100), (124, 100), (124, 188), (210, 188)],
    ],
}


def _cover(src: Image.Image, width: int, height: int) -> Image.Image:
    scale = max(width / src.width, height / src.height)
    resized = src.resize((int(src.width * scale), int(src.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - width) // 2
    top = max(0, (resized.height - height) // 5)
    return resized.crop((left, top, left + width, top + height))


def _full(path: Path) -> Image.Image:
    return _cover(Image.open(path).convert("RGB"), W, H)


def _shade() -> Image.Image:
    row = Image.new("L", (W, 1), 0)
    pix = row.load()
    for x in range(760):
        pix[x, 0] = int(188 * (1 - x / 760) ** 1.35)
    return row.resize((W, H))


PHOTOS: dict[str, Image.Image] = {}
DEFAULT_PHOTO: dict[str, str] = {}
SHADE = _shade()
BLACK = Image.new("RGBA", (W, H), (0, 0, 0, 255))
BLACK.putalpha(SHADE)


def _prepare() -> None:
    global DAY, PHOTOS, DEFAULT_PHOTO
    name = os.environ.get("US_DAILY_DAY") or datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    DAY = ROOT / "output" / "us-daily" / name / "anh"
    DAY.mkdir(parents=True, exist_ok=True)
    STATIC.mkdir(parents=True, exist_ok=True)
    for filename, url in PORTRAIT_URLS.items():
        dest = DAY / filename
        cached = STATIC / filename
        if not dest.exists() or dest.stat().st_size < 1000:
            if cached.exists() and cached.stat().st_size > 1000:
                dest.write_bytes(cached.read_bytes())
            else:
                request = urllib.request.Request(url, headers={"User-Agent": "us-daily/1.0 (local briefing)"})
                payload = urllib.request.urlopen(request, timeout=40).read()
                cached.write_bytes(payload)
                dest.write_bytes(payload)
    PHOTOS = {
        "trump": _full(DAY / "trump.jpg"),
        "capitol": _full(DAY / "capitol.jpg"),
    }
    DEFAULT_PHOTO = {}
    for image in sorted(DAY.glob("[0-9][0-9].img")):
        PHOTOS[image.stem] = _full(image)
        DEFAULT_PHOTO[image.stem] = image.stem
    lead = "00" if "00" in PHOTOS else "capitol"
    DEFAULT_PHOTO["intro"] = lead
    DEFAULT_PHOTO["end"] = lead


def _clip_names() -> list[str]:
    names = ["intro"] if (DAY / "intro.mp3").exists() and (DAY / "intro.ass").exists() else []
    stories = sorted(path.stem for path in DAY.glob("[0-9][0-9].mp3") if (DAY / f"{path.stem}.ass").exists())
    names.extend(stories)
    if (DAY / "end.mp3").exists() and (DAY / "end.ass").exists():
        names.append("end")
    return names


def _clean(token: str) -> str:
    return token.strip(" .,!?;:\"“”'’").lower()


def _parts(token: str) -> set[str]:
    return set(re.split(r"[\s/-]+", _clean(token)))


def _kind(token: str) -> str | None:
    parts = _parts(token)
    if parts & {"money", "dollar", "dollars", "economy", "economic"}:
        return "dollar"
    if parts & {"congress", "chambers", "washington", "house", "majorities", "capitol"}:
        return "building"
    if parts & {"collapse", "collapsed", "war", "losses"}:
        return "chart"
    if parts & {"door", "vatican", "pope", "popes"} or _clean(token).startswith("pope"):
        return "door"
    if parts & {"10", "years", "prison"}:
        return "ten"
    return None


def _photo_key(token: str) -> str | None:
    parts = _parts(token)
    word = _clean(token)
    if parts & {"trump", "president"} or word.startswith("trump"):
        return "trump"
    if parts & {"congress", "chambers", "washington", "house"}:
        return "capitol"
    return None


def _events(cues) -> list[tuple[float, float, str, str | None, str | None]]:
    events = []
    for _start, _end, words in cues:
        for start, end, token in words:
            events.append((start, end, token, _kind(token), _photo_key(token)))
    return events


def _fit(draw: ImageDraw.ImageDraw, text: str, start: int) -> ImageFont.FreeTypeFont:
    size = start
    while size > 42:
        font = ImageFont.truetype(r"C:\Windows\Fonts\impact.ttf", size)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= 760:
            return font
        size -= 4
    return ImageFont.truetype(r"C:\Windows\Fonts\impact.ttf", 42)


def _trace(draw: ImageDraw.ImageDraw, lines: list[list[tuple[int, int]]], budget: float) -> tuple[tuple[float, float], tuple[float, float], bool]:
    pen = (lines[0][0][0] + OX, lines[0][0][1] + OY)
    direction = (0.25, 0.85)
    left = budget
    if left <= 0:
        return pen, direction, False
    for line in lines:
        for start, end in zip(line, line[1:]):
            ax, ay = start[0] + OX, start[1] + OY
            bx, by = end[0] + OX, end[1] + OY
            dx, dy = bx - ax, by - ay
            span = (dx * dx + dy * dy) ** 0.5 or 1.0
            direction = (dx / span, dy / span)
            if left >= span:
                draw.line([(ax, ay), (bx, by)], fill=INK_COLOR, width=7)
                left -= span
                pen = (bx, by)
            else:
                point = (ax + dx * (left / span), ay + dy * (left / span))
                draw.line([(ax, ay), point], fill=INK_COLOR, width=7)
                return point, direction, False
    return pen, direction, True


def _hand(draw: ImageDraw.ImageDraw, tip: tuple[float, float], direction: tuple[float, float], done: bool) -> None:
    if done:
        return
    ux, uy = direction
    nx, ny = -uy, ux
    grip = (tip[0] - ux * 58 + nx * 6, tip[1] - uy * 58 + ny * 6)
    draw.line([grip, tip], fill=(32, 32, 36), width=8)
    nib_a = (tip[0] - ux * 12 + nx * 6, tip[1] - uy * 12 + ny * 6)
    nib_b = (tip[0] - ux * 12 - nx * 6, tip[1] - uy * 12 - ny * 6)
    draw.polygon([tip, nib_a, nib_b], fill=(18, 18, 18))
    palm = (grip[0] - ux * 18, grip[1] - uy * 18)
    draw.ellipse((palm[0] - 26, palm[1] - 18, palm[0] + 28, palm[1] + 20), fill=SKIN, outline=(96, 64, 42))
    for finger in range(4):
        along = 10 + finger * 11
        fx = grip[0] - ux * 4 + nx * (along - 22)
        fy = grip[1] - uy * 4 + ny * (along - 22)
        draw.rounded_rectangle((fx - 6, fy - 14, fx + 7, fy + 12), radius=4, fill=(222, 184, 152), outline=(96, 64, 42))
    thumb = (grip[0] + nx * 16 - ux * 8, grip[1] + ny * 16 - uy * 8)
    draw.ellipse((thumb[0] - 9, thumb[1] - 7, thumb[0] + 12, thumb[1] + 11), fill=(210, 170, 140), outline=(96, 64, 42))


def _spoken(events, second: float) -> tuple[str, str | None, float | None, str]:
    token = ""
    kind = None
    started = None
    photo = None
    photo_until = -1.0
    for start, end, word, word_kind, word_photo in events:
        if start > second:
            break
        if start <= second < end + 0.08:
            token = word
        if word_kind and word_kind != kind:
            kind = word_kind
            started = start
        if word_photo and start <= second:
            photo = word_photo
            photo_until = end + 2.4
    if photo is None or second > photo_until:
        photo = None
    return token, kind, started, photo or ""


def _frame(name: str, second: float, duration: float, cues) -> Image.Image:
    _bg, top, mid, key, key_color = POSTERS.get(name, ((18, 18, 22), "U.S.", "STORY", name, (255, 214, 40)))
    events = _events(cues)
    token, kind, started, photo_key = _spoken(events, second)
    photo_name = photo_key or DEFAULT_PHOTO.get(name, "capitol")
    if photo_name not in PHOTOS:
        photo_name = "capitol"
    image = PHOTOS[photo_name].copy()
    image = image.convert("RGBA")
    image.alpha_composite(BLACK)
    draw = ImageDraw.Draw(image)
    if kind and started is not None and second >= started:
        draw.rounded_rectangle((78, 392, 390, 628), radius=16, fill=(8, 12, 22))
        tip, direction, done = _trace(draw, MODELS[kind], (second - started) * DRAW_SPEED)
        _hand(draw, tip, direction, done)
    y = 28
    for text, color, start in ((top, (255, 255, 255), 52), (mid, (255, 255, 255), 60), (key, key_color, 78)):
        font = _fit(draw, text, start)
        draw.text((32, y), text, font=font, fill=color, stroke_width=3, stroke_fill=(0, 0, 0))
        box = draw.textbbox((32, y), text, font=font)
        y = box[3] - 4
    draw.text((860, 28), OUTLET.get(name, "U.S. BRIEFING"), font=FONT_BUG, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    draw.rectangle((0, 640, W, H), fill=(0, 0, 0, 255))
    if token:
        hot = _clean(token) in HOT or kind is not None
        draw.text((32, 652), token, font=FONT_MID, fill=key_color if hot else (255, 255, 255))
    return image.convert("RGB")


def _duration(path: Path) -> float:
    proc = subprocess.run([str(FFMPEG), "-i", str(path)], capture_output=True, text=True)
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
    if not match:
        raise RuntimeError(path.name)
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _clip(name: str) -> Path:
    audio = DAY / f"{name}.mp3"
    cues = _cues(DAY / f"{name}.ass")
    duration = _duration(audio)
    frames = int(duration * FPS)
    out = DAY / f"{name}-but.mp4"
    proc = subprocess.Popen(
        [
            str(FFMPEG), "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
            "-i", "-",
            "-i", str(audio),
            "-shortest",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k", "-ar", "24000", "-ac", "1",
            "-movflags", "+faststart",
            str(out),
        ],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None
    for frame in range(frames):
        image = _frame(name, frame / FPS, duration, cues)
        proc.stdin.write(image.tobytes())
    proc.stdin.close()
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"{name} ffmpeg {code}")
    return out


def _count_color(image: Image.Image, rgb: tuple[int, int, int], box: tuple[int, int, int, int], tol: int = 28) -> int:
    count = 0
    for pixel in image.crop(box).getdata():
        if all(abs(channel - target) <= tol for channel, target in zip(pixel, rgb)):
            count += 1
    return count


def _patch_diff(left: Image.Image, right: Image.Image, box: tuple[int, int, int, int]) -> int:
    total = 0
    for a, b in zip(left.crop(box).getdata(), right.crop(box).getdata()):
        total += sum(abs(channel - other) for channel, other in zip(a, b))
    return total


def _qa_stills() -> list[str]:
    """So ảnh với từ đang nói. Trả về danh sách lỗi, không chặn file video."""
    _prepare()
    folder = DAY / "qa"
    folder.mkdir(exist_ok=True)
    failed: list[str] = []
    if "end" not in _clip_names():
        return ["thieu clip ket"]
    end_cues = _cues(DAY / "end.ass")
    end_dur = _duration(DAY / "end.mp3")
    ending = _frame("end", max(0.0, end_dur - 0.15), end_dur, end_cues)
    ending.save(folder / "ending.jpg", quality=90)
    end_key = DEFAULT_PHOTO.get("end", "capitol")
    if ending.getpixel((1000, 300)) != PHOTOS[end_key].getpixel((1000, 300)):
        failed.append("cuoi video mat anh")
    if "00" not in _clip_names():
        print("QA-MAY", "khong co tin 00")
        return failed
    cues = _cues(DAY / "00.ass")
    events = _events(cues)
    duration = _duration(DAY / "00.mp3")
    trump_at = next((start for start, _end, _token, _kind, photo in events if photo == "trump"), None)
    draw_at = next((start for start, _end, _token, kind, _photo in events if kind), None)
    if trump_at is not None and trump_at + 0.2 < duration:
        face = (860, 80, 1120, 420)
        trump_on = _frame("00", trump_at + 0.12, duration, cues)
        trump_on.save(folder / "trump.jpg", quality=90)
        own = DEFAULT_PHOTO.get("00", "capitol")
        if _patch_diff(trump_on, PHOTOS["trump"], face) >= _patch_diff(trump_on, PHOTOS[own], face):
            failed.append("luc noi Trump khong phai chan dung")
    if draw_at is not None and draw_at + 1.3 < duration:
        before = _frame("00", max(0.05, draw_at - 0.35), duration, cues)
        started = _frame("00", draw_at + 0.45, duration, cues)
        later = _frame("00", draw_at + 1.15, duration, cues)
        before.save(folder / "pen-start.jpg", quality=90)
        later.save(folder / "pen-mid.jpg", quality=90)
        sketch = (78, 392, 390, 628)
        ink_before = _count_color(before, INK_COLOR, sketch)
        ink_start = _count_color(started, INK_COLOR, sketch)
        ink_later = _count_color(later, INK_COLOR, sketch)
        skin = _count_color(later, SKIN, (0, 300, 520, 680), tol=36)
        if draw_at > 0.5 and ink_before > 80:
            failed.append("net ve xuat hien truoc tu khoa")
        if ink_start < 30 or skin < 80 or ink_later <= ink_start:
            failed.append("tay khong ve tiep net")
    print("QA-MAY", "dat" if not failed else "; ".join(failed))
    return failed


def main() -> None:
    _prepare()
    notes = _qa_stills()
    if notes:
        (DAY / "qa-loi.txt").write_text("\n".join(notes) + "\n", encoding="utf-8")
    names = _clip_names()
    if not names:
        raise RuntimeError(f"Khong co mp3 trong {DAY}")
    clips = [_clip(name) for name in names]
    listing = DAY / "but-list.txt"
    listing.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
    out = DAY.parent / "vi-du-but.mp4"
    proc = subprocess.run(
        [
            str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
            "-c", "copy", "-movflags", "+faststart", str(out),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-400:])
    print(out)


if __name__ == "__main__":
    main()
