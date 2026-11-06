"""Một video: người Mỹ đang tìm giá của khoản vay nhà.

Số lấy từ Freddie Mac, Redfin, Apartment List, và phần giải thích của Investopedia.
Không bịa lãi suất. Không phải lời khuyên cá nhân. Không tự đăng.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SPOKEN = """
You did not search for a dream house. You searched for the price of the loan.
Freddie Mac's survey on November 5, 2026 put the average 30-year fixed rate at 7.18 percent. One year earlier, the same survey said 6.22 percent.
Picture one loan. 300,000 dollars, for 30 years, principal and interest only. At last year's rate the monthly bill is about 1,841 dollars. At this week's rate it is about 2,032 dollars. The rate wrote about 191 dollars onto the bill. Taxes, insurance, and a person's own credit are not in that sketch.
The next search is how much house can I afford. The calculator does not hand you a house. It hands you that bill, and asks whether the bill fits.
Rent versus buy is the search after that. In the four weeks ending October 25, 2026, Redfin's median sale price was 389,601 dollars, down 0.1 percent from a year earlier. Newsweek reported that figure. Apartment List put the national median rent at 1,384 dollars in October, the first rise in three years. Redfin's median mortgage payment that same late October week was 2,786 dollars, up 10.7 percent from a year earlier. Three national numbers. Not one front door.
In March 2026, Google searches for the words help with mortgage jumped. A New York Post headline said that line had passed the 2008 peak. Investopedia looked closer. Google counts the phrase differently now, and the words also catch people applying for a loan. The share of single-family mortgages that were late was under 2 percent in the second quarter of 2025. The peak in 2010 was above 11 percent. The search looks like panic. The missed payments do not look like 2008.
This week, write three lines. The Freddie Mac rate from the latest Thursday survey. The monthly payment on the amount you would actually borrow. The rent you pay now. If you cannot say the middle number out loud, that is the affordability answer in this example.
This is not personal financial advice, and it is not a promise about a rent payment or a loan.
""".strip()
BOARD = (
    ("search", ("dream house", "price of the loan")),
    ("rates", ("7.18", "freddie mac")),
    ("oldrate", ("6.22",)),
    ("loan", ("300,000", "picture one loan")),
    ("oldbill", ("1,841",)),
    ("newbill", ("2,032",)),
    ("gap", ("191",)),
    ("sketch", ("not in that sketch",)),
    ("afford", ("how much house", "bill fits")),
    ("doors", ("rent versus buy",)),
    ("price", ("median sale price", "389,601")),
    ("rent", ("1,384", "apartment list")),
    ("paymed", ("2,786", "median mortgage payment")),
    ("notone", ("not one front door", "three national")),
    ("spike", ("help with mortgage", "2008")),
    ("late", ("under 2 percent", "11 percent")),
    ("calm", ("missed payments do not", "looks like panic")),
    ("week", ("this week", "three lines")),
    ("advice", ("not personal", "not a promise")),
)
SOURCES = """
Freddie Mac Primary Mortgage Market Survey, 5/11/2026: lãi suất cố định 30 năm trung bình 7,18%. Cùng kỳ một năm trước 6,22%.
Hai hóa đơn 1.841 đô và 2.032 đô là gốc cộng lãi trên khoản vay 300.000 đô, 30 năm, tại đúng hai mức đó. Chưa gồm thuế, bảo hiểm, hay điểm tín dụng.
Redfin, bốn tuần kết thúc 25/10/2026, qua Newsweek: giá bán trung vị 389.601 đô, giảm 0,1% so với một năm trước. Khoản trả góp vay trung vị 2.786 đô, tăng 10,7%.
Apartment List, tháng 10/2026: tiền thuê trung vị cả nước 1.384 đô, lần tăng đầu tiên sau ba năm.
New York Post, 24/3/2026, đưa tin cụm "help with mortgage" trên Google Trends vượt đỉnh 2008. Investopedia nói cách đếm đã đổi, cụm từ còn gồm người đang xin vay, và tỷ lệ nợ vay nhà một hộ trễ hạn quý II/2025 vẫn dưới 2%, trong khi đỉnh 2010 hơn 11%.
Payney, mẫu tìm kiếm tiền tệ tại Mỹ tháng 9/2026: "mortgage rates" khoảng 12 lần mức quan tâm của "emergency fund" trong mẫu đó. Đây là điểm Google Trends, không phải số lượt gõ.
Không phải lời khuyên tài chính cá nhân.
"""


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "us-daily" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _marks(words):
    sample = " ".join(token for _start, _end, token in words).lower()
    spans, cursor = [], 0
    for index, (_start, _end, token) in enumerate(words):
        spans.append((cursor, index))
        cursor += len(token) + 1
    search_from = 0
    found = []
    for name, phrases in BOARD:
        best_at, best_phrase = None, ""
        for phrase in phrases:
            at = sample.find(phrase, search_from)
            if at >= 0 and (best_at is None or at < best_at):
                best_at, best_phrase = at, phrase
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
    return found or [(words[0][0], "search", words[0][2])]


def _chunks(text: str) -> list[str]:
    sentences: list[str] = []
    for block in text.split("\n"):
        for bit in block.split(". "):
            bit = bit.strip()
            if not bit:
                continue
            sentences.append(bit if bit.endswith(".") else bit + ".")
    groups: list[str] = []
    buf = ""
    for sentence in sentences:
        if buf and len(buf) + len(sentence) > 220:
            groups.append(buf)
            buf = sentence
        else:
            buf = f"{buf} {sentence}".strip()
    if buf:
        groups.append(buf)
    return groups


def _bill(draw, x, y, title, amount, font, fill, shown: bool) -> None:
    if not shown:
        return
    draw.rounded_rectangle((x, y, x + 240, y + 130), radius=16, fill=(255, 252, 244), outline=(28, 28, 32), width=5)
    draw.text((x + 18, y + 16), title, font=font, fill=(80, 80, 88))
    draw.text((x + 18, y + 64), amount, font=font, fill=fill)


def _door(draw, x, y, label, amount, font) -> None:
    draw.rounded_rectangle((x, y, x + 200, y + 180), radius=12, fill=(232, 214, 186), outline=(28, 28, 32), width=5)
    draw.ellipse((x + 160, y + 80, x + 178, y + 98), fill=(186, 150, 60))
    draw.text((x + 16, y + 40), label, font=font, fill=(28, 28, 32))
    draw.text((x + 16, y + 90), amount, font=font, fill=(24, 58, 122))


def _scene(draw, fonts, name, unit, second) -> tuple[float, float]:
    unit = max(0.0, min(1.0, unit))
    small, mid, big = fonts["small"], fonts["mid"], fonts["number"]
    if name == "search":
        draw.text((250, 70), "dream house", font=mid, fill=(170, 170, 176))
        draw.line((250, 100, 250 + int(320 * min(1, unit * 2)), 100), fill=(186, 48, 36), width=5)
        draw.rounded_rectangle((250, 140, 980, 230), radius=28, fill=(255, 255, 255), outline=(28, 28, 32), width=5)
        shown = "mortgage rates today"[: max(1, int(unit * 45))]
        draw.text((300, 155), shown, font=mid, fill=(28, 28, 32))
        return (300 + min(520, len(shown) * 18), 220)
    if name in {"rates", "oldrate"}:
        draw.text((280, 70), "7.18%", font=big, fill=(186, 48, 36))
        draw.text((700, 90), "6.22%", font=mid, fill=(80, 80, 88))
        draw.text((700, 150), "one year ago", font=small, fill=(80, 80, 88))
        draw.text((700, 210), "Freddie Mac, Nov 5, 2026", font=small, fill=(80, 80, 88))
        return (320, 175) if name == "rates" else (740, 155)
    if name == "loan":
        draw.polygon([(860, 170), (1000, 70), (1140, 170)], fill=(186, 92, 72), outline=(28, 28, 32))
        draw.rectangle((910, 170, 1090, 280), fill=(232, 214, 186), outline=(28, 28, 32), width=4)
        draw.text((280, 70), "$300,000", font=big, fill=(28, 28, 32))
        draw.text((620, 175), "30 years", font=mid, fill=(80, 80, 88))
        return (860, 230)
    if name in {"oldbill", "newbill", "gap", "sketch"}:
        _bill(draw, 280, 70, "last year", "$1,841", mid, (36, 110, 70), True)
        _bill(draw, 620, 70, "this week", "$2,032", mid, (186, 48, 36), name != "oldbill")
        if name in {"gap", "sketch"}:
            walk = 360 + int(240 * unit)
            draw.ellipse((walk, 230, walk + 110, 340), fill=(242, 184, 32), outline=(120, 78, 0), width=4)
            draw.text((walk + 18, 262), "$191", font=small, fill=(28, 28, 32))
            if name == "sketch":
                draw.text((780, 250), "no tax", font=small, fill=(80, 80, 88))
                draw.text((780, 290), "no insurance", font=small, fill=(80, 80, 88))
            return (walk + 20, 250)
        return (300, 190) if name == "oldbill" else (640, 190)
    if name == "afford":
        draw.rounded_rectangle((300, 70, 860, 280), radius=18, fill=(36, 48, 64), outline=(28, 28, 32), width=5)
        draw.rounded_rectangle((340, 100, 820, 190), radius=8, fill=(214, 236, 214))
        draw.text((380, 112), "$2,032", font=big, fill=(24, 90, 48))
        draw.text((360, 210), "a bill, not a house", font=small, fill=(255, 255, 255))
        return (360, 200)
    if name in {"doors", "notone"}:
        draw.text((420, 55), "not one front door", font=mid, fill=(186, 48, 36))
        _door(draw, 300, 120, "rent", "$1,384", small)
        _door(draw, 640, 120, "loan bill", "$2,786", small)
        return (300, 250) if name == "doors" else (640, 250)
    if name == "price":
        draw.text((280, 70), "$389,601", font=big, fill=(28, 28, 32))
        draw.text((280, 175), "down 0.1%", font=small, fill=(80, 80, 88))
        draw.polygon([(780, 200), (900, 110), (1020, 200)], fill=(186, 92, 72), outline=(28, 28, 32))
        draw.rectangle((820, 200, 980, 300), fill=(232, 214, 186), outline=(28, 28, 32), width=4)
        return (250, 150)
    if name == "rent":
        draw.rounded_rectangle((300, 80, 780, 250), radius=12, fill=(255, 252, 244), outline=(28, 28, 32), width=5)
        draw.text((340, 100), "national rent", font=small, fill=(80, 80, 88))
        draw.text((340, 140), "$1,384", font=big, fill=(24, 58, 122))
        return (340, 220)
    if name == "paymed":
        draw.rounded_rectangle((300, 80, 860, 270), radius=12, fill=(255, 236, 230), outline=(28, 28, 32), width=5)
        draw.text((340, 100), "median loan bill", font=small, fill=(80, 80, 88))
        draw.text((340, 140), "$2,786", font=big, fill=(186, 48, 36))
        draw.text((680, 160), "up 10.7%", font=small, fill=(186, 48, 36))
        draw.text((680, 200), "in a year", font=small, fill=(80, 80, 88))
        return (320, 250)
    if name in {"spike", "late", "calm"}:
        points = []
        steps = 16 if name != "spike" else max(2, int(2 + unit * 14))
        for step in range(steps):
            along = step / 15
            height = int(24 + 150 * along * along)
            points.append((760 + step * 18, 250 - height))
        if name == "spike":
            if len(points) > 1:
                draw.line(points, fill=(186, 48, 36), width=6)
            draw.text((760, 48), "searches jumped", font=small, fill=(186, 48, 36))
            return (760, 245)
        draw.text((520, 55), "under 2%", font=mid, fill=(36, 110, 70))
        draw.rounded_rectangle((520, 115, 680, 175), radius=8, fill=(48, 140, 86), outline=(28, 28, 32), width=3)
        draw.rounded_rectangle((780, 90, 920, 280), radius=8, fill=(186, 48, 36), outline=(28, 28, 32), width=3)
        draw.text((780, 50), "2010, above 11%", font=small, fill=(186, 48, 36))
        if name == "calm":
            draw.text((250, 70), "not 2008", font=mid, fill=(36, 110, 70))
        return (500, 160)
    if name == "week":
        lines = ("Freddie rate", "your monthly payment", "your rent")
        row_now = min(2, int(unit * 4))
        for row, line in enumerate(lines):
            if row > row_now:
                continue
            y = 60 + row * 78
            draw.rounded_rectangle((420, y, 1040, y + 64), radius=12, fill=(255, 252, 244), outline=(28, 28, 32), width=4)
            draw.text((460, y + 8), f"{row + 1}.  {line}", font=mid, fill=(28, 28, 32))
        return (430, 115 + row_now * 78)
    draw.rounded_rectangle((420, 70, 1040, 230), radius=16, fill=(255, 248, 230), outline=(28, 28, 32), width=5)
    draw.text((470, 95), "an example", font=mid, fill=(28, 28, 32))
    draw.text((470, 160), "not a promise", font=small, fill=(120, 50, 40))
    return (450 + 400 * unit, 220)


def _frame(tien, words, marks, fonts, second: float):
    image = Image.new("RGB", (tien.W, tien.H), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    index = tien._scene_at(marks, second)
    start, name, _token = marks[index]
    end = marks[index + 1][0] if index + 1 < len(marks) else words[-1][1]
    unit = (second - start) / max(0.35, end - start)
    tien._room(draw, index)
    tip = _scene(draw, fonts, name, unit, second)
    tien._host(draw, tip[0], tip[1], second)
    tien._caption(draw, fonts["caption"], tien._live_line(words, second))
    return image


def _render(tien, draw_mod, words, audio: Path, dest: Path) -> None:
    marks = _marks(words)
    lines = [f"{start:6.1f}s {name} (từ «{token}»)" for start, name, token in marks]
    dest.with_suffix(".canh.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(marks)} canh")
    for line in lines:
        print(line)
    fonts = tien._fonts(draw_mod)
    ffmpeg = draw_mod._ffmpeg_bin()
    frames = max(1, int(draw_mod._duration(audio) * tien.FPS))
    proc = subprocess.Popen(
        [
            ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{tien.W}x{tien.H}", "-r", str(tien.FPS),
            "-i", "-", "-i", str(audio), "-shortest",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k", "-ar", "24000", "-ac", "1", "-movflags", "+faststart", str(dest),
        ],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert proc.stdin is not None
    for frame in range(frames):
        proc.stdin.write(_frame(tien, words, marks, fonts, frame / tien.FPS).tobytes())
    proc.stdin.close()
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg {dest.name} {code}")


async def _speak_parts(run, draw_mod, text: str, dest: Path):
    words = []
    parts = []
    shift = 0.0
    for index, chunk in enumerate(_chunks(text)):
        part = dest.with_name(f"nha-phan-{index}.mp3")
        got = await run._speak_timed(chunk, part)
        if len(got) < max(4, int(len(chunk.split()) * 0.7)):
            got = await run._speak_timed(chunk, part)
        dur = draw_mod._duration(part)
        for start, end, token in got:
            words.append((start + shift, end + shift, token))
        parts.append(part)
        shift += dur
        print(f"doan {index + 1}: {len(got)} tu, {dur:.1f}s")
    listing = dest.with_suffix(".list.txt")
    listing.write_text("".join(f"file '{part.as_posix()}'\n" for part in parts), encoding="utf-8")
    subprocess.run(
        [draw_mod._ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(dest)],
        check=True,
        stderr=subprocess.DEVNULL,
    )
    return words


def main() -> int:
    run = _load("run")
    tien = _load("tien")
    draw_mod = _load("but_ve")
    folder = run.OUT / datetime.now(run.NY).strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "nha.txt").write_text(SPOKEN + "\n\n" + SOURCES, encoding="utf-8")
    audio = folder / "nha.mp3"
    cache = folder / "nha.words.json"
    if cache.exists() and audio.exists() and audio.stat().st_size > 10000:
        words = [tuple(item) for item in json.loads(cache.read_text(encoding="utf-8"))]
        print(f"dung lai giong da thu, {len(words)} tu")
    else:
        words = asyncio.run(_speak_parts(run, draw_mod, SPOKEN, audio))
        cache.write_text(json.dumps(words), encoding="utf-8")
    (folder / "nha.loi.txt").write_text(" ".join(token for _s, _e, token in words), encoding="utf-8")
    dest = folder / "nha.mp4"
    _render(tien, draw_mod, words, audio, dest)
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
