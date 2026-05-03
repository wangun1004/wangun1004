"""SRT subtitle file generation from scene data (no external deps)."""

from __future__ import annotations

from pathlib import Path

import config
from modules.script_generator import Scene


def _seconds_to_srt_time(total_seconds: float) -> str:
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    secs = int(total_seconds % 60)
    millis = int(round((total_seconds - int(total_seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(scenes: list[Scene], output_dir: str = config.OUTPUT_DIR) -> Path:
    """Build a single SRT file covering the full video timeline."""
    blocks: list[str] = []
    cursor = 0.0
    index = 1

    for scene in scenes:
        lines = scene.subtitles or _split_narration(scene.narration)
        if not lines:
            cursor += scene.duration_seconds
            continue

        line_duration = scene.duration_seconds / len(lines)

        for line in lines:
            if not line.strip():
                cursor += line_duration
                continue
            start = _seconds_to_srt_time(cursor)
            end = _seconds_to_srt_time(cursor + line_duration - 0.1)
            blocks.append(f"{index}\n{start} --> {end}\n{line.strip()}\n")
            cursor += line_duration
            index += 1

    out_path = Path(output_dir) / "subtitles.srt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(blocks), encoding="utf-8")
    return out_path


def _split_narration(text: str, max_chars: int = 40) -> list[str]:
    """Split long narration into subtitle-sized chunks."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > max_chars:
            if current:
                lines.append(current.strip())
            current = word
        else:
            current += (" " if current else "") + word
    if current:
        lines.append(current.strip())
    return lines
