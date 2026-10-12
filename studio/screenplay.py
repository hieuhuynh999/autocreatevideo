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

KIDS_GENRE = "Trẻ em: vui chơi, học tiếng Anh"
KIDS_LOOK = (
    "3D animated movie character, Pixar-like, big friendly eyes, colorful, "
    "soft daylight, bright playground, wholesome child fully clothed, "
    "not a photograph, not a real person, full body, centered, no text, no letters"
)
# Hai tư thế cùng khung hình. Video đổi qua lại để thấy động tác.
KIDS_MOVES = {
    "Hello!": ("3D child standing, both arms down", "3D child waving the right hand high, big smile"),
    "Let's play!": ("3D child holding a colorful ball at the waist", "3D child tossing a colorful ball up with both hands"),
    "Clap your hands!": ("3D child with both hands open and apart", "3D child clapping, palms pressed together"),
    "Jump!": ("3D child crouched, knees bent", "3D child jumping, both feet off the ground, arms up"),
    "Run!": ("3D child running, left foot forward", "3D child running, right foot forward"),
    "Let's sing!": ("3D child standing, mouth closed", "3D child singing, mouth open, one hand on the chest"),
    "One, two, three!": ("3D child holding up one finger", "3D child holding up three fingers"),
    "It is red.": ("3D child pointing at a red ball", "3D child lifting a bright red ball"),
    "It is blue.": ("3D child pointing at a blue ball", "3D child lifting a bright blue ball"),
    "It is yellow.": ("3D child pointing at a yellow flower", "3D child holding a yellow flower up"),
    "A ball.": ("3D child standing beside a colorful ball", "3D child with one foot lifted toward the ball"),
    "A cat.": ("3D child sitting beside a cute stylized cat", "3D child gently petting the cat"),
    "A dog.": ("3D child sitting beside a cute stylized puppy", "3D child hugging the puppy"),
    "A book.": ("3D child holding a closed picture book", "3D child opening the picture book"),
    "Thank you!": ("3D child holding a toy with both hands", "3D child handing the toy forward"),
    "Goodbye!": ("3D child standing, one arm down", "3D child waving goodbye"),
    "Look!": ("3D child looking forward", "3D child pointing at a flower"),
    "I can do it!": ("3D child with fists near the waist", "3D child raising both fists, proud smile"),
}
KIDS_LOCK = (
    "the same 3D animated child, about 7, round face, big eyes, red t-shirt, blue shorts, "
    "white sneakers, fully clothed, same face and clothes in every shot"
)
KIDS_BEATS = [
    ("Sân chơi", "wide shot of a bright playground"),
    ("Cùng chơi", "medium shot of children playing one game"),
    ("Chỉ vật", "close-up of one colorful toy or object"),
    ("Làm động tác", "a child doing one clear playful action"),
    ("Nói từ", "friendly close-up while a child speaks one English word"),
    ("Tạm biệt", "wide shot of children waving goodbye"),
]
# Cụm dài đứng trước để "màu đỏ" khớp trước "đỏ".
KIDS_WORDS = [
    ("xin chào", "Hello!", "Xin chào"),
    ("tạm biệt", "Goodbye!", "Tạm biệt"),
    ("cảm ơn", "Thank you!", "Cảm ơn"),
    ("vỗ tay", "Clap your hands!", "Vỗ tay"),
    ("cùng chơi", "Let's play!", "Cùng chơi"),
    ("màu đỏ", "It is red.", "Màu đỏ"),
    ("màu xanh", "It is blue.", "Màu xanh"),
    ("màu vàng", "It is yellow.", "Màu vàng"),
    ("quả bóng", "A ball.", "Quả bóng"),
    ("con mèo", "A cat.", "Con mèo"),
    ("con chó", "A dog.", "Con chó"),
    ("chơi", "Let's play!", "Cùng chơi"),
    ("nhảy", "Jump!", "Nhảy"),
    ("chạy", "Run!", "Chạy"),
    ("hát", "Let's sing!", "Cùng hát"),
    ("đếm", "One, two, three!", "Đếm một, hai, ba"),
    ("sách", "A book.", "Quyển sách"),
]
KIDS_DEFAULT = [
    ("Hello!", "Xin chào"),
    ("Let's play!", "Cùng chơi nào"),
    ("Look!", "Nhìn này"),
    ("I can do it!", "Mình làm được"),
    ("Thank you!", "Cảm ơn"),
    ("Goodbye!", "Tạm biệt"),
]


