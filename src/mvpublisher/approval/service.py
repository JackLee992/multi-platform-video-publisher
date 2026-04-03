from datetime import datetime, timezone

from mvpublisher.models.draft import DraftApprovalStatus, PublishDraft


class ApprovalError(Exception):
    """Raised when draft approval requirements are not satisfied."""


class ApprovalService:
    def is_approved(self, draft: PublishDraft) -> bool:
        return draft.approval_status == DraftApprovalStatus.APPROVED

    def approve(self, draft: PublishDraft, publish_now: bool) -> PublishDraft:
        if not draft.source_video_path.exists() or not draft.source_video_path.is_file():
            raise ApprovalError("source_video_path must point to an existing file")
        if not draft.selected_title or not draft.selected_title.strip():
            raise ApprovalError("selected_title must be present")
        if (
            draft.selected_cover_path is None
            or not draft.selected_cover_path.exists()
            or not draft.selected_cover_path.is_file()
        ):
            raise ApprovalError("selected_cover_path must be present and exist")
        if not draft.selected_platforms:
            raise ApprovalError("selected_platforms must be non-empty")

        return draft.model_copy(
            update={
                "approval_status": DraftApprovalStatus.APPROVED,
                "publish_mode": "immediate" if publish_now else "manual_hold",
                "updated_at": datetime.now(timezone.utc),
            }
        )
