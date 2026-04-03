from datetime import datetime, timezone
from typing import Optional

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import DraftApprovalStatus, PublishDraft
from mvpublisher.validation.service import ValidationService


class ApprovalError(Exception):
    """Raised when draft approval requirements are not satisfied."""


class ApprovalService:
    def __init__(self, validation_service: Optional[ValidationService] = None):
        self.validation_service = validation_service or ValidationService()

    def is_approved(self, draft: PublishDraft) -> bool:
        return draft.approval_status == DraftApprovalStatus.APPROVED

    def approve(
        self,
        draft: PublishDraft,
        publish_now: bool,
        execution_mode: Optional[ExecutionMode] = None,
    ) -> PublishDraft:
        effective_mode = execution_mode or (
            ExecutionMode.AUTOPUBLISH if publish_now else ExecutionMode.AUTOFILL_ONLY
        )
        draft = draft.model_copy(update={"execution_mode": effective_mode})
        status, errors = self.validation_service.validate(draft)
        if errors:
            raise ApprovalError(errors[0].message)

        return draft.model_copy(
            update={
                "approval_status": DraftApprovalStatus.APPROVED,
                "publish_mode": "immediate" if publish_now else "manual_hold",
                "execution_mode": effective_mode,
                "validation_status": status,
                "validation_errors": errors,
                "updated_at": datetime.now(timezone.utc),
            }
        )
