import base64
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from mvpublisher.approval.service import ApprovalService
from mvpublisher.config import AppConfig
from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import PlatformName
from mvpublisher.storage.drafts import DraftRepository


class ApprovalPayload(BaseModel):
    selected_title: str
    selected_cover_path: str
    selected_platforms: list[str]
    publish_now: bool = False
    execution_mode: str = ExecutionMode.AUTOFILL_ONLY.value


class CoverUploadPayload(BaseModel):
    filename: str
    content_base64: str


class RetryPayload(BaseModel):
    platform_name: str
    execution_mode: str = ExecutionMode.AUTOFILL_ONLY.value


def create_app() -> FastAPI:
    templates = Jinja2Templates(
        directory=str(Path(__file__).resolve().parent / "templates")
    )
    app = FastAPI()
    config = AppConfig.from_env()
    repository = DraftRepository(config.home_dir / "drafts")
    approval_service = ApprovalService()

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        drafts = repository.list()
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "request": request,
                "drafts": drafts,
                "execution_mode_options": [mode.value for mode in ExecutionMode],
            },
        )

    @app.get("/drafts/{draft_id}", response_class=HTMLResponse)
    async def draft_detail(request: Request, draft_id: str):
        draft = repository.load(draft_id)
        return templates.TemplateResponse(
            request,
            "draft_detail.html",
            {
                "request": request,
                "draft": draft,
                "platform_options": [platform.value for platform in PlatformName],
                "execution_mode_options": [mode.value for mode in ExecutionMode],
            },
        )

    @app.post("/api/drafts/{draft_id}/approval")
    async def approve_draft(draft_id: str, payload: ApprovalPayload):
        draft = repository.load(draft_id)
        updated_draft = draft.model_copy(
            update={
                "selected_title": payload.selected_title,
                "selected_cover_path": Path(payload.selected_cover_path),
                "selected_platforms": [
                    PlatformName(platform_name)
                    for platform_name in payload.selected_platforms
                ],
            }
        )
        approved_draft = approval_service.approve(
            updated_draft,
            publish_now=payload.publish_now,
            execution_mode=ExecutionMode(payload.execution_mode),
        )
        saved_draft = repository.save(approved_draft)
        return {
            "draft_id": saved_draft.draft_id,
            "approval_status": saved_draft.approval_status.value,
            "publish_mode": saved_draft.publish_mode,
            "execution_mode": saved_draft.execution_mode.value,
        }

    @app.post("/api/drafts/{draft_id}/retry")
    async def retry_platform(draft_id: str, payload: RetryPayload):
        draft = repository.load(draft_id)
        updated = repository.save(
            draft.model_copy(update={"execution_mode": ExecutionMode(payload.execution_mode)})
        )
        return {
            "draft_id": updated.draft_id,
            "platform_name": payload.platform_name,
            "execution_mode": updated.execution_mode.value,
        }

    @app.post("/api/drafts/{draft_id}/cover-upload")
    async def upload_cover(draft_id: str, payload: CoverUploadPayload):
        repository.load(draft_id)
        upload_dir = repository.artifact_dir(draft_id) / "uploaded_covers"
        upload_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(payload.filename).suffix or ".jpg"
        target_path = upload_dir / f"manual-cover{suffix}"
        try:
            binary = base64.b64decode(payload.content_base64)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid cover upload payload") from exc
        target_path.write_bytes(binary)
        return {
            "cover_path": str(target_path),
            "cover_url": f"/drafts/{draft_id}/uploaded-covers/{target_path.name}",
        }

    @app.get("/drafts/{draft_id}/cover-candidates/{filename}")
    async def cover_candidate(draft_id: str, filename: str):
        draft = repository.load(draft_id)
        for cover_path in draft.cover_candidate_paths:
            path = Path(cover_path)
            if path.name == filename and path.exists():
                return FileResponse(path)
        raise HTTPException(status_code=404, detail="Cover candidate not found")

    @app.get("/drafts/{draft_id}/uploaded-covers/{filename}")
    async def uploaded_cover(draft_id: str, filename: str):
        repository.load(draft_id)
        path = repository.artifact_dir(draft_id) / "uploaded_covers" / filename
        if path.exists():
            return FileResponse(path)
        raise HTTPException(status_code=404, detail="Uploaded cover not found")

    return app
