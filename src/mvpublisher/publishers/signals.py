from dataclasses import dataclass

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import PlatformName


@dataclass(frozen=True)
class PlatformSignal:
    status: str
    success_signal: str
    awaiting_manual_publish: bool
    result_url: str


def build_platform_signal(
    platform_name: PlatformName,
    execution_mode: ExecutionMode,
) -> PlatformSignal:
    if execution_mode is ExecutionMode.AUTOFILL_ONLY:
        return PlatformSignal(
            status="awaiting_manual_publish",
            success_signal=_autofill_signal_name(platform_name),
            awaiting_manual_publish=True,
            result_url=_editor_url(platform_name),
        )

    return PlatformSignal(
        status="submitted_for_verification",
        success_signal=_autopublish_signal_name(platform_name),
        awaiting_manual_publish=False,
        result_url=_editor_url(platform_name),
    )


def _editor_url(platform_name: PlatformName) -> str:
    return {
        PlatformName.XIAOHONGSHU: "https://creator.xiaohongshu.com/publish/publish",
        PlatformName.DOUYIN: "https://creator.douyin.com/creator-micro/content/upload",
        PlatformName.WECHAT_CHANNELS: "https://channels.weixin.qq.com/platform/post/create",
    }[platform_name]


def _autofill_signal_name(platform_name: PlatformName) -> str:
    return {
        PlatformName.XIAOHONGSHU: "xiaohongshu_editor_ready",
        PlatformName.DOUYIN: "douyin_editor_ready",
        PlatformName.WECHAT_CHANNELS: "wechat_channels_editor_ready",
    }[platform_name]


def _autopublish_signal_name(platform_name: PlatformName) -> str:
    return {
        PlatformName.XIAOHONGSHU: "xiaohongshu_submit_requested",
        PlatformName.DOUYIN: "douyin_submit_requested",
        PlatformName.WECHAT_CHANNELS: "wechat_channels_submit_requested",
    }[platform_name]

