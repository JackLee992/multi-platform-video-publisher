import json
import re
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from mvpublisher.models.draft import PublishDraft


_DRAFT_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class DraftRepository:
    def __init__(self, root: Path, artifacts_root: Optional[Path] = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        if artifacts_root is None:
            self.artifacts_root = self.root.parent / "artifacts"
        else:
            self.artifacts_root = Path(artifacts_root)
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
    def _validate_draft_id(self, draft_id: str) -> None:
        if not _DRAFT_ID_PATTERN.fullmatch(draft_id):
            raise ValueError("invalid draft_id")

    def artifact_dir(self, draft_id: str) -> Path:
        self._validate_draft_id(draft_id)
        path = self.artifacts_root / draft_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _path(self, draft_id: str) -> Path:
        self._validate_draft_id(draft_id)
        return self.root / f"{draft_id}.json"

    def list_ids(self) -> list[str]:
        draft_ids: list[str] = []
        for path in sorted(self.root.glob("*.json")):
            if _DRAFT_ID_PATTERN.fullmatch(path.stem):
                draft_ids.append(path.stem)
        return draft_ids

    def save(self, draft: PublishDraft) -> PublishDraft:
        self._validate_draft_id(draft.draft_id)
        draft_to_save = draft.model_copy(
            update={"updated_at": datetime.now(timezone.utc)}
        )
        path = self._path(draft_to_save.draft_id)
        tmp_path = path.with_suffix(".tmp")
        try:
            tmp_path.write_text(
                json.dumps(
                    draft_to_save.model_dump(mode="json"),
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            tmp_path.replace(path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
        return draft_to_save

    def load(self, draft_id: str) -> PublishDraft:
        self._validate_draft_id(draft_id)
        return DraftRepository._load_from_path(self._path(draft_id))

    @staticmethod
    def _load_from_path(path: Path) -> PublishDraft:
        return PublishDraft.model_validate_json(path.read_text(encoding="utf-8"))
