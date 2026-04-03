from pathlib import Path

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import PlatformName, PublishDraft, ValidationStatus
from mvpublisher.validation.service import ValidationService


def build_ready_draft(tmp_path: Path, title: str = "测试视频发三端") -> PublishDraft:
    source_video = tmp_path / "video.mp4"
    cover_path = tmp_path / "cover.jpg"
    source_video.write_text("video")
    cover_path.write_text("cover")
    return PublishDraft.new(source_video_path=source_video).model_copy(
        update={
            "selected_title": title,
            "selected_cover_path": cover_path,
            "selected_platforms": [PlatformName.XIAOHONGSHU],
            "execution_mode": ExecutionMode.AUTOPUBLISH,
        }
    )


def test_validation_passes_when_required_fields_exist(tmp_path):
    draft = build_ready_draft(tmp_path)

    status, errors = ValidationService().validate(draft)

    assert status is ValidationStatus.PASSED
    assert errors == []


def test_validation_fails_when_required_fields_missing(tmp_path):
    draft = PublishDraft.new(source_video_path=tmp_path / "missing.mp4")

    status, errors = ValidationService().validate(draft)

    assert status is ValidationStatus.FAILED
    assert [error.field for error in errors] == [
        "source_video_path",
        "selected_title",
        "selected_cover_path",
        "selected_platforms",
    ]


def test_validation_enforces_wechat_channels_title_limit(tmp_path):
    draft = build_ready_draft(tmp_path, title="这是一个明显超过十六个中文字符限制的视频号标题")
    draft = draft.model_copy(update={"selected_platforms": [PlatformName.WECHAT_CHANNELS]})

    status, errors = ValidationService().validate(draft)

    assert status is ValidationStatus.FAILED
    assert any(error.platforms == [PlatformName.WECHAT_CHANNELS] for error in errors)
