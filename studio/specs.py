"""Khổ hình và câu prompt dùng chung."""

# Khung đăng TikTok, Facebook Reels và YouTube Shorts. Mọi lần xuất đều dùng cỡ này.
PHONE_ASPECT = "9:16"

ASPECTS = {
    "16:9": (1280, 720),
    "9:16": (1080, 1920),
    "1:1": (720, 720),
}

# Ảnh gốc hơi nhỏ hơn khung xuất, phần dựng phóng lên cho lia máy mượt.
GEN_SIZE = {
    "16:9": (1280, 720),
    "9:16": (576, 1024),
    "1:1": (768, 768),
}

MAX_SCENES = 8
MIN_SECONDS = 4
MAX_SECONDS = 12


def craft_visual_prompt(base: str, style: str, lock: str, *, motion: bool) -> str:
    """Ghép prompt người dùng với phong cách và khóa nhân vật."""
    parts: list[str] = []
    for piece in (base, style):
        text = " ".join((piece or "").split()).strip(" .")
        if text and text.lower() not in " ".join(parts).lower():
            parts.append(text)
    if lock:
        line = " ".join(lock.split()).strip(" .")
        blob = " ".join(parts).lower()
        if line and line.lower() not in blob:
            parts.append("consistent character: " + line)
    blob = " ".join(parts).lower()
    if motion:
        parts.append("continuous camera move, no subtitles, no text, no logo")
    elif "3d animated" in blob or "not a photograph" in blob:
        parts.append("3D animated movie frame, expressive pose, no text, no letters, no logo, no watermark")
    else:
        parts.append(
            "photorealistic RAW photo, sharp detailed faces, natural light, "
            "no text, no letters, no subtitles, no logo, no watermark"
        )
    return ". ".join(parts)
