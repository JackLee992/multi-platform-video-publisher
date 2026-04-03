# P0 Stable Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the P0 stable core for the multi-platform video publisher, including preflight validation, execution mode selection, publish history, success heuristics, retry support, and a usable review workspace.

**Architecture:** Extend the current Python application in place. Add explicit execution modes and validation models at the draft layer, make publisher results history-aware and mode-aware, then expose those states through the review web app. Keep the first iteration focused on stable storage and operator-visible states before polishing automation details.

**Tech Stack:** Python 3.11+, Pydantic v2, Typer, FastAPI, Jinja2, pytest, current Chrome reuse helpers, Playwright fallback

---

## File Structure

### Modify

- `src/mvpublisher/models/draft.py`
- `src/mvpublisher/storage/drafts.py`
- `src/mvpublisher/approval/service.py`
- `src/mvpublisher/publishers/base.py`
- `src/mvpublisher/publishers/runner.py`
- `src/mvpublisher/publishers/xiaohongshu.py`
- `src/mvpublisher/publishers/douyin.py`
- `src/mvpublisher/publishers/wechat_channels.py`
- `src/mvpublisher/web/app.py`
- `src/mvpublisher/web/templates/index.html`
- `src/mvpublisher/web/templates/draft_detail.html`
- `tests/test_draft_models.py`
- `tests/test_storage.py`
- `tests/test_approval_service.py`
- `tests/test_publish_runner.py`
- `tests/test_web_routes.py`

### Create

- `src/mvpublisher/execution_modes.py`
- `src/mvpublisher/validation/service.py`
- `tests/test_validation_service.py`

## Task 1: Add Execution Modes And Draft History Models

**Files:**
- Create: `src/mvpublisher/execution_modes.py`
- Modify: `src/mvpublisher/models/draft.py`
- Modify: `tests/test_draft_models.py`

- [ ] **Step 1: Write failing model tests**

Add tests that prove:
- drafts default to an execution mode
- validation status and errors round-trip
- publish history stores mode-aware platform results

- [ ] **Step 2: Run the targeted tests**

Run: `cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher && ./.venv/bin/python -m pytest tests/test_draft_models.py -q`
Expected: FAIL because execution mode and history fields do not exist yet

- [ ] **Step 3: Implement minimal model changes**

Add:
- `ExecutionMode` enum in `src/mvpublisher/execution_modes.py`
- `ValidationStatus`
- `ValidationError`
- `PublishHistoryEntry`
- `PlatformPublishRecord`
- draft-level `execution_mode`, `validation_status`, `validation_errors`, `publish_history`

- [ ] **Step 4: Re-run the model tests**

Run: `cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher && ./.venv/bin/python -m pytest tests/test_draft_models.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
git add src/mvpublisher/execution_modes.py src/mvpublisher/models/draft.py tests/test_draft_models.py
git commit -m "feat: add execution modes and draft history models"
```

## Task 2: Implement Validation Service And Approval Gate Integration

**Files:**
- Create: `src/mvpublisher/validation/service.py`
- Create: `tests/test_validation_service.py`
- Modify: `src/mvpublisher/approval/service.py`
- Modify: `tests/test_approval_service.py`

- [ ] **Step 1: Write failing validation tests**

Cover:
- missing video path
- missing cover path
- missing selected title
- missing selected platforms
- invalid execution mode
- known WeChat Channels short-title limit

- [ ] **Step 2: Run validation and approval tests**

Run: `cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher && ./.venv/bin/python -m pytest tests/test_validation_service.py tests/test_approval_service.py -q`
Expected: FAIL because the validation service does not exist

- [ ] **Step 3: Implement validation and approval wiring**

Make approval and publish entry points able to:
- compute validation status
- persist validation errors
- block execution on failed validation

- [ ] **Step 4: Re-run the validation and approval tests**

Run: `cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher && ./.venv/bin/python -m pytest tests/test_validation_service.py tests/test_approval_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
git add src/mvpublisher/validation/service.py src/mvpublisher/approval/service.py tests/test_validation_service.py tests/test_approval_service.py
git commit -m "feat: add preflight validation service"
```

