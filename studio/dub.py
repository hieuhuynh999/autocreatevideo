"""Bỏ tiếng gốc của video, dịch lời nói, đọc lại và gắn phụ đề."""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

import imageio_ffmpeg

from studio.render import _media_duration, _write_srt
from studio.specs import ASPECTS, PHONE_ASPECT

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
PHONE_WIDTH, PHONE_HEIGHT = ASPECTS[PHONE_ASPECT]
MAX_SECONDS = 120
TARGETS = {
    "vi": ("vi", "vi-VN-HoaiMyNeural"),
    "en": ("en", "en-US-AndrewNeural"),
}
HEAR = ("zh-CN", "en-US", "vi-VN")


def _run(args: list[str], cwd: Path | None = None) -> str:
    process = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode != 0:
        raise RuntimeError((process.stderr or process.stdout or "ffmpeg lỗi")[-900:])
    return process.stderr or ""


def _silence(dest: Path, seconds: float) -> None:
    if seconds < 0.05:
        return
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", f"{seconds:.3f}", "-c:a", "pcm_s16le", str(dest),
        ]
    )


def _speech_spans(wav: Path, duration: float) -> list[tuple[float, float]]:
    log = _run(
        [
            FFMPEG, "-hide_banner", "-i", str(wav),
            "-af", "silencedetect=noise=-32dB:d=0.45",
            "-f", "null", "-",
        ]
    )
    events: list[tuple[str, float]] = []
    for kind, value in re.findall(r"silence_(start|end):\s*([0-9.]+)", log):
        events.append((kind, float(value)))
    silences: list[tuple[float, float]] = []
    pending: float | None = None
    for kind, value in events:
        if kind == "start":
            pending = value
        elif pending is not None:
            silences.append((pending, value))
            pending = None
    if pending is not None:
        silences.append((pending, duration))
    spans: list[tuple[float, float]] = []
    cursor = 0.0
    for start, end in silences:
        if start - cursor >= 0.45:
            spans.append((cursor, start))
        cursor = max(cursor, end)
    if duration - cursor >= 0.45:
        spans.append((cursor, duration))
    if not spans:
        spans = [(0.0, duration)]
    pieces: list[tuple[float, float]] = []
    for start, end in spans:
        point = start
        while end - point > 20:
            pieces.append((point, point + 18))
            point += 18
        if end - point >= 0.45:
            pieces.append((point, end))
    return pieces


def _cut(wav: Path, dest: Path, start: float, end: float) -> None:
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
            "-i", str(wav), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dest),
        ]
    )


def _hear(wav: Path) -> str:
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    with sr.AudioFile(str(wav)) as source:
        audio = recognizer.record(source)
    last_error = ""
    for language in HEAR:
        try:
            text = recognizer.recognize_google(audio, language=language)
        except sr.UnknownValueError:
            continue
        except sr.RequestError as exc:
            last_error = str(exc)
            break
        cleaned = " ".join(str(text or "").split())
        if cleaned:
            return cleaned
    if last_error:
        raise RuntimeError("Máy nghe tiếng gốc chưa trả lời. Hãy thử lại khi có mạng.")
    return ""


def _translate(text: str, target: str) -> str:
    query = urllib.parse.urlencode({"client": "gtx", "sl": "auto", "tl": target, "dt": "t", "q": text})
    request = urllib.request.Request(
        "https://translate.googleapis.com/translate_a/single?" + query,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Chưa dịch được lời thoại. Hãy thử lại khi có mạng.") from exc
    parts = []
    for block in payload[0] or []:
        if block and block[0]:
            parts.append(str(block[0]))
    translated = " ".join(parts).strip()
    return translated or text


def _speak(text: str, voice: str, dest: Path) -> None:
    import edge_tts

    async def run() -> None:
        last = None
        for _ in range(2):
            try:
                await edge_tts.Communicate(text, voice, rate="-6%").save(str(dest))
                if dest.is_file() and dest.stat().st_size > 400:
                    return
            except Exception as exc:
                last = exc
        if last:
            raise RuntimeError("Chưa tạo được giọng đọc mới.") from last
        raise RuntimeError("Chưa tạo được giọng đọc mới.")

    asyncio.run(run())


def _to_wav(src: Path, dest: Path) -> None:
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dest),
        ]
    )


def _fit(src: Path, dest: Path, limit: float) -> Path:
    length = _media_duration(src)
    if length <= 0:
        return src
    if length <= limit + 0.05:
        if src.suffix.lower() == ".wav":
            return src
        _to_wav(src, dest)
        return dest
    tempo = min(1.35, length / max(limit, 0.5))
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src), "-filter:a", f"atempo={tempo:.3f}",
            "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dest),
        ]
    )
    return dest


def _concat(pieces: list[Path], dest: Path, list_file: Path) -> None:
    rows = []
    for piece in pieces:
        if piece.is_file() and piece.stat().st_size > 40:
            rows.append("file '" + piece.resolve().as_posix() + "'")
    if not rows:
        raise RuntimeError("Chưa tạo được tiếng dịch.")
    list_file.write_text("\n".join(rows), encoding="utf-8")
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c:a", "pcm_s16le", str(dest),
        ]
    )


