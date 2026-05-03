"""Text-to-speech audio generation.

Priority:
  1. ElevenLabs (high quality, requires API key)
  2. gTTS (free, Google TTS, no API key needed)
"""

from __future__ import annotations

import os
from pathlib import Path

from tenacity import retry, stop_after_attempt, wait_exponential

import config
from modules.script_generator import Scene


class TTSGenerator:
    def __init__(self, output_dir: str = config.OUTPUT_DIR):
        self._audio_dir = Path(output_dir) / "audio"
        self._audio_dir.mkdir(parents=True, exist_ok=True)
        self._use_elevenlabs = bool(config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE_ID)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _elevenlabs_tts(self, text: str, out_path: Path) -> None:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import VoiceSettings

        client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
        audio = client.text_to_speech.convert(
            voice_id=config.ELEVENLABS_VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.75),
        )
        with out_path.open("wb") as f:
            for chunk in audio:
                f.write(chunk)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _gtts(self, text: str, out_path: Path) -> None:
        from gtts import gTTS

        lang = config.LANGUAGE if config.LANGUAGE in ("ko", "en", "ja", "zh") else "ko"
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(str(out_path))

    def generate_scene_audio(self, scene: Scene) -> Path:
        out_path = self._audio_dir / f"scene_{scene.index:03d}.mp3"
        if out_path.exists():
            return out_path

        text = scene.narration
        if self._use_elevenlabs:
            self._elevenlabs_tts(text, out_path)
        else:
            self._gtts(text, out_path)
        return out_path

    def generate_all(self, scenes: list[Scene]) -> list[Path]:
        return [self.generate_scene_audio(scene) for scene in scenes]
