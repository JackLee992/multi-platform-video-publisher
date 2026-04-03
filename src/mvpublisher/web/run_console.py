from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import PlatformName


RunConsoleStatus = Literal["idle", "running", "success", "failed", "partial"]


class RunConsoleLogEntry(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    level: str
    message: str


class RunConsolePlatformResult(BaseModel):
    platform_name: PlatformName
    status: str
    success_signal: Optional[str] = None
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    finished_at: Optional[datetime] = None


class RunConsoleState(BaseModel):
    draft_id: str
    status: RunConsoleStatus
    execution_mode: Union[ExecutionMode, str]
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    logs: list[RunConsoleLogEntry] = Field(default_factory=list)
    results: list[RunConsolePlatformResult] = Field(default_factory=list)


class RunConsoleStore:
    def __init__(self, artifact_root: Path):
        self.artifact_root = Path(artifact_root)

    def _path(self, draft_id: str) -> Path:
        return self.artifact_root / draft_id / "run_console" / "latest.json"

    def save_latest(self, state: RunConsoleState) -> Path:
        path = self._path(state.draft_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load_latest(self, draft_id: str) -> Optional[RunConsoleState]:
        path = self._path(draft_id)
        if not path.exists():
            return None
        return RunConsoleState.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        )
