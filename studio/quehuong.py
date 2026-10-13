"""Nhạc quê nhẹ, tool tự đánh từ giai điệu dân gian khuyết danh.

Ru con, Lý ngựa ô và Cò lả là dân ca truyền khẩu, không phải bản thu của ca sĩ.
File wav do tool tổng hợp. Không dùng bản ghi âm có chủ quyền.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

RATE = 44100
BPM = 62

PITCH = {
    "C4": 261.63,
    "D4": 293.66,
    "E4": 329.63,
    "G4": 392.00,
    "A4": 440.00,
    "C5": 523.25,
    "D5": 587.33,
    "R": 0.0,
}

# nốt, số phách. Nhịp chậm, âm lượng nhỏ.
RU_CON = [
    ("G4", 1), ("E4", 1), ("G4", 1), ("A4", 1.5), ("G4", 0.5), ("E4", 1), ("D4", 1),
    ("C4", 1), ("D4", 1), ("E4", 1), ("G4", 2), ("E4", 1), ("D4", 1), ("C4", 2),
    ("R", 1),
    ("G4", 1), ("A4", 1), ("C5", 1.5), ("A4", 0.5), ("G4", 1), ("E4", 1),
    ("D4", 1), ("E4", 1), ("G4", 1), ("E4", 1), ("D4", 1), ("C4", 2),
    ("R", 2),
]
LY_NGUA_O = [
    ("E4", 1), ("G4", 1), ("A4", 1.5), ("G4", 0.5), ("E4", 1), ("C4", 1),
    ("D4", 1), ("E4", 1), ("G4", 1.5), ("E4", 0.5), ("D4", 1), ("C4", 2),
    ("R", 1),
    ("G4", 1), ("A4", 1), ("C5", 1), ("A4", 1), ("G4", 1), ("E4", 1),
    ("G4", 1), ("E4", 1), ("D4", 1), ("C4", 2),
    ("R", 2),
]
CO_LA = [
    ("G4", 1.5), ("E4", 0.5), ("G4", 1), ("A4", 1), ("C5", 1.5), ("A4", 0.5),
    ("G4", 1), ("E4", 1), ("D4", 1), ("E4", 1), ("G4", 2),
    ("E4", 1), ("D4", 1), ("C4", 2),
    ("R", 1),
    ("C5", 1), ("A4", 1), ("G4", 1), ("E4", 1), ("G4", 1), ("D4", 1), ("C4", 2),
    ("R", 2),
]
TUNES = {
    "ru-con": RU_CON,
    "ly-ngua-o": LY_NGUA_O,
    "co-la": CO_LA,
}


def _note(name: str, beats: float) -> list[float]:
    seconds = beats * (60 / BPM)
    count = max(1, int(RATE * seconds))
    freq = PITCH[name]
    samples: list[float] = []
    for index in range(count):
        t = index / RATE
        if freq <= 0:
            samples.append(0.0)
            continue
        attack = min(1.0, t / 0.04)
        decay = math.exp(-1.6 * t)
        tone = (
            math.sin(2 * math.pi * freq * t)
            + 0.18 * math.sin(2 * math.pi * freq * 2 * t)
            + 0.35 * math.sin(2 * math.pi * (freq / 2) * t)
        )
        samples.append(0.11 * attack * decay * tone)
    return samples


def write_que(dest: Path, duration: float, tune: str = "ru-con") -> Path:
    """Ghi một file wav đủ dài, lặp một giai điệu quê."""
    melody = TUNES.get(tune) or RU_CON
    needed = max(1, int(RATE * duration))
    song: list[float] = []
    while len(song) < needed:
        for name, beats in melody:
            song.extend(_note(name, beats))
    song = song[:needed]
    fade = min(len(song), int(RATE * 1.4))
    for index in range(fade):
        song[-1 - index] *= index / fade
    dest.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dest), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        frames = b"".join(struct.pack("<h", max(-32767, min(32767, int(sample * 32767)))) for sample in song)
        handle.writeframes(frames)
    return dest
