# Chrome Current-Session Failure Archive

This note archives the real failures found while validating the Chrome current-session publish path against Xiaohongshu, Douyin, and WeChat Channels on April 7, 2026.

Use it as a first-stop troubleshooting reference before assuming a platform workflow is fully broken.

## Fast Triage

| Symptom | Likely Layer | How To Confirm | Script-Fixable |
| --- | --- | --- | --- |
| `No such file or directory` for `scripts/chrome_current_session_publish.sh` under `.venv/...` | Local Python package path resolution | Run `./.venv/bin/python -m mvpublisher.cli publish-draft <draft-id>` and inspect the missing path | Yes |
| `TypeError: Failed to fetch` during injected upload but local asset server shows `200` | Browser fetch to local asset server | Check `/tmp/chrome-current-session-publish.log` and compare browser-side error with server-side `GET` success | Yes |
| Xiaohongshu fills fields but does not actually publish | Wrong element targeted for submit, or button not ready yet | Inspect real page and confirm semantic `button` exists before submit | Yes |
| Douyin reaches publish stage then AppleScript throws syntax error `-2741` | Script syntax, not platform behavior | Re-run single-platform Douyin publish and inspect `publish_douyin()` block | Yes |
| Douyin publish clicks but never leaves editor page | Post-cover modal still blocks submit | Check whether `设置横封面获更多流量` prompt is still visible | Yes |
| WeChat Channels uploads and fills successfully but cannot publish | Platform account permissions | Inspect current page text for `你还不能发表视频` and missing admin/operator rights | No |

## Failure 1: Installed Environment Could Not Locate The Publish Script

### Symptom

`publish-draft` failed before any platform work started because the current-session runner tried to execute a path under `.venv/lib/python3.11/.../scripts/chrome_current_session_publish.sh`.

### Root Cause

The publisher resolved the shell script relative to the installed Python package location instead of the repository root.

### Fix

`src/mvpublisher/publishers/chrome_current_session.py` now searches `Path.cwd()`, its parents, and the module parents until it finds `scripts/chrome_current_session_publish.sh`.

### Verification

- `./.venv/bin/python -m pytest -q tests/test_chrome_current_session_publish.py`
- Confirm `test_find_current_session_publish_script_falls_back_to_repo_root_when_installed` passes.

## Failure 2: Injected Video Upload Was Unstable On HTTPS Creator Pages

### Symptom

Xiaohongshu upload began with:

- `upload_start`
- `scheduled`
- `{"ok":false,"error":"TypeError: Failed to fetch"}`

At the same time, the local asset server log still showed successful `GET /IMG_0037.MOV`.

### Root Cause

The old asset serving path used bare `python3 -m http.server`, which did not expose explicit CORS headers. The browser could still reach the server, but the page-side `fetch()` path was not stable enough for the injected upload flow.

### Fix

A dedicated local server at `scripts/chrome_current_session_asset_server.py` now serves assets with:

- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, HEAD, OPTIONS`
- `Access-Control-Allow-Headers: *`
- `Cache-Control: no-store`

`chrome_current_session_publish.sh` now launches that server instead of raw `http.server`.

### Verification

- Run the single-platform script for Xiaohongshu.
- Confirm upload returns a JSON success payload such as:
  - `{"ok":true,"files":1,"name":"IMG_0037.MOV","size":...}`

## Failure 3: Xiaohongshu Submit Click Was Targeting The Wrong DOM Node

### Symptom

The script logged `publish_start`, but the page stayed on the editor and no success page was detected.

### Root Cause

The submit helper searched `button,div,span` by text and could click a text wrapper instead of the real submit button.

### Fix

`publish_xiaohongshu()` now:

- waits up to 25 seconds for a semantic `button` whose trimmed text is `发布`
- ignores disabled buttons
- clicks the real `button`, not a nested `div` or `span`

### Verification

Run the Xiaohongshu script directly and confirm the result reaches:

- `https://creator.xiaohongshu.com/publish/success?...`
- page text includes `发布成功`

## Failure 4: Douyin Publish Failed Because Of AppleScript Syntax

### Symptom

Douyin progressed through upload, title fill, description fill, and cover fill, then failed at publish with AppleScript syntax error `-2741`.

### Root Cause

`publish_douyin()` had an incorrectly escaped `return \"NOT_FOUND\"` inside a heredoc, which AppleScript treated as invalid syntax.

### Fix

The return statement now uses normal AppleScript string syntax:

- `return "NOT_FOUND"`

### Verification

- Run `./.venv/bin/python -m pytest -q tests/test_chrome_current_session_publish.py`
- Confirm `test_current_session_script_keeps_douyin_applescript_return_unescaped` passes.

## Failure 5: Douyin Horizontal-Cover Prompt Blocked Final Submit

### Symptom

Douyin cover upload finished, but the editor remained blocked by a prompt offering extra horizontal-cover setup. The normal `发布` button could be clicked without navigating to the manage page.

### Root Cause

The script completed the cover flow but did not dismiss the follow-up recommendation overlay containing `设置横封面获更多流量`.

### Fix

After `verify_douyin_cover`, the script now runs `dismiss_douyin_cover_prompt()` and clicks:

- `暂不设置` when the prompt is present
- or `完成` as a fallback dismissal path

### Verification

Run the single-platform Douyin script and confirm the final result lands on:

- `https://creator.douyin.com/creator-micro/content/manage?enter_from=publish`

## Failure 6: WeChat Channels Needed Clear Separation Between Timing And Permissions

### Symptom

WeChat Channels completed:

- injected upload
- title fill
- description fill
- cover upload
- cover verification

but publish did not complete.

### Root Cause

Two different classes of issues were present:

1. Timing risk:
   The script could attempt `发表` before the page was fully ready.
2. Platform permission block:
   The account displayed `你还不能发表视频` because the current login was not an admin or operator for that video account.

### Fix

The script now waits for publish readiness before clicking `发表`:

- `发表` button exists
- button is not disabled
- page text does not contain `上传中`, `处理中`, or `生成中`

This prevents premature submit attempts.

The permission issue is not script-fixable and should be surfaced to the operator as a platform-side blocker.

### Verification

- For timing: confirm the publish step waits until the button is ready.
- For permissions: inspect page text for `你还不能发表视频` and verify the current login has video account admin/operator rights.

## Recommended Operator Checklist Before Re-Running A Failed Publish

1. Run `./.venv/bin/python -m pytest -q tests/test_chrome_current_session_publish.py tests/test_platform_publishers_script_usage.py`.
2. If upload fails with `Failed to fetch`, inspect `/tmp/chrome-current-session-publish.log`.
3. If Xiaohongshu or Douyin stays on the editor page, inspect whether the final submit button is real and unobstructed.
4. If WeChat Channels fails, first check for permission text before changing the automation.
5. When in doubt, rerun a single-platform script instead of a full three-platform publish.
