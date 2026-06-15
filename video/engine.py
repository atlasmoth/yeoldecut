from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import math
import uuid

from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    ImageClip,
    concatenate_videoclips,
    vfx,
)
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


VIDEO_SIZE = (1080, 1920)
INK = (32, 24, 18)
PARCHMENT = (237, 218, 181)
PARCHMENT_DARK = (190, 139, 82)
GOLD = (220, 167, 75)
MIN_SCENE_DURATION = 3.4
TITLE_DURATION = 2.8
FINAL_DURATION = 4.2
ON_SCREEN_WORD_LIMIT = 8
ON_SCREEN_CHAR_LIMIT = 54
CAPTION_WORD_LIMIT = 22
CAPTION_CHAR_LIMIT = 150


def _load_font(size: int, bold: bool = False, serif: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    family = "DejaVuSerif" if serif else "DejaVuSans"
    suffix = "-Bold" if bold else ""
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/{family}{suffix}.ttf",
        f"/usr/local/share/fonts/{family}{suffix}.ttf",
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]

    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue

    try:
        return ImageFont.truetype(f"{family}{suffix}.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def _measure(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    text = " ".join((text or "").split())
    if not text:
        return []

    lines: list[str] = []
    current = ""

    for word in text.split(" "):
        candidate = word if not current else f"{current} {word}"
        width, _ = _measure(draw, candidate, font)
        if width <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)
            current = word
        else:
            clipped = word
            while clipped:
                for index in range(len(clipped), 0, -1):
                    piece = clipped[:index]
                    width, _ = _measure(draw, piece, font)
                    if width <= max_width:
                        lines.append(piece)
                        clipped = clipped[index:]
                        break

    if current:
        lines.append(current)

    return lines


def _draw_centered_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    max_width: int,
    line_gap: int = 12,
    stroke: int = 0,
    stroke_fill: tuple[int, int, int] | None = None,
) -> int:
    lines = _wrap_text(draw, text, font, max_width)
    for line in lines:
        width, height = _measure(draw, line, font)
        x = (VIDEO_SIZE[0] - width) // 2
        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill,
            stroke_width=stroke,
            stroke_fill=stroke_fill or fill,
        )
        y += height + line_gap
    return y


