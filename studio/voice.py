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


def synthesize(text: str, dest: Path) -> Path | None:
    """Ghi một file wav. Trả về None nếu không đọc được câu này."""
    parts = spoken_parts(text)
    if not parts:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    pieces: list[Path] = []
    for index, (line, voice) in enumerate(parts):
        piece = dest.with_name(f"{dest.stem}_{index}.mp3")
        try:
            _edge_save(line, voice, piece)
        except Exception:
            if VIETNAMESE.search(line):
                continue
            try:
                _sapi_save(line, piece)
            except Exception:
                continue
        if piece.is_file() and piece.stat().st_size > 400:
            pieces.append(piece)
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
