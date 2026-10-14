"""Tạo chuyển động từ ảnh cảnh đã có. Cảnh sau bắt đầu đúng khung hình cuối của cảnh trước."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from studio.adapters.free_video import generate as free_clip
from studio.adapters.free_video import remaining
from studio.adapters.stock_video import fill_stock, ready as stock_ready

CHAIN = "waypoint"
PROMPT = (
    "Continue this exact frame. Same characters, same clothes, same garden. "
    "Smooth motion into the next moment. No cut and no text."
)


def _ids(items: list[dict]) -> str:
    return ", ".join(str(item["index"]) for item in items)


def _meta_path(folder: Path, index: int) -> Path:
    return folder / f"scene_{index:02d}_motion.json"


def _tail_path(folder: Path, index: int) -> Path:
    return folder / f"scene_{index:02d}_tail.jpg"


def _chained(folder: Path, index: int, clip: Path) -> bool:
    meta = _meta_path(folder, index)
    if not clip.is_file() or clip.stat().st_size < 1000 or not meta.is_file():
        return False
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return data.get("chain") == CHAIN


def _save_tail(clip: Path, dest: Path) -> None:
    """Lưu đúng khung sẽ còn lại ở cuối clip, để cảnh sau bắt đầu từ đó."""
    from studio.render import FFMPEG, _media_duration
    from studio.remotion_export import _keep_frames

    full = _media_duration(clip) or 3.5
    frames = _keep_frames(FFMPEG, clip, full)
    stamp = max(0.0, (frames - 1) / 30.0)
    process = subprocess.run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(clip), "-ss", f"{stamp:.3f}",
            "-frames:v", "1", "-q:v", "2", str(dest),
        ],
        capture_output=True,
    )
    if process.returncode != 0 or not dest.is_file() or dest.stat().st_size < 1000:
        raise RuntimeError("Không lấy được khung cuối của cảnh trước.")


def _mark(folder: Path, index: int, start: Path, end: Path | None) -> None:
    _meta_path(folder, index).write_text(
        json.dumps({"chain": CHAIN, "start": start.name, "end": end.name if end else ""}, ensure_ascii=False),
        encoding="utf-8",
    )


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
    missing_images = []
    for position, scene in enumerate(scenes):
        index = int(scene.get("index") or position + 1)
        image = folder / f"scene_{index:02d}.jpg"
        if not image.is_file() or image.stat().st_size < 1000:
            missing_images.append(str(index))
    if missing_images:
        return {
            "mode": "need_images",
            "message": (
                "Chưa có ảnh cảnh "
                + ", ".join(missing_images)
                + ". Bấm Tải ảnh đã vẽ trước, rồi Tạo chuyển động."
            ),
            "scenes": [],
        }
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
            clip = folder / f"scene_{index:02d}_motion.mp4"
            if _chained(folder, index, clip):
                print(f"Cảnh {index} đã nối từ khung trước.", flush=True)
                _save_tail(clip, _tail_path(folder, index))
                made.append({"index": index, "image": image.name, "video": clip.name})
                continue
            if resting:
                missed.append(index)
                continue
            if progress:
                progress(
                    f"Vòng {round_no}: đang nối cảnh {index} từ khung hình trước. "
                    f"Đã có clip: {_ids(made) or 'chưa có'}."
                )
            start = image
            previous = _tail_path(folder, index - 1)
            if index > 1 and previous.is_file() and previous.stat().st_size > 1000:
                start = previous
            nxt = folder / f"scene_{index + 1:02d}.jpg"
            end = nxt if nxt.is_file() and nxt.stat().st_size > 1000 else None
            print(f"Đang tạo chuyển động cảnh {index} nối liền. Còn {remaining()} cảnh trong ngày.", flush=True)
            try:
                engine = free_clip(start, PROMPT, clip, 4.0, end)
                _save_tail(clip, _tail_path(folder, index))
                _mark(folder, index, start, end)
            except RuntimeError as exc:
                print(f"Cảnh {index} chưa xong: {exc}", flush=True)
                missed.append(index)
                if "đã đủ 12" in str(exc) or "Hết lượt GPU" in str(exc):
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
        stock_notes: list[str] = []
        if any(stock_ready().values()):
            by_index = {
                int(scene.get("index") or position + 1): scene
                for position, scene in enumerate(scenes)
            }
            for index in missed:
                stock_file = folder / f"scene_{index:02d}_stock.mp4"
                if stock_file.is_file() and stock_file.stat().st_size > 1000:
                    continue
                source_name = fill_stock(by_index.get(index) or {}, stock_file)
                if source_name:
                    stock_notes.append(f"{index} ({source_name})")
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
        stock_text = ""
        if stock_notes:
            stock_text = " Đã lấy video kho cho cảnh " + ", ".join(stock_notes) + ". Máy Wan vẫn được gọi lại để thay bằng đúng nhân vật."
        if done:
            note = (
                f"Cảnh {done} đã có clip. Còn cảnh {missing}. "
                f"Tool tự gọi tiếp sau {wait} giây, đến khi đủ mọi cảnh.{stock_text}"
            )
        else:
            note = (
                f"Chưa có clip Wan. Cảnh {missing} máy đang bận. "
                f"Tool tự gọi tiếp sau {wait} giây, đến khi đủ mọi cảnh.{stock_text}"
            )
        print(note, flush=True)
        if progress:
            progress(note)
        time.sleep(wait)
    return {
        "mode": "video",
        "message": (
            "Đã tạo chuyển động nối liền. Cảnh sau bắt đầu đúng khung hình cuối của cảnh trước, "
            "nên chỗ ghép không còn là hai video khác nhau. Bấm Xem trước. "
            f"Hôm nay còn {remaining()} cảnh."
        ),
        "scenes": made,
    }
