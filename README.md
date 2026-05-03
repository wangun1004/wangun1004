# YouTube Video Automation Pipeline

유튜브 트렌딩 분석 → AI 스크립트 → 이미지/TTS/자막 생성 → 영상 편집 → 자동 업로드 파이프라인

## 아키텍처

```
main.py (오케스트레이터)
  │
  ├── modules/youtube_search.py   → YouTube Data API로 트렌딩 검색 & 벤치마킹
  ├── modules/script_generator.py → Claude Sonnet으로 스크립트/씬 대본 생성
  ├── modules/image_generator.py  → DALL-E 3으로 씬별 이미지 생성
  ├── modules/tts_generator.py    → ElevenLabs / gTTS로 내레이션 음성 생성
  ├── modules/subtitle_generator.py → SRT 자막 파일 생성
  ├── modules/video_editor.py     → MoviePy + FFmpeg으로 영상 편집 & 렌더링
  └── modules/youtube_uploader.py → OAuth2 인증 후 YouTube 업로드
```

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env
# .env 파일에 API 키 입력
```

## 필요한 API 키

| 서비스 | 용도 | 필수 여부 |
|--------|------|-----------|
| YouTube Data API v3 | 트렌딩 검색 + 업로드 | 필수 |
| Anthropic Claude | 스크립트 생성 | 필수 |
| OpenAI (DALL-E 3) | 씬 이미지 생성 | 필수 |
| ElevenLabs | 고품질 TTS | 선택 (없으면 gTTS 사용) |

## 사용법

```bash
# 기본 실행 (업로드는 private으로)
python main.py --topic "인공지능의 미래"

# 공개 업로드
python main.py --topic "건강한 식습관 10가지" --privacy public

# 업로드 없이 영상만 생성
python main.py --topic "주식 투자 입문" --skip-upload

# 이미지 재생성 없이 (이전 실행 결과 재사용)
python main.py --topic "주식 투자 입문" --skip-images
```

## 파이프라인 흐름

```
1. YouTube 트렌딩 검색 (상위 10개 영상 분석)
       ↓
2. 벤치마크 리포트 생성 (조회수, 참여율, 인기 태그)
       ↓
3. Claude로 스크립트 생성 (12씬 × 50초 = ~10분)
       ↓
4. DALL-E 3으로 씬별 이미지 생성 (1792×1024, 16:9)
       ↓
5. TTS로 내레이션 MP3 생성
       ↓
6. SRT 자막 파일 생성
       ↓
7. MoviePy로 영상 편집 (이미지+음성+자막 합성)
       ↓
8. YouTube 업로드 (제목/설명/태그/썸네일 자동 설정)
```

## 테스트

```bash
python -m pytest tests/ -v
```

## YouTube OAuth2 설정

1. [Google Cloud Console](https://console.cloud.google.com)에서 프로젝트 생성
2. YouTube Data API v3 활성화
3. OAuth2 클라이언트 ID 생성 (데스크톱 앱)
4. `.env`에 `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` 입력
5. 첫 실행 시 브라우저에서 Google 계정 인증
6. `youtube_token.json` 자동 저장 (이후 자동 갱신)

## 출력 파일 구조

```
output/
  images/
    scene_001.png       # DALL-E 생성 이미지
    scene_001_resized.png
    ...
  audio/
    scene_001.mp3       # TTS 음성
    ...
  subtitles.srt         # 전체 자막
  script.json           # 생성된 스크립트
  final_video.mp4       # 최종 영상
```
