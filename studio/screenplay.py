"""Chia một ý tưởng thành các cảnh phim ngắn."""

from __future__ import annotations

import re

BEATS = [
    ("Toàn cảnh", "wide establishing shot, the place before the person"),
    ("Trung cảnh", "medium shot, the lead in the middle of an ordinary action"),
    ("Cận chi tiết", "close-up of one object or a pair of hands"),
    ("Bước ngoặt", "the moment something unexpected enters the frame"),
    ("Cận mặt", "close-up on the face as the feeling changes"),
    ("Hình cuối", "lingering wide shot, the last image of the film"),
]


def clean_idea(idea: str) -> str:
    text = re.sub(r"\s+", " ", idea or "").strip()
    text = "".join(ch for ch in text if ch >= " " or ch == " ")
    return text[:700]


def _scene(shot: str, action: str, dialogue: str, subtitle: str, image_prompt: str, video_prompt: str) -> dict:
    return {
        "shot": shot[:80],
        "action": action[:400],
        "dialogue": dialogue[:300],
        "subtitle": subtitle[:120],
        "image_prompt": image_prompt[:500],
        "video_prompt": video_prompt[:500],
    }


def _sentences(idea: str) -> list[str]:
    parts = re.split(r"(?<=[.!?…])\s+", idea.strip())
    parts = [part.strip() for part in parts if len(part.strip()) > 8]
    if parts:
        return parts
    chunks = [part.strip() for part in re.split(r"[,;]", idea) if len(part.strip()) > 8]
    return chunks or [idea.strip()]


def write_screenplay(idea: str, genre: str, n: int, style: str, lock: str) -> dict:
    """Giữ nguyên câu người dùng viết. Mỗi câu là một cảnh."""
    idea = clean_idea(idea)
    genre = (genre or "Đời thường").strip()[:40]
    style = (style or "35mm cinematic film still").strip()[:160]
    lock = " ".join((lock or "").split()).strip()[:300]
    n = max(3, min(6, int(n)))
    sentences = _sentences(idea)
    if len(sentences) > n:
        sentences = sentences[: n - 1] + [" ".join(sentences[n - 1 :])]
    while len(sentences) < n:
        sentences.append("Giữ nguyên hình vừa rồi. Không thêm sự kiện mới.")

    scenes = []
    for index, sentence in enumerate(sentences[:n]):
        shot, image_en = BEATS[min(index, len(BEATS) - 1)]
        image_prompt = f"{image_en}, {style}, {genre} short film, moment: {sentence[:180]}"
        video_prompt = f"slow camera move, one physical action, {image_en}, {style}, moment: {sentence[:160]}"
        scenes.append(_scene(shot, sentence, "", sentence[:110], image_prompt, video_prompt))

    title = sentences[0][:42].rstrip("., ")
    if len(sentences[0]) > 42:
        title += "…"
    return {
        "title": title or "Phim ngắn",
        "logline": idea[:240],
        "character_lock": lock or "the same adult lead, consistent face, hair, and clothes in every shot",
        "scenes": scenes,
        "source": "local",
    }
