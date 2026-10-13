"""Chuyển động miễn phí qua vài máy Wan. Không dùng pollen và không gọi Gemini."""

from __future__ import annotations

import base64
import json
import threading
import time
import uuid
from datetime import date
from pathlib import Path

import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
QUOTA_FILE = ROOT / "output" / "_free_quota.json"
DAILY_CLIPS = 12
_LOCK = threading.Lock()
_COOLDOWN: dict[str, float] = {}
_WINS: dict[str, int] = {}
HINTS = (
    ("uống", "one animal takes a sip from a small cup"),
    ("táo", "one animal offers an apple with both hands"),
    ("nước", "one animal offers a small cup"),
    ("lắc", "one animal shakes its head"),
    ("gật", "one animal nods"),
    ("vẫy", "one animal waves"),
    ("vỗ", "one animal claps"),
    ("đứng", "one animal stands up"),
    ("bay", "one animal lands beside the other"),
    ("nghiêng", "one animal tilts its head"),
    ("đi", "the two animals walk side by side"),
)
ENGINES = (
    {
        "name": "Wan A",
        "base": "https://cbensimon-wan2-2-fp8da-aoti-preview2.hf.space",
        "kind": "upload",
        "tail": [False, True],
        "frame": 16,
    },
    {
        "name": "Wan B",
        "base": "https://r3gm-wan2-2-fp8da-aoti-preview.hf.space",
        "kind": "upload",
        "tail": [True, False, True],
        "frame": "16",
    },
    {
        "name": "Wan C",
        "base": "https://prithivmlmods-wan2-2-fast.hf.space",
        "kind": "b64",
    },
)


def _quota() -> dict:
    today = date.today().isoformat()
    if QUOTA_FILE.is_file():
        try:
            data = json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if data.get("date") == today:
            return data
    return {"date": today, "clips": 0}


def _save_quota(data: dict) -> None:
    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_FILE.write_text(json.dumps(data), encoding="utf-8")


def remaining() -> int:
    return max(0, DAILY_CLIPS - int(_quota().get("clips") or 0))


def _multipart(filename: str, payload: bytes) -> tuple[str, bytes]:
    boundary = "----FreeVideo" + uuid.uuid4().hex
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{filename}\"\r\n"
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode() + payload + f"\r\n--{boundary}--\r\n".encode()
    return boundary, body


def _request(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 120) -> bytes:
    request = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:180]
        raise RuntimeError(f"{exc.code} {detail}") from exc


def _short_prompt(text: str) -> str:
    low = text.lower()
    for key, phrase in HINTS:
        if key in low:
            return f"The same animals stay inside the frame. {phrase}. Camera stays still."
    return "The same animals stay inside the frame and move gently. Camera stays still."


def _clip_bytes(payload: object) -> bytes:
    if isinstance(payload, str):
        if payload.startswith("data:video"):
            encoded = payload.split(",", 1)[1]
            return base64.b64decode(encoded)
        if payload.startswith("http") and (".mp4" in payload or "/file=" in payload or "gradio_api/file" in payload):
            return _request(payload, timeout=120)
        return b""
    if isinstance(payload, dict):
        for value in payload.values():
            found = _clip_bytes(value)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _clip_bytes(item)
            if found:
                return found
    return b""


def _listen(base: str, event_id: str) -> bytes:
    request = urllib.request.Request(
        f"{base}/gradio_api/call/generate_video/{event_id}",
        headers={"Accept": "text/event-stream", "User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            event = ""
            for line in response:
                text = line.decode("utf-8", "replace").strip()
                if text.startswith("event:"):
                    event = text.split(":", 1)[1].strip()
                elif text.startswith("data:") and event == "complete":
                    raw = text.split(":", 1)[1].strip() or "null"
                    return _clip_bytes(json.loads(raw))
                elif text.startswith("data:") and event == "error":
                    print(f"Wan bận trên {base}", flush=True)
                    break
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"đang bận ({exc.code})") from exc
    return b""


def _call(base: str, data: list) -> bytes:
    raw = json.loads(
        _request(
            base + "/gradio_api/call/generate_video",
            json.dumps({"data": data}).encode(),
            {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            timeout=60,
        )
    )
    event_id = raw.get("event_id")
    if not event_id:
        raise RuntimeError("không xếp được hàng")
    clip = _listen(base, event_id)
    if len(clip) < 1000:
        raise RuntimeError("chưa trả clip")
    return clip


def _upload_call(engine: dict, image: Path, prompt: str) -> bytes:
    base = engine["base"]
    boundary, body = _multipart(image.name, image.read_bytes())
    uploaded = json.loads(
        _request(
            base + "/gradio_api/upload",
            body,
            {"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "Mozilla/5.0"},
        )
    )
    if not isinstance(uploaded, list) or not uploaded:
        raise RuntimeError("không nhận ảnh")
    path = uploaded[0]
    file_data = {
        "path": path,
        "url": f"{base}/gradio_api/file={path}",
        "orig_name": image.name,
        "meta": {"_type": "gradio.FileData"},
    }
    fields = [
        file_data,
        None,
        prompt[:180],
        4,
        "text, subtitles, letters, watermark",
        3.5,
        1,
        1,
        42,
        True,
        6,
        "UniPCMultistep",
        3.0,
        engine["frame"],
        *engine["tail"],
    ]
    return _call(base, fields)


def _b64_call(engine: dict, image: Path, prompt: str) -> bytes:
    encoded = base64.b64encode(image.read_bytes()).decode("ascii")
    fields = [
        "data:image/jpeg;base64," + encoded,
        prompt[:180],
        4,
        "text, subtitles, letters, watermark",
        3.5,
        1.0,
        1.0,
        42,
        True,
    ]
    return _call(engine["base"], fields)


def _ranked() -> list[dict]:
    return sorted(ENGINES, key=lambda item: (-_WINS.get(item["name"], 0), ENGINES.index(item)))


def generate(image: Path, prompt: str, dest: Path, seconds: float = 4.0) -> str:
    del seconds
    state = _quota()
    if int(state.get("clips") or 0) >= DAILY_CLIPS:
        raise RuntimeError(
            "Hôm nay đã đủ 12 cảnh, khoảng 2 phim. Mai bấm Tạo chuyển động lại."
        )
    prompt = _short_prompt(prompt)
    ready = [item for item in _ranked() if time.time() >= _COOLDOWN.get(item["name"], 0)]
    if not ready:
        raise RuntimeError("Các máy video đang nghỉ một lát.")
    errors: list[str] = []
    with _LOCK:
        for engine in ready:
            try:
                print(f"Gọi {engine['name']} cho {image.name}", flush=True)
                clip = _upload_call(engine, image, prompt) if engine["kind"] == "upload" else _b64_call(engine, image, prompt)
                dest.write_bytes(clip)
                _WINS[engine["name"]] = _WINS.get(engine["name"], 0) + 1
                _COOLDOWN.pop(engine["name"], None)
                state["clips"] = int(state.get("clips") or 0) + 1
                _save_quota(state)
                return engine["name"]
            except (RuntimeError, ValueError, OSError) as exc:
                dest.unlink(missing_ok=True)
                _COOLDOWN[engine["name"]] = time.time() + 80
                errors.append(engine["name"])
                print(f"{engine['name']} chưa xong: {exc}", flush=True)
    raise RuntimeError("Máy đang bận: " + ", ".join(errors))
