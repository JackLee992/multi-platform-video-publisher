from pathlib import Path
from datetime import datetime, timezone

from mvpublisher.models.draft import PlatformName
from mvpublisher.models.draft import PublishDraft
from mvpublisher.sessions.playwright_fallback import (
    SessionResolution,
    open_url_with_persistent_playwright,
)

from .base import PublishResult
from .chrome_current_session import run_current_session_publish_script
from .signals import build_platform_signal


class WechatChannelsPublisher:
    platform_name = PlatformName.WECHAT_CHANNELS.value
    publish_url = "https://channels.weixin.qq.com/platform/post/create"

    def publish(
        self,
        draft: PublishDraft,
        session_resolution: object,
        artifact_root: Path,
    ) -> PublishResult:
        finished_at = datetime.now(timezone.utc)
        signal = build_platform_signal(PlatformName.WECHAT_CHANNELS, draft.execution_mode)
        result = PublishResult(
            platform_name=self.platform_name,
            status=signal.status,
            submitted=draft.execution_mode.value == "autopublish",
            result_url=signal.result_url,
            error_message=None,
            success_signal=signal.success_signal,
            execution_mode=draft.execution_mode,
            awaiting_manual_publish=signal.awaiting_manual_publish,
            finished_at=finished_at,
        )
        try:
            if isinstance(session_resolution, SessionResolution):
                if session_resolution.mode == "browser_reuse":
                    run_current_session_publish_script(
                        draft=draft,
                        platform_name=PlatformName.WECHAT_CHANNELS,
                    )
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
                result_url=signal.result_url,
                error_message=str(exc),
                error_type=exc.__class__.__name__,
                execution_mode=draft.execution_mode,
                finished_at=finished_at,
            )
        result.write(artifact_root)
        return result
