"""Một video giải thích tiền, nhà hoặc kinh tế mỗi ngày.

Mỗi câu là một cảnh khác: đồ vật đúng câu đó, và đồ vật chuyển động trong câu.
Nhân vật là hình vẽ riêng. Không chép tranh, mặt, hay logo của kênh khác.
Không bịa số thị trường. Không tự đăng.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import math
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
# Mỗi mốc chỉ xuất hiện một lần, theo đúng thứ tự lời thoại.
# Câu nằm giữa hai mốc giữ cảnh của mốc trước, nhưng đổi phòng và phía nhân vật.
CARD_BOARD = (
    ("open", ("here is the number",)),
    ("card", ("card balance", "never falls")),
    ("split", ("divide by twelve", "month rate", "1.67%")),
    ("interest", ("first month of interest", "16.67")),
    ("minimum", ("required minimum", "reduces what you owe", "8.33")),
    ("trap", ("still near", "the trap")),
    ("multiply", ("simple yearly", "one thousand times")),
    ("compound", ("compounds every month", "costs more")),
    ("statement", ("own statement", "something else")),
    ("replay", ("second way",)),
    ("month1", ("month one", "nine hundred ninety-two", "sixty-seven cents")),
    ("month2", ("month two", "barely moves", "speed is slow")),
    ("hundred", ("add one hundred", "one hundred eight")),
    ("drop", ("eight hundred",)),
    ("plot", ("whole plot",)),
    ("rates", ("fourteen percent", "different stories")),
    ("formula", ("the formula stays", "in the margin")),
    ("penalty", ("do not skip", "penalty rate")),
    ("extra", ("the extra payment",)),
    ("both", ("every card",)),
    ("week", ("this week",)),
    ("recap", ("the way we just did",)),
    ("cut", ("cut the balance",)),
    ("autopay", ("autopay", "on a calendar")),
    ("advice", ("not personal", "not a promise")),
)
FUND_BOARD = (
    ("open", ("here is the number",)),
    ("pile", ("your own money", "twenty-four thousand")),
    ("ghost", ("labeled hypothetical", "not a forecast", "seven percent")),
    ("city", ("index fund", "wide list")),
    ("onehouse", ("one stock", "one company can cut")),
    ("folder", ("workplace", "does not tell you which")),
    ("boxes", ("separate the two numbers", "how much of it")),
    ("risk", ("a single stock", "bad tuesday")),
    ("fifty", ("fifty dollars", "six thousand")),
    ("week", ("this week",)),
    ("autopay", ("day after payday", "set the transfer")),
    ("advice", ("not personal", "not a projection")),
)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _marks(words):
    """Đổi cảnh đúng lúc câu nói chạm cụm từ, không chờ hết một đoạn 6 giây."""
    full = " ".join(token for _start, _end, token in words)
    sample = full.lower()
    if "card balance" in sample or "the trap" in sample:
        board = CARD_BOARD
    elif "twenty-four thousand" in sample or "index fund" in sample:
        board = FUND_BOARD
    else:
        board = (
            ("open", ("here is the number",)),
            ("week", ("this week",)),
            ("advice", ("not personal financial advice",)),
        )
    spans = []
    cursor = 0
    for index, (_start, _end, token) in enumerate(words):
        spans.append((cursor, index))
        cursor += len(token) + 1
    search_from = 0
    found = []
    for name, phrases in board:
        best_at = None
        best_phrase = ""
        for phrase in phrases:
            at = sample.find(phrase, search_from)
            if at >= 0 and (best_at is None or at < best_at):
                best_at = at
                best_phrase = phrase
        if best_at is None:
            continue
        search_from = best_at + len(best_phrase)
        word_index = 0
        for char_at, index in spans:
            if char_at <= best_at:
                word_index = index
            else:
                break
        start, _end, token = words[word_index]
        found.append((start, name, token))
    if not found and words:
        found.append((words[0][0], "open", words[0][2]))
    return found


def _scene_at(marks, second: float) -> int:
    chosen = 0
    for index, (start, _name, _token) in enumerate(marks):
        if start <= second + 0.04:
            chosen = index
        else:
            break
    return chosen


def _live_line(words, second: float) -> str:
    index = 0
    for word_index, (start, _end, _token) in enumerate(words):
        if start <= second + 0.04:
            index = word_index
        else:
            break
    window = words[max(0, index - 6) : index + 5]
    bits: list[str] = []
    for _start, _end, token in window:
        if bits and token[:1].isupper() and (len(token) == 1 or not token.isupper()):
            bits.append(". " + token)
        elif bits:
            bits.append(" " + token)
        else:
            bits.append(token)
    return "".join(bits)


def _text(draw, xy, text, font, fill) -> None:
    draw.text(xy, text, font=font, fill=fill, anchor="lt")


def _coin(draw, x, y, radius=22) -> None:
    draw.ellipse((x, y, x + radius * 2, y + radius * 2), fill=GOLD, outline=(120, 78, 0), width=4)
    draw.ellipse((x + 6, y + 6, x + radius * 2 - 6, y + radius * 2 - 6), outline=(160, 110, 20), width=3)


def _hand(draw, x: float, y: float) -> None:
    draw.ellipse((x - 16, y - 16, x + 16, y + 16), fill=SKIN, outline=INK, width=3)


def _arm(draw, start, end) -> None:
    draw.line((*start, *end), fill=NAVY, width=18)
    _hand(draw, end[0], end[1])


def _wallet(draw, x, y, opened: float) -> None:
    opened = max(0.0, min(1.0, opened))
    draw.rounded_rectangle((x, y + 36, x + 210, y + 150), radius=14, fill=(122, 74, 42), outline=INK, width=4)
    flap = y + 48 - int(70 * opened)
    draw.polygon([(x + 8, y + 56), (x + 202, y + 56), (x + 184, flap), (x + 26, flap)], fill=(92, 52, 28), outline=INK)
    if opened > 0.25:
        lift = int(36 * opened)
        draw.rounded_rectangle((x + 46, y + 48 - lift, x + 164, y + 100), radius=6, fill=(78, 150, 96), outline=INK, width=3)


def _hits(box, other) -> bool:
    return box[0] < other[2] and box[2] > other[0] and box[1] < other[3] and box[3] > other[1]


def _marker(draw, start, end) -> None:
    """Cây bút to: thân, vòng vàng, kẹp, và ngòi sắt."""
    x0, y0 = start
    x1, y1 = end
    dx, dy = x1 - x0, y1 - y0
    dist = math.hypot(dx, dy) or 1
    ux, uy = dx / dist, dy / dist
    px, py = -uy * 16, ux * 16
    neck = (x1 - ux * 34, y1 - uy * 34)
    draw.polygon(
        [
            (x0 + px, y0 + py),
            (neck[0] + px * 0.8, neck[1] + py * 0.8),
            (neck[0] - px * 0.8, neck[1] - py * 0.8),
            (x0 - px, y0 - py),
        ],
        fill=(32, 48, 92),
        outline=INK,
    )
    band = (neck[0] - ux * 18, neck[1] - uy * 18)
    draw.line((band[0] + px, band[1] + py, band[0] - px, band[1] - py), fill=GOLD, width=8)
    clip = (x0 + ux * 22 + px * 0.15, y0 + uy * 22 + py * 0.15)
    draw.line((clip[0], clip[1], clip[0] + ux * 48, clip[1] + uy * 48), fill=(226, 226, 232), width=4)
    draw.polygon(
        [(x1, y1), (neck[0] + px * 0.45, neck[1] + py * 0.45), (neck[0] - px * 0.45, neck[1] - py * 0.45)],
        fill=(176, 182, 190),
        outline=INK,
    )
    draw.line((neck[0], neck[1], x1, y1), fill=(40, 40, 44), width=2)
    for finger in range(3):
        along = 18 + finger * 16
        fx, fy = x0 + ux * along, y0 + uy * along
        draw.ellipse((fx - 9, fy - 9, fx + 9, fy + 9), fill=SKIN, outline=INK, width=2)


def _host(draw, tip_x: float, tip_y: float, second: float) -> None:
    """Người nhỏ đứng bên hình, tay trái giữ giấy, tay phải cầm bút chạm nét."""
    step = int(18 * math.sin(second * 8))
    sway = int(8 * math.sin(second * 5))
    sprite = Image.new("RGBA", (280, 300), (0, 0, 0, 0))
    pen = ImageDraw.Draw(sprite)
    x, y = 24, 8
    pen.ellipse((x + 24, y + 246, x + 112, y + 268), fill=(120, 90, 60, 255))
    pen.rounded_rectangle((x + 30 + step, y + 168, x + 58 + step, y + 248), radius=8, fill=(32, 40, 72, 255))
    pen.rounded_rectangle((x + 74 - step, y + 168, x + 102 - step, y + 248), radius=8, fill=(32, 40, 72, 255))
    pen.ellipse((x + 22 + step, y + 232, x + 66 + step, y + 256), fill=(28, 28, 32, 255))
    pen.ellipse((x + 68 - step, y + 232, x + 112 - step, y + 256), fill=(28, 28, 32, 255))
    pen.rounded_rectangle((x + 18, y + 78, x + 116, y + 186), radius=18, fill=(*NAVY, 255), outline=(*INK, 255), width=4)
    pen.polygon([(x + 60, y + 86), (x + 78, y + 86), (x + 69, y + 138)], fill=(196, 42, 48, 255))
    _arm(pen, (x + 28, y + 118), (x - 8, y + 168 - step))
    hand = (x + 176, y + 128 + sway)
    _arm(pen, (x + 108, y + 112), hand)
    pen.ellipse((x + 8, y + 48, x + 28, y + 72), fill=(*SKIN, 255), outline=(*INK, 255), width=3)
    pen.ellipse((x + 106, y + 48, x + 126, y + 72), fill=(*SKIN, 255), outline=(*INK, 255), width=3)
    pen.ellipse((x + 30, y + 6, x + 104, y + 88), fill=(*SKIN, 255), outline=(*INK, 255), width=4)
    pen.pieslice((x + 30, y + 2, x + 104, y + 58), 200, 340, fill=(*INK, 255))
    if (second % 3.4) < 0.12:
        pen.line((x + 46, y + 44, x + 62, y + 44), fill=(*INK, 255), width=3)
        pen.line((x + 72, y + 44, x + 88, y + 44), fill=(*INK, 255), width=3)
    else:
        pen.ellipse((x + 48, y + 38, x + 60, y + 50), fill=(*INK, 255))
        pen.ellipse((x + 74, y + 38, x + 86, y + 50), fill=(*INK, 255))
    pen.arc((x + 52, y + 52, x + 84, y + 74), 15, 165, fill=(150, 70, 60, 255), width=3)
    scale = 0.7
    frame = sprite.resize((int(280 * scale), int(300 * scale)), Image.Resampling.NEAREST)
    width, height = frame.size
    hx, hy = hand[0] * scale, hand[1] * scale
    nib_x = tip_x + 4 * math.sin(second * 16)
    nib_y = tip_y + 3 * math.cos(second * 16)
    letters = (tip_x - 24, tip_y - 78, tip_x + 190, tip_y + 8)
    paste_x = int(max(8, min(900, nib_x - hx - 96)))
    paste_y = int(min(350, max(letters[3] + 6, nib_y - hy + 78)))
    if _hits((paste_x, paste_y, paste_x + width, paste_y + height), letters):
        paste_x = int(max(8, letters[0] - width - 18))
        paste_y = int(min(350, max(paste_y, letters[3] + 10)))
    draw._image.paste(frame, (paste_x, paste_y), frame)
    _marker(draw, (paste_x + hx, paste_y + hy), (nib_x, nib_y))


def _trace(x, y, width, height, unit: float):
    width, height = float(width), float(height)
    dist = max(0.0, min(1.0, unit)) * 2 * (width + height)
    if dist <= width:
        return x + dist, y
    dist -= width
    if dist <= height:
        return x + width, y + dist
    dist -= height
    if dist <= width:
        return x + width - dist, y + height
    return x, y + height - (dist - width)


def _room(draw, index: int) -> None:
    skies = ((176, 214, 242), (255, 220, 186), (214, 228, 196), (186, 198, 232), (255, 236, 214), (230, 214, 228))
    floors = ((214, 186, 146), (168, 188, 150), (196, 176, 150), (150, 170, 190), (210, 170, 140), (180, 160, 170))
    draw.rectangle((0, 0, W, 460), fill=skies[index % 6])
    draw.rectangle((0, 460, W, H), fill=floors[index % 6])
    draw.rounded_rectangle((180, 36, 1220, 530), radius=18, fill=(255, 252, 246), outline=INK, width=5)
    host_right = index % 2 == 1
    if index % 3 == 0:
        left = 40 if host_right else 980
        draw.rectangle((left, 70, left + 240, 280), outline=INK, width=6, fill=(232, 244, 255))
        draw.line((left + 120, 70, left + 120, 280), fill=INK, width=4)
        draw.line((left, 175, left + 240, 175), fill=INK, width=4)
    elif index % 3 == 1:
        sun = 40 if host_right else 1040
        draw.ellipse((sun, 36, sun + 150, 186), fill=(255, 214, 80), outline=INK, width=4)
    else:
        bush = 980 if host_right else 40
        draw.rectangle((bush, 80, bush + 180, 300), fill=(90, 120, 90), outline=INK, width=4)


def _card(draw, x, y, label, font) -> None:
    draw.rounded_rectangle((x, y, x + 340, y + 200), radius=18, fill=(36, 92, 176), outline=INK, width=5)
    draw.rounded_rectangle((x + 24, y + 28, x + 90, y + 72), radius=8, fill=GOLD)
    draw.rectangle((x, y + 100, x + 340, y + 132), fill=INK)
    _text(draw, (x + 24, y + 146), label, font, (255, 255, 255))


def _column(draw, x, base, height, width, fill, label, font) -> None:
    height = max(8, int(height))
    draw.rounded_rectangle((x, base - height, x + width, base), radius=10, fill=fill, outline=INK, width=4)
    _text(draw, (x, base - height - 36), label, font, INK)


def _caption(draw, font, text: str) -> None:
    draw.rounded_rectangle((40, 600, 1240, 700), radius=16, fill=(16, 16, 18))
    lines, current = [], ""
    for word in text.split():
        trial = word if not current else f"{current} {word}"
        if font.getlength(trial) > 1140 and current:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    for row, line in enumerate(lines[:2]):
        _text(draw, (64, 612 + row * 40), line, font, (255, 255, 255))


def _pen_tip(name: str, unit: float, second: float):
    unit = max(0.0, min(1.0, unit))
    if name == "open":
        return (500 + 180 * unit, 230)
    if name == "card":
        if unit < 0.4:
            return (230, 250 + 80 * (unit / 0.4))
        return (640, 130 + 170 * ((unit - 0.4) / 0.6))
    if name == "replay":
        return _trace(280 + 220 * unit, 140, 340, 200, unit)
    if name == "split":
        month = int(second * 2) % 12
        column, row = month % 6, month // 6
        return (405 + column * 110, 140 + row * 150)
    if name == "interest":
        return (640, 122 + 220 * unit)
    if name == "minimum":
        slot = min(2, int(unit * 3))
        heights = (80 + 140 * unit, 40 + 180 * unit, 20 + 50 * unit)
        return ((660, 860, 1060)[slot], 506 - heights[slot])
    if name == "trap":
        return (300 + 180 * unit, 175)
    if name == "multiply":
        return (300 + min(2, int(unit * 3)) * 230, 250)
    if name == "compound":
        return (600 + 40 * unit, 280)
    if name == "statement":
        return (450 + 420 * unit, 190)
    if name == "month1":
        return (380 + 160 * min(1, unit * 1.6), 280)
    if name == "month2":
        angle = -1.2 + second * 0.35
        return (400 + 70 * math.cos(angle), 220 + 70 * math.sin(angle))
    if name == "hundred":
        return (286 + 280 * unit, 266)
    if name == "drop":
        return (720, 500 - (300 - 140 * unit))
    if name == "plot":
        ring = 70 + 16 * math.sin(second * 5)
        return (610 + ring * math.cos(second * 4), 270 + ring * math.sin(second * 4))
    if name == "rates":
        return (870, 250 + 10 * math.sin(second * 8))
    if name == "formula":
        return (400 + min(2, int(unit * 3)) * 300, 250)
    if name == "penalty":
        return (520 + 10 * math.sin(second * 18), 250)
    if name == "extra":
        return (640 + 40 * math.sin(second * 3), 250)
    if name == "recap":
        item = int(second) % 3
        return (410 + item * 280, 230 + 12 * math.sin(second * 3))
    if name == "pile":
        item = int(second * 3) % 4
        y = 360 - ((second * 50 + item * 40) % 220)
        return (436 + item * 70, y)
    if name == "ghost":
        return (640, 460 - 240 * unit)
    if name == "city":
        item = min(7, int(unit * 8))
        height = (40 + item * 28) * min(1, unit + 0.2)
        return (370 + item * 80, 460 - height)
    if name == "onehouse":
        return (660 + 8 * math.sin(second * 10), 180)
    if name == "folder":
        return (620, 210 - 70 * (1 - unit))
    if name == "boxes":
        return (880, 260)
    if name == "risk":
        crack = 200 * unit
        return (690 + crack / 5, 180 + crack)
    if name == "fifty":
        return (770, 480 - (70 + 160 * unit))
    if name == "both":
        item = 0 if unit < 0.55 else 1
        return (500 + item * 280, 210)
    if name == "week":
        return (405 + int(unit * 6) * 110, 170)
    if name == "autopay":
        return (540 + 260 * unit, 290)
    if name == "cut":
        return (600, 500 - (300 - 160 * unit))
    return (500 + 380 * unit, 330)


def _act(draw, fonts, name: str, unit: float, second: float, index: int, number: str) -> None:
    _room(draw, index)
    unit = max(0.0, min(1.0, unit))
    if name == "open":
        size = 36 + int(56 * unit)
        font = fonts["grow"](size)
        _text(draw, (520, 150), number, font, (186, 48, 36))
        for item in range(4):
            _coin(draw, 430 + int((160 + item * 40) * unit), 360 - int(80 * math.sin(second * 3 + item)), 16)
    elif name == "card":
        _wallet(draw, 230, 250, min(1.0, unit * 1.6))
        _card(draw, 640, 110, "$1,000", fonts["small"])
        draw.ellipse((990, 300, 1130, 440), fill=(186, 48, 36), outline=INK, width=4)
        _text(draw, (1010, 345), "20%", fonts["mid"], (255, 255, 255))
        _text(draw, (250, 210), "$200 a year", fonts["small"], (120, 40, 30))
        for item in range(5):
            fall = (second * 120 + item * 55) % 150
            drift = int(16 * math.sin(second * 3 + item))
            _coin(draw, 300 + drift, 160 + int(fall), 14)
    elif name == "replay":
        slide = int(220 * unit)
        _card(draw, 280 + slide, 140, "$1,000", fonts["small"])
    elif name == "cut":
        _column(draw, 520, 500, 300 - 160 * unit, 160, (48, 150, 86), "extra", fonts["small"])
        _coin(draw, 300 + int(180 * unit), 240, 28)
    elif name == "split":
        for month in range(12):
            column, row = month % 6, month // 6
            drop = int(70 * unit) if month == int(second) % 12 else 0
            x, y = 360 + column * 110, 90 + row * 150 + drop
            fill = GOLD if drop else (255, 255, 255)
            draw.rounded_rectangle((x, y, x + 90, y + 110), radius=8, fill=fill, outline=INK, width=3)
            _text(draw, (x + 28, y + 36), str(month + 1), fonts["small"], INK)
        _text(draw, (470, 400), "1.67% a month", fonts["small"], INK)
    elif name == "interest":
        y = 80 + int(220 * unit)
        _coin(draw, 560, y, 42)
        _text(draw, (680, y + 24), "$16.67", fonts["small"], INK)
        draw.rounded_rectangle((430, 420, 860, 520), radius=8, fill=(255, 252, 240), outline=INK, width=4)
    elif name == "minimum":
        _column(draw, 660, 500, 80 + 140 * unit, 120, (36, 92, 176), "$25", fonts["small"])
        _column(draw, 860, 500, 40 + 180 * unit, 140, (196, 52, 48), "$16.67", fonts["small"])
        _column(draw, 1060, 500, 20 + 50 * unit, 110, (48, 150, 86), "$8.33", fonts["small"])
        _coin(draw, 470 + int(160 * unit), 80 + int(40 * math.sin(second * 4)), 16)
        _coin(draw, 470 + int(400 * unit), 120 + int(30 * math.sin(second * 5)), 12)
    elif name == "trap":
        _column(draw, 520, 500, 280, 160, (196, 52, 48), "$1,000", fonts["small"])
        jaw = int(180 * unit)
        draw.rectangle((300, 160, 300 + jaw, 190), fill=INK)
        draw.rectangle((980 - jaw, 160, 980, 190), fill=INK)
    elif name == "multiply":
        labels = ("$1,000", "x 20%", number)
        for item, label in enumerate(labels):
            arrived = min(1.0, max(0.0, (unit - item * 0.12) / 0.22))
            if arrived <= 0:
                continue
            x = 200 + item * 230 + int((1 - arrived) * 70)
            draw.rounded_rectangle((x, 200, x + 200, 310), radius=12, fill=(255, 248, 230), outline=INK, width=4)
            _text(draw, (x + 16, 230), label, fonts["small"], INK)
    elif name == "compound":
        radius = 20 + int(40 * unit)
        _coin(draw, 560, 240, radius)
        for item in range(int(3 + 5 * unit)):
            _coin(draw, 480 + item * 36, 400 - int(20 * math.sin(second * 2 + item)), 14)
    elif name == "statement":
        draw.rounded_rectangle((400, 80, 980, 500), radius=12, fill=(255, 252, 242), outline=INK, width=5)
        for row in range(5):
            draw.rectangle((450, 140 + row * 60, 900, 162 + row * 60), fill=(220, 214, 200))
        pen_x = 450 + int(420 * unit)
        draw.line((pen_x, 150, pen_x + 40, 230), fill=(30, 30, 30), width=6)
        draw.polygon([(pen_x + 34, 214), (pen_x + 70, 250), (pen_x + 20, 236)], fill=GOLD)
    elif name == "month1":
        height = 300 - 18 * unit
        _column(draw, 620, 500, height, 140, (196, 52, 48), "992" if unit > 0.72 else "1,000", fonts["small"])
        _coin(draw, 360 + int(160 * min(1, unit * 1.6)), 250, 18)
        if unit > 0.28:
            _text(draw, (300, 120), "$25 paid", fonts["small"], NAVY)
            _text(draw, (300, 160), "$16.67 interest", fonts["small"], (186, 48, 36))
            _text(draw, (300, 200), "$8.33 off", fonts["small"], (36, 120, 70))
    elif name == "month2":
        _column(draw, 620, 500, 276 - 6 * unit, 140, (196, 52, 48), "992", fonts["small"])
        angle = -1.2 + second * 0.35
        draw.ellipse((300, 120, 500, 320), fill=(255, 248, 236), outline=INK, width=5)
        draw.line((400, 220, 400 + 70 * math.cos(angle), 220 + 70 * math.sin(angle)), fill=(180, 40, 40), width=6)
        _text(draw, (330, 340), "barely moves", fonts["small"], INK)
    elif name == "hundred":
        _coin(draw, 240 + int(280 * unit), 220, 46)
        _text(draw, (250 + int(280 * unit), 250), "$100", fonts["small"], INK)
        if unit > 0.4:
            _text(draw, (240, 120), "$108 off the balance", fonts["small"], (36, 120, 70))
        _column(draw, 860, 500, 280 - 90 * unit, 120, (48, 150, 86), "800s" if unit > 0.65 else "992", fonts["small"])
    elif name == "drop":
        _column(draw, 720, 500, 300 - 140 * unit, 170, (48, 150, 86), "800s", fonts["small"])
    elif name == "plot":
        _coin(draw, 560, 220, 50)
        ring = 70 + int(16 * math.sin(second * 5))
        draw.ellipse((610 - ring, 270 - ring, 610 + ring, 270 + ring), outline=(186, 48, 36), width=6)
        _text(draw, (560, 400), "the extra $100", fonts["small"], INK)
    elif name == "rates":
        _card(draw, 300, 140, "14%", fonts["small"])
        _card(draw, 700, 140 + int(10 * math.sin(second * 8)), "29%", fonts["small"])
        _column(draw, 360, 520, 80, 80, (48, 150, 86), "", fonts["small"])
        _column(draw, 800, 520, 80 + 140 * unit, 80, (196, 52, 48), "", fonts["small"])
    elif name == "formula":
        for item, label in enumerate(("balance", "x APR", "÷ 12")):
            if unit < item / 3:
                continue
            x = 280 + item * 300
            draw.rounded_rectangle((x, 180, x + 240, 320), radius=14, fill=(255, 248, 230), outline=INK, width=4)
            _text(draw, (x + 24, 220), label, fonts["small"], INK)
    elif name == "penalty":
        shake = int(10 * math.sin(second * 18))
        _card(draw, 340 + shake, 150, "missed", fonts["small"])
        draw.ellipse((760, 160, 980, 380), outline=(186, 48, 36), width=8)
        _text(draw, (800, 240), "!", fonts["number"], (186, 48, 36))
    elif name == "extra":
        _coin(draw, 380, 280, 18)
        _text(draw, (360, 220), "$25", fonts["small"], INK)
        _coin(draw, 560 + int(40 * math.sin(second * 3)), 200, 40)
        _text(draw, (560, 160), "extra", fonts["small"], (186, 48, 36))
    elif name == "recap":
        for item, label in enumerate(("$1,000", "x APR", "÷ 12")):
            x = 300 + item * 280
            y = 160 + int(12 * math.sin(second * 3 + item))
            draw.rounded_rectangle((x, y, x + 220, y + 140), radius=14, fill=(255, 248, 230), outline=INK, width=4)
            _text(draw, (x + 24, y + 48), label, fonts["small"], INK)
    elif name == "pile":
        for item in range(8):
            y = 360 - int((second * 50 + item * 40) % 220)
            _coin(draw, 420 + (item % 4) * 70, y, 16)
        _text(draw, (400, 120), number, fonts["mid"], INK)
    elif name == "ghost":
        height = int(240 * unit)
        draw.rounded_rectangle((520, 460 - height, 760, 460), radius=12, outline=(80, 80, 120), width=4)
        _text(draw, (600, 180), "?", fonts["number"], (80, 80, 120))
        _text(draw, (430, 80), "a guess, not a promise", fonts["small"], INK)
    elif name == "city":
        for item in range(8):
            height = int((40 + item * 28) * min(1, unit + 0.2))
            draw.rectangle((340 + item * 80, 460 - height, 400 + item * 80, 460), fill=(120, 168, 196), outline=INK, width=3)
    elif name == "onehouse":
        sway = int(8 * math.sin(second * 10))
        draw.rectangle((560 + sway, 160, 760 + sway, 460), fill=(214, 120, 110), outline=INK, width=4)
        _text(draw, (580, 100), "one company", fonts["small"], INK)
    elif name == "folder":
        draw.rounded_rectangle((420, 200, 900, 480), radius=12, fill=(255, 236, 170), outline=INK, width=5)
        flap = int(80 * (1 - unit))
        draw.polygon([(420, 200), (620, 200), (560, 200 - flap), (420, 200 - flap)], fill=(232, 190, 90), outline=INK)
    elif name == "boxes":
        draw.rounded_rectangle((340, 160, 620, 420), radius=12, fill=(255, 248, 230), outline=INK, width=4)
        _text(draw, (370, 240), "you put in", fonts["small"], INK)
        grow = int(80 * unit)
        draw.rounded_rectangle((720, 160, 1040, 420), radius=12, outline=(80, 80, 120), width=4)
        _text(draw, (760, 200 + grow), "maybe", fonts["small"], (80, 80, 120))
    elif name == "risk":
        sway = int(6 * math.sin(second * 12))
        draw.rectangle((600 + sway, 140, 780 + sway, 460), fill=(214, 120, 110), outline=INK, width=4)
        crack = int(200 * unit)
        draw.line((690, 180, 690 + crack // 5, 180 + crack), fill=INK, width=4)
    elif name == "fifty":
        _column(draw, 400, 480, 70, 120, (48, 150, 86), "$50", fonts["small"])
        _column(draw, 700, 480, 70 + 160 * unit, 140, GOLD, "$200", fonts["small"])
    elif name == "both":
        for item in range(2):
            x = 400 + item * 280
            draw.rounded_rectangle((x, 160, x + 200, 280), radius=12, fill=(255, 255, 255), outline=INK, width=4)
            if unit > 0.3 + item * 0.3:
                draw.line((x + 30, 210, x + 70, 260), fill=(36, 140, 72), width=8)
                draw.line((x + 70, 260, x + 150, 150), fill=(36, 140, 72), width=8)
    elif name == "week":
        for day in range(7):
            x = 360 + day * 110
            fill = GOLD if day == int(unit * 6) else (255, 255, 255)
            draw.rounded_rectangle((x, 160, x + 90, 280), radius=8, fill=fill, outline=INK, width=3)
        draw.ellipse((360 + int(unit * 6) * 110 - 8, 150, 470 + int(unit * 6) * 110, 300), outline=(186, 48, 36), width=5)
    elif name == "autopay":
        knob = 480 + int(260 * unit)
        draw.rounded_rectangle((460, 240, 860, 340), radius=40, fill=(48, 150, 86) if unit > 0.5 else (180, 180, 180), outline=INK, width=4)
        draw.ellipse((knob, 220, knob + 120, 360), fill=(255, 255, 255), outline=INK, width=4)
    else:
        draw.rounded_rectangle((420, 160, 980, 360), radius=16, fill=(255, 248, 230), outline=INK, width=5)
        _text(draw, (470, 210), "an example", fonts["mid"], INK)
        _text(draw, (470, 270), "not a promise", fonts["small"], (120, 50, 40))
        draw.line((470, 320, 470 + int(420 * unit), 320), fill=(120, 50, 40), width=6)
    tip_x, tip_y = _pen_tip(name, unit, second)
    _host(draw, tip_x, tip_y, second)


def _fonts(draw_mod) -> dict:
    cache: dict[int, object] = {}

    def grow(size: int):
        if size not in cache:
            cache[size] = draw_mod.ImageFont.truetype(draw_mod.FONT_DISPLAY, size)
        return cache[size]

    return {
        "number": grow(84),
        "mid": grow(48),
        "small": grow(32),
        "caption": draw_mod.ImageFont.truetype(draw_mod.FONT_BOLD, 32),
        "grow": grow,
    }


def _frame(words, marks, fonts, number: str, second: float):
    image = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    index = _scene_at(marks, second)
    start, name, _token = marks[index]
    end = marks[index + 1][0] if index + 1 < len(marks) else words[-1][1]
    unit = (second - start) / max(0.35, end - start)
    _act(draw, fonts, name, unit, second, index, number)
    _caption(draw, fonts["caption"], _live_line(words, second))
    return image


def _render(draw_mod, words, audio: Path, dest: Path, number: str) -> None:
    marks = _marks(words)
    log = dest.with_suffix(".canh.txt")
    lines = [f"{start:6.1f}s {name} (từ «{token}»)" for start, name, token in marks]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(marks)} canh")
    for line in lines:
        print(line)
    fonts = _fonts(draw_mod)
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
        image = _frame(words, marks, fonts, number, frame / FPS)
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
    shot = "Each sentence gets its own moving picture of the thing just said."
    item = run.finance_one(when)
    print(item["title"], item["words"])
    text = run._package("finance", item["spoken"], item["title"], [item["source"]], shot)
    (folder / "finance-1.txt").write_text(text, encoding="utf-8")
    audio = folder / "tai-chinh-1.mp3"
    words = asyncio.run(run._speak_timed(item["spoken"], audio))
    dest = folder / "tai-chinh-1.mp4"
    _render(draw_mod, words, audio, dest, item["number"])
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