def _shorten(text: str | None, limit: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _word_count(text: str | None) -> int:
    return len(" ".join((text or "").split()).split())


def _compact_text(text: str | None, max_words: int, max_chars: int) -> str:
    clean = " ".join((text or "").split())
    if not clean:
        return ""

    words = clean.split()
    clipped = " ".join(words[:max_words])
    clipped = _shorten(clipped, max_chars)
    clipped = clipped.rstrip(" ,;:-")

    if clipped and clipped != clean and not clipped.endswith("..."):
        return f"{clipped}..."
    return clipped


def _parchment_base(size: tuple[int, int] = VIDEO_SIZE) -> Image.Image:
    image = Image.new("RGB", size, PARCHMENT)
    draw = ImageDraw.Draw(image)
    for inset, color in [(34, INK), (48, PARCHMENT_DARK), (62, INK)]:
        draw.rounded_rectangle(
            (inset, inset, size[0] - inset, size[1] - inset),
            radius=22,
            outline=color,
            width=4 if inset != 48 else 2,
        )
    return image


def _save_title_card(
    out_path: Path,
    title: str,
    subtitle: str,
    eyebrow: str = "YeOldeCut presents",
) -> str:
    image = _parchment_base()
    draw = ImageDraw.Draw(image)
    eyebrow_font = _load_font(42, serif=False)
    title_font = _load_font(96, bold=True)
    subtitle_font = _load_font(44)

    y = 420
    y = _draw_centered_wrapped(draw, eyebrow.upper(), y, eyebrow_font, PARCHMENT_DARK, 900, line_gap=10)
    y += 74
    y = _draw_centered_wrapped(draw, _shorten(title, 62), y, title_font, INK, 920, line_gap=20)
    y += 58
    _draw_centered_wrapped(draw, _compact_text(subtitle, 20, 124), y, subtitle_font, INK, 840, line_gap=14)

    draw.line((190, 1240, 890, 1240), fill=PARCHMENT_DARK, width=5)
    _draw_centered_wrapped(draw, "A tiny-model cinematic roast", 1290, subtitle_font, INK, 840)

    image.save(out_path)
    return str(out_path)


def _save_final_card(out_path: Path, title: str, caption: str) -> str:
    image = _parchment_base()
    draw = ImageDraw.Draw(image)
    title_font = _load_font(80, bold=True)
    caption_font = _load_font(42)
    small_font = _load_font(34, serif=False)

    y = 520
    y = _draw_centered_wrapped(draw, _shorten(title, 76), y, title_font, INK, 920, line_gap=20)
    y += 76
    y = _draw_centered_wrapped(draw, _compact_text(caption, 24, 150), y, caption_font, INK, 860, line_gap=16)
    y += 84
    _draw_centered_wrapped(draw, "Generated with YeOldeCut", y, small_font, PARCHMENT_DARK, 840)

    image.save(out_path)
    return str(out_path)


def _save_scene_card(out_path: Path, image_path: str | None, scene: dict[str, Any], index: int) -> str:
    size = VIDEO_SIZE

    if image_path and Path(image_path).exists():
        source = Image.open(image_path).convert("RGB")
        background = ImageOps.fit(source, size).filter(ImageFilter.GaussianBlur(28))
        dim = Image.new("RGBA", size, (22, 16, 12, 166))
        image = Image.alpha_composite(background.convert("RGBA"), dim)

        foreground = ImageOps.contain(source, (940, 940))
        x = (size[0] - foreground.width) // 2
        y = 310
        shadow = Image.new("RGBA", (foreground.width + 34, foreground.height + 34), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle((0, 0, shadow.width - 1, shadow.height - 1), radius=28, fill=(0, 0, 0, 110))
        image.alpha_composite(shadow, (x - 17, y - 10))
        frame = Image.new("RGBA", (foreground.width + 26, foreground.height + 26), (245, 226, 190, 255))
        image.alpha_composite(frame, (x - 13, y - 13))
        image.paste(foreground, (x, y))
    else:
        image = _parchment_base().convert("RGBA")

    draw = ImageDraw.Draw(image)
    tag_font = _load_font(34, bold=True, serif=False)
    title_font = _load_font(58, bold=True)
    caption_font = _load_font(38)

    tag = f"Scene {index + 1}"
    draw.rounded_rectangle((78, 90, 1002, 166), radius=24, fill=(237, 218, 181, 232), outline=GOLD, width=3)
    _draw_centered_wrapped(draw, tag.upper(), 108, tag_font, INK, 840)

    on_screen = scene.get("on_screen_text") or scene.get("scene_template") or "The court considers the evidence"
    _draw_centered_wrapped(
        draw,
        _compact_text(on_screen, ON_SCREEN_WORD_LIMIT, ON_SCREEN_CHAR_LIMIT),
        188,
        title_font,
        (250, 235, 207),
        900,
        line_gap=12,
        stroke=3,
        stroke_fill=(0, 0, 0),
    )

    narration = scene.get("narration") or ""
    panel_top = 1392
    draw.rounded_rectangle(
        (88, panel_top, 992, 1718),
        radius=28,
        fill=(30, 22, 16, 222),
        outline=(237, 218, 181, 230),
        width=3,
    )
    _draw_centered_wrapped(
        draw,
        _compact_text(narration, CAPTION_WORD_LIMIT, CAPTION_CHAR_LIMIT),
        panel_top + 38,
        caption_font,
        (252, 239, 214),
        780,
        line_gap=12,
    )

    image.convert("RGB").save(out_path)
    return str(out_path)


def _duration_for(path: str | None) -> float:
    if not path:
        return 0.0
    clip = None
    try:
        clip = AudioFileClip(path)
        return float(clip.duration or 0.0)
    except Exception:
        return 0.0
    finally:
        if clip is not None:
            clip.close()


def _scene_durations(scenes: list[dict[str, Any]], target_total: float) -> list[float]:
    if not scenes:
        return []

    raw = []
    for scene in scenes:
        narration_words = _word_count(scene.get("narration"))
        screen_words = _word_count(scene.get("on_screen_text") or scene.get("scene_template"))
        estimated = max(MIN_SCENE_DURATION, (narration_words / 2.45) + (screen_words * 0.18) + 0.9)
        try:
            model_duration = float(scene.get("duration_seconds") or 0)
        except (TypeError, ValueError):
            model_duration = 0.0
        raw.append(max(estimated, min(model_duration, 8.0) if model_duration > 0 else 0.0))

    if sum(raw) <= 0:
        return [target_total / len(scenes)] * len(scenes)

    scale = target_total / sum(raw)
    return [max(MIN_SCENE_DURATION, value * scale) for value in raw]


def _close_all(clips: Iterable[Any]) -> None:
    for clip in clips:
        if clip is None:
            continue
        close = getattr(clip, "close", None)
        if close:
            close()


def _with_transitions(clips: list[ImageClip], duration: float = 0.55) -> list[ImageClip]:
    if len(clips) < 2:
        return clips

    transitioned: list[ImageClip] = []
    for index, clip in enumerate(clips):
        effects = []
        if index > 0:
            effects.append(vfx.CrossFadeIn(duration))
        if index < len(clips) - 1:
            effects.append(vfx.CrossFadeOut(duration))
        transitioned.append(clip.with_effects(effects) if effects else clip)
    return transitioned


def compose_movie(
    script: dict[str, Any],
    image_paths: list[str],
    narration_path: str,
    music_path: str | None,
    out_dir: str | Path = "outputs",
    fps: int = 24,
    transition_seconds: float = 0.55,
) -> str:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slide_dir = out_dir / "slides"
    slide_dir.mkdir(parents=True, exist_ok=True)

    scenes = list(script.get("scenes") or [])
    movie_title = script.get("movie_title") or "The Court of Tiny Sorrows"
    logline = script.get("logline") or "A small model makes a grand spectacle of a small heartbreak."
    final_card = script.get("final_card") or "Thus concludes the judgment."
    share_caption = script.get("share_caption") or "I fed a rejection text to YeOldeCut and received a medieval roast film."

    title_duration = TITLE_DURATION
    final_duration = FINAL_DURATION
    narration_duration = _duration_for(narration_path)
    clip_count = len(scenes) + 2
    overlap_total = transition_seconds * max(0, clip_count - 1)
    target_scene_total = max(
        narration_duration - title_duration - final_duration + overlap_total,
        len(scenes) * MIN_SCENE_DURATION,
        12.0,
    )
    scene_durations = _scene_durations(scenes, target_scene_total)

    slide_paths: list[tuple[str, float]] = []
    title_path = slide_dir / "title.png"
    slide_paths.append((_save_title_card(title_path, script.get("title_card") or movie_title, logline), title_duration))

    for index, scene in enumerate(scenes):
        image_path = image_paths[index] if index < len(image_paths) else None
        scene_path = slide_dir / f"scene-{index + 1:02d}.png"
        duration = scene_durations[index] if index < len(scene_durations) else 4.0
        slide_paths.append((_save_scene_card(scene_path, image_path, scene, index), duration))

    outro_path = slide_dir / "final.png"
    slide_paths.append((_save_final_card(outro_path, final_card, share_caption), final_duration))

    clips = [ImageClip(path).with_duration(duration) for path, duration in slide_paths]
    transitioned_clips = _with_transitions(clips, duration=transition_seconds)
    video = None
    audio = None
    audio_clips = []
    output_path = out_dir / f"{uuid.uuid4()}.mp4"

    try:
        video = concatenate_videoclips(
            transitioned_clips,
            method="compose",
            padding=-transition_seconds if len(transitioned_clips) > 1 else 0,
        )

        if music_path:
            music = AudioFileClip(music_path).with_volume_scaled(0.14)
            if music.duration and music.duration > video.duration:
                music = music.subclipped(0, video.duration)
            audio_clips.append(music)

        voice = AudioFileClip(narration_path).with_volume_scaled(1.0)
        audio_clips.append(voice)

        audio = CompositeAudioClip(audio_clips)
        video = video.with_audio(audio)
        video.write_videofile(
            str(output_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            audio_fps=44100,
            preset="medium",
            threads=max(1, min(4, math.floor((fps or 24) / 8))),
            ffmpeg_params=["-movflags", "+faststart"],
            pixel_format="yuv420p",
            logger=None,
        )
    finally:
        _close_all([video, audio, *audio_clips, *transitioned_clips, *clips])

    return str(output_path)
