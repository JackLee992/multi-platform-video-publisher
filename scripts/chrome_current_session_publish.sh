#!/usr/bin/env bash

set -euo pipefail

PORT="${CHROME_INJECT_PORT:-8765}"
HOST="${CHROME_INJECT_HOST:-127.0.0.1}"

usage() {
  cat <<'EOF'
Usage:
  chrome_current_session_publish.sh --video /abs/path.mov --title "Title" [options]

Options:
  --video PATH           Absolute path to local video file
  --title TEXT           Shared title used across platforms
  --description TEXT     Optional description. Defaults to title
  --platform NAME        xiaohongshu | douyin | wechat_channels | all
  --port N               Local file server port. Default: 8765
  --skip-publish         Only upload and fill fields, do not click final publish

Examples:
  ./scripts/chrome_current_session_publish.sh \
    --video /Users/me/Downloads/test.mov \
    --title "第二次三端测试"

  ./scripts/chrome_current_session_publish.sh \
    --video /Users/me/Downloads/test.mov \
    --title "第二次三端测试" \
    --platform xiaohongshu
EOF
}

VIDEO_PATH=""
TITLE=""
DESCRIPTION=""
PLATFORM="all"
SKIP_PUBLISH="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --video)
      VIDEO_PATH="$2"
      shift 2
      ;;
    --title)
      TITLE="$2"
      shift 2
      ;;
    --description)
      DESCRIPTION="$2"
      shift 2
      ;;
    --platform)
      PLATFORM="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --skip-publish)
      SKIP_PUBLISH="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$VIDEO_PATH" || -z "$TITLE" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "$VIDEO_PATH" ]]; then
  echo "Video not found: $VIDEO_PATH" >&2
  exit 1
fi

if [[ -z "$DESCRIPTION" ]]; then
  DESCRIPTION="$TITLE"
fi

VIDEO_DIR="$(cd "$(dirname "$VIDEO_PATH")" && pwd)"
VIDEO_FILE="$(basename "$VIDEO_PATH")"

ensure_server() {
  if ! lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    python3 -m http.server "$PORT" --bind "$HOST" --directory "$VIDEO_DIR" >/tmp/chrome-current-session-publish.log 2>&1 &
    SERVER_PID=$!
    sleep 1
  else
    SERVER_PID=""
  fi
}

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

ensure_server

curl -fsSI "http://${HOST}:${PORT}/${VIDEO_FILE}" >/dev/null

run_osascript() {
  osascript - "$@"
}

focus_platform_tab() {
  local platform_name="$1"
  local match_expr=""

  case "$platform_name" in
    xiaohongshu)
      match_expr='url starts with "https://creator.xiaohongshu.com/publish/publish" or url starts with "https://creator.xiaohongshu.com/publish/success"'
      ;;
    douyin)
      match_expr='url starts with "https://creator.douyin.com/creator-micro/content/upload" or url starts with "https://creator.douyin.com/creator-micro/content/post/video" or url starts with "https://creator.douyin.com/creator-micro/content/manage"'
      ;;
    wechat_channels)
      match_expr='url starts with "https://channels.weixin.qq.com/platform/post/create" or url starts with "https://channels.weixin.qq.com/platform/post/list"'
      ;;
    *)
      return 0
      ;;
  esac

  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  activate
  set matchedWindowIndex to 0
  set matchedTabIndex to 0
  repeat with w in windows
    repeat with i from 1 to (count of tabs of w)
      set t to tab i of w
      set tabUrl to (URL of t as text)
      if ${match_expr//url/tabUrl} then
        set matchedWindowIndex to index of w
        set matchedTabIndex to i
      end if
    end repeat
  end repeat
  if matchedWindowIndex is not 0 then
    set index of window matchedWindowIndex to 1
    set active tab index of window 1 to matchedTabIndex
    return "focused"
  end if
end tell
return "not_found"
APPLESCRIPT
}

upload_xiaohongshu() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://creator.xiaohongshu.com/publish/publish" then
        set js to "window.__codexUploadResult='starting'; (async () => { try { const input = document.querySelector('input[type=file]'); if (!input) throw new Error('missing input'); const res = await fetch('http://${HOST}:${PORT}/${VIDEO_FILE}'); const blob = await res.blob(); const file = new File([blob], '${VIDEO_FILE}', {type: blob.type || 'video/quicktime'}); const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files; input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); window.__codexUploadResult = JSON.stringify({ok:true, files: input.files.length, name: input.files[0] && input.files[0].name, size: input.files[0] && input.files[0].size}); } catch (error) { window.__codexUploadResult = JSON.stringify({ok:false, error: String(error)}); } })(); 'scheduled'"
        return execute t javascript js
      end if
    end repeat
  end repeat
end tell
APPLESCRIPT
}

