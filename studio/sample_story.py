"""Dự án mẫu Ong Bông và Châu Chấu Lá. Nội dung mới, kết thúc thân thiện."""

from __future__ import annotations

LOOK = (
    "soft 3D animated, round friendly insect characters, big eyes, gentle garden light, "
    "fresh colors, not a photograph, no text, no letters"
)
BEE = "the same round bee, yellow and black stripes, tiny blue scarf, big friendly eyes"
HOPPER = "the same green grasshopper, leaf-green vest, big friendly eyes"

CHARACTERS = [
    {
        "id": "bee",
        "name": "Ong Bông",
        "look": "Ong tròn, sọc vàng đen, khăn xanh nhỏ, mắt to",
        "personality": "Ấm áp, hay giúp bạn",
        "voice": "en-US-AnaNeural",
        "lock": BEE,
    },
    {
        "id": "hopper",
        "name": "Châu Chấu Lá",
        "look": "Châu chấu xanh, áo lá, mắt to",
        "personality": "Hiền, hơi mệt lúc đầu rồi vui",
        "voice": "vi-VN-HoaiMyNeural",
        "lock": HOPPER,
    },
]


def _scene(
    shot: str,
    setting: str,
    start: str,
    actions: list[dict],
    end: str,
    camera: str,
    camera_move: str,
    props: str,
    lines: list[tuple[str, str, str]],
    image: str,
    duration: int = 5,
) -> dict:
    english = " / ".join(line[1] for line in lines)
    vietnamese = " / ".join(line[2] for line in lines)
    spoken = " — ".join(part for line in lines for part in (line[1], line[2]))
    return {
        "shot": shot,
        "setting": setting,
        "characters": ["Ong Bông", "Châu Chấu Lá"],
        "speaker": lines[0][0],
        "dialogue": spoken,
        "line_en": english,
        "line_vi": vietnamese,
        "subtitle": english,
        "duration": duration,
        "start_state": start,
        "actions": actions,
        "emotion": actions[0]["emotion"] if actions else "",
        "props": props,
        "camera": camera,
        "camera_move": camera_move,
        "end_state": end,
        "continuity": start,
        "image_prompt": f"{image}. {LOOK}. {BEE}. {HOPPER}",
        "video_prompt": (
            "Character motion only, camera separate. "
            + " ".join(
                f"At {item['start']}s, {item['character']} {item['action']} {item['object']}, feeling {item['emotion']}."
                for item in actions
            )
            + f" Camera: {camera_move}. No text."
        ),
        "goal": vietnamese,
    }


