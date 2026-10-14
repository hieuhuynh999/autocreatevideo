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
_TOKENS: dict[str, tuple[str, float]] = {}
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
        "name": "Wan nhanh",
        "base": "https://zerogpu-aoti-wan2-2-fp8da-aoti-faster.hf.space",
        "repo": "zerogpu-aoti/wan2-2-fp8da-aoti-faster",
        "kind": "fast",
    },
    {
        "name": "Wan A",
        "base": "https://cbensimon-wan2-2-fp8da-aoti-preview2.hf.space",
        "repo": "cbensimon/wan2-2-fp8da-aoti-preview2",
        "kind": "upload",
        "tail": [False, True],
        "frame": "16",
    },
    {
        "name": "Wan B",
        "base": "https://r3gm-wan2-2-fp8da-aoti-preview.hf.space",
        "repo": "r3gm/wan2-2-fp8da-aoti-preview",
        "kind": "upload",
        "tail": [True, False, True],
        "frame": "16",
    },
    {
        "name": "Wan C",
        "base": "https://prithivmlmods-wan2-2-fast.hf.space",
        "repo": "prithivMLmods/Wan2.2-Fast",
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


def _token(repo: str) -> str:
    if not repo:
        return ""
    cached = _TOKENS.get(repo)
    if cached and cached[1] > time.time():
        return cached[0]
    try:
        raw = _request(
            f"https://huggingface.co/api/spaces/{repo}/jwt",
            headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        token = str(json.loads(raw).get("token") or "")
    except (RuntimeError, ValueError, OSError):
        token = ""
    if token:
        _TOKENS[repo] = (token, time.time() + 1200)
    return token


def _auth(engine: dict, extra: dict | None = None) -> dict:
    headers = {"User-Agent": "Mozilla/5.0"}
    token = _token(str(engine.get("repo") or ""))
    if token:
        headers["Authorization"] = "Bearer " + token
    if extra:
        headers.update(extra)
    return headers


def _request(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 120) -> bytes:
    request = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:180]
        raise RuntimeError(f"{exc.code} {detail}") from exc


def _short_prompt(text: str) -> str:
    cleaned = " ".join((text or "").split())
    if cleaned.lower().startswith(("continue", "animate")):
        return cleaned[:180]
    low = cleaned.lower()
    for key, phrase in HINTS:
        if key in low:
            return f"The same characters stay in this picture. {phrase}. The camera moves gently. No cut."[:180]
    return "The same characters stay in this picture and move gently. The camera moves with them. No cut."


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


def _listen(engine: dict, event_id: str) -> bytes:
    base = engine["base"]
    started = time.time()
    request = urllib.request.Request(
        f"{base}/gradio_api/call/generate_video/{event_id}",
        headers=_auth(engine, {"Accept": "text/event-stream"}),
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
                    raw = text.split(":", 1)[1].strip()
                    if time.time() - started < 20 and raw in {"", "null", "None"}:
                        raise RuntimeError("từ chối ngay")
                    print(f"Wan báo lỗi trên {base}: {raw[:180]}", flush=True)
                    raise RuntimeError("máy báo lỗi")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"đang bận ({exc.code})") from exc
    return b""


def _call(engine: dict, data: list) -> bytes:
    base = engine["base"]
    raw = json.loads(
        _request(
            base + "/gradio_api/call/generate_video",
            json.dumps({"data": data}).encode(),
            _auth(engine, {"Content-Type": "application/json"}),
            timeout=60,
        )
    )
    event_id = raw.get("event_id")
    if not event_id:
        raise RuntimeError("không xếp được hàng")
    clip = _listen(engine, event_id)
    if len(clip) < 1000:
        raise RuntimeError("chưa trả clip")
    return clip


def _file_data(engine: dict, image: Path) -> dict:
    base = engine["base"]
    boundary, body = _multipart(image.name, image.read_bytes())
    uploaded = json.loads(
        _request(
            base + "/gradio_api/upload",
            body,
            _auth(engine, {"Content-Type": f"multipart/form-data; boundary={boundary}"}),
        )
    )
    if not isinstance(uploaded, list) or not uploaded:
        raise RuntimeError("không nhận ảnh")
    path = uploaded[0]
    return {
        "path": path,
        "url": f"{base}/gradio_api/file={path}",
        "orig_name": image.name,
        "meta": {"_type": "gradio.FileData"},
    }


def _upload_call(engine: dict, image: Path, prompt: str, end_image: Path | None = None) -> bytes:
    file_data = _file_data(engine, image)
    end_data = _file_data(engine, end_image) if end_image is not None and end_image.is_file() else None
    fields = [
        file_data,
        end_data,
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
    return _call(engine, fields)


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
    return _call(engine, fields)


def _fast_call(engine: dict, image: Path, prompt: str) -> bytes:
    base = engine["base"]
    boundary, body = _multipart(image.name, image.read_bytes())
    uploaded = json.loads(
        _request(
            base + "/gradio_api/upload",
            body,
            _auth(engine, {"Content-Type": f"multipart/form-data; boundary={boundary}"}),
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
        prompt[:180],
        6,
        "text, subtitles, letters, watermark",
        3.5,
        1,
        1,
        42,
        True,
    ]
    return _call(engine, fields)


def _ranked() -> list[dict]:
    return sorted(ENGINES, key=lambda item: (-_WINS.get(item["name"], 0), ENGINES.index(item)))


def generate(
    image: Path,
    prompt: str,
    dest: Path,
    seconds: float = 4.0,
    end_image: Path | None = None,
) -> str:
    del seconds
    state = _quota()
    if int(state.get("clips") or 0) >= DAILY_CLIPS:
        raise RuntimeError(
            "Hôm nay đã đủ 12 cảnh, khoảng 2 phim. Mai bấm Tạo chuyển động lại."
        )
    prompt = _short_prompt(prompt)
    ready = [item for item in _ranked() if time.time() >= _COOLDOWN.get(item["name"], 0)]
    if end_image is not None:
        ready.sort(key=lambda item: item.get("kind") != "upload")
    if not ready:
        raise RuntimeError("Các máy video đang nghỉ một lát.")
    errors: list[str] = []
    refused = 0
    with _LOCK:
        for engine in ready:
            try:
                print(f"Gọi {engine['name']} cho {image.name}", flush=True)
                kind = engine["kind"]
                if kind == "upload":
                    clip = _upload_call(engine, image, prompt, end_image)
                elif kind == "fast":
                    clip = _fast_call(engine, image, prompt)
                else:
                    clip = _b64_call(engine, image, prompt)
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
                if "từ chối ngay" in str(exc):
                    refused += 1
                print(f"{engine['name']} chưa xong: {exc}", flush=True)
    if errors and refused == len(errors):
        raise RuntimeError(
            "Hết lượt GPU miễn phí hôm nay. Máy từ chối ngay, không xếp hàng. "
            "Bấm lại sau 7 giờ sáng mai. Bấm Xem trước để ghép ảnh, lời đọc và phụ đề ngay."
        )
    raise RuntimeError("Máy đang bận: " + ", ".join(errors))
