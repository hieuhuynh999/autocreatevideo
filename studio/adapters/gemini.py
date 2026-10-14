"""Vẽ ảnh bằng Gemini. Khóa chỉ nằm trên máy, không trả về trình duyệt."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEY_FILE = ROOT / "studio" / "gemini.key"
MODEL = "gemini-nano-banana-2.1"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def load_key() -> str:
    import os

    env = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if env:
        return env
    if KEY_FILE.is_file():
        return KEY_FILE.read_text(encoding="utf-8").strip()
    return ""


def save_key(value: str) -> None:
    text = (value or "").strip()
    if len(text) < 8:
        raise ValueError("Khóa Gemini quá ngắn.")
    KEY_FILE.write_text(text, encoding="utf-8")


def key_ready() -> bool:
    return bool(load_key())


def _message(status: int, raw: str) -> str:
    detail = raw
    try:
        payload = json.loads(raw)
        detail = str((payload.get("error") or {}).get("message") or raw)
    except json.JSONDecodeError:
        detail = raw
    lowered = detail.lower()
    if status in {401, 403} and "billing" not in lowered:
        return "Khóa Gemini không được chấp nhận. Tạo khóa tại aistudio.google.com/apikey rồi dán lại."
    if "billing" in lowered or "free tier" in lowered or "prepay" in lowered:
        return (
            "Tài khoản Google chưa trả được tiền ảnh. Model vẽ ảnh không có mức miễn phí, "
            "khoảng 0,03 USD mỗi ảnh. Bật thanh toán trong Google AI Studio rồi thử lại."
        )
    if status == 429 or "quota" in lowered or "resource_exhausted" in lowered:
        return "Gemini hết lượt trong phút này. Đợi một lát rồi bấm Tạo ảnh lại."
    return f"Gemini trả {status}: {detail[:240]}"


def generate_image(prompt: str, dest: Path, reference: Path | None = None) -> None:
    key = load_key()
    if not key:
        raise RuntimeError(
            "Chưa có khóa Gemini. Tạo tại aistudio.google.com/apikey, dán vào ô Khóa Gemini rồi bấm Lưu khóa."
        )
    parts: list[dict] = []
    if reference and reference.is_file():
        parts.append(
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(reference.read_bytes()).decode("ascii"),
                }
            }
        )
    parts.append({"text": prompt[:4000]})
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {"aspectRatio": "9:16", "imageSize": "1K"},
        },
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
            "User-Agent": "phim-ngan-ai",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(_message(exc.code, exc.read().decode("utf-8", "replace"))) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Không kết nối được Gemini: {exc.reason}") from exc
    payload = json.loads(raw.decode("utf-8"))
    for candidate in payload.get("candidates") or []:
        for part in (candidate.get("content") or {}).get("parts") or []:
            blob = part.get("inlineData") or part.get("inline_data") or {}
            encoded = blob.get("data") or ""
            if not encoded:
                continue
            image_bytes = base64.b64decode(encoded)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(image_bytes)
            return
    reason = str((payload.get("promptFeedback") or {}).get("blockReason") or "")
    if reason:
        raise RuntimeError(f"Gemini từ chối ảnh này: {reason}.")
    raise RuntimeError("Gemini không trả ảnh.")