def _write_vtt(path: Path, rows: list[tuple[float, float, str]]) -> None:
    def stamp(seconds: float) -> str:
        ms = max(0, int(round(seconds * 1000)))
        hours, ms = divmod(ms, 3_600_000)
        minutes, ms = divmod(ms, 60_000)
        secs, ms = divmod(ms, 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"

    blocks = ["WEBVTT", ""]
    for start, end, text in rows:
        blocks.append(f"{stamp(start)} --> {stamp(max(end, start + 0.4))}")
        blocks.append(text)
        blocks.append("")
    path.write_text("\n".join(blocks), encoding="utf-8")


def _ass_path(path: Path) -> str:
    return path.resolve().as_posix().replace(":", "\\:")


def _phone_scale() -> str:
    return (
        f"scale={PHONE_WIDTH}:{PHONE_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={PHONE_WIDTH}:{PHONE_HEIGHT}"
    )


def _mux(video: Path, voice: Path, srt: Path, dest: Path) -> list[str]:
    style = "FontName=Segoe UI\\,FontSize=22\\,PrimaryColour=&H00FFFFFF\\,Outline=1\\,Alignment=2\\,MarginV=80"
    burned = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video), "-i", str(voice),
        "-vf", f"{_phone_scale()},subtitles='{_ass_path(srt)}':force_style='{style}'",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
        str(dest),
    ]
    try:
        _run(burned)
        return []
    except RuntimeError:
        _run(
            [
                FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(video), "-i", str(voice),
                "-vf", _phone_scale(),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                str(dest),
            ]
        )
        return ["Phụ đề đã lưu trong phu-de.srt. Chưa ghi được chữ lên hình."]


def dub_video(folder: Path, source: Path, lang: str, title: str, theme: str, overview: str) -> dict:
    if lang not in TARGETS:
        raise ValueError("Chỉ dịch sang tiếng Việt hoặc tiếng Anh.")
    target, voice = TARGETS[lang]
    duration = _media_duration(source)
    if duration <= 0.4:
        raise ValueError("Không đọc được độ dài video.")
    if duration > MAX_SECONDS:
        raise ValueError("Video đổi giọng cần ngắn hơn 2 phút.")
    work = folder / "_dub"
    if work.exists():
        import shutil
        shutil.rmtree(work)
    work.mkdir(parents=True)
    speech = work / "goc.wav"
    try:
        _run(
            [
                FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(source), "-vn", "-ac", "1", "-ar", "16000",
                "-c:a", "pcm_s16le", str(speech),
            ]
        )
    except RuntimeError as exc:
        raise ValueError("Video không có tiếng để dịch.") from exc

    heard: list[tuple[float, float, str]] = []
    for index, (start, end) in enumerate(_speech_spans(speech, duration)):
        piece = work / f"cut_{index:02d}.wav"
        _cut(speech, piece, start, end)
        try:
            text = _hear(piece)
        except RuntimeError:
            raise
        if text:
            heard.append((start, end, text))
    if not heard:
        raise ValueError("Chưa nghe được lời trong video. Hãy dùng video có tiếng nói rõ.")

    rows: list[tuple[float, float, str]] = []
    pieces: list[Path] = []
    cursor = 0.0
    transcript = []
    for index, (start, end, original) in enumerate(heard):
        translated = _translate(original, target)
        transcript.append(f"[{start:.1f}] {original}\n    {translated}")
        spoken = work / f"say_{index:02d}.mp3"
        wav = work / f"say_{index:02d}.wav"
        _speak(translated, voice, spoken)
        fitted = _fit(spoken, wav, max(0.6, end - start - 0.05))
        gap = start - cursor
        if gap > 0.05:
            quiet = work / f"gap_{index:02d}.wav"
            _silence(quiet, gap)
            if quiet.is_file():
                pieces.append(quiet)
        pieces.append(fitted if fitted.is_file() else spoken)
        used = _media_duration(pieces[-1])
        leftover = (end - start) - used
        if leftover > 0.05:
            quiet = work / f"pad_{index:02d}.wav"
            _silence(quiet, leftover)
            if quiet.is_file():
                pieces.append(quiet)
        cursor = end
        rows.append((start, end, translated))
    tail = duration - cursor
    if tail > 0.05:
        quiet = work / "tail.wav"
        _silence(quiet, tail)
        if quiet.is_file():
            pieces.append(quiet)

    voice_wav = work / "dich.wav"
    _concat(pieces, voice_wav, work / "list.txt")
    srt = folder / "phu-de.srt"
    vtt = folder / "phu-de.vtt"
    _write_srt(srt, rows)
    _write_vtt(vtt, rows)
    (folder / "loi-goc.txt").write_text("\n".join(transcript), encoding="utf-8")
    final = folder / "phim.mp4"
    warnings = _mux(source, voice_wav, srt, final)
    exports = folder / "xuat"
    exports.mkdir(exist_ok=True)
    version = len(list(exports.glob("phim-*.mp4"))) + 1
    export = exports / f"phim-{version:02d}.mp4"
    export.write_bytes(final.read_bytes())
    language = "Tiếng Việt" if lang == "vi" else "English"
    (folder / "mo-ta.txt").write_text(
        "\n".join(
            [
                f"Tên: {title or 'Đổi giọng'}",
                f"Chủ đề: {theme}",
                f"Mô tả tổng quan: {overview}",
                f"Dịch sang: {language}",
                "Tiếng gốc đã được bỏ. Video dùng giọng đọc mới và phụ đề cùng ngôn ngữ.",
                "Khung: 1080×1920.",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "file": final.name,
        "seconds": round(_media_duration(final) or duration, 2),
        "srt": srt.name,
        "vtt": vtt.name,
        "export": f"xuat/{export.name}",
        "warnings": warnings,
        "renderer": "dub",
    }
