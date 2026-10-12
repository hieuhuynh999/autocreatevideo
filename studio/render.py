"""Dựng animatic: lia máy trên storyboard, phụ đề, lời đọc và nhạc nền."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

from studio.images import write_placeholder
from studio.specs import ASPECTS, MAX_SECONDS, MIN_SECONDS, craft_visual_prompt
from studio.voice import synthesize

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


def _action_clip(pose_a: Path, pose_b: Path, subtitle: Path, dest: Path, width: int, height: int, frames: int) -> None:
    """Đổi hai tư thế liên tục để thấy vẫy tay, vỗ tay, nhảy."""
    duration = frames / FPS
    fade_out = max(0.2, duration - 0.2)
    fit = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={FPS},format=yuv420p"
    graph = (
        f"[0:v]{fit}[base];"
        f"[1:v]{fit}[alt];"
        "[base][alt]overlay=enable='lt(mod(t\\,0.64)\\,0.32)'[flip];"
        f"[flip]fade=t=in:st=0:d=0.12,fade=t=out:st={fade_out:.2f}:d=0.16[vid];"
        "[vid][2:v]overlay=0:0:format=auto,format=yuv420p[out]"
    )
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-t", f"{duration:.3f}", "-i", str(pose_a),
            "-loop", "1", "-t", f"{duration:.3f}", "-i", str(pose_b),
            "-loop", "1", "-t", f"{duration:.3f}", "-i", str(subtitle),
            "-filter_complex", graph,
            "-map", "[out]",
            "-frames:v", str(frames),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
            str(dest),
        ]
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


def _media_duration(path: Path) -> float:
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


def _fit_voice(src: Path, dest: Path, limit: float) -> Path:
    length = _media_duration(src)
    if length <= 0 or length <= limit + 0.05:
        return src
    tempo = min(1.8, length / max(limit, 0.45))
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src), "-filter:a", f"atempo={tempo:.3f}",
            "-c:a", "pcm_s16le", str(dest),
        ]
    )
    return dest


def _narration(scene: dict) -> str:
    subtitle = str(scene.get("subtitle") or "").strip()
    dialogue = str(scene.get("dialogue") or "").strip()
    if "—" in subtitle or "–" in subtitle:
        return subtitle
    return dialogue or subtitle


def _music_graph(duration: float, bright: bool) -> str:
    notes = (523.25, 659.25, 783.99) if bright else (196.00, 246.94, 392.00)
    rate = "4.5" if bright else "2.2"
    depth = "0.4" if bright else "0.22"
    volume = "0.20" if bright else "0.13"
    fade_out = max(0.3, duration - 1.3)
    return (
        f"sine=frequency={notes[0]}:sample_rate=44100:duration={duration:.2f}[a];"
        f"sine=frequency={notes[1]}:sample_rate=44100:duration={duration:.2f}[b];"
        f"sine=frequency={notes[2]}:sample_rate=44100:duration={duration:.2f}[c];"
        "[a][b][c]amix=inputs=3:normalize=0,"
        f"tremolo=f={rate}:d={depth},lowpass=f=2400,"
        f"afade=t=in:st=0:d=0.5,afade=t=out:st={fade_out:.2f}:d=1.1,volume={volume}"
    )


def _add_soundtrack(
    video: Path,
    dest: Path,
    duration: float,
    cues: list[tuple[Path, float]],
    music: bool,
    bright: bool,
    work: Path,
) -> None:
    args = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(video)]
    filters: list[str] = []
    labels: list[str] = []
    for index, (path, start) in enumerate(cues):
        args.extend(["-i", str(path)])
        delay = max(0, int(start * 1000))
        label = f"s{index}"
        filters.append(f"[{index + 1}:a]adelay={delay}:all=1,apad=whole_dur={duration:.2f}[{label}]")
        labels.append(f"[{label}]")
    if labels:
        filters.append("".join(labels) + f"amix=inputs={len(labels)}:duration=longest:normalize=0[speech]")
    if music:
        fade_out = max(0.3, duration - 1.2)
        if bright:
            from studio.nursery import write_nursery

            song = write_nursery(work / "nhac_thieu_nhi.wav", duration)
            args.extend(["-i", str(song)])
            bed = (
                f"volume=0.7,afade=t=in:st=0:d=0.35,"
                f"afade=t=out:st={fade_out:.2f}:d=1.0"
            )
        else:
            args.extend(["-f", "lavfi", "-i", _music_graph(duration, False)])
            bed = "anull"
        music_index = 1 + len(cues)
        filters.append(f"[{music_index}:a]{bed}[bed]")
        if labels:
            filters.append("[bed][speech]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[outa]")
        else:
            filters.append("[bed]alimiter=limit=0.95[outa]")
    else:
        filters.append("[speech]alimiter=limit=0.95[outa]")
    args.extend(
        [
            "-filter_complex", ";".join(filters),
            "-map", "0:v", "-map", "[outa]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-shortest", "-movflags", "+faststart",
            str(dest),
        ]
    )
    _run(args)


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
        pose_b = folder / f"scene_{index:02d}_b.jpg"
        if not source.is_file():
            write_placeholder(source, width, height, f"Cảnh {index}", str(scene.get("action") or scene.get("subtitle") or ""))
        still = work / f"still_{index:02d}.jpg"
        sub = work / f"sub_{index:02d}.png"
        clip = work / f"clip_{index:02d}.mp4"
        caption = str(scene.get("subtitle") or scene.get("dialogue") or "").strip()
        _subtitle_png(sub, caption, width, height)
        if pose_b.is_file():
            _action_clip(source, pose_b, sub, clip, width, height, frames)
        else:
            _prepare_still(source, still, width, height)
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
    want_voice = bool(payload.get("voice", True))
    want_music = bool(payload.get("ambient", True))
    cues: list[tuple[Path, float]] = []
    if want_voice:
        title_len = int(3.2 * FPS) / FPS
        spoken_title = synthesize(title, work / "voice_title.mp3")
        if spoken_title:
            cues.append((_fit_voice(spoken_title, work / "voice_title_fit.wav", max(0.8, title_len - 0.5)), 0.25))
        cursor = title_len
        for position, scene in enumerate(scenes):
            scene_len = int(min(MAX_SECONDS, max(MIN_SECONDS, float(scene.get("duration") or 5))) * FPS) / FPS
            spoken = synthesize(_narration(scene), work / f"voice_{position:02d}.mp3")
            if spoken:
                fitted = _fit_voice(spoken, work / f"voice_{position:02d}_fit.wav", max(0.6, scene_len - 0.35))
                cues.append((fitted, cursor + 0.12))
            cursor += scene_len
    bright = "tiếng Anh" in title or any("—" in str(scene.get("subtitle") or "") for scene in scenes)
    if cues or want_music:
        try:
            _add_soundtrack(silent, final, duration, cues, want_music, bright, work)
        except RuntimeError as exc:
            print(f"Không trộn được tiếng: {exc}", flush=True)
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
