"""Review sản phẩm từ ảnh người dùng tải lên. Không vẽ lại bằng model 3D."""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path

from PIL import Image

from studio.render import render_film
from studio.specs import ASPECTS, PHONE_ASPECT

WIDTH, HEIGHT = ASPECTS[PHONE_ASPECT]
MAX_PHOTOS = 6


def _sentences(text: str) -> list[str]:
    raw = " ".join((text or "").replace("\n", " ").split())
    parts = re.split(r"(?<=[\.!?。！？])\s+", raw)
    return [part.strip() for part in parts if part.strip()]


def _spread(lines: list[str], count: int) -> list[str]:
    if count < 1:
        return []
    if not lines:
        return ["Giới thiệu sản phẩm."] * count
    if len(lines) <= count:
        padded = lines + [""] * (count - len(lines))
        return padded
    groups: list[list[str]] = [[] for _ in range(count)]
    for index, line in enumerate(lines):
        groups[min(count - 1, index * count // len(lines))].append(line)
    return [" ".join(group).strip() for group in groups]


def _cover(blob: bytes, dest: Path) -> None:
    image = Image.open(io.BytesIO(blob))
    image = image.convert("RGB")
    scale = max(WIDTH / image.width, HEIGHT / image.height)
    resized = image.resize(
        (max(WIDTH, round(image.width * scale)), max(HEIGHT, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    left = max(0, (resized.width - WIDTH) // 2)
    top = max(0, (resized.height - HEIGHT) // 2)
    frame = resized.crop((left, top, left + WIDTH, top + HEIGHT))
    dest.parent.mkdir(parents=True, exist_ok=True)
    frame.save(dest, quality=92)


def _decode(item: str) -> bytes:
    text = str(item or "").strip()
    if "," in text and text.lower().startswith("data:"):
        text = text.split(",", 1)[1]
    try:
        blob = base64.b64decode(text, validate=False)
    except Exception as exc:
        raise ValueError("Ảnh tải lên không đọc được.") from exc
    if len(blob) < 80 or len(blob) > 4_000_000:
        raise ValueError("Mỗi ảnh cần nhỏ hơn 4 MB sau khi thu nhỏ.")
    return blob


def build_review(folder: Path, data: dict) -> dict:
    raw_images = data.get("images")
    if not isinstance(raw_images, list) or not raw_images:
        raise ValueError("Hãy tải ít nhất một ảnh sản phẩm.")
    photos = raw_images[:MAX_PHOTOS]
    for index, item in enumerate(photos, start=1):
        if not isinstance(item, str):
            raise ValueError("Ảnh tải lên không đúng định dạng.")
        _cover(_decode(item), folder / f"scene_{index:02d}.jpg")

    script = str(data.get("script") or data.get("overview") or "").strip()
    lines = _spread(_sentences(script), len(photos))
    title = str(data.get("title") or "Review sản phẩm")[:80]
    theme = " ".join(str(data.get("theme") or "").split()).strip()[:80] or "Review sản phẩm"
    overview = " ".join(str(data.get("overview") or script).split()).strip()[:500]
    scenes = []
    for index, line in enumerate(lines, start=1):
        spoken = line or overview or "Giới thiệu sản phẩm."
        scenes.append(
            {
                "index": index,
                "shot": f"Ảnh sản phẩm {index}",
                "action": spoken,
                "dialogue": spoken,
                "subtitle": spoken[:140],
                "line_en": "",
                "line_vi": spoken[:240],
                "image_prompt": "uploaded product photo, photorealistic, not 3D",
                "video_prompt": "",
                "duration": 8,
            }
        )
    payload = {
        "title": title,
        "logline": overview[:500],
        "theme": theme,
        "overview": overview,
        "lock": "",
        "style": "photorealistic product photo, real camera, not 3D, not cartoon",
        "aspect": PHONE_ASPECT,
        "ambient": False,
        "music": "none",
        "caption": "vi",
        "voice": True,
        "kids": False,
        "mode": "review",
        "frame": "caption",
        "scenes": scenes,
    }
    result = render_film(folder, payload)
    result["scenes"] = len(scenes)
    return result
