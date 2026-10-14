"""Dựng phim dọc bằng Remotion: nền chuyển động và phụ đề tiếng Anh hiện từng từ."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

INTRO = 0.0
OUTRO = 0.0
AUDIO_DELAY = 0.05
ROOT = Path(__file__).resolve().parents[1] / "remotion"
PUBLIC = ROOT / "public" / "job"
_LOCK = threading.Lock()
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def _node() -> Path | None:
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "node-portable"
    found = sorted(root.glob("*/node.exe"))
    if found:
        return found[-1]
    which = shutil.which("node")
    return Path(which) if which else None


def _cli() -> Path | None:
    direct = ROOT / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    if direct.is_file():
        return direct
    if not (ROOT / "node_modules").is_dir():
        return None
    matches = sorted((ROOT / "node_modules").glob("**/remotion-cli.js"))
    return matches[0] if matches else None


def _norm(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z']+", "", text).lower()


def align_caption(line_en: str, timed: list[dict], duration: float) -> list[dict]:
    """Ghép câu tiếng Anh trên màn hình với mốc từ của giọng đọc."""
    display = [word for word in line_en.split() if word]
    if not display:
        return []
    usable = [item for item in timed if _norm(str(item.get("text") or ""))]
    matched: list[dict] = []
    cursor = 0
    for token in display:
        want = _norm(token)
        found_at = None
        for index in range(cursor, len(usable)):
            got = _norm(str(usable[index]["text"]))
            if got and (got == want or got.startswith(want) or want.startswith(got)):
                found_at = index
                break
        if found_at is None:
            matched = []
            break
        item = usable[found_at]
        start = float(item["start"])
        matched.append(
            {
                "text": token,
                "start": round(start, 3),
                "end": round(max(float(item["end"]), start + 0.12), 3),
            }
        )
        cursor = found_at + 1
    if len(matched) == len(display):
        return matched
    span = max(0.8, min(max(0.8, duration - AUDIO_DELAY - 0.25), float(usable[-1]["end"]) if usable else duration * 0.72))
    step = span / len(display)
    return [
        {
            "text": token,
            "start": round(0.12 + index * step, 3),
            "end": round(0.12 + (index + 1) * step - 0.04, 3),
        }
        for index, token in enumerate(display)
    ]


def _keep_frames(ffmpeg: str, path: Path, full: float) -> int:
    """Bỏ khúc đứng hình cuối clip. Giữ nguyên phần còn đang cử động."""
    maximum = max(1, int(round(full * 30)) - 2)
    process = subprocess.run(
        [
            ffmpeg, "-hide_banner", "-loglevel", "error",
            "-i", str(path),
            "-vf", "fps=10,scale=48:86,format=gray",
            "-f", "rawvideo", "-",
        ],
        capture_output=True,
    )
    count = 48 * 86
    raw = process.stdout or b""
    frames = [raw[index:index + count] for index in range(0, len(raw) - count + 1, count)]
    last = 0.4
    for index in range(max(0, len(frames) - 1)):
        left = frames[index]
        right = frames[index + 1]
        diff = sum(abs(a - b) for a, b in zip(left, right)) / count
        if diff >= 0.5:
            last = (index + 1) / 10
    keep = min(full - 0.08, max(max(2.0, full - 1.0), last))
    return max(1, min(maximum, int(round(keep * 30))))


def _video_frames(ffmpeg: str, path: Path) -> int:
    process = subprocess.run(
        [
            ffmpeg, "-hide_banner", "-loglevel", "error",
            "-i", str(path), "-an",
            "-vf", "scale=8:8,format=gray",
            "-f", "rawvideo", "-",
        ],
        capture_output=True,
    )
    got = len(process.stdout or b"") // 64
    if got < 1:
        raise RuntimeError("Không đếm được khung hình của cảnh.")
    return got


def _encode_part(
    ffmpeg: str,
    source: Path,
    dest: Path,
    frames: int,
    width: int,
    height: int,
) -> int:
    end = max(1, frames) / 30
    process = subprocess.run(
        [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(source),
            "-vf",
            (
                f"trim=end={end:.6f},setpts=PTS-STARTPTS,"
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},fps=30,format=yuv420p,setsar=1"
            ),
            "-an",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "18",
            "-r", "30",
            str(dest),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode != 0 or not dest.is_file():
        tail = (process.stderr or process.stdout or "Không cắt được cảnh.").strip()[-900:]
        raise RuntimeError(tail or "Không cắt được cảnh.")
    return _video_frames(ffmpeg, dest)


def _stitch_reel(
    ffmpeg: str,
    parts: list[tuple[Path, int]],
    dest: Path,
    width: int,
    height: int,
) -> list[int]:
    """Nối các clip thành một file hình. Không mờ, không đẩy, không chồng hai cảnh."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    encoded: list[Path] = []
    counts: list[int] = []
    try:
        for index, (path, frames) in enumerate(parts):
            part = dest.parent / f"_reel_{index:02d}.mp4"
            counts.append(_encode_part(ffmpeg, path, part, frames, width, height))
            encoded.append(part)
        inputs: list[str] = []
        labels: list[str] = []
        for index, part in enumerate(encoded):
            inputs.extend(["-i", str(part)])
            labels.append(f"[{index}:v]")
        process = subprocess.run(
            [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                *inputs,
                "-filter_complex", "".join(labels) + f"concat=n={len(encoded)}:v=1:a=0[v]",
                "-map", "[v]", "-an",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "18",
                "-r", "30",
                str(dest),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if process.returncode != 0 or not dest.is_file() or dest.stat().st_size < 1000:
            tail = (process.stderr or process.stdout or "Không nối được các cảnh.").strip()[-900:]
            raise RuntimeError(tail or "Không nối được các cảnh.")
        return counts
    finally:
        for part in encoded:
            part.unlink(missing_ok=True)


def _public_name(path: Path) -> str:
    if path.parent == PUBLIC:
        return f"job/{path.name}"
    dest = PUBLIC / path.name
    shutil.copy2(path, dest)
    return f"job/{dest.name}"


def export_remotion(
    folder: Path,
    payload: dict,
    spoken: list[Path | None],
    word_marks: list[list[dict]],
    lengths: list[float],
    warnings: list[str],
    title: str,
    logline: str,
) -> dict | None:
    node = _node()
    cli = _cli()
    if node is None or cli is None:
        warnings.append("Chưa cài Remotion trên máy này, nên bản xem trước dựng theo cách cũ.")
        return None
    with _LOCK:
        return _export_locked(folder, payload, spoken, word_marks, lengths, warnings, title, logline, node, cli)


def _export_locked(
    folder: Path,
    payload: dict,
    spoken: list[Path | None],
    word_marks: list[list[dict]],
    lengths: list[float],
    warnings: list[str],
    title: str,
    logline: str,
    node: Path,
    cli: Path,
) -> dict:
    from studio.images import write_placeholder
    from studio.musicbed import license_lines, normalize, write_bed
    from studio.render import FFMPEG, _fit_voice, _media_duration, _write_srt
    from studio.specs import ASPECTS, PHONE_ASPECT

    width, height = ASPECTS[PHONE_ASPECT]
    scenes = payload.get("scenes") or []
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir(parents=True)
    fonts = True
    for name in ("segoeui.ttf", "segoeuib.ttf"):
        source = Path(r"C:\Windows\Fonts") / name
        if source.is_file():
            shutil.copy2(source, PUBLIC / name)
        else:
            fonts = False

    used_motion = False
    used_stock = False
    scene_props: list[dict] = []
    srt_rows: list[tuple[float, float, str]] = []
    cursor = INTRO
    want_voice = bool(payload.get("voice", True))
    vietnamese_only = payload.get("caption") == "vi"
    prepared: list[dict] = []
    for position, scene in enumerate(scenes):
        index = int(scene.get("index") or position + 1)
        duration = float(lengths[position])
        image = folder / f"scene_{index:02d}.jpg"
        if not image.is_file():
            write_placeholder(
                image,
                width,
                height,
                f"Cảnh {index}",
                str(scene.get("action") or scene.get("line_vi") or ""),
            )
        shutil.copy2(image, PUBLIC / f"scene-{index:02d}.jpg")
        wan = folder / f"scene_{index:02d}_motion.mp4"
        stock = folder / f"scene_{index:02d}_stock.mp4"
        clip = None
        if wan.is_file() and wan.stat().st_size > 1000:
            clip = wan
            used_motion = True
        elif stock.is_file() and stock.stat().st_size > 1000:
            clip = stock
            used_stock = True
            warnings.append(f"Cảnh {index} đang dùng video kho vì máy tạo chuyển động chưa trả clip.")
        video_seconds = _media_duration(clip) if clip is not None else 0.0
        frames = max(1, int(round(duration * 30)))
        if clip is not None and video_seconds > 2.2:
            frames = _keep_frames(FFMPEG, clip, video_seconds)
        prepared.append(
            {
                "scene": scene,
                "index": index,
                "clip": clip,
                "frames": frames,
                "video_seconds": video_seconds,
            }
        )

    reel_name = ""
    clips = [item["clip"] for item in prepared]
    if clips and all(item is not None for item in clips):
        counts = _stitch_reel(
            FFMPEG,
            [(item["clip"], item["frames"]) for item in prepared],
            PUBLIC / "reel.mp4",
            width,
            height,
        )
        for item, count in zip(prepared, counts):
            item["frames"] = count
        reel_name = "job/reel.mp4"
    else:
        for item in prepared:
            clip = item["clip"]
            if clip is None:
                continue
            shutil.copy2(clip, PUBLIC / f"scene-{item['index']:02d}.mp4")

    for position, item in enumerate(prepared):
        scene = item["scene"]
        index = item["index"]
        frames = item["frames"]
        duration = frames / 30
        video_seconds = float(item["video_seconds"] or 0)
        video_name = "" if reel_name or item["clip"] is None else f"job/scene-{index:02d}.mp4"

        line_en = "" if vietnamese_only else str(scene.get("line_en") or "").strip()
        line_vi = str(scene.get("line_vi") or scene.get("subtitle") or scene.get("dialogue") or "").strip()
        marks = word_marks[position] if position < len(word_marks) else []
        if not vietnamese_only and not line_en and marks:
            line_en = " ".join(str(item.get("text") or "") for item in marks if str(item.get("text") or "").strip())
        audio_name = ""
        words: list[dict] = []
        raw = spoken[position] if position < len(spoken) else None
        if want_voice and raw is not None and raw.is_file():
            limit = max(0.6, duration - 0.35)
            length = _media_duration(raw)
            tempo = min(1.25, length / limit) if length > limit + 0.05 else 1.0
            fitted = _fit_voice(raw, PUBLIC / f"voice-{index:02d}.wav", limit)
            audio_name = _public_name(fitted)
            scaled = [
                {
                    "text": item.get("text") or "",
                    "start": float(item.get("start") or 0) / tempo,
                    "end": float(item.get("end") or 0) / tempo,
                }
                for item in marks
            ]
            words = [] if vietnamese_only else align_caption(line_en, scaled, duration)
        elif line_en and not vietnamese_only:
            words = align_caption(line_en, [], duration)

        scene_props.append(
            {
                "duration": duration,
                "frames": frames,
                "image": f"job/scene-{index:02d}.jpg",
                "video": video_name,
                "videoSeconds": round(video_seconds, 3),
                "lineEn": line_en,
                "lineVi": line_vi,
                "words": words,
                "audio": audio_name,
                "audioDelay": AUDIO_DELAY,
            }
        )
        caption = line_vi if vietnamese_only else (
            " — ".join(part for part in (line_en, line_vi) if part) or str(scene.get("subtitle") or "").strip()
        )
        if caption:
            srt_rows.append((cursor + AUDIO_DELAY, max(cursor + AUDIO_DELAY + 0.4, cursor + duration - 0.05), caption))
        cursor += duration

    total = cursor + OUTRO
    tune = normalize(str(payload.get("music") or ("thieu-nhi" if payload.get("ambient", True) else "none")))
    music_name = ""
    if write_bed(PUBLIC / "music.wav", max(total, 1), tune):
        music_name = "job/music.wav"
    title_audio = ""

    props = {
        "title": title,
        "logline": logline,
        "intro": INTRO,
        "outro": OUTRO,
        "music": music_name,
        "musicVolume": 0.16 if tune not in {"none", "thieu-nhi"} else 0.22,
        "titleAudio": title_audio,
        "fonts": fonts,
        "captionMode": "vi" if vietnamese_only else "bilingual",
        "reel": reel_name,
        "scenes": scene_props,
    }
    props_path = (folder / "remotion-props.json").resolve()
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    final = (folder / "phim.mp4").resolve()
    command = [
        str(node),
        str(cli),
        "render",
        "src/index.ts",
        "KidsFilm",
        str(final),
        f"--props={props_path}",
        "--overwrite",
        "--concurrency=1",
        "--log=error",
    ]
    if CHROME.is_file():
        command.append(f"--browser-executable={CHROME}")
    env = os.environ.copy()
    env["PATH"] = str(node.parent) + os.pathsep + env.get("PATH", "")
    process = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
        env=env,
    )
    if process.returncode != 0 or not final.is_file() or final.stat().st_size < 1000:
        tail = (process.stderr or process.stdout or "Remotion lỗi").strip()[-1600:]
        raise RuntimeError(tail or "Remotion không tạo được file.")

    srt = folder / "phu-de.srt"
    _write_srt(srt, srt_rows)
    lines = license_lines(tune)
    if lines:
        (folder / "giay-phep-nhac.txt").write_text("\n".join(lines), encoding="utf-8")
    exports = folder / "xuat"
    exports.mkdir(exist_ok=True)
    version = len(list(exports.glob("phim-*.mp4"))) + 1
    archived = exports / f"phim-{version:02d}.mp4"
    shutil.copyfile(final, archived)
    shutil.rmtree(PUBLIC, ignore_errors=True)
    return {
        "file": final.name,
        "seconds": round(total, 1),
        "warnings": warnings,
        "srt": srt.name,
        "export": f"xuat/{archived.name}",
        "motion": "video" if used_motion else "stock" if used_stock else "storyboard",
        "renderer": "remotion",
    }
