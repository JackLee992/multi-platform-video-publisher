from pathlib import Path
import json

import pytest

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import DraftApprovalStatus, PlatformName, PublishDraft
from mvpublisher.publishers.base import PublishResult
from mvpublisher.publishers.runner import apply_publish_results, run_publishers
from mvpublisher.publishers.xiaohongshu import XiaohongshuPublisher
from mvpublisher.publishers.douyin import DouyinPublisher
from mvpublisher.publishers.wechat_channels import WechatChannelsPublisher
from mvpublisher.sessions.playwright_fallback import SessionResolution


def build_publish_draft(tmp_path: Path, platforms: list[PlatformName]) -> PublishDraft:
    video = tmp_path / "video.mp4"
    cover = tmp_path / "cover.jpg"
    video.write_text("video")
    cover.write_text("cover")
    return PublishDraft.new(source_video_path=video).model_copy(
        update={
            "selected_title": "Demo title",
            "selected_cover_path": cover,
            "selected_platforms": platforms,
            "approval_status": DraftApprovalStatus.APPROVED,
            "execution_mode": ExecutionMode.AUTOFILL_ONLY,
        }
    )


def test_minimal_publishers_return_paused_manual_completion_result_and_create_artifact_root(tmp_path):
    draft = build_publish_draft(tmp_path, [PlatformName.XIAOHONGSHU])
    platform_cases = [
        (XiaohongshuPublisher(), PlatformName.XIAOHONGSHU.value),
        (DouyinPublisher(), PlatformName.DOUYIN.value),
        (WechatChannelsPublisher(), PlatformName.WECHAT_CHANNELS.value),
    ]

    for publisher, platform in platform_cases:
        artifact_root = tmp_path / platform
        result: PublishResult = publisher.publish(
            draft=draft,
            session_resolution={"platform": platform},
            artifact_root=artifact_root,
        )

        assert result.platform_name == platform
        assert result.status == "awaiting_manual_publish"
        assert result.submitted is False
        assert result.result_url is not None
        assert result.error_message is None
        assert result.awaiting_manual_publish is True
        assert result.execution_mode is ExecutionMode.AUTOFILL_ONLY
        assert artifact_root.exists()
        assert (artifact_root / "publish_result.json").exists()
        assert (artifact_root / "result_summary.txt").exists()
        assert (artifact_root / "page_state.txt").exists()


def test_xiaohongshu_publisher_writes_artifact_on_pause(tmp_path):
    draft = build_publish_draft(tmp_path, [PlatformName.XIAOHONGSHU])
    publisher = XiaohongshuPublisher()
    artifact_root = tmp_path / "artifacts"

    result = publisher.publish(
        draft=draft,
        session_resolution=SessionResolution(
            mode="browser_reuse",
            state_dir=tmp_path / "state",
        ),
        artifact_root=artifact_root,
    )

    assert result.status in {"success", "awaiting_manual_publish", "failed"}
    artifact = artifact_root / "publish_result.json"
    assert artifact.exists()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["platform_name"] == PlatformName.XIAOHONGSHU.value
    assert payload["status"] == result.status
    assert payload["screenshot_path"]


def test_run_publishers_iterates_selected_platforms_and_calls_session_factory(tmp_path):
    draft = build_publish_draft(
        tmp_path,
        [PlatformName.XIAOHONGSHU, PlatformName.DOUYIN],
    )

    requested_platforms: list[PlatformName] = []

    def fake_session_factory(platform_name: PlatformName) -> dict[str, object]:
        requested_platforms.append(platform_name)
        return {"platform": platform_name.value}

    results = run_publishers(
        draft=draft,
        publishers={
            PlatformName.XIAOHONGSHU: XiaohongshuPublisher(),
            PlatformName.DOUYIN: DouyinPublisher(),
            PlatformName.WECHAT_CHANNELS: WechatChannelsPublisher(),
        },
        session_factory=fake_session_factory,
        artifact_root=tmp_path / "artifacts",
    )

    assert len(results) == 2
    assert [result.platform_name for result in results] == [
        PlatformName.XIAOHONGSHU.value,
        PlatformName.DOUYIN.value,
    ]
    assert [result.status for result in results] == [
        "awaiting_manual_publish",
        "awaiting_manual_publish",
    ]
    assert requested_platforms == [
        PlatformName.XIAOHONGSHU,
        PlatformName.DOUYIN,
    ]
    assert [result.submitted for result in results] == [False, False]
    assert all(result.result_url for result in results)
    assert [result.error_message for result in results] == [None, None]
    assert (tmp_path / "artifacts" / PlatformName.XIAOHONGSHU.value).is_dir()
    assert (tmp_path / "artifacts" / PlatformName.DOUYIN.value).is_dir()
    assert not (tmp_path / "artifacts" / PlatformName.WECHAT_CHANNELS.value).exists()


def test_apply_publish_results_appends_mode_aware_history(tmp_path):
    draft = build_publish_draft(tmp_path, [PlatformName.XIAOHONGSHU])
    results = [
        PublishResult(
            platform_name=PlatformName.XIAOHONGSHU.value,
            status="awaiting_manual_publish",
            submitted=False,
            result_url="https://example.com",
            error_message=None,
            success_signal="editor_ready",
            execution_mode=ExecutionMode.AUTOFILL_ONLY,
            awaiting_manual_publish=True,
        )
    ]

    updated = apply_publish_results(draft, results)

    assert len(updated.publish_history) == 1
    assert updated.publish_history[0].execution_mode is ExecutionMode.AUTOFILL_ONLY
    assert updated.publish_history[0].results[0].awaiting_manual_publish is True


def test_run_publishers_requires_approved_draft(tmp_path):
    draft = build_publish_draft(tmp_path, [PlatformName.XIAOHONGSHU]).model_copy(
        update={"approval_status": DraftApprovalStatus.DRAFT}
    )

    with pytest.raises(ValueError, match="approved"):
        run_publishers(
            draft=draft,
            publishers={PlatformName.XIAOHONGSHU: XiaohongshuPublisher()},
            session_factory=lambda platform_name: {"platform": platform_name.value},
            artifact_root=tmp_path / "artifacts",
        )


def test_run_publishers_accepts_only_approved_status_value(tmp_path):
    draft = build_publish_draft(
        tmp_path, [PlatformName.XIAOHONGSHU]
    ).model_copy(update={"approval_status": "approved"})

    results = run_publishers(
        draft=draft,
        publishers={PlatformName.XIAOHONGSHU: XiaohongshuPublisher()},
        session_factory=lambda platform_name: {"platform": platform_name.value},
        artifact_root=tmp_path / "artifacts",
    )

    assert len(results) == 1


def test_publish_draft_rejects_duplicate_selected_platforms(tmp_path):
    video = tmp_path / "video.mp4"
    cover = tmp_path / "cover.jpg"
    video.write_text("video")
    cover.write_text("cover")

    with pytest.raises(ValueError, match="selected_platforms"):
        PublishDraft(
            source_video_path=video,
            selected_title="Demo title",
            selected_cover_path=cover,
            selected_platforms=[
                PlatformName.XIAOHONGSHU,
                PlatformName.XIAOHONGSHU,
            ],
        )
