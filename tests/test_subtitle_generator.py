"""Unit tests for subtitle generator (no external API needed)."""

import sys
import os
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.subtitle_generator import _split_narration, generate_srt, _seconds_to_srt_time
from modules.script_generator import Scene


class TestSplitNarration(unittest.TestCase):
    def test_short_text_single_line(self):
        lines = _split_narration("안녕하세요", max_chars=40)
        self.assertEqual(lines, ["안녕하세요"])

    def test_long_text_splits_correctly(self):
        text = "이것은 매우 긴 텍스트입니다 여러 줄로 나뉘어야 합니다 자막이 잘 표시됩니다"
        lines = _split_narration(text, max_chars=20)
        self.assertGreater(len(lines), 1)

    def test_empty_text(self):
        lines = _split_narration("", max_chars=40)
        self.assertEqual(lines, [])


class TestSecondsToSrtTime(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(_seconds_to_srt_time(0.0), "00:00:00,000")

    def test_one_hour(self):
        self.assertEqual(_seconds_to_srt_time(3600.0), "01:00:00,000")

    def test_millis(self):
        result = _seconds_to_srt_time(1.5)
        self.assertEqual(result, "00:00:01,500")

    def test_full(self):
        result = _seconds_to_srt_time(3723.25)
        self.assertEqual(result, "01:02:03,250")


class TestGenerateSrt(unittest.TestCase):
    def test_generates_srt_file(self):
        scenes = [
            Scene(index=1, title="씬 1", narration="안녕하세요 테스트입니다",
                  image_prompt="test", duration_seconds=10,
                  subtitles=["안녕하세요", "테스트입니다"]),
            Scene(index=2, title="씬 2", narration="두 번째 씬입니다",
                  image_prompt="test2", duration_seconds=10,
                  subtitles=["두 번째 씬입니다"]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            srt_path = generate_srt(scenes, output_dir=tmp)
            self.assertTrue(srt_path.exists())
            content = srt_path.read_text(encoding="utf-8")
            self.assertIn("안녕하세요", content)
            self.assertIn("두 번째 씬입니다", content)

    def test_timing_is_sequential(self):
        scenes = [
            Scene(index=1, title="S1", narration="텍스트", image_prompt="p",
                  duration_seconds=5, subtitles=["첫 번째", "두 번째"]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            srt_path = generate_srt(scenes, output_dir=tmp)
            content = srt_path.read_text(encoding="utf-8")
            self.assertIn("00:00:00", content)

    def test_srt_format_arrows(self):
        scenes = [
            Scene(index=1, title="S1", narration="텍스트", image_prompt="p",
                  duration_seconds=10, subtitles=["자막"]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            srt_path = generate_srt(scenes, output_dir=tmp)
            content = srt_path.read_text(encoding="utf-8")
            self.assertIn("-->", content)


if __name__ == "__main__":
    unittest.main()
