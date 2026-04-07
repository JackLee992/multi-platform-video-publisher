# Publish Failure Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the root causes, fixes, and verification steps for the Chrome current-session publish failures found during real-platform validation.

**Architecture:** Add one focused troubleshooting archive for maintainers and one short README pointer so operators know where to look before retrying a failed publish. Keep the archive organized by symptom, root cause, fix, and verification evidence.

**Tech Stack:** Markdown, existing repository docs, pytest verification notes

---

### Task 1: Archive The Failure Modes

**Files:**
- Create: `docs/chrome-current-session-failure-archive.md`

- [ ] **Step 1: Write the archive document**

Include sections for:
- script path resolution failing from installed environments
- local asset fetch instability from HTTPS creator pages
- Xiaohongshu publish button targeting the wrong DOM element
- Douyin publish AppleScript syntax break
- Douyin horizontal-cover prompt blocking final submit
- WeChat Channels permission failure versus script timing issues

- [ ] **Step 2: Include a fast triage table**

Document:
- symptom
- likely layer
- how to confirm
- whether it is script-fixable or operator/platform-blocked

### Task 2: Link The Archive From Main Docs

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a troubleshooting pointer**

Place it near the real-publish guidance and first-run permissions so users can find the archive before rerunning live publishes.

### Task 3: Verify And Keep Scope Tight

**Files:**
- Test: `./.venv/bin/python -m pytest -q tests/test_chrome_current_session_publish.py tests/test_platform_publishers_script_usage.py`

- [ ] **Step 1: Run focused verification**

Run:

```bash
./.venv/bin/python -m pytest -q tests/test_chrome_current_session_publish.py tests/test_platform_publishers_script_usage.py
```

Expected: PASS
