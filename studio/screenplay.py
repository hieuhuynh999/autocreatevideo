"""Chia một ý tưởng thành các cảnh phim ngắn."""

from __future__ import annotations

import re

from studio.specs import MAX_SCENES

BEATS = [
    ("Toàn cảnh", "wide establishing shot, the place before the person"),
    ("Trung cảnh", "medium shot, the lead in the middle of an ordinary action"),
    ("Cận chi tiết", "close-up of one object or a pair of hands"),
    ("Bước ngoặt", "the moment something unexpected enters the frame"),
    ("Cận mặt", "close-up on the face as the feeling changes"),
    ("Hình cuối", "lingering wide shot, the last image of the film"),
]

KIDS_GENRES = {
    "Truyện giáo dục",
    "Học màu và số",
    "Khám phá động vật",
    "Kỹ năng sống",
    "Phiêu lưu nhẹ",
    "Bài hát thiếu nhi",
    "Học tiếng Anh",
    "Trẻ em: vui chơi, học tiếng Anh",
}
LAYOUTS = {
    "Truyện kể": ["Mở đầu", "Gặp việc", "Hành động", "Giải quyết", "Bài học", "Kết"],
    "Học khái niệm": ["Giới thiệu", "Ví dụ", "Câu hỏi", "Suy nghĩ", "Đáp án", "Nhắc lại"],
    "Khám phá": ["Dẫn đường", "Địa điểm", "Phát hiện", "Tổng kết", "Chia sẻ", "Tạm biệt"],
    "Bài hát": ["Mở đầu", "Đoạn hát", "Điệp khúc", "Đoạn tiếp", "Điệp khúc", "Kết"],
}
CAMERAS = [
    "toàn cảnh, máy tiến nhẹ",
    "trung cảnh, máy cố định",
    "cận tay và vật",
    "trung cảnh",
    "toàn cảnh",
    "máy lia từ vật sang bạn nhỏ",
]
LICENSE = {
    "name": "Liên khúc thiếu nhi dân gian",
    "works": ["Twinkle Twinkle Little Star", "Mary Had a Little Lamb", "Frère Jacques"],
    "terms": (
        "Ba giai điệu thuộc phạm vi công cộng. Tool tự đánh nhạc, không dùng bản thu của ca sĩ. "
        "Được đưa vào video đã xuất. Không cam kết hệ thống nhận diện nhạc sẽ im lặng."
    ),
}
KIDS_LOOK = (
    "3D animated, Pixar-like, same child, yellow t-shirt, blue shorts, white sneakers, "
    "fully clothed, soft daylight, not a photograph, no text, no letters"
)
SHOTS = {
    "faucet": (
        "wide bathroom shot, the child stands at a white sink and reaches for a silver faucet",
        "close-up of two small hands turning the silver faucet, water starts pouring into the sink",
        "side angle, water flows from the faucet onto both open palms in the sink",
    ),
    "wash": (
        "medium shot, the child holds a white bar of soap above the bathroom sink",
        "close-up of two small hands rubbing together with thick soap bubbles between the palms",
        "three-quarter angle, the child rubs soapy hands in circles, bubbles on the fingers",
    ),
    "rinse": (
        "medium shot from the left, both soapy hands move under the running faucet",
        "close-up of clear water rinsing soap off two small palms into the sink",
        "front shot, the child lifts two clean wet hands, water dripping from the fingers",
    ),
    "towel": (
        "medium shot, the child picks up a small white towel beside the sink",
        "close-up of two hands wiping dry on the white towel",
        "front shot, the child holds both clean dry hands up toward the camera",
    ),
    "Clap your hands!": (
        "wide shot, the child stands with both hands open and apart",
        "close-up of two palms clapping together",
        "side angle, the child claps again and smiles",
    ),
    "wave": (
        "wide shot, the child stands with both arms down",
        "medium shot, the child raises the right hand and waves",
        "closer front angle, the waving hand moves near the face, big smile",
    ),
    "Hello!": (
        "wide playground shot, the child stands and looks at the camera",
        "medium shot, the child waves the right hand hello",
        "side angle, the wave continues, the other arm stays down",
    ),
    "Jump!": (
        "wide shot, the child bends both knees on the grass",
        "low angle, both feet leave the ground, arms up",
        "side angle, the child lands on both feet",
    ),
}
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
    "wash": ("3D child standing at a sink, hands down", "3D child rubbing both hands together with soap bubbles"),
    "faucet": ("3D child reaching toward a faucet", "3D child with both hands under a running faucet"),
    "rinse": ("3D child with soapy hands under water", "3D child holding up two clean hands"),
    "towel": ("3D child holding a small towel", "3D child drying both hands on the towel"),
    "wave": ("3D child standing, both arms down", "3D child waving one hand, big smile"),
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
ACTION_WORDS = [
    ("xà phòng", "wash"),
    ("rửa sạch", "rinse"),
    ("rửa tay", "wash"),
    ("vòi nước", "faucet"),
    ("mở vòi", "faucet"),
    ("lau khô", "towel"),
    ("lau tay", "towel"),
    ("vỗ tay", "Clap your hands!"),
    ("xin chào", "Hello!"),
    ("tạm biệt", "Goodbye!"),
    ("cảm ơn", "Thank you!"),
    ("cùng chơi", "Let's play!"),
    ("màu đỏ", "It is red."),
    ("màu xanh", "It is blue."),
    ("màu vàng", "It is yellow."),
    ("quả bóng", "A ball."),
    ("con mèo", "A cat."),
    ("con chó", "A dog."),
    ("nhảy", "Jump!"),
    ("chạy", "Run!"),
    ("hát", "Let's sing!"),
    ("đếm", "One, two, three!"),
    ("vẫy", "wave"),
]


