"""Kiểm định bốn video trước khi mở Studio, và so tiêu đề với kênh đối thủ.

Lỗi chặn (không đăng): thiếu file, sai khung hình, quá ngắn hoặc quá dài,
không có tiếng, tiếng gần như im, hình đen, tiêu đề quá 100 ký tự, bài tiền
không có số hoặc thiếu câu "not personal financial advice", bản tin không
nêu tên báo, Short thiếu #Shorts.

So với đối thủ (chỉ cảnh báo, ghi vào mail): độ dài tiêu đề và tỉ lệ tiêu đề
có chữ số, lấy từ RSS công khai của các kênh cùng ngách.
"""

from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) us-daily/1.0"

RIVALS = {
    "tin": ("@PBSNewsHour", "@TLDRnewsGLOBAL", "@NBCNews"),
    "tien": ("@EconomicsExplained", "@moneyguyshow", "@GrahamStephan"),
}
RULES = {
    "tin": {"shape": (1280, 720), "min": 60, "max": 1800},
    "tien": {"shape": (1280, 720), "min": 40, "max": 1800},
    "short-tin": {"shape": (1080, 1920), "min": 10, "max": 60},
    "short-tien": {"shape": (1080, 1920), "min": 10, "max": 60},
}
OUTLETS = ("PBS", "NPR", "New York Times")


def _ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _probe(path: Path) -> dict:
    proc = subprocess.run([_ffmpeg(), "-i", str(path)], capture_output=True, text=True, errors="replace")
    text = proc.stderr
    info: dict = {"duration": None, "size": None, "audio": "Audio:" in text}
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if match:
        hours, minutes, seconds = match.groups()
        info["duration"] = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    size = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", text)
    if size:
        info["size"] = (int(size.group(1)), int(size.group(2)))
    return info


def _loudness(path: Path) -> float | None:
    proc = subprocess.run(
        [_ffmpeg(), "-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"],
        capture_output=True,
        text=True,
        errors="replace",
    )
    match = re.search(r"mean_volume: (-?\d+(?:\.\d+)?) dB", proc.stderr)
    return float(match.group(1)) if match else None


