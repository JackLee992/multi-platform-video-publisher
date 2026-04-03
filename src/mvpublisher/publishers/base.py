from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Optional
from typing import Protocol, runtime_checkable

from mvpublisher.models.draft import PublishDraft


@dataclass(frozen=True)
class PublishResult:
    platform_name: str
    status: str
    submitted: bool
    result_url: Optional[str]
    error_message: Optional[str]

    def write(self, artifact_root: Path) -> None:
        artifact_root.mkdir(parents=True, exist_ok=True)
        (artifact_root / "publish_result.json").write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


@runtime_checkable
class Publisher(Protocol):
    platform_name: str

    def publish(
        self,
        draft: PublishDraft,
        session_resolution: object,
        artifact_root: Path,
    ) -> PublishResult:
        ...