def clean_idea(idea: str) -> str:
    lines = []
    for raw in (idea or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = " ".join(raw.split()).strip()
        line = "".join(ch for ch in line if ch >= " ")
        if line:
            lines.append(line)
    return "\n".join(lines)[:4000]


def _scene(
    shot: str,
    action: str,
    dialogue: str,
    subtitle: str,
    image_prompt: str,
    video_prompt: str,
    pose_b: str = "",
    pose_c: str = "",
    camera: str = "",
    goal: str = "",
    continuity: str = "",
) -> dict:
    scene = {
        "shot": shot[:80],
        "action": action[:400],
        "dialogue": dialogue[:300],
        "subtitle": subtitle[:140],
        "image_prompt": image_prompt[:500],
        "video_prompt": video_prompt[:500],
    }
    if pose_b:
        scene["pose_b"] = pose_b[:500]
    if pose_c:
        scene["pose_c"] = pose_c[:500]
    if camera:
        scene["camera"] = camera[:160]
    if goal:
        scene["goal"] = goal[:240]
    if continuity:
        scene["continuity"] = continuity[:240]
    return scene


def _camera_hint(text: str) -> str:
    lowered = text.lower()
    if "lùi" in lowered:
        return "The camera pulls back slightly"
    if "tiến" in lowered:
        return "The camera moves in slightly"
    if "cận" in lowered:
        return "Medium close-up"
    if "ngang tầm" in lowered:
        return "Camera at the characters' eye level"
    if "trung cảnh" in lowered:
        return "Medium shot"
    return ""


_FILLER_RE = re.compile(
    r"(giữ nguyên hình vừa rồi|không thêm sự kiện mới|keep the previous image|do not add new events)",
    re.IGNORECASE,
)
_CAMERA_MARKS = (
    "the camera pulls back slightly",
    "the camera moves in slightly",
    "camera at the characters' eye level",
    "medium close-up",
    "medium shot",
)


def _is_filler(text: str) -> bool:
    stripped = _FILLER_RE.sub("", text or "")
    return len(stripped.strip(" .,")) < 8


_DRAW_RE = re.compile(r"^(?:vẽ|ve|hình)\s*:\s*(.+)$", re.IGNORECASE)
_SAY_RE = re.compile(r"^(?:đọc|doc|lồng tiếng|long tieng|thoại|thoai)\s*:\s*(.+)$", re.IGNORECASE)


def _spoken_pair(text: str) -> tuple[str, str]:
    """Tách lời lồng tiếng. Phần trước gạch ngang là tiếng Anh, phần sau là tiếng Việt."""
    raw = (text or "").replace("“", "").replace("”", "").replace('"', "").replace("'", "")
    raw = re.sub(r"nghĩa tiếng Việt\s*:\s*", "", raw, flags=re.IGNORECASE)
    raw = " ".join(raw.replace("–", "—").split()).strip(" .")
    if "—" in raw:
        english, _, vietnamese = raw.partition("—")
        return english.strip(" ."), vietnamese.strip(" .")
    return raw.strip(" ."), ""


def _marked_scenes(idea: str) -> list[tuple[str, str]]:
    """Mỗi cảnh là một khối Vẽ + Đọc. Không cắt đôi câu ở giữa."""
    if not re.search(r"(?m)^(?:vẽ|ve|hình)\s*:", idea or "", re.IGNORECASE):
        return []
    scenes: list[tuple[str, str]] = []
    draw = ""
    say = ""

    def flush() -> None:
        nonlocal draw, say
        if draw or say:
            scenes.append((draw.strip(" ."), say.strip()))
        draw = ""
        say = ""

    for raw in (idea or "").replace("\r\n", "\n").split("\n"):
        line = " ".join(raw.split()).strip()
        if not line:
            flush()
            continue
        if "|" in line and re.search(r"(?:đọc|doc|lồng tiếng)\s*:", line, re.IGNORECASE):
            left, right = line.split("|", 1)
            draw_match = _DRAW_RE.match(left.strip())
            say_match = _SAY_RE.match(right.strip())
            if draw or say:
                flush()
            draw = draw_match.group(1) if draw_match else left.strip()
            say = say_match.group(1) if say_match else right.strip()
            flush()
            continue
        draw_match = _DRAW_RE.match(line)
        say_match = _SAY_RE.match(line)
        if draw_match:
            if draw or say:
                flush()
            draw = draw_match.group(1)
        elif say_match and draw:
            say = say_match.group(1)
        elif draw and not say:
            draw = f"{draw} {line}".strip()
        else:
            return []
    flush()
    return [(item_draw, item_say) for item_draw, item_say in scenes if item_draw or item_say]


def _sentences(idea: str) -> list[str]:
    """Mỗi dòng là một cảnh. Đoạn bị dính lại thì tách theo câu máy quay."""
    lines = [line.strip() for line in (idea or "").replace("\r\n", "\n").split("\n")]
    lines = [line for line in lines if line and not _is_filler(line)]
    if len(lines) > 1:
        return lines
    text = _FILLER_RE.sub(" ", lines[0] if lines else "")
    text = " ".join(text.split()).strip()
    mark = "|".join(re.escape(item) for item in _CAMERA_MARKS)
    if text and re.search(mark, text, re.IGNORECASE):
        pieces = re.split(f"({mark})", text, flags=re.IGNORECASE)
        scenes: list[str] = []
        buffer = ""
        for piece in pieces:
            bit = piece.strip()
            if not bit:
                continue
            if re.fullmatch(mark, bit, flags=re.IGNORECASE):
                buffer = f"{buffer} {bit}".strip()
                scenes.append(buffer)
                buffer = ""
            elif buffer:
                scenes.append(buffer)
                buffer = bit
            else:
                buffer = bit
        if buffer:
            scenes.append(buffer)
        scenes = [item for item in scenes if len(item) > 8 and not _is_filler(item)]
        if len(scenes) > 1:
            return scenes
    parts = [part.strip() for part in re.split(r"(?<=[.!?…])\s+", text) if len(part.strip()) > 8]
    parts = [part for part in parts if not _is_filler(part)]
    if parts:
        return parts
    return [text] if text else []


def _split_once(text: str) -> list[str]:
    for pattern in (r"(?<=[.!?…])\s+", r",\s+", r"\s+and\s+", r"\s+và\s+"):
        bits = [bit.strip(" .") for bit in re.split(pattern, text, maxsplit=1) if bit.strip(" .")]
        if len(bits) == 2 and min(len(bit) for bit in bits) > 12:
            return bits
    words = text.split()
    if len(words) >= 12:
        middle = len(words) // 2
        return [" ".join(words[:middle]), " ".join(words[middle:])]
    return [text]


def _fit_count(sentences: list[str], n: int) -> list[str]:
    """Luôn ra đúng số cảnh đã chọn."""
    pieces = [item.strip() for item in sentences if item and item.strip()]
    if not pieces:
        return []
    if len(pieces) > n:
        width = len(pieces) / n
        grouped = []
        for index in range(n):
            start = round(index * width)
            end = round((index + 1) * width)
            grouped.append(" ".join(pieces[start:end]).strip())
        return [item for item in grouped if item]
    guard = 0
    while len(pieces) < n and guard < n * 3:
        guard += 1
        index = max(range(len(pieces)), key=lambda item: len(pieces[item]))
        bits = _split_once(pieces[index])
        if len(bits) < 2:
            break
        pieces[index : index + 1] = bits
    return pieces[:n]


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


def _angles(sentence: str, english: str, bilingual: bool) -> tuple[str, str, str]:
    move = english if bilingual else ""
    if not bilingual:
        lowered = sentence.lower()
        found = []
        for key, move_id in ACTION_WORDS:
            position = lowered.find(key)
            if position >= 0:
                found.append((len(key), position, move_id))
        if found:
            found.sort(key=lambda item: (-item[0], item[1]))
            move = found[0][2]
        else:
            move = "wave"
    if move in SHOTS:
        return SHOTS[move]
    _rest, peak = KIDS_MOVES.get(move, KIDS_MOVES["wave"])
    return (
        f"wide shot, {peak}",
        f"close-up of the hands doing this action, {peak}",
        f"side angle, {peak}",
    )


def _kids_screenplay(idea: str, n: int, style: str, lock: str, genre: str, layout: str, age: str) -> dict:
    del style
    bilingual = genre in {"Học tiếng Anh", "Trẻ em: vui chơi, học tiếng Anh"}
    labels = LAYOUTS.get(layout, LAYOUTS["Truyện kể"])
    sentences = _sentences(idea)
    if len(sentences) > n:
        sentences = sentences[: n - 1] + [" ".join(sentences[n - 1 :])]
    while len(sentences) < n:
        sentences.append("Bạn nhỏ vẫy tay tạm biệt.")
    scenes = []
    for index, sentence in enumerate(sentences[:n]):
        shot = labels[index % len(labels)]
        english, vietnamese = _kids_lesson(sentence, index)
        wide, close, side = _angles(sentence, english, bilingual)
        image_prompt = f"{close}. {KIDS_LOOK}"
        pose_b = f"{wide}. {KIDS_LOOK}"
        pose_c = f"{side}. {KIDS_LOOK}"
        video_prompt = f"Cut wide, then close-up of the action, then a side angle. {close}. No text."
        if bilingual:
            dialogue = english
            subtitle = f"{english} — {vietnamese}"
        else:
            dialogue = sentence
            subtitle = sentence[:110]
        previous = "Đầu câu chuyện." if index == 0 else f"Nối từ cảnh {index}: giữ áo vàng, quần xanh và vật vừa dùng."
        scenes.append(
            _scene(
                shot,
                f"Góc rộng: {wide}. Cận hành động: {close}. Góc nghiêng: {side}.",
                dialogue,
                subtitle,
                image_prompt,
                video_prompt,
                pose_b,
                pose_c,
                CAMERAS[index % len(CAMERAS)],
                sentence,
                previous,
            )
        )
    title = "Cùng chơi tiếng Anh" if bilingual else sentences[0][:42].rstrip("., ")
    return {
        "title": title or "Phim thiếu nhi",
        "logline": idea[:240],
        "character_lock": lock or KIDS_LOCK,
        "genre": genre,
        "layout": layout,
        "age": age,
        "license": LICENSE,
        "scenes": scenes,
        "source": "local",
    }


def write_screenplay(
    idea: str,
    genre: str,
    n: int,
    style: str,
    lock: str,
    layout: str = "Truyện kể",
    age: str = "3–5",
) -> dict:
    """Giữ nguyên câu người dùng viết. Mỗi câu là một cảnh."""
    idea = clean_idea(idea)
    genre = (genre or "Kỹ năng sống").strip()[:80]
    style = (style or "35mm cinematic film still").strip()[:160]
    lock = " ".join((lock or "").split()).strip()[:300]
    layout = layout if layout in LAYOUTS else "Truyện kể"
    age = age if age in {"3–5", "6–8"} else "3–5"
    n = max(3, min(MAX_SCENES, int(n)))
    if genre in KIDS_GENRES or genre.startswith("Trẻ em"):
        return _kids_screenplay(idea, n, style, lock, genre, layout, age)
    marked = _marked_scenes(idea)
    if marked:
        if len(marked) > n:
            marked = marked[:n]
        sentences = [draw for draw, _say in marked]
    else:
        sentences = _fit_count(_sentences(idea) or [idea.strip()], n)
    look = f"{style} {lock}".lower()
    kids_look = "3d animated" in look or "not a photograph" in look
    scenes = []
    for index, sentence in enumerate(sentences[:n]):
        shot, image_en = BEATS[min(index, len(BEATS) - 1)]
        if kids_look:
            from studio.images import _scene_action

            spoken = marked[index][1] if marked else ""
            if not spoken:
                match = re.search(r"nói\s+(.+)$", sentence, re.IGNORECASE)
                if match:
                    spoken = match.group(1).strip(" .")
            action_vi = sentence if marked else (_scene_action(sentence, sentence) or sentence)
            line_en, line_vi = _spoken_pair(spoken)
            image_prompt = (
                "3D animated kids movie frame, not a photograph, no text. "
                f"Scene: {action_vi[:360]}"
            )
            video_prompt = (
                "gentle camera move, one clear action, 3D animated kids movie, not a photograph. "
                f"Scene: {action_vi[:240]}"
            )
            scene = _scene(shot, action_vi[:400], "", line_en[:110] or action_vi[:110], image_prompt, video_prompt)
            if line_en or line_vi:
                scene["line_en"] = line_en[:240]
                scene["line_vi"] = line_vi[:240]
                scene["dialogue"] = f"{line_en} — {line_vi}".strip(" —")[:300]
            scenes.append(scene)
        else:
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