def _dark_frames(path: Path, duration: float) -> int:
    from PIL import Image, ImageStat

    dark = 0
    for share in (0.1, 0.5, 0.9):
        stamp = max(0.5, duration * share)
        proc = subprocess.run(
            [_ffmpeg(), "-ss", f"{stamp:.2f}", "-i", str(path), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
            capture_output=True,
        )
        if not proc.stdout:
            dark += 1
            continue
        from io import BytesIO

        image = Image.open(BytesIO(proc.stdout)).convert("L")
        stat = ImageStat.Stat(image)
        if stat.mean[0] < 12 or stat.stddev[0] < 4:
            dark += 1
    return dark


def _channel_feed(handle: str) -> list[str]:
    request = urllib.request.Request(f"https://www.youtube.com/{handle}", headers={"User-Agent": UA, "Accept-Language": "en-US"})
    with urllib.request.urlopen(request, timeout=20) as response:
        page = response.read().decode("utf-8", "replace")
    found = re.search(r'"externalId":"(UC[\w-]{22})"', page) or re.search(r'channel/(UC[\w-]{22})', page)
    if not found:
        return []
    feed = f"https://www.youtube.com/feeds/videos.xml?channel_id={found.group(1)}"
    request = urllib.request.Request(feed, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=20) as response:
        root = ET.fromstring(response.read())
    space = {"a": "http://www.w3.org/2005/Atom"}
    return [node.text or "" for node in root.findall("a:entry/a:title", space)]


def rivals(folder: Path) -> dict[str, dict]:
    cache = folder / "doi-thu.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    result: dict[str, dict] = {}
    for kind, handles in RIVALS.items():
        titles: list[str] = []
        used: list[str] = []
        for handle in handles:
            try:
                got = _channel_feed(handle)
            except Exception:
                got = []
            if got:
                used.append(handle)
                titles += got
        if titles:
            lengths = sorted(len(title) for title in titles)
            result[kind] = {
                "channels": used,
                "count": len(titles),
                "median": statistics.median(lengths),
                "low": lengths[max(0, int(len(lengths) * 0.1) - 1)],
                "high": lengths[min(len(lengths) - 1, int(len(lengths) * 0.9))],
                "digit_share": sum(bool(re.search(r"\d", title)) for title in titles) / len(titles),
            }
    cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _slot(item: dict) -> str:
    name = Path(item["file"]).name
    if name.startswith("short-tin"):
        return "short-tin"
    if name.startswith("short-tien"):
        return "short-tien"
    if name.startswith("tai-chinh"):
        return "tien"
    return "tin"


def check(folder: Path) -> tuple[bool, str]:
    manifest = folder / "lich.json"
    if not manifest.exists():
        return False, "KIỂM ĐỊNH: thiếu lich.json, chưa có gì để đăng."
    items = json.loads(manifest.read_text(encoding="utf-8"))
    board = rivals(folder)
    lines = ["KIỂM ĐỊNH TRƯỚC KHI ĐĂNG"]
    blocking = 0
    seen = set()
    for item in items:
        slot = _slot(item)
        seen.add(slot)
        rule = RULES[slot]
        path = Path(item["file"])
        title = item.get("title", "")
        description = item.get("description", "")
        bad: list[str] = []
        warn: list[str] = []
        if not path.exists():
            bad.append("thiếu file")
        else:
            info = _probe(path)
            length = info["duration"] or 0
            if info["size"] != rule["shape"]:
                bad.append(f"khung {info['size']}, cần {rule['shape'][0]}x{rule['shape'][1]}")
            if length < rule["min"] or length > rule["max"]:
                bad.append(f"dài {length:.0f}s, cần {rule['min']}–{rule['max']}s")
            if not info["audio"]:
                bad.append("không có tiếng")
            else:
                loud = _loudness(path)
                if loud is None or loud < -40:
                    bad.append(f"tiếng gần như im ({loud} dB)")
            if length and _dark_frames(path, length) >= 2:
                bad.append("hình đen ở nhiều đoạn")
        if not title or len(title) > 100:
            bad.append(f"tiêu đề {len(title)} ký tự, cần 1–100")
        if slot in ("tien", "short-tien"):
            if not re.search(r"\d", title):
                bad.append("tiêu đề bài tiền không có chữ số")
            if "not personal financial advice" not in description.lower():
                bad.append("mô tả thiếu câu not personal financial advice")
        if slot == "tin" and not any(name in description for name in OUTLETS):
            bad.append("mô tả bản tin không nêu PBS, NPR hay New York Times")
        if slot.startswith("short") and "#Shorts" not in title + description:
            bad.append("Short thiếu #Shorts")
        rival = board.get("tin" if slot in ("tin", "short-tin") else "tien")
        if rival and not slot.startswith("short"):
            plain = len(title)
            if plain < rival["low"] or plain > rival["high"]:
                warn.append(
                    f"tiêu đề {plain} ký tự, đối thủ thường {rival['low']}–{rival['high']} (trung vị {rival['median']:.0f})"
                )
            if rival["digit_share"] >= 0.5 and not re.search(r"\d", title):
                warn.append(f"{rival['digit_share']:.0%} tiêu đề đối thủ có chữ số, tiêu đề này không có")
        status = "ĐẠT" if not bad else "CHẶN"
        blocking += bool(bad)
        lines.append(f"- {path.name} [{status}] {title}")
        lines += [f"    lỗi: {text}" for text in bad]
        lines += [f"    so đối thủ: {text}" for text in warn]
    for slot in RULES:
        if slot not in seen:
            lines.append(f"- thiếu video {slot} [CHẶN]")
            blocking += 1
    if board:
        lines.append("")
        lines.append("Đối thủ đã đọc (RSS công khai, 15 video mới nhất mỗi kênh):")
        for kind, data in board.items():
            label = "bản tin" if kind == "tin" else "bài tiền"
            lines.append(
                f"- {label}: {', '.join(data['channels'])}; {data['count']} tiêu đề, "
                f"trung vị {data['median']:.0f} ký tự, {data['digit_share']:.0%} có chữ số"
            )
    else:
        lines.append("")
        lines.append("Không đọc được RSS đối thủ hôm nay. Chỉ áp các lỗi chặn.")
    ok = blocking == 0
    lines.append("")
    lines.append("KẾT LUẬN: ĐẠT, được đăng." if ok else f"KẾT LUẬN: {blocking} video bị chặn, không đăng ngày này.")
    report = "\n".join(lines)
    (folder / "kiem-dinh.txt").write_text(report + "\n", encoding="utf-8")
    return ok, report


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python us-daily/kiem_dinh.py output/us-daily/YYYY-MM-DD")
        return 2
    ok, report = check(Path(sys.argv[1]))
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
