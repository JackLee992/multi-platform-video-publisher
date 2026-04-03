from pathlib import Path

import pytest

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import PlatformName, PublishDraft
from mvpublisher.publishers import (
    DouyinPublisher,
    WechatChannelsPublisher,
    XiaohongshuPublisher,
)
from mvpublisher.sessions.playwright_fallback import SessionResolution


def _build_draft(tmp_path: Path, execution_mode: ExecutionMode) -> PublishDraft:
    video = tmp_path / "video.mov"
    video.write_text("video", encoding="utf-8")
    cover = tmp_path / "cover.jpg"
    cover.write_text("cover", encoding="utf-8")
    return PublishDraft.new(source_video_path=video).model_copy(
        update={
            "selected_title": "测试标题",
            "selected_cover_path": cover,
            "summary": "测试摘要",
            "execution_mode": execution_mode,
        }
    )


@pytest.mark.parametrize(
    ("publisher", "platform_name", "module_name"),
    [
        (XiaohongshuPublisher(), PlatformName.XIAOHONGSHU, "xiaohongshu"),
        (DouyinPublisher(), PlatformName.DOUYIN, "douyin"),
        (WechatChannelsPublisher(), PlatformName.WECHAT_CHANNELS, "wechat_channels"),
    ],
)
def test_browser_reuse_publishers_use_current_session_script(
    tmp_path: Path,
    monkeypatch,
    publisher,
    platform_name: PlatformName,
    module_name: str,
) -> None:
    draft = _build_draft(tmp_path, ExecutionMode.AUTOPUBLISH)
    calls: list[tuple[str, PlatformName]] = []

    def fake_script_runner(*, draft, platform_name):
        calls.append((draft.selected_title, platform_name))

    monkeypatch.setattr(
        f"mvpublisher.publishers.{module_name}.run_current_session_publish_script",
        fake_script_runner,
    )

    result = publisher.publish(
        draft=draft,
        session_resolution=SessionResolution(
            mode="browser_reuse",
            state_dir=tmp_path / "state",
        ),
        artifact_root=tmp_path / platform_name.value,
    )

    assert calls == [("测试标题", platform_name)]
    assert result.status == "submitted_for_verification"
