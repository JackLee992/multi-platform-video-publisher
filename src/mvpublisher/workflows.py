import json
from pathlib import Path
from typing import Callable, Mapping, Optional, Protocol

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.media.cover_frames import extract_cover_frames
from mvpublisher.models.draft import PlatformDraft, PlatformName, PublishDraft
from mvpublisher.publishers.base import PublishResult, Publisher
from mvpublisher.publishers.runner import apply_publish_results, run_publishers
from mvpublisher.sessions.playwright_fallback import SessionResolution
from mvpublisher.storage.drafts import DraftRepository
from mvpublisher.suggestions.generator import build_suggestions


class VideoSkillRunner(Protocol):
    def run(self, source_video_path: Path, output_root: Path) -> dict:
        ...


CoverFrameExtractor = Callable[[Path, Path], list[Path]]
SessionFactory = Callable[[PlatformName], SessionResolution]


def create_draft_from_video(
    source_video_path: Path,
    repository: DraftRepository,
    skill_runner: VideoSkillRunner,
    cover_frame_extractor: CoverFrameExtractor = extract_cover_frames,
) -> PublishDraft:
    source_video_path = Path(source_video_path).resolve()
    draft = PublishDraft.new(source_video_path=source_video_path)

    artifact_root = repository.artifact_dir(draft.draft_id)
    pipeline_summary = skill_runner.run(
        source_video_path=source_video_path,
        output_root=artifact_root / "video_skill",
    )
    transcript_payload = _load_transcript_payload(pipeline_summary)
    suggestions = build_suggestions(
        source_video_path=source_video_path,
        transcript_payload=transcript_payload,
    )
    cover_candidate_paths = cover_frame_extractor(
        source_video_path,
        artifact_root / "cover_candidates",
    )

    draft = draft.model_copy(
        update={
            "transcript_artifacts_path": _coerce_optional_path(
                pipeline_summary.get("project_dir")
            ),
            "summary": suggestions.summary,
            "keywords": suggestions.keywords,
            "title_suggestions": suggestions.title_suggestions,
            "cover_suggestions": suggestions.cover_suggestions,
            "cover_candidate_paths": cover_candidate_paths,
            "description_suggestions": suggestions.description_suggestions,
        }
    )
    return repository.save(draft)


def publish_draft_from_repository(
    draft_id: str,
    repository: DraftRepository,
    publishers: Mapping[PlatformName, Publisher],
    session_factory: SessionFactory,
    selected_platforms: Optional[list[PlatformName]] = None,
    execution_mode: Optional[ExecutionMode] = None,
) -> tuple[PublishDraft, list[PublishResult]]:
    draft = repository.load(draft_id)
    if execution_mode is not None:
        draft = draft.model_copy(update={"execution_mode": execution_mode})
    target_platforms = selected_platforms or draft.selected_platforms
    draft_for_publish = draft.model_copy(update={"selected_platforms": target_platforms})
    attempt_number = len(draft.publish_history) + 1
    publish_root = repository.artifact_dir(draft_id) / "publish" / f"attempt-{attempt_number:03d}"
    repository.write_snapshot(draft_for_publish, publish_root / "draft_snapshot.json")
    results = run_publishers(
        draft=draft_for_publish,
        publishers=publishers,
        session_factory=session_factory,
        artifact_root=publish_root,
    )
    result_map = {PlatformName(result.platform_name): result for result in results}
    existing_platform_drafts = {
        platform_draft.platform_name: platform_draft
        for platform_draft in draft.platform_drafts
    }
    for platform_name in target_platforms:
        existing_platform_drafts[platform_name] = PlatformDraft(
            platform_name=platform_name,
            execution_status=result_map[platform_name].status,
            last_error=result_map[platform_name].error_message,
            result_url=result_map[platform_name].result_url,
            artifacts=[
                str(
                    publish_root
                    / platform_name.value
                    / "publish_result.json"
                ),
                str(publish_root / "draft_snapshot.json"),
            ],
        )
    updated_platform_drafts = [
        existing_platform_drafts[platform_name]
        for platform_name in draft.selected_platforms
        if platform_name in existing_platform_drafts
    ]
    updated_draft = apply_publish_results(
        draft.model_copy(update={"platform_drafts": updated_platform_drafts}),
        results,
    )
    saved_draft = repository.save(
        updated_draft
    )
    return saved_draft, results


def _load_transcript_payload(pipeline_summary: dict) -> dict:
    artifacts = pipeline_summary.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return {}

    transcript_json = artifacts.get("transcript_json")
    if not transcript_json:
        return {}

    transcript_path = Path(str(transcript_json))
    if not transcript_path.exists():
        return {}

    return json.loads(transcript_path.read_text(encoding="utf-8"))


def _coerce_optional_path(value: object) -> Optional[Path]:
    if value in (None, ""):
        return None
    return Path(str(value))
