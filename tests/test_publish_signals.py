from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import PlatformName
from mvpublisher.publishers.signals import build_platform_signal


def test_build_platform_signal_for_autofill_only():
    signal = build_platform_signal(
        PlatformName.WECHAT_CHANNELS,
        ExecutionMode.AUTOFILL_ONLY,
    )

    assert signal.status == "awaiting_manual_publish"
    assert signal.awaiting_manual_publish is True
    assert signal.success_signal == "wechat_channels_editor_ready"
    assert signal.result_url.endswith("/platform/post/create")


def test_build_platform_signal_for_autopublish():
    signal = build_platform_signal(
        PlatformName.DOUYIN,
        ExecutionMode.AUTOPUBLISH,
    )

    assert signal.status == "submitted_for_verification"
    assert signal.awaiting_manual_publish is False
    assert signal.success_signal == "douyin_submit_requested"
