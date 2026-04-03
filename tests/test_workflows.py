import json
from pathlib import Path

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import DraftApprovalStatus, PlatformName
from mvpublisher.publishers.base import PublishResult
from mvpublisher.storage.drafts import DraftRepository
from mvpublisher.workflows import create_draft_from_video, publish_draft_from_repository


class StubSkillRunner:
    def __init__(self, transcript_payload: dict):
        self.transcript_payload = transcript_payload

    def run(self, source_video_path: Path, output_root: Path) -> dict:
        output_root.mkdir(parents=True, exist_ok=True)
        transcript_path = output_root / "transcript.json"
        transcript_path.write_text(
            json.dumps(self.transcript_payload, ensure_ascii=False),
            encoding="utf-8",
        )
        return {
            "project_dir": str(output_root),
            "artifacts": {"transcript_json": str(transcript_path)},
            "source_video": str(source_video_path),
        }


def test_create_draft_from_video_persists_suggestions_and_cover_candidates(tmp_path):
    video = tmp_path / "demo.mp4"
    video.write_text("video", encoding="utf-8")
    repository = DraftRepository(tmp_path / "drafts")

    def fake_cover_extractor(source_video_path: Path, output_dir: Path) -> list[Path]:
        assert source_video_path == video.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        cover_path = output_dir / "frame-01.jpg"
        cover_path.write_text("cover", encoding="utf-8")
        return [cover_path]

    draft = create_draft_from_video(
        source_video_path=video,
        repository=repository,
        skill_runner=StubSkillRunner(
            {"text": "今天聊多平台视频自动发布，减少重复操作。"}
        ),
        cover_frame_extractor=fake_cover_extractor,
    )

    reloaded = repository.load(draft.draft_id)

    assert reloaded.source_video_path == video.resolve()
    assert reloaded.summary
    assert reloaded.title_suggestions
    assert reloaded.description_suggestions
    assert reloaded.cover_suggestions
    assert reloaded.cover_candidate_paths
    assert reloaded.transcript_artifacts_path is not None


def test_publish_draft_from_repository_persists_platform_results(tmp_path):
    video = tmp_path / "demo.mp4"
    cover = tmp_path / "cover.jpg"
    video.write_text("video", encoding="utf-8")
    cover.write_text("cover", encoding="utf-8")
    repository = DraftRepository(tmp_path / "drafts")
    draft = repository.save(
        create_draft_from_video(
            source_video_path=video,
            repository=repository,
            skill_runner=StubSkillRunner({"text": "测试发布内容"}),
            cover_frame_extractor=lambda source_video_path, output_dir: [cover],
        ).model_copy(
            update={
                "selected_title": "最终标题",
                "selected_cover_path": cover,
                "selected_platforms": [PlatformName.XIAOHONGSHU],
                "approval_status": DraftApprovalStatus.APPROVED,
            }
        )
    )

    class FakePublisher:
        platform_name = PlatformName.XIAOHONGSHU.value

        def publish(self, draft, session_resolution, artifact_root):
            artifact_root.mkdir(parents=True, exist_ok=True)
            result = PublishResult(
                platform_name=self.platform_name,
                status="awaiting_manual_publish",
                submitted=False,
                result_url="https://creator.xiaohongshu.com/publish/publish",
                error_message=None,
                execution_mode=ExecutionMode.AUTOFILL_ONLY,
                awaiting_manual_publish=True,
            )
            result.write(artifact_root)
            return result

    saved_draft, results = publish_draft_from_repository(
        draft_id=draft.draft_id,
        repository=repository,
        publishers={PlatformName.XIAOHONGSHU: FakePublisher()},
        session_factory=lambda platform_name: object(),
        execution_mode=ExecutionMode.AUTOFILL_ONLY,
    )

    assert len(results) == 1
    assert saved_draft.platform_drafts[0].platform_name == PlatformName.XIAOHONGSHU
    assert saved_draft.platform_drafts[0].execution_status == "awaiting_manual_publish"
    assert saved_draft.platform_drafts[0].result_url
    assert saved_draft.platform_drafts[0].artifacts
    assert saved_draft.publish_history
    assert saved_draft.publish_history[0].results[0].awaiting_manual_publish is True