poll_xiaohongshu_upload() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 25 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.xiaohongshu.com/publish/publish" then
          set resultJson to execute t javascript "window.__codexUploadResult || ''"
          if resultJson is not "" and resultJson is not "starting" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "timeout"
end tell
APPLESCRIPT
}

fill_xiaohongshu() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://creator.xiaohongshu.com/publish/publish" then
        set js to "(() => { const title = ${TITLE@Q}; const titleInput = Array.from(document.querySelectorAll('input')).find(el => (el.placeholder || '').includes('填写标题')); if (!titleInput) return JSON.stringify({ok:false,error:'missing title input'}); const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; setter.call(titleInput, title); titleInput.dispatchEvent(new Event('input', { bubbles: true })); titleInput.dispatchEvent(new Event('change', { bubbles: true })); return JSON.stringify({ok:true, title:titleInput.value}); })()"
        return execute t javascript js
      end if
    end repeat
  end repeat
end tell
APPLESCRIPT
}

publish_xiaohongshu() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://creator.xiaohongshu.com/publish/publish" then
        set marker to execute t javascript "(document.body && document.body.innerText || '').includes('发布') ? 'MATCH' : ''"
        if marker is "MATCH" then
          return execute t javascript "(() => { const btn = Array.from(document.querySelectorAll('button,div,span')).find(el => (el.innerText || '').trim() === '发布'); if (!btn) return JSON.stringify({ok:false,error:'missing publish'}); btn.click(); return JSON.stringify({ok:true,text:btn.innerText,url:location.href}); })()"
        end if
      end if
    end repeat
  end repeat
  return "NOT_FOUND"
end tell
APPLESCRIPT
}

check_xiaohongshu_result() {
  sleep 4
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) contains "creator.xiaohongshu.com" then
        set bodyText to execute t javascript "(document.body && document.body.innerText || '').slice(0,1200)"
        if (URL of t as text) contains "/publish/success" or bodyText contains "发布成功" then
          return (URL of t as text) & linefeed & bodyText
        end if
      end if
    end repeat
  end repeat
  return "NOT_FOUND"
end tell
APPLESCRIPT
}

upload_douyin() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/upload" or (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/post/video" then
        set js to "window.__codexDouyinUpload='starting'; (async () => { try { const input = document.querySelector('input[type=file]'); if (!input) throw new Error('missing input'); const res = await fetch('http://${HOST}:${PORT}/${VIDEO_FILE}'); const blob = await res.blob(); const file = new File([blob], '${VIDEO_FILE}', {type: blob.type || 'video/quicktime'}); const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files; input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); window.__codexDouyinUpload = JSON.stringify({ok:true, files: input.files.length, name: input.files[0] && input.files[0].name, size: input.files[0] && input.files[0].size}); } catch (error) { window.__codexDouyinUpload = JSON.stringify({ok:false, error: String(error)}); } })(); 'scheduled'"
        return execute t javascript js
      end if
    end repeat
  end repeat
end tell
APPLESCRIPT
}

poll_douyin_upload() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 25 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/upload" or (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/post/video" then
          set resultJson to execute t javascript "window.__codexDouyinUpload || ''"
          if resultJson is not "" and resultJson is not "starting" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "timeout"
end tell
APPLESCRIPT
}

fill_douyin() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/upload" or (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/post/video" then
        set js to "(() => { const title = ${TITLE@Q}; const desc = ${DESCRIPTION@Q}; const titleInput = Array.from(document.querySelectorAll('input')).find(el => (el.placeholder || '').includes('填写作品标题')); if (!titleInput) return JSON.stringify({ok:false,error:'missing title input'}); const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; setter.call(titleInput, title); titleInput.dispatchEvent(new Event('input', { bubbles: true })); titleInput.dispatchEvent(new Event('change', { bubbles: true })); const editor = document.querySelector('[contenteditable=true]'); if (editor) { editor.focus(); editor.innerHTML = ''; editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward', data: null })); editor.textContent = desc; editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: desc })); editor.dispatchEvent(new Event('change', { bubbles: true })); } return JSON.stringify({ok:true, title:titleInput.value, editorText: editor ? editor.innerText : null}); })()"
        return execute t javascript js
      end if
    end repeat
  end repeat
end tell
APPLESCRIPT
}

publish_douyin() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/upload" or (URL of t as text) starts with "https://creator.douyin.com/creator-micro/content/post/video" then
        return execute t javascript "(() => { const btn = Array.from(document.querySelectorAll('button')).find(el => (el.innerText || '').includes('发布') && !(el.innerText || '').includes('高清发布')); if (!btn) return JSON.stringify({ok:false,error:'missing publish'}); btn.click(); return JSON.stringify({ok:true,text:btn.innerText,url:location.href}); })()"
      end if
    end repeat
  end repeat
  return \"NOT_FOUND\"
end tell
APPLESCRIPT
}

