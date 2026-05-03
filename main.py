#!/usr/bin/env python3
"""YouTube Video Automation Pipeline

Usage:
  python main.py --topic "인공지능의 미래"
  python main.py --topic "AI의 미래" --privacy public --skip-upload
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

import config
from modules.youtube_search import YouTubeBenchmarker
from modules.script_generator import ScriptGenerator
from modules.image_generator import ImageGenerator
from modules.tts_generator import TTSGenerator
from modules.subtitle_generator import generate_srt
from modules.video_editor import VideoEditor
from modules.youtube_uploader import YouTubeUploader

console = Console()


def _check_env():
    missing = []
    if not config.YOUTUBE_API_KEY:
        missing.append("YOUTUBE_API_KEY")
    if not config.ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not config.OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if missing:
        console.print(f"[red]Missing environment variables: {', '.join(missing)}[/red]")
        console.print("[yellow]Copy .env.example to .env and fill in your API keys.[/yellow]")
        sys.exit(1)


def _print_benchmark(report: dict):
    table = Table(title="📊 트렌딩 벤치마크", show_header=True)
    table.add_column("제목", style="cyan", max_width=50)
    table.add_column("조회수", justify="right")
    table.add_column("참여율", justify="right")
    for v in report.get("top_videos", []):
        table.add_row(v["title"], f"{v['views']:,}", f"{v['engagement']:.2%}")
    console.print(table)
    console.print(f"  평균 조회수: [green]{report.get('avg_views', 0):,}[/green]")
    console.print(f"  인기 태그: [cyan]{', '.join(report.get('popular_tags', [])[:10])}[/cyan]")


def _print_script_summary(script):
    console.print(Panel(
        f"[bold]{script.youtube_title}[/bold]\n\n"
        f"씬 수: {len(script.scenes)}  |  예상 길이: {script.total_duration}초\n\n"
        f"[italic]{script.youtube_description[:200]}...[/italic]",
        title="📝 생성된 스크립트",
        border_style="green",
    ))


@click.command()
@click.option("--topic", "-t", required=True, help="동영상 주제 (예: '인공지능의 미래')")
@click.option("--privacy", "-p", default="private",
              type=click.Choice(["private", "unlisted", "public"]),
              help="업로드 공개 범위 (기본: private)")
@click.option("--skip-upload", is_flag=True, default=False, help="YouTube 업로드 건너뛰기")
@click.option("--skip-images", is_flag=True, default=False, help="이미지 생성 건너뛰기 (기존 파일 재사용)")
@click.option("--output-dir", default=config.OUTPUT_DIR, help="출력 디렉토리")
def run(topic: str, privacy: str, skip_upload: bool, skip_images: bool, output_dir: str):
    """YouTube 자동화 파이프라인 — 검색 → 스크립트 → 이미지 → TTS → 영상 편집 → 업로드"""

    _check_env()

    console.print(Panel(
        f"[bold cyan]YouTube 자동화 파이프라인 시작[/bold cyan]\n주제: [yellow]{topic}[/yellow]",
        border_style="cyan",
    ))

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    state_file = Path(output_dir) / "pipeline_state.json"
    state: dict = {}

    # ── Step 1: YouTube 트렌딩 검색 & 벤치마킹 ──────────────────────────────
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        task = p.add_task("[cyan]YouTube 트렌딩 분석 중...", total=None)
        benchmarker = YouTubeBenchmarker()
        videos = benchmarker.search_trending(topic)
        report = benchmarker.build_benchmark_report(videos)
        p.update(task, description="[green]✓ 트렌딩 분석 완료")

    _print_benchmark(report)
    state["benchmark"] = report

    # ── Step 2: AI 스크립트 생성 ─────────────────────────────────────────────
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        task = p.add_task("[cyan]Claude로 스크립트 생성 중...", total=None)
        generator = ScriptGenerator()
        script = generator.generate(topic, report)
        p.update(task, description="[green]✓ 스크립트 생성 완료")

    _print_script_summary(script)

    script_path = Path(output_dir) / "script.json"
    script_path.write_text(
        json.dumps(
            {
                "title": script.youtube_title,
                "description": script.youtube_description,
                "tags": script.youtube_tags,
                "scenes": [
                    {"index": s.index, "title": s.title, "narration": s.narration}
                    for s in script.scenes
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    # ── Step 3: 씬별 이미지 생성 ─────────────────────────────────────────────
    image_paths = []
    if not skip_images:
        with Progress(
            SpinnerColumn(), TextColumn("{task.description}"),
            BarColumn(), TimeElapsedColumn(), console=console
        ) as p:
            task = p.add_task("[cyan]이미지 생성 중...", total=len(script.scenes))
            img_gen = ImageGenerator(output_dir)
            for scene in script.scenes:
                path = img_gen.generate_scene_image(scene)
                image_paths.append(path)
                p.advance(task)
                p.update(task, description=f"[cyan]이미지 생성: 씬 {scene.index}/{len(script.scenes)}")
    else:
        img_dir = Path(output_dir) / "images"
        image_paths = sorted(img_dir.glob("scene_*_resized.png")) or sorted(img_dir.glob("scene_*.png"))
        console.print(f"[yellow]이미지 생성 건너뜀 — {len(image_paths)}개 기존 파일 사용[/yellow]")

    # ── Step 4: TTS 음성 생성 ─────────────────────────────────────────────────
    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"),
        BarColumn(), TimeElapsedColumn(), console=console
    ) as p:
        task = p.add_task("[cyan]TTS 음성 생성 중...", total=len(script.scenes))
        tts = TTSGenerator(output_dir)
        audio_paths = []
        for scene in script.scenes:
            path = tts.generate_scene_audio(scene)
            audio_paths.append(path)
            p.advance(task)

    console.print(f"[green]✓ TTS 완료 — {len(audio_paths)}개 오디오 파일[/green]")

    # ── Step 5: 자막 SRT 생성 ────────────────────────────────────────────────
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        task = p.add_task("[cyan]자막 생성 중...", total=None)
        srt_path = generate_srt(script.scenes, output_dir)
        p.update(task, description="[green]✓ 자막 생성 완료")

    console.print(f"[green]✓ SRT 저장: {srt_path}[/green]")

    # ── Step 6: 영상 편집 & 렌더링 ───────────────────────────────────────────
    console.print("[cyan]영상 편집 및 렌더링 시작 (시간이 걸릴 수 있습니다)...[/cyan]")
    editor = VideoEditor(output_dir)
    video_path = editor.assemble(script, image_paths, audio_paths)
    console.print(f"[green]✓ 영상 렌더링 완료: {video_path}[/green]")

    # ── Step 7: YouTube 업로드 ───────────────────────────────────────────────
    if not skip_upload:
        thumbnail_path = image_paths[0] if image_paths else None
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            task = p.add_task("[cyan]YouTube 업로드 중...", total=None)
            uploader = YouTubeUploader()
            url = uploader.upload(video_path, script, thumbnail_path, privacy)
            p.update(task, description="[green]✓ 업로드 완료")

        console.print(Panel(
            f"[bold green]업로드 완료![/bold green]\n\n"
            f"URL: [link={url}]{url}[/link]\n"
            f"공개 범위: [yellow]{privacy}[/yellow]",
            title="🎉 완료",
            border_style="green",
        ))
    else:
        console.print(f"[yellow]업로드 건너뜀. 영상 파일: {video_path}[/yellow]")

    console.print("\n[bold green]파이프라인 완료![/bold green]")


if __name__ == "__main__":
    run()
