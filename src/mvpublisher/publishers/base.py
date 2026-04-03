from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Optional
from typing import Protocol, runtime_checkable

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import PublishDraft


@dataclass(frozen=True)
class PublishResult:
    platform_name: str
    status: str
    submitted: bool
    result_url: Optional[str]
    error_message: Optional[str]
    error_type: Optional[str] = None
    screenshot_path: Optional[str] = None
    success_signal: Optional[str] = None
    execution_mode: ExecutionMode = ExecutionMode.AUTOPUBLISH
    awaiting_manual_publish: bool = False
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    attempt: int = 1

    def write(self, artifact_root: Path) -> None:
        artifact_root.mkdir(parents=True, exist_ok=True)
        summary_path = artifact_root / "result_summary.txt"
        summary_path.write_text(
            "\n".join(
                [
                    f"platform={self.platform_name}",
                    f"status={self.status}",
                    f"execution_mode={self.execution_mode.value}",
                    f"submitted={self.submitted}",
                    f"success_signal={self.success_signal or ''}",
                    f"result_url={self.result_url or ''}",
                    f"error_type={self.error_type or ''}",
                    f"error_message={self.error_message or ''}",
                ]
            ),
            encoding="utf-8",
        )
        screenshot_path_value = self.screenshot_path
        if screenshot_path_value is None:
            screenshot_path = artifact_root / "page_state.txt"
            screenshot_path.write_text(
                f"status={self.status}\nsuccess_signal={self.success_signal or ''}\nresult_url={self.result_url or ''}\n",
                encoding="utf-8",
            )
            screenshot_path_value = str(screenshot_path)
        (artifact_root / "publish_result.json").write_text(
            json.dumps(
                {**asdict(self), "screenshot_path": screenshot_path_value},
                ensure_ascii=False,
                indent=2,
                default=_json_default,
            ),
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


def _json_default(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")
