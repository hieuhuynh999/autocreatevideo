"""Chọn nhạc nền: thiếu nhi, hoặc một giai điệu quê do tool tự đánh."""

from __future__ import annotations

from pathlib import Path

TUNES = ("none", "thieu-nhi", "ru-con", "ly-ngua-o", "co-la")

_LICENSE = {
    "thieu-nhi": (
        "Nhạc: Liên khúc thiếu nhi dân gian",
        "Tác phẩm: Twinkle Twinkle Little Star; Mary Had a Little Lamb; Frère Jacques",
    ),
    "ru-con": (
        "Nhạc: Ru con",
        "Tác phẩm: dân ca ru con khuyết danh",
    ),
    "ly-ngua-o": (
        "Nhạc: Lý ngựa ô",
        "Tác phẩm: dân ca Lý ngựa ô khuyết danh",
    ),
    "co-la": (
        "Nhạc: Cò lả",
        "Tác phẩm: dân ca Cò lả khuyết danh",
    ),
}


def normalize(tune: str) -> str:
    return tune if tune in TUNES else "thieu-nhi"


def write_bed(dest: Path, duration: float, tune: str) -> Path | None:
    choice = normalize(tune)
    if choice == "none":
        return None
    if choice == "thieu-nhi":
        from studio.nursery import write_nursery

        return write_nursery(dest, duration)
    from studio.quehuong import write_que

    return write_que(dest, duration, choice)


def license_lines(tune: str) -> list[str]:
    choice = normalize(tune)
    if choice == "none":
        return []
    title, work = _LICENSE[choice]
    return [
        title,
        work,
        "Giấy phép: giai điệu dân gian khuyết danh, thuộc phạm vi công cộng.",
        "File này do tool tự đánh, không phải bản thu của ca sĩ.",
        "Được dùng trong video đã xuất. Không cam kết phần mềm nhận diện nhạc sẽ bỏ qua.",
        "Ngày kiểm tra: 2026-10-13",
    ]
