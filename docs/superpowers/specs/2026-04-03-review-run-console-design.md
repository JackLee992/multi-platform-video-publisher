# Review Run Console Design

## Context

The project currently supports a standard review-first flow:

1. Create draft from local video
2. Open draft review page
3. Human confirms title, cover, platforms, and execution mode
4. Run publish execution

The review page already supports approval, validation display, publish history, and retry. What is missing is an in-page execution control that behaves more like a development tool:

- a clear `Run` button
- visible execution progress
- visible per-platform results
- a lightweight debug surface for the current run

The goal is to make the standard review page the primary operator surface, instead of forcing the operator to switch back to the CLI to trigger publish execution.

## Goals

- Keep the standard flow review-first by default
- Add a `Run` button directly in the draft review page
- Show in-page execution progress and final results
- Reuse existing publish workflow and publish history storage
- Make the page useful as a lightweight debugging console for the latest run

## Non-Goals

- Replacing publish history with a brand new event system
- Implementing WebSocket streaming in the first version
- Running multiple publish jobs concurrently from one draft page
- Building a separate standalone execution dashboard

## User Experience

The draft detail page will gain a new section: `Run Console`.

This section has two parts:

1. `Run Controls`
   - `Run` button
   - execution mode summary
   - readiness hint
   - disabled state when draft is not yet approved
   - running state when a run is already active

2. `Run Output`
   - current run status: `idle`, `running`, `success`, `failed`, `partial`
   - a scrolling log area with timestamped messages
   - result cards for each selected platform
   - fields per platform:
     - platform name
     - execution status
     - success signal
     - result URL
     - error message
     - finished time

## Interaction Rules

### Approval Gate

The `Run` button is only enabled after the draft has been saved and approved.

If the draft has unsaved edits, the operator must click `保存确认` first.

### Running State

When the run starts:

- the `Run` button becomes disabled
- its label changes to `Running...`
- the output panel starts polling for current run data

### Completion State

When the run finishes:

- the output panel shows final aggregated status
- platform result cards are updated
- publish history remains the source of truth for archived runs
- the page may optionally refresh publish history automatically after polling detects completion

## Architecture

This feature adds a thin runtime layer on top of the existing publish workflow.

### Existing Reuse

Reuse these current pieces:

- draft approval state
- `publish_draft_from_repository(...)`
- platform publishers
- publish history
- artifact writing

### New Pieces

Add a per-run status store for the currently active review-page execution.

Recommended model:

- one lightweight run-state file under the draft artifact directory
- written incrementally by the run endpoint
- read by a polling status endpoint

This keeps the implementation simple and avoids introducing WebSockets or background task infrastructure in the first version.

## Backend Design

### New Endpoint: Start Run

Add:

- `POST /api/drafts/{draft_id}/run`

Behavior:

1. Load draft
2. Verify draft is approved
3. Create a `current run` state record
4. Write initial log lines
5. Execute publish workflow
6. Update run-state as each platform completes
7. Mark final run status

### New Endpoint: Poll Run Status

Add:

- `GET /api/drafts/{draft_id}/run-status`

Behavior:

1. Load latest run-state file for the draft
2. Return:
   - run status
   - started time
   - finished time
   - log lines
   - per-platform results

### Run-State Storage

Recommended path:

- `runtime/artifacts/<draft_id>/run_console/latest.json`

Recommended shape:

- `draft_id`
- `status`
- `started_at`
- `finished_at`
- `execution_mode`
- `logs`
- `results`

Each log item should contain:

- timestamp
- level
- message

Each result item should contain:

- platform name
- status
- success signal
- result URL
- error message
- finished time

## Frontend Design

Modify the draft detail page to add a `Run Console` section below the approval form and above or alongside publish history.

### Run Controls

Show:

- current approval status
- current execution mode
- `Run` button

Button behavior:

- disabled when `approval_status != approved`
- disabled while a run is in progress
- clicking sends `POST /api/drafts/{draft_id}/run`

### Run Output

Show:

- current status badge
- live log list
- per-platform cards

Polling behavior:

- start polling after successful `Run`
- poll every 1 to 2 seconds
- stop polling when run reaches final state

## Status Semantics

### Overall Run Status

Use:

- `idle`
- `running`
- `success`
- `failed`
- `partial`

Rules:

- `success` means all selected platforms ended in success-like terminal states
- `failed` means all selected platforms failed
- `partial` means mixed outcomes

### Platform Status

Reuse existing platform result status values whenever possible.

## Logging Plan

The first version should log only high-signal steps:

- run requested
- draft loaded
- publish workflow started
- platform execution started
- platform execution finished
- run finished

Do not attempt verbose browser-step logging in this first version.

If we later want deeper debugging, we can add richer per-platform logs or artifact links without changing the operator flow.

## Error Handling

### Run Start Errors

If the run cannot start:

- return HTTP 400 for approval or validation problems
- show the error inline in the run console

### Mid-Run Errors

If one platform fails:

- continue collecting remaining platform results when practical
- mark overall status as `partial` or `failed`
- preserve the platform error message in both run-state and publish history

### Polling Errors

If polling fails temporarily:

- keep the last known UI state
- show a short inline warning
- allow manual refresh

## Testing

Add tests for:

- run endpoint rejects unapproved drafts
- run endpoint creates run-state
- run-status endpoint returns latest state
- final run-state matches publish workflow results
- draft detail template renders run console scaffold

## Acceptance Criteria

- The review page has a visible `Run` button
- Approved drafts can start execution from the review page
- The page shows in-progress status without full page reload
- Final per-platform results are visible in-page
- Publish history still records final archived results
- Failed runs show visible error information

## Future Extensions

Possible later improvements:

- WebSocket log streaming
- links to artifact files per platform
- richer debug details
- cancel run
- rerun failed platforms from the same run console
