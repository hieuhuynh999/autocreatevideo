"""Tạo ảnh bám cảnh 1, rồi tạo chuyển động từ đúng ảnh đó."""

from __future__ import annotations

import time
from pathlib import Path

from studio.adapters.free_video import generate as free_clip
from studio.adapters.free_video import remaining
from studio.adapters.pollinations import edit_image, key_ready
from studio.images import create_scene_image

FOLLOW = (
    "Edit this picture. Keep the exact same animals, colors, clothes, sizes and the same garden background. "
    "Do not add or remove animals. Keep every animal fully inside the frame. Change only the action: "
)
MOTION = (
    "Animate only the animals already in this picture. Keep the same colors, clothes and the same garden. "
    "Do not add characters. Keep every animal fully inside the frame. The camera stays still. Action: "
)


def _ids(items: list[dict]) -> str:
    return ", ".join(str(item["index"]) for item in items)


def _action(scene: dict) -> str:
    steps = scene.get("actions") if isinstance(scene.get("actions"), list) else []
    if steps:
        bits = []
        for item in steps:
            if not isinstance(item, dict):
                continue
            bits.append(
                f"{item.get('character', '')} {item.get('action', '')} {item.get('object', '')}".strip()
            )
        if bits:
            return "; ".join(bits)
    return str(scene.get("video_prompt") or scene.get("image_prompt") or scene.get("action") or "")


def build_motion(
    folder: Path,
    scenes: list[dict],
    aspect: str,
    lock: str,
    progress=None,
    stop=None,
) -> dict:
    if not scenes:
        raise ValueError("Chưa có cảnh.")
    if not key_ready() and not (folder / "scene_01.jpg").is_file():
        return {
            "mode": "need_key",
            "message": (
                "Chưa có ảnh cảnh 1. Bấm Tạo ảnh trước. Chuyển động dùng máy Wan miễn phí, "
                "khoảng 2 phim mỗi ngày, và lấy đúng ảnh đã có."
            ),
        }
    master = folder / "scene_01.jpg"
    round_no = 0
    made: list[dict] = []
    missed: list[int] = []
    while True:
        round_no += 1
        if stop and stop():
            return {
                "mode": "partial",
                "message": "Đã dừng phim này vì bạn đang tạo chuyển động cho phim khác.",
                "scenes": made,
            }
        made = []
        missed = []
        stopped = ""
        resting = False
        for position, scene in enumerate(scenes):
            index = int(scene.get("index") or position + 1)
            image = folder / f"scene_{index:02d}.jpg"
            action = _action(scene)[:500]
            if index == 1 and not image.is_file():
                created = create_scene_image(
                    folder, 1, str(scene.get("image_prompt") or action), "", lock, aspect, 101, action
                )
                if created.get("placeholder"):
                    raise RuntimeError(created.get("error") or "Không tạo được ảnh cảnh 1.")
            elif index > 1:
                if not master.is_file():
                    raise RuntimeError("Hãy có ảnh cảnh 1 trước. Các cảnh sau bám ảnh đó.")
                if not image.is_file():
                    print(f"Cảnh {index} đang bám ảnh cảnh 1.", flush=True)
                    edit_image(master, FOLLOW + action, image)
            clip = folder / f"scene_{index:02d}_motion.mp4"
            if clip.is_file() and clip.stat().st_size > 1000:
                print(f"Cảnh {index} đã có clip chuyển động.", flush=True)
                made.append({"index": index, "image": image.name, "video": clip.name})
                continue
            if resting:
                missed.append(index)
                continue
            if progress:
                progress(
                    f"Vòng {round_no}: đang gọi máy cho cảnh {index}. "
                    f"Đã có clip: {_ids(made) or 'chưa có'}."
                )
            print(f"Đang tạo chuyển động cảnh {index}. Còn {remaining()} cảnh trong ngày.", flush=True)
            try:
                engine = free_clip(image, MOTION + action, clip, 4.0)
            except RuntimeError as exc:
                print(f"Cảnh {index} chưa xong: {exc}", flush=True)
                missed.append(index)
                if "đã đủ 12" in str(exc):
                    stopped = str(exc)
                    break
                if "đang nghỉ" in str(exc):
                    resting = True
                continue
            print(f"Cảnh {index} xong bằng {engine}.", flush=True)
            made.append({"index": index, "image": image.name, "video": clip.name})
            time.sleep(8)
        if not missed:
            break
        if stopped:
            missing = ", ".join(str(item) for item in missed)
            done = _ids(made)
            if done:
                message = f"Cảnh {done} đã có clip. Cảnh {missing} chưa làm được. {stopped}"
            else:
                message = stopped
            return {"mode": "partial", "message": message, "scenes": made}
        wait = min(120, 40 + round_no * 10)
        missing = ", ".join(str(item) for item in missed)
        done = _ids(made)
        if done:
            note = (
                f"Cảnh {done} đã có clip. Còn cảnh {missing}. "
                f"Tool tự gọi tiếp sau {wait} giây, đến khi đủ mọi cảnh."
            )
        else:
            note = (
                f"Chưa có clip. Cảnh {missing} máy đang bận. "
                f"Tool tự gọi tiếp sau {wait} giây, đến khi đủ mọi cảnh."
            )
        print(note, flush=True)
        if progress:
            progress(note)
        time.sleep(wait)
    return {
        "mode": "video",
        "message": (
            "Đã tạo chuyển động bằng máy Wan miễn phí. Cảnh sau giữ ảnh cảnh 1. "
            "Các con vật trong hình được cử động. Bấm Xem trước để ghép lời và phụ đề. "
            f"Hôm nay còn {remaining()} cảnh."
        ),
        "scenes": made,
    }
