"""Video assembly: images + audio + subtitles → final MP4."""

from __future__ import annotations

import os
from pathlib import Path

from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)
from PIL import Image

import config
from modules.script_generator import Scene, VideoScript


def _resize_image(img_path: Path, width: int = config.VIDEO_WIDTH, height: int = config.VIDEO_HEIGHT) -> Path:
    """Resize/crop image to exact video dimensions; return resized path."""
    out = img_path.with_stem(img_path.stem + "_resized")
    if out.exists():
        return out
    with Image.open(img_path) as img:
        img = img.convert("RGB")
        img_ratio = img.width / img.height
        target_ratio = width / height
        if img_ratio > target_ratio:
            new_height = height
            new_width = int(img_ratio * height)
        else:
            new_width = width
            new_height = int(width / img_ratio)
        img = img.resize((new_width, new_height), Image.LANCZOS)
        left = (new_width - width) // 2
        top = (new_height - height) // 2
        img = img.crop((left, top, left + width, top + height))
        img.save(str(out), "PNG")
    return out


def _build_scene_clip(
    scene: Scene,
    img_path: Path,
    audio_path: Path,
) -> CompositeVideoClip:
    """Combine one scene's image + audio + subtitle overlay."""
    resized = _resize_image(img_path)
    audio = AudioFileClip(str(audio_path))
    duration = max(audio.duration, scene.duration_seconds)

    base = (
        ImageClip(str(resized))
        .set_duration(duration)
        .set_fps(config.VIDEO_FPS)
        .set_audio(audio)
    )

    layers: list = [base]

    lines = scene.subtitles or []
    if lines:
        full_text = "\n".join(lines)
        try:
            subtitle = (
                TextClip(
                    full_text,
                    fontsize=config.SUBTITLE_FONT_SIZE,
                    font=config.FONT_PATH if Path(config.FONT_PATH).exists() else "DejaVu-Sans-Bold",
                    color=config.SUBTITLE_COLOR,
                    stroke_color="black",
                    stroke_width=2,
                    method="caption",
                    size=(config.VIDEO_WIDTH - 100, None),
                    align="center",
                )
                .set_duration(duration)
                .set_position(("center", config.VIDEO_HEIGHT - 180))
            )
            layers.append(subtitle)
        except Exception:
            pass  # subtitle render failure is non-fatal

    return CompositeVideoClip(layers, size=(config.VIDEO_WIDTH, config.VIDEO_HEIGHT))


class VideoEditor:
    def __init__(self, output_dir: str = config.OUTPUT_DIR):
        self._out_dir = Path(output_dir)
        self._out_dir.mkdir(parents=True, exist_ok=True)

    def assemble(
        self,
        script: VideoScript,
        image_paths: list[Path],
        audio_paths: list[Path],
    ) -> Path:
        """Concatenate all scene clips into one video file."""
        clips = []
        for scene, img, aud in zip(script.scenes, image_paths, audio_paths):
            clip = _build_scene_clip(scene, img, aud)
            clips.append(clip)

        final = concatenate_videoclips(clips, method="compose")
        out_path = self._out_dir / "final_video.mp4"

        final.write_videofile(
            str(out_path),
            fps=config.VIDEO_FPS,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset="fast",
            ffmpeg_params=["-crf", "23"],
        )
        final.close()
        for c in clips:
            c.close()

        return out_path
