"""Nhạc thiếu nhi tự chơi từ giai điệu dân gian đã hết bản quyền.

Không dùng bản thu của ai. Ba giai điệu thuộc phạm vi công cộng:
Twinkle Twinkle Little Star, Mary Had a Little Lamb, Frère Jacques.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

RATE = 44100
BPM = 96

PITCH = {
    "C4": 261.63,
    "D4": 293.66,
    "E4": 329.63,
    "F4": 349.23,
    "G4": 392.00,
    "A4": 440.00,
    "C5": 523.25,
    "R": 0.0,
}

# nốt, số phách. 1 phách = một nốt đen.
TWINKLE = [
    ("C4", 1), ("C4", 1), ("G4", 1), ("G4", 1), ("A4", 1), ("A4", 1), ("G4", 2),
    ("F4", 1), ("F4", 1), ("E4", 1), ("E4", 1), ("D4", 1), ("D4", 1), ("C4", 2),
    ("G4", 1), ("G4", 1), ("F4", 1), ("F4", 1), ("E4", 1), ("E4", 1), ("D4", 2),
    ("G4", 1), ("G4", 1), ("F4", 1), ("F4", 1), ("E4", 1), ("E4", 1), ("D4", 2),
    ("C4", 1), ("C4", 1), ("G4", 1), ("G4", 1), ("A4", 1), ("A4", 1), ("G4", 2),
    ("F4", 1), ("F4", 1), ("E4", 1), ("E4", 1), ("D4", 1), ("D4", 1), ("C4", 2),
]
MARY = [
    ("E4", 1), ("D4", 1), ("C4", 1), ("D4", 1), ("E4", 1), ("E4", 1), ("E4", 2),
    ("D4", 1), ("D4", 1), ("D4", 2), ("E4", 1), ("G4", 1), ("G4", 2),
    ("E4", 1), ("D4", 1), ("C4", 1), ("D4", 1), ("E4", 1), ("E4", 1), ("E4", 1), ("E4", 1),
    ("D4", 1), ("D4", 1), ("E4", 1), ("D4", 1), ("C4", 2),
]
FRERE = [
    ("C4", 1), ("D4", 1), ("E4", 1), ("C4", 1), ("C4", 1), ("D4", 1), ("E4", 1), ("C4", 1),
    ("E4", 1), ("F4", 1), ("G4", 2), ("E4", 1), ("F4", 1), ("G4", 2),
    ("G4", 0.5), ("A4", 0.5), ("G4", 0.5), ("F4", 0.5), ("E4", 1), ("C4", 1),
    ("G4", 0.5), ("A4", 0.5), ("G4", 0.5), ("F4", 0.5), ("E4", 1), ("C4", 1),
    ("C4", 1), ("G4", 1), ("C4", 2), ("C4", 1), ("G4", 1), ("C5", 2),
]
MEDLEY = TWINKLE + [("R", 1)] + MARY + [("R", 1)] + FRERE + [("R", 2)]


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
        attack = min(1.0, t / 0.015)
        decay = math.exp(-3.4 * t)
        wave_sample = (
            math.sin(2 * math.pi * freq * t)
            + 0.28 * math.sin(2 * math.pi * freq * 2 * t)
            + 0.08 * math.sin(2 * math.pi * freq * 3 * t)
        )
        samples.append(0.2 * attack * decay * wave_sample)
    return samples


def write_nursery(dest: Path, duration: float) -> Path:
    """Ghi một file wav đủ dài, lặp liên khúc thiếu nhi."""
    needed = max(1, int(RATE * duration))
    song: list[float] = []
    while len(song) < needed:
        for name, beats in MEDLEY:
            song.extend(_note(name, beats))
    song = song[:needed]
    fade = int(RATE * 1.1)
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
