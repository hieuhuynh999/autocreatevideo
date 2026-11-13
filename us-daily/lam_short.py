"""Dựng hai Short dọc 1080x1920 mỗi ngày: tin Mỹ lúc 8:00 và tiền bạc lúc 16:00 giờ New York.

Không cắt từ video dài. Mỗi Short có lời riêng, dưới 58 giây.

Vùng chữ trên điện thoại:
- 230 px trên cùng bị thanh tìm kiếm của YouTube che.
- Từ 1500 px trở xuống là tên kênh, tiêu đề và nút đăng ký.
- Từ 850 px trở xuống, 180 px bên phải là cột nút thích, bình luận, chia sẻ.
Mọi chữ phải nằm trong TOP_ZONE hoặc LOW_ZONE. Mỗi khung chữ được ghi vào
short-*.layout.json để kiem_dinh.py đo lại.

    python us-daily/lam_short.py [--day YYYY-MM-DD] [--only tin|tien]
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import wave
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "us-daily"
NY = ZoneInfo("America/New_York")
W, H, FPS = 1080, 1920, 30
TOP_ZONE = (60, 230, 1020, 850)
LOW_ZONE = (60, 850, 900, 1500)
CAPTION_BOX = (60, 1190, 900, 1480)
CAPTION_MAX, CAPTION_MIN = 84, 56
MAX_SECONDS = 58.0
FADE = 0.18
GAP = 0.12
TAIL = 0.45

WHITE = (255, 255, 255)
YELLOW = (255, 212, 0)
RED = (204, 32, 39)
NAVY = (12, 26, 56)
GOLD = (246, 192, 44)
GREY = (200, 206, 216)
INK = (10, 10, 14)

FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
FACES = {
    "black": ("seguibl.ttf", "ariblk.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"),
    "bold": ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"),
    "text": ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"),
}
_fonts: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def _load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    key = (kind, size)
    if key not in _fonts:
        for name in FACES[kind]:
            for folder in (FONT_DIR, Path("/usr/share/fonts/truetype/dejavu")):
                if (folder / name).exists():
                    _fonts[key] = ImageFont.truetype(str(folder / name), size)
                    break
            if key in _fonts:
                break
        else:
            _fonts[key] = ImageFont.load_default(size)
    return _fonts[key]


def _ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def inside_safe(box) -> bool:
    x0, y0, x1, y1 = box
    if x0 < TOP_ZONE[0] or y0 < TOP_ZONE[1] or y1 > LOW_ZONE[3]:
        return False
    if y1 <= TOP_ZONE[3]:
        return x1 <= TOP_ZONE[2]
    return x1 <= LOW_ZONE[2]


class Layout:
    """Ghi lại mọi khung chữ đã vẽ, để đo vùng an toàn và cỡ chữ."""

    def __init__(self) -> None:
        self.items: dict[tuple, dict] = {}
        self.warnings: list[str] = []

    def add(self, kind: str, text: str, size: int, box) -> None:
        box = [int(round(value)) for value in box]
        key = (kind, text, size)
        if key in self.items:
            old = self.items[key]["box"]
            box = [min(old[0], box[0]), min(old[1], box[1]), max(old[2], box[2]), max(old[3], box[3])]
        self.items[key] = {"kind": kind, "text": text, "size": size, "box": box}

    def warn(self, text: str) -> None:
        if text not in self.warnings:
            self.warnings.append(text)

    def dump(self, path: Path, extra: dict) -> None:
        items = list(self.items.values())
        outside = [item for item in items if not inside_safe(item["box"])]
        data = {
            "size": [W, H],
            "top_zone": TOP_ZONE,
            "low_zone": LOW_ZONE,
            "caption_min": CAPTION_MIN,
            "elements": items,
            "outside": outside,
            "warnings": self.warnings,
            **extra,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _width(text: str, face: ImageFont.FreeTypeFont, stroke: int = 0) -> int:
    box = face.getbbox(text, stroke_width=stroke)
    return box[2] - box[0]


def _wrap(text: str, face: ImageFont.FreeTypeFont, width: int, stroke: int = 0) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if current and _width(trial, face, stroke) > width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def fit(text: str, kind: str, largest: int, smallest: int, width: int, max_lines: int, stroke: int = 0, layout: Layout | None = None):
    for size in range(largest, smallest - 1, -2):
        face = font(kind, size)
        lines = _wrap(text, face, width, stroke)
        if len(lines) <= max_lines and all(_width(line, face, stroke) <= width for line in lines):
            return face, lines
    face = font(kind, smallest)
    lines = _wrap(text, face, width, stroke)
    if len(lines) > max_lines:
        kept = lines[:max_lines]
        while kept[-1] and _width(kept[-1] + "…", face, stroke) > width:
            kept[-1] = kept[-1].rsplit(" ", 1)[0] if " " in kept[-1] else kept[-1][:-1]
        kept[-1] += "…"
        lines = kept
        if layout:
            layout.warn(f"chữ bị rút gọn: {text[:60]}")
    return face, lines


def block(draw, lines, face, x, y, layout: Layout, kind: str, fill=WHITE, stroke=0, stroke_fill=INK, align="left", spacing=1.12, right=None):
    size = face.size
    for line in lines:
        width = _width(line, face, stroke)
        # Mép mực của chữ (gồm viền) nằm đúng tại x, không lấn ra lề.
        ink = face.getbbox(line, stroke_width=stroke)[0]
        if align == "center":
            left = x - width / 2 - ink
        elif align == "right":
            left = right - width - ink
        else:
            left = x - ink
        draw.text((left, y), line, font=face, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        box = draw.textbbox((left, y), line, font=face, stroke_width=stroke)
        layout.add(kind, line, size, box)
        y += size * spacing
    return y


def pill(draw, text, face, x, y, fill, color, layout: Layout, kind: str, right: int | None = None, pad=(22, 10)):
    width = _width(text, face)
    height = face.size + pad[1] * 2
    left = right - width - pad[0] * 2 if right is not None else x
    draw.rounded_rectangle((left, y, left + width + pad[0] * 2, y + height), radius=height // 2, fill=fill)
    top = y + pad[1] - face.getbbox(text)[1] + (face.size - (face.getbbox(text)[3] - face.getbbox(text)[1])) / 2
    draw.text((left + pad[0], top), text, font=face, fill=color)
    layout.add(kind, text, face.size, (left, y, left + width + pad[0] * 2, y + height))
    return left


def _ease(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3 - 2 * value)


def _cover(image: Image.Image, width: int, height: int) -> Image.Image:
    scale = max(width / image.width, height / image.height)
    resized = image.resize((max(width, int(image.width * scale + 0.5)), max(height, int(image.height * scale + 0.5))), Image.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _gradient(height: int, top_alpha: int, bottom_alpha: int) -> Image.Image:
    column = Image.new("L", (1, height))
    for row in range(height):
        share = row / max(1, height - 1)
        column.putpixel((0, row), int(top_alpha + (bottom_alpha - top_alpha) * share))
    return column.resize((W, height))


# ---------- lời đọc ----------

async def _voices(texts: list[str], folder: Path, stem: str) -> list[list[tuple[float, float, str]]]:
    run = _load("run")
    timed = []
    for index, text in enumerate(texts):
        timed.append(await run._speak_timed(text, folder / f"{stem}-{index:02d}.mp3"))
    return timed


def _to_wav(source: Path) -> Path:
    dest = source.with_suffix(".wav")
    proc = subprocess.run(
        [_ffmpeg(), "-y", "-i", str(source), "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(dest)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-400:])
    return dest


def _wav_seconds(path: Path) -> float:
    with wave.open(str(path)) as handle:
        return handle.getnframes() / handle.getframerate()


def speak(texts: list[str], folder: Path, stem: str) -> list[dict]:
    words = asyncio.run(_voices(texts, folder, stem))
    parts = []
    for index, timed in enumerate(words):
        wav = _to_wav(folder / f"{stem}-{index:02d}.mp3")
        parts.append({"wav": wav, "seconds": _wav_seconds(wav), "words": timed})
    return parts


def join_audio(parts: list[dict], dest: Path) -> list[tuple[float, float]]:
    spans = []
    clock = 0.0
    with wave.open(str(dest), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(48000)
        for index, part in enumerate(parts):
            with wave.open(str(part["wav"])) as handle:
                out.writeframes(handle.readframes(handle.getnframes()))
            pause = TAIL if index == len(parts) - 1 else GAP
            out.writeframes(b"\x00\x00" * int(48000 * pause))
            spans.append((clock, clock + part["seconds"] + pause))
            clock += part["seconds"] + pause
    return spans


# ---------- chữ chạy ----------

WEAK = {"the", "a", "an", "of", "to", "and", "in", "on", "for", "with", "at", "by", "as", "your", "his", "her", "its", "their", "is", "are"}

def caption_chunks(parts: list[dict], spans: list[tuple[float, float]]) -> list[dict]:
    chunks: list[dict] = []
    for part, (start, _end) in zip(parts, spans):
        current: list[tuple[float, float, str]] = []
        for word_start, word_end, token in part["words"]:
            word = (start + word_start, start + word_end, token)
            if current:
                text = " ".join(item[2] for item in current + [word])
                gap = word[0] - current[-1][1]
                pause = gap > 0.35 or re.search(r"[.!?,;:]$", current[-1][2])
                if len(current) >= 4 or len(text) > 24 or pause:
                    carry = []
                    while not pause and len(current) > 1 and current[-1][2].lower() in WEAK:
                        carry.insert(0, current.pop())
                    chunks.append({"words": current})
                    current = carry
            current.append(word)
        if current:
            chunks.append({"words": current})
    for index, chunk in enumerate(chunks):
        following = chunks[index + 1]["words"][0][0] if index + 1 < len(chunks) else chunk["words"][-1][1] + 0.4
        chunk["start"] = chunk["words"][0][0]
        chunk["end"] = min(following, chunk["words"][-1][1] + 0.6)
    return chunks


def _caption_layout(chunk: dict, layout: Layout) -> dict:
    if "face" in chunk:
        return chunk
    text = " ".join(item[2] for item in chunk["words"])
    width = CAPTION_BOX[2] - CAPTION_BOX[0]
    stroke = 8
    face, lines = None, None
    for size in range(CAPTION_MAX, CAPTION_MIN - 1, -4):
        trial = font("black", size)
        wrapped = _wrap(text, trial, width, stroke)
        if len(wrapped) <= 2 and all(_width(line, trial, stroke) <= width for line in wrapped):
            face, lines = trial, wrapped
            break
    if face is None:
        face = font("black", CAPTION_MIN)
        lines = _wrap(text, face, width, stroke)
        layout.warn(f"chữ chạy quá dài ở cỡ nhỏ nhất: {text}")
    chunk["face"], chunk["lines"], chunk["stroke"] = face, lines, stroke
    return chunk


def draw_caption(draw, chunks: list[dict], second: float, layout: Layout) -> None:
    active = None
    for chunk in chunks:
        if chunk["start"] <= second < chunk["end"]:
            active = chunk
            break
    if active is None:
        return
    chunk = _caption_layout(active, layout)
    face, lines, stroke = chunk["face"], chunk["lines"], chunk["stroke"]
    line_height = int(face.size * 1.12)
    total = line_height * len(lines)
    middle = (CAPTION_BOX[1] + CAPTION_BOX[3]) / 2
    top = middle - total / 2
    centre = (CAPTION_BOX[0] + CAPTION_BOX[2]) / 2
    current = max((index for index, item in enumerate(chunk["words"]) if item[0] <= second), default=-1)
    position = 0
    for row, line in enumerate(lines):
        width = _width(line, face, stroke)
        x = centre - width / 2 - face.getbbox(line, stroke_width=stroke)[0]
        y = top + row * line_height
        tokens = line.split()
        for place, token in enumerate(tokens):
            color = YELLOW if position == current else WHITE
            position += 1
            prefix = " ".join(tokens[:place]) + (" " if place else "")
            draw.text((x + face.getlength(prefix), y), token, font=face, fill=color, stroke_width=stroke, stroke_fill=INK)
        layout.add("caption", line, face.size, draw.textbbox((x, y), line, font=face, stroke_width=stroke))


def progress(draw, second: float, total: float) -> None:
    left, right, y = LOW_ZONE[0], LOW_ZONE[2], LOW_ZONE[3] - 8
    draw.rounded_rectangle((left, y, right, y + 7), radius=3, fill=(255, 255, 255, 70))
    done = left + (right - left) * min(1.0, second / total)
    draw.rounded_rectangle((left, y, max(left + 7, done), y + 7), radius=3, fill=(255, 255, 255, 230))


# ---------- encode ----------

def encode(frames, audio: Path, dest: Path, seconds: float) -> None:
    command = [
        _ffmpeg(), "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high", "-g", "60",
        "-c:a", "aac", "-b:a", "160k", "-ac", "2",
        "-t", f"{seconds:.2f}", "-movflags", "+faststart",
        str(dest),
    ]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for image in frames:
            proc.stdin.write(image.tobytes())
        proc.stdin.close()
    except BrokenPipeError:
        pass
    error = proc.stderr.read().decode("utf-8", "replace")
    if proc.wait() != 0 or not dest.exists():
        raise RuntimeError(error[-800:])


def contact_sheet(video: Path, dest: Path, seconds: float, marks: list[float]) -> None:
    """Ảnh soát: khung đỏ là vùng YouTube che, khung xanh là vùng chữ."""
    from io import BytesIO

    thumbs = []
    for stamp in marks:
        proc = subprocess.run(
            [_ffmpeg(), "-ss", f"{min(stamp, seconds - 0.1):.2f}", "-i", str(video), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
            capture_output=True,
        )
        if not proc.stdout:
            continue
        frame = Image.open(BytesIO(proc.stdout)).convert("RGB")
        over = ImageDraw.Draw(frame, "RGBA")
        over.rectangle((0, 0, W, TOP_ZONE[1]), fill=(255, 0, 0, 70))
        over.rectangle((0, LOW_ZONE[3], W, H), fill=(255, 0, 0, 70))
        over.rectangle((LOW_ZONE[2], TOP_ZONE[3], W, LOW_ZONE[3]), fill=(255, 0, 0, 70))
        over.rectangle(CAPTION_BOX, outline=(0, 255, 120, 255), width=4)
        thumbs.append(frame.resize((360, 640)))
    if not thumbs:
        return
    sheet = Image.new("RGB", (360 * len(thumbs) + 10 * (len(thumbs) - 1), 640), (30, 30, 30))
    for index, thumb in enumerate(thumbs):
        sheet.paste(thumb, (index * 370, 0))
    sheet.save(dest, quality=88)


# ---------- tin ----------

class Photo:
    def __init__(self, path: Path) -> None:
        image = Image.open(path).convert("RGB")
        ratio = image.width / image.height
        self.full = ratio < 0.8 and image.height >= 900
        if self.full:
            self.region = (0, 0, W, H)
        else:
            self.region = (0, 320, W, 1130)
        width = self.region[2] - self.region[0]
        height = self.region[3] - self.region[1]
        self.big = _cover(image, int(width * 1.12), int(height * 1.12))
        backdrop = _cover(image, W, H).filter(ImageFilter.GaussianBlur(38))
        self.backdrop = ImageEnhance.Brightness(backdrop).enhance(0.36)
        self.low_res = image.width < 640
        self.shade = None
        if self.full:
            shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            shade.paste((0, 0, 0, 255), (0, 0, W, 420), _gradient(420, 170, 0))
            shade.paste((0, 0, 0, 255), (0, 980, W, H), _gradient(H - 980, 0, 215))
            self.shade = shade

    def frame(self, share: float, flip: bool) -> Image.Image:
        width = self.region[2] - self.region[0]
        height = self.region[3] - self.region[1]
        zoom = 1.12 - 0.08 * _ease(share)
        window_w, window_h = width * zoom, height * zoom
        room = self.big.width - window_w
        drift = (share - 0.5) * (1 if flip else -1) * 0.8
        left = room / 2 + room / 2 * drift
        top = (self.big.height - window_h) / 2
        piece = self.big.crop((left, top, left + window_w, top + window_h)).resize((width, height), Image.BILINEAR)
        canvas = (self.backdrop.copy() if not self.full else Image.new("RGB", (W, H)))
        canvas.paste(piece, (self.region[0], self.region[1]))
        if self.shade is not None:
            canvas.paste(self.shade, (0, 0), self.shade)
        return canvas


def _story_words(item: dict) -> tuple[str, str]:
    headline = item["title"].strip().rstrip(".") + "."
    spoken = item["spoken"]
    if spoken.startswith(headline):
        spoken = spoken[len(headline):]
    spoken = re.sub(r"That is [^.]+\.", "", spoken)
    spoken = re.sub(r"[A-Z][A-Za-z ]+ is also reporting this\.", "", spoken)
    brief = " ".join(spoken.split())
    if len(brief.split()) > 30:
        brief = ""
    return headline, brief


def news_parts(when: datetime, folder: Path) -> tuple[list[dict], list[dict]]:
    run = _load("run")
    groups, _errors = run._load_news()
    _text, ready = run.news_script(when, groups, folder)
    stories = []
    for item in ready:
        headline, brief = _story_words(item)
        stories.append({**item, "headline": headline, "brief": brief})
        if len(stories) == 3:
            break
    return stories, ready


def _news_texts(stories: list[dict]) -> list[str]:
    texts = [" ".join(part for part in (story["headline"], story["brief"], f"That is {story['outlet']}.") if part) for story in stories]
    texts.append("That's today's U.S. briefing. Not advice about your vote or your money.")
    return texts


def build_news(when: datetime, folder: Path) -> dict:
    work = folder / "anh"
    work.mkdir(parents=True, exist_ok=True)
    stories, _ready = news_parts(when, folder)
    if len(stories) < 2:
        raise RuntimeError(f"chỉ có {len(stories)} bài có ảnh, cần ít nhất 2")
    while True:
        texts = _news_texts(stories)
        parts = speak(texts, work, "tin")
        seconds = sum(part["seconds"] for part in parts) + GAP * (len(parts) - 1) + TAIL
        if seconds <= MAX_SECONDS:
            break
        longest = max(stories, key=lambda story: len(story["brief"].split()))
        if longest["brief"]:
            longest["brief"] = ""
        elif len(stories) > 2:
            stories.pop()
        else:
            raise RuntimeError(f"bản tin vẫn dài {seconds:.1f}s sau khi rút gọn")
    audio = work / "tin.wav"
    spans = join_audio(parts, audio)
    seconds = spans[-1][1]
    chunks = caption_chunks(parts, spans)
    photos = [Photo(Path(story["image"])) for story in stories]
    layout = Layout()
    day = f"{when.strftime('%b').upper()} {when.day}"
    total = len(stories)
    head = font("bold", 34)
    credit = font("bold", 34)

    def frames():
        previous = None
        last_scene = -1
        for number in range(int(math.ceil(seconds * FPS))):
            second = number / FPS
            scene = next(index for index, span in enumerate(spans) if second < span[1] or index == len(spans) - 1)
            start, end = spans[scene]
            share = (second - start) / max(0.01, end - start)
            if scene < total:
                photo = photos[scene]
                canvas = photo.frame(share, bool(scene % 2))
                draw = ImageDraw.Draw(canvas, "RGBA")
                pill(draw, f"U.S. NEWS · {day}", head, TOP_ZONE[0], 240, RED, WHITE, layout, "header")
                pill(draw, f"{scene + 1}/{total}", head, 0, 240, (0, 0, 0, 170), WHITE, layout, "counter", right=TOP_ZONE[2])
                face, lines = fit(f"PHOTO + STORY: {stories[scene]['outlet'].upper()}", "bold", 34, 26, LOW_ZONE[2] - LOW_ZONE[0], 1, layout=layout)
                block(draw, lines, face, LOW_ZONE[0], 1138, layout, "credit", fill=GREY, stroke=3)
            else:
                canvas = ImageEnhance.Brightness(photos[-1].backdrop).enhance(0.7)
                draw = ImageDraw.Draw(canvas, "RGBA")
                pill(draw, f"U.S. NEWS · {day}", head, TOP_ZONE[0], 240, RED, WHITE, layout, "header")
                face, lines = fit(f"Today's {total} U.S. stories", "black", 96, 64, TOP_ZONE[2] - TOP_ZONE[0], 2, layout=layout)
                y = block(draw, lines, face, TOP_ZONE[0], 400, layout, "end-title", stroke=4)
                outlets = []
                for story in stories:
                    if story["outlet"] not in outlets:
                        outlets.append(story["outlet"])
                face, lines = fit("Sources: " + " · ".join(outlets), "bold", 40, 30, TOP_ZONE[2] - TOP_ZONE[0], 2, layout=layout)
                y = block(draw, lines, face, TOP_ZONE[0], y + 30, layout, "end-sources", fill=GREY)
                face, lines = fit("Follow for tomorrow's briefing", "black", 60, 44, LOW_ZONE[2] - LOW_ZONE[0], 2, layout=layout)
                block(draw, lines, face, LOW_ZONE[0], 900, layout, "end-follow", fill=YELLOW, stroke=4)
            draw_caption(draw, chunks, second, layout)
            progress(draw, second, seconds)
            if scene != last_scene:
                last_scene = scene
                fade_from = previous if scene else None
            if fade_from is not None and second - start < FADE:
                canvas = Image.blend(fade_from, canvas, _ease((second - start) / FADE))
            else:
                previous = canvas
            yield canvas

    dest = folder / "short-tin.mp4"
    encode(frames(), audio, dest, seconds)
    marks = [(start + end) / 2 for start, end in spans]
    contact_sheet(dest, folder / "xem-short-tin.jpg", seconds, marks)
    layout.dump(
        folder / "short-tin.layout.json",
        {
            "seconds": seconds,
            "scenes": [
                {"outlet": story["outlet"], "full_screen": photo.full, "low_res": photo.low_res, "headline": story["headline"]}
                for story, photo in zip(stories, photos)
            ],
        },
    )
    (folder / "short-tin.txt").write_text("\n\n".join(_news_texts(stories)) + "\n", encoding="utf-8")
    return {"file": dest, "seconds": seconds, "stories": stories}


# ---------- tiền ----------

def _split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+(?=[A-Z])", " ".join(text.split()))
    return [piece.strip() for piece in pieces if piece.strip()]


def money_texts(item: dict) -> list[str]:
    lines = [line.strip() for line in item["spoken"].splitlines() if line.strip()]
    fact = lines[0].replace("Here is the number you control.", "").replace("Here is the number.", "").strip()
    fails = next((line for line in lines if re.search(r"\b(fails|breaks)\b", line)), "")
    week = next((line for line in lines if line.startswith("This week")), "")
    texts = _split_sentences(fact)[:2]
    generic = ("this video is", "the source for the rule", "this is not personal financial advice")
    extra = [
        line for line in lines[1:]
        if line not in (fails, week) and not line.lower().startswith(generic) and not line.startswith("This week")
    ]
    if extra and sum(len(text.split()) for text in texts) < 40:
        texts.append(_split_sentences(extra[0])[0])
    if fails:
        texts.append(_split_sentences(fails)[0])
    if week:
        texts.append(_split_sentences(week)[0])
    texts.append("This is not personal financial advice.")
    return texts


FIGURE = re.compile(r"(\$?\d[\d,]*(?:\.\d+)?)(\s*(?:dollars|percent|%))?", re.I)


def _figure(sentence: str, main: str) -> str:
    best = ""
    for number, unit in FIGURE.findall(sentence):
        number = number.rstrip(",")
        if not unit and "$" not in number:
            continue
        unit = (unit or "").strip().lower()
        if unit in ("percent", "%"):
            text = f"{number}%"
        elif unit == "dollars" or number.startswith("$"):
            text = number if number.startswith("$") else f"${number}"
        else:
            text = number
        if text.replace(",", "") != main.replace(",", ""):
            return text
        best = best or text
    return best


ICON_RULES = (
    ("shield", ("not personal financial advice",)),
    ("check", ("this week",)),
    ("warn", ("fails", "breaks", "do not")),
    ("house", ("rent", "mortgage", "home", "house", "down payment", "closing", "lease", "loan")),
    ("card", ("card", "apr", "interest")),
    ("receipt", ("grocer", "bill", "receipt", "utilities", "paycheck")),
    ("jar", ("save", "saving", "emergency", "deposit")),
    ("chart", ("grow", "invest", "index", "market", "return", "fund")),
    ("bank", ("irs", "tax", "limit", "401", "ira", "fica", "social security")),
    ("calendar", ("month", "year", "week", "twelve")),
)
ICON_LABEL = {
    "shield": "NOT ADVICE",
    "check": "THIS WEEK",
    "warn": "WHERE IT FAILS",
    "card": "CREDIT CARD",
    "house": "HOUSING",
    "receipt": "BILLS",
    "jar": "SAVINGS",
    "chart": "GROWTH",
    "bank": "THE RULE",
    "calendar": "THE MATH",
    "coins": "THE NUMBER",
}


def _icon_for(sentence: str) -> str:
    lower = sentence.lower()
    for name, words in ICON_RULES:
        if any(word in lower for word in words):
            return name
    return "coins"


def icon(name: str, size: int = 220) -> Image.Image:
    scale = 4
    big = size * scale
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    u = big / 100
    line = int(5 * u)
    if name == "card":
        draw.rounded_rectangle((8 * u, 24 * u, 92 * u, 78 * u), radius=8 * u, fill=(46, 110, 220))
        draw.rectangle((8 * u, 34 * u, 92 * u, 44 * u), fill=INK)
        draw.rounded_rectangle((16 * u, 54 * u, 34 * u, 66 * u), radius=2 * u, fill=GOLD)
        draw.rectangle((44 * u, 60 * u, 82 * u, 64 * u), fill=WHITE)
    elif name == "house":
        draw.polygon([(50 * u, 10 * u), (92 * u, 46 * u), (8 * u, 46 * u)], fill=(232, 72, 60))
        draw.rectangle((18 * u, 44 * u, 82 * u, 88 * u), fill=WHITE)
        draw.rectangle((42 * u, 60 * u, 58 * u, 88 * u), fill=(120, 76, 40))
        draw.rectangle((24 * u, 52 * u, 36 * u, 64 * u), fill=(120, 190, 255))
        draw.rectangle((64 * u, 52 * u, 76 * u, 64 * u), fill=(120, 190, 255))
    elif name == "receipt":
        points = [(20 * u, 8 * u), (80 * u, 8 * u), (80 * u, 92 * u)]
        for step in range(6):
            points.append((80 * u - step * 10 * u - 5 * u, (86 if step % 2 == 0 else 92) * u))
        points.append((20 * u, 92 * u))
        draw.polygon(points, fill=WHITE)
        for row in range(5):
            draw.rectangle((30 * u, (22 + row * 12) * u, (70 if row < 4 else 52) * u, (26 + row * 12) * u), fill=(90, 90, 100))
        draw.rectangle((56 * u, 70 * u, 72 * u, 76 * u), fill=RED)
    elif name == "jar":
        draw.rounded_rectangle((20 * u, 26 * u, 80 * u, 92 * u), radius=14 * u, fill=(170, 220, 255, 200), outline=WHITE, width=line)
        draw.rectangle((28 * u, 14 * u, 72 * u, 26 * u), fill=(200, 200, 210))
        for row, x in ((0, 34), (0, 54), (1, 44), (2, 34), (2, 56)):
            y = 78 - row * 12
            draw.ellipse((x * u, (y - 5) * u, (x + 16) * u, (y + 5) * u), fill=GOLD, outline=(170, 120, 10), width=int(2 * u))
    elif name == "chart":
        draw.line((10 * u, 90 * u, 90 * u, 90 * u), fill=WHITE, width=line)
        for index, height in enumerate((24, 40, 34, 58, 76)):
            x = 16 + index * 15
            draw.rectangle((x * u, (88 - height) * u, (x + 10) * u, 88 * u), fill=(60, 200, 120))
        draw.line([(18 * u, 60 * u), (38 * u, 46 * u), (52 * u, 52 * u), (70 * u, 30 * u), (88 * u, 12 * u)], fill=GOLD, width=line)
        draw.polygon([(88 * u, 8 * u), (90 * u, 22 * u), (77 * u, 14 * u)], fill=GOLD)
    elif name == "bank":
        draw.polygon([(50 * u, 8 * u), (94 * u, 30 * u), (6 * u, 30 * u)], fill=WHITE)
        for x in (16, 36, 56, 76):
            draw.rectangle((x * u, 36 * u, (x + 8) * u, 76 * u), fill=WHITE)
        draw.rectangle((8 * u, 80 * u, 92 * u, 90 * u), fill=WHITE)
        draw.text((38 * u, 14 * u), "$", font=font("black", int(14 * u)), fill=NAVY)
    elif name == "calendar":
        draw.rounded_rectangle((10 * u, 16 * u, 90 * u, 90 * u), radius=8 * u, fill=WHITE)
        draw.rounded_rectangle((10 * u, 16 * u, 90 * u, 36 * u), radius=8 * u, fill=RED)
        draw.rectangle((10 * u, 28 * u, 90 * u, 36 * u), fill=RED)
        for row in range(3):
            for col in range(4):
                draw.rectangle(((18 + col * 18) * u, (44 + row * 14) * u, (28 + col * 18) * u, (52 + row * 14) * u), fill=(150, 150, 160))
        draw.rectangle((54 * u, 72 * u, 64 * u, 80 * u), fill=GOLD)
    elif name == "warn":
        draw.polygon([(50 * u, 8 * u), (94 * u, 88 * u), (6 * u, 88 * u)], fill=GOLD)
        draw.rectangle((45 * u, 34 * u, 55 * u, 64 * u), fill=INK)
        draw.ellipse((44 * u, 70 * u, 56 * u, 82 * u), fill=INK)
    elif name == "check":
        draw.rounded_rectangle((10 * u, 10 * u, 90 * u, 90 * u), radius=14 * u, fill=(40, 180, 100))
        draw.line([(26 * u, 52 * u), (44 * u, 70 * u), (76 * u, 32 * u)], fill=WHITE, width=int(10 * u), joint="curve")
    elif name == "shield":
        draw.polygon([(50 * u, 6 * u), (88 * u, 20 * u), (82 * u, 62 * u), (50 * u, 94 * u), (18 * u, 62 * u), (12 * u, 20 * u)], fill=(90, 140, 230))
        draw.text((36 * u, 26 * u), "i", font=font("black", int(44 * u)), fill=WHITE)
    else:
        for x, y in ((14, 52), (40, 40), (60, 58)):
            draw.ellipse((x * u, y * u, (x + 30) * u, (y + 30) * u), fill=GOLD, outline=(170, 120, 10), width=int(3 * u))
            draw.text(((x + 9) * u, (y + 2) * u), "$", font=font("black", int(22 * u)), fill=(150, 100, 0))
    return image.resize((size, size), Image.LANCZOS)


def _money_background() -> Image.Image:
    top, bottom = (16, 34, 74), (6, 14, 34)
    column = Image.new("RGB", (1, H))
    for row in range(H):
        share = row / (H - 1)
        column.putpixel((0, row), tuple(int(top[i] + (bottom[i] - top[i]) * share) for i in range(3)))
    canvas = column.resize((W, H))
    draw = ImageDraw.Draw(canvas, "RGBA")
    for x in range(0, W, 90):
        draw.line((x, 0, x, H), fill=(255, 255, 255, 10), width=2)
    for y in range(0, H, 90):
        draw.line((0, y, W, y), fill=(255, 255, 255, 10), width=2)
    return canvas


def _count_up(number: str, share: float) -> str:
    if "/" in number or not re.search(r"\d", number):
        return number
    match = re.search(r"\d[\d,]*(?:\.\d+)?", number)
    raw = match.group(0)
    value = float(raw.replace(",", ""))
    decimals = len(raw.split(".")[1]) if "." in raw else 0
    shown = value * _ease(share)
    text = f"{shown:,.{decimals}f}" if "," in raw else f"{shown:.{decimals}f}"
    return number[: match.start()] + text + number[match.end():]


def build_money(when: datetime, folder: Path) -> dict:
    run = _load("run")
    work = folder / "anh"
    work.mkdir(parents=True, exist_ok=True)
    item = run.finance_one(when)
    texts = money_texts(item)
    while True:
        parts = speak(texts, work, "tien")
        seconds = sum(part["seconds"] for part in parts) + GAP * (len(parts) - 1) + TAIL
        if seconds <= MAX_SECONDS or len(texts) <= 3:
            break
        drop = next((index for index, text in enumerate(texts) if re.search(r"\b(fails|breaks)\b", text)), 1)
        texts.pop(drop)
    if seconds > MAX_SECONDS:
        raise RuntimeError(f"bài tiền dài {seconds:.1f}s")
    audio = work / "tien.wav"
    spans = join_audio(parts, audio)
    seconds = spans[-1][1]
    chunks = caption_chunks(parts, spans)
    layout = Layout()
    background = _money_background()
    main = item["number"]
    icons = [_icon_for(text) for text in texts]
    figures = [_figure(text, main) for text in texts]
    art = {name: icon(name) for name in set(icons)}
    day = f"{when.strftime('%b').upper()} {when.day}"
    head = font("bold", 34)
    title = item["title"]
    source = re.split(r"[.,;]", item["source"])[0].strip()
    number_width = TOP_ZONE[2] - TOP_ZONE[0]
    number_face, _ = fit(main, "black", 200, 90, number_width, 1, stroke=6, layout=layout)
    title_face, title_lines = fit(title, "bold", 50, 36, number_width, 2, layout=layout)
    source_face, source_lines = fit(f"Source: {source}", "text", 34, 26, number_width, 1, layout=layout)

    def frames():
        previous = None
        last_scene = -1
        for number in range(int(math.ceil(seconds * FPS))):
            second = number / FPS
            scene = next(index for index, span in enumerate(spans) if second < span[1] or index == len(spans) - 1)
            start, end = spans[scene]
            local = second - start
            canvas = background.copy()
            draw = ImageDraw.Draw(canvas, "RGBA")
            pill(draw, f"MONEY MATH · {day}", head, TOP_ZONE[0], 240, GOLD, NAVY, layout, "header")
            pill(draw, f"{scene + 1}/{len(texts)}", head, 0, 240, (255, 255, 255, 40), WHITE, layout, "counter", right=TOP_ZONE[2])
            shown = _count_up(main, second / 0.9) if second < 0.9 else main
            y = block(draw, [shown], number_face, TOP_ZONE[0], 330, layout, "number", fill=GOLD, stroke=6, stroke_fill=(60, 40, 0))
            y = block(draw, title_lines, title_face, TOP_ZONE[0], y + 18, layout, "title")
            block(draw, source_lines, source_face, TOP_ZONE[0], y + 10, layout, "source", fill=GREY)
            panel = (LOW_ZONE[0], 880, LOW_ZONE[2], 1160)
            draw.rounded_rectangle(panel, radius=28, fill=(255, 255, 255, 26), outline=(255, 255, 255, 60), width=2)
            pop = 0.7 + 0.3 * _ease(local / 0.25)
            bob = math.sin(second * 2.2) * 6
            glyph = art[icons[scene]]
            size = int(glyph.width * pop)
            glyph_now = glyph.resize((size, size), Image.BILINEAR)
            canvas.paste(glyph_now, (int(panel[0] + 30 + (220 - size) / 2), int(panel[1] + 30 + (220 - size) / 2 + bob)), glyph_now)
            text_left = panel[0] + 280
            text_width = panel[2] - 24 - text_left
            slide = (1 - _ease(local / 0.3)) * 60
            label = ICON_LABEL[icons[scene]]
            label_face, label_lines = fit(label, "bold", 40, 28, text_width, 1, layout=layout)
            block(draw, label_lines, label_face, text_left + slide, panel[1] + 50, layout, "label", fill=GREY)
            if figures[scene]:
                fig_face, fig_lines = fit(figures[scene], "black", 104, 56, text_width, 1, stroke=4, layout=layout)
                block(draw, fig_lines, fig_face, text_left + slide, panel[1] + 110, layout, "figure", fill=YELLOW, stroke=4)
            draw_caption(draw, chunks, second, layout)
            progress(draw, second, seconds)
            if scene != last_scene:
                last_scene = scene
                fade_from = previous if scene else None
            if fade_from is not None and local < FADE:
                canvas = Image.blend(fade_from, canvas, _ease(local / FADE))
            else:
                previous = canvas
            yield canvas

    dest = folder / "short-tien.mp4"
    encode(frames(), audio, dest, seconds)
    marks = [(start + end) / 2 for start, end in spans]
    contact_sheet(dest, folder / "xem-short-tien.jpg", seconds, marks)
    layout.dump(
        folder / "short-tien.layout.json",
        {"seconds": seconds, "scenes": [{"icon": name, "figure": figure, "text": text} for name, figure, text in zip(icons, figures, texts)]},
    )
    (folder / "short-tien.txt").write_text("\n\n".join(texts) + "\n", encoding="utf-8")
    return {"file": dest, "seconds": seconds, "item": item, "texts": texts}


# ---------- tiêu đề và lịch ----------

def write_posts(folder: Path, when: datetime, news: dict | None, money: dict | None) -> None:
    job = _load("job")
    lich = _load("lich")
    times = lich.public_times(when)
    items = []
    blocks = [
        f"Ngày New York: {when.strftime('%Y-%m-%d')}",
        "Hai Short dọc mỗi ngày: tin Mỹ 8:00 và tiền bạc 16:00 giờ miền Đông (20:00 và 04:00 giờ Việt Nam mùa đông).",
        "",
    ]
    if news:
        lead = news["stories"][0]["headline"]
        title = job._title(lead, when, 70) + " #Shorts"
        lines = [lead, "", "In this Short:"]
        for index, story in enumerate(news["stories"], start=1):
            lines.append(f"{index}. {story['outlet']}: {story['title']}")
            lines.append(story["link"])
        lines += [
            "",
            "Pictures and headlines belong to the newsrooms named in the video.",
            "This is not advice about your vote or your money.",
            "",
            job._tags(" ".join(story["title"] for story in news["stories"]), "news") + " #Shorts",
        ]
        description = "\n".join(lines)
        items.append({"file": str(news["file"]), "title": title, "description": description, "publish_at": times["short-tin"].isoformat(), "category": "25"})
        blocks += ["===== SHORT TIN =====", f"File: {news['file']}", f"Giờ công khai: {times['short-tin'].strftime('%Y-%m-%d %H:%M %Z')}", f"Dài {news['seconds']:.1f}s", title, "", description, ""]
    if money:
        item = money["item"]
        title = job._title(item["title"], when, 92) + " #Shorts"
        lines = [
            money["texts"][0],
            "",
            f"Source: {item['source']}",
            "",
            "This is not personal financial advice.",
            "",
            job._tags(item["title"] + " " + " ".join(money["texts"]), "finance") + " #Shorts",
        ]
        description = "\n".join(lines)
        items.append({"file": str(money["file"]), "title": title, "description": description, "publish_at": times["short-tien"].isoformat(), "category": "27"})
        blocks += ["===== SHORT TIỀN =====", f"File: {money['file']}", f"Giờ công khai: {times['short-tien'].strftime('%Y-%m-%d %H:%M %Z')}", f"Dài {money['seconds']:.1f}s", title, "", description, ""]
    manifest = folder / "lich.json"
    if manifest.exists():
        rebuilt = {Path(item["file"]).name for item in items}
        kept = [
            item for item in json.loads(manifest.read_text(encoding="utf-8"))
            if Path(item["file"]).name not in rebuilt and Path(item["file"]).exists()
        ]
        items = sorted(kept + items, key=lambda item: item["publish_at"])
    manifest.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "youtube.txt").write_text("\n".join(blocks), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", default=os.environ.get("US_DAILY_DAY", ""))
    parser.add_argument("--only", choices=("tin", "tien"), default="")
    args = parser.parse_args()
    when = datetime.now(NY)
    if args.day:
        when = datetime.strptime(args.day, "%Y-%m-%d").replace(tzinfo=NY, hour=6)
    folder = OUT / when.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    news = money = None
    failed = 0
    if args.only in ("", "tin"):
        try:
            news = build_news(when, folder)
            print(f"Short tin: {news['file']} ({news['seconds']:.1f}s)")
        except Exception as exc:
            failed += 1
            print(f"Chưa dựng được Short tin: {exc}")
    if args.only in ("", "tien"):
        try:
            money = build_money(when, folder)
            print(f"Short tiền: {money['file']} ({money['seconds']:.1f}s)")
        except Exception as exc:
            failed += 1
            print(f"Chưa dựng được Short tiền: {exc}")
    write_posts(folder, when, news, money)
    print(folder / "lich.json")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
