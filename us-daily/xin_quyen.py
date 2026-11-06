"""Một lần: mở trình duyệt để bạn bấm Cho phép, rồi ghi refresh token vào .env.

Không đọc mật khẩu. Không in client secret hay token.
Chạy sau khi .env đã có YOUTUBE_CLIENT_ID và YOUTUBE_CLIENT_SECRET:

  python us-daily/xin_quyen.py
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
PORT = 8765
REDIRECT = f"http://127.0.0.1:{PORT}/"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def _read(name: str) -> str:
    if not ENV.exists():
        return ""
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _write(name: str, value: str) -> None:
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    prefix = name + "="
    found = False
    updated = []
    for line in lines:
        if line.startswith(prefix):
            updated.append(f"{name}={value}")
            found = True
        else:
            updated.append(line)
    if not found:
        if updated and updated[-1] != "":
            updated.append("")
        updated.append(f"{name}={value}")
    ENV.write_text("\n".join(updated) + "\n", encoding="utf-8")


def main() -> int:
    client_id = _read("YOUTUBE_CLIENT_ID")
    client_secret = _read("YOUTUBE_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Điền YOUTUBE_CLIENT_ID và YOUTUBE_CLIENT_SECRET vào .env rồi chạy lại.")
        print("Hai mã này lấy ở Google Cloud, mục Credentials, OAuth client loại Desktop.")
        return 1

    holder: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            holder["code"] = params.get("code", [""])[0]
            holder["error"] = params.get("error", [""])[0]
            body = "Đã nhận. Quay lại cửa sổ lệnh.".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            return

    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": REDIRECT,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    webbrowser.open(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")
    print("Trình duyệt đã mở. Đăng nhập đúng Gmail của kênh và bấm Cho phép.")
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    server.handle_request()
    if holder.get("error") or not holder.get("code"):
        print("Google chưa cấp quyền. Nếu báo redirect_uri_mismatch, thêm địa chỉ này vào OAuth client:")
        print(REDIRECT)
        return 1
    body = urllib.parse.urlencode(
        {
            "code": holder["code"],
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT,
            "grant_type": "authorization_code",
        }
    ).encode()
    request = urllib.request.Request("https://oauth2.googleapis.com/token", data=body, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode())
    refresh = payload.get("refresh_token", "")
    if not refresh:
        print("Google không trả refresh token. Chạy lại và bấm Cho phép thêm một lần.")
        return 1
    _write("YOUTUBE_REFRESH_TOKEN", refresh)
    print("Đã ghi YOUTUBE_REFRESH_TOKEN vào .env. Không copy mã này vào chat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
