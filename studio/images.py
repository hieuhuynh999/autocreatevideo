"""Tạo ảnh storyboard cho từng cảnh."""

from __future__ import annotations

import io
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from studio.adapters.gemini import generate_image
from studio.adapters.gemini import key_ready as gemini_ready
from studio.adapters.pollinations import key_ready, upload_image
from studio.specs import GEN_SIZE

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


def _wait_gap() -> None:
    global _LAST_IMAGE
    gap = IMAGE_GAP - (time.time() - _LAST_IMAGE)
    if _LAST_IMAGE and gap > 0:
        time.sleep(gap)


def _image_url(prompt: str, seed: int, width: int, height: int, model: str, image_url: str = "") -> str:
    query = {
        "width": str(width),
        "height": str(height),
        "nologo": "true",
        "model": model,
        "seed": str(seed % 1_000_000),
    }
    if image_url:
        query["image"] = image_url
    return "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt[:700]) + "?" + urllib.parse.urlencode(query)


def _fetch_image(url: str, dest: Path) -> str | None:
    """Tải một ảnh. Trả về None nếu thành công."""
    global _LAST_IMAGE
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
            kind = response.headers.get("Content-Type") or ""
        if "json" in kind or data[:1] in (b"{", b"[") or len(data) < 1000:
            raise RuntimeError(data.decode("utf-8", "replace")[:180] or "Không nhận được ảnh.")
        image = Image.open(io.BytesIO(data))
        image.load()
        if image.width < 64 or image.height < 64:
            raise ValueError("ảnh quá nhỏ")
        grade(image).save(dest, quality=92)
        _LAST_IMAGE = time.time()
        return None
    except Exception as exc:
        _LAST_IMAGE = time.time()
        return f"{type(exc).__name__}: {exc}"


def _download_image(
    prompt: str,
    dest: Path,
    seed: int,
    width: int,
    height: int,
    reference: Path | None = None,
) -> tuple[str | None, bool]:
    """Vẽ bằng Flux miễn phí. Có ảnh trước thì cảnh này bám ảnh đó, không tốn pollen."""
    followed = False
    last_error = "không rõ"
    if reference and reference.is_file() and key_ready():
        _wait_gap()
        try:
            hosted = upload_image(reference)
        except Exception as exc:
            print(f"Chưa đưa được ảnh trước lên: {exc}", flush=True)
            hosted = ""
        if hosted:
            follow = (
                "Next shot of the same 3D kids film. Keep the same faces, hair, clothes, colors, "
                "body sizes and the same place. Change only the pose to this action: "
                + prompt[:500]
            )
            error = _fetch_image(_image_url(follow, seed, width, height, "klein", hosted), dest)
            if error is None:
                return None, True
            print(f"Flux Klein chưa bám ảnh trước: {error}", flush=True)
            last_error = error
    for attempt in range(3):
        _wait_gap()
        error = _fetch_image(
            _image_url(prompt, seed + attempt, width, height, "flux"),
            dest,
        )
        if error is None:
            return None, followed
        last_error = error
        if "402" not in error:
            time.sleep(3)
    return last_error, False


def _wants_3d(*parts: str) -> bool:
    blob = " ".join(parts).lower()
    return "3d animated" in blob or "not a photograph" in blob


