"""Video kho miễn phí, theo cách MoneyPrinterTurbo tìm Pexels, Pixabay và Coverr.

Nguồn gốc: MoneyPrinterTurbo, MIT License, Copyright (c) 2024 Harry.
Chỉ tải video dọc khi có khóa miễn phí do người dùng tự lưu trên máy.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode

import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
KEY_DIR = ROOT / "studio"
SOURCES = ("pexels", "pixabay", "coverr")


def _key(name: str) -> str:
    env = os.environ.get(f"{name.upper()}_API_KEY", "").strip()
    if env:
        return env
    path = KEY_DIR / f"{name}.key"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""


def save_key(name: str, value: str) -> None:
    if name not in SOURCES:
        raise ValueError("Nguồn video không được hỗ trợ.")
    path = KEY_DIR / f"{name}.key"
    text = value.strip()
    if text:
        path.write_text(text, encoding="utf-8")
    elif path.exists():
        path.unlink()


def ready() -> dict:
    return {name: bool(_key(name)) for name in SOURCES}


def _query(scene: dict) -> str:
    text = " ".join(
        str(scene.get(key) or "")
        for key in ("line_en", "subtitle", "shot")
    )
    words = re.findall(r"[A-Za-z]{3,}", text)
    if words:
        return " ".join(words[:4])
    return "cartoon animals garden"


def _get(url: str, headers: dict | None = None) -> bytes:
    request = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read()


def _portrait(width: int, height: int) -> bool:
    return height >= width and height >= 400


def _pexels(query: str) -> str:
    key = _key("pexels")
    if not key:
        return ""
    url = "https://api.pexels.com/v1/videos/search?" + urlencode(
        {"query": query, "orientation": "portrait", "per_page": "8"}
    )
    payload = json.loads(_get(url, {"Authorization": key, "User-Agent": "Mozilla/5.0"}))
    best = ""
    best_size = 10**12
    for video in payload.get("videos") or []:
        for item in video.get("video_files") or []:
            width = int(item.get("width") or 0)
            height = int(item.get("height") or 0)
            link = str(item.get("link") or "")
            if link and _portrait(width, height) and width * height < best_size:
                best = link
                best_size = width * height
    return best


def _pixabay(query: str) -> str:
    key = _key("pixabay")
    if not key:
        return ""
    url = "https://pixabay.com/api/videos/?" + urlencode(
        {"key": key, "q": query, "per_page": "8", "safesearch": "true"}
    )
    payload = json.loads(_get(url))
    for hit in payload.get("hits") or []:
        videos = hit.get("videos") or {}
        for size in ("small", "tiny", "medium"):
            item = videos.get(size) or {}
            width = int(item.get("width") or 0)
            height = int(item.get("height") or 0)
            link = str(item.get("url") or "")
            if link and _portrait(width, height):
                return link
    return ""


def _coverr(query: str) -> str:
    key = _key("coverr")
    if not key:
        return ""
    url = "https://api.coverr.co/videos?" + urlencode(
        {"query": query, "urls": "true", "page_size": "8", "filter": "is_vertical:true"}
    )
    payload = json.loads(_get(url, {"Authorization": f"Bearer {key}", "User-Agent": "Mozilla/5.0"}))
    for hit in payload.get("hits") or []:
        urls = hit.get("urls") or {}
        link = str(urls.get("mp4_download") or urls.get("mp4") or "")
        if link:
            return link
    return ""


def fill_stock(scene: dict, dest: Path) -> str:
    """Tải một video dọc. Trả về tên nguồn, hoặc chuỗi rỗng nếu không có khóa hay không tải được."""
    if not any(ready().values()):
        return ""
    query = _query(scene)
    finders = (("Pexels", _pexels), ("Pixabay", _pixabay), ("Coverr", _coverr))
    for name, finder in finders:
        try:
            link = finder(query)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            print(f"{name} chưa trả video: {exc}", flush=True)
            continue
        if not link:
            continue
        try:
            data = _get(link)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"{name} không tải được file: {exc}", flush=True)
            continue
        if len(data) < 1000 or len(data) > 25_000_000:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        print(f"Đã lấy video kho {name} cho {dest.name}.", flush=True)
        return name
    return ""
