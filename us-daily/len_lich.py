"""Hẹn bốn video lên kênh bằng YouTube, giờ công khai đã ghi trong lich.json.

Không gõ mật khẩu Google. Không in token. Máy chủ Linux không có hồ sơ Chrome
đã đăng nhập, nên đường này dùng token tải lên đã cấp một lần.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
NY = ZoneInfo("America/New_York")
CHANNEL = "UCE056WfiFMV6k4N5irnIDnA"


def _secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    path = ROOT / ".env"
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _refresh() -> str:
    client_id = _secret("YOUTUBE_CLIENT_ID")
    client_secret = _secret("YOUTUBE_CLIENT_SECRET")
    refresh = _secret("YOUTUBE_REFRESH_TOKEN")
    if not (client_id and client_secret and refresh):
        return ""
    body = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        }
    ).encode()
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode())
    return payload.get("access_token", "")


def _soon_enough(stamp: str) -> str:
    when = datetime.fromisoformat(stamp)
    if when.tzinfo is None:
        when = when.replace(tzinfo=NY)
    earliest = datetime.now(when.tzinfo) + timedelta(minutes=20)
    if when < earliest:
        when = earliest
    return when.astimezone(NY).isoformat()


def _upload(token: str, item: dict) -> str:
    video = Path(item["file"])
    size = video.stat().st_size
    publish_at = _soon_enough(item["publish_at"])
    meta = {
        "snippet": {
            "title": item["title"][:100],
            "description": item["description"],
            "categoryId": item.get("category", "27"),
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_at,
            "selfDeclaredMadeForKids": False,
            "embeddable": True,
        },
    }
    raw = json.dumps(meta).encode()
    request = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=raw,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(size),
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        location = response.headers.get("Location")
    if not location:
        raise RuntimeError("YouTube không trả địa chỉ tải.")
    with video.open("rb") as handle:
        put = urllib.request.Request(
            location,
            data=handle.read(),
            method="PUT",
            headers={"Content-Type": "video/mp4", "Content-Length": str(size)},
        )
        with urllib.request.urlopen(put, timeout=600) as response:
            done = json.loads(response.read().decode())
    video_id = done.get("id", "")
    return f"https://youtu.be/{video_id} lúc {publish_at}" if video_id else publish_at


def schedule(folder: Path) -> int:
    manifest = folder / "lich.json"
    if not manifest.exists():
        print(f"Chưa có {manifest.name}")
        return 1
    items = json.loads(manifest.read_text(encoding="utf-8"))
    try:
        token = _refresh()
    except urllib.error.HTTPError:
        print("Token YouTube bị từ chối. Không in nội dung lỗi.")
        return 1
    if not token:
        print(
            "Chưa hẹn giờ: máy chủ chưa có YOUTUBE_CLIENT_ID, "
            "YOUTUBE_CLIENT_SECRET và YOUTUBE_REFRESH_TOKEN. Không gõ mật khẩu."
        )
        return 0
    for item in items:
        path = Path(item["file"])
        if not path.exists():
            print(f"Thiếu file, bỏ qua: {path.name}")
            continue
        try:
            link = _upload(token, item)
        except urllib.error.HTTPError:
            print(f"YouTube từ chối {path.name}. Không in nội dung lỗi.")
            return 1
        print(f"Đã hẹn {path.name}: {link}")
    print(f"Kênh {CHANNEL}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python us-daily/len_lich.py output/us-daily/YYYY-MM-DD")
        return 1
    return schedule(Path(sys.argv[1]))


if __name__ == "__main__":
    raise SystemExit(main())
