from pathlib import Path
from typing import Callable, Mapping

from mvpublisher.approval.service import ApprovalService
from mvpublisher.models.draft import PlatformName, PublishDraft

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
