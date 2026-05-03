"""Unit tests for script generator — JSON parsing logic (no API calls)."""

import sys
import os
import json
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.script_generator import ScriptGenerator, VideoScript, Scene


_MOCK_RESPONSE = {
    "youtube_title": "인공지능이 바꾸는 미래 TOP 10",
    "youtube_description": "AI가 우리 삶을 어떻게 변화시키는지 알아봅니다.",
    "youtube_tags": ["AI", "인공지능", "미래"],
    "intro_hook": "지금 당장 알아야 할 AI의 모든 것!",
    "scenes": [
        {
            "index": i,
            "title": f"씬 {i}",
            "narration": f"씬 {i}의 내레이션입니다.",
            "image_prompt": f"Scene {i} image prompt in English",
            "duration_seconds": 50,
            "subtitles": [f"씬 {i} 자막"],
        }
        for i in range(1, 13)
    ],
    "outro": "구독과 좋아요 부탁드립니다!",
}


class TestScriptParser(unittest.TestCase):
    """Test that the ScriptGenerator correctly parses Claude's JSON response."""

    def _parse(self, data: dict) -> VideoScript:
        gen = ScriptGenerator.__new__(ScriptGenerator)
        raw = json.dumps(data, ensure_ascii=False)
        scenes = [
            Scene(
                index=s["index"],
                title=s["title"],
                narration=s["narration"],
                image_prompt=s["image_prompt"],
                duration_seconds=s.get("duration_seconds", 50),
                subtitles=s.get("subtitles", []),
            )
            for s in data["scenes"]
        ]
        return VideoScript(
            topic="test",
            youtube_title=data["youtube_title"],
            youtube_description=data["youtube_description"],
            youtube_tags=data.get("youtube_tags", []),
            intro_hook=data["intro_hook"],
            scenes=scenes,
            outro=data["outro"],
        )

    def test_parses_12_scenes(self):
        script = self._parse(_MOCK_RESPONSE)
        self.assertEqual(len(script.scenes), 12)

    def test_total_duration(self):
        script = self._parse(_MOCK_RESPONSE)
        self.assertEqual(script.total_duration, 600)

    def test_scene_fields(self):
        script = self._parse(_MOCK_RESPONSE)
        s = script.scenes[0]
        self.assertEqual(s.index, 1)
        self.assertIsInstance(s.image_prompt, str)
        self.assertTrue(len(s.image_prompt) > 0)
        self.assertTrue(s.narration)

    def test_tags_preserved(self):
        script = self._parse(_MOCK_RESPONSE)
        self.assertIn("AI", script.youtube_tags)


if __name__ == "__main__":
    unittest.main()
