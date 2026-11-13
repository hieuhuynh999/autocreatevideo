"""Kiểm định hai Short trước khi mở Studio, và so với Short của kênh đối thủ.

Lỗi chặn (không đăng): thiếu file, khác 1080x1920, dưới 29 fps, ngoài 15–59
giây, không có tiếng, độ to ngoài -20 đến -9 LUFS, hình đen, chữ nằm ngoài
vùng an toàn của điện thoại, chữ chạy nhỏ hơn cỡ tối thiểu, chữ bị rút gọn,
tiêu đề quá 100 ký tự, bài tiền không có số hoặc thiếu câu "not personal
financial advice", Short tin không nêu tên báo, thiếu #Shorts.

So với đối thủ (chỉ cảnh báo, ghi vào mail): độ dài tiêu đề và tỉ lệ tiêu đề
có chữ số từ RSS công khai; độ dài video và độ to so với Short đối thủ đã đo
trong doi_thu_short.json (chạy lại do_doi_thu.py để cập nhật).
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
    "short-tin": {"shape": (1080, 1920), "min": 15, "max": 59},
    "short-tien": {"shape": (1080, 1920), "min": 15, "max": 59},
}
OUTLETS = ("PBS", "NPR", "New York Times")
LUFS_RANGE = (-20.0, -9.0)
BENCHMARK = Path(__file__).with_name("doi_thu_short.json")


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
    fps = re.search(r"(\d+(?:\.\d+)?) fps", text)
    info["fps"] = float(fps.group(1)) if fps else None
    return info


def _loudness(path: Path) -> float | None:
    proc = subprocess.run(
        [_ffmpeg(), "-i", str(path), "-af", "ebur128", "-vn", "-f", "null", "-"],
        capture_output=True,
        text=True,
        errors="replace",
    )
    found = re.findall(r"I:\s+(-?\d+(?:\.\d+)?) LUFS", proc.stderr)
    return float(found[-1]) if found else None


def _inside(box, layout: dict) -> bool:
    top, low = layout["top_zone"], layout["low_zone"]
    x0, y0, x1, y1 = box
    if x0 < top[0] or y0 < top[1] or y1 > low[3]:
        return False
    if y1 <= top[3]:
        return x1 <= top[2]
    return x1 <= low[2]


def _layout_problems(path: Path) -> tuple[list[str], list[str]]:
    """Đọc khung chữ đã vẽ. Đo lại vùng an toàn thay vì tin cờ của bộ dựng."""
    file = path.with_suffix(".layout.json")
    if not file.exists():
        return ["thiếu file đo bố cục chữ"], []
    layout = json.loads(file.read_text(encoding="utf-8"))
    bad, warn = [], []
    outside = [item for item in layout["elements"] if not _inside(item["box"], layout)]
    for item in outside[:3]:
        bad.append(f"chữ ra ngoài vùng an toàn: «{item['text'][:40]}» ở {item['box']}")
    small = [item for item in layout["elements"] if item["kind"] == "caption" and item["size"] < layout["caption_min"]]
    if small:
        bad.append(f"chữ chạy cỡ {min(item['size'] for item in small)}, dưới {layout['caption_min']}")
    for text in layout.get("warnings", []):
        bad.append(text)
    captions = [item for item in layout["elements"] if item["kind"] == "caption"]
    if not captions:
        bad.append("không có chữ chạy")
    for scene in layout.get("scenes", []):
        if scene.get("low_res"):
            warn.append(f"ảnh {scene.get('outlet')} độ phân giải thấp")
    return bad, warn


def _benchmark() -> dict:
    if not BENCHMARK.exists():
        return {}
    try:
        return json.loads(BENCHMARK.read_text(encoding="utf-8"))
    except Exception:
        return {}


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
    return "short-tien" if Path(item["file"]).name.startswith("short-tien") else "short-tin"


def check(folder: Path) -> tuple[bool, str]:
    manifest = folder / "lich.json"
    if not manifest.exists():
        return False, "KIỂM ĐỊNH: thiếu lich.json, chưa có gì để đăng."
    items = json.loads(manifest.read_text(encoding="utf-8"))
    board = rivals(folder)
    bench = _benchmark()
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
            if not info["fps"] or info["fps"] < 29:
                bad.append(f"{info['fps']} fps, cần ít nhất 29")
            loud = None
            if not info["audio"]:
                bad.append("không có tiếng")
            else:
                loud = _loudness(path)
                if loud is None or not (LUFS_RANGE[0] <= loud <= LUFS_RANGE[1]):
                    bad.append(f"độ to {loud} LUFS, cần {LUFS_RANGE[0]:.0f} đến {LUFS_RANGE[1]:.0f}")
            if length and _dark_frames(path, length) >= 2:
                bad.append("hình đen ở nhiều đoạn")
            layout_bad, layout_warn = _layout_problems(path)
            bad += layout_bad
            warn += layout_warn
            mark = bench.get("tin" if slot == "short-tin" else "tien") or {}
            if mark.get("duration_median"):
                low, high = mark["duration_low"], mark["duration_high"]
                if length > high + 10 or length < low - 10:
                    warn.append(f"dài {length:.0f}s, Short đối thủ {low:.0f}–{high:.0f}s (trung vị {mark['duration_median']:.0f}s)")
                else:
                    warn.append(f"dài {length:.0f}s, trong khoảng Short đối thủ {low:.0f}–{high:.0f}s")
            if loud is not None and mark.get("lufs_median") is not None:
                warn.append(
                    f"độ to {loud:.1f} LUFS, đối thủ trung vị {mark['lufs_median']:.1f}; YouTube phát mọi video ở khoảng -14, video to hơn sẽ bị hạ xuống"
                )
        if not title or len(title) > 100:
            bad.append(f"tiêu đề {len(title)} ký tự, cần 1–100")
        if slot == "short-tien":
            if not re.search(r"\d", title):
                bad.append("tiêu đề bài tiền không có chữ số")
            if "not personal financial advice" not in description.lower():
                bad.append("mô tả thiếu câu not personal financial advice")
        if slot == "short-tin" and not any(name in description for name in OUTLETS):
            bad.append("mô tả Short tin không nêu PBS, NPR hay New York Times")
        if "#Shorts" not in title + description:
            bad.append("Short thiếu #Shorts")
        rival = board.get("tin" if slot == "short-tin" else "tien")
        if rival:
            plain = len(title.replace(" #Shorts", ""))
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
    if bench:
        lines.append("Short đối thủ đã đo (do_doi_thu.py):")
        for kind, data in bench.items():
            if not data.get("count"):
                continue
            label = "tin" if kind == "tin" else "tiền"
            lines.append(
                f"- {label}: {', '.join(data['channels'])}; {data['count']} Short, dài {data['duration_low']:.0f}–{data['duration_high']:.0f}s "
                f"(trung vị {data['duration_median']:.0f}s), độ to trung vị {data['lufs_median']} LUFS"
            )
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
