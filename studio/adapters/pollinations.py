"""Gọi Pollinations. Khóa chỉ đọc trên máy, không trả về trình duyệt."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEY_FILE = ROOT / "studio" / "pollinations.key"


def load_key() -> str:
    import os

    env = (os.environ.get("POLLINATIONS_API_KEY") or "").strip()
    if env:
        return env
    if KEY_FILE.is_file():
        return KEY_FILE.read_text(encoding="utf-8").strip()
    return ""


def save_key(value: str) -> None:
    text = (value or "").strip()
    if len(text) < 8:
        raise ValueError("Khóa quá ngắn.")
    KEY_FILE.write_text(text, encoding="utf-8")


def key_ready() -> bool:
    return bool(load_key())


def _request(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 180) -> tuple[bytes, str]:
    request = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), response.headers.get("Content-Type") or ""
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError(
                "Khóa không được chấp nhận. Vào enter.pollinations.ai/keys, tạo khóa, rồi dán khóa đó vào ô Lưu khóa."
            ) from exc
        if exc.code == 402:
            raise RuntimeError(
                "Tài khoản Pollinations hết pollen. Ảnh các cảnh đã có. Tạo chuyển động cần khoảng 0,05 pollen mỗi cảnh. Nạp tại enter.pollinations.ai/top-up rồi bấm Tạo chuyển động lại."
            ) from exc
        detail = exc.read().decode("utf-8", "replace")[:240]
        raise RuntimeError(f"Pollinations trả {exc.code}: {detail}") from exc


def _multipart(fields: list[tuple[str, str]], files: list[tuple[str, str, bytes, str]]) -> tuple[str, bytes]:
    boundary = "----KidsStudioBoundary"
    chunks: list[bytes] = []
    for name, value in fields:
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
        )
    for name, filename, payload, mime in files:
        chunks.append(
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\n"
                f"Content-Type: {mime}\r\n\r\n"
            ).encode()
            + payload
            + b"\r\n"
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return boundary, b"".join(chunks)


def edit_image(source: Path, prompt: str, dest: Path) -> None:
    """Sửa ảnh cảnh 1 thành cảnh sau. Giữ nhân vật và bối cảnh, chỉ đổi hành động."""
    key = load_key()
    if not key:
        raise RuntimeError("Cảnh sau cần khóa Pollinations để bám đúng ảnh cảnh 1.")
    boundary, body = _multipart(
        [("model", "kontext"), ("prompt", prompt[:900])],
        [("image", source.name, source.read_bytes(), "image/jpeg")],
    )
    raw, _kind = _request(
        "https://gen.pollinations.ai/v1/images/edits",
        body,
        {
            "Authorization": f"Bearer {key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0",
        },
        timeout=180,
    )
    payload = json.loads(raw.decode("utf-8"))
    item = (payload.get("data") or [{}])[0]
    encoded = item.get("b64_json") or ""
    if not encoded and item.get("url"):
        downloaded, _kind = _request(item["url"], timeout=120)
        dest.write_bytes(downloaded)
        return
    if not encoded:
        raise RuntimeError("Pollinations không trả ảnh đã sửa.")
    dest.write_bytes(base64.b64decode(encoded))


def upload_image(path: Path) -> str:
    """Đưa ảnh lên địa chỉ riêng để engine video nhìn khung đầu. Không gắn thẻ công khai."""
    key = load_key()
    if not key:
        raise RuntimeError("Tạo chuyển động cần khóa Pollinations.")
    boundary, body = _multipart(
        [],
        [("file", path.name, path.read_bytes(), "image/jpeg")],
    )
    raw, _kind = _request(
        "https://media.pollinations.ai/upload",
        body,
        {
            "Authorization": f"Bearer {key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Mozilla/5.0",
        },
        timeout=120,
    )
    payload = json.loads(raw.decode("utf-8"))
    url = str(payload.get("url") or "")
    if not url.startswith("http"):
        raise RuntimeError("Không nhận được địa chỉ ảnh để tạo chuyển động.")
    return url


def image_to_video(prompt: str, image_url: str, dest: Path, aspect: str, seconds: int) -> None:
    key = load_key()
    if not key:
        raise RuntimeError("Tạo chuyển động cần khóa Pollinations.")
    ratio = {"16:9": "16:9", "9:16": "9:16"}.get(aspect, "")
    query = {
        "model": "wan-fast",
        "duration": str(max(2, min(5, int(seconds)))),
        "audio": "false",
        "image": image_url,
    }
    if ratio:
        query["aspectRatio"] = ratio
    url = (
        "https://gen.pollinations.ai/video/"
        + urllib.parse.quote(prompt[:700])
        + "?"
        + urllib.parse.urlencode(query)
    )
    data, kind = _request(
        url,
        headers={"Authorization": f"Bearer {key}", "User-Agent": "Mozilla/5.0"},
        timeout=240,
    )
    if "json" in kind or data[:1] in (b"{", b"["):
        raise RuntimeError(data.decode("utf-8", "replace")[:300])
    if len(data) < 1000:
        raise RuntimeError("File chuyển động quá nhỏ.")
    dest.write_bytes(data)
