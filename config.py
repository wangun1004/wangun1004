import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_TOKEN_FILE = "youtube_token.json"
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
IMAGE_SIZE = "1792x1024"
IMAGE_MODEL = "dall-e-3"

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))
TARGET_DURATION = int(os.getenv("TARGET_DURATION", "600"))
LANGUAGE = os.getenv("LANGUAGE", "ko")

BENCHMARK_MAX_RESULTS = 10
SCENE_COUNT = 12
SECONDS_PER_SCENE = TARGET_DURATION // SCENE_COUNT

FONT_PATH = os.path.join("assets", "fonts", "NotoSansKR-Bold.ttf")
SUBTITLE_FONT_SIZE = 48
SUBTITLE_COLOR = "white"
SUBTITLE_BG_COLOR = "rgba(0,0,0,180)"