def clean_idea(idea: str) -> str:
    text = re.sub(r"\s+", " ", idea or "").strip()
    text = "".join(ch for ch in text if ch >= " " or ch == " ")
    return text[:700]


def _scene(
    shot: str,
    action: str,
    dialogue: str,
    subtitle: str,
    image_prompt: str,
    video_prompt: str,
    pose_b: str = "",
) -> dict:
    scene = {
        "shot": shot[:80],
        "action": action[:400],
        "dialogue": dialogue[:300],
        "subtitle": subtitle[:120],
        "image_prompt": image_prompt[:500],
        "video_prompt": video_prompt[:500],
    }
    if pose_b:
        scene["pose_b"] = pose_b[:500]
    return scene


def _sentences(idea: str) -> list[str]:
    parts = re.split(r"(?<=[.!?…])\s+", idea.strip())
    parts = [part.strip() for part in parts if len(part.strip()) > 8]
    if parts:
        return parts
    chunks = [part.strip() for part in re.split(r"[,;]", idea) if len(part.strip()) > 8]
    return chunks or [idea.strip()]


def _kids_lesson(sentence: str, index: int) -> tuple[str, str]:
    lowered = sentence.lower()
    found = []
    for key, english, vietnamese in KIDS_WORDS:
        position = lowered.find(key)
        if position >= 0:
            found.append((len(key), position, english, vietnamese))
    if found:
        found.sort(key=lambda item: (-item[0], item[1]))
        _, _, english, vietnamese = found[0]
        return english, vietnamese
    english, vietnamese = KIDS_DEFAULT[index % len(KIDS_DEFAULT)]
    return english, vietnamese


def _kids_screenplay(idea: str, n: int, style: str, lock: str) -> dict:
    sentences = _sentences(idea)
    if len(sentences) > n:
        sentences = sentences[: n - 1] + [" ".join(sentences[n - 1 :])]
    while len(sentences) < n:
        sentences.append("Các bạn vẫy tay tạm biệt.")
    scenes = []
    for index, sentence in enumerate(sentences[:n]):
        shot, _image_en = KIDS_BEATS[min(index, len(KIDS_BEATS) - 1)]
        english, vietnamese = _kids_lesson(sentence, index)
        rest, peak = KIDS_MOVES.get(english, KIDS_MOVES["Hello!"])
        image_prompt = f"{peak}. {KIDS_LOOK}"
        pose_b = f"{rest}. {KIDS_LOOK}"
        video_prompt = f"3D animated child repeats this action: {peak}. no text, no letters"
        scenes.append(
            _scene(
                shot,
                f"{sentence} Các bạn nói to: {english}",
                english,
                f"{english} — {vietnamese}",
                image_prompt,
                video_prompt,
                pose_b,
            )
        )
    return {
        "title": "Cùng chơi tiếng Anh",
        "logline": idea[:240],
        "character_lock": lock or KIDS_LOCK,
        "scenes": scenes,
        "source": "local",
    }


def write_screenplay(idea: str, genre: str, n: int, style: str, lock: str) -> dict:
    """Giữ nguyên câu người dùng viết. Mỗi câu là một cảnh."""
    idea = clean_idea(idea)
    genre = (genre or "Đời thường").strip()[:80]
    style = (style or "35mm cinematic film still").strip()[:160]
    lock = " ".join((lock or "").split()).strip()[:300]
    n = max(3, min(6, int(n)))
    if genre.startswith("Trẻ em"):
        return _kids_screenplay(idea, n, style, lock)
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
