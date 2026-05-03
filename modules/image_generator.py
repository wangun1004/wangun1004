"""Scene image generation using DALL-E 3."""

from __future__ import annotations

import os
from pathlib import Path

import requests
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

import config
from modules.script_generator import Scene


class ImageGenerator:
    def __init__(self, output_dir: str = config.OUTPUT_DIR):
        self._client = OpenAI(api_key=config.OPENAI_API_KEY)
        self._img_dir = Path(output_dir) / "images"
        self._img_dir.mkdir(parents=True, exist_ok=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=30))
    def generate_scene_image(self, scene: Scene) -> Path:
        """Generate a 16:9 image for a scene and save it locally."""
        out_path = self._img_dir / f"scene_{scene.index:03d}.png"
        if out_path.exists():
            return out_path

        prompt = (
            f"{scene.image_prompt}, "
            "cinematic photography, ultra-detailed, 8k resolution, "
            "professional lighting, vibrant colors, widescreen 16:9"
        )

        response = self._client.images.generate(
            model=config.IMAGE_MODEL,
            prompt=prompt[:4000],
            size=config.IMAGE_SIZE,
            quality="hd",
            n=1,
        )

        image_url = response.data[0].url
        img_data = requests.get(image_url, timeout=60).content
        out_path.write_bytes(img_data)
        return out_path

    def generate_all(self, scenes: list[Scene]) -> list[Path]:
        """Generate images for every scene, return paths in order."""
        paths: list[Path] = []
        for scene in scenes:
            path = self.generate_scene_image(scene)
            paths.append(path)
        return paths
