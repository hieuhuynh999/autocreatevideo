"""Review sản phẩm: ảnh thật đặt lên nền, camera đi theo từng câu."""

from __future__ import annotations

import base64
import io
import re
import subprocess
from pathlib import Path

from PIL import Image

from studio.render import FFMPEG, render_film
from studio.specs import ASPECTS, PHONE_ASPECT

WIDTH, HEIGHT = ASPECTS[PHONE_ASPECT]
MAX_PHOTOS = 6
FPS = 30


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
        return lines + [""] * (count - len(lines))
    groups: list[list[str]] = [[] for _ in range(count)]
    for index, line in enumerate(lines):
        groups[min(count - 1, index * count // len(lines))].append(line)
    return [" ".join(group).strip() for group in groups]


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


def _open_rgb(blob: bytes) -> Image.Image:
    return Image.open(io.BytesIO(blob)).convert("RGB")


def _cover(image: Image.Image) -> Image.Image:
    scale = max(WIDTH / image.width, HEIGHT / image.height)
    resized = image.resize(
        (max(WIDTH, round(image.width * scale)), max(HEIGHT, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    left = max(0, (resized.width - WIDTH) // 2)
    top = max(0, (resized.height - HEIGHT) // 2)
    return resized.crop((left, top, left + WIDTH, top + HEIGHT))


def _cut_edge_white(image: Image.Image) -> Image.Image:
    """Bỏ nền trắng dính mép ảnh, giữ phần trắng nằm trong sản phẩm."""
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    seen = bytearray(width * height)
    stack: list[tuple[int, int]] = []

    def near_white(x: int, y: int) -> bool:
        red, green, blue, _alpha = pixels[x, y]
        return red > 236 and green > 236 and blue > 236

    for x in range(width):
        stack.append((x, 0))
        stack.append((x, height - 1))
    for y in range(height):
        stack.append((0, y))
        stack.append((width - 1, y))
    while stack:
        x, y = stack.pop()
        slot = y * width + x
        if seen[slot] or not near_white(x, y):
            continue
        seen[slot] = 1
        red, green, blue, _alpha = pixels[x, y]
        pixels[x, y] = (red, green, blue, 0)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height and not seen[ny * width + nx]:
                stack.append((nx, ny))
    return rgba


def _compose(product_blob: bytes, background_blob: bytes, dest: Path) -> None:
    frame = _cover(_open_rgb(background_blob)).convert("RGBA")
    product = _cut_edge_white(_open_rgb(product_blob))
    max_w = int(WIDTH * 0.82)
    max_h = int(HEIGHT * 0.7)
    scale = min(max_w / product.width, max_h / product.height)
    size = (max(2, round(product.width * scale)), max(2, round(product.height * scale)))
    product = product.resize(size, Image.Resampling.LANCZOS)
    x = (WIDTH - product.width) // 2
    y = (HEIGHT - product.height) // 2 + int(HEIGHT * 0.03)
    shade = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    silhouette = Image.new("RGBA", product.size, (0, 0, 0, 70))
    silhouette.putalpha(product.getchannel("A"))
    shade.paste(silhouette, (x + 14, y + 18), silhouette)
    frame.alpha_composite(shade)
    frame.alpha_composite(product, (x, y))
    dest.parent.mkdir(parents=True, exist_ok=True)
    frame.convert("RGB").save(dest, quality=92)


def _spoken_seconds(text: str) -> float:
    words = max(1, len(text.split()))
    return min(12.0, max(4.0, round(1.3 + words * 0.55, 2)))


def _camera_clip(image: Path, dest: Path, frames: int, move: str) -> None:
    """Video từ ảnh thật. Camera đi chậm, không vẽ lại sản phẩm."""
    last = max(frames - 1, 1)
    if move == "out":
        zoom, xpos, ypos = "if(eq(on,0),1.08,max(1.0,zoom-0.0008))", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif move == "right":
        zoom, xpos, ypos = "1.06", f"(iw-iw/zoom)*on/{last}", "(ih-ih/zoom)/2"
    else:
        zoom, xpos, ypos = "min(zoom+0.0008,1.08)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    process = subprocess.run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-framerate", str(FPS), "-i", str(image),
            "-vf",
            (
                f"zoompan=z='{zoom}':x='{xpos}':y='{ypos}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
                "format=yuv420p"
            ),
            "-frames:v", str(frames),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "18",
            str(dest),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode != 0 or not dest.is_file() or dest.stat().st_size < 1000:
        tail = (process.stderr or process.stdout or "Không tạo được video review.").strip()[-800:]
        raise RuntimeError(tail or "Không tạo được video review.")


def build_review(folder: Path, data: dict) -> dict:
    raw_images = data.get("images")
    if not isinstance(raw_images, list) or not raw_images:
        raise ValueError("Hãy tải ít nhất một ảnh sản phẩm.")
    background = data.get("background")
    if not isinstance(background, str) or not background.strip():
        raise ValueError("Hãy tải một ảnh nền.")
    background_blob = _decode(background)
    photos = raw_images[:MAX_PHOTOS]
    for index, item in enumerate(photos, start=1):
        if not isinstance(item, str):
            raise ValueError("Ảnh tải lên không đúng định dạng.")
        _compose(_decode(item), background_blob, folder / f"scene_{index:02d}.jpg")

    script = str(data.get("script") or data.get("overview") or "").strip()
    lines = _spread(_sentences(script), len(photos))
    title = str(data.get("title") or "Review sản phẩm")[:80]
    theme = " ".join(str(data.get("theme") or "").split()).strip()[:80] or "Review sản phẩm"
    overview = " ".join(str(data.get("overview") or script).split()).strip()[:500]
    moves = ("in", "right", "out")
    scenes = []
    for index, line in enumerate(lines, start=1):
        spoken = line or overview or "Giới thiệu sản phẩm."
        seconds = _spoken_seconds(spoken)
        frames = max(FPS * 4, int(round(seconds * FPS)))
        _camera_clip(
            folder / f"scene_{index:02d}.jpg",
            folder / f"scene_{index:02d}_motion.mp4",
            frames,
            moves[(index - 1) % len(moves)],
        )
        scenes.append(
            {
                "index": index,
                "shot": f"Ảnh sản phẩm {index}",
                "action": spoken,
                "dialogue": spoken,
                "subtitle": spoken[:140],
                "line_en": "",
                "line_vi": spoken[:240],
                "image_prompt": "real product photo on the uploaded background, not 3D",
                "video_prompt": (
                    "Photorealistic camera move over this real photo. "
                    f"The review line is: {spoken[:180]}"
                ),
                "duration": frames / FPS,
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
