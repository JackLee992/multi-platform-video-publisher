from pathlib import Path

from datetime import datetime, timezone
import pytest

import json

from mvpublisher.models.draft import (
    DraftApprovalStatus,
    PlatformDraft,
    PlatformName,
    PublishDraft,
)
from mvpublisher.storage.drafts import DraftRepository


def test_repository_round_trip(tmp_path):
    drafts_root = tmp_path / "drafts"
    repo = DraftRepository(drafts_root)
    draft = PublishDraft.new(source_video_path=drafts_root / "demo.mp4")
    artifact_dir = repo.artifact_dir(draft.draft_id)
    draft = draft.model_copy(update={"selected_platforms": [PlatformName.XIAOHONGSHU]})

    saved = repo.save(draft)
    loaded = repo.load(saved.draft_id)

    assert artifact_dir.exists()
    assert artifact_dir.is_dir()
    assert artifact_dir == tmp_path / "artifacts" / draft.draft_id

    assert loaded.draft_id == saved.draft_id
    assert loaded.selected_platforms == [PlatformName.XIAOHONGSHU]
    assert loaded.approval_status == DraftApprovalStatus.DRAFT
    assert loaded.publish_mode == "manual_hold"
    assert loaded.keywords == []


def test_repository_rejects_invalid_draft_id(tmp_path):
    repo = DraftRepository(tmp_path / "drafts")
    draft = PublishDraft.new(source_video_path=tmp_path / "demo.mp4").model_copy(
        update={"draft_id": "../bad-id"}
    )

    with pytest.raises(ValueError):
        repo.save(draft)

    with pytest.raises(ValueError):
        repo.artifact_dir("../bad-id")

    with pytest.raises(ValueError):
        repo.load("../bad-id")


def test_repository_save_refreshes_updated_at(tmp_path):
    repo = DraftRepository(tmp_path / "drafts")
    draft = PublishDraft.new(source_video_path=tmp_path / "demo.mp4").model_copy(
        update={"updated_at": datetime(2000, 1, 1, tzinfo=timezone.utc)}
    )

    saved = repo.save(draft)

    assert saved.updated_at > draft.updated_at
    loaded = repo.load(saved.draft_id)
    assert loaded.updated_at == saved.updated_at


def test_repository_load_reconciles_extra_platform_drafts(tmp_path):
    repo = DraftRepository(tmp_path / "drafts")
    draft = PublishDraft.new(source_video_path=tmp_path / "demo.mp4").model_copy(
        update={
            "selected_platforms": [PlatformName.XIAOHONGSHU],
            "platform_drafts": [PlatformDraft(platform_name=PlatformName.XIAOHONGSHU)],
        }
    )
    saved = repo.save(draft)
    payload = json.loads((tmp_path / "drafts" / f"{saved.draft_id}.json").read_text(encoding="utf-8"))
    payload["platform_drafts"].append({"platform_name": "douyin", "enabled": True})
    (tmp_path / "drafts" / f"{saved.draft_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    loaded = repo.load(saved.draft_id)

    assert loaded.selected_platforms == [PlatformName.XIAOHONGSHU]
    assert [item.platform_name for item in loaded.platform_drafts] == [
        PlatformName.XIAOHONGSHU
    ]
