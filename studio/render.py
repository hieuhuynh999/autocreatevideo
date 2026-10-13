"""Dựng animatic: lia máy trên storyboard, phụ đề, lời đọc và nhạc nền."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

from studio.images import write_placeholder
from studio.specs import ASPECTS, PHONE_ASPECT, MAX_SECONDS, MIN_SECONDS, craft_visual_prompt
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
    lines = _wrap(draw, caption, font, int(width * 0.84), 2)
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


def _zoom(mode: str, frames: int, width: int, height: int, edge: str = "both") -> str:
    if mode == "in":
        z, x, y = "min(zoom+0.0015,1.12)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mode == "out":
        z, x, y = "if(eq(on,0),1.12,max(1.0,zoom-0.0015))", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mode == "right":
        z, x, y = "1.08", f"(iw-iw/zoom)*on/{max(frames - 1, 1)}", "(ih-ih/zoom)/2"
    else:
        z, x, y = "1.08", f"(iw-iw/zoom)*(1-on/{max(frames - 1, 1)})", "(ih-ih/zoom)/2"
    fades = []
    if edge in {"both", "in"}:
        fades.append("fade=t=in:st=0:d=0.12")
    if edge in {"both", "out"}:
        fades.append(f"fade=t=out:st={max(0.2, frames / FPS - 0.16):.2f}:d=0.14")
    fade = ("," + ",".join(fades)) if fades else ""
    return (
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={FPS}"
        f"{fade},format=yuv420p"
    )


def _clip(
    image: Path,
    subtitle: Path,
    dest: Path,
    width: int,
    height: int,
    frames: int,
    mode: str,
    edge: str = "both",
) -> None:
    graph = f"[0:v]{_zoom(mode, frames, width, height, edge)}[vid];[vid][1:v]overlay=0:0:format=auto[out]"
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


def _cut_sequence(
    images: list[Path],
    subtitle: Path,
    dest: Path,
    work: Path,
    width: int,
    height: int,
    frames: int,
) -> bool:
    """Cắt toàn cảnh, rồi cận hành động, rồi góc nghiêng. Mỗi góc giữ đủ lâu để thấy việc đang làm."""
    usable = [path for path in images if path.is_file()]
    if len(usable) < 2:
        return False
    counts = [frames // len(usable)] * len(usable)
    counts[-1] += frames - sum(counts)
    modes = ("in", "right", "out")
    parts: list[Path] = []
    for index, (image, count) in enumerate(zip(usable, counts)):
        if count < 8:
            continue
        still = work / f"{dest.stem}_still_{index}.jpg"
        part = work / f"{dest.stem}_part_{index}.mp4"
        _prepare_still(image, still, width, height)
        edge = "in" if index == 0 else "out" if index == len(usable) - 1 else "none"
        _clip(still, subtitle, part, width, height, count, modes[index % 3], edge)
        parts.append(part)
    if len(parts) < 2:
        return False
    _concat(parts, dest, work / f"{dest.stem}_cuts.txt")
    return True


def _prepare_still(source: Path, dest: Path, width: int, height: int) -> None:
    with Image.open(source) as image:
        _cover(image, width * 2, height * 2).save(dest, quality=92)


def _layout_b_still(
    source: Path,
    dest: Path,
    width: int,
    height: int,
    title: str,
    english: str,
    vietnamese: str,
) -> None:
    """Tiêu đề trên, hình giữa, tiếng Anh rồi tiếng Việt ở dưới. Chữ không nằm trong ảnh AI."""
    canvas = Image.new("RGB", (width, height), (255, 248, 236))
    draw = ImageDraw.Draw(canvas)
    top = max(64, int(height * 0.11))
    bottom = max(110, int(height * 0.24))
    mid_h = height - top - bottom
    title_font = _font(FONT_TITLE, max(22, width // 24))
    draw.text((width / 2, top / 2), title[:42], anchor="mm", fill=(47, 125, 120), font=title_font)
    with Image.open(source) as image:
        canvas.paste(_cover(image.convert("RGB"), width, mid_h), (0, top))
    en_font = _font(FONT_TITLE, max(20, width // 28))
    vi_font = _font(FONT_BODY, max(18, width // 30))
    y = top + mid_h + 14
    for line in _wrap(draw, english or "", en_font, int(width * 0.9), 2):
        draw.text((width / 2, y), line, anchor="mt", fill=(43, 36, 28), font=en_font)
        y += int(en_font.size * 1.25)
    y += 6
    for line in _wrap(draw, vietnamese or "", vi_font, int(width * 0.9), 2):
        draw.text((width / 2, y), line, anchor="mt", fill=(180, 78, 52), font=vi_font)
        y += int(vi_font.size * 1.25)
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest, quality=92)


def _hold(image: Path, dest: Path, width: int, height: int, frames: int, edge: str) -> None:
    duration = frames / FPS
    fades = []
    if edge in {"both", "in"}:
        fades.append("fade=t=in:st=0:d=0.12")
    if edge in {"both", "out"}:
        fades.append(f"fade=t=out:st={max(0.16, duration - 0.16):.2f}:d=0.14")
    fade = ("," + ",".join(fades)) if fades else ""
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-framerate", str(FPS), "-i", str(image),
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={FPS}{fade},format=yuv420p",
            "-frames:v", str(frames),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
            str(dest),
        ]
    )


def _caption_mask(path: Path, width: int, height: int, title: str, english: str, vietnamese: str) -> tuple[int, int]:
    top = max(64, int(height * 0.11))
    bottom = max(110, int(height * 0.24))
    if (height - top - bottom) % 2:
        bottom += 1
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, width, top], fill=(255, 248, 236, 255))
    draw.rectangle([0, height - bottom, width, height], fill=(255, 248, 236, 255))
    title_font = _font(FONT_TITLE, max(22, width // 24))
    draw.text((width / 2, top / 2), title[:42], anchor="mm", fill=(47, 125, 120, 255), font=title_font)
    en_font = _font(FONT_TITLE, max(20, width // 28))
    vi_font = _font(FONT_BODY, max(18, width // 30))
    y = height - bottom + 14
    for line in _wrap(draw, english or "", en_font, int(width * 0.9), 2):
        draw.text((width / 2, y), line, anchor="mt", fill=(43, 36, 28, 255), font=en_font)
        y += int(en_font.size * 1.25)
    y += 6
    for line in _wrap(draw, vietnamese or "", vi_font, int(width * 0.9), 2):
        draw.text((width / 2, y), line, anchor="mt", fill=(180, 78, 52, 255), font=vi_font)
        y += int(vi_font.size * 1.25)
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    return top, height - top - bottom


def _fit(width: int, height: int, color: str) -> str:
    """Thu video vào khung rồi mới thêm viền. Tránh pad nhỏ hơn hình sau khi làm tròn."""
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"scale=w='min(iw\\,{width})':h='min(ih\\,{height})',"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={color}"
    )


def _place_motion(
    video: Path,
    dest: Path,
    work: Path,
    width: int,
    height: int,
    frames: int,
    subtitle: Path,
    title: str,
    english: str,
    vietnamese: str,
    frame_mode: str,
) -> None:
    """Đặt clip chuyển động vào khung, không kéo méo. Giữ con vật trong hình."""
    duration = frames / FPS
    if frame_mode == "caption":
        mask = work / f"{dest.stem}_mask.png"
        top, mid_h = _caption_mask(mask, width, height, title, english, vietnamese)
        _run(
            [
                FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", f"color=c=0xFFF8EC:s={width}x{height}:r={FPS}:d={duration:.2f}",
                "-i", str(video),
                "-loop", "1", "-i", str(mask),
                "-filter_complex",
                (
                    f"[1:v]{_fit(width, mid_h, '0xFFF8EC')},fps={FPS},"
                    f"tpad=stop_mode=clone:stop_duration={duration + 1:.2f},trim=duration={duration:.2f},setpts=PTS-STARTPTS[vid];"
                    f"[0:v][vid]overlay=0:{top}:shortest=1[base];"
                    "[base][2:v]overlay=0:0:shortest=1,format=yuv420p"
                ),
                "-an", "-frames:v", str(frames),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
                str(dest),
            ]
        )
        return
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(video),
            "-loop", "1", "-i", str(subtitle),
            "-filter_complex",
            (
                f"[0:v]{_fit(width, height, 'black')},fps={FPS},"
                f"tpad=stop_mode=clone:stop_duration={duration + 1:.2f},trim=duration={duration:.2f},setpts=PTS-STARTPTS[vid];"
                "[vid][1:v]overlay=0:0:shortest=1,format=yuv420p"
            ),
            "-an", "-frames:v", str(frames),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
            str(dest),
        ]
    )


def _hold_sequence(images: list[Path], dest: Path, work: Path, width: int, height: int, frames: int) -> None:
    usable = [path for path in images if path.is_file()] or images[:1]
    counts = [frames // len(usable)] * len(usable)
    counts[-1] += frames - sum(counts)
    parts: list[Path] = []
    for index, (image, count) in enumerate(zip(usable, counts)):
        if count < 8:
            continue
        part = work / f"{dest.stem}_hold_{index}.mp4"
        edge = "in" if index == 0 else "out" if index == len(usable) - 1 else "none"
        _hold(image, part, width, height, count, edge)
        parts.append(part)
    if len(parts) == 1:
        shutil.copyfile(parts[0], dest)
        return
    _concat(parts, dest, work / f"{dest.stem}_holds.txt")


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
    tempo = min(1.25, length / max(limit, 0.45))
    _run(
        [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src), "-filter:a", f"atempo={tempo:.3f}",
            "-c:a", "pcm_s16le", str(dest),
        ]
    )
    return dest


def _narration(scene: dict) -> str:
    dialogue = str(scene.get("dialogue") or "").strip()
    subtitle = str(scene.get("subtitle") or "").strip()
    if "—" in dialogue or "–" in dialogue:
        return dialogue
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
                f"volume=0.42,afade=t=in:st=0:d=0.35,"
                f"afade=t=out:st={fade_out:.2f}:d=1.0"
            )
        else:
            args.extend(["-f", "lavfi", "-i", _music_graph(duration, False)])
            bed = "anull"
        music_index = 1 + len(cues)
        filters.append(f"[{music_index}:a]{bed}[bed]")
        if labels:
            filters.append("[speech]asplit=2[sp][key]")
            filters.append("[bed][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[ducked]")
            filters.append("[ducked][sp]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[outa]")
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


def _write_srt(path: Path, rows: list[tuple[float, float, str]]) -> None:
    def stamp(seconds: float) -> str:
        ms = max(0, int(round(seconds * 1000)))
        hours, ms = divmod(ms, 3_600_000)
        minutes, ms = divmod(ms, 60_000)
        secs, ms = divmod(ms, 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

    blocks = []
    for index, (start, end, text) in enumerate(rows, start=1):
        blocks.append(f"{index}\n{stamp(start)} --> {stamp(max(end, start + 0.3))}\n{text}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def render_film(folder: Path, payload: dict) -> dict:
    width, height = ASPECTS[PHONE_ASPECT]
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

    want_voice = bool(payload.get("voice", True))
    warnings: list[str] = []
    spoken: list[Path | None] = []
    lengths: list[float] = []
    for position, scene in enumerate(scenes):
        duration = min(MAX_SECONDS, max(MIN_SECONDS, float(scene.get("duration") or 6)))
        audio = synthesize(_narration(scene), work / f"voice_{position:02d}.mp3") if want_voice else None
        if audio:
            need = _media_duration(audio) + 0.55
            if need > duration + 0.15:
                if need <= MAX_SECONDS:
                    duration = need
                    warnings.append(f"Cảnh {position + 1} được kéo dài để không cắt lời đọc.")
                else:
                    warnings.append(
                        f"Cảnh {position + 1} có câu dài hơn {int(MAX_SECONDS)} giây. Lời được đọc nhanh hơn một chút, không bị cắt cụt."
                    )
        spoken.append(audio)
        lengths.append(duration)

    total_frames = int(3.2 * FPS)
    used_motion = False
    for position, scene in enumerate(scenes):
        index = int(scene.get("index") or position + 1)
        duration = lengths[position]
        frames = int(duration * FPS)
        source = folder / f"scene_{index:02d}.jpg"
        if not source.is_file():
            write_placeholder(source, width, height, f"Cảnh {index}", str(scene.get("action") or scene.get("subtitle") or ""))
        still = work / f"still_{index:02d}.jpg"
        sub = work / f"sub_{index:02d}.png"
        clip = work / f"clip_{index:02d}.mp4"
        caption = str(scene.get("subtitle") or scene.get("dialogue") or "").strip()
        _subtitle_png(sub, caption, width, height)
        motion_file = folder / f"scene_{index:02d}_motion.mp4"
        if motion_file.is_file():
            used_motion = True
            _place_motion(
                motion_file,
                clip,
                work,
                width,
                height,
                frames,
                sub,
                title,
                str(scene.get("line_en") or ""),
                str(scene.get("line_vi") or caption),
                str(payload.get("frame") or "full"),
            )
            clips.append(clip)
            total_frames += frames
            continue
        angles = [
            path
            for path in (
                folder / f"scene_{index:02d}_b.jpg",
                source,
                folder / f"scene_{index:02d}_c.jpg",
            )
            if path.is_file()
        ] or [source]
        if payload.get("frame") == "caption":
            framed: list[Path] = []
            for shot_index, shot in enumerate(angles):
                framed_path = work / f"framed_{index:02d}_{shot_index}.jpg"
                _layout_b_still(
                    shot,
                    framed_path,
                    width,
                    height,
                    title,
                    str(scene.get("line_en") or ""),
                    str(scene.get("line_vi") or caption),
                )
                framed.append(framed_path)
            _hold_sequence(framed, clip, work, width, height, frames)
        elif not _cut_sequence(angles, sub, clip, work, width, height, frames):
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
    want_music = bool(payload.get("ambient", True))
    cues: list[tuple[Path, float]] = []
    srt_rows: list[tuple[float, float, str]] = []
    title_len = int(3.2 * FPS) / FPS
    if want_voice:
        spoken_title = synthesize(title, work / "voice_title.mp3")
        if spoken_title:
            cues.append((_fit_voice(spoken_title, work / "voice_title_fit.wav", max(0.8, title_len - 0.5)), 0.25))
        cursor = title_len
        for position, scene in enumerate(scenes):
            scene_len = int(lengths[position] * FPS) / FPS
            audio = spoken[position]
            if audio:
                fitted = _fit_voice(audio, work / f"voice_{position:02d}_fit.wav", max(0.6, scene_len - 0.35))
                start = cursor + 0.12
                cues.append((fitted, start))
                caption = str(scene.get("subtitle") or scene.get("dialogue") or "").strip()
                if caption:
                    srt_rows.append((start, min(cursor + scene_len - 0.05, start + _media_duration(fitted)), caption))
            cursor += scene_len
    bright = bool(payload.get("kids")) or "tiếng Anh" in title or any("—" in str(scene.get("subtitle") or "") for scene in scenes)
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
    srt = folder / "phu-de.srt"
    _write_srt(srt, srt_rows)
    if bright and want_music:
        (folder / "giay-phep-nhac.txt").write_text(
            "\n".join(
                [
                    "Nhạc: Liên khúc thiếu nhi dân gian",
                    "Tác phẩm: Twinkle Twinkle Little Star; Mary Had a Little Lamb; Frère Jacques",
                    "Giấy phép: giai điệu thuộc phạm vi công cộng. File này do tool tự đánh, không phải bản thu của ca sĩ.",
                    "Được dùng trong video đã xuất. Không cam kết phần mềm nhận diện nhạc sẽ bỏ qua.",
                    "Ngày kiểm tra: 2026-10-12",
                ]
            ),
            encoding="utf-8",
        )
    exports = folder / "xuat"
    exports.mkdir(exist_ok=True)
    version = len(list(exports.glob("phim-*.mp4"))) + 1
    archived = exports / f"phim-{version:02d}.mp4"
    shutil.copyfile(final, archived)
    shutil.rmtree(work, ignore_errors=True)
    return {
        "file": final.name,
        "seconds": round(duration, 1),
        "warnings": warnings,
        "srt": srt.name,
        "export": f"xuat/{archived.name}",
        "motion": "video" if used_motion else "storyboard",
    }


def stitch_videos(paths: list[Path], dest: Path, width: int, height: int) -> float:
    """Ghép vài video, căn khung bằng viền, không kéo méo."""
    if len(paths) < 2:
        raise ValueError("Cần ít nhất hai video để ghép.")
    work = dest.parent / "_ghep"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    parts: list[Path] = []
    fit = (
        f"{_fit(width, height, 'black')},fps={FPS},format=yuv420p"
    )
    for index, path in enumerate(paths):
        part = work / f"part_{index:02d}.mp4"
        _run(
            [
                FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(path),
                "-vf", fit,
                "-c:v", "libx264", "-c:a", "aac", "-ar", "44100", "-ac", "1",
                str(part),
            ]
        )
        parts.append(part)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _concat(parts, dest, work / "list.txt")
    duration = _media_duration(dest)
    shutil.rmtree(work, ignore_errors=True)
    return duration
