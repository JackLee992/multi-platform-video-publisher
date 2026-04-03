from pathlib import Path
from typing import Callable, Mapping

from mvpublisher.approval.service import ApprovalService
from mvpublisher.models.draft import (
    PlatformName,
    PlatformPublishRecord,
    PublishDraft,
    PublishHistoryEntry,
)

from .base import PublishResult, Publisher


SessionFactory = Callable[[PlatformName], object]


def run_publishers(
    draft: PublishDraft,
    publishers: Mapping[PlatformName, Publisher],
    session_factory: SessionFactory,
    artifact_root: Path,
) -> list[PublishResult]:
    if not ApprovalService().is_approved(draft):
        raise ValueError("Draft must be approved before publishing")

    results: list[PublishResult] = []
    for selected_platform in draft.selected_platforms:
        publisher = publishers[selected_platform]
        session = session_factory(selected_platform)
        result_root = Path(artifact_root) / selected_platform.value
        result = publisher.publish(
            draft=draft,
            session_resolution=session,
            artifact_root=result_root,
        )
        results.append(result)
    return results


def apply_publish_results(
    draft: PublishDraft,
    results: list[PublishResult],
) -> PublishDraft:
    records = [
        PlatformPublishRecord(
            platform_name=PlatformName(result.platform_name),
            status=result.status,
            started_at=result.started_at,
            finished_at=result.finished_at,
            error_message=result.error_message,
            error_type=result.error_type,
            screenshot_path=Path(result.screenshot_path) if result.screenshot_path else None,
            result_url=result.result_url,
            success_signal=result.success_signal,
            attempt=result.attempt,
            execution_mode=result.execution_mode,
            awaiting_manual_publish=result.awaiting_manual_publish,
        )
        for result in results
    ]
    history_entry = PublishHistoryEntry(
        execution_mode=draft.execution_mode,
        results=records,
    )
    return draft.model_copy(
        update={
            "publish_history": [*draft.publish_history, history_entry],
        }
    )
