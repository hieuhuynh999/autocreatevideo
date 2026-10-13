"""Tạo ảnh storyboard cho từng cảnh."""

from __future__ import annotations

import io
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from studio.adapters.pollinations import edit_image, key_ready
from studio.specs import GEN_SIZE, craft_visual_prompt

FOLLOW = (
    "Edit this picture. Keep the exact same animals, colors, clothes, sizes and the same garden background. "
    "Do not add or remove animals. Keep every animal fully inside the frame. Change only the action: "
)

FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
_IMAGE_LOCK = threading.Lock()
_LAST_IMAGE = 0.0
IMAGE_GAP = 42


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


def _download_image(prompt: str, dest: Path, seed: int, width: int, height: int) -> str | None:
    """Tải một ảnh. Trả về None nếu thành công. Người gọi phải giữ khóa."""
    global _LAST_IMAGE
    last_error = "không rõ"
    for attempt in range(3):
        gap = IMAGE_GAP - (time.time() - _LAST_IMAGE)
        if _LAST_IMAGE and gap > 0:
            time.sleep(gap)
        url = (
            "https://image.pollinations.ai/prompt/"
            + urllib.parse.quote(prompt)
            + f"?width={width}&height={height}&nologo=true&model=flux&seed={(int(seed) + attempt) % 1_000_000}"
        )
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(request, timeout=100) as response:
                data = response.read()
            image = Image.open(io.BytesIO(data))
            image.load()
            if image.width < 64 or image.height < 64:
                raise ValueError("ảnh quá nhỏ")
            grade(image).save(dest, quality=92)
            _LAST_IMAGE = time.time()
            return None
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            _LAST_IMAGE = time.time()
            if not isinstance(exc, urllib.error.HTTPError) or exc.code != 402:
                time.sleep(3)
    return last_error


def create_scene_image(
    folder: Path,
    index: int,
    prompt: str,
    style: str,
    lock: str,
    aspect: str,
    seed: int,
    fallback_text: str,
    pose_b: str = "",
    pose_c: str = "",
) -> dict:
    width, height = GEN_SIZE["9:16"]
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"scene_{index:02d}.jpg"
    for extra in (folder / f"scene_{index:02d}_b.jpg", folder / f"scene_{index:02d}_c.jpg"):
        if extra.exists():
            extra.unlink()
    master = folder / "scene_01.jpg"
    if index > 1:
        if not master.is_file():
            return {
                "file": dest.name,
                "placeholder": True,
                "error": "Hãy tạo ảnh cảnh 1 trước. Cảnh sau bám ảnh đó.",
                "needs_key": False,
                "followed": False,
                "motion": False,
            }
        if not key_ready():
            return {
                "file": dest.name,
                "placeholder": False,
                "error": "Cảnh sau cần khóa Pollinations để sửa từ ảnh cảnh 1, không vẽ nhân vật mới.",
                "needs_key": True,
                "followed": False,
                "motion": False,
            }
        try:
            print(f"Cảnh {index} đang bám ảnh cảnh 1.", flush=True)
            edit_image(master, FOLLOW + (prompt or fallback_text), dest)
        except Exception as exc:
            print(f"Ảnh cảnh {index} lỗi: {exc}", flush=True)
            return {
                "file": dest.name,
                "placeholder": not dest.is_file(),
                "error": str(exc),
                "needs_key": False,
                "followed": False,
                "motion": False,
            }
        return {"file": dest.name, "placeholder": False, "needs_key": False, "followed": True, "motion": False}
    if "photorealistic" in prompt.lower() or "3d animated" in prompt.lower():
        style = ""
    final_prompt = craft_visual_prompt(prompt, style, lock, motion=False)
    with _IMAGE_LOCK:
        error = _download_image(final_prompt, dest, seed, width, height)
        if error is None:
            return {"file": dest.name, "placeholder": False, "needs_key": False, "followed": False, "motion": False}
    print(f"Ảnh cảnh {index} lỗi: {error}", flush=True)
    write_placeholder(dest, width, height, f"Cảnh {index}", fallback_text or prompt)
    return {"file": dest.name, "placeholder": True, "error": error, "needs_key": False, "followed": False, "motion": False}
