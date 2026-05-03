"""YouTube trending video search and benchmarking."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential

import config


@dataclass
class VideoStats:
    video_id: str
    title: str
    channel: str
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: int
    tags: list[str] = field(default_factory=list)
    description: str = ""
    thumbnail_url: str = ""
    engagement_rate: float = 0.0

    def __post_init__(self):
        if self.view_count > 0:
            self.engagement_rate = (self.like_count + self.comment_count) / self.view_count


def _parse_iso8601_duration(duration: str) -> int:
    """Convert PT1H2M3S → seconds."""
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    m = re.match(pattern, duration)
    if not m:
        return 0
    hours, minutes, seconds = (int(v) if v else 0 for v in m.groups())
    return hours * 3600 + minutes * 60 + seconds


class YouTubeBenchmarker:
    def __init__(self):
        from googleapiclient.discovery import build  # lazy import to avoid broken cryptography
        self._yt = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search_trending(self, topic: str, max_results: int = config.BENCHMARK_MAX_RESULTS) -> list[VideoStats]:
        """Search YouTube for trending videos on a topic and return enriched stats."""
        search_resp = (
            self._yt.search()
            .list(
                q=topic,
                part="id,snippet",
                type="video",
                order="viewCount",
                maxResults=max_results,
                videoDuration="medium",
                relevanceLanguage=config.LANGUAGE,
            )
            .execute()
        )

        video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
        if not video_ids:
            return []

        details_resp = (
            self._yt.videos()
            .list(part="snippet,statistics,contentDetails", id=",".join(video_ids))
            .execute()
        )

        results: list[VideoStats] = []
        for item in details_resp.get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            content = item.get("contentDetails", {})
            thumbnails = snippet.get("thumbnails", {})
            thumb_url = (
                thumbnails.get("maxres", thumbnails.get("high", thumbnails.get("default", {})))
                .get("url", "")
            )
            results.append(
                VideoStats(
                    video_id=item["id"],
                    title=snippet.get("title", ""),
                    channel=snippet.get("channelTitle", ""),
                    view_count=int(stats.get("viewCount", 0)),
                    like_count=int(stats.get("likeCount", 0)),
                    comment_count=int(stats.get("commentCount", 0)),
                    duration_seconds=_parse_iso8601_duration(content.get("duration", "PT0S")),
                    tags=snippet.get("tags", []),
                    description=snippet.get("description", "")[:500],
                    thumbnail_url=thumb_url,
                )
            )

        results.sort(key=lambda v: v.view_count, reverse=True)
        return results

    def build_benchmark_report(self, videos: list[VideoStats]) -> dict:
        """Summarise benchmark findings for the script generator."""
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