def sample_project() -> dict:
    scenes = [
        _scene(
            "Gặp nhau",
            "Khu vườn, lá lớn",
            "Châu Chấu ngồi trên lá. Ong chưa có mặt. Giỏ để bên cạnh, chưa mở.",
            [
                {"character": "Ong Bông", "action": "bay xuống rồi nghiêng đầu", "object": "Châu Chấu Lá", "start": 0, "duration": 2, "emotion": "quan tâm"},
                {"character": "Châu Chấu Lá", "action": "ngẩng lên nhìn Ong", "object": "Ong Bông", "start": 2, "duration": 3, "emotion": "mệt"},
            ],
            "Ong đứng cạnh lá. Châu Chấu vẫn ngồi, mắt nhìn Ong.",
            "Trung cảnh",
            "Máy tĩnh",
            "Không cầm đồ",
            [("Ong Bông", "Are you okay?", "Bạn ổn không?"), ("Châu Chấu Lá", "I'm tired.", "Mình mệt.")],
            "A round bee with a tiny blue scarf lands beside a green grasshopper in a leaf vest sitting on a large leaf, bee tilts its head",
        ),
        _scene(
            "Đưa táo",
            "Cùng chiếc lá và chiếc giỏ",
            "Ong đứng cạnh Châu Chấu. Giỏ có một quả táo, chưa được cầm.",
            [
                {"character": "Ong Bông", "action": "nhìn giỏ, lấy táo, nâng bằng hai tay và đưa sang", "object": "quả táo", "start": 0, "duration": 3, "emotion": "hơi mong"},
                {"character": "Châu Chấu Lá", "action": "nhìn quả táo rồi lắc đầu", "object": "quả táo", "start": 3, "duration": 2, "emotion": "từ chối nhẹ"},
            ],
            "Ong vẫn cầm táo. Châu Chấu đã lắc đầu.",
            "Trung cảnh",
            "Máy tiến rất nhẹ vào hai bàn tay",
            "Quả táo",
            [("Ong Bông", "Would you like an apple?", "Bạn muốn ăn một quả táo không?"), ("Châu Chấu Lá", "No, thank you.", "Không, cảm ơn bạn.")],
            "The bee lifts a red apple with both hands and offers it to the seated grasshopper, a small basket beside them",
        ),
        _scene(
            "Đưa nước",
            "Cùng chỗ ngồi",
            "Ong đang cầm táo. Cốc nước nằm trong giỏ.",
            [
                {"character": "Ong Bông", "action": "đặt táo lại vào giỏ", "object": "quả táo", "start": 0, "duration": 1.5, "emotion": "nhẹ nhàng"},
                {"character": "Ong Bông", "action": "lấy cốc nước và đưa bằng hai tay", "object": "cốc nước", "start": 1.5, "duration": 2, "emotion": "muốn giúp"},
                {"character": "Châu Chấu Lá", "action": "gật đầu", "object": "cốc nước", "start": 3.5, "duration": 1.5, "emotion": "đồng ý"},
            ],
            "Ong đưa cốc. Châu Chấu đã gật, tay chưa chạm cốc.",
            "Cận tay và cốc",
            "Máy tĩnh",
            "Táo trong giỏ, cốc nước",
            [("Ong Bông", "Some water?", "Một chút nước nhé?"), ("Châu Chấu Lá", "Yes, please.", "Có, cho mình nhé.")],
            "The bee puts the apple back into the basket and offers a small cup of water with both hands, the grasshopper nods",
        ),
        _scene(
            "Uống nước",
            "Cùng chiếc lá",
            "Cốc còn trong tay Ong, Châu Chấu chuẩn bị nhận.",
            [
                {"character": "Châu Chấu Lá", "action": "nhận cốc bằng hai tay và uống một ngụm", "object": "cốc nước", "start": 0, "duration": 3, "emotion": "dễ chịu"},
                {"character": "Ong Bông", "action": "buông tay khi bạn đã cầm chắc, rồi mỉm cười", "object": "cốc nước", "start": 2, "duration": 3, "emotion": "vui"},
            ],
            "Châu Chấu cầm cốc, miệng cười. Ong đứng cạnh, tay trống.",
            "Cận mặt Châu Chấu và cốc",
            "Máy tĩnh",
            "Cốc nước",
            [("Châu Chấu Lá", "I feel better!", "Mình thấy khỏe hơn rồi!")],
            "The grasshopper holds a small cup with both hands and smiles after a sip, the bee has let go and smiles beside him",
        ),
        _scene(
            "Đứng dậy",
            "Lối cạnh chiếc lá",
            "Châu Chấu ngồi, cầm cốc. Ong đứng sát.",
            [
                {"character": "Châu Chấu Lá", "action": "đặt cốc xuống cạnh giỏ rồi đứng dậy", "object": "cốc nước", "start": 0, "duration": 2.5, "emotion": "phấn khởi"},
                {"character": "Ong Bông", "action": "bước lùi một bước để nhường chỗ, rồi vỗ tay", "object": "", "start": 2.5, "duration": 2.5, "emotion": "vui"},
            ],
            "Cốc nằm cạnh giỏ. Hai bạn đứng. Ong vừa vỗ tay.",
            "Toàn cảnh thấp",
            "Máy lùi một chút",
            "Cốc đã đặt xuống",
            [("Châu Chấu Lá", "Let's play together!", "Cùng chơi nào!"), ("Ong Bông", "Great idea!", "Ý hay đấy!")],
            "The grasshopper sets the cup beside the basket and stands up, the bee steps back and claps",
        ),
        _scene(
            "Đi cùng nhau",
            "Lối nhỏ trong vườn",
            "Hai bạn đứng cạnh giỏ. Cốc và táo ở lại bên giỏ.",
            [
                {"character": "Ong Bông", "action": "đi cạnh bạn trên lối nhỏ", "object": "", "start": 0, "duration": 3, "emotion": "vui"},
                {"character": "Châu Chấu Lá", "action": "quay lại vẫy tay", "object": "", "start": 3, "duration": 2, "emotion": "tạm biệt"},
            ],
            "Hai bạn ở cuối lối, tay đang vẫy. Giỏ ở lại phía sau.",
            "Toàn cảnh",
            "Máy lùi nhẹ",
            "Không cầm đồ",
            [("Ong Bông", "See you next time!", "Hẹn gặp lại nhé!"), ("Châu Chấu Lá", "See you next time!", "Hẹn gặp lại nhé!")],
            "The bee and the grasshopper walk side by side on a garden path and turn back to wave, basket left behind",
        ),
    ]
    return {
        "title": "Ong Bông và Châu Chấu Lá",
        "theme": "Giúp bạn khi mệt",
        "overview": "Ong Bông thấy Châu Chấu Lá mệt, rót một cốc nước, rồi hai bạn đi chơi trong vườn.",
        "logline": "Ong giúp Châu Chấu hết mệt bằng một cốc nước, rồi hai bạn đi chơi.",
        "genre": "Hội thoại vui",
        "layout": "Học khái niệm",
        "age": "3–5",
        "frame": "caption",
        "aspect": "9:16",
        "character_lock": f"{BEE}; {HOPPER}",
        "characters": CHARACTERS,
        "license": {
            "name": "Liên khúc thiếu nhi dân gian",
            "works": ["Twinkle Twinkle Little Star", "Mary Had a Little Lamb", "Frère Jacques"],
            "terms": "Giai điệu công cộng, tool tự đánh. Chưa phải thư viện nhạc thương mại đã thẩm định từng bài.",
        },
        "motion": "storyboard",
        "scenes": scenes,
        "source": "sample",
    }
