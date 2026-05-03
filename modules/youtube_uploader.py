"""YouTube video uploader using OAuth2."""

from __future__ import annotations

import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from tenacity import retry, stop_after_attempt, wait_exponential

import config
from modules.script_generator import VideoScript


def _get_credentials() -> Credentials:
    """Load or refresh OAuth2 credentials, running browser flow if needed."""
    creds = None
    token_file = Path(config.YOUTUBE_TOKEN_FILE)

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), config.YOUTUBE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_config = {
                "installed": {
                    "client_id": config.YOUTUBE_CLIENT_ID,
                    "client_secret": config.YOUTUBE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, config.YOUTUBE_SCOPES)
            creds = flow.run_local_server(port=0)

        token_file.write_text(creds.to_json())
    return creds


class YouTubeUploader:
    def __init__(self):
        creds = _get_credentials()
        self._yt = build("youtube", "v3", credentials=creds)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=60))
    def upload(
        self,
        video_path: Path,
        script: VideoScript,
        thumbnail_path: Path | None = None,
        privacy: str = "private",
    ) -> str:
        """Upload video and optionally set thumbnail. Returns video URL."""
        body = {
            "snippet": {
                "title": script.youtube_title,
                "description": script.youtube_description,
                "tags": script.youtube_tags[:500],
                "categoryId": "22",  # People & Blogs
                "defaultLanguage": config.LANGUAGE,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,  # 10 MB chunks
        )

        request = self._yt.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            _, response = request.next_chunk()

        video_id = response["id"]

        if thumbnail_path and thumbnail_path.exists():
            self._yt.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path)),
            ).execute()

        return f"https://www.youtube.com/watch?v={video_id}"
