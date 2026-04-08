from mvpublisher.config import AppConfig
from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.paths import runtime_root
from pathlib import Path
from datetime import datetime, timezone
import pytest

from mvpublisher.models.draft import (
    CodexDraftReview,
    DraftApprovalStatus,
    PlatformDraft,
    PlatformName,
    PlatformPublishRecord,
    PublishDraft,
    PublishHistoryEntry,
    ValidationError,
    ValidationStatus,
)



def test_app_config_happy_path_env(tmp_path, monkeypatch):
    expected = tmp_path / "runtime-home"
    monkeypatch.setenv("MVPUBLISHER_HOME", str(expected))
    config = AppConfig.from_env()

    assert config.app_name == "mvpublisher"
    assert config.home_dir == expected
    assert not expected.exists()
    assert runtime_root(config).exists()


def test_app_config_default_when_unset(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MVPUBLISHER_HOME", raising=False)
    config = AppConfig.from_env()
    expected = tmp_path / "runtime"

    assert config.app_name == "mvpublisher"
    assert config.home_dir == expected
    assert not expected.exists()
    assert runtime_root(config).exists()


def test_app_config_empty_env_falls_back(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MVPUBLISHER_HOME", "")
    config = AppConfig.from_env()
    expected = tmp_path / "runtime"

    assert config.app_name == "mvpublisher"
    assert config.home_dir == expected
    assert not expected.exists()
    assert runtime_root(config).exists()


def test_publish_draft_requires_confirmation_fields():
    started = datetime.now(timezone.utc)
    draft = PublishDraft.new(source_video_path=Path("/tmp/video.mp4"))
    finished = datetime.now(timezone.utc)

    assert isinstance(draft.draft_id, str)
    assert len(draft.draft_id) == 32
    assert draft.approval_status is DraftApprovalStatus.DRAFT
    assert draft.publish_mode == "manual_hold"
    assert draft.execution_mode is ExecutionMode.AUTOPUBLISH
    assert draft.validation_status is ValidationStatus.UNKNOWN
    assert draft.validation_errors == []
    assert isinstance(draft.created_at, datetime)
    assert isinstance(draft.updated_at, datetime)
    assert draft.created_at.tzinfo == timezone.utc
    assert draft.updated_at.tzinfo == timezone.utc
    assert started <= draft.created_at <= finished
    assert started <= draft.updated_at <= finished
    assert draft.updated_at >= draft.created_at
    assert DraftApprovalStatus.DRAFT.value == "draft"
    assert DraftApprovalStatus.APPROVED.value == "approved"
    assert PlatformName.XIAOHONGSHU.value == "xiaohongshu"
    assert PlatformName.DOUYIN.value == "douyin"
    assert PlatformName.WECHAT_CHANNELS.value == "wechat_channels"
    assert draft.transcript_artifacts_path is None
    assert draft.summary is None
    assert draft.keywords == []
    assert draft.title_suggestions == []
    assert draft.cover_suggestions == []
    assert draft.description_suggestions == []
    assert draft.selected_title is None
    assert draft.selected_cover_path is None
    assert draft.selected_platforms == []
    assert draft.platform_drafts == []
    assert draft.publish_history == []
    assert draft.codex_review is None


def test_platform_draft_shape_contract():
    draft = PlatformDraft(platform_name=PlatformName.XIAOHONGSHU)

    assert draft.platform_name is PlatformName.XIAOHONGSHU
    assert draft.scheduled_time is None
    assert draft.execution_status == "pending"
    assert draft.artifacts == []


def test_publish_draft_supports_validation_and_history_models(tmp_path):
    started = datetime.now(timezone.utc)
    finished = datetime.now(timezone.utc)
    draft = PublishDraft.new(source_video_path=tmp_path / "demo.mp4").model_copy(
        update={
            "execution_mode": ExecutionMode.AUTOFILL_ONLY,
            "validation_status": ValidationStatus.FAILED,
            "validation_errors": [
                ValidationError(
                    field="selected_title",
                    message="selected_title must be present",
                    platforms=[PlatformName.XIAOHONGSHU],
                )
            ],
            "publish_history": [
                PublishHistoryEntry(
                    execution_mode=ExecutionMode.AUTOFILL_ONLY,
                    results=[
                        PlatformPublishRecord(
                            platform_name=PlatformName.XIAOHONGSHU,
                            status="awaiting_manual_publish",
                            started_at=started,
                            finished_at=finished,
                            success_signal="editor_ready",
                            execution_mode=ExecutionMode.AUTOFILL_ONLY,
                            awaiting_manual_publish=True,
                        )
                    ],
                )
            ],
        }
    )

    assert draft.execution_mode is ExecutionMode.AUTOFILL_ONLY
    assert draft.validation_status is ValidationStatus.FAILED
    assert draft.validation_errors[0].field == "selected_title"
    assert draft.publish_history[0].execution_mode is ExecutionMode.AUTOFILL_ONLY
    assert draft.publish_history[0].results[0].awaiting_manual_publish is True
    assert draft.publish_history[0].results[0].success_signal == "editor_ready"


def test_publish_draft_supports_codex_review_payload(tmp_path):
    draft = PublishDraft.new(source_video_path=tmp_path / "demo.mp4").model_copy(
        update={
            "codex_review": CodexDraftReview(
                status="reviewed",
                content_summary="孩子在背诵《悯农》并和镜头互动。",
                refined_transcript="锄禾日当午，汗滴禾下土。谁知盘中餐，粒粒皆辛苦。来背！",
                recommended_title="孩子背诵《悯农》",
                title_candidates=["孩子背诵《悯农》", "莉莉背诗瞬间"],
                notes=["原始转写存在同音错字，已按常见诗句修正。"],
            )
        }
    )

    assert draft.codex_review is not None
    assert draft.codex_review.recommended_title == "孩子背诵《悯农》"
    assert "莉莉背诗瞬间" in draft.codex_review.title_candidates


def test_publish_draft_rejects_invalid_platform_drafts(tmp_path):
    with pytest.raises(ValueError):
        PublishDraft(
            source_video_path=tmp_path / "demo.mp4",
            selected_platforms=[PlatformName.XIAOHONGSHU, PlatformName.DOUYIN],
            platform_drafts=[
                PlatformDraft(platform_name=PlatformName.XIAOHONGSHU),
                PlatformDraft(platform_name=PlatformName.XIAOHONGSHU),
            ],
        )

    with pytest.raises(ValueError):
        PublishDraft(
            source_video_path=tmp_path / "demo.mp4",
            selected_platforms=[PlatformName.XIAOHONGSHU],
            platform_drafts=[PlatformDraft(platform_name=PlatformName.DOUYIN)],
        )

    with pytest.raises(ValueError):
        PublishDraft(
            source_video_path=tmp_path / "demo.mp4",
            selected_platforms=[],
            platform_drafts=[PlatformDraft(platform_name=PlatformName.DOUYIN)],
        )
