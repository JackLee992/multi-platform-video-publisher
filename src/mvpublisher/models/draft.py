import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set

from pydantic import BaseModel, Field, model_validator

from mvpublisher.execution_modes import ExecutionMode


class DraftApprovalStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"


class PlatformName(str, Enum):
    XIAOHONGSHU = "xiaohongshu"
    DOUYIN = "douyin"
    WECHAT_CHANNELS = "wechat_channels"


class PlatformDraft(BaseModel):
    platform_name: PlatformName
    enabled: bool = True
    title_override: Optional[str] = None
    description_override: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    scheduled_time: Optional[str] = None
    execution_status: str = "pending"
    last_error: Optional[str] = None
    result_url: Optional[str] = None
    artifacts: List[str] = Field(default_factory=list)


class ValidationStatus(str, Enum):
    UNKNOWN = "unknown"
    PASSED = "passed"
    FAILED = "failed"


class ValidationError(BaseModel):
    field: str
    message: str
    platforms: List[PlatformName] = Field(default_factory=list)


class CodexDraftReview(BaseModel):
    status: str = "pending"
    content_summary: Optional[str] = None
    refined_transcript: Optional[str] = None
    recommended_title: Optional[str] = None
    title_candidates: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    reviewed_at: Optional[datetime] = None


class PlatformPublishRecord(BaseModel):
    platform_name: PlatformName
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    screenshot_path: Optional[Path] = None
    result_url: Optional[str] = None
    success_signal: Optional[str] = None
    attempt: int = 1
    execution_mode: ExecutionMode = ExecutionMode.AUTOPUBLISH
    awaiting_manual_publish: bool = False


class PublishHistoryEntry(BaseModel):
    history_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_mode: ExecutionMode = ExecutionMode.AUTOPUBLISH
    results: List[PlatformPublishRecord] = Field(default_factory=list)


class PublishDraft(BaseModel):
    draft_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_video_path: Path
    transcript_artifacts_path: Optional[Path] = None
    summary: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    title_suggestions: List[str] = Field(default_factory=list)
    cover_suggestions: List[str] = Field(default_factory=list)
    cover_candidate_paths: List[Path] = Field(default_factory=list)
    description_suggestions: List[str] = Field(default_factory=list)
    approval_status: DraftApprovalStatus = DraftApprovalStatus.DRAFT
    publish_mode: str = "manual_hold"
    execution_mode: ExecutionMode = ExecutionMode.AUTOPUBLISH
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    validation_errors: List[ValidationError] = Field(default_factory=list)
    selected_title: Optional[str] = None
    selected_cover_path: Optional[Path] = None
    selected_platforms: List[PlatformName] = Field(default_factory=list)
    platform_drafts: List[PlatformDraft] = Field(default_factory=list)
    publish_history: List[PublishHistoryEntry] = Field(default_factory=list)
    codex_review: Optional[CodexDraftReview] = None

    @classmethod
    def new(cls, source_video_path: Path) -> "PublishDraft":
        now = datetime.now(timezone.utc)
        return cls(
            draft_id=uuid.uuid4().hex,
            created_at=now,
            updated_at=now,
            source_video_path=source_video_path,
        )

    @model_validator(mode="after")
    def validate_platform_drafts(self) -> "PublishDraft":
        if len(self.selected_platforms) != len(set(self.selected_platforms)):
            raise ValueError("selected_platforms must not contain duplicate values")

        platform_names = [platform_draft.platform_name for platform_draft in self.platform_drafts]
        if len(platform_names) != len(set(platform_names)):
            raise ValueError("platform_drafts must not contain duplicate platform_name values")

        selected_platforms: Set[PlatformName] = set(self.selected_platforms)
        extra_platforms = set(platform_names) - selected_platforms
        if extra_platforms:
            raise ValueError("platform_drafts must only reference selected_platforms")

        return self
