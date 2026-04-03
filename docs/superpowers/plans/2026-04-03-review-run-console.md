# Review Run Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `Run` button and in-page execution console to the draft review page so approved drafts can be executed from the UI with visible progress and results.

**Architecture:** Extend the existing review app with a lightweight run-state file per draft, plus `run` and `run-status` endpoints. Reuse the existing publish workflow and publish history, while the frontend polls the latest run-state and renders a console-like view without introducing WebSockets.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, Pydantic v2, pytest, existing draft repository and publish workflow

---

### Task 1: Run-State Storage Contract

**Files:**
- Create: `src/mvpublisher/web/run_console.py`
- Test: `tests/test_run_console.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from mvpublisher.models.draft import PlatformName
from mvpublisher.web.run_console import (
    RunConsoleLogEntry,
    RunConsolePlatformResult,
    RunConsoleState,
    RunConsoleStore,
)


def test_run_console_store_writes_and_reads_latest_state(tmp_path: Path) -> None:
    store = RunConsoleStore(tmp_path)
    state = RunConsoleState(
        draft_id="d" * 32,
        status="running",
        execution_mode="autopublish",
        logs=[
            RunConsoleLogEntry(level="info", message="run started"),
        ],
        results=[
            RunConsolePlatformResult(
                platform_name=PlatformName.XIAOHONGSHU,
                status="submitted_for_verification",
                success_signal="xiaohongshu_submit_requested",
            )
        ],
    )

    store.save_latest(state)

    loaded = store.load_latest("d" * 32)
    assert loaded is not None
    assert loaded.status == "running"
    assert loaded.logs[0].message == "run started"
    assert loaded.results[0].platform_name == PlatformName.XIAOHONGSHU
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_run_console.py::test_run_console_store_writes_and_reads_latest_state -q
```

Expected: FAIL with `ModuleNotFoundError` or missing symbols from `mvpublisher.web.run_console`

- [ ] **Step 3: Write minimal implementation**

```python
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal, Optional

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
    execution_mode: ExecutionMode | str
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
        return RunConsoleState.model_validate(json.loads(path.read_text(encoding="utf-8")))
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_run_console.py::test_run_console_store_writes_and_reads_latest_state -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mvpublisher/web/run_console.py tests/test_run_console.py
git commit -m "feat: add run console state storage"
```

### Task 2: Run And Status API Endpoints

**Files:**
- Modify: `src/mvpublisher/web/app.py`
- Modify: `src/mvpublisher/workflows.py`
- Modify: `tests/test_web_routes.py`
- Test: `tests/test_run_console.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_run_endpoint_rejects_unapproved_draft(client, draft_repository, draft):
    response = client.post(f"/api/drafts/{draft.draft_id}/run")
    assert response.status_code == 400
    assert "approved" in response.json()["detail"]


def test_run_endpoint_writes_run_state_and_returns_running_status(client, approved_draft, repository):
    response = client.post(f"/api/drafts/{approved_draft.draft_id}/run")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"running", "success", "partial", "failed"}

    status_response = client.get(f"/api/drafts/{approved_draft.draft_id}/run-status")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert "logs" in status_payload
    assert "results" in status_payload
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_web_routes.py -q
```

Expected: FAIL because `/api/drafts/{draft_id}/run` and `/run-status` do not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
from datetime import datetime, timezone

from mvpublisher.approval.service import ApprovalService
from mvpublisher.web.run_console import (
    RunConsoleLogEntry,
    RunConsolePlatformResult,
    RunConsoleState,
    RunConsoleStore,
)


def _compute_overall_status(results: list[RunConsolePlatformResult]) -> str:
    statuses = [result.status for result in results]
    if not statuses:
        return "failed"
    if all(status not in {"failed"} for status in statuses):
        return "success"
    if all(status == "failed" for status in statuses):
        return "failed"
    return "partial"


@app.post("/api/drafts/{draft_id}/run")
async def run_draft(draft_id: str):
    draft = repository.load(draft_id)
    if not ApprovalService().is_approved(draft):
        raise HTTPException(status_code=400, detail="Draft must be approved before run")

    store = RunConsoleStore(config.home_dir / "artifacts")
    state = RunConsoleState(
        draft_id=draft_id,
        status="running",
        execution_mode=draft.execution_mode,
        logs=[
            RunConsoleLogEntry(level="info", message="run requested"),
            RunConsoleLogEntry(level="info", message="publish workflow started"),
        ],
    )
    store.save_latest(state)

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
    state.logs.append(RunConsoleLogEntry(level="info", message="publish workflow finished"))
    state.finished_at = datetime.now(timezone.utc)
    state.status = _compute_overall_status(state.results)
    store.save_latest(state)

    return {
        "draft_id": saved_draft.draft_id,
        "status": state.status,
        "execution_mode": saved_draft.execution_mode.value,
    }


