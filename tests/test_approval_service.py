from pathlib import Path

import pytest

from mvpublisher.approval.service import ApprovalError, ApprovalService
from mvpublisher.models.draft import DraftApprovalStatus, PlatformName, PublishDraft


def build_approved_ready_draft(tmp_path: Path, *, with_source: bool = True) -> PublishDraft:
    source_video = tmp_path / "video.mp4"
    cover_path = tmp_path / "cover.jpg"
    if with_source:
        source_video.write_text("video")
    cover_path.write_text("cover")
    return PublishDraft.new(source_video_path=source_video).model_copy(
        update={
            "selected_title": "Test title",
            "selected_cover_path": cover_path,
            "selected_platforms": [PlatformName.XIAOHONGSHU],
        }
    )


def test_approve_marks_draft_immediate_when_publish_now(tmp_path):
    draft = build_approved_ready_draft(tmp_path)
    service = ApprovalService()

    result = service.approve(draft=draft, publish_now=True)

    assert result.approval_status == DraftApprovalStatus.APPROVED
    assert result.publish_mode == "immediate"


def test_approve_marks_draft_manual_hold_when_not_publish_now(tmp_path):
    draft = build_approved_ready_draft(tmp_path)
    service = ApprovalService()

    result = service.approve(draft=draft, publish_now=False)

    assert result.approval_status == DraftApprovalStatus.APPROVED
    assert result.publish_mode == "manual_hold"


def test_approve_requires_existing_source_video(tmp_path):
    draft = build_approved_ready_draft(tmp_path, with_source=False)
    service = ApprovalService()

    with pytest.raises(ApprovalError, match="source_video_path"):
        service.approve(draft=draft, publish_now=True)


def test_approve_requires_source_video_to_be_file(tmp_path):
    source_dir = tmp_path / "video-dir"
    source_dir.mkdir()
    cover_path = tmp_path / "cover.jpg"
    cover_path.write_text("cover")
    draft = PublishDraft.new(source_video_path=source_dir).model_copy(
        update={
            "selected_title": "Test title",
            "selected_cover_path": cover_path,
            "selected_platforms": [PlatformName.XIAOHONGSHU],
        }
    )
    service = ApprovalService()

    with pytest.raises(ApprovalError, match="source_video_path"):
        service.approve(draft=draft, publish_now=True)


def test_approve_requires_selected_title(tmp_path):
    source_video = tmp_path / "video.mp4"
    source_video.write_text("video")
    cover_path = tmp_path / "cover.jpg"
    cover_path.write_text("cover")
    draft = PublishDraft.new(source_video_path=source_video).model_copy(
        update={
            "selected_cover_path": cover_path,
            "selected_platforms": [PlatformName.XIAOHONGSHU],
        }
    )
    service = ApprovalService()

    with pytest.raises(ApprovalError, match="selected_title"):
        service.approve(draft=draft, publish_now=True)


def test_approve_rejects_whitespace_only_selected_title(tmp_path):
    source_video = tmp_path / "video.mp4"
    source_video.write_text("video")
    cover_path = tmp_path / "cover.jpg"
    cover_path.write_text("cover")
    draft = PublishDraft.new(source_video_path=source_video).model_copy(
        update={
            "selected_title": "   ",
            "selected_cover_path": cover_path,
            "selected_platforms": [PlatformName.XIAOHONGSHU],
        }
    )
    service = ApprovalService()

    with pytest.raises(ApprovalError, match="selected_title"):
        service.approve(draft=draft, publish_now=True)


def test_approve_requires_existing_selected_cover_path(tmp_path):
    source_video = tmp_path / "video.mp4"
    source_video.write_text("video")
    missing_cover = tmp_path / "missing-cover.jpg"
    draft = PublishDraft.new(source_video_path=source_video).model_copy(
        update={
            "selected_title": "Test title",
            "selected_cover_path": missing_cover,
            "selected_platforms": [PlatformName.XIAOHONGSHU],
        }
    )
    service = ApprovalService()

    with pytest.raises(ApprovalError, match="selected_cover_path"):
        service.approve(draft=draft, publish_now=True)


def test_approve_requires_selected_cover_path_to_be_file(tmp_path):
    source_video = tmp_path / "video.mp4"
    source_video.write_text("video")
    cover_dir = tmp_path / "cover-dir"
    cover_dir.mkdir()
    draft = PublishDraft.new(source_video_path=source_video).model_copy(
        update={
            "selected_title": "Test title",
            "selected_cover_path": cover_dir,
            "selected_platforms": [PlatformName.XIAOHONGSHU],
        }
    )
    service = ApprovalService()

    with pytest.raises(ApprovalError, match="selected_cover_path"):
        service.approve(draft=draft, publish_now=True)


def test_approve_requires_selected_platforms(tmp_path):
    source_video = tmp_path / "video.mp4"
    source_video.write_text("video")
    cover_path = tmp_path / "cover.jpg"
    cover_path.write_text("cover")
    draft = PublishDraft.new(source_video_path=source_video).model_copy(
        update={
            "selected_title": "Test title",
            "selected_cover_path": cover_path,
            "selected_platforms": [],
        }
    )
    service = ApprovalService()

    with pytest.raises(ApprovalError, match="selected_platforms"):
        service.approve(draft=draft, publish_now=True)