def _scene_action(prompt: str, fallback: str) -> str:
    text = prompt or ""
    found = None
    for label in ("this new shot:", "scene:", "moment:"):
        found = re.search(re.escape(label), text, re.IGNORECASE)
        if found:
            break
    if found:
        text = text[found.end() :]
    else:
        text = fallback or text
    text = re.split(r",?\s*nói\s+", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = re.sub(r",?\s*máy\s+[^,\.]+", "", text, flags=re.IGNORECASE)
    return " ".join(text.split()).strip(" .")


def _to_english(text: str) -> str:
    if not text or not re.search(r"[àáạảãâăêôơưđ]", text, re.IGNORECASE):
        return text
    query = urllib.parse.urlencode({"client": "gtx", "sl": "vi", "tl": "en", "dt": "t", "q": text[:400]})
    request = urllib.request.Request(
        "https://translate.googleapis.com/translate_a/single?" + query,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        parts = [str(block[0]) for block in (payload[0] or []) if block and block[0]]
        return " ".join(parts).strip() or text
    except Exception:
        return text


def _is_filler(text: str) -> bool:
    lowered = (text or "").lower()
    return (
        "keep the previous image" in lowered
        or "do not add new events" in lowered
        or "giữ nguyên hình" in lowered
    )


def _previous_action(folder: Path, index: int) -> str:
    path = folder / "kich-ban.json"
    if not path.is_file() or index < 2:
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    scenes = data.get("scenes") or []
    slot = index - 2
    if slot < 0 or slot >= len(scenes):
        return ""
    previous = _scene_action(str(scenes[slot].get("action") or ""), "")
    if _is_filler(previous):
        return ""
    return previous[:240]


def _flux_scene(
    folder_dest: Path,
    prompt: str,
    seed: int,
    width: int,
    height: int,
    fallback: str,
    reference: Path | None = None,
) -> dict:
    with _IMAGE_LOCK:
        error, followed = _download_image(prompt, folder_dest, seed, width, height, reference)
    if error is None:
        return {
            "file": folder_dest.name,
            "placeholder": False,
            "needs_key": False,
            "followed": followed,
            "motion": False,
            "note": "Flux miễn phí, vẽ theo câu mô tả tiếng Anh.",
        }
    print(f"Ảnh lỗi: {error}", flush=True)
    write_placeholder(folder_dest, width, height, "Cảnh", fallback or prompt)
    return {
        "file": folder_dest.name,
        "placeholder": True,
        "error": error,
        "needs_key": False,
        "followed": False,
        "motion": False,
    }


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
    reset: bool = False,
) -> dict:
    width, height = GEN_SIZE["9:16"]
    folder.mkdir(parents=True, exist_ok=True)
    if reset and index == 1:
        for old in folder.glob("scene_*.jpg"):
            old.unlink()
    dest = folder / f"scene_{index:02d}.jpg"
    for extra in (folder / f"scene_{index:02d}_b.jpg", folder / f"scene_{index:02d}_c.jpg"):
        if extra.exists():
            extra.unlink()
    action = _to_english(_scene_action(prompt, fallback_text))
    if _is_filler(action):
        return {
            "file": dest.name,
            "placeholder": True,
            "error": "Cảnh này chưa có hành động riêng. Bấm Tạo storyboard lại, rồi tạo ảnh.",
            "needs_key": False,
            "followed": False,
            "motion": False,
        }
    previous = _previous_action(folder, index) if index > 1 else ""
    reference = folder / f"scene_{index - 1:02d}.jpg" if index > 1 else None
    if index > 1 and (reference is None or not reference.is_file()):
        return {
            "file": dest.name,
            "placeholder": True,
            "error": f"Hãy tạo ảnh cảnh {index - 1} trước. Cảnh này bám ảnh đó.",
            "needs_key": False,
            "followed": False,
            "motion": False,
        }
    if _wants_3d(prompt, style, lock):
        head = "3D animated kids movie frame, not a photograph, no text, no letters, no logo."
    else:
        head = "photorealistic film still, natural light, no text, no letters, no logo."
    parts = [head]
    if previous and previous.lower() not in action.lower():
        parts.append(f"Continue from the previous shot, which showed: {previous}.")
    parts.append(f"The picture must show this action: {action}.")
    if lock:
        parts.append(f"Use this exact same character design and place: {lock}")
    final_prompt = " ".join(parts)
    if not gemini_ready():
        return {
            "file": dest.name,
            "placeholder": True,
            "error": (
                "Chưa có khóa Gemini. Tạo tại aistudio.google.com/apikey, dán vào ô Khóa Gemini rồi bấm Lưu khóa. "
                "Model vẽ ảnh không miễn phí, khoảng 0,03 USD mỗi ảnh."
            ),
            "needs_key": True,
            "followed": False,
            "motion": False,
        }
    followed = bool(reference and reference.is_file())
    print(
        f"Cảnh {index} vẽ bằng Gemini" + (f", bám ảnh cảnh {index - 1}." if followed else "."),
        flush=True,
    )
    try:
        generate_image(final_prompt, dest, reference if followed else None)
        image = Image.open(dest)
        image.load()
        grade(image.convert("RGB")).save(dest, quality=92)
    except Exception as exc:
        print(f"Ảnh cảnh {index} lỗi: {exc}", flush=True)
        write_placeholder(dest, width, height, f"Cảnh {index}", fallback_text or action)
        return {
            "file": dest.name,
            "placeholder": True,
            "error": str(exc),
            "needs_key": False,
            "followed": False,
            "motion": False,
        }
    return {
        "file": dest.name,
        "placeholder": False,
        "needs_key": False,
        "followed": followed,
        "motion": False,
        "note": (
            f"Gemini. Cảnh này bám ảnh cảnh {index - 1}."
            if followed
            else "Gemini vẽ cảnh này theo kịch bản tiếng Việt đã dịch sang tiếng Anh."
        ),
    }