@app.get("/api/drafts/{draft_id}/run-status")
async def run_status(draft_id: str):
    repository.load(draft_id)
    store = RunConsoleStore(config.home_dir / "artifacts")
    state = store.load_latest(draft_id)
    if state is None:
        return {
            "draft_id": draft_id,
            "status": "idle",
            "logs": [],
            "results": [],
        }
    return state.model_dump(mode="json")
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_web_routes.py tests/test_run_console.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mvpublisher/web/app.py src/mvpublisher/workflows.py tests/test_web_routes.py tests/test_run_console.py
git commit -m "feat: add review page run endpoints"
```

### Task 3: Run Console UI

**Files:**
- Modify: `src/mvpublisher/web/templates/draft_detail.html`
- Modify: `tests/test_web_routes.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_draft_detail_includes_run_console(client, approved_draft):
    response = client.get(f"/drafts/{approved_draft.draft_id}")
    html = response.text
    assert "Run Console" in html
    assert 'id="run-button"' in html
    assert 'id="run-log"' in html
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_web_routes.py::test_draft_detail_includes_run_console -q
```

Expected: FAIL because the draft page has no run console yet

- [ ] **Step 3: Write minimal implementation**

```html
<h2 style="margin-top: 22px;">Run Console</h2>
<div class="suggestion-list">
  <div class="chip">
    <div>当前状态：<span id="run-state-status">idle</span></div>
    <div>当前模式：<span id="run-state-mode">{{ draft.execution_mode.value }}</span></div>
  </div>
  <div class="inline-row">
    <button type="button" class="button" id="run-button" {% if draft.approval_status.value != "approved" %}disabled{% endif %}>
      Run
    </button>
    <span class="hint" id="run-hint">
      {% if draft.approval_status.value != "approved" %}
      请先保存确认
      {% else %}
      已批准，可直接执行
      {% endif %}
    </span>
  </div>
  <div class="chip">
    <pre id="run-log">等待执行...</pre>
  </div>
  <div id="run-results" class="suggestion-list"></div>
</div>
```

```javascript
const runButton = document.getElementById("run-button");
const runStatus = document.getElementById("run-state-status");
const runLog = document.getElementById("run-log");
const runResults = document.getElementById("run-results");

const renderRunState = (state) => {
  runStatus.textContent = state.status || "idle";
  runLog.textContent = (state.logs || [])
    .map((entry) => `[${entry.created_at}] ${entry.level}: ${entry.message}`)
    .join("\n") || "等待执行...";
  runResults.innerHTML = (state.results || []).map((result) => `
    <div class="chip">
      <div>${result.platform_name} / ${result.status}</div>
      <div>信号：${result.success_signal || "none"}</div>
      <div>结果地址：${result.result_url || "none"}</div>
      <div>错误：${result.error_message || "none"}</div>
    </div>
  `).join("");
};

const pollRunStatus = async () => {
  const response = await fetch("/api/drafts/{{ draft.draft_id }}/run-status");
  const data = await response.json();
  renderRunState(data);
  if (data.status === "running") {
    window.setTimeout(pollRunStatus, 1500);
  }
};

runButton?.addEventListener("click", async () => {
  runButton.disabled = true;
  runButton.textContent = "Running...";
  const response = await fetch("/api/drafts/{{ draft.draft_id }}/run", { method: "POST" });
  const data = await response.json();
  if (!response.ok) {
    saveStatus.textContent = `执行失败：${data.detail || "unknown error"}`;
    runButton.disabled = false;
    runButton.textContent = "Run";
    return;
  }
  await pollRunStatus();
  runButton.disabled = false;
  runButton.textContent = "Run";
});

pollRunStatus();
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_web_routes.py::test_draft_detail_includes_run_console -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mvpublisher/web/templates/draft_detail.html tests/test_web_routes.py
git commit -m "feat: add run console to draft detail page"
```

### Task 4: End-To-End Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add minimal README note**

```markdown
### 审核页直接执行

草稿确认页现在支持 `Run` 按钮：

- 先保存确认
- 再点击 `Run`
- 页面会轮询显示当前执行状态、日志和平台结果
```

- [ ] **Step 2: Run targeted tests**

Run:

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_run_console.py tests/test_web_routes.py -q
```

Expected: PASS

- [ ] **Step 3: Run full test suite**

Run:

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
PYTHONPATH=src ./.venv/bin/python -m pytest -q
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document review page run console"
```
