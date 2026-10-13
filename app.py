"""Máy chủ local cho Xưởng phim ngắn."""

from __future__ import annotations

import json
import re
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from studio.images import create_scene_image
from studio.render import render_film, stitch_videos
from studio.sample_story import sample_project
from studio.adapters.motion import build_motion
from studio.adapters.pollinations import key_ready, save_key
from studio.adapters.stock_video import ready as stock_ready
from studio.adapters.stock_video import save_key as save_stock_key
from studio.screenplay import clean_idea, write_screenplay
from studio.specs import ASPECTS, PHONE_ASPECT, MAX_SCENES, MAX_SECONDS, MIN_SECONDS

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web" / "index.html"
OUTPUT = ROOT / "output"
HOST = "127.0.0.1"
PORT = 7860
SID_RE = re.compile(r"^[a-f0-9]{10}$")
_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.RLock()
_CURRENT_SID = ""


def _job_message(job: dict, text: str) -> None:
    with _JOBS_LOCK:
        job["message"] = text


def project_dir(sid: str) -> Path:
    if not SID_RE.fullmatch(sid or ""):
        raise ValueError("Phiên làm việc không hợp lệ.")
    folder = (OUTPUT / sid).resolve()
    folder.relative_to(OUTPUT.resolve())
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _motion_view(sid: str) -> dict:
    if not SID_RE.fullmatch(sid or ""):
        return {"mode": "idle", "message": "Chưa chạy.", "scenes": []}
    with _JOBS_LOCK:
        job = _JOBS.get(sid) or {"mode": "idle", "message": "Chưa chạy.", "scenes": []}
        scenes = []
        for item in job.get("scenes") or []:
            image = str(item.get("image") or "")
            if image and not image.startswith("/"):
                image = f"/output/{sid}/{image}"
            scenes.append({**item, "image": image})
        return {
            "mode": job.get("mode") or "idle",
            "message": job.get("message") or "",
            "scenes": scenes,
        }


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "XuongPhim/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_500_000:
            raise ValueError("Dữ liệu gửi lên quá lớn.")
        data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if not isinstance(data, dict):
            raise ValueError("Thiếu dữ liệu.")
        return data

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            body = WEB.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if path.startswith("/output/"):
            self._send_output(path[len("/output/") :])
            return
        if path == "/api/sample":
            self._sample()
            return
        if path == "/api/key":
            self._json(200, {"ready": key_ready()})
            return
        if path == "/api/stock-key":
            self._json(200, stock_ready())
            return
        if path == "/api/motion":
            sid = parse_qs(urlparse(self.path).query).get("sid", [""])[0]
            self._json(200, _motion_view(sid))
            return
        self.send_error(404)

    def _send_output(self, rel: str) -> None:
        root = OUTPUT.resolve()
        candidate = (root / rel).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            self.send_error(404)
            return
        if candidate.suffix.lower() not in {".jpg", ".mp4", ".txt", ".json", ".srt"} or not candidate.is_file():
            self.send_error(404)
            return
        data = candidate.read_bytes()
        size = len(data)
        start, end = 0, size - 1
        status = 200
        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes=") and size:
            spec = range_header.split("=", 1)[1].split(",")[0].strip()
            left, _, right = spec.partition("-")
            try:
                if left == "":
                    start = max(0, size - int(right or "0"))
                else:
                    start = int(left)
                    end = int(right) if right else size - 1
            except ValueError:
                start, end = 0, size - 1
            end = min(end, size - 1)
            if start > end or start < 0:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            status = 206
        chunk = data[start : end + 1]
        kind = {
            ".jpg": "image/jpeg",
            ".mp4": "video/mp4",
            ".txt": "text/plain; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".srt": "application/x-subrip; charset=utf-8",
        }[candidate.suffix.lower()]
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(chunk)))
        self.send_header("Cache-Control", "no-store")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        try:
            self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            data = self._read_json()
            if path == "/api/script":
                self._script(data)
            elif path == "/api/image":
                self._image(data)
            elif path == "/api/render":
                self._render(data)
            elif path == "/api/motion":
                self._motion(data)
            elif path == "/api/key":
                save_key(str(data.get("key") or ""))
                self._json(200, {"ready": True})
            elif path == "/api/stock-key":
                for name in ("pexels", "pixabay", "coverr"):
                    if name in data:
                        save_stock_key(name, str(data.get(name) or ""))
                self._json(200, stock_ready())
            elif path == "/api/stitch":
                self._stitch(data)
            else:
                self.send_error(404)
        except (ValueError, RuntimeError) as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:
            print("Lỗi:", type(exc).__name__, exc)
            self._json(500, {"error": "Có lỗi khi xử lý. Hãy thử lại."})

    def _script(self, data: dict) -> None:
        idea = clean_idea(str(data.get("idea") or ""))
        if len(idea) < 20:
            raise ValueError("Hãy kể rõ hơn: một nhân vật, việc đang xảy ra, và cảm xúc cuối.")
        count = int(data.get("count") or 4)
        count = max(3, min(MAX_SCENES, count))
        screenplay = write_screenplay(
            idea,
            str(data.get("genre") or "Kỹ năng sống"),
            count,
            str(data.get("style") or ""),
            str(data.get("lock") or ""),
            str(data.get("layout") or "Truyện kể"),
            str(data.get("age") or "3–5"),
        )
        sid = uuid4().hex[:10]
        folder = project_dir(sid)
        (folder / "kich-ban.json").write_text(
            json.dumps(screenplay, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._json(200, {"sid": sid, **screenplay})

    def _sample(self) -> None:
        screenplay = sample_project()
        sid = uuid4().hex[:10]
        folder = project_dir(sid)
        (folder / "kich-ban.json").write_text(
            json.dumps(screenplay, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._json(200, {"sid": sid, **screenplay})

    def _image(self, data: dict) -> None:
        folder = project_dir(str(data.get("sid") or ""))
        index = int(data.get("index") or 0)
        if index < 1 or index > MAX_SCENES:
            raise ValueError("Số cảnh không hợp lệ.")
        result = create_scene_image(
            folder,
            index,
            str(data.get("prompt") or ""),
            str(data.get("style") or ""),
            str(data.get("lock") or ""),
            PHONE_ASPECT,
            int(data.get("seed") or index * 97),
            str(data.get("fallback") or ""),
            str(data.get("pose_b") or ""),
            str(data.get("pose_c") or ""),
        )
        self._json(
            200,
            {
                "url": f"/output/{folder.name}/{result['file']}?v={uuid4().hex[:6]}",
                "placeholder": result["placeholder"],
                "needs_key": bool(result.get("needs_key")),
                "followed": bool(result.get("followed")),
                "error": result.get("error") or "",
            },
        )

    def _motion(self, data: dict) -> None:
        folder = project_dir(str(data.get("sid") or ""))
        scenes = data.get("scenes")
        if not isinstance(scenes, list) or not scenes:
            raise ValueError("Hãy tạo storyboard trước.")
        clean = [dict(item) for item in scenes[:MAX_SCENES] if isinstance(item, dict)]
        lock = str(data.get("lock") or "")
        global _CURRENT_SID
        with _JOBS_LOCK:
            _CURRENT_SID = folder.name
            current = _JOBS.get(folder.name)
            if current and current.get("mode") == "running":
                self._json(200, _motion_view(folder.name))
                return
            job = {
                "mode": "running",
                "message": "Đang tự gọi máy video đến khi mọi cảnh đều có clip.",
                "scenes": [],
            }
            _JOBS[folder.name] = job

        def work() -> None:
            try:
                result = build_motion(
                    folder,
                    clean,
                    PHONE_ASPECT,
                    lock,
                    progress=lambda text: _job_message(job, text),
                    stop=lambda: _CURRENT_SID != folder.name,
                )
                with _JOBS_LOCK:
                    job.clear()
                    job.update(result)
            except Exception as exc:
                print("Lỗi chuyển động:", type(exc).__name__, exc, flush=True)
                job["mode"] = "partial"
                job["message"] = str(exc)
                job.setdefault("scenes", [])

        threading.Thread(target=work, daemon=True).start()
        self._json(200, _motion_view(folder.name))

    def _render(self, data: dict) -> None:
        folder = project_dir(str(data.get("sid") or ""))
        scenes = data.get("scenes")
        if not isinstance(scenes, list) or not scenes:
            raise ValueError("Hãy viết kịch bản trước khi dựng.")
        clean_scenes = []
        for item in scenes[:MAX_SCENES]:
            if not isinstance(item, dict):
                continue
            duration = float(item.get("duration") or 5)
            clean_scenes.append(
                {
                    "index": int(item.get("index") or len(clean_scenes) + 1),
                    "shot": str(item.get("shot") or "")[:80],
                    "action": str(item.get("action") or "")[:400],
                    "dialogue": str(item.get("dialogue") or "")[:300],
                    "subtitle": str(item.get("subtitle") or "")[:140],
                    "image_prompt": str(item.get("image_prompt") or "")[:500],
                    "video_prompt": str(item.get("video_prompt") or "")[:500],
                    "pose_b": str(item.get("pose_b") or "")[:500],
                    "pose_c": str(item.get("pose_c") or "")[:500],
                    "line_en": str(item.get("line_en") or "")[:240],
                    "line_vi": str(item.get("line_vi") or "")[:240],
                    "actions": item.get("actions") if isinstance(item.get("actions"), list) else [],
                    "camera": str(item.get("camera") or "")[:160],
                    "goal": str(item.get("goal") or "")[:240],
                    "continuity": str(item.get("continuity") or "")[:240],
                    "duration": min(MAX_SECONDS, max(MIN_SECONDS, duration)),
                }
            )
        payload = {
            "title": str(data.get("title") or "Phim ngắn")[:80],
            "logline": str(data.get("logline") or "")[:240],
            "lock": str(data.get("lock") or "")[:300],
            "style": str(data.get("style") or "")[:160],
            "aspect": PHONE_ASPECT,
            "ambient": bool(data.get("ambient", True)),
            "voice": bool(data.get("voice", True)),
            "kids": bool(data.get("kids", False)),
            "frame": "caption" if data.get("frame") == "caption" else "full",
            "scenes": clean_scenes,
        }
        (folder / "kich-ban.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result = render_film(folder, payload)
        self._json(
            200,
            {
                "video": f"/output/{folder.name}/phim.mp4?v={uuid4().hex[:6]}",
                "prompts": f"/output/{folder.name}/prompt-video.txt",
                "seconds": result["seconds"],
                "folder": str(folder),
                "warnings": result.get("warnings") or [],
                "srt": f"/output/{folder.name}/{result.get('srt', 'phu-de.srt')}",
                "export": f"/output/{folder.name}/{result.get('export', 'phim.mp4')}",
                "motion": result.get("motion") or "storyboard",
                "renderer": result.get("renderer") or "ffmpeg",
            },
        )

    def _stitch(self, data: dict) -> None:
        raw = data.get("files") or []
        if not isinstance(raw, list) or len(raw) < 2:
            raise ValueError("Chọn ít nhất hai file mp4 trong thư mục output.")
        paths = []
        root = OUTPUT.resolve()
        for item in raw[:8]:
            candidate = (root / str(item)).resolve()
            candidate.relative_to(root)
            if candidate.suffix.lower() != ".mp4" or not candidate.is_file():
                raise ValueError("Chỉ ghép file mp4 đã có trong output.")
            paths.append(candidate)
        width, height = ASPECTS[PHONE_ASPECT]
        dest_dir = project_dir("a11ce00001")
        dest = dest_dir / "phim.mp4"
        seconds = stitch_videos(paths, dest, width, height)
        self._json(200, {"video": f"/output/{dest_dir.name}/phim.mp4", "seconds": round(seconds, 1)})


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    OUTPUT.mkdir(parents=True, exist_ok=True)
    port = PORT
    server = None
    for candidate in range(PORT, PORT + 8):
        try:
            server = ThreadingHTTPServer((HOST, candidate), StudioHandler)
            port = candidate
            break
        except OSError:
            continue
    if server is None:
        raise SystemExit("Không mở được cổng 7860–7867. Hãy tắt bản đang chạy rồi thử lại.")
    url = f"http://{HOST}:{port}"
    print(f"Xưởng phim ngắn đang chạy tại {url}", flush=True)
    print("Tắt bằng Ctrl+C trong cửa sổ này.", flush=True)
    threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã tắt.")
        server.shutdown()


if __name__ == "__main__":
    main()
