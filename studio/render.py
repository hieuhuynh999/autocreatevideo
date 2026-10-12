"""Dựng animatic: lia máy trên storyboard, phụ đề, tiếng nền."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

from studio.images import write_placeholder
from studio.specs import ASPECTS, MAX_SECONDS, MIN_SECONDS, craft_visual_prompt

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 24
FONT_TITLE = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_BODY = Path(r"C:\Windows\Fonts\segoeui.ttf")
MODES = ("in", "out", "right", "left")


def _font(path: Path, size: int) -> ImageFont.ImageFont:
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, limit: int) -> list[str]:
    words = [part for part in text.split() if part]
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
            if len(lines) >= limit:
                break
    if len(lines) < limit:
        lines.append(current)
    if len(lines) > limit:
        lines = lines[:limit]
    return lines


def _cover(image: Image.Image, width: int, height: int) -> Image.Image:
    frame = image.convert("RGB")
    scale = max(width / frame.width, height / frame.height)
    resized = frame.resize((max(1, int(frame.width * scale)), max(1, int(frame.height * scale))), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - width) // 2)
    top = max(0, (resized.height - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def _card(path: Path, width: int, height: int, kicker: str, title: str, subtitle: str) -> None:
    image = Image.new("RGB", (width, height), (12, 10, 8))
    draw = ImageDraw.Draw(image)
    margin = int(width * 0.1)
    kicker_font = _font(FONT_BODY, max(24, width // 36))
    draw.text((margin, int(height * 0.34)), kicker.upper(), font=kicker_font, fill=(230, 194, 122))
    line_y = int(height * 0.34) + kicker_font.size + 18
    draw.rectangle([margin, line_y, margin + int(width * 0.16), line_y + 3], fill=(230, 194, 122))
    title_size = max(42, width // 16)
    title_font = _font(FONT_TITLE, title_size)
    while title_size > 32 and any(
        draw.textlength(line, font=title_font) > width - margin * 2
        for line in _wrap(draw, title, title_font, width - margin * 2, 3)
    ):
        title_size -= 2
        title_font = _font(FONT_TITLE, title_size)
    y = line_y + 28
    for line in _wrap(draw, title or "Phim ngắn", title_font, width - margin * 2, 3):
        draw.text((margin, y), line, font=title_font, fill=(246, 241, 231))
        y += int(title_font.size * 1.18)
    body_font = _font(FONT_BODY, max(22, width // 40))
    y += 16
    for line in _wrap(draw, subtitle, body_font, width - margin * 2, 4):
        draw.text((margin, y), line, font=body_font, fill=(214, 201, 180))
        y += int(body_font.size * 1.35)
    image.save(path, quality=92)


def _subtitle_png(path: Path, text: str, width: int, height: int) -> None:
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    caption = " ".join((text or "").split()).strip()
    if not caption:
        layer.save(path)
        return
    draw = ImageDraw.Draw(layer)
    font = _font(FONT_BODY, max(26, width // 28))
    lines = _wrap(draw, caption, font, int(width * 0.84), 3)
    line_h = int(font.size * 1.35)
    y = height - line_h * len(lines) - int(height * 0.08)
    for line in lines:
        text_width = draw.textlength(line, font=font)
        x = (width - text_width) / 2
        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 248, 236, 255),
            stroke_width=3,
            stroke_fill=(0, 0, 0, 230),
        )
        y += line_h
    layer.save(path)


def _run(args: list[str]) -> None:
    process = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if process.returncode != 0:
        tail = (process.stderr or process.stdout or "ffmpeg lỗi").strip()[-1800:]
        raise RuntimeError(tail)


def _zoom(mode: str, frames: int, width: int, height: int) -> str:
    if mode == "in":
        z, x, y = "min(zoom+0.00115,1.16)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mode == "out":
        z, x, y = "if(eq(on,0),1.16,max(1.0,zoom-0.00115))", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mode == "right":
        z, x, y = "1.1", f"(iw-iw/zoom)*on/{max(frames - 1, 1)}", "(ih-ih/zoom)/2"
    else:
        z, x, y = "1.1", f"(iw-iw/zoom)*(1-on/{max(frames - 1, 1)})", "(ih-ih/zoom)/2"
    return (
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={FPS},"
        f"fade=t=in:st=0:d=0.25,fade=t=out:st={max(0.3, frames / FPS - 0.28):.2f}:d=0.25,format=yuv420p"
    )


def _clip(image: Path, subtitle: Path, dest: Path, width: int, height: int, frames: int, mode: str) -> None:
    graph = f"[0:v]{_zoom(mode, frames, width, height)}[vid];[vid][1:v]overlay=0:0:format=auto[out]"
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-framerate", str(FPS), "-i", str(image),
            "-loop", "1", "-framerate", str(FPS), "-i", str(subtitle),
            "-filter_complex", graph,
            "-map", "[out]",
            "-frames:v", str(frames),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
            str(dest),
        ]
    )


def _prepare_still(source: Path, dest: Path, width: int, height: int) -> None:
    with Image.open(source) as image:
        _cover(image, width * 2, height * 2).save(dest, quality=92)


def _concat(clips: list[Path], dest: Path, list_file: Path) -> None:
    lines = [f"file '{clip.resolve().as_posix()}'" for clip in clips]
    list_file.write_text("\n".join(lines), encoding="utf-8")
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c", "copy", str(dest),
        ]
    )


def _add_bed(video: Path, dest: Path, duration: float) -> None:
    tone = (
        "aevalsrc=0.03*sin(2*PI*110*t)+0.018*sin(2*PI*164.81*t)+0.01*sin(2*PI*220*t)"
        f":s=44100:d={duration:.2f},lowpass=f=1400,"
        "afade=t=in:st=0:d=1.0,"
        f"afade=t=out:st={max(0.2, duration - 1.4):.2f}:d=1.2,volume=0.85"
    )
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(video),
            "-f", "lavfi", "-i", tone,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-shortest", "-movflags", "+faststart",
            str(dest),
        ]
    )


def _prompt_pack(folder: Path, title: str, logline: str, lock: str, style: str, scenes: list[dict]) -> None:
    lines = [
        f"PHIM: {title}",
        f"LOGLINE: {logline}",
        f"KHÓA NHÂN VẬT: {lock}",
        f"PHONG CÁCH: {style}",
        "",
        "Dán khối CHUYỂN ĐỘNG của từng cảnh vào Kling, Hailuo, Veo, Luma hoặc Runway.",
        "Giữ nguyên câu khóa nhân vật ở mọi cảnh để mặt và trang phục không bị đổi.",
        "Ảnh tĩnh dùng để làm storyboard. Video AI chỉ nên tạo sau khi animatic đã đúng nhịp.",
        "",
    ]
    for scene in scenes:
        lines.extend(
            [
                f"CẢNH {scene['index']} — {scene.get('shot', '')}",
                f"HÀNH ĐỘNG: {scene.get('action', '')}",
                f"THOẠI: {scene.get('dialogue', '')}",
                f"PHỤ ĐỀ: {scene.get('subtitle', '')}",
                "HÌNH:",
                craft_visual_prompt(scene.get("image_prompt", ""), style, lock, motion=False),
                "CHUYỂN ĐỘNG:",
                craft_visual_prompt(scene.get("video_prompt", ""), style, lock, motion=True),
                "",
            ]
        )
    (folder / "prompt-video.txt").write_text("\n".join(lines), encoding="utf-8")


def render_film(folder: Path, payload: dict) -> dict:
    aspect = payload.get("aspect") if payload.get("aspect") in ASPECTS else "16:9"
    width, height = ASPECTS[aspect]
    title = str(payload.get("title") or "Phim ngắn")[:80]
    logline = str(payload.get("logline") or "")[:240]
    lock = str(payload.get("lock") or "")[:300]
    style = str(payload.get("style") or "")[:160]
    scenes = payload.get("scenes") or []
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Chưa có cảnh để dựng.")

    work = folder / "_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    _prompt_pack(folder, title, logline, lock, style, scenes)

    clips: list[Path] = []
    title_still = work / "title.jpg"
    _card(title_still, width * 2, height * 2, "Phim ngắn", title, logline)
    _subtitle_png(work / "title.png", "", width, height)
    title_clip = work / "title.mp4"
    _clip(title_still, work / "title.png", title_clip, width, height, int(3.2 * FPS), "in")
    clips.append(title_clip)

    total_frames = int(3.2 * FPS)
    for position, scene in enumerate(scenes):
        index = int(scene.get("index") or position + 1)
        duration = float(scene.get("duration") or 5)
        duration = min(MAX_SECONDS, max(MIN_SECONDS, duration))
        frames = int(duration * FPS)
        source = folder / f"scene_{index:02d}.jpg"
        if not source.is_file():
            write_placeholder(source, width, height, f"Cảnh {index}", str(scene.get("action") or scene.get("subtitle") or ""))
        still = work / f"still_{index:02d}.jpg"
        sub = work / f"sub_{index:02d}.png"
        clip = work / f"clip_{index:02d}.mp4"
        _prepare_still(source, still, width, height)
        caption = str(scene.get("subtitle") or scene.get("dialogue") or "").strip()
        _subtitle_png(sub, caption, width, height)
        _clip(still, sub, clip, width, height, frames, MODES[position % len(MODES)])
        clips.append(clip)
        total_frames += frames

    end_still = work / "end.jpg"
    _card(end_still, width * 2, height * 2, "Hết", title, logline)
    _subtitle_png(work / "end.png", "", width, height)
    end_clip = work / "end.mp4"
    end_frames = int(2.8 * FPS)
    _clip(end_still, work / "end.png", end_clip, width, height, end_frames, "out")
    clips.append(end_clip)
    total_frames += end_frames

    silent = work / "silent.mp4"
    _concat(clips, silent, work / "list.txt")
    final = folder / "phim.mp4"
    duration = total_frames / FPS
    if payload.get("ambient", True):
        try:
            _add_bed(silent, final, duration)
        except RuntimeError:
            shutil.copyfile(silent, final)
    else:
        _run(
            [
                FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(silent), "-c", "copy", "-movflags", "+faststart", str(final),
            ]
        )
    shutil.rmtree(work, ignore_errors=True)
    return {"file": final.name, "seconds": round(duration, 1)}
