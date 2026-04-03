from pathlib import Path
from datetime import datetime, timezone

from mvpublisher.models.draft import PlatformName
from mvpublisher.models.draft import PublishDraft
from mvpublisher.sessions.browser_reuse import open_url_in_google_chrome
from mvpublisher.sessions.playwright_fallback import (
    SessionResolution,
    open_url_with_persistent_playwright,
)

from .base import PublishResult


class DouyinPublisher:
    platform_name = PlatformName.DOUYIN.value
    publish_url = "https://creator.douyin.com/creator-micro/content/upload"

    def publish(
        self,
        draft: PublishDraft,
        session_resolution: object,
        artifact_root: Path,
    ) -> PublishResult:
        finished_at = datetime.now(timezone.utc)
        result = PublishResult(
            platform_name=self.platform_name,
            status="awaiting_manual_publish",
            submitted=False,
            result_url=self.publish_url,
            error_message=None,
            success_signal="editor_ready",
            execution_mode=draft.execution_mode,
            awaiting_manual_publish=True,
            finished_at=finished_at,
        )
        try:
            if isinstance(session_resolution, SessionResolution):
                if session_resolution.mode == "browser_reuse":
                    open_url_in_google_chrome(self.publish_url)
                else:
                    open_url_with_persistent_playwright(
                        state_dir=session_resolution.state_dir,
                        url=self.publish_url,
                    )
        except Exception as exc:
            result = PublishResult(
                platform_name=self.platform_name,
                status="failed",
                submitted=False,
                result_url=self.publish_url,
                error_message=str(exc),
                error_type=exc.__class__.__name__,
                execution_mode=draft.execution_mode,
                finished_at=finished_at,
            )
        result.write(artifact_root)
        return result