## Task 3: Make Publish Results Mode-Aware And Retryable

**Files:**
- Modify: `src/mvpublisher/publishers/base.py`
- Modify: `src/mvpublisher/publishers/runner.py`
- Modify: `src/mvpublisher/publishers/xiaohongshu.py`
- Modify: `src/mvpublisher/publishers/douyin.py`
- Modify: `src/mvpublisher/publishers/wechat_channels.py`
- Modify: `src/mvpublisher/storage/drafts.py`
- Modify: `tests/test_publish_runner.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Write failing publish-runner tests**

Cover:
- `autofill_only` results are stored as `awaiting_manual_publish`
- `autopublish` results store success signals
- retry appends a new history record instead of overwriting

- [ ] **Step 2: Run publish runner and storage tests**

Run: `cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher && ./.venv/bin/python -m pytest tests/test_publish_runner.py tests/test_storage.py -q`
Expected: FAIL because results are not history-aware or mode-aware yet

- [ ] **Step 3: Implement result persistence and retry plumbing**

Make publisher results store:
- execution mode
- success signal
- result URL
- screenshot path
- awaiting-manual state
- retry attempt count

- [ ] **Step 4: Re-run publish runner and storage tests**

Run: `cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher && ./.venv/bin/python -m pytest tests/test_publish_runner.py tests/test_storage.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
git add src/mvpublisher/publishers/base.py src/mvpublisher/publishers/runner.py src/mvpublisher/publishers/xiaohongshu.py src/mvpublisher/publishers/douyin.py src/mvpublisher/publishers/wechat_channels.py src/mvpublisher/storage/drafts.py tests/test_publish_runner.py tests/test_storage.py
git commit -m "feat: add publish history and retry records"
```

## Task 4: Expose Validation, History, And Mode Selection In The Review UI

**Files:**
- Modify: `src/mvpublisher/web/app.py`
- Modify: `src/mvpublisher/web/templates/index.html`
- Modify: `src/mvpublisher/web/templates/draft_detail.html`
- Modify: `tests/test_web_routes.py`

- [ ] **Step 1: Write failing web route tests**

Cover:
- draft list page shows summary rows
- detail page shows validation results
- detail page exposes publish history
- execution mode can be updated
- retry endpoint accepts target platform and mode

- [ ] **Step 2: Run the web tests**

Run: `cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher && ./.venv/bin/python -m pytest tests/test_web_routes.py -q`
Expected: FAIL because the current web app does not expose these states yet

- [ ] **Step 3: Implement UI and API changes**

Add:
- draft list summary
- validation section
- publish history section
- execution mode controls
- retry action wiring

- [ ] **Step 4: Re-run the web tests**

Run: `cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher && ./.venv/bin/python -m pytest tests/test_web_routes.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
git add src/mvpublisher/web/app.py src/mvpublisher/web/templates/index.html src/mvpublisher/web/templates/draft_detail.html tests/test_web_routes.py
git commit -m "feat: add p0 review workspace states"
```

## Task 5: Verify The P0 Slice End To End

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap-1.0.md`
  Only if implementation changes the roadmap wording

- [ ] **Step 1: Run the relevant test suite**

Run: `cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher && ./.venv/bin/python -m pytest tests/test_draft_models.py tests/test_validation_service.py tests/test_storage.py tests/test_approval_service.py tests/test_publish_runner.py tests/test_web_routes.py -q`
Expected: PASS

- [ ] **Step 2: Run the full suite**

Run: `cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher && ./.venv/bin/python -m pytest -q`
Expected: PASS

- [ ] **Step 3: Update docs if needed**

Document:
- execution mode selection
- validation failures
- history and retry behavior

- [ ] **Step 4: Commit**

```bash
cd /Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher
git add README.md docs/roadmap-1.0.md
git commit -m "docs: describe p0 stable core workflow"
```
