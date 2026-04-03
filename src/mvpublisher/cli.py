from pathlib import Path
import subprocess

import typer

from mvpublisher.config import AppConfig
from mvpublisher.media.video_skill_adapter import VideoSkillAdapter
from mvpublisher.models.draft import PlatformName
from mvpublisher.publishers import (
    DouyinPublisher,
    WechatChannelsPublisher,
    XiaohongshuPublisher,
)
from mvpublisher.sessions import PlatformSessionRequest, resolve_session
from mvpublisher.storage.drafts import DraftRepository
from mvpublisher.web.app import create_app
from mvpublisher.workflows import create_draft_from_video, publish_draft_from_repository


app = typer.Typer(help="Multi-platform video publishing workstation")


@app.command("create-draft")
def create_draft(video_path: str) -> None:
    config = AppConfig.from_env()
    repository = DraftRepository(config.home_dir / "drafts")
    skill_adapter = VideoSkillAdapter(process_video_script=_find_video_skill_script())
    draft = create_draft_from_video(
        source_video_path=Path(video_path),
        repository=repository,
        skill_runner=skill_adapter,
    )
    typer.echo(f"draft_id:{draft.draft_id}")
    typer.echo(f"draft_path:{repository._path(draft.draft_id)}")


@app.command("publish-draft")
def publish_draft(draft_id: str) -> None:
    config = AppConfig.from_env()
    repository = DraftRepository(config.home_dir / "drafts")
    saved_draft, results = publish_draft_from_repository(
        draft_id=draft_id,
        repository=repository,
        publishers=_default_publishers(),
        session_factory=lambda platform_name: resolve_session(
            request=PlatformSessionRequest(platform_name=platform_name.value),
            state_root=config.home_dir / "sessions",
            live_browser_available=True,
        ),
    )
    typer.echo(f"draft_id:{saved_draft.draft_id}")
    for result in results:
        typer.echo(
            f"{result.platform_name}:{result.status}:{result.result_url or ''}"
        )


@app.command("serve-review")
def serve_review(draft_id: str, host: str = "127.0.0.1", port: int = 8000) -> None:
    review_url = f"http://{host}:{port}/drafts/{draft_id}"
    typer.echo(f"serve-review:{draft_id}")
    typer.echo(f"Review URL: {review_url}")
    _open_review_url_in_google_chrome(review_url)
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port)


def _open_review_url_in_google_chrome(url: str) -> None:
    subprocess.Popen(["open", "-a", "Google Chrome", url])

def _find_video_skill_script() -> Path:
    for base in [Path.cwd(), *Path.cwd().parents, Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        candidate = Path(base) / "video-skills-codex" / "scripts" / "process_video.py"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not locate video-skills-codex/scripts/process_video.py")


def _default_publishers() -> dict[PlatformName, object]:
    return {
        PlatformName.XIAOHONGSHU: XiaohongshuPublisher(),
        PlatformName.DOUYIN: DouyinPublisher(),
        PlatformName.WECHAT_CHANNELS: WechatChannelsPublisher(),
    }


if __name__ == "__main__":
    app()
