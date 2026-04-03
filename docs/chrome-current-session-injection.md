# Chrome Current Session Injection

This note captures the Chrome-session injection path that was validated on April 3, 2026.

It is intended for local operator-assisted publishing when:

- the target accounts are already logged in inside the user's current Chrome profile
- a platform page exposes a usable file input in the main DOM or an open shadow root
- we want to avoid the macOS file picker and inject the file from a local HTTP server instead

## Verified flow

The repository script [`scripts/chrome_current_session_publish.sh`](/Users/elainelee999/Documents/Playground/.worktrees/codex-multi-platform-publisher/multi-platform-video-publisher/scripts/chrome_current_session_publish.sh) follows this shape:

1. Ensure a local HTTP server can serve the source video.
2. Find the already-open Chrome tab for the target platform.
3. Run JavaScript inside that tab with AppleScript `execute ... javascript`.
4. Fetch the local video over `http://127.0.0.1:<port>/<filename>`.
5. Build a `File`, attach it to the page's `input[type=file]`, and dispatch `input` plus `change`.
6. Fill the minimum title or description fields.
7. Optionally click the final publish button.
8. Poll the same tab for a post-submit success signal.

## Verified page targets

- Xiaohongshu:
  - page: `https://creator.xiaohongshu.com/publish/publish`
  - upload input in main DOM
  - publish success signal: URL contains `/publish/success` or page contains `发布成功`
- Douyin:
  - page: `https://creator.douyin.com/creator-micro/content/upload`
  - upload input in main DOM
  - publish success signal: URL contains `/content/manage`
- WeChat Channels:
  - page: `https://channels.weixin.qq.com/platform/post/create`
  - upload input inside `wujie-app.shadowRoot`
  - publish success signal: URL contains `/platform/post/list`

## Known limitations

- This path depends on current page structure and visible upload inputs.
- It does not replace final account-level permissions on the platform side.
- It assumes the current Chrome tab is still logged in and not blocked by a modal we cannot dismiss safely.
- The local file server must serve the exact filename used in the injected `fetch(...)`.
