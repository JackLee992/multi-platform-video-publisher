from datetime import datetime, timezone
import base64
from pathlib import Path
from typing import Callable, Mapping, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from mvpublisher.approval.service import ApprovalService
from mvpublisher.config import AppConfig
from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import PlatformDraft, PlatformName
from mvpublisher.publishers import (
    DouyinPublisher,
    Publisher,
    WechatChannelsPublisher,
    XiaohongshuPublisher,
)
from mvpublisher.sessions import PlatformSessionRequest, resolve_session
from mvpublisher.storage.drafts import DraftRepository
from mvpublisher.workflows import publish_draft_from_repository
from mvpublisher.web.run_console import (
    RunConsoleLogEntry,
    RunConsolePlatformResult,
    RunConsoleState,
    RunConsoleStore,
)


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


SessionFactory = Callable[[PlatformName], object]


def create_app(
    repository: Optional[DraftRepository] = None,
    publishers: Optional[Mapping[PlatformName, Publisher]] = None,
    session_factory: Optional[SessionFactory] = None,
) -> FastAPI:
    templates = Jinja2Templates(
        directory=str(Path(__file__).resolve().parent / "templates")
    )
    app = FastAPI()
    config = AppConfig.from_env()
    repository = repository or DraftRepository(config.home_dir / "drafts")
    run_console_store = RunConsoleStore(config.home_dir / "artifacts")
    approval_service = ApprovalService()
    publishers = publishers or _default_publishers()
    session_factory = session_factory or (
        lambda platform_name: resolve_session(
            request=PlatformSessionRequest(platform_name=platform_name.value),
            state_root=config.home_dir / "sessions",
            live_browser_available=True,
        )
    )

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
        selected_platforms = [
            PlatformName(platform_name) for platform_name in payload.selected_platforms
        ]
        existing_platform_drafts = {
            platform_draft.platform_name: platform_draft
            for platform_draft in draft.platform_drafts
        }
        updated_draft = draft.model_copy(
            update={
                "selected_title": payload.selected_title,
                "selected_cover_path": Path(payload.selected_cover_path),
                "selected_platforms": selected_platforms,
                "platform_drafts": [
                    existing_platform_drafts.get(
                        platform_name,
                        PlatformDraft(platform_name=platform_name),
                    )
                    for platform_name in selected_platforms
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
        platform_name = PlatformName(payload.platform_name)
        saved_draft, results = publish_draft_from_repository(
            draft_id=draft_id,
            repository=repository,
            publishers=publishers,
            session_factory=session_factory,
            selected_platforms=[platform_name],
            execution_mode=ExecutionMode(payload.execution_mode),
        )
        result = results[0]
        return {
            "draft_id": saved_draft.draft_id,
            "platform_name": result.platform_name,
            "execution_mode": result.execution_mode.value,
            "status": result.status,
        }

    @app.post("/api/drafts/{draft_id}/run")
    async def run_draft(draft_id: str):
        draft = repository.load(draft_id)
        if not approval_service.is_approved(draft):
            raise HTTPException(status_code=400, detail="Draft must be approved before run")

        state = RunConsoleState(
            draft_id=draft_id,
            status="running",
            execution_mode=draft.execution_mode,
            logs=[
                RunConsoleLogEntry(level="info", message="run requested"),
                RunConsoleLogEntry(level="info", message="publish workflow started"),
            ],
        )
        run_console_store.save_latest(state)

        results = []
        for platform in draft.selected_platforms:
            state.logs.append(
                RunConsoleLogEntry(
                    level="info",
                    message=f"{platform.value} execution started",
                )
            )
            run_console_store.save_latest(state)

        saved_draft, results = publish_draft_from_repository(
            draft_id=draft_id,
            repository=repository,
            publishers=publishers,
            session_factory=session_factory,
        )

        state.results = [
            RunConsolePlatformResult(
                platform_name=PlatformName(result.platform_name),
                status=result.status,
                success_signal=result.success_signal,
                result_url=result.result_url,
                error_message=result.error_message,
                finished_at=result.finished_at,
            )
            for result in results
        ]
        for result in state.results:
            state.logs.append(
                RunConsoleLogEntry(
                    level="info",
                    message=f"{result.platform_name.value} execution finished: {result.status}",
                )
            )
        state.logs.append(RunConsoleLogEntry(level="info", message="publish workflow finished"))
        state.finished_at = datetime.now(timezone.utc)
        state.status = _compute_run_status(state.results)
        run_console_store.save_latest(state)

        return {
            "draft_id": saved_draft.draft_id,
            "status": state.status,
            "execution_mode": saved_draft.execution_mode.value,
        }

    @app.get("/api/drafts/{draft_id}/run-status")
    async def run_status(draft_id: str):
        repository.load(draft_id)
        state = run_console_store.load_latest(draft_id)
        if state is None:
            return {
                "draft_id": draft_id,
                "status": "idle",
                "logs": [],
                "results": [],
            }
        return state.model_dump(mode="json")

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


def _default_publishers() -> dict[PlatformName, Publisher]:
    return {
        PlatformName.XIAOHONGSHU: XiaohongshuPublisher(),
        PlatformName.DOUYIN: DouyinPublisher(),
        PlatformName.WECHAT_CHANNELS: WechatChannelsPublisher(),
    }


def _compute_run_status(results: list[RunConsolePlatformResult]) -> str:
    statuses = [result.status for result in results]
    if not statuses:
        return "failed"
    if all(status == "failed" for status in statuses):
        return "failed"
    if any(status == "failed" for status in statuses):
        return "partial"
    return "success"
