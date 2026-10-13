"""Đọc lời thoại bằng giọng tiếng Anh hoặc tiếng Việt."""

from __future__ import annotations

import asyncio
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VIETNAMESE = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)
VOICE_EN = "en-US-AnaNeural"
VOICE_VI = "vi-VN-HoaiMyNeural"


def spoken_parts(text: str) -> list[tuple[str, str]]:
    """Tách một câu thành các đoạn, mỗi đoạn một giọng."""
    raw = " ".join((text or "").replace("—", "|").replace("–", "|").split())
    if not raw:
        return []
    chunks = [part.strip(" .") for part in raw.split("|") if part.strip(" .")]
    if not chunks:
        return []
    parts: list[tuple[str, str]] = []
    for chunk in chunks:
        voice = VOICE_VI if VIETNAMESE.search(chunk) else VOICE_EN
        parts.append((chunk, voice))
    return parts


def _edge_save(text: str, voice: str, dest: Path) -> None:
    import edge_tts

    async def run() -> None:
        clip = edge_tts.Communicate(text, voice, rate="-8%")
        await clip.save(str(dest))

    asyncio.run(run())


def _sapi_save(text: str, dest: Path) -> None:
    wav = dest.with_suffix(".wav")
    script = dest.with_suffix(".ps1")
    safe = text.replace("'", "''")
    script.write_text(
        "\n".join(
            [
                "Add-Type -AssemblyName System.Speech",
                "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer",
                "$speaker.SelectVoice('Microsoft Zira Desktop')",
                "$speaker.Rate = -2",
                f"$speaker.SetOutputToWaveFile('{wav}')",
                f"$speaker.Speak('{safe}')",
                "$speaker.Dispose()",
            ]
        ),
        encoding="utf-8-sig",
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        check=True,
        capture_output=True,
        text=True,
    )
    if dest.suffix.lower() != ".wav":
        subprocess.run(
            [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav), str(dest)],
            check=True,
            capture_output=True,
        )


def _run(args: list[str]) -> None:
    process = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if process.returncode != 0:
        raise RuntimeError((process.stderr or "ffmpeg lỗi")[-800:])


def _to_wav(pieces: list[Path], dest: Path) -> None:
    inputs: list[str] = []
    for piece in pieces:
        inputs.extend(["-i", str(piece)])
    labels = "".join(f"[{index}:a]" for index in range(len(pieces)))
    graph = f"{labels}concat=n={len(pieces)}:v=0:a=1[out]"
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            *inputs, "-filter_complex", graph, "-map", "[out]",
            "-c:a", "pcm_s16le", str(dest),
        ]
    )


def _piece_duration(path: Path) -> float:
    process = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", process.stderr or "")
    if not match:
        return 0
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _edge_collect(text: str, voice: str, dest: Path) -> list[dict]:
    """Tải lời đọc và mốc từng từ. Mốc tính bằng giây trong file của đoạn này."""
    import edge_tts

    async def run() -> list[dict]:
        clip = edge_tts.Communicate(text, voice, rate="-8%", boundary="WordBoundary")
        words: list[dict] = []
        audio = bytearray()
        async for chunk in clip.stream():
            kind = chunk["type"]
            if kind == "audio":
                audio.extend(chunk["data"])
            elif kind == "WordBoundary":
                start = float(chunk["offset"]) / 10_000_000
                end = start + float(chunk["duration"]) / 10_000_000
                token = str(chunk.get("text") or "").strip()
                if token:
                    words.append({"text": token, "start": start, "end": end})
        if not audio:
            raise RuntimeError("Không nhận được tiếng đọc.")
        dest.write_bytes(bytes(audio))
        return words

    return asyncio.run(run())


def _save_piece(line: str, voice: str, piece: Path) -> list[dict]:
    try:
        return _edge_collect(line, voice, piece)
    except Exception:
        try:
            _edge_save(line, voice, piece)
        except Exception:
            if VIETNAMESE.search(line):
                return []
            _sapi_save(line, piece)
        return []


def _join_speech(dest: Path, pieces: list[Path]) -> Path | None:
    if not pieces:
        return None
    wav = dest.with_suffix(".wav")
    try:
        _to_wav(pieces, wav)
    except RuntimeError:
        return None
    if wav.is_file() and wav.stat().st_size > 400:
        return wav
    return None


def synthesize(text: str, dest: Path) -> Path | None:
    """Ghi một file wav. Trả về None nếu không đọc được câu này."""
    audio, _words = synthesize_timed(text, dest)
    return audio


def synthesize_timed(text: str, dest: Path) -> tuple[Path | None, list[dict]]:
    """Ghi wav và mốc từ tiếng Anh, để phụ đề vàng chạy đúng nhịp lời đọc."""
    parts = spoken_parts(text)
    if not parts:
        return None, []
    dest.parent.mkdir(parents=True, exist_ok=True)
    pieces: list[Path] = []
    words: list[dict] = []
    offset = 0.0
    for index, (line, voice) in enumerate(parts):
        piece = dest.with_name(f"{dest.stem}_{index}.mp3")
        try:
            piece_words = _save_piece(line, voice, piece)
        except Exception:
            continue
        if not piece.is_file() or piece.stat().st_size <= 400:
            continue
        if voice == VOICE_EN:
            for item in piece_words:
                words.append(
                    {
                        "text": item["text"],
                        "start": round(item["start"] + offset, 3),
                        "end": round(item["end"] + offset, 3),
                    }
                )
        pieces.append(piece)
        offset += _piece_duration(piece)
    return _join_speech(dest, pieces), words
