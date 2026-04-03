from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import (
    PlatformName,
    PublishDraft,
    ValidationError,
    ValidationStatus,
)


class ValidationService:
    def validate(self, draft: PublishDraft) -> tuple[ValidationStatus, list[ValidationError]]:
        errors: list[ValidationError] = []

        if not draft.source_video_path.exists() or not draft.source_video_path.is_file():
            errors.append(
                ValidationError(
                    field="source_video_path",
                    message="source_video_path must point to an existing file",
                )
            )

        if not draft.selected_title or not draft.selected_title.strip():
            errors.append(
                ValidationError(
                    field="selected_title",
                    message="selected_title must be present",
                    platforms=list(draft.selected_platforms),
                )
            )

        if (
            draft.selected_cover_path is None
            or not draft.selected_cover_path.exists()
            or not draft.selected_cover_path.is_file()
        ):
            errors.append(
                ValidationError(
                    field="selected_cover_path",
                    message="selected_cover_path must be present and exist",
                    platforms=list(draft.selected_platforms),
                )
            )

        if not draft.selected_platforms:
            errors.append(
                ValidationError(
                    field="selected_platforms",
                    message="selected_platforms must be non-empty",
                )
            )

        if draft.execution_mode not in {
            ExecutionMode.AUTOPUBLISH,
            ExecutionMode.AUTOFILL_ONLY,
        }:
            errors.append(
                ValidationError(
                    field="execution_mode",
                    message="execution_mode must be a supported value",
                )
            )

        if (
            PlatformName.WECHAT_CHANNELS in draft.selected_platforms
            and draft.selected_title
            and len(draft.selected_title.strip()) > 16
        ):
            errors.append(
                ValidationError(
                    field="selected_title",
                    message="wechat_channels short title must be 16 characters or fewer",
                    platforms=[PlatformName.WECHAT_CHANNELS],
                )
            )

        status = ValidationStatus.FAILED if errors else ValidationStatus.PASSED
        return status, errors

