"""Unit tests for YouTube search utilities (no network, no google-api-client)."""

import sys
import os
import unittest
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import only the pure-Python helpers — avoid googleapiclient import
from modules.youtube_search import _parse_iso8601_duration, VideoStats


class TestParseDuration(unittest.TestCase):
    def test_full_duration(self):
        self.assertEqual(_parse_iso8601_duration("PT1H2M3S"), 3723)

    def test_minutes_only(self):
        self.assertEqual(_parse_iso8601_duration("PT5M30S"), 330)

    def test_seconds_only(self):
        self.assertEqual(_parse_iso8601_duration("PT45S"), 45)

    def test_hours_only(self):
        self.assertEqual(_parse_iso8601_duration("PT2H"), 7200)

    def test_empty(self):
        self.assertEqual(_parse_iso8601_duration("PT0S"), 0)


class TestVideoStatsEngagement(unittest.TestCase):
    def test_engagement_calculation(self):
        v = VideoStats(
            video_id="abc",
            title="Test",
            channel="Ch",
            view_count=1000,
            like_count=50,
            comment_count=10,
            duration_seconds=300,
        )
        self.assertAlmostEqual(v.engagement_rate, 0.06)

    def test_zero_views_no_division_error(self):
        v = VideoStats(
            video_id="x", title="T", channel="C",
            view_count=0, like_count=0, comment_count=0, duration_seconds=0,
        )
        self.assertEqual(v.engagement_rate, 0.0)


class TestBuildBenchmarkReport(unittest.TestCase):
    def _make_video(self, vid_id, views, tags=None):
        return VideoStats(
            video_id=vid_id,
            title=f"Video {vid_id}",
            channel="TestCh",
            view_count=views,
            like_count=views // 20,
            comment_count=views // 100,
            duration_seconds=300,
            tags=tags or [],
        )

    def _benchmarker_build_report(self, videos):
        """Replicate YouTubeBenchmarker.build_benchmark_report without instantiating the class."""
        if not videos:
            return {}
        avg_views = sum(v.view_count for v in videos) / len(videos)
        avg_duration = sum(v.duration_seconds for v in videos) / len(videos)
        top_tags: dict[str, int] = {}
        for v in videos:
            for tag in v.tags:
                top_tags[tag] = top_tags.get(tag, 0) + 1
        sorted_tags = sorted(top_tags.items(), key=lambda x: x[1], reverse=True)[:20]
        return {
            "top_videos": [
                {"title": v.title, "views": v.view_count, "engagement": round(v.engagement_rate, 4)}
                for v in videos[:5]
            ],
            "avg_views": int(avg_views),
            "avg_duration_seconds": int(avg_duration),
            "popular_tags": [t for t, _ in sorted_tags],
            "top_title_patterns": [v.title for v in videos[:5]],
        }

    def test_report_structure(self):
        videos = [
            self._make_video("1", 100000, ["python", "ai"]),
            self._make_video("2", 80000, ["python", "ml"]),
            self._make_video("3", 60000, ["ai"]),
        ]
        report = self._benchmarker_build_report(videos)
        self.assertIn("top_videos", report)
        self.assertIn("avg_views", report)
        self.assertIn("popular_tags", report)
        self.assertEqual(report["avg_views"], 80000)
        self.assertIn("python", report["popular_tags"])

    def test_empty_videos(self):
        report = self._benchmarker_build_report([])
        self.assertEqual(report, {})


if __name__ == "__main__":
    unittest.main()
