"""AI-powered script and scene breakdown generator using Claude."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

import config


@dataclass
class Scene:
    index: int
    title: str
    narration: str          # TTS text
    image_prompt: str       # DALL-E prompt
    duration_seconds: int
    subtitles: list[str] = field(default_factory=list)  # split lines


@dataclass
class VideoScript:
    topic: str
    youtube_title: str
    youtube_description: str
    youtube_tags: list[str]
    intro_hook: str
    scenes: list[Scene]
    outro: str
    total_duration: int = 0

    def __post_init__(self):
        self.total_duration = sum(s.duration_seconds for s in self.scenes)


_SYSTEM_PROMPT = """당신은 유튜브 바이럴 콘텐츠 전문가입니다.
트렌딩 분석 데이터를 기반으로 시청자를 사로잡는 고품질 유튜브 동영상 스크립트를 작성합니다.
반드시 JSON 형식으로만 응답하세요. 설명이나 마크다운 코드블록 없이 순수 JSON만 반환하세요."""

_USER_PROMPT_TEMPLATE = """
주제: {topic}
목표 길이: 약 {duration}초 (10분)
씬 수: {scene_count}개
언어: {language}

## 트렌딩 벤치마크 데이터
{benchmark}

## 요청사항
위 트렌딩 데이터를 참고하여 "{topic}" 주제의 유튜브 동영상 스크립트를 작성해주세요.

다음 JSON 구조로 반환하세요:
{{
  "youtube_title": "클릭률 높은 제목 (50자 이내)",
  "youtube_description": "SEO 최적화된 설명 (500자)",
  "youtube_tags": ["태그1", "태그2", ...],
  "intro_hook": "처음 5초 훅 멘트",
  "scenes": [
    {{
      "index": 1,
      "title": "씬 제목",
      "narration": "내레이션 전문 (해당 씬 음성 대본, {secs_per_scene}초 분량)",
      "image_prompt": "영어로 작성된 DALL-E 이미지 생성 프롬프트 (photorealistic, cinematic 스타일)",
      "duration_seconds": {secs_per_scene},
      "subtitles": ["자막 라인1", "자막 라인2", "자막 라인3"]
    }}
  ],
  "outro": "아웃트로 멘트 (구독/좋아요 요청 포함)"
}}

각 씬의 narration은 실제 음성으로 읽을 때 정확히 {secs_per_scene}초가 되도록 작성하세요.
subtitles는 narration을 3-4줄로 분할한 것입니다.
image_prompt는 반드시 영어로, 16:9 비율의 고퀄리티 장면을 묘사하세요.
"""


class ScriptGenerator:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def generate(self, topic: str, benchmark: dict) -> VideoScript:
        prompt = _USER_PROMPT_TEMPLATE.format(
            topic=topic,
            duration=config.TARGET_DURATION,
            scene_count=config.SCENE_COUNT,
            language="한국어" if config.LANGUAGE == "ko" else "English",
            benchmark=json.dumps(benchmark, ensure_ascii=False, indent=2),
            secs_per_scene=config.SECONDS_PER_SCENE,
        )

        message = self._client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=8192,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()
        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        data = json.loads(raw)

        scenes = [
            Scene(
                index=s["index"],
                title=s["title"],
                narration=s["narration"],
                image_prompt=s["image_prompt"],
                duration_seconds=s.get("duration_seconds", config.SECONDS_PER_SCENE),
                subtitles=s.get("subtitles", []),
            )
            for s in data["scenes"]
        ]

        return VideoScript(
            topic=topic,
            youtube_title=data["youtube_title"],
            youtube_description=data["youtube_description"],
            youtube_tags=data.get("youtube_tags", []),
            intro_hook=data["intro_hook"],
            scenes=scenes,
            outro=data["outro"],
        )
