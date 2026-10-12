"""Tạo ảnh storyboard cho từng cảnh."""

from __future__ import annotations

import io
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from studio.specs import GEN_SIZE, craft_visual_prompt

FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    path = FONT_BOLD if bold and FONT_BOLD.exists() else FONT
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def grade(im: Image.Image) -> Image.Image:
    """Tăng tương phản nhẹ và che góc watermark của ảnh miễn phí."""
    width, height = im.size
    if height > 220:
        im = im.crop((0, 0, width, height - max(36, height // 12)))
    im = ImageEnhance.Contrast(im).enhance(1.06)
    im = ImageEnhance.Color(im).enhance(1.04)
    base = im.convert("RGBA")
    width, height = base.size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for step in range(16):
        alpha = int(64 * (1 - step / 16))
        pad = step * 3
        draw.rectangle(
            [pad, pad, width - 1 - pad, height - 1 - pad],
            outline=(0, 0, 0, alpha),
        )
    corner_w = min(260, width // 3)
    corner_h = min(72, height // 7)
    corner = Image.new("RGBA", (corner_w, corner_h), (0, 0, 0, 0))
    pixels = corner.load()
    for y in range(corner_h):
        for x in range(corner_w):
            fade = (x / corner_w) ** 1.3 * (y / corner_h) ** 1.15
            pixels[x, y] = (8, 6, 4, int(230 * fade))
    overlay.paste(corner, (width - corner_w, height - corner_h), corner)
    return Image.alpha_composite(base, overlay).convert("RGB")


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, limit: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = current + " " + word
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
            if len(lines) == limit - 1:
                break
    if len(lines) < limit:
        lines.append(current)
    if len(lines) == limit and len(" ".join(words)) > len(" ".join(lines)):
        lines[-1] = lines[-1].rstrip(".") + "…"
    return lines


def write_placeholder(path: Path, width: int, height: int, heading: str, body: str) -> None:
    image = Image.new("RGB", (width, height), (16, 13, 11))
    draw = ImageDraw.Draw(image)
    draw.rectangle([24, 24, width - 25, height - 25], outline=(230, 194, 122), width=2)
    kicker_font = _font(max(18, width // 28))
    body_font = _font(max(22, width // 28))
    draw.text((48, 48), heading, font=kicker_font, fill=(230, 194, 122))
    y = 48 + kicker_font.size + 24
    for line in _wrap(draw, body or "Cảnh này chưa có ảnh.", body_font, width - 96, 5):
        draw.text((48, y), line, font=body_font, fill=(246, 241, 231))
        y += int(body_font.size * 1.4)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, quality=90)


def create_scene_image(
    folder: Path,
    index: int,
    prompt: str,
    style: str,
    lock: str,
    aspect: str,
    seed: int,
    fallback_text: str,
) -> dict:
    width, height = GEN_SIZE.get(aspect, GEN_SIZE["16:9"])
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"scene_{index:02d}.jpg"
    final_prompt = craft_visual_prompt(prompt, style, lock, motion=False)
    url = (
        "https://image.pollinations.ai/prompt/"
        + urllib.parse.quote(final_prompt)
        + f"?width={width}&height={height}&nologo=true&model=flux&seed={int(seed) % 1_000_000}"
    )
    last_error = "không rõ"
    for attempt in range(3):
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(request, timeout=100) as response:
                data = response.read()
            image = Image.open(io.BytesIO(data))
            image.load()
            grade(image).save(dest, quality=90)
            return {"file": dest.name, "placeholder": False}
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < 2:
                time.sleep(2 + attempt * 2)
    print(f"Ảnh cảnh {index} lỗi: {last_error}", flush=True)
    write_placeholder(dest, width, height, f"Cảnh {index}", fallback_text or prompt)
    return {"file": dest.name, "placeholder": True, "error": last_error}
