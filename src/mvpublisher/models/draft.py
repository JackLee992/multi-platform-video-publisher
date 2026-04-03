import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Set
from typing import List
from typing import Optional

from pydantic import BaseModel, Field, model_validator


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
    selected_title: Optional[str] = None
    selected_cover_path: Optional[Path] = None
    selected_platforms: List[PlatformName] = Field(default_factory=list)
    platform_drafts: List[PlatformDraft] = Field(default_factory=list)

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
