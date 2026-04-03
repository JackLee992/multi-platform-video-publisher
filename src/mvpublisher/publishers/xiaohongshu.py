from pathlib import Path

from mvpublisher.models.draft import PlatformName
from mvpublisher.models.draft import PublishDraft
from mvpublisher.sessions.browser_reuse import open_url_in_google_chrome
from mvpublisher.sessions.playwright_fallback import (
    SessionResolution,
    open_url_with_persistent_playwright,
)

from .base import PublishResult


class XiaohongshuPublisher:
    platform_name = PlatformName.XIAOHONGSHU.value
    publish_url = "https://creator.xiaohongshu.com/publish/publish"

    def publish(
        self,
        draft: PublishDraft,
        session_resolution: object,
        artifact_root: Path,
    ) -> PublishResult:
        del draft
        result = PublishResult(
            platform_name=self.platform_name,
            status="paused_for_manual_completion",
            submitted=False,
            result_url=self.publish_url,
            error_message=None,
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
            )
        result.write(artifact_root)
        return result