check_douyin_result() {
  sleep 5
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) contains "creator.douyin.com" then
        set bodyText to execute t javascript "(document.body && document.body.innerText || '').slice(0,1200)"
        if (URL of t as text) contains "/content/manage" then
          return (URL of t as text) & linefeed & bodyText
        end if
      end if
    end repeat
  end repeat
  return "NOT_FOUND"
end tell
APPLESCRIPT
}

upload_wechat_channels() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
        set js to "window.__codexWxUpload='starting'; (async () => { try { const host = document.querySelector('wujie-app'); const shadow = host && host.shadowRoot; const input = shadow && shadow.querySelector('input[type=file]'); if (!input) throw new Error('missing shadow input'); const res = await fetch('http://${HOST}:${PORT}/${VIDEO_FILE}'); const blob = await res.blob(); const file = new File([blob], '${VIDEO_FILE}', {type: blob.type || 'video/quicktime'}); const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files; input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); window.__codexWxUpload = JSON.stringify({ok:true, files: input.files.length, name: input.files[0] && input.files[0].name, size: input.files[0] && input.files[0].size}); } catch (error) { window.__codexWxUpload = JSON.stringify({ok:false, error: String(error)}); } })(); 'scheduled'"
        return execute t javascript js
      end if
    end repeat
  end repeat
end tell
APPLESCRIPT
}

poll_wechat_channels_upload() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat 25 times
    repeat with w in windows
      repeat with t in tabs of w
        if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
          set resultJson to execute t javascript "window.__codexWxUpload || ''"
          if resultJson is not "" and resultJson is not "starting" then return resultJson
        end if
      end repeat
    end repeat
    delay 1
  end repeat
  return "timeout"
end tell
APPLESCRIPT
}

fill_wechat_channels() {
  run_osascript <<APPLESCRIPT
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
        set js to "(() => { const shadow = document.querySelector('wujie-app')?.shadowRoot; if (!shadow) return JSON.stringify({ok:false,error:'missing shadow root'}); const title = ${TITLE@Q}; const titleInput = Array.from(shadow.querySelectorAll('input')).find(el => (el.placeholder || '').includes('6-16个字符')); if (!titleInput) return JSON.stringify({ok:false,error:'missing short title input'}); const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; setter.call(titleInput, title); titleInput.dispatchEvent(new Event('input', { bubbles: true })); titleInput.dispatchEvent(new Event('change', { bubbles: true })); return JSON.stringify({ok:true, title:titleInput.value}); })()"
        return execute t javascript js
      end if
    end repeat
  end repeat
end tell
APPLESCRIPT
}

publish_wechat_channels() {
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/create" then
        return execute t javascript "(() => { const shadow = document.querySelector('wujie-app')?.shadowRoot; const btn = shadow && Array.from(shadow.querySelectorAll('button')).find(el => (el.innerText || '').trim() === '发表'); if (!btn) return JSON.stringify({ok:false,error:'missing publish'}); btn.click(); return JSON.stringify({ok:true,text:btn.innerText,url:location.href}); })()"
      end if
    end repeat
  end repeat
  return "NOT_FOUND"
end tell
APPLESCRIPT
}

check_wechat_channels_result() {
  sleep 5
  run_osascript <<'APPLESCRIPT'
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if (URL of t as text) starts with "https://channels.weixin.qq.com/platform/post/" then
        set js to "(() => { const shadow = document.querySelector('wujie-app')?.shadowRoot; const text = shadow ? (shadow.innerText || '').slice(0,1200) : ((document.body && document.body.innerText) || '').slice(0,1200); return JSON.stringify({url: location.href, text}); })()"
        return execute t javascript js
      end if
    end repeat
  end repeat
  return "NOT_FOUND"
end tell
APPLESCRIPT
}

run_platform() {
  local platform_name="$1"
  echo "==> ${platform_name}"

  case "$platform_name" in
    xiaohongshu)
      upload_xiaohongshu
      poll_xiaohongshu_upload
      fill_xiaohongshu
      if [[ "$SKIP_PUBLISH" == "false" ]]; then
        publish_xiaohongshu
        check_xiaohongshu_result
      fi
      ;;
    douyin)
      upload_douyin
      poll_douyin_upload
      fill_douyin
      if [[ "$SKIP_PUBLISH" == "false" ]]; then
        publish_douyin
        check_douyin_result
      fi
      ;;
    wechat_channels)
      upload_wechat_channels
      poll_wechat_channels_upload
      fill_wechat_channels
      if [[ "$SKIP_PUBLISH" == "false" ]]; then
        publish_wechat_channels
        check_wechat_channels_result
      fi
      ;;
    *)
      echo "Unsupported platform: $platform_name" >&2
      exit 1
      ;;
  esac

  focus_platform_tab "$platform_name" >/dev/null
}

if [[ "$PLATFORM" == "all" ]]; then
  run_platform xiaohongshu
  run_platform douyin
  run_platform wechat_channels
else
  run_platform "$PLATFORM"
fi
